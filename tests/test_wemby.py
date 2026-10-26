"""Unit tests for Victor Wembanyama Defensive & Gravity Lab."""

from __future__ import annotations

import pandas as pd
import pytest
from analysis.wemby import (
    get_wemby_logs,
    stocks_distribution,
    defensive_impact_summary,
    offensive_gravity_summary,
    WEMBY_ID,
)


@pytest.fixture
def sample_player_logs():
    return pd.DataFrame([
        {
            "game_id": "0022500001",
            "game_date": "2025-10-25",
            "player_id": WEMBY_ID,
            "player_name": "Victor Wembanyama",
            "min": 32.0,
            "pts": 28,
            "reb": 12,
            "ast": 4,
            "stl": 2,
            "blk": 5,
            "tov": 3,
            "fga": 18,
            "fgm": 10,
            "fg3a": 7,
            "fg3m": 3,
            "fta": 6,
            "ftm": 5,
            "plus_minus": 14,
            "ts_pct": 0.679,
            "usg_pct": 0.32,
        },
        {
            "game_id": "0022500002",
            "game_date": "2025-10-28",
            "player_id": WEMBY_ID,
            "player_name": "Victor Wembanyama",
            "min": 30.0,
            "pts": 22,
            "reb": 10,
            "ast": 5,
            "stl": 5,
            "blk": 5,
            "tov": 2,
            "fga": 16,
            "fgm": 8,
            "fg3a": 5,
            "fg3m": 2,
            "fta": 4,
            "ftm": 4,
            "plus_minus": 8,
            "ts_pct": 0.619,
            "usg_pct": 0.29,
        },
        {
            "game_id": "0022500001",
            "game_date": "2025-10-25",
            "player_id": 1641706,
            "player_name": "Stephon Castle",
            "min": 28.0,
            "pts": 14,
            "reb": 4,
            "ast": 6,
            "stl": 1,
            "blk": 0,
            "tov": 2,
            "fga": 11,
            "fgm": 5,
            "fg3a": 3,
            "fg3m": 1,
            "fta": 4,
            "ftm": 3,
            "plus_minus": 4,
            "ts_pct": 0.548,
            "usg_pct": 0.22,
        },
    ])


@pytest.fixture
def sample_games():
    return pd.DataFrame([
        {
            "game_id": "0022500001",
            "game_date": "2025-10-25",
            "result": "W",
            "pts": 118,
            "opp_pts": 105,
            "margin": 13,
            "drtg": 104.2,
            "ortg": 117.1,
            "status": "Final",
        },
        {
            "game_id": "0022500002",
            "game_date": "2025-10-28",
            "result": "W",
            "pts": 112,
            "opp_pts": 102,
            "margin": 10,
            "drtg": 101.5,
            "ortg": 111.4,
            "status": "Final",
        },
    ])


def test_get_wemby_logs(sample_player_logs):
    wemby = get_wemby_logs(sample_player_logs)
    assert len(wemby) == 2
    assert "stocks" in wemby.columns
    assert wemby["stocks"].tolist() == [7, 10]
    assert "efg_pct" in wemby.columns
    assert "computed_ts_pct" in wemby.columns


def test_stocks_distribution(sample_player_logs):
    wemby = get_wemby_logs(sample_player_logs)
    dist = stocks_distribution(wemby)
    assert dist["games"] == 2
    assert dist["total_blocks"] == 10
    assert dist["total_steals"] == 7
    assert dist["total_stocks"] == 17
    assert dist["games_5plus_blk"] == 2
    assert dist["games_5plus_stocks"] == 2
    assert dist["five_by_fives"] == 1  # 2nd game had 22 pts, 10 reb, 5 ast, 5 stl, 5 blk!


def test_defensive_impact_summary(sample_games, sample_player_logs):
    wemby = get_wemby_logs(sample_player_logs)
    impact = defensive_impact_summary(sample_games, wemby)
    assert impact["total_tracked_games"] == 2
    assert impact["high_stocks_games"] == 2
    assert impact["high_stocks_record"] == "2-0 (1.000)"


def test_offensive_gravity_summary(sample_player_logs):
    wemby = get_wemby_logs(sample_player_logs)
    off = offensive_gravity_summary(wemby)
    assert off["ppg"] == 25.0
    assert off["fga_per_game"] == 17.0
    assert off["fg3a_per_game"] == 6.0
    assert off["three_point_attempt_rate"] > 0.3
