"""Tests for the Game Score spotlight: Valiente, Compinche, Breakout and Hot Hand."""

from __future__ import annotations

import pandas as pd
import pytest

from analysis.performers import (
    BREAKOUT_MARGIN,
    MIN_BASELINE_GAMES,
    game_performers,
    game_score,
    hot_hand,
    season_game_honors,
    stat_line,
)


def _row(game_n: int, name: str, pts: int, ast: int = 0, reb: int = 0, stl: int = 0, blk: int = 0,
         fgm: int | None = None, fga: int | None = None, minutes: float = 30.0) -> dict:
    fgm = pts // 2 if fgm is None else fgm
    fga = fgm * 2 if fga is None else fga
    return {
        "game_id": f"G{game_n:03d}", "game_date": f"2026-11-{game_n:02d}", "player_name": name,
        "min": minutes, "pts": pts, "reb": reb, "oreb": reb // 4, "dreb": reb - reb // 4,
        "ast": ast, "stl": stl, "blk": blk, "tov": 1, "pf": 2,
        "fgm": fgm, "fga": fga, "ftm": 0, "fta": 0,
    }


def test_game_score_matches_hollinger_formula():
    row = pd.DataFrame([{"pts": 20, "fgm": 8, "fga": 15, "fta": 4, "ftm": 3, "oreb": 2, "dreb": 6,
                         "reb": 8, "stl": 2, "ast": 5, "blk": 1, "pf": 3, "tov": 2}])
    expected = 20 + 0.4 * 8 - 0.7 * 15 - 0.4 * 1 + 0.7 * 2 + 0.3 * 6 + 2 + 0.7 * 5 + 0.7 * 1 - 0.4 * 3 - 2
    assert game_score(row).iloc[0] == pytest.approx(expected)


def test_game_score_falls_back_to_total_rebounds_without_split():
    row = pd.DataFrame([{"pts": 10, "fgm": 4, "fga": 8, "fta": 0, "ftm": 0, "reb": 10,
                         "stl": 0, "ast": 0, "blk": 0, "pf": 0, "tov": 0}])
    assert game_score(row).iloc[0] == pytest.approx(10 + 1.6 - 5.6 + 4.0)


def test_player_of_the_game_follows_production_not_name():
    logs = pd.DataFrame([
        _row(1, "Star Center", pts=25, fgm=9, fga=21, reb=13),
        _row(1, "Point Guard", pts=19, fgm=6, fga=11, ast=9, stl=3),
    ])
    potg = game_performers(logs)["player_of_the_game"]
    assert potg["player_name"] == "Point Guard"


def test_dnps_are_ignored():
    logs = pd.DataFrame([
        _row(1, "Starter", pts=10),
        {**_row(1, "Bench Guy", pts=0), "min": 0.0},
    ])
    honors = game_performers(logs)
    assert honors["player_of_the_game"]["player_name"] == "Starter"
    assert "compinche" not in honors


def test_compinche_is_highest_ranked_teammate_without_needing_a_baseline():
    logs = pd.DataFrame([
        _row(1, "Victor Wembanyama", pts=35, reb=12, blk=4),
        _row(1, "De'Aaron Fox", pts=24, ast=8),
        _row(1, "Stephon Castle", pts=12, ast=5),
        _row(1, "DNP", pts=50, minutes=0),
    ])
    result = game_performers(logs)
    assert result["player_of_the_game"]["player_name"] == "Victor Wembanyama"
    assert result["compinche"]["player_name"] == "De'Aaron Fox"
    assert result["compinche"]["line"] == "24 PTS · 8 AST · 0 REB"


def test_wemby_can_be_the_compinche_when_a_teammate_outplays_him():
    logs = pd.DataFrame([
        _row(1, "Victor Wembanyama", pts=15),
        _row(1, "De'Aaron Fox", pts=30),
    ])
    result = game_performers(logs)
    assert result["player_of_the_game"]["player_name"] == "De'Aaron Fox"
    assert result["compinche"]["player_name"] == "Victor Wembanyama"


def test_honor_ties_are_stable_when_input_order_changes():
    logs = pd.DataFrame([
        _row(1, "Zed", pts=20, minutes=35),
        _row(1, "Ben", pts=20, minutes=30),
        _row(1, "Amy", pts=20, minutes=30),
    ], index=[0, 0, 0])
    for ordered in (logs, logs.iloc[::-1]):
        honors = game_performers(ordered)
        assert honors["player_of_the_game"]["player_name"] == "Zed"
        assert honors["compinche"]["player_name"] == "Amy"


def test_empty_logs_have_no_honorees():
    assert game_performers(pd.DataFrame()) == {}


def test_history_keeps_each_games_honorees_and_completed_games_without_logs():
    games = pd.DataFrame([
        {"game_id": f"G{i:03d}", "game_date": f"2026-11-{i:02d}", "status": status}
        for i, status in ((1, "Final"), (2, "Final"), (3, "Final"), (4, "Scheduled"))
    ])
    logs = pd.DataFrame([
        _row(1, "Victor Wembanyama", pts=30), _row(1, "De'Aaron Fox", pts=20),
        _row(2, "Victor Wembanyama", pts=15), _row(2, "De'Aaron Fox", pts=35),
        _row(4, "Unfinished", pts=50),
    ])
    original = logs.copy(deep=True)
    history = season_game_honors(games.iloc[::-1], logs)
    assert [game["game_id"] for game in history] == ["G003", "G002", "G001"]
    assert "player_of_the_game" not in history[0] and "compinche" not in history[0]
    assert history[1]["player_of_the_game"]["player_name"] == "De'Aaron Fox"
    assert history[1]["compinche"]["player_name"] == "Victor Wembanyama"
    assert history[2]["player_of_the_game"]["player_name"] == "Victor Wembanyama"
    assert history[2]["compinche"]["player_name"] == "De'Aaron Fox"
    pd.testing.assert_frame_equal(logs, original)


def test_history_before_first_game_and_without_box_scores():
    assert season_game_honors(pd.DataFrame(), pd.DataFrame()) == []
    games = pd.DataFrame([{"game_id": "G001", "game_date": "2026-11-01", "status": "Final"}])
    history = season_game_honors(games, pd.DataFrame())
    assert len(history) == 1 and "player_of_the_game" not in history[0]


def test_breakout_needs_a_baseline_and_a_big_jump():
    rows = []
    for g in range(1, MIN_BASELINE_GAMES + 1):
        rows += [_row(g, "Star", pts=25), _row(g, "Role Player", pts=6)]
    g = MIN_BASELINE_GAMES + 1
    rows += [_row(g, "Star", pts=30), _row(g, "Role Player", pts=6 + int(BREAKOUT_MARGIN) + 10)]
    result = game_performers(pd.DataFrame(rows))
    assert result["player_of_the_game"]["player_name"] == "Star"
    assert result["breakout"]["player_name"] == "Role Player"
    assert result["breakout"]["above_avg"] >= BREAKOUT_MARGIN


def test_no_breakout_before_baseline_exists():
    logs = pd.DataFrame([_row(1, "Star", pts=30), _row(1, "Role Player", pts=25)])
    assert "breakout" not in game_performers(logs)


def test_hot_hand_uses_recent_window():
    rows = [_row(g, "Early Hot", pts=30 if g <= 3 else 5) for g in range(1, 9)]
    rows += [_row(g, "Late Hot", pts=5 if g <= 3 else 25) for g in range(1, 9)]
    assert hot_hand(pd.DataFrame(rows), last_n=5)["player_name"] == "Late Hot"


def test_stat_line_leads_with_points_then_notable_stats():
    row = pd.Series({"pts": 19, "reb": 3, "ast": 9, "stl": 3, "blk": 1})
    assert stat_line(row) == "19 PTS · 9 AST · 3 STL"
