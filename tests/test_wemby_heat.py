"""Tests for the Wemby Lab Heat Check: pooled shooting, recent form, minutes tax and best stretches."""

from __future__ import annotations

import pandas as pd
import pytest

from analysis.wemby import (
    best_stretches, get_wemby_logs, heat_check, offensive_gravity_summary, pooled_shooting, rolling_form,
)


def _logs(points, minutes=None, fga=None, season="2026-27", start="2026-10-20", fta=0):
    """One Wembanyama row per game; only points vary unless told otherwise."""
    n = len(points)
    minutes = minutes or [30.0] * n
    fga = fga or [20] * n
    dates = pd.date_range(start, periods=n, freq="2D")
    return pd.DataFrame({
        "game_id": [f"{season}-{i}" for i in range(n)], "game_date": dates, "season": season,
        "player_id": 1641705, "player_name": "Victor Wembanyama",
        "min": minutes, "pts": points, "reb": 10, "ast": 3, "stl": 1, "blk": 3, "tov": 2, "pf": 2,
        "fgm": [f // 2 for f in fga], "fga": fga, "fg3m": 1, "fg3a": 4, "ftm": fta, "fta": fta,
    })


def _games(logs, margins):
    return pd.DataFrame({"game_id": logs["game_id"], "margin": margins,
                         "opponent_abbr": "OPP", "home_away": "H"})


def test_pooled_shooting_weights_by_shots():
    logs = _logs([12, 20], fga=[20, 10])
    # per-game TS is 0.30 and 1.00 (mean 0.65); pooled is 32 / (2 * 30)
    assert pooled_shooting(logs)["ts_pct"] == pytest.approx(32 / 60)
    assert offensive_gravity_summary(get_wemby_logs(logs))["true_shooting_pct"] == pytest.approx(0.533, abs=0.001)


def test_heat_check_compares_last_window_and_projects_at_close_game_minutes():
    logs = _logs([20, 22, 24, 30, 40, 35, 30, 45],
                 minutes=[34, 36, 35, 30, 25, 24, 26, 25])
    games = _games(logs, [5, -8, 10, 3, 25, 20, 18, 30])        # games 0-3 are within 10
    prev = _logs([25] * 12, minutes=[32] * 12, season="2025-26", start="2025-10-20")
    h = heat_check(get_wemby_logs(logs), games, prev)

    assert h["last"]["games"] == 5 and h["last"]["pts"] == pytest.approx(36.0)
    assert h["before"]["games"] == 3 and h["before"]["pts"] == pytest.approx(22.0)
    assert h["prev"]["games"] == 12 and h["prev_season"] == "2025-26"
    assert h["last_margins"] == [3, 25, 20, 18, 30]
    assert h["target_minutes"] == pytest.approx((34 + 36 + 35 + 30) / 4)
    assert "4 games decided by 10 or fewer" in h["target_basis"]
    last_min = 30 + 25 + 24 + 26 + 25
    assert h["projected"]["pts"] == pytest.approx(180 / last_min * h["target_minutes"])


def test_heat_check_falls_back_to_last_season_minutes():
    logs = _logs([30] * 6, minutes=[28] * 6)
    games = _games(logs, [20] * 6)                                # no competitive games
    prev = _logs([25] * 10, minutes=[31] * 10, season="2025-26", start="2025-10-20")
    h = heat_check(get_wemby_logs(logs), games, prev)
    assert h["target_minutes"] == pytest.approx(31.0) and h["target_basis"] == "his average last season"
    assert h["before"] == {}                                      # one earlier game is too few to compare


def test_heat_check_needs_a_full_window():
    logs = _logs([30] * 4)
    assert heat_check(get_wemby_logs(logs), _games(logs, [5] * 4), pd.DataFrame()) == {}


def test_rolling_form_pools_shots_inside_window():
    logs = _logs([10, 20, 30], fga=[10, 10, 20])
    form = rolling_form(get_wemby_logs(logs), _games(logs, [1, 2, 3]), window=2, min_periods=2)
    assert pd.isna(form["roll_ts_pct"].iloc[0])
    assert form["roll_ts_pct"].iloc[2] == pytest.approx(50 / (2 * 30))
    assert form["roll_pts_per_36"].iloc[2] == pytest.approx(50 / 60 * 36)


def test_best_stretches_ranks_and_collapses_overlaps():
    prev = _logs([20, 20, 20, 20, 20, 41, 41, 41, 41, 41, 20, 20], season="2025-26", start="2025-10-20")
    # This season: a hot run at the end whose best window is one game earlier than the current one
    cur = _logs([20, 20, 20, 40, 44, 44, 44, 44, 40], season="2026-27")
    res = best_stretches({"2025-26": prev, "2026-27": cur}, "2026-27", window=5, top=3)

    # Windows: 8 last season + 5 this season = 13. Current (games 4-8) averages 43.2; games 3-7 also 43.2
    assert res["total"] == 13
    assert res["seasons"] == ["2025-26", "2026-27"]
    assert res["current_rank"] == 1                               # ties the overlapping window above it
    assert res["better_outside_run"] == 0
    rows = res["rows"]
    assert len(rows) == 3
    assert rows[0]["season"] == "2026-27" and rows[0]["current_run"] is True
    assert rows[1]["season"] == "2025-26" and rows[1]["pts"] == pytest.approx(41.0)
    # No two listed stretches from the same season overlap
    same = [r for r in rows if r["season"] == "2025-26"]
    assert all(a["last_idx"] < b["first"] or b["last_idx"] < a["first"] for a in same for b in same if a is not b)


def test_best_stretches_appends_current_run_when_outside_top():
    prev = _logs([40] * 12, season="2025-26", start="2025-10-20")
    cur = _logs([10] * 6, season="2026-27")
    res = best_stretches({"2025-26": prev, "2026-27": cur}, "2026-27", window=5, top=2)
    assert [r["current_run"] for r in res["rows"]] == [False, False, True]
    # 8 last-season stretches beat it; this season's two windows tie and share rank 9
    assert res["current_rank"] == 9 and res["rows"][-1]["rank"] == 9
    assert res["better_outside_run"] == 8
