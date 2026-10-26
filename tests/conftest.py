"""Shared fixtures and helpers for the spurs_tracker test suite."""

from __future__ import annotations

import sys
from pathlib import Path
import pandas as pd
import pytest

# Ensure repo root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SAS_ID = 1610612759
GSW_ID = 1610612744


def nba_game(
    game_id: str,
    game_date: str,
    pts: int,
    opp_pts: int,
    *,
    is_home: bool = True,
    opp_id: int = GSW_ID,
    opp_abbr: str = "GSW",
) -> dict:
    """One row of the cached games table, with standard NBA fields."""
    wl = "W" if pts > opp_pts else "L"
    return {
        "game_id": game_id,
        "game_date": game_date,
        "season": 2025,
        "team_id": SAS_ID,
        "team_abbr": "SAS",
        "opp_id": opp_id,
        "opp_abbr": opp_abbr,
        "is_home": is_home,
        "matchup": "SAS vs. " + opp_abbr if is_home else "SAS @ " + opp_abbr,
        "wl": wl,
        "pts": pts,
        "opp_pts": opp_pts,
        "margin": pts - opp_pts,
        "fgm": 42,
        "fga": 90,
        "fg_pct": 0.467,
        "fg3m": 14,
        "fg3a": 38,
        "fg3_pct": 0.368,
        "ftm": 18,
        "fta": 24,
        "ft_pct": 0.750,
        "oreb": 10,
        "dreb": 34,
        "reb": 44,
        "ast": 28,
        "stl": 7,
        "blk": 8,
        "tov": 12,
        "pf": 18,
    }


def games_df(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


@pytest.fixture
def sas_team_id() -> int:
    return SAS_ID
