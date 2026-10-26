"""Unit tests for Rodeo Road Trip split tracker."""

from __future__ import annotations

import pandas as pd
import pytest
from analysis.rodeo import (
    segment_rodeo_games,
    rodeo_split_metrics,
    historical_rodeo_comparison,
    HISTORICAL_RODEO_BENCHMARKS,
)


@pytest.fixture
def sample_games():
    return pd.DataFrame([
        {
            "game_id": "0022500001",
            "game_date": "2025-11-15",
            "home_away": "H",
            "result": "W",
            "pts": 115,
            "opp_pts": 105,
            "margin": 10,
            "ortg": 114.0,
            "drtg": 104.0,
            "nrtg": 10.0,
            "pace": 99.0,
            "status": "Final",
        },
        {
            "game_id": "0022500002",
            "game_date": "2026-02-05",
            "home_away": "A",
            "result": "W",
            "pts": 108,
            "opp_pts": 102,
            "margin": 6,
            "ortg": 109.0,
            "drtg": 103.0,
            "nrtg": 6.0,
            "pace": 98.0,
            "status": "Final",
        },
        {
            "game_id": "0022500003",
            "game_date": "2026-02-08",
            "home_away": "A",
            "result": "L",
            "pts": 100,
            "opp_pts": 106,
            "margin": -6,
            "ortg": 102.0,
            "drtg": 108.0,
            "nrtg": -6.0,
            "pace": 97.0,
            "status": "Final",
        },
        {
            "game_id": "0022500004",
            "game_date": "2026-03-10",
            "home_away": "H",
            "result": "W",
            "pts": 120,
            "opp_pts": 110,
            "margin": 10,
            "ortg": 118.0,
            "drtg": 108.0,
            "nrtg": 10.0,
            "pace": 101.0,
            "status": "Final",
        },
    ])


def test_segment_rodeo_games(sample_games):
    segmented = segment_rodeo_games(sample_games)
    splits = segmented["rodeo_split"].tolist()
    assert splits[0] == "Pre-RRT"
    assert splits[1] == "Active RRT"
    assert splits[2] == "Active RRT"
    assert splits[3] == "Post-RRT"


def test_rodeo_split_metrics(sample_games):
    segmented = segment_rodeo_games(sample_games)
    metrics = rodeo_split_metrics(segmented)

    assert "Pre-RRT" in metrics
    assert "Active RRT" in metrics
    assert "Post-RRT" in metrics

    rrt = metrics["Active RRT"]
    assert rrt["games"] == 2
    assert rrt["record"] == "1-1"
    assert rrt["win_pct"] == 0.500
    assert rrt["avg_margin"] == 0.0


def test_historical_rodeo_comparison():
    current_metrics = {"games": 2, "record": "1-1", "win_pct": 0.500, "avg_margin": 0.0, "net_rtg": 0.0}
    comp = historical_rodeo_comparison(current_metrics)
    assert len(comp) == len(HISTORICAL_RODEO_BENCHMARKS) + 1
    assert comp.iloc[-1]["season"] == "Current Season"
    assert comp.iloc[-1]["record"] == "1-1"
