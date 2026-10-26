"""
Spurs Notebook Visualizer — Builds the interactive living essay notebook web portal.

Generates docs/notebook.html with dynamically evaluated essays from
blog/posts.py, with zero hardcoded statistics, adhering to the Spurs theme system.
"""

from __future__ import annotations

from pathlib import Path
import pandas as pd

import config
from config import TEAM_ABBR, SEASON, season_str
from viz import theme
from analysis.wemby import get_wemby_logs
from analysis.standings import season_record
from blog.posts import get_all_posts


def build_notebook_page(
    games: pd.DataFrame,
    player_logs: pd.DataFrame,
    roster: pd.DataFrame,
    season: int = SEASON,
    team_abbr: str = TEAM_ABBR,
    output_path: Path | None = None,
) -> Path:
    """Build and write the Spurs Notebook living essays HTML page."""
    if output_path is None:
        output_path = theme.page_path("notebook", team_abbr, season)

    # Assemble context for build-time evaluation
    ctx = {
        "games": games,
        "player_logs": player_logs,
        "roster": roster,
        "wemby_logs": get_wemby_logs(player_logs),
        "season_record": season_record(games),
        "season": season,
        "team_abbr": team_abbr,
    }

    posts = get_all_posts(ctx)

    articles_html = ""
    for post in posts:
        slug = post["slug"]
        title = post["title"]
        category = post["category"]
        date = post["date"]
        content = post["html"]

        badge_class = "teal" if "Gravity" in category else ("orange" if "Road" in category else "silver")

        articles_html += f"""
        <article class="card" id="{slug}" style="padding: clamp(20px, 4vw, 36px); margin-bottom: 32px; border-left: 4px solid {theme.SPURS_SILVER};">
          <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px; margin-bottom: 12px;">
            <span class="badge {badge_class}">{category}</span>
            <span style="font-family: {theme.FONT_MONO}; font-size: 0.8rem; color: {theme.TEXT_MUTED};">{date}</span>
          </div>

          <h2 style="font-family: {theme.FONT_STENCIL}; font-size: clamp(1.4rem, 3vw, 2.0rem); color: {theme.COURT_WHITE}; border-bottom: 1px solid {theme.COURT_LINE}; padding-bottom: 12px; margin-bottom: 18px; line-height: 1.25;">
            {title}
          </h2>

          <div class="essay-body" style="color: #C4CED4; font-size: 1.05rem; line-height: 1.75;">
            {content}
          </div>
        </article>
        """

    hero_intro = f"""
    <div class="card" style="background: linear-gradient(180deg, {theme.SILVER_SLATE} 0%, {theme.SHADOW_BLACK} 100%); border-top: 3px solid {theme.FIESTA_TEAL}; margin-bottom: 32px;">
      <h2 style="border-bottom: none; font-size: 1.3rem; margin-bottom: 8px;">The Living Notebook &bull; Computed at Build Time</h2>
      <p style="color: {theme.TEXT_MUTED}; line-height: 1.6; font-size: 0.95rem;">
        Every essay in this ledger adheres to the immutable Spurs Tracker rule: <strong>zero hand-typed numbers</strong>.
        Every metric, defensive rating delta, and win percentage cited is evaluated directly against the underlying
        Parquet cache at page build time. As the season evolves, the narrative shifts with the data.
      </p>
    </div>
    """

    body_content = f"""
    {hero_intro}
    <div class="articles-container">
      {articles_html}
    </div>
    """

    season_s = season_str(season)
    html = theme.page_html(
        title="Spurs Notebook",
        subtitle="Living Essays in Silver & Black Performance Analytics &mdash; Computed Dynamically at Build Time",
        body_content=body_content,
        current_slug="notebook",
        badge=f"{season_s} Essays",
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path
