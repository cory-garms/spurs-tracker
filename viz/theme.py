"""
San Antonio Spurs Visual Theme — Single source of truth for colour, typography,
Plotly layouts, and HTML chrome across the Spurs Tracker analytics suite.

Identity:
  - Arena / Dark: Frost Bank Center court at night (#0B0E11, #161A1F, #1D232A)
  - Primary Identity: Spurs Silver (#C4CED4) & Spurs Steel (#8A9399)
  - Vintage Fiesta Accents:
      * Teal (#00B2A9) — Island / Turquoise (Win / high-performance)
      * Fuschia (#EF426F) — Fiesta Pink (Loss / defensive alert)
      * Orange (#FF8200) — Rowdy Fiesta Orange (Warning / neutral)
  - Hardwood Gold: (#D4A373)
"""

from __future__ import annotations

import re
from pathlib import Path
import config

# ---------------------------------------------------------------------------
# Surfaces & Ink — Frost Bank Center Night
# ---------------------------------------------------------------------------
FROST_BANK_FLOOR = "#0B0E11"  # Deep night court background
SILVER_SLATE     = "#161A1F"  # Card background / Plotly paper_bgcolor
SHADOW_BLACK     = "#1D232A"  # Sub-card, table headers, deep surfaces
COURT_LINE       = "#28313A"  # Subtle grid lines and borders
SPURS_SILVER     = "#C4CED4"  # Official Spurs Silver
SPURS_STEEL      = "#8A9399"  # Secondary metallic steel
COURT_WHITE      = "#F6F8FA"  # Primary typography on dark surfaces
TEXT_MUTED       = "#9DA7B0"  # Secondary annotations & subtitles
HARDWOOD_GOLD    = "#D4A373"  # Accent wood tone
ALAMO_STONE      = "#C9B097"  # San Antonio limestone / Mission stone
ALAMO_OCHRE      = "#D4A373"  # Spanish mission ochre

# ---------------------------------------------------------------------------
# The Alamo & Mission Heritage SVGs
# ---------------------------------------------------------------------------
ALAMO_ICON_SVG = (
    '<svg class="alamo-icon-svg" viewBox="0 0 100 50" fill="none" xmlns="http://www.w3.org/2000/svg" aria-label="The Alamo Mission Icon">'
    '<path d="M 6 46 L 94 46 L 94 34 L 84 34 L 84 26 C 81 26 78 24 76 21 C 72 21 69 16 63 16 C 60 10 53 8 50 8 C 47 8 40 10 37 16 C 31 16 28 21 24 21 C 22 24 19 26 16 26 L 16 34 L 6 34 Z" fill="currentColor"/>'
    '<path d="M 46 20 C 46 17 54 17 54 20 L 54 27 L 46 27 Z" fill="#0B0E11"/>'
    '<path d="M 43 46 L 43 36 C 43 32 57 32 57 36 L 57 46 Z" fill="#0B0E11"/>'
    '</svg>'
)

ALAMO_ROOFLINE_SVG = (
    '<svg class="alamo-roofline-svg" viewBox="0 0 120 18" fill="none" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="none">'
    f'<path d="M 0 18 L 14 18 L 14 12 L 30 12 L 30 8 C 36 8 40 6 44 4 C 50 4 54 0 60 0 C 66 0 70 4 76 4 C 80 6 84 8 90 8 L 90 12 L 106 12 L 106 18 L 120 18 Z" fill="{SILVER_SLATE}"/>'
    f'<path d="M 0 18 L 14 18 L 14 12 L 30 12 L 30 8 C 36 8 40 6 44 4 C 50 4 54 0 60 0 C 66 0 70 4 76 4 C 80 6 84 8 90 8 L 90 12 L 106 12 L 106 18 L 120 18" stroke="{COURT_LINE}" stroke-width="1" fill="none"/>'
    '</svg>'
)

# ---------------------------------------------------------------------------
# Vintage Fiesta Accents
# ---------------------------------------------------------------------------
FIESTA_TEAL      = "#00B2A9"  # Win / Over / Deterrence
FIESTA_FUSCHIA   = "#EF426F"  # Loss / Under / Defect
FIESTA_ORANGE    = "#FF8200"  # Warning / Neutral mark

CATEGORICAL: tuple[str, ...] = (
    FIESTA_TEAL,
    SPURS_SILVER,
    FIESTA_FUSCHIA,
    FIESTA_ORANGE,
)

WIN   = FIESTA_TEAL
LOSS  = FIESTA_FUSCHIA
ALERT = FIESTA_ORANGE

# ---------------------------------------------------------------------------
# Typography
# ---------------------------------------------------------------------------
FONTS_LINK = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
    '  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
    '  <link href="https://fonts.googleapis.com/css2?'
    'family=Barlow+Condensed:wght@400;600;700;800&'
    'family=Graduate&'
    'family=Share+Tech+Mono&'
    'family=Teko:wght@500;600;700&display=swap" rel="stylesheet">'
)

FONT_DISPLAY = '"Teko", sans-serif'
FONT_STENCIL = '"Barlow Condensed", sans-serif'
FONT_TITLE   = '"Barlow Condensed", sans-serif'
FONT_MONO    = '"Share Tech Mono", monospace'
FONT_BODY    = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'

# ---------------------------------------------------------------------------
# Plotly Layout Standards
# ---------------------------------------------------------------------------
LAYOUT_BASE = dict(
    paper_bgcolor=SILVER_SLATE,
    plot_bgcolor=FROST_BANK_FLOOR,
    font=dict(color=COURT_WHITE, family="Share Tech Mono, monospace", size=12),
    xaxis=dict(gridcolor=COURT_LINE, zerolinecolor=COURT_LINE),
    yaxis=dict(gridcolor=COURT_LINE, zerolinecolor=COURT_LINE),
    margin=dict(l=60, r=30, t=50, b=50),
    legend=dict(
        bgcolor="rgba(0,0,0,0)",
        bordercolor=COURT_LINE,
        font=dict(family="Barlow Condensed, sans-serif", size=13),
    ),
)

PLOTLY_CONFIG = {
    "responsive": True,
    "displaylogo": False,
    "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d"],
}


def apply(fig, **extra):
    """Apply the Spurs Silver & Black theme to a Plotly figure."""
    fig.update_layout(**{**LAYOUT_BASE, **extra})
    fig.update_xaxes(gridcolor=COURT_LINE, zerolinecolor=COURT_LINE, automargin=True)
    fig.update_yaxes(gridcolor=COURT_LINE, zerolinecolor=COURT_LINE, automargin=True)
    fig.update_layout(autosize=True)
    return fig


# ---------------------------------------------------------------------------
# Navigation & Modes
# ---------------------------------------------------------------------------
MODE_COURT = "court"
MODE_PROPS = "props"

MODE_LABELS = {
    MODE_COURT: "🏀 Court Intelligence",
    MODE_PROPS: "🎲 Props & Market",
}

# slug -> (filename, nav label, mode)
# Filenames are season-agnostic so shared links survive the yearly rollover;
# the current season (config.SEASON) always publishes to these names.
PAGES: dict[str, tuple[str, str, str]] = {
    "dashboard": ("dashboard.html",       "Season Dashboard", MODE_COURT),
    "wemby":     ("wemby_lab.html",       "Wemby Lab",        MODE_COURT),
    "rodeo":     ("rodeo_road_trip.html", "Rodeo Road Trip",  MODE_COURT),
    "notebook":  ("notebook.html",        "Spurs Notebook",   MODE_COURT),
    "matchup":   ("matchup.html",         "Matchup Intel",    MODE_PROPS),
    "board":     ("props_board.html",     "Player Props",     MODE_PROPS),
}


def page_path(slug: str, team_abbr: str = config.TEAM_ABBR, season: int = config.SEASON) -> Path:
    """
    Output path for a registered page. The current team/season gets the stable
    filename; any other team or season (backfills, comparisons) is suffixed so it
    never overwrites the live page.
    """
    filename = PAGES[slug][0]
    if team_abbr.upper() != config.TEAM_ABBR or season != config.SEASON:
        stem = filename.removesuffix(".html")
        filename = f"{stem}_{team_abbr.upper()}_{season}.html"
    return config.OUTPUT_DIR / filename


def stamp_index_season(season_label: str) -> None:
    """Keep the hand-authored landing page's season badge in sync with the build."""
    index = config.OUTPUT_DIR / "index.html"
    if not index.exists():
        return
    html = index.read_text(encoding="utf-8")
    html = re.sub(r'(<span class="badge">)\d{4}-\d{2}( Season Suite</span>)', rf"\g<1>{season_label}\g<2>", html)
    index.write_text(html, encoding="utf-8")


def _mode_landing(mode: str) -> str:
    for slug, (fn, _, m) in PAGES.items():
        if m == mode:
            return fn
    return "index.html"


def nav_bar(current_slug: str) -> str:
    """Generate the responsive Spurs dual-mode navigation bar."""
    curr_entry = PAGES.get(current_slug)
    curr_mode = curr_entry[2] if curr_entry else MODE_COURT

    # Mode switch buttons
    mode_buttons = []
    for mode, label in MODE_LABELS.items():
        is_active = (mode == curr_mode)
        active_cls = " active" if is_active else ""
        target_fn = _mode_landing(mode)
        if is_active:
            mode_buttons.append(f'<span class="mode-seg{active_cls}">{label}</span>')
        else:
            mode_buttons.append(f'<a href="{target_fn}" class="mode-seg">{label}</a>')
    mode_switch_html = f'<div class="mode-switch">{"".join(mode_buttons)}</div>'

    # Page links inside the active mode
    page_links = [
        '<a href="index.html" class="nav-page index-link">← Spurs HQ</a>'
    ]
    for slug, (filename, label, mode) in PAGES.items():
        if mode != curr_mode:
            continue
        if slug == current_slug:
            page_links.append(f'<span class="nav-page current">{label}</span>')
        else:
            page_links.append(f'<a href="{filename}" class="nav-page">{label}</a>')

    pages_html = f'<div class="nav-pages">{" ".join(page_links)}</div>'
    return f'<nav class="nav-bar">{mode_switch_html}{pages_html}</nav>'


# ---------------------------------------------------------------------------
# CSS Chrome Generator
# ---------------------------------------------------------------------------
def page_css() -> str:
    """Stonecutter Silver & Black + Fiesta CSS."""
    return f"""
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    html, body {{
      background:
        radial-gradient(ellipse at 50% 0%, rgba(196, 206, 212, 0.04) 0%, transparent 70%),
        {FROST_BANK_FLOOR};
      color: {COURT_WHITE};
      font-family: {FONT_BODY};
      min-height: 100vh;
      width: 100%;
      overflow-x: hidden;
      -webkit-text-size-adjust: 100%;
    }}
    body {{ padding: clamp(12px, 3vw, 28px); }}

    /* ---- Navigation ---- */
    .nav-bar {{ margin-bottom: 24px; }}
    .mode-switch {{
      display: flex; width: 100%;
      border: 1px solid {COURT_LINE}; border-radius: 4px;
      overflow: hidden; margin-bottom: 12px;
      background: {FROST_BANK_FLOOR};
    }}
    .mode-seg {{
      flex: 1 1 50%; text-align: center;
      padding: 10px 8px;
      font-family: {FONT_STENCIL}; font-size: clamp(0.75rem, 2.5vw, 0.9rem);
      font-weight: 700;
      letter-spacing: 0.08em; text-transform: uppercase;
      color: {TEXT_MUTED}; text-decoration: none;
      background: {FROST_BANK_FLOOR};
      transition: background 0.18s ease, color 0.18s ease;
      min-height: 44px; display: flex; align-items: center; justify-content: center;
    }}
    .mode-seg + .mode-seg {{ border-left: 1px solid {COURT_LINE}; }}
    .mode-seg.active {{
      background: {SHADOW_BLACK}; color: {COURT_WHITE};
      box-shadow: inset 0 -3px 0 {SPURS_SILVER};
    }}
    a.mode-seg:hover {{ background: {SILVER_SLATE}; color: {COURT_WHITE}; }}

    .nav-pages {{ display: flex; flex-wrap: wrap; gap: 8px; }}
    .nav-page {{
      color: {COURT_WHITE}; text-decoration: none;
      font-family: {FONT_STENCIL}; font-size: 0.8rem;
      font-weight: 600;
      letter-spacing: 0.06em; text-transform: uppercase;
      padding: 8px 14px;
      background: {SILVER_SLATE};
      border: 1px solid {COURT_LINE};
      border-radius: 4px;
      transition: all 0.18s ease;
    }}
    a.nav-page:hover {{ background: {SHADOW_BLACK}; border-color: {SPURS_SILVER}; color: {SPURS_SILVER}; }}
    .nav-page.current {{
      background: {SHADOW_BLACK}; border-color: {SPURS_SILVER}; color: {SPURS_SILVER};
      box-shadow: inset 0 0 0 1px {SPURS_SILVER};
      cursor: default;
    }}
    .nav-page.index-link {{ color: {TEXT_MUTED}; background: transparent; border-color: transparent; }}
    .nav-page.index-link:hover {{ color: {COURT_WHITE}; background: {SILVER_SLATE}; }}

    /* ---- Alamo Heritage & Architecture ---- */
    .alamo-header-wrap {{
      margin-bottom: 24px;
      position: relative;
    }}
    .alamo-roofline-crown {{
      width: clamp(140px, 30vw, 240px);
      height: 18px;
      margin: 0 auto -1px;
      display: block;
      position: relative;
      z-index: 2;
    }}
    .alamo-roofline-crown svg {{
      width: 100%; height: 100%; display: block;
    }}
    .alamo-meta-banner {{
      display: inline-flex; align-items: center; gap: 8px;
      font-family: {FONT_MONO}; font-size: 0.72rem; letter-spacing: 0.12em;
      text-transform: uppercase; color: {ALAMO_STONE}; margin-bottom: 10px;
      padding: 4px 10px; background: rgba(201, 176, 151, 0.08);
      border: 1px solid rgba(201, 176, 151, 0.25); border-radius: 4px;
    }}
    .alamo-icon-svg {{
      width: 22px; height: 12px; display: inline-block; vertical-align: middle;
      color: {ALAMO_STONE}; flex-shrink: 0;
    }}
    .alamo-footer-seal {{
      display: flex; justify-content: center; align-items: center; margin-bottom: 14px;
      opacity: 0.75;
    }}
    .alamo-footer-seal .alamo-icon-svg {{
      width: 44px; height: 22px; color: {SPURS_STEEL};
    }}

    /* ---- Header ---- */
    header {{
      background:
        radial-gradient(ellipse at 90% 10%, rgba(201, 176, 151, 0.06) 0%, transparent 60%),
        linear-gradient(180deg, {SILVER_SLATE} 0%, {SHADOW_BLACK} 100%);
      border: 1px solid {COURT_LINE};
      border-top: 3px solid {SPURS_SILVER};
      border-radius: 6px;
      padding: clamp(16px, 3vw, 24px);
      position: relative;
    }}
    header::after {{
      content: "";
      position: absolute; bottom: 0; left: 0; right: 0; height: 3px;
      background: linear-gradient(90deg, {FIESTA_TEAL} 0%, {FIESTA_TEAL} 33.3%, {FIESTA_FUSCHIA} 33.3%, {FIESTA_FUSCHIA} 66.6%, {FIESTA_ORANGE} 66.6%, {FIESTA_ORANGE} 100%);
    }}
    header h1 {{
      font-family: {FONT_DISPLAY};
      font-size: clamp(1.8rem, 4.5vw, 2.8rem);
      letter-spacing: 0.04em;
      text-transform: uppercase;
      color: {COURT_WHITE};
      display: flex; align-items: center; flex-wrap: wrap; gap: 12px;
    }}
    header p {{
      color: {TEXT_MUTED}; margin-top: 6px;
      font-size: clamp(0.85rem, 2vw, 1.0rem); line-height: 1.5;
    }}

    /* ---- Cards ---- */
    .chart-section, .card {{
      background: {SILVER_SLATE};
      border: 1px solid {COURT_LINE};
      border-radius: 6px;
      padding: clamp(14px, 3vw, 22px);
      margin-bottom: 24px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    }}
    .chart-title, .card h2 {{
      font-family: {FONT_STENCIL};
      font-size: 1.1rem;
      font-weight: 700;
      color: {SPURS_SILVER};
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 16px;
      padding-bottom: 8px;
      border-bottom: 1px solid {COURT_LINE};
      display: flex; align-items: center; justify-content: space-between;
    }}

    /* ---- Badges ---- */
    .badge {{
      display: inline-block;
      font-family: {FONT_MONO};
      font-size: 0.75rem;
      padding: 3px 8px;
      border-radius: 3px;
      background: {SHADOW_BLACK};
      border: 1px solid {SPURS_STEEL};
      color: {COURT_WHITE};
      text-transform: uppercase;
    }}
    .badge.teal {{ background: rgba(0, 178, 169, 0.15); border-color: {FIESTA_TEAL}; color: {FIESTA_TEAL}; }}
    .badge.fuschia {{ background: rgba(239, 66, 111, 0.15); border-color: {FIESTA_FUSCHIA}; color: {FIESTA_FUSCHIA}; }}
    .badge.orange {{ background: rgba(255, 130, 0, 0.15); border-color: {FIESTA_ORANGE}; color: {FIESTA_ORANGE}; }}

    /* ---- Footer ---- */
    footer {{
      text-align: center; color: {TEXT_MUTED};
      font-size: 0.85rem; margin-top: 48px; padding-top: 24px;
      border-top: 1px solid {COURT_LINE};
    }}
    footer .stonecutter {{
      max-width: 680px; margin: 0 auto 16px;
      font-style: italic; font-size: 0.8rem; line-height: 1.5; color: {SPURS_STEEL};
    }}
    footer a {{ color: {SPURS_SILVER}; text-decoration: none; }}
    footer a:hover {{ text-decoration: underline; }}
    """


def page_footer() -> str:
    """Generate the standard Spurs footer with stonecutter motto and Alamo City seal."""
    return f"""
    <footer>
      <div class="alamo-footer-seal" aria-hidden="true">
        {ALAMO_ICON_SVG}
      </div>
      <p class="stonecutter">
        &ldquo;When nothing seems to help, I go and look at a stonecutter hammering away at his rock,
        perhaps a hundred times without as much as a crack showing in it. Yet at the hundred and first blow
        it will split in two, and I know it was not that last blow that did it, but all that had gone before.&rdquo;
        <br>&mdash; Jacob Riis / San Antonio Spurs Creed
      </p>
      <p>The Alamo City &bull; San Antonio Spurs Analytics Suite &bull; Silver &amp; Black Performance Intelligence</p>
    </footer>
    """


def page_html(
    title: str,
    subtitle: str,
    body_content: str,
    current_slug: str = "dashboard",
    badge: str = "2025-26 Season",
) -> str:
    """Wrap content in the official Spurs HTML shell."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} — San Antonio Spurs Analytics</title>
  {FONTS_LINK}
  <style>
{page_css()}
  </style>
</head>
<body>
  {nav_bar(current_slug)}
  <div class="alamo-header-wrap">
    <div class="alamo-roofline-crown">
      {ALAMO_ROOFLINE_SVG}
    </div>
    <header>
      <div class="alamo-meta-banner">
        {ALAMO_ICON_SVG}
        <span>The Alamo City &bull; Mission San Antonio</span>
      </div>
      <h1>{title} <span class="badge">{badge}</span></h1>
      <p>{subtitle}</p>
    </header>
  </div>
  <main>
    {body_content}
  </main>
  {page_footer()}
</body>
</html>
"""
