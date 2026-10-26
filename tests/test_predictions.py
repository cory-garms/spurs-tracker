"""Unit tests for Matchup & Beatdown Predictor Engine."""

from __future__ import annotations

import pandas as pd
import pytest
from analysis.predictions import predict_matchup, predict_all_opponents


@pytest.fixture
def sample_games():
    return pd.DataFrame([
        {
            "game_id": "0022500001",
            "game_date": "2025-10-25",
            "season": "2025-26",
            "home_away": "H",
            "opponent_id": 1610612745,
            "opponent_abbr": "HOU",
            "result": "W",
            "pts": 118,
            "opp_pts": 105,
            "margin": 13,
            "status": "Final",
        },
        {
            "game_id": "0022500002",
            "game_date": "2025-10-28",
            "season": "2025-26",
            "home_away": "H",
            "opponent_id": 1610612745,
            "opponent_abbr": "HOU",
            "result": "W",
            "pts": 122,
            "opp_pts": 110,
            "margin": 12,
            "status": "Final",
        },
        {
            "game_id": "0022500003",
            "game_date": "2025-11-01",
            "season": "2025-26",
            "home_away": "A",
            "opponent_id": 1610612738,
            "opponent_abbr": "BOS",
            "result": "L",
            "pts": 102,
            "opp_pts": 115,
            "margin": -13,
            "status": "Final",
        },
    ])


def test_predict_matchup_home_advantage(sample_games):
    home_pred = predict_matchup(sample_games, "HOU", is_home=True)
    away_pred = predict_matchup(sample_games, "HOU", is_home=False)

    assert home_pred["projected_margin"] > away_pred["projected_margin"]
    assert home_pred["win_probability_pct"] > away_pred["win_probability_pct"]
    assert home_pred["opponent_abbr"] == "HOU"
    assert "beatdown_tier" in home_pred
    assert 0.0 <= home_pred["win_probability_pct"] <= 100.0


def test_predict_matchup_blowout_probabilities(sample_games):
    pred = predict_matchup(sample_games, "HOU", is_home=True)

    # Monotonicity: P(margin > 0) >= P(margin >= 10) >= P(margin >= 15) >= P(margin >= 20)
    assert pred["win_probability_pct"] >= pred["prob_double_digit_pct"]
    assert pred["prob_double_digit_pct"] >= pred["prob_blowout_pct"]
    assert pred["prob_blowout_pct"] >= pred["prob_demolition_pct"]


def test_predict_all_opponents_sorted(sample_games):
    df = predict_all_opponents(sample_games, is_home=True)
    assert not df.empty
    assert len(df) == 29  # 29 other NBA teams

    # Verify descending sort by projected margin
    margins = df["proj_margin"].tolist()
    assert margins == sorted(margins, reverse=True)
