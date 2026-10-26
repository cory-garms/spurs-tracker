"""Tests for the Next Game preview: schedule lookups, tale of the tape and projection."""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import pytest

from analysis.matchup_preview import players_to_watch, projection, tale_of_the_tape
from data.schedule import head_to_head, next_game, recent_results


def _sched_row(gid, tip, status, home, away, hs=0, as_=0):
    return {"game_id": gid, "tipoff_utc": tip, "status": status, "home_abbr": home, "away_abbr": away,
            "home_score": hs, "away_score": as_, "arena": "Frost Bank Center", "city": "San Antonio", "tv": "TV"}


@pytest.fixture
def schedule():
    return pd.DataFrame([
        _sched_row("1", "2026-10-21T01:30:00Z", 3, "SAS", "OKC", 104, 116),
        _sched_row("2", "2026-10-25T00:00:00Z", 3, "DAL", "SAS", 106, 122),
        _sched_row("3", "2026-10-26T00:00:00Z", 3, "SAC", "SAS", 100, 110),
        _sched_row("4", "2026-10-28T00:00:00Z", 1, "SAS", "SAC"),
        _sched_row("5", "2026-10-29T01:00:00Z", 1, "UTA", "SAS"),
    ])


def test_next_game_is_first_unfinished(schedule):
    g = next_game(schedule, "SAS", datetime(2026, 10, 26, 12, tzinfo=timezone.utc))
    assert g["opponent"] == "SAC" and g["is_home"] is True
    assert g["when"] == "Tuesday, Oct 27 · 7:00 PM CT"  # 00:00 UTC -> 7 PM Central


def test_recent_results_from_team_perspective(schedule):
    res = recent_results(schedule, "SAS")
    assert [r["result"] for r in res] == ["W", "W", "L"]           # most recent first
    assert res[1] == {"result": "W", "score": "122-106", "opponent": "DAL", "venue": "@", "date": "Oct 24"}


def test_head_to_head_only_completed_meetings(schedule):
    h2h = head_to_head(schedule, "SAS", "SAC")
    assert len(h2h) == 1 and h2h[0]["score"] == "110-100"


@pytest.fixture
def standings():
    return pd.DataFrame([
        {"team_abbr": "SAS", "wins": 8, "losses": 2, "nrtg": 6.0, "ortg": 116.0, "drtg": 110.0, "pace": 100.0},
        {"team_abbr": "SAC", "wins": 2, "losses": 8, "nrtg": -6.0, "ortg": 108.0, "drtg": 114.0, "pace": 100.0},
        {"team_abbr": "OKC", "wins": 9, "losses": 1, "nrtg": 12.0, "ortg": 118.0, "drtg": 106.0, "pace": 100.0},
    ])


def test_tale_of_the_tape_edges_respect_direction(standings):
    rows = {r["label"]: r for r in tale_of_the_tape(standings, "SAS", "SAC")}
    assert rows["Offensive rating"]["edge"] == "SAS"
    assert rows["Defensive rating"]["edge"] == "SAS"      # lower is better
    assert rows["Defensive rating"]["team_rank"] == 2      # OKC's 106 is best
    assert rows["Pace"]["edge"] is None                    # style, not quality


def test_projection_shrinks_early_ratings_and_adds_home_court(standings):
    home = projection(standings, "SAS", "SAC", is_home=True)
    away = projection(standings, "SAS", "SAC", is_home=False)
    # 10 games each: nets shrink by half (+3 vs -3) -> 6 pts at pace 100, +/- 2 home court
    assert home["margin"] == pytest.approx(8.0)
    assert away["margin"] == pytest.approx(4.0)
    assert 0.5 < away["win_prob"] < home["win_prob"] < 1


def test_players_to_watch_ranked_by_game_score():
    players = pd.DataFrame([
        {"player_name": "Scorer", "gp": 3, "pts": 29, "reb": 3, "oreb": 0, "dreb": 3, "ast": 3, "stl": 1, "blk": 0,
         "tov": 3, "pf": 2, "fgm": 10, "fga": 24, "ftm": 6, "fta": 7},
        {"player_name": "Big", "gp": 3, "pts": 19, "reb": 17, "oreb": 5, "dreb": 12, "ast": 7, "stl": 1, "blk": 0,
         "tov": 3, "pf": 3, "fgm": 8, "fga": 13, "ftm": 3, "fta": 4},
    ])
    assert players_to_watch(players)[0]["player_name"] == "Big"
