"""
League-Wide Context Fetcher & Cache Orchestrator.

Fetches and caches season records, advanced ratings (OffRtg, DefRtg, NetRtg, Pace)
and the Four Factors for all 30 NBA teams into data/cache/league_standings_{season}.parquet,
plus per-player season stats for any one team (the next opponent).

Used by:
  - Next Game preview (viz/matchup_viz.py)
  - Matchup projections (analysis/predictions.py)
"""

from __future__ import annotations

import logging
from pathlib import Path
import pandas as pd

import config
from config import CACHE_DIR, TEAMS, season_str
from client.nba_client import NBAClient

log = logging.getLogger(__name__)

LEAGUE_STANDINGS_SCHEMA: dict[str, str] = {
    "team_id": "Int64",
    "team_abbr": "object",
    "team_name": "object",
    "conference": "object",
    "division": "object",
    "wins": "Int64",
    "losses": "Int64",
    "win_pct": "Float64",
    "pts_pg": "Float64",
    "opp_pts_pg": "Float64",
    "margin": "Float64",
    "ortg": "Float64",
    "drtg": "Float64",
    "nrtg": "Float64",
    "pace": "Float64",
    # Four Factors, own and allowed
    "efg_pct": "Float64",
    "tov_pct": "Float64",
    "oreb_pct": "Float64",
    "fta_rate": "Float64",
    "opp_efg_pct": "Float64",
    "opp_tov_pct": "Float64",
    "opp_oreb_pct": "Float64",
    "opp_fta_rate": "Float64",
}


def _cache_path(season: int) -> Path:
    return CACHE_DIR / f"league_standings_{season}.parquet"


def fetch_league_standings(
    season: int = config.SEASON,
    client: NBAClient | None = None,
    force_refresh: bool = False,
) -> pd.DataFrame:
    """
    Fetch and cache league-wide records, ratings and Four Factors for all 30 teams.
    Returns DataFrame matching LEAGUE_STANDINGS_SCHEMA.

    If the API is unreachable the last good cache is returned; with no cache the
    error propagates. Ratings are never filled with placeholders, since every
    matchup comparison downstream would silently treat all 30 teams as equal.
    """
    cache_file = _cache_path(season)
    if not force_refresh and cache_file.exists():
        log.info("Loading league standings from cache: %s", cache_file)
        return pd.read_parquet(cache_file)

    client = client or NBAClient()
    season_s = season_str(season)
    log.info("Fetching league ratings for %s...", season_s)

    try:
        base = client.get_league_team_stats(season_s, "Base")
        adv = client.get_league_team_stats(season_s, "Advanced")
        ff = client.get_league_team_stats(season_s, "Four Factors")
    except Exception as e:
        if cache_file.exists():
            log.warning("League ratings fetch failed (%s); keeping last cache %s", e, cache_file)
            return pd.read_parquet(cache_file)
        raise

    id_to_abbr = {v["id"]: k for k, v in TEAMS.items()}
    df = (
        base[["team_id", "gp", "w", "l", "w_pct", "pts", "plus_minus"]]
        .merge(adv[["team_id", "off_rating", "def_rating", "net_rating", "pace"]], on="team_id")
        .merge(ff[["team_id", "efg_pct", "fta_rate", "tm_tov_pct", "oreb_pct",
                   "opp_efg_pct", "opp_fta_rate", "opp_tov_pct", "opp_oreb_pct"]], on="team_id")
    )
    df["team_abbr"] = df["team_id"].map(id_to_abbr)
    df = df[df["team_abbr"].notna()].copy()
    out = pd.DataFrame({
        "team_id": df["team_id"],
        "team_abbr": df["team_abbr"],
        "team_name": df["team_abbr"].map(lambda a: TEAMS[a]["name"]),
        "conference": df["team_abbr"].map(lambda a: TEAMS[a]["conf"]),
        "division": df["team_abbr"].map(lambda a: TEAMS[a]["div"]),
        "wins": df["w"],
        "losses": df["l"],
        "win_pct": df["w_pct"],
        "pts_pg": df["pts"].round(1),
        "opp_pts_pg": (df["pts"] - df["plus_minus"]).round(1),
        "margin": df["plus_minus"].round(2),
        "ortg": df["off_rating"],
        "drtg": df["def_rating"],
        "nrtg": df["net_rating"],
        "pace": df["pace"],
        "efg_pct": df["efg_pct"],
        "tov_pct": df["tm_tov_pct"],
        "oreb_pct": df["oreb_pct"],
        "fta_rate": df["fta_rate"],
        "opp_efg_pct": df["opp_efg_pct"],
        "opp_tov_pct": df["opp_tov_pct"],
        "opp_oreb_pct": df["opp_oreb_pct"],
        "opp_fta_rate": df["opp_fta_rate"],
    })
    for col, dtype in LEAGUE_STANDINGS_SCHEMA.items():
        out[col] = out[col].astype(dtype)

    cache_file.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(cache_file, index=False)
    log.info("Cached %d teams in league standings → %s", len(out), cache_file)
    return out.reset_index(drop=True)


def load_league_standings(season: int = config.SEASON) -> pd.DataFrame:
    """Load cached league standings."""
    cache_file = _cache_path(season)
    if not cache_file.exists():
        return fetch_league_standings(season=season, force_refresh=False)
    return pd.read_parquet(cache_file)


# ---------------------------------------------------------------------------
# One team's player season stats (used for the next opponent's players to watch)
# ---------------------------------------------------------------------------

def _team_players_path(team_id: int, season: int) -> Path:
    return CACHE_DIR / f"team_players_{team_id}_{season}.parquet"


def fetch_team_players(team_id: int, season: int = config.SEASON,
                       client: NBAClient | None = None, force_refresh: bool = False) -> pd.DataFrame:
    """Per-game season stats for every player on one team; last cache kept if the API fails."""
    path = _team_players_path(team_id, season)
    if not force_refresh and path.exists():
        return pd.read_parquet(path)
    client = client or NBAClient()
    try:
        df = client.get_league_player_stats(season_str(season), team_id=team_id)
    except Exception as e:
        if path.exists():
            log.warning("Player stats fetch failed for %s (%s); keeping last cache", team_id, e)
            return pd.read_parquet(path)
        raise
    keep = ["player_id", "player_name", "gp", "min", "pts", "reb", "oreb", "dreb", "ast", "stl", "blk",
            "tov", "pf", "fgm", "fga", "fg3m", "ftm", "fta", "plus_minus"]
    df = df[[c for c in keep if c in df.columns]]
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    return df


def load_team_players(team_id: int, season: int = config.SEASON) -> pd.DataFrame:
    path = _team_players_path(team_id, season)
    return pd.read_parquet(path) if path.exists() else pd.DataFrame()
