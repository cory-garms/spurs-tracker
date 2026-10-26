"""Tests for the Game Score spotlight: Player of the Game, Breakout and Hot Hand."""

from __future__ import annotations

import pandas as pd
import pytest

from analysis.performers import (
    BREAKOUT_MARGIN,
    MIN_BASELINE_GAMES,
    game_performers,
    game_score,
    hot_hand,
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
    assert game_performers(logs)["player_of_the_game"]["player_name"] == "Starter"


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
