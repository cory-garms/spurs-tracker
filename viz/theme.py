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

from datetime import date
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

# Lotería palette (landing page): cream card stock, ink outlines, adobe terracotta
LOTERIA_CREAM    = "#F4EAD5"
LOTERIA_INK      = "#1B1712"
ADOBE_TERRACOTTA = "#7A2E1F"
MARIGOLD         = "#F2C14E"

# Three-band sarape stripe, as worn on the 1990s Fiesta-era uniforms
SARAPE_STRIPE = (
    f"linear-gradient({FIESTA_TEAL} 0 33.3%, {FIESTA_FUSCHIA} 33.3% 66.6%, {FIESTA_ORANGE} 66.6%)"
)
SARAPE_RIBBON = (
    f"repeating-linear-gradient(90deg, {FIESTA_TEAL} 0 60px, {FIESTA_FUSCHIA} 60px 120px, {FIESTA_ORANGE} 120px 180px)"
)

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
    'family=Alfa+Slab+One&'
    'family=Barlow+Condensed:wght@400;600;700;800&'
    'family=Bowlby+One&'
    'family=Courier+Prime:wght@400;700&'
    'family=Rye&'
    'family=Share+Tech+Mono&'
    'family=Teko:wght@500;600;700&'
    'family=VT323&display=swap" rel="stylesheet">'
)

# Single quotes inside: these are interpolated into style="..." attributes,
# where a double quote would end the attribute and silently drop the font.
FONT_DISPLAY = "'Bowlby One', sans-serif"       # chunky 90s italic headlines
FONT_HEADING = "'Teko', sans-serif"             # section & card titles
FONT_LED     = "'VT323', monospace"             # arena scoreboard numerals
FONT_WESTERN = "'Rye', serif"                   # Lotería card names
FONT_SLAB    = "'Alfa Slab One', serif"         # Lotería card numerals
FONT_TYPE    = "'Courier Prime', monospace"     # typewritten captions
FONT_STENCIL = "'Barlow Condensed', sans-serif"
FONT_TITLE   = "'Barlow Condensed', sans-serif"
FONT_MONO    = "'Share Tech Mono', monospace"
FONT_BODY    = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"

# ---------------------------------------------------------------------------
# Plotly Layout Standards
# ---------------------------------------------------------------------------
LAYOUT_BASE = dict(
    paper_bgcolor=SILVER_SLATE,
    plot_bgcolor=FROST_BANK_FLOOR,
    font=dict(color=COURT_WHITE, family="Share Tech Mono, monospace", size=12),
    title_font=dict(family="Teko, sans-serif", size=22, color=COURT_WHITE),
    xaxis=dict(gridcolor=COURT_LINE, zerolinecolor=COURT_LINE),
    yaxis=dict(gridcolor=COURT_LINE, zerolinecolor=COURT_LINE),
    margin=dict(l=60, r=30, t=50, b=50),
    legend=dict(
        bgcolor="rgba(0,0,0,0)",
        bordercolor=COURT_LINE,
        font=dict(family="Teko, sans-serif", size=16),
    ),
)

# Fans read these charts, they don't operate them: hover tooltips stay, the
# zoom/pan toolbar goes, and scroll-zoom is off so phones can scroll past charts.
PLOTLY_CONFIG = {
    "responsive": True,
    "displaylogo": False,
    "displayModeBar": False,
    "scrollZoom": False,
}


def chart_html(fig, div_id: str, include_plotlyjs: bool | str = False) -> str:
    """
    Embed a themed figure in a page. The surrounding section heading names the
    chart, so the figure's own title is dropped to avoid saying it twice.
    """
    import plotly.io as pio

    fig.update_layout(title=None, margin=dict(t=24))
    return pio.to_html(
        fig, full_html=False, include_plotlyjs=include_plotlyjs,
        div_id=div_id, config=PLOTLY_CONFIG,
    )


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
# Filenames are season-agnostic so shared links survive the yearly rollover;
# the current season (config.SEASON) always publishes to these names.
PAGES: dict[str, tuple[str, str]] = {
    "dashboard": ("dashboard.html",       "Dashboard"),
    "roster":    ("roster.html",          "Roster"),
    "wemby":     ("wemby_lab.html",       "Wemby Lab"),
    "rodeo":     ("rodeo_road_trip.html", "Rodeo Road Trip"),
    "notebook":  ("notebook.html",        "Notebook"),
    "matchup":   ("matchup.html",         "Next Game"),
    "board":     ("props_board.html",     "Props"),
}


# Early-season thresholds: trend charts need enough games to show a trend, and
# graded/percentage stats get a small-sample label until they settle.
MIN_TREND_GAMES = 10
MIN_GRADE_GAMES = 5
SMALL_SAMPLE_GAMES = 15


def small_sample_badge(text: str) -> str:
    """Inline label marking a stat as too early to read much into."""
    return f'<span class="badge small-sample" title="Small sample: expect this to move a lot">{text}</span>'


def early_season_note(games_played: int) -> str:
    """Page-level notice shown until the sample is large enough to trust rates and trends."""
    if games_played >= SMALL_SAMPLE_GAMES:
        return ""
    return (
        f'<div class="early-season" role="note"><strong>Early season:</strong> {games_played} '
        f'game{"s" if games_played != 1 else ""} played. Percentages and hit rates swing a lot this early; '
        f'trend charts appear after {MIN_TREND_GAMES} games.</div>'
    )


# Seasonal pages are still built (old links keep working) but are only featured
# in the nav and on the landing page inside their window: (month, day) inclusive.
SEASONAL_PAGES: dict[str, tuple[tuple[int, int], tuple[int, int]]] = {
    # Rodeo Road Trip: lead-up from mid-January, through the post-trip splits in April
    "rodeo": ((1, 15), (4, 30)),
}


def is_featured(slug: str, today: date | None = None) -> bool:
    """Whether a page should be surfaced in navigation right now."""
    window = SEASONAL_PAGES.get(slug)
    if window is None:
        return True
    today = today or date.today()
    (m1, d1), (m2, d2) = window
    return (m1, d1) <= (today.month, today.day) <= (m2, d2)


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


def nav_bar(current_slug: str, today: date | None = None) -> str:
    """One row of links: back to HQ, then every page that's in season."""
    links = ['<a href="index.html" class="nav-page index-link">← Spurs Stats HQ</a>']
    for slug, (filename, label) in PAGES.items():
        if slug == current_slug:
            links.append(f'<span class="nav-page current" aria-current="page">{label}</span>')
        elif is_featured(slug, today):
            links.append(f'<a href="{filename}" class="nav-page">{label}</a>')
    return f'<nav class="nav-bar"><div class="nav-pages">{" ".join(links)}</div></nav>'


# ---------------------------------------------------------------------------
# CSS Chrome Generator
# ---------------------------------------------------------------------------
def page_css() -> str:
    """Fiesta Night '94: Silver & Black base with 1990s Fiesta-uniform accents."""
    return f"""
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    html, body {{
      background:
        repeating-linear-gradient(135deg, rgba(255,255,255,0.012) 0 2px, transparent 2px 12px),
        {FROST_BANK_FLOOR};
      color: {COURT_WHITE};
      font-family: {FONT_BODY};
      min-height: 100vh;
      width: 100%;
      overflow-x: hidden;
      -webkit-text-size-adjust: 100%;
    }}
    .sarape-band {{
      height: 18px; background: {SARAPE_STRIPE};
      transform: skewY(-0.8deg); margin: 10px -20px 0;
    }}
    .page {{ padding: clamp(12px, 3vw, 28px); max-width: 1440px; margin: 0 auto; }}

    /* ---- Navigation ---- */
    .nav-bar {{ margin-bottom: 28px; }}
    .nav-pages {{ display: flex; flex-wrap: wrap; gap: 10px; }}
    @media (max-width: 640px) {{
      /* One swipeable row on phones instead of three wrapped rows */
      .nav-pages {{
        flex-wrap: nowrap; overflow-x: auto; scrollbar-width: none;
        padding: 2px 8px 8px 2px; margin: 0 -12px 0 0;
      }}
      .nav-pages::-webkit-scrollbar {{ display: none; }}
      .nav-page {{ flex: 0 0 auto; }}
    }}
    .nav-page {{
      color: {COURT_WHITE}; text-decoration: none;
      font-family: {FONT_HEADING}; font-size: 1.1rem; line-height: 1;
      font-weight: 600;
      letter-spacing: 0.08em; text-transform: uppercase;
      padding: 9px 14px 7px;
      background: {SILVER_SLATE};
      border: 2px solid {COURT_LINE};
      transition: transform 0.12s ease, box-shadow 0.12s ease, border-color 0.12s ease;
    }}
    a.nav-page:hover {{
      border-color: {COURT_WHITE}; transform: translate(-2px, -2px);
      box-shadow: 4px 4px 0 {FIESTA_TEAL};
    }}
    .nav-page.current {{
      background: {COURT_WHITE}; border-color: {COURT_WHITE}; color: {FROST_BANK_FLOOR};
      box-shadow: 4px 4px 0 {FIESTA_FUSCHIA};
      cursor: default;
    }}
    .nav-page.index-link {{ color: {MARIGOLD}; background: transparent; border-color: transparent; }}
    .nav-page.index-link:hover {{ box-shadow: none; transform: none; color: {COURT_WHITE}; }}

    /* ---- Alamo Heritage & Architecture ---- */
    .alamo-header-wrap {{ margin-bottom: 36px; position: relative; }}
    .alamo-roofline-crown {{
      width: clamp(140px, 30vw, 240px); height: 18px;
      margin: 0 auto -2px; display: block; position: relative; z-index: 2;
    }}
    .alamo-roofline-crown svg {{ width: 100%; height: 100%; display: block; }}
    .alamo-meta-banner {{
      display: inline-flex; align-items: center; gap: 8px;
      font-family: {FONT_HEADING}; font-size: 1.05rem; font-weight: 600; line-height: 1;
      letter-spacing: 0.22em; text-transform: uppercase; color: {FIESTA_ORANGE};
      margin-bottom: 12px;
    }}
    .alamo-icon-svg {{
      width: 22px; height: 12px; display: inline-block; vertical-align: middle;
      color: {FIESTA_ORANGE}; flex-shrink: 0;
    }}
    .alamo-footer-seal {{
      display: flex; justify-content: center; align-items: center; margin-bottom: 14px;
    }}
    .alamo-footer-seal .alamo-icon-svg {{ width: 44px; height: 22px; color: {SPURS_SILVER}; }}

    /* ---- Header ---- */
    header {{
      background: {SILVER_SLATE};
      border: 2px solid {COURT_WHITE};
      box-shadow: 8px 8px 0 {FIESTA_FUSCHIA}, 16px 16px 0 {FIESTA_TEAL};
      padding: clamp(18px, 3.5vw, 30px);
      position: relative;
      margin-right: 16px;
    }}
    header h1 {{
      display: flex; align-items: center; flex-wrap: wrap; gap: 10px 18px;
      line-height: 1;
    }}
    header h1 .title-text {{
      font-family: {FONT_DISPLAY};
      font-size: clamp(1.7rem, 5vw, 3.2rem);
      font-weight: 400;
      text-transform: uppercase;
      color: {COURT_WHITE};
      transform: skewX(-9deg);
      text-shadow: 3px 3px 0 {FIESTA_FUSCHIA}, 6px 6px 0 {FIESTA_TEAL};
    }}
    header h1 .badge {{
      font-family: {FONT_LED}; font-size: 1.35rem; line-height: 1;
      color: {FIESTA_ORANGE}; border: 2px solid {FIESTA_ORANGE}; background: transparent;
      padding: 3px 10px 1px; text-shadow: 0 0 10px rgba(255, 130, 0, 0.5);
    }}
    header p {{
      color: {SPURS_SILVER}; margin-top: 14px;
      font-size: clamp(0.9rem, 2vw, 1.05rem); line-height: 1.5;
    }}

    /* ---- Cards ---- */
    .chart-section, .card {{
      --accent: {FIESTA_TEAL};
      background: {SILVER_SLATE};
      border: 2px solid rgba(246, 248, 250, 0.85);
      padding: clamp(14px, 3vw, 22px);
      margin: 0 8px 32px 0;
      box-shadow: 8px 8px 0 var(--accent);
    }}
    .chart-section:nth-of-type(3n+2), .card:nth-of-type(3n+2) {{ --accent: {FIESTA_FUSCHIA}; }}
    .chart-section:nth-of-type(3n), .card:nth-of-type(3n) {{ --accent: {FIESTA_ORANGE}; }}
    .chart-title, .card h2 {{
      font-family: {FONT_HEADING};
      font-size: clamp(1.35rem, 3vw, 1.7rem);
      font-weight: 600; line-height: 1;
      color: {COURT_WHITE};
      text-transform: uppercase;
      letter-spacing: 0.06em;
      margin-bottom: 16px;
      padding-bottom: 10px;
      border-bottom: 2px dashed {COURT_LINE};
      display: flex; align-items: center; gap: 12px;
    }}
    .chart-title::before, .card h2::before {{
      content: ""; flex: 0 0 auto; width: 14px; height: 14px; margin-right: -2px;
      background: {SARAPE_STRIPE}; order: -1;
    }}
    .chart-title > :not(:first-child):last-child, .card h2 > :not(:first-child):last-child {{ margin-left: auto; }}

    /* ---- Badges ---- */
    .badge {{
      display: inline-block;
      font-family: {FONT_MONO};
      font-size: 0.75rem;
      padding: 3px 8px;
      background: {SHADOW_BLACK};
      border: 1px solid {SPURS_STEEL};
      color: {COURT_WHITE};
      text-transform: uppercase;
    }}
    .badge.teal {{ background: rgba(0, 178, 169, 0.15); border-color: {FIESTA_TEAL}; color: {FIESTA_TEAL}; }}
    .badge.fuschia {{ background: rgba(239, 66, 111, 0.15); border-color: {FIESTA_FUSCHIA}; color: {FIESTA_FUSCHIA}; }}
    .badge.small-sample {{
      font-family: {FONT_TYPE}; font-size: 0.72rem; text-transform: none; letter-spacing: 0;
      color: {MARIGOLD}; border: 1px dashed {MARIGOLD}; background: rgba(242, 193, 78, 0.08);
      white-space: normal; line-height: 1.35;
    }}
    .early-season {{
      border: 2px dashed {MARIGOLD}; background: rgba(242, 193, 78, 0.07); color: {COURT_WHITE};
      padding: 12px 16px; margin: 0 8px 28px 0; font-size: 0.92rem; line-height: 1.5;
    }}
    .early-season strong {{ color: {MARIGOLD}; font-family: {FONT_HEADING}; font-size: 1.15rem;
      font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; margin-right: 4px; }}
    .badge.orange {{ background: rgba(255, 130, 0, 0.15); border-color: {FIESTA_ORANGE}; color: {FIESTA_ORANGE}; }}

    /* ---- Footer ---- */
    footer {{
      text-align: center; color: {TEXT_MUTED};
      font-size: 0.85rem; margin-top: 56px; padding-top: 28px;
      position: relative;
    }}
    footer::before {{
      content: ""; position: absolute; top: 0; left: 0; right: 0; height: 8px;
      background: {SARAPE_RIBBON};
    }}
    footer .credit {{
      font-family: {FONT_HEADING}; font-size: 1.35rem; font-weight: 600; line-height: 1.1;
      letter-spacing: 0.08em; text-transform: uppercase; color: {COURT_WHITE};
    }}
    footer .links {{ margin-top: 8px; font-family: {FONT_TYPE}; font-size: 0.85rem; }}
    footer .links span {{ margin: 0 8px; color: {TEXT_MUTED}; }}
    footer a {{ color: {MARIGOLD}; text-decoration: none; }}
    footer a:hover, footer a:focus-visible {{ text-decoration: underline; }}

    @media (max-width: 640px) {{
      header {{ box-shadow: 6px 6px 0 {FIESTA_FUSCHIA}, 12px 12px 0 {FIESTA_TEAL}; margin-right: 12px; }}
      .chart-section, .card {{ box-shadow: 6px 6px 0 var(--accent); margin-right: 6px; }}
    }}
    {_avatar_css()}
    """


def _avatar_css() -> str:
    from viz.avatars import avatar_css  # avatars imports theme, so resolve at call time
    return avatar_css()


def share_meta(title: str, description: str, image: str = "latest") -> str:
    """Open Graph / Twitter tags so shared links unfurl with a preview card."""
    import html as _html
    import re as _re
    from viz.share_images import og_image_url  # share_images imports theme

    desc = _html.escape(_html.unescape(_re.sub(r"<[^>]+>", "", description)).strip(), quote=True)
    title = _html.escape(_html.unescape(title), quote=True)
    url = og_image_url(image)
    tags = [
        f'<meta name="description" content="{desc}">',
        '<meta property="og:type" content="website">',
        '<meta property="og:site_name" content="Spurs Stats HQ">',
        f'<meta property="og:title" content="{title}">',
        f'<meta property="og:description" content="{desc}">',
        f'<meta name="twitter:title" content="{title}">',
        f'<meta name="twitter:description" content="{desc}">',
    ]
    if url:
        tags += [
            f'<meta property="og:image" content="{url}">',
            '<meta property="og:image:width" content="1200">',
            '<meta property="og:image:height" content="630">',
            '<meta name="twitter:card" content="summary_large_image">',
            f'<meta name="twitter:image" content="{url}">',
        ]
    else:
        tags.append('<meta name="twitter:card" content="summary">')
    return "\n  ".join(tags)


def page_footer() -> str:
    """Standard footer: Alamo seal, author credit and links."""
    return f"""
    <footer>
      <div class="alamo-footer-seal" aria-hidden="true">
        {ALAMO_ICON_SVG}
      </div>
      <p class="credit">Created and Maintained by <a href="https://www.corygarms.com" target="_blank" rel="noopener">Cory Garms</a></p>
      <p class="links">
        <a href="https://x.com/cory_garms" target="_blank" rel="noopener">X / Twitter @cory_garms</a>
        <span aria-hidden="true">&bull;</span>
        <a href="https://github.com/cory-garms" target="_blank" rel="noopener">GitHub cory-garms</a>
      </p>
    </footer>
    """


def page_html(
    title: str,
    subtitle: str,
    body_content: str,
    current_slug: str = "dashboard",
    badge: str = f"{config.season_str(config.SEASON)} Season",
    games_played: int | None = None,
    og_image: str = "latest",
) -> str:
    """Wrap content in the official Spurs HTML shell."""
    note = early_season_note(games_played) if games_played is not None else ""
    share = share_meta(f"{title} · Spurs Stats HQ", subtitle, og_image)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} — San Antonio Spurs Analytics</title>
  {share}
  {FONTS_LINK}
  <style>
{page_css()}
  </style>
</head>
<body>
  <div class="sarape-band" aria-hidden="true"></div>
  <div class="page">
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
      <h1><span class="title-text">{title}</span> <span class="badge">{badge}</span></h1>
      <p>{subtitle}</p>
    </header>
  </div>
  <main>
    {note}
    {body_content}
  </main>
  {page_footer()}
  </div>
</body>
</html>
"""
