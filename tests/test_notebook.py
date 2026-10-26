"""Unit tests for the Spurs Living Notebook dynamic essay engine."""

from __future__ import annotations

import pandas as pd
import pytest
from blog.posts import get_all_posts, build_french_horizon_post, build_stonecutters_ledger_post


@pytest.fixture
def sample_context():
    player_logs = pd.DataFrame([
        {
            "game_id": "0022500001",
            "game_date": "2025-10-25",
            "player_id": 1641705,
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
    ])
    from analysis.wemby import get_wemby_logs
    wemby_logs = get_wemby_logs(player_logs)

    games = pd.DataFrame([
        {
            "game_id": "0022500001",
            "game_date": "2025-10-25",
            "home_away": "H",
            "result": "W",
            "pts": 118,
            "opp_pts": 105,
            "margin": 13,
            "drtg": 104.2,
            "ortg": 117.1,
            "nrtg": 12.9,
            "pace": 100.0,
            "status": "Final",
        }
    ])
    from analysis.standings import season_record
    return {
        "games": games,
        "player_logs": player_logs,
        "wemby_logs": wemby_logs,
        "season_record": season_record(games),
        "season": 2025,
        "team_abbr": "SAS",
    }


def test_get_all_posts(sample_context):
    posts = get_all_posts(sample_context)
    assert len(posts) == 4
    slugs = [p["slug"] for p in posts]
    assert "french-horizon" in slugs
    assert "stonecutters-ledger" in slugs
    assert "rodeo-gauntlet" in slugs
    assert "pass-first" in slugs

    for p in posts:
        assert p["title"]
        assert p["html"]
        assert len(p["html"]) > 100


def test_french_horizon_contains_computed_numbers(sample_context):
    post = build_french_horizon_post(sample_context)
    html = post["html"]
    # Verify that the computed stats appear in the generated HTML
    assert "Victor Wembanyama" in html
    assert "5.00 blocks" in html
    assert "2.00 steals" in html
    assert "7.00 stocks" in html
