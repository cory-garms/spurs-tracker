"""
Roster management.

Fetches the active roster from the NBA Stats API commonteamroster endpoint,
enriches it with position group labels, and caches as a parquet file.

Position groups
---------------
  G  — guards (PG, SG, G)
  F  — forwards (SF, PF, F, G-F, F-G)
  C  — centers (C, F-C, C-F)
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from client.nba_client import NBAClient
from data.schema import ROSTER_SCHEMA, enforce_schema
from config import CACHE_DIR, season_str

log = logging.getLogger(__name__)

# Position → group mapping
_POSITION_GROUP: dict[str, str] = {
    "G":   "G", "PG":  "G", "SG":  "G",
    "F":   "F", "SF":  "F", "PF":  "F",
    "G-F": "F", "F-G": "F",
    "C":   "C", "F-C": "C", "C-F": "C",
}


def _cache_path(team_id: int, season: int) -> Path:
    return CACHE_DIR / f"roster_{team_id}_{season}.parquet"


def fetch_roster(
    team_id: int,
    season: int,
    client: NBAClient | None = None,
    force_refresh: bool = False,
) -> pd.DataFrame:
    """
    Return the roster as a DataFrame matching ROSTER_SCHEMA.
    Results are cached; pass force_refresh=True to re-fetch from the API.
    """
    cache = _cache_path(team_id, season)
    if cache.exists() and not force_refresh:
        log.info("Loading roster from cache: %s", cache)
        return pd.read_parquet(cache)

    client = client or NBAClient()
    sstr   = season_str(season)
    log.info("Fetching roster for team %d season %s", team_id, sstr)

    raw = client.get_roster(team_id, sstr)

    rows: list[dict] = []
    for _, row in raw.iterrows():
        pos       = str(row.get("position", "") or "")
        pos_group = _POSITION_GROUP.get(pos, "F")
        rows.append({
            "player_id":           row.get("player_id") or row.get("playerid"),
            "player_name":         row.get("player") or row.get("playername", ""),
            "jersey_number":       str(row.get("num", "") or ""),
            "position":            pos,
            "position_group":      pos_group,
            "years_of_experience": _safe_int(row.get("exp")),
        })

    df = pd.DataFrame(rows)
    df = enforce_schema(df, ROSTER_SCHEMA)
    df.to_parquet(cache, index=False)
    log.info("Cached roster (%d players) → %s", len(df), cache)
    return df


def get_position_group(df_roster: pd.DataFrame, group: str) -> pd.DataFrame:
    """Filter roster to a position group: 'G', 'F', or 'C'."""
    return df_roster[df_roster["position_group"] == group].copy()


def player_id_map(df_roster: pd.DataFrame) -> dict[int, str]:
    """Return {player_id: player_name} dict for quick lookups."""
    return dict(zip(df_roster["player_id"], df_roster["player_name"]))


def _safe_int(val, default: int = 0) -> int:
    try:
        v = str(val).strip()
        if v in ("", "R", "None", "nan"):
            return default
        return int(v)
    except (TypeError, ValueError):
        return default
