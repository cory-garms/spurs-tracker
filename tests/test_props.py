"""Tests for the prop board analytics: lines, hit-rate ranges, matchup factors and rest."""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import pytest

from analysis.matchup_preview import SHRINK_GAMES
from analysis.props import (
    MIN_PREV_GAMES, balanced_line, half_point_line, lean, matchup_factors, prop_rows, rest_days,
    wilson_interval,
)
from data.schedule import LOCAL_TZ


def test_half_point_line_rounds_down_to_half():
    assert half_point_line(17.0) == 17.5
    assert half_point_line(17.9) == 17.5


def _s(*vals):
    return pd.Series(vals, dtype=float)


def test_balanced_line_picks_side_closest_to_even_split():
    assert balanced_line(_s(4, 4, 4, 4, 6)) == 4.5        # over 3.5: 5/5, over 4.5: 1/5 -> higher is closer
    assert balanced_line(_s(10, 12, 18, 18, 18, 25)) == 17.5   # over 17.5: 4/6, over 18.5: 1/6 -> lower is closer


def test_balanced_line_ties_go_to_higher_line():
    assert balanced_line(_s(2, 3, 4, 5, 6)) == 4.5        # 3/5 vs 2/5
    assert balanced_line(_s(0, 1, 1, 1, 3)) == 1.5        # 4/5 vs 1/5
    assert balanced_line(_s(10, 20, 30)) == 20.5          # 2/3 vs 1/3: exact tie, not float noise


def test_balanced_line_keeps_half_point_median_and_floor():
    assert balanced_line(_s(17, 18)) == 17.5
    assert balanced_line(_s(0, 0, 0, 1)) == 0.5           # never below 0.5


def test_wilson_interval_known_values():
    lo, hi = wilson_interval(11, 11)
    assert lo == pytest.approx(0.741, abs=0.002) and hi == 1.0
    lo, hi = wilson_interval(3, 10)
    assert lo == pytest.approx(0.108, abs=0.002) and hi == pytest.approx(0.603, abs=0.002)
    assert wilson_interval(0, 0) == (0.0, 1.0)


def test_lean_needs_whole_range_off_fifty():
    assert lean(11, 11) == "over"
    assert lean(0, 11) == "under"
    assert lean(7, 11) is None
    assert lean(3, 3) is None          # 3 for 3 is not enough to call


@pytest.fixture
def standings():
    return pd.DataFrame([
        {"team_abbr": "SAS", "wins": 9, "losses": 2, "drtg": 105.0, "pace": 100.0},
        {"team_abbr": "CHI", "wins": 1, "losses": 9, "drtg": 125.0, "pace": 104.0},
        {"team_abbr": "OKC", "wins": 9, "losses": 1, "drtg": 110.0, "pace": 98.0},
    ])


def test_matchup_factors_shrink_opponent_defense(standings):
    f = matchup_factors(standings, "SAS", "CHI")
    league = (105 + 125 + 110) / 3
    adj = league + (125 - league) * 10 / (10 + SHRINK_GAMES)
    assert f["available"] is True
    assert f["game_pace"] == pytest.approx(102.0)
    assert f["pace_factor"] == pytest.approx(1.02)
    assert f["opp_drtg_adj"] == pytest.approx(adj)
    assert f["points_factor"] == pytest.approx(1.02 * adj / league)
    assert f["opp_drtg_rank"] == 3          # worst defense of three


def test_matchup_factors_neutral_without_ratings():
    f = matchup_factors(pd.DataFrame(), "SAS", "CHI")
    assert f == {"pace_factor": 1.0, "points_factor": 1.0, "available": False}


def _sched(gid, tip, home, away, status=3):
    return {"game_id": gid, "tipoff_utc": tip, "status": status, "home_abbr": home, "away_abbr": away,
            "home_score": 0, "away_score": 0, "arena": "", "city": "", "tv": ""}


def test_rest_days_counts_full_days_off():
    schedule = pd.DataFrame([
        _sched("1", "2026-11-08T01:00:00Z", "SAS", "UTA"),   # Nov 7, 7 PM CT
        _sched("2", "2026-11-10T02:00:00Z", "PHX", "SAS"),   # Nov 9, 8 PM CT
        _sched("3", "2026-11-11T01:00:00Z", "CHI", "UTA"),   # Nov 10, 7 PM CT
    ])
    tip = datetime(2026, 11, 11, 19, 0, tzinfo=LOCAL_TZ)
    assert rest_days(schedule, "SAS", tip) == 1
    assert rest_days(schedule, "CHI", tip) == 0             # second night of a back-to-back
    assert rest_days(schedule, "OKC", tip) is None


def _log(gid, date, name, minutes, pts, ast=0, blk=0):
    return {"game_id": gid, "game_date": pd.Timestamp(date), "player_name": name, "min": minutes,
            "pts": pts, "reb": 0, "ast": ast, "fg3m": 0, "blk": blk}


def test_prop_rows_lines_venue_and_dnps():
    logs = pd.DataFrame([
        _log("g1", "2026-11-01", "Ace", 30, 10, ast=6),
        _log("g2", "2026-11-02", "Ace", 30, 20, ast=6),
        _log("g3", "2026-11-03", "Ace", 30, 30, ast=6),
        _log("g4", "2026-11-04", "Ace", 0, 0, ast=0),         # DNP: excluded everywhere
        _log("g1", "2026-11-01", "Bench", 10, 2),
    ])
    games = pd.DataFrame({"game_id": ["g1", "g2", "g3", "g4"], "home_away": ["H", "A", "A", "H"]})
    prev = pd.DataFrame([_log(f"p{i}", "2025-12-01", "Ace", 30, 15) for i in range(MIN_PREV_GAMES)])
    factors = {"pace_factor": 1.1, "points_factor": 1.2}

    rows = {(r["player_name"], r["stat"]): r for r in prop_rows(logs, prev, games, factors, venue="A")}

    pts = rows[("Ace", "Points")]
    assert pts["games"] == 3
    assert pts["median"] == 20 and pts["current_line"] == 20.5
    assert pts["tonight"] == pytest.approx(24.0)            # points use the points factor
    assert (pts["venue_hits"], pts["venue_n"]) == (1, 2)    # road games g2, g3; only 30 clears 20.5
    assert pts["prev_line"] == 15.5 and pts["prev_hits"] == 2
    assert pts["prev_range"] == wilson_interval(2, 3)

    ast = rows[("Ace", "Assists")]                          # signature stat picked from averages
    assert ast["tonight"] == pytest.approx(6.6)             # other stats use pace only

    bench = rows[("Bench", "Points")]
    assert bench["prev_line"] is None and bench["prev_lean"] is None


def test_prop_rows_empty_without_games():
    assert prop_rows(pd.DataFrame(columns=["min"]), pd.DataFrame(), pd.DataFrame()) == []
