"""Unit tests for Beautiful Game passing & ball movement analytical engine."""

from __future__ import annotations

import pandas as pd
import pytest
from analysis.beautiful_game import (
    team_ball_movement_summary,
    player_pass_contributors,
)


@pytest.fixture
def sample_data():
    player_logs = pd.DataFrame([
        {
            "game_id": "0022500001",
            "player_id": 1,
            "player_name": "Chris Paul",
            "min": 26.0,
            "pts": 10,
            "ast": 9,
            "tov": 2,
            "fgm": 3,
            "fg3m": 2,
        },
        {
            "game_id": "0022500001",
            "player_id": 2,
            "player_name": "Victor Wembanyama",
            "min": 32.0,
            "pts": 28,
            "ast": 4,
            "tov": 3,
            "fgm": 10,
            "fg3m": 3,
        },
        {
            "game_id": "0022500001",
            "player_id": 3,
            "player_name": "Devin Vassell",
            "min": 30.0,
            "pts": 20,
            "ast": 5,
            "tov": 1,
            "fgm": 7,
            "fg3m": 3,
        },
    ])
    games = pd.DataFrame([
        {
            "game_id": "0022500001",
            "pts": 118,
            "opp_pts": 105,
            "ast": 28,
            "tov": 12,
            "fgm": 42,
            "fg3m": 14,
            "status": "Final",
        }
    ])
    return games, player_logs


def test_team_ball_movement_summary(sample_data):
    games, player_logs = sample_data
    summary = team_ball_movement_summary(games, player_logs)

    assert summary["games"] == 1
    assert summary["assists_per_game"] == 18.0
    assert summary["turnovers_per_game"] == 6.0
    assert summary["ast_tov_ratio"] == 3.0
    assert summary["beautiful_game_index"] > 60.0


def test_player_pass_contributors(sample_data):
    games, player_logs = sample_data
    # Use min_games=1 to test with single-game fixture
    contributors = player_pass_contributors(player_logs, min_games=1)

    assert len(contributors) == 3
    assert contributors.iloc[0]["player_name"] == "Chris Paul"
    assert contributors.iloc[0]["ast_pg"] == 9.0
    assert contributors.iloc[0]["ast_tov"] == 4.5
