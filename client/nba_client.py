"""
NBA Stats API client.

Wraps https://stats.nba.com/stats/ with retry logic, rate limiting,
and consistent response parsing.  No API key required, but specific
headers are required to avoid 403 responses.

All endpoints return {"resultSets": [{"headers": [...], "rowSet": [...]}]}.
"""

from __future__ import annotations

import time
import logging
from typing import Any

import pandas as pd
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import NBA_STATS_BASE, NBA_API_HEADERS, REQUEST_TIMEOUT, REQUEST_DELAY

log = logging.getLogger(__name__)


class NBAClient:
    """Thin, stateful wrapper around the NBA Stats API."""

    def __init__(self) -> None:
        self._session = requests.Session()
        self._session.headers.update(NBA_API_HEADERS)
        self._last_call: float = 0.0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_call
        if elapsed < REQUEST_DELAY:
            time.sleep(REQUEST_DELAY - elapsed)

    @retry(
        retry=retry_if_exception_type(requests.RequestException),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=15),
        reraise=True,
    )
    def _get(self, endpoint: str, params: dict | None = None) -> Any:
        self._throttle()
        url = f"{NBA_STATS_BASE}/{endpoint}"
        log.debug("GET %s %s", url, params)
        resp = self._session.get(url, params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        self._last_call = time.monotonic()
        return resp.json()

    def _parse(self, data: dict, result_set_index: int = 0) -> pd.DataFrame:
        """Parse a resultSets response into a DataFrame with lowercase columns."""
        rs = data["resultSets"][result_set_index]
        return pd.DataFrame(rs["rowSet"], columns=[c.lower() for c in rs["headers"]])

    # ------------------------------------------------------------------
    # Team Game Log
    # ------------------------------------------------------------------

    def get_team_game_log(
        self,
        team_id: int,
        season: str,
        season_type: str = "Regular Season",
    ) -> pd.DataFrame:
        """
        One row per completed game for the team.

        Columns (lowercase): team_id, game_id, game_date, matchup, wl,
        w, l, w_pct, min, fgm, fga, fg_pct, fg3m, fg3a, fg3_pct,
        ftm, fta, ft_pct, oreb, dreb, reb, ast, stl, blk, tov, pf,
        pts, plus_minus, video_available
        """
        data = self._get("teamgamelog", {
            "TeamID":     team_id,
            "Season":     season,
            "SeasonType": season_type,
        })
        return self._parse(data)

    # ------------------------------------------------------------------
    # Boxscores
    # ------------------------------------------------------------------

    def get_boxscore_traditional(self, game_id: str) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Returns (player_df, team_df) from boxscoretraditionalv3.

        player_df columns: team_id, player_id, player_name, comment, min,
          fgm, fga, fg_pct, fg3m, fg3a, fg3_pct, ftm, fta, ft_pct, oreb,
          dreb, reb, ast, stl, blk, to, pf, pts, plus_minus
        team_df columns: team_id, pts
        """
        data = self._get("boxscoretraditionalv3", {
            "GameID":      game_id,
            "LeagueID":    "00",
            "startPeriod": 0,
            "endPeriod":   14,
            "startRange":  0,
            "endRange":    28800,
            "rangeType":   0,
        })

        bst = data.get("boxScoreTraditional", {})
        team_rows:   list[dict] = []
        player_rows: list[dict] = []

        for side_key in ("homeTeam", "awayTeam"):
            side = bst.get(side_key, {})
            tid  = side.get("teamId")
            ts   = side.get("statistics", {})
            team_rows.append({
                "team_id": tid,
                "pts":     ts.get("points", 0),
            })
            for player in side.get("players", []):
                ps = player.get("statistics", {})
                player_rows.append({
                    "team_id":    tid,
                    "player_id":  player.get("personId"),
                    "player_name": f"{player.get('firstName', '')} {player.get('familyName', '')}".strip(),
                    "comment":    player.get("comment", ""),
                    "min":        ps.get("minutes", "0:00"),
                    "fgm":        ps.get("fieldGoalsMade", 0),
                    "fga":        ps.get("fieldGoalsAttempted", 0),
                    "fg_pct":     ps.get("fieldGoalsPercentage", 0.0),
                    "fg3m":       ps.get("threePointersMade", 0),
                    "fg3a":       ps.get("threePointersAttempted", 0),
                    "fg3_pct":    ps.get("threePointersPercentage", 0.0),
                    "ftm":        ps.get("freeThrowsMade", 0),
                    "fta":        ps.get("freeThrowsAttempted", 0),
                    "ft_pct":     ps.get("freeThrowsPercentage", 0.0),
                    "oreb":       ps.get("reboundsOffensive", 0),
                    "dreb":       ps.get("reboundsDefensive", 0),
                    "reb":        ps.get("reboundsTotal", 0),
                    "ast":        ps.get("assists", 0),
                    "stl":        ps.get("steals", 0),
                    "blk":        ps.get("blocks", 0),
                    "to":         ps.get("turnovers", 0),
                    "pf":         ps.get("foulsPersonal", 0),
                    "pts":        ps.get("points", 0),
                    "plus_minus": int(ps.get("plusMinusPoints", 0)),
                })

        return pd.DataFrame(player_rows), pd.DataFrame(team_rows)

    def get_boxscore_advanced(self, game_id: str) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Returns (player_df, team_df) parsed from boxscoreadvancedv3.

        player_df columns: team_id, player_id, usg_pct, ts_pct, off_rating,
          def_rating, net_rating, pace
        team_df columns: team_id, off_rating, def_rating, net_rating, pace
        """
        data = self._get("boxscoreadvancedv3", {
            "GameID":      game_id,
            "LeagueID":    "00",
            "startPeriod": 0,
            "endPeriod":   14,
            "startRange":  0,
            "endRange":    28800,
            "rangeType":   0,
        })

        bsa = data.get("boxScoreAdvanced", {})
        team_rows:   list[dict] = []
        player_rows: list[dict] = []

        for side_key in ("homeTeam", "awayTeam"):
            side = bsa.get(side_key, {})
            tid  = side.get("teamId")
            ts   = side.get("statistics", {})
            team_rows.append({
                "team_id":    tid,
                "off_rating": ts.get("offensiveRating", 0.0),
                "def_rating": ts.get("defensiveRating", 0.0),
                "net_rating": ts.get("netRating", 0.0),
                "pace":       ts.get("pace", 0.0),
            })
            for player in side.get("players", []):
                ps = player.get("statistics", {})
                player_rows.append({
                    "team_id":    tid,
                    "player_id":  player.get("personId"),
                    "usg_pct":    ps.get("usagePercentage", 0.0),
                    "ts_pct":     ps.get("trueShootingPercentage", 0.0),
                    "off_rating": ps.get("offensiveRating", 0.0),
                    "def_rating": ps.get("defensiveRating", 0.0),
                    "net_rating": ps.get("netRating", 0.0),
                    "pace":       ps.get("pace", 0.0),
                })

        return pd.DataFrame(player_rows), pd.DataFrame(team_rows)

    # ------------------------------------------------------------------
    # Standings
    # ------------------------------------------------------------------

    def get_standings(self, season: str, season_type: str = "Regular Season") -> pd.DataFrame:
        """
        Live standings from leaguestandingsv3.
        Columns include: team_id, team_city, team_name, conference,
          division, wins, losses, win_pct, games_back, streak, ...
        """
        data = self._get("leaguestandingsv3", {
            "Season":     season,
            "SeasonType": season_type,
            "LeagueID":   "00",
        })
        return self._parse(data)

    # ------------------------------------------------------------------
    # Roster
    # ------------------------------------------------------------------

    def get_roster(self, team_id: int, season: str) -> pd.DataFrame:
        """
        Active roster from commonteamroster.
        Columns: teamid, season, leagueid, player, num, position,
          how_acquired, player_id, ...
        """
        data = self._get("commonteamroster", {
            "TeamID": team_id,
            "Season": season,
        })
        return self._parse(data)

    # ------------------------------------------------------------------
    # League-wide stats (for rankings)
    # ------------------------------------------------------------------

    # The league "dash" endpoints answer 500 unless every filter is present, even when empty
    _DASH_FILTERS: dict[str, Any] = {
        "PlusMinus": "N", "PaceAdjust": "N", "Rank": "N", "Month": 0, "OpponentTeamID": 0,
        "Period": 0, "LastNGames": 0, "PORound": 0, "TeamID": 0, "TwoWay": 0,
        "DateFrom": "", "DateTo": "", "GameSegment": "", "Location": "", "Outcome": "",
        "SeasonSegment": "", "VsConference": "", "VsDivision": "", "Conference": "",
        "Division": "", "GameScope": "", "PlayerExperience": "", "PlayerPosition": "",
        "StarterBench": "", "ShotClockRange": "",
    }

    def get_league_team_stats(
        self, season: str, measure_type: str = "Base", per_mode: str = "PerGame"
    ) -> pd.DataFrame:
        """Season team stats for all 30 teams. measure_type: Base, Advanced, Four Factors, ..."""
        data = self._get("leaguedashteamstats", {
            **self._DASH_FILTERS,
            "Season":      season,
            "SeasonType":  "Regular Season",
            "LeagueID":    "00",
            "MeasureType": measure_type,
            "PerMode":     per_mode,
        })
        return self._parse(data)

    def get_league_player_stats(
        self,
        season: str,
        team_id: int | None = None,
        per_mode: str = "PerGame",
    ) -> pd.DataFrame:
        """Season player stats (optionally filtered to one team)."""
        data = self._get("leaguedashplayerstats", {
            **self._DASH_FILTERS,
            "Season":      season,
            "SeasonType":  "Regular Season",
            "LeagueID":    "00",
            "MeasureType": "Base",
            "PerMode":     per_mode,
            "TeamID":      team_id or 0,
        })
        return self._parse(data)
