"""Tests for La Baraja (roster page), player pages and player links."""

from __future__ import annotations

import pandas as pd

import config
from viz import avatars, roster_viz


def _games():
    return pd.DataFrame([
        {"game_id": f"G{i}", "game_date": f"2026-10-2{i}", "status": "Final", "home_away": "H",
         "opponent_abbr": "OKC", "result": r, "pts": 110, "opp_pts": 100 if r == "W" else 120}
        for i, r in ((1, "W"), (2, "L"))
    ])


def _row(gid, date, name, pts, minutes=30.0):
    return {"game_id": gid, "game_date": date, "player_name": name, "min": minutes, "pts": pts,
            "reb": 5, "oreb": 1, "dreb": 4, "ast": 4, "stl": 1, "blk": 1, "tov": 2, "pf": 2,
            "fgm": pts // 2, "fga": pts, "fg3m": 1, "fg3a": 3, "ftm": 0, "fta": 0, "plus_minus": 3}


def _logs():
    return pd.DataFrame([
        _row("G1", "2026-10-21", "De'Aaron Fox", 25), _row("G1", "2026-10-21", "Tarris Reed Jr.", 4, 8.0),
        _row("G2", "2026-10-22", "De'Aaron Fox", 18), _row("G2", "2026-10-22", "Tarris Reed Jr.", 9, 12.0),
    ])


def _roster():
    return pd.DataFrame([
        {"player_name": "De'Aaron Fox", "jersey_number": "4", "position": "G", "years_of_experience": 9},
        {"player_name": "Tarris Reed Jr.", "jersey_number": "10", "position": "C", "years_of_experience": 0},
        {"player_name": "Jayden Quaintance", "jersey_number": "22", "position": "F", "years_of_experience": 0},
    ])


def test_builds_roster_and_a_page_per_player(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUT_DIR", tmp_path)
    paths = {p.name for p in roster_viz.build_roster_pages(_games(), _logs(), _roster())}
    assert {"roster.html", "player_fox.html", "player_tarris-reed-jr.html",
            "player_jayden-quaintance.html"} <= paths


def test_roster_orders_by_minutes_and_separates_yet_to_play(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUT_DIR", tmp_path)
    roster_viz.build_roster_pages(_games(), _logs(), _roster())
    html = (tmp_path / "roster.html").read_text()
    assert html.index("De&#x27;Aaron Fox") < html.index("Tarris Reed Jr.") < html.index("Yet to Play")
    assert html.index("Yet to Play") < html.index("Jayden Quaintance")


def test_player_page_shows_honors_and_game_log(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUT_DIR", tmp_path)
    roster_viz.build_roster_pages(_games(), _logs(), _roster())
    html = (tmp_path / "player_fox.html").read_text()
    assert "El Valiente &middot; Player of the Game &times;2" in html
    assert "Game Log" in html and "#4 &middot; G &middot; 9 yrs exp" in html


def test_compinche_honors_appear_on_player_page_and_roster(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUT_DIR", tmp_path)
    roster_viz.build_roster_pages(_games(), _logs(), _roster())
    player = (tmp_path / "player_tarris-reed-jr.html").read_text()
    assert "El Compinche &middot; Wingman &times;2" in player
    assert "Player of the Game &times;" not in player
    assert "Compinche &times;2" in (tmp_path / "roster.html").read_text()


def test_unfinished_games_do_not_count_as_player_honors():
    games = _games()
    games.loc[games["game_id"] == "G2", "status"] = "Scheduled"
    honors = roster_viz._honors(games, _logs())
    assert honors["De'Aaron Fox"]["player_of_the_game"] == 1
    assert honors["Tarris Reed Jr."]["compinche"] == 1


def test_rookie_label(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUT_DIR", tmp_path)
    roster_viz.build_roster_pages(_games(), _logs(), _roster())
    assert "Rookie" in (tmp_path / "player_tarris-reed-jr.html").read_text()


def test_player_link_only_when_page_exists(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUT_DIR", tmp_path)
    assert avatars.player_link("Domantas Sabonis") == "Domantas Sabonis"
    (tmp_path / "player_fox.html").write_text("x")
    assert avatars.player_link("De'Aaron Fox", "Fox") == '<a class="player-link" href="player_fox.html">Fox</a>'


def test_other_seasons_do_not_overwrite_live_player_pages(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUT_DIR", tmp_path)
    assert roster_viz.build_roster_pages(_games(), _logs(), _roster(), season=config.SEASON - 1) == []
