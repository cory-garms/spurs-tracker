"""Unit tests for Session 2 analytical modeling engines."""

from __future__ import annotations

import pandas as pd
import pytest

from analysis.four_factors import (
    game_four_factors,
    team_four_factors_summary,
    four_factors_diagnostic_table,
)
from analysis.lineups import (
    two_man_pairings,
    key_spurs_synergies,
    starter_bench_deep_split,
)
from analysis.clutch import (
    clutch_game_summary,
    clutch_player_leaders,
)
from analysis.predictions import predict_matchup


@pytest.fixture
def mock_session2_data():
    games = pd.DataFrame([
        {
            "game_id": "001",
            "game_date": "2025-10-25",
            "home_away": "H",
            "opponent_abbr": "HOU",
            "result": "W",
            "pts": 115,
            "opp_pts": 112,
            "margin": 3,
            "status": "Final",
            "ortg": 114.5,
            "drtg": 111.5,
            "pace": 100.0,
        },
        {
            "game_id": "002",
            "game_date": "2025-10-28",
            "home_away": "H",
            "opponent_abbr": "DAL",
            "result": "L",
            "pts": 108,
            "opp_pts": 112,
            "margin": -4,
            "status": "Final",
            "ortg": 107.0,
            "drtg": 111.0,
            "pace": 101.0,
        },
        {
            "game_id": "003",
            "game_date": "2025-10-31",
            "home_away": "A",
            "opponent_abbr": "MEM",
            "result": "W",
            "pts": 125,
            "opp_pts": 105,
            "margin": 20,
            "status": "Final",
            "ortg": 124.0,
            "drtg": 104.0,
            "pace": 100.5,
        },
    ])

    player_logs = pd.DataFrame([
        # Game 001 (Clutch Win by 3)
        {"game_id": "001", "game_date": "2025-10-25", "player_id": 1, "player_name": "Chris Paul", "min": 32.0, "pts": 16, "reb": 4, "ast": 10, "plus_minus": 6, "tov": 1, "fgm": 6, "fga": 12, "fg3m": 2, "fg3a": 5, "ftm": 2, "fta": 2, "oreb": 0, "dreb": 4, "ts_pct": 0.621},
        {"game_id": "001", "game_date": "2025-10-25", "player_id": 2, "player_name": "Victor Wembanyama", "min": 34.0, "pts": 28, "reb": 14, "ast": 4, "plus_minus": 8, "tov": 3, "fgm": 10, "fga": 18, "fg3m": 3, "fg3a": 7, "ftm": 5, "fta": 6, "oreb": 3, "dreb": 11, "ts_pct": 0.679},
        {"game_id": "001", "game_date": "2025-10-25", "player_id": 3, "player_name": "Stephon Castle", "min": 28.0, "pts": 14, "reb": 5, "ast": 5, "plus_minus": 4, "tov": 2, "fgm": 5, "fga": 10, "fg3m": 1, "fg3a": 3, "ftm": 3, "fta": 4, "oreb": 1, "dreb": 4, "ts_pct": 0.595},
        {"game_id": "001", "game_date": "2025-10-25", "player_id": 4, "player_name": "Devin Vassell", "min": 30.0, "pts": 20, "reb": 4, "ast": 3, "plus_minus": 2, "tov": 1, "fgm": 8, "fga": 16, "fg3m": 3, "fg3a": 8, "ftm": 1, "fta": 2, "oreb": 0, "dreb": 4, "ts_pct": 0.592},
        {"game_id": "001", "game_date": "2025-10-25", "player_id": 5, "player_name": "Jeremy Sochan", "min": 26.0, "pts": 12, "reb": 7, "ast": 3, "plus_minus": 3, "tov": 1, "fgm": 5, "fga": 9, "fg3m": 0, "fg3a": 1, "ftm": 2, "fta": 3, "oreb": 2, "dreb": 5, "ts_pct": 0.581},
        {"game_id": "001", "game_date": "2025-10-25", "player_id": 6, "player_name": "Keldon Johnson", "min": 20.0, "pts": 15, "reb": 5, "ast": 2, "plus_minus": -4, "tov": 1, "fgm": 6, "fga": 11, "fg3m": 2, "fg3a": 5, "ftm": 1, "fta": 2, "oreb": 1, "dreb": 4, "ts_pct": 0.631},
        {"game_id": "001", "game_date": "2025-10-25", "player_id": 7, "player_name": "Harrison Barnes", "min": 22.0, "pts": 10, "reb": 3, "ast": 1, "plus_minus": -4, "tov": 0, "fgm": 4, "fga": 8, "fg3m": 2, "fg3a": 4, "ftm": 0, "fta": 0, "oreb": 0, "dreb": 3, "ts_pct": 0.625},

        # Game 002 (Clutch Loss by 4)
        {"game_id": "002", "game_date": "2025-10-28", "player_id": 1, "player_name": "Chris Paul", "min": 30.0, "pts": 12, "reb": 3, "ast": 8, "plus_minus": -2, "tov": 2, "fgm": 4, "fga": 10, "fg3m": 2, "fg3a": 4, "ftm": 2, "fta": 2, "oreb": 0, "dreb": 3, "ts_pct": 0.551},
        {"game_id": "002", "game_date": "2025-10-28", "player_id": 2, "player_name": "Victor Wembanyama", "min": 33.0, "pts": 24, "reb": 12, "ast": 3, "plus_minus": -1, "tov": 4, "fgm": 9, "fga": 19, "fg3m": 2, "fg3a": 6, "ftm": 4, "fta": 5, "oreb": 2, "dreb": 10, "ts_pct": 0.566},
        {"game_id": "002", "game_date": "2025-10-28", "player_id": 3, "player_name": "Stephon Castle", "min": 26.0, "pts": 11, "reb": 4, "ast": 4, "plus_minus": -3, "tov": 2, "fgm": 4, "fga": 9, "fg3m": 1, "fg3a": 3, "ftm": 2, "fta": 2, "oreb": 1, "dreb": 3, "ts_pct": 0.556},
        {"game_id": "002", "game_date": "2025-10-28", "player_id": 4, "player_name": "Devin Vassell", "min": 31.0, "pts": 18, "reb": 4, "ast": 2, "plus_minus": -2, "tov": 2, "fgm": 7, "fga": 15, "fg3m": 3, "fg3a": 7, "ftm": 1, "fta": 2, "oreb": 0, "dreb": 4, "ts_pct": 0.567},
        {"game_id": "002", "game_date": "2025-10-28", "player_id": 5, "player_name": "Jeremy Sochan", "min": 28.0, "pts": 14, "reb": 6, "ast": 2, "plus_minus": -2, "tov": 1, "fgm": 6, "fga": 10, "fg3m": 0, "fg3a": 1, "ftm": 2, "fta": 2, "oreb": 2, "dreb": 4, "ts_pct": 0.643},
        {"game_id": "002", "game_date": "2025-10-28", "player_id": 6, "player_name": "Keldon Johnson", "min": 22.0, "pts": 16, "reb": 6, "ast": 1, "plus_minus": -6, "tov": 2, "fgm": 6, "fga": 12, "fg3m": 2, "fg3a": 5, "ftm": 2, "fta": 3, "oreb": 1, "dreb": 5, "ts_pct": 0.601},
        {"game_id": "002", "game_date": "2025-10-28", "player_id": 7, "player_name": "Harrison Barnes", "min": 24.0, "pts": 13, "reb": 4, "ast": 2, "plus_minus": -4, "tov": 1, "fgm": 5, "fga": 9, "fg3m": 2, "fg3a": 4, "ftm": 1, "fta": 2, "oreb": 0, "dreb": 4, "ts_pct": 0.658},
    ])
    return games, player_logs


def test_four_factors_calculations(mock_session2_data):
    games, player_logs = mock_session2_data
    g_ff = game_four_factors(player_logs)
    assert len(g_ff) == 2
    assert "efg_pct" in g_ff.columns
    assert "tov_pct" in g_ff.columns
    assert "oreb_pct" in g_ff.columns
    assert "ftr" in g_ff.columns

    summary = team_four_factors_summary(player_logs, games)
    assert summary["games_analyzed"] == 2
    assert 0.40 <= summary["efg_pct"] <= 0.70
    assert 0.05 <= summary["tov_pct"] <= 0.25

    table = four_factors_diagnostic_table(player_logs, games)
    assert len(table) == 4
    assert "grade" in table.columns


def test_lineups_and_synergies(mock_session2_data):
    games, player_logs = mock_session2_data
    pairs = two_man_pairings(player_logs, min_games=1)
    assert not pairs.empty
    assert "net_pm_pg" in pairs.columns

    synergies = key_spurs_synergies(player_logs)
    assert not synergies.empty

    split = starter_bench_deep_split(player_logs)
    assert len(split["starter_names"]) == 5
    assert len(split["bench_names"]) >= 1
    assert split["starter_avg_pts"] > 0
    assert split["bench_scoring_share_pct"] > 0


def test_clutch_playbook_engine(mock_session2_data):
    games, player_logs = mock_session2_data
    summary = clutch_game_summary(games)
    # Games 001 (+3) and 002 (-4) are both clutch games
    assert summary["clutch_games_played"] == 2
    assert summary["clutch_record"] == "1-1"
    assert summary["clutch_win_pct"] == 50.0
    assert "composure_index" in summary

    leaders = clutch_player_leaders(games, player_logs, min_clutch_games=1)
    assert not leaders.empty
    assert leaders.iloc[0]["clutch_pts_pg"] > 0


def test_calibrated_predictions_with_rest_fatigue(mock_session2_data):
    games, _ = mock_session2_data

    # Rested Spurs vs Back-to-Back Opponent
    fresh_pred = predict_matchup(games, "HOU", is_home=True, spurs_rest_days=2, opp_rest_days=0)

    # Back-to-Back Spurs vs Rested Opponent
    tired_pred = predict_matchup(games, "HOU", is_home=True, spurs_rest_days=0, opp_rest_days=2)

    # Fresh legs must have higher projected margin and win probability
    assert fresh_pred["projected_margin"] > tired_pred["projected_margin"]
    assert fresh_pred["win_probability_pct"] > tired_pred["win_probability_pct"]
    assert fresh_pred["prob_blowout_pct"] >= tired_pred["prob_blowout_pct"]
