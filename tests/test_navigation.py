"""
Site navigation tests for spurs_tracker.

Ensures that the navigation registry is consistent, every page declares a known
mode, every mode has a valid landing page, and all registered output files exist
on disk in docs/.
"""

from __future__ import annotations

import re
from pathlib import Path
import pytest

import config
from viz import theme

DOCS = Path(__file__).resolve().parent.parent / "docs"


class TestPageRegistry:
    def test_every_page_declares_a_known_mode(self):
        for slug, (_, _, mode) in theme.PAGES.items():
            assert mode in theme.MODE_LABELS, f"{slug} has an unregistered mode"

    def test_every_mode_has_a_landing_page(self):
        for mode in theme.MODE_LABELS:
            landing = theme._mode_landing(mode)
            assert landing != "index.html", f"{mode} has no pages"
            assert landing.endswith(".html")

    def test_registered_filenames_exist_on_disk(self):
        for slug, (filename, _, _) in theme.PAGES.items():
            target = DOCS / filename
            assert target.exists(), f"{slug} -> {filename} not built"


class TestNavBar:
    def test_marks_exactly_one_mode_active(self):
        for slug in theme.PAGES:
            html = theme.nav_bar(slug)
            assert html.count("mode-seg active") == 1, slug

    def test_the_active_mode_is_the_current_page_s_mode(self):
        for slug, (_, _, mode) in theme.PAGES.items():
            html = theme.nav_bar(slug)
            active = re.search(r'mode-seg active">([^<]+)', html).group(1)
            assert active == theme.MODE_LABELS[mode], slug

    def test_shows_only_the_current_mode_s_pages(self):
        for slug, (_, _, mode) in theme.PAGES.items():
            html = theme.nav_bar(slug)
            pages_chunk = re.search(r'<div class="nav-pages">(.*?)</div>', html, re.S).group(1)
            for other_slug, (filename, _, other_mode) in theme.PAGES.items():
                if other_mode == mode:
                    continue
                assert filename not in pages_chunk, (
                    f"Page {filename} from mode {other_mode} leaked into nav for {slug}"
                )


class TestPagePath:
    def test_current_season_uses_stable_filename(self):
        assert theme.page_path("dashboard").name == "dashboard.html"

    def test_other_seasons_never_overwrite_live_page(self):
        path = theme.page_path("dashboard", config.TEAM_ABBR, config.SEASON - 1)
        assert path.name == f"dashboard_{config.TEAM_ABBR}_{config.SEASON - 1}.html"
