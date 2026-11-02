"""Game honors stay consistent across the home page, spotlight and season table."""

from __future__ import annotations

import pandas as pd
import pytest

import config
from viz import dashboard, index_viz


@pytest.fixture
def season_data():
    games = pd.DataFrame([
        {"game_id": f"G{i}", "game_date": f"2026-10-{20 + i}", "status": "Final",
         "home_away": "H" if i == 1 else "A", "opponent_abbr": "OKC" if i == 1 else "DAL",
         "result": "W" if i == 1 else "L", "pts": 110, "opp_pts": 100 if i == 1 else 120,
         "margin": 10 if i == 1 else -10, "nrtg": 5.0, "ortg": 110.0, "drtg": 105.0, "pace": 100.0}
        for i in (1, 2)
    ])
    logs = pd.DataFrame([
        {"game_id": f"G{i}", "game_date": f"2026-10-{20 + i}", "player_name": name,
         "player_id": 1641705 if name == "Victor Wembanyama" else 1628368, "min": 30.0,
         "pts": pts, "fgm": pts // 2, "fga": pts, "reb": 5, "oreb": 1, "dreb": 4,
         "ast": 4, "stl": 1, "blk": 1, "ftm": 0, "fta": 0, "pf": 2, "tov": 1,
         "fg3m": 1, "fg3a": 3, "plus_minus": 5, "ts_pct": 0.5, "usg_pct": 0.25}
        for i, name, pts in ((1, "Victor Wembanyama", 30), (1, "De'Aaron Fox", 20),
                             (2, "Victor Wembanyama", 15), (2, "De'Aaron Fox", 35))
    ])
    return games, logs


def test_dashboard_build_includes_latest_pair_and_all_games(season_data, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUT_DIR", tmp_path)
    games, logs = season_data
    (tmp_path / "player_fox.html").write_text("player page")
    output = dashboard.build(games, logs, "San Antonio Spurs", output_path=tmp_path / "dashboard.html")
    html = output.read_text()
    spotlight = html.split('id="spotlight"', 1)[1].split("</section>", 1)[0]
    assert "El Valiente &middot; Player of the Game" in spotlight
    assert "El Compinche &middot; Sidekick" in spotlight
    assert spotlight.index("De&#x27;Aaron Fox") < spotlight.index("Victor Wembanyama")
    assert 'href="player_fox.html"' in spotlight
    assert 'href="#honor-roll"' in spotlight
    assert html.index('data-game-id="G2"') < html.index('data-game-id="G1"')
    latest = html.split('data-game-id="G2"', 1)[1].split("</tr>", 1)[0]
    first = html.split('data-game-id="G1"', 1)[1].split("</tr>", 1)[0]
    assert "@ DAL" in latest and "L 110-120" in latest
    assert latest.index("De&#x27;Aaron Fox") < latest.index("Victor Wembanyama")
    assert first.index("Victor Wembanyama") < first.index("De&#x27;Aaron Fox")
    assert "GmSc" in latest and "PTS" in latest


def test_history_renders_missing_box_scores_and_ignores_unfinished_games(season_data):
    games, logs = season_data
    games.loc[games["game_id"] == "G2", "status"] = "Scheduled"
    html = dashboard._season_honors_html(games, pd.DataFrame())
    assert 'data-game-id="G1"' in html and 'data-game-id="G2"' not in html
    assert html.count("Box score pending") == 2
    assert "Honors appear after the first completed game" in dashboard._season_honors_html(pd.DataFrame(), logs)


def test_missing_latest_box_score_does_not_reuse_previous_games_spotlight(season_data):
    games, logs = season_data
    assert dashboard._spotlight_html(games, logs[logs["game_id"] == "G1"]) == ""


def test_home_page_highlights_latest_valiente_and_links_full_awards_log(season_data, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(index_viz, "load_schedule", lambda season: pd.DataFrame())
    games, logs = season_data
    output = index_viz.build_index_page(games, logs)
    html = output.read_text()
    assert '<div class="name">El Valiente</div>' in html
    assert '<div class="name">El Compinche</div>' not in html
    assert "Last game&#x27;s top Game Score: De&#x27;Aaron Fox" in html
    assert "Last game&#x27;s top teammate:" not in html
    assert 'href="dashboard.html#honor-roll"' in html
    assert "Who's hot" not in html


def test_home_page_handles_no_games_or_player_logs(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(index_viz, "load_schedule", lambda season: pd.DataFrame())
    games = pd.DataFrame(columns=["status", "game_date", "result"])
    html = index_viz.build_index_page(games, pd.DataFrame()).read_text()
    assert "El Valiente" in html and "El Compinche" in html
    assert "Player of the Game appears after a completed box score" in html
