"""Tests for viz/theme.py colour constants and helpers."""

from __future__ import annotations

import pytest
from viz import theme


def test_theme_categorical_marks_defined():
    assert len(theme.CATEGORICAL) == 4
    assert theme.FIESTA_TEAL in theme.CATEGORICAL
    assert theme.SPURS_SILVER in theme.CATEGORICAL
    assert theme.FIESTA_FUSCHIA in theme.CATEGORICAL
    assert theme.FIESTA_ORANGE in theme.CATEGORICAL


def test_theme_semantic_colors():
    assert theme.WIN == theme.FIESTA_TEAL
    assert theme.LOSS == theme.FIESTA_FUSCHIA
    assert theme.ALERT == theme.FIESTA_ORANGE


def test_page_css_contains_spurs_tokens():
    css = theme.page_css()
    assert theme.FROST_BANK_FLOOR in css
    assert theme.SPURS_SILVER in css
    assert theme.FIESTA_TEAL in css


def test_page_html_renders_structure():
    html = theme.page_html(
        title="Test Page",
        subtitle="Testing the shell",
        body_content="<div>Court Content</div>",
        current_slug="dashboard",
    )
    assert "<!DOCTYPE html>" in html
    assert "Test Page" in html
    assert "Court Content" in html
    assert "Created and Maintained by" in html
    assert '<a href="https://www.corygarms.com" target="_blank" rel="noopener">Cory Garms</a>' in html
    assert 'href="https://x.com/cory_garms"' in html
    assert 'href="https://github.com/cory-garms"' in html


def test_alamo_styling_elements():
    assert theme.ALAMO_STONE == "#C9B097"
    assert "<svg" in theme.ALAMO_ICON_SVG
    assert "<svg" in theme.ALAMO_ROOFLINE_SVG

    css = theme.page_css()
    assert "alamo-roofline-crown" in css
    assert "alamo-meta-banner" in css
    assert "alamo-footer-seal" in css

    html = theme.page_html(
        title="Alamo Test",
        subtitle="Testing Alamo styling",
        body_content="<div>Test</div>",
        current_slug="dashboard",
    )
    assert "The Alamo City" in html
    assert "alamo-roofline-crown" in html
    assert "alamo-footer-seal" in html


def test_font_constants_are_safe_inside_style_attributes():
    # Interpolated into style="..."; a double quote would end the attribute and drop the font
    for name in dir(theme):
        if name.startswith("FONT_") and name != "FONTS_LINK":
            assert '"' not in getattr(theme, name), name
