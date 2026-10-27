"""Tests for link-preview images and the share tags that point at them."""

from __future__ import annotations

import pandas as pd
from PIL import Image

import config
from viz import share_images, theme


def _games():
    return pd.DataFrame([{
        "game_id": "G1", "game_date": "2026-10-24", "status": "Final", "home_away": "A",
        "opponent_abbr": "DAL", "result": "W", "pts": 122, "opp_pts": 106, "margin": 16,
        "nrtg": 14.5,
    }])


def _logs():
    return pd.DataFrame([{
        "game_id": "G1", "game_date": "2026-10-24", "player_name": "Bench Player", "min": 30.0,
        "pts": 19, "reb": 3, "oreb": 0, "dreb": 3, "ast": 9, "stl": 3, "blk": 1, "tov": 2, "pf": 2,
        "fgm": 6, "fga": 11, "ftm": 5, "fta": 6,
    }])


def test_latest_game_image_is_1200_by_630(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUT_DIR", tmp_path)
    out = share_images.render_latest_game(_games(), _logs(), tmp_path / "img/og/latest.png")
    assert out is not None and Image.open(out).size == (1200, 630)


def test_no_image_before_any_game(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUT_DIR", tmp_path)
    empty = _games().iloc[0:0]
    assert share_images.render_latest_game(empty, _logs(), tmp_path / "x.png") is None


def test_image_url_is_absolute_and_versioned(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUT_DIR", tmp_path)
    share_images.render_latest_game(_games(), _logs(), tmp_path / "img/og/latest.png")
    url = share_images.og_image_url("latest")
    assert url.startswith(config.SITE_URL + "/img/og/latest.png?v=")


def test_share_meta_uses_large_card_only_when_image_exists(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUT_DIR", tmp_path)
    assert 'content="summary"' in theme.share_meta("T", "<b>desc</b>")
    share_images.render_latest_game(_games(), _logs(), tmp_path / "img/og/latest.png")
    meta = theme.share_meta("T", "<b>desc</b> &middot; more")
    assert "summary_large_image" in meta and 'property="og:image"' in meta
    assert 'content="desc · more"' in meta  # tags stripped, entities decoded
