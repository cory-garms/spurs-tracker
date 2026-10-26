"""
Site navigation tests for spurs_tracker.

Ensures that the navigation registry is consistent, every page declares a known
mode, every mode has a valid landing page, and all registered output files exist
on disk in docs/.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
import pytest

import config
from viz import theme

DOCS = Path(__file__).resolve().parent.parent / "docs"


class TestPageRegistry:
    def test_registered_filenames_exist_on_disk(self):
        for slug, (filename, _) in theme.PAGES.items():
            target = DOCS / filename
            assert target.exists(), f"{slug} -> {filename} not built"


class TestNavBar:
    OFF_SEASON = date(2026, 10, 26)   # Rodeo not featured
    RODEO_SEASON = date(2027, 2, 10)

    def test_marks_exactly_the_current_page(self):
        for slug, (_, label) in theme.PAGES.items():
            html = theme.nav_bar(slug, self.RODEO_SEASON)
            assert html.count('class="nav-page current"') == 1, slug
            assert f'aria-current="page">{label}<' in html, slug

    def test_links_every_other_featured_page(self):
        html = theme.nav_bar("dashboard", self.RODEO_SEASON)
        for slug, (filename, _) in theme.PAGES.items():
            if slug != "dashboard":
                assert f'href="{filename}"' in html, slug

    def test_hides_out_of_season_pages(self):
        html = theme.nav_bar("dashboard", self.OFF_SEASON)
        assert "rodeo_road_trip.html" not in html

    def test_out_of_season_page_still_shows_itself_as_current(self):
        html = theme.nav_bar("rodeo", self.OFF_SEASON)
        assert 'aria-current="page">Rodeo Road Trip<' in html

    def test_always_links_home(self):
        assert 'href="index.html"' in theme.nav_bar("wemby")


class TestPagePath:
    def test_current_season_uses_stable_filename(self):
        assert theme.page_path("dashboard").name == "dashboard.html"

    def test_other_seasons_never_overwrite_live_page(self):
        path = theme.page_path("dashboard", config.TEAM_ABBR, config.SEASON - 1)
        assert path.name == f"dashboard_{config.TEAM_ABBR}_{config.SEASON - 1}.html"


class TestSeasonalPages:
    def test_rodeo_hidden_in_october(self):
        from datetime import date
        assert not theme.is_featured("rodeo", date(2026, 10, 26))

    def test_rodeo_featured_through_the_trip_and_april_splits(self):
        from datetime import date
        assert theme.is_featured("rodeo", date(2027, 1, 15))
        assert theme.is_featured("rodeo", date(2027, 2, 10))
        assert theme.is_featured("rodeo", date(2027, 4, 30))
        assert not theme.is_featured("rodeo", date(2027, 5, 1))

    def test_non_seasonal_pages_always_featured(self):
        from datetime import date
        assert theme.is_featured("dashboard", date(2026, 7, 4))
