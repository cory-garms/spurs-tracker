"""
Combined Plotly dashboard — assembles all charts into one self-contained HTML file.

Usage:
    python viz_report.py --team SAS --season 2024
    # → output/dashboard_SAS_2024.html

CDN note: include_plotlyjs="cdn" is set ONLY on the first figure so the Plotly
version always matches the installed package.  Never hardcode a CDN version string.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

from config import OUTPUT_DIR, TEAM_ABBR, SEASON
from viz.charts import (
    _apply_theme, _BG, _PAPER_BG, _GRID, _TEXT, _GREEN, _RED, _BLUE, _YELLOW, _DIM,
    season_timeline,
    rolling_win_pct_chart,
    score_margin_chart,
    streak_timeline_chart,
    scoring_trend_chart,
    player_scoring_leaderboard,
    hot_cold_chart,
    shot_efficiency_chart,
    defensive_rating_trend,
)


# ---------------------------------------------------------------------------
# Full dashboard
# ---------------------------------------------------------------------------

def build(
    games: pd.DataFrame,
    player_logs: pd.DataFrame,
    team_name: str,
    team_abbr: str = TEAM_ABBR,
    season: int = SEASON,
    output_path: Path | None = None,
) -> Path:
    """
    Build and write the full interactive HTML dashboard.

    Sections (top to bottom):
      1.  Season Timeline
      2.  Rolling Win% (5-game, 10-game)
      3.  Score Margin per Game
      4.  Streak Timeline
      5.  Scoring Trend (pts + opp_pts rolling)
      6.  Player Scoring Leaderboard (heatmap)
      7.  Hot / Cold Tracker
      8.  Shot Efficiency (usg% vs TS%)
      9.  Defensive Rating Trend

    Returns the path to the written HTML file.
    """
    from analysis.offense import hot_cold_summary
    from analysis.streaks import streak_timeline

    if output_path is None:
        output_path = OUTPUT_DIR / f"dashboard_{team_abbr}_{season}.html"

    figures: list[tuple[str, go.Figure, int]] = []

    # 1. Season timeline
    fig1 = season_timeline(games, team_name)
    figures.append(("Season Timeline", fig1, 420))

    # 2. Rolling win%
    fig2 = rolling_win_pct_chart(games, team_name, windows=[5, 10])
    figures.append(("Rolling Win%", fig2, 380))

    # 3. Score margin
    fig3 = score_margin_chart(games, team_name)
    figures.append(("Score Margin per Game", fig3, 420))

    # 4. Streak timeline
    streak_df = streak_timeline(games)
    fig4 = streak_timeline_chart(streak_df, team_name)
    figures.append(("Streak Timeline", fig4, 320))

    # 5. Scoring trend
    fig5 = scoring_trend_chart(games, team_name, window=10)
    figures.append(("Scoring Trend", fig5, 380))

    # 6. Player leaderboard heatmap
    if not player_logs.empty:
        fig6 = player_scoring_leaderboard(player_logs, team_name)
        if fig6.data:
            from analysis.offense import player_season_averages
            n_players = len(player_season_averages(player_logs, min_games=10))
            figures.append(("Player Scoring Leaderboard", fig6, max(400, n_players * 30 + 100)))

    # 7. Hot / cold
    if not player_logs.empty:
        hc = hot_cold_summary(player_logs, windows=[5, 10], min_games=10)
        if not hc.empty:
            fig7 = hot_cold_chart(hc, team_name)
            figures.append(("Hot / Cold Tracker", fig7, max(380, len(hc) * 25 + 100)))

    # 8. Shot efficiency
    if not player_logs.empty:
        fig8 = shot_efficiency_chart(player_logs, team_name)
        if fig8.data:
            figures.append(("Shot Efficiency (USG% vs TS%)", fig8, 520))

    # 9. Defensive rating trend
    if "drtg" in games.columns and games["drtg"].notna().any():
        fig9 = defensive_rating_trend(games, team_name)
        if fig9.data:
            figures.append(("Defensive Rating Trend", fig9, 380))

    # -----------------------------------------------------------------------
    # Assemble HTML
    # CDN fix: include_plotlyjs="cdn" only on first figure — version always
    # matches installed plotly package, avoids blank-chart regression.
    # -----------------------------------------------------------------------
    import plotly.io as pio

    divs_html = ""
    for i, (title, fig, height) in enumerate(figures):
        div_id    = title.lower().replace(" ", "_").replace("/", "_").replace("%", "pct")
        # Embed the full Plotly.js bundle on the first figure so binary-encoded
        # array data (dtype/bdata) is decoded by the exact matching JS version.
        # "cdn" risks version mismatch when cdn.plot.ly lags the installed package.
        include_js = True if i == 0 else False
        fig.update_layout(height=height)
        chart_div = pio.to_html(
            fig, full_html=False, include_plotlyjs=include_js, div_id=div_id
        )
        divs_html += f"""
        <section class="chart-section">
            <h2 class="chart-title">{title}</h2>
            {chart_div}
        </section>
        """

    season_s = f"{season}-{str(season + 1)[-2:]}"
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{team_name} — {season_s} Dashboard</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: {_BG};
      color: {_TEXT};
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", monospace;
      padding: 24px;
    }}
    header {{
      border-bottom: 1px solid {_GRID};
      padding-bottom: 16px;
      margin-bottom: 32px;
    }}
    header h1 {{ font-size: 1.8rem; color: {_TEXT}; }}
    header p  {{ color: {_DIM}; margin-top: 4px; font-size: 0.9rem; }}
    .chart-section {{
      background: {_PAPER_BG};
      border: 1px solid {_GRID};
      border-radius: 8px;
      padding: 20px;
      margin-bottom: 24px;
    }}
    .chart-title {{
      font-size: 1rem;
      font-weight: 600;
      color: {_DIM};
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 12px;
    }}
    footer {{
      text-align: center;
      color: {_DIM};
      font-size: 0.8rem;
      margin-top: 40px;
      padding-top: 16px;
      border-top: 1px solid {_GRID};
    }}
    footer a {{ color: {_BLUE}; text-decoration: none; }}
  </style>
</head>
<body>
  <header>
    <h1>{team_name} — {season_s} Season Dashboard</h1>
    <p>Data: NBA Stats API &nbsp;|&nbsp;
       Built with <a href="https://github.com/cgarms/spurs-tracker">spurs-tracker</a></p>
  </header>

  {divs_html}

  <footer>
    <p>Generated by <a href="https://github.com/cgarms/spurs-tracker">spurs-tracker</a>
    &mdash; data via <a href="https://stats.nba.com">NBA Stats API</a></p>
  </footer>
</body>
</html>"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path


# ---------------------------------------------------------------------------
# PNG exports
# ---------------------------------------------------------------------------

def build_png_exports(
    games: pd.DataFrame,
    player_logs: pd.DataFrame,
    team_name: str,
    team_abbr: str = TEAM_ABBR,
    season: int = SEASON,
) -> list[Path]:
    """Export key charts as static PNGs. Requires kaleido: pip install kaleido"""
    from analysis.streaks import streak_timeline
    from viz.exports import save_png

    out_dir = OUTPUT_DIR / "img"
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    exports = [
        ("timeline",    season_timeline(games, team_name),                        1200, 500),
        ("rolling_win", rolling_win_pct_chart(games, team_name),                  1200, 450),
        ("margin",      score_margin_chart(games, team_name),                     1200, 500),
        ("streak",      streak_timeline_chart(streak_timeline(games), team_name), 1200, 350),
    ]

    if not player_logs.empty:
        exports.append((
            "player_heatmap",
            player_scoring_leaderboard(player_logs, team_name),
            1200, 500,
        ))

    for name, fig, w, h in exports:
        path = out_dir / f"{team_abbr}_{season}_{name}.png"
        try:
            written.append(save_png(fig, path, width=w, height=h))
        except Exception as e:
            print(f"PNG export failed for {name}: {e} (is kaleido installed?)")

    return written
