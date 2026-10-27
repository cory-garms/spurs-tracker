"""Tests for player avatars: emblem when published, initials otherwise."""

from __future__ import annotations

import config
from viz import avatars


def test_initials_skip_suffixes_and_punctuation():
    assert avatars.initials("De'Aaron Fox") == "DF"
    assert avatars.initials("Tarris Reed Jr.") == "TR"
    assert avatars.initials("Nene") == "N"


def test_falls_back_to_initials_when_emblem_not_published(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUT_DIR", tmp_path)
    html = avatars.avatar_html("De'Aaron Fox", "md")
    assert "avatar-initials" in html and ">DF<" in html


def test_uses_emblem_once_published(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUT_DIR", tmp_path)
    (tmp_path / "img" / "players").mkdir(parents=True)
    (tmp_path / "img" / "players" / "fox.webp").write_bytes(b"webp")
    html = avatars.avatar_html("De'Aaron Fox", "lg")
    assert 'src="img/players/fox.webp"' in html
    assert 'title="El Zorro"' in html and "avatar-lg" in html


def test_players_without_an_entry_get_initials(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUT_DIR", tmp_path)
    assert avatars.avatar_src("Domantas Sabonis") is None
    assert ">DS<" in avatars.avatar_html("Domantas Sabonis")


def test_initials_color_is_stable():
    assert avatars._initials_color("Luke Kornet") == avatars._initials_color("Luke Kornet")


def test_emblem_slugs_are_unique():
    slugs = [slug for slug, _ in avatars.PLAYER_EMBLEMS.values()]
    assert len(slugs) == len(set(slugs))
