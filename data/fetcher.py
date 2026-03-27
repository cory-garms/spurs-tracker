"""
Data fetcher — orchestrates all NBA Stats API calls and builds the
three canonical tables (games, player_game_log, roster).

Usage (programmatic):
    from data.fetcher import Fetcher
    f = Fetcher(team_id=1610612759, season=2024)
    f.fetch_all()

Tables written to data/cache/:
    games_{team_id}_{season}.parquet
    player_game_log_{team_id}_{season}.parquet
    roster_{team_id}_{season}.parquet
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from client.nba_client import NBAClient
from data.schema import GAMES_SCHEMA, PLAYER_GAME_LOG_SCHEMA, enforce_schema
from data.roster import fetch_roster
from config import CACHE_DIR, TEAMS, season_str

log = logging.getLogger(__name__)

# Build {abbreviation: team_id} reverse lookup
_ABBR_TO_ID: dict[str, int] = {k: v["id"] for k, v in TEAMS.items()}
_ID_TO_ABBR: dict[int, str] = {v["id"]: k for k, v in TEAMS.items()}

# NBA API sometimes returns slightly different abbreviations
_NBA_API_ABBR_MAP: dict[str, str] = {
    "PHO": "PHX", "NOH": "NOP", "NOK": "NOP", "NJN": "BKN",
    "SEA": "OKC", "VAN": "MEM", "CHH": "CHA", "CHO": "CHA",
    "GOS": "GSW", "UTH": "UTA",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_int(val, default: int = 0) -> int:
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def _safe_float(val, default: float = 0.0) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _parse_minutes(min_str) -> float:
    """Convert '35:12' or '35.000000' or numeric to float minutes."""
    if min_str is None or (isinstance(min_str, float) and pd.isna(min_str)):
        return 0.0
    s = str(min_str).strip()
    if ":" in s:
        parts = s.split(":")
        return round(int(parts[0]) + int(parts[1]) / 60, 2)
    try:
        return float(s)
    except ValueError:
        return 0.0


def _parse_game_date(date_str: str) -> str:
    """Normalize NBA API date strings to YYYY-MM-DD."""
    import dateutil.parser
    try:
        return dateutil.parser.parse(str(date_str)).strftime("%Y-%m-%d")
    except Exception:
        return str(date_str)


def _opponent_abbr_from_matchup(matchup: str, our_abbr: str) -> str:
    """
    Extract opponent abbreviation from matchup string like 'SAS vs. LAL'
    or 'SAS @ LAL'.
    """
    sep = "vs." if "vs." in matchup else "@"
    parts = matchup.split(sep)
    if len(parts) == 2:
        raw = parts[1].strip()
        return _NBA_API_ABBR_MAP.get(raw, raw)
    return ""


# ---------------------------------------------------------------------------
# Fetcher
# ---------------------------------------------------------------------------

class Fetcher:
    def __init__(
        self,
        team_id: int,
        season: int,
        client: NBAClient | None = None,
        force_refresh: bool = False,
    ) -> None:
        self.team_id   = team_id
        self.season    = season
        self.season_s  = season_str(season)
        self.client    = client or NBAClient()
        self.force     = force_refresh
        self.team_abbr = _ID_TO_ABBR.get(team_id, "")

    def _cache(self, name: str) -> Path:
        return CACHE_DIR / f"{name}_{self.team_id}_{self.season}.parquet"

    def _needs_refresh(self, name: str) -> bool:
        return self.force or not self._cache(name).exists()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def fetch_all(self) -> dict[str, pd.DataFrame]:
        """Fetch and cache all tables. Returns dict of DataFrames."""
        log.info("=== Fetching all data: team=%d season=%s ===",
                 self.team_id, self.season_s)

        roster = fetch_roster(self.team_id, self.season, self.client, self.force)

        if not self._needs_refresh("games") and not self._needs_refresh("player_game_log"):
            log.info("All tables cached, loading from disk")
            games      = pd.read_parquet(self._cache("games"))
            player_log = pd.read_parquet(self._cache("player_game_log"))
        else:
            games, player_log = self._fetch_boxscore_data()

        log.info("=== Fetch complete ===")
        return {
            "roster":          roster,
            "games":           games,
            "player_game_log": player_log,
        }

    # ------------------------------------------------------------------
    # Core fetch: game log + boxscores in one pass
    # ------------------------------------------------------------------

    def _fetch_boxscore_data(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Fetch team game log + per-game boxscores.
        Returns (games_df, player_game_log_df).
        """
        log.info("Fetching team game log for %s %s", self.team_abbr, self.season_s)
        game_log = self.client.get_team_game_log(
            self.team_id, self.season_s, season_type="Regular Season"
        )

        if game_log.empty:
            log.warning("No games found for team %d season %s", self.team_id, self.season_s)
            games_df  = pd.DataFrame()
            games_df  = enforce_schema(games_df, GAMES_SCHEMA)
            plog_df   = pd.DataFrame()
            plog_df   = enforce_schema(plog_df, PLAYER_GAME_LOG_SCHEMA)
            games_df.to_parquet(self._cache("games"), index=False)
            plog_df.to_parquet(self._cache("player_game_log"), index=False)
            return games_df, plog_df

        # game_log from teamgamelog has: game_id, game_date, matchup, wl, pts (no plus_minus)
        game_rows:  list[dict] = []
        player_rows: list[dict] = []

        total = len(game_log)
        log.info("Processing %d games...", total)

        for i, (_, gl_row) in enumerate(game_log.iterrows()):
            game_id   = str(gl_row["game_id"])
            raw_date  = gl_row.get("game_date", "")
            game_date = _parse_game_date(raw_date)
            matchup   = str(gl_row.get("matchup", ""))
            result    = str(gl_row.get("wl", "")).upper()
            pts       = _safe_int(gl_row.get("pts"))

            is_home      = "vs." in matchup
            opp_abbr_raw = _opponent_abbr_from_matchup(matchup, self.team_abbr)
            opp_abbr     = _NBA_API_ABBR_MAP.get(opp_abbr_raw, opp_abbr_raw)
            opp_id       = _ABBR_TO_ID.get(opp_abbr, 0)

            opp_pts = 0
            pace = ortg = drtg = nrtg = 0.0

            # Fetch advanced boxscore for pace/ratings and player usg_pct
            adv_player_df = pd.DataFrame()
            adv_team_df   = pd.DataFrame()
            try:
                adv_player_df, adv_team_df = self.client.get_boxscore_advanced(game_id)
                our_team_adv = adv_team_df[
                    adv_team_df["team_id"] == self.team_id
                ] if not adv_team_df.empty else pd.DataFrame()
                if not our_team_adv.empty:
                    pace = _safe_float(our_team_adv.iloc[0].get("pace"))
                    ortg = _safe_float(our_team_adv.iloc[0].get("off_rating"))
                    drtg = _safe_float(our_team_adv.iloc[0].get("def_rating"))
                    nrtg = _safe_float(our_team_adv.iloc[0].get("net_rating"))
            except Exception as e:
                log.warning("Advanced boxscore failed for %s: %s", game_id, e)

            # Traditional boxscore for player stats + opponent points
            try:
                trad_player_df, trad_team_df = self.client.get_boxscore_traditional(game_id)

                # opp_pts from the opponent's team row in the traditional boxscore
                if not trad_team_df.empty and "team_id" in trad_team_df.columns:
                    opp_team_row = trad_team_df[trad_team_df["team_id"] != self.team_id]
                    if not opp_team_row.empty:
                        opp_pts = _safe_int(opp_team_row.iloc[0].get("pts"))

                # Filter to our team's players
                our_players = trad_player_df[
                    trad_player_df["team_id"] == self.team_id
                ] if not trad_player_df.empty else pd.DataFrame()

                # Build usg_pct lookup from advanced boxscore
                usg_lookup: dict[int, float] = {}
                ts_lookup:  dict[int, float] = {}
                if not adv_player_df.empty:
                    our_adv = adv_player_df[adv_player_df["team_id"] == self.team_id]
                    for _, ar in our_adv.iterrows():
                        pid = _safe_int(ar.get("player_id"))
                        usg_lookup[pid] = _safe_float(ar.get("usg_pct"))
                        ts_lookup[pid]  = _safe_float(ar.get("ts_pct"))

                for _, pr in our_players.iterrows():
                    pid     = _safe_int(pr.get("player_id"))
                    minutes = _parse_minutes(pr.get("min"))

                    # Skip DNP entries
                    if minutes == 0 and str(pr.get("comment", "")).upper() in (
                        "DNP", "DND", "NWT", "INACTIVE"
                    ):
                        continue

                    fgm = _safe_int(pr.get("fgm"))
                    fga = _safe_int(pr.get("fga"))
                    ftm = _safe_int(pr.get("ftm"))
                    fta = _safe_int(pr.get("fta"))
                    pts_p = _safe_int(pr.get("pts"))
                    oreb  = _safe_int(pr.get("oreb"))
                    dreb  = _safe_int(pr.get("dreb"))

                    # Compute TS% if not available from advanced
                    ts_pct = ts_lookup.get(pid, 0.0)
                    if ts_pct == 0.0:
                        denom = 2 * (fga + 0.44 * fta)
                        ts_pct = round(pts_p / denom, 3) if denom > 0 else 0.0

                    fg_pct  = _safe_float(pr.get("fg_pct"))
                    fg3_pct = _safe_float(pr.get("fg3_pct"))
                    ft_pct  = _safe_float(pr.get("ft_pct"))
                    # Sometimes returned as None/NaN — recompute
                    fg3m = _safe_int(pr.get("fg3m"))
                    fg3a = _safe_int(pr.get("fg3a"))

                    player_rows.append({
                        "game_id":    game_id,
                        "game_date":  game_date,
                        "season":     self.season_s,
                        "player_id":  pid,
                        "player_name": str(pr.get("player_name", "")),
                        "min":        minutes,
                        "pts":        pts_p,
                        "reb":        oreb + dreb,
                        "ast":        _safe_int(pr.get("ast")),
                        "stl":        _safe_int(pr.get("stl")),
                        "blk":        _safe_int(pr.get("blk")),
                        "tov":        _safe_int(pr.get("to")),
                        "pf":         _safe_int(pr.get("pf")),
                        "fgm":        fgm,
                        "fga":        fga,
                        "fg_pct":     fg_pct if fg_pct else (fgm / fga if fga > 0 else 0.0),
                        "fg3m":       fg3m,
                        "fg3a":       fg3a,
                        "fg3_pct":    fg3_pct if fg3_pct else (fg3m / fg3a if fg3a > 0 else 0.0),
                        "ftm":        ftm,
                        "fta":        fta,
                        "ft_pct":     ft_pct if ft_pct else (ftm / fta if fta > 0 else 0.0),
                        "plus_minus": _safe_int(pr.get("plus_minus")),
                        "ts_pct":     ts_pct,
                        "usg_pct":    usg_lookup.get(pid, 0.0),
                    })
            except Exception as e:
                log.warning("Traditional boxscore failed for %s: %s", game_id, e)

            game_rows.append({
                "game_id":       game_id,
                "game_date":     game_date,
                "season":        self.season_s,
                "home_away":     "H" if is_home else "A",
                "opponent_id":   opp_id,
                "opponent_abbr": opp_abbr,
                "result":        result,
                "pts":           pts,
                "opp_pts":       opp_pts,
                "margin":        pts - opp_pts,
                "pace":          pace,
                "ortg":          ortg,
                "drtg":          drtg,
                "nrtg":          nrtg,
                "status":        "Final",
            })

            if (i + 1) % 10 == 0:
                log.info("  Processed %d / %d games", i + 1, total)

        games_df = pd.DataFrame(game_rows)
        games_df = enforce_schema(games_df, GAMES_SCHEMA)
        games_df.to_parquet(self._cache("games"), index=False)
        log.info("Cached %d games → %s", len(games_df), self._cache("games"))

        plog_df = pd.DataFrame(player_rows)
        plog_df = enforce_schema(plog_df, PLAYER_GAME_LOG_SCHEMA)
        plog_df.to_parquet(self._cache("player_game_log"), index=False)
        log.info("Cached %d player-game rows → %s", len(plog_df), self._cache("player_game_log"))

        return games_df, plog_df

    # ------------------------------------------------------------------
    # Load helpers (read-only, no API calls)
    # ------------------------------------------------------------------

    def load(self, name: str) -> pd.DataFrame:
        """Load a cached table by name: 'games', 'player_game_log', 'roster'."""
        path = self._cache(name)
        if not path.exists():
            raise FileNotFoundError(
                f"Cache not found: {path}\n"
                f"Run `python fetch.py --team {self.team_abbr} --season {self.season}` first."
            )
        return pd.read_parquet(path)
