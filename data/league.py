"""
League-Wide Context Fetcher & Cache Orchestrator.

Fetches and caches season standings and advanced ratings (OffRtg, DefRtg, NetRtg, Pace)
for all 30 NBA teams into data/cache/league_standings_{season}.parquet.

Used by:
  - Matchup & Beatdown Predictor (analysis/predictions.py)
  - Standings & Conference Rankings (analysis/standings.py)
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
}


def _cache_path(season: int) -> Path:
    return CACHE_DIR / f"league_standings_{season}.parquet"


def fetch_league_standings(
    season: int = config.SEASON,
    client: NBAClient | None = None,
    force_refresh: bool = False,
) -> pd.DataFrame:
    """
    Fetch and cache league-wide standings and ratings for all 30 teams.
    Returns DataFrame matching LEAGUE_STANDINGS_SCHEMA.
    """
    cache_file = _cache_path(season)
    if not force_refresh and cache_file.exists():
        log.info("Loading league standings from cache: %s", cache_file)
        return pd.read_parquet(cache_file)

    client = client or NBAClient()
    season_s = season_str(season)
    log.info("Fetching league standings for %s...", season_s)

    try:
        raw_standings = client.get_standings(season_s, season_type="Regular Season")
    except Exception as e:
        log.warning("Could not fetch live standings from API (%s). Building baseline from TEAMS registry.", e)
        raw_standings = pd.DataFrame()

    records = []
    # Reverse lookup for abbr by ID
    id_to_abbr = {v["id"]: k for k, v in TEAMS.items()}

    if not raw_standings.empty:
        # Standardize columns from leaguestandingsv3
        for _, row in raw_standings.iterrows():
            tid = int(row.get("teamid", 0))
            abbr = id_to_abbr.get(tid, str(row.get("teamcity", "")[:3]).upper())
            tinfo = TEAMS.get(abbr, {})

            w = int(row.get("w", 0))
            l = int(row.get("l", 0))
            g = w + l
            pts = float(row.get("pointsfor", 0.0))
            opp_pts = float(row.get("pointsagainst", 0.0))
            pts_pg = round(pts / g, 1) if g > 0 else 112.0
            opp_pts_pg = round(opp_pts / g, 1) if g > 0 else 112.0

            records.append({
                "team_id": tid,
                "team_abbr": abbr,
                "team_name": tinfo.get("name", str(row.get("teamname", abbr))),
                "conference": tinfo.get("conf", str(row.get("conferencename", "West"))),
                "division": tinfo.get("div", "NBA"),
                "wins": w,
                "losses": l,
                "win_pct": round(w / g, 3) if g > 0 else 0.500,
                "pts_pg": pts_pg,
                "opp_pts_pg": opp_pts_pg,
                "margin": round(pts_pg - opp_pts_pg, 2),
                "ortg": round(float(row.get("offensive_rating", pts_pg)), 1),
                "drtg": round(float(row.get("defensive_rating", opp_pts_pg)), 1),
                "nrtg": round(float(row.get("net_rating", pts_pg - opp_pts_pg)), 2),
                "pace": round(float(row.get("pace", 99.5)), 1),
            })
    else:
        # Baseline fallback with realistic baseline ratings for all 30 teams
        for abbr, info in TEAMS.items():
            records.append({
                "team_id": info["id"],
                "team_abbr": abbr,
                "team_name": info["name"],
                "conference": info["conf"],
                "division": info["div"],
                "wins": 0,
                "losses": 0,
                "win_pct": 0.500,
                "pts_pg": 112.5,
                "opp_pts_pg": 112.5,
                "margin": 0.0,
                "ortg": 112.5,
                "drtg": 112.5,
                "nrtg": 0.0,
                "pace": 99.5,
            })

    df = pd.DataFrame(records)
    # Cast types
    for col, dtype in LEAGUE_STANDINGS_SCHEMA.items():
        if col in df.columns:
            df[col] = df[col].astype(dtype)

    cache_file.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(cache_file, index=False)
    log.info("Cached %d teams in league standings → %s", len(df), cache_file)
    return df


def load_league_standings(season: int = config.SEASON) -> pd.DataFrame:
    """Load cached league standings."""
    cache_file = _cache_path(season)
    if not cache_file.exists():
        return fetch_league_standings(season=season, force_refresh=False)
    return pd.read_parquet(cache_file)
