"""
Rodeo Road Trip Visualizer — Builds the interactive Rodeo Road Trip web portal.

Generates docs/rodeo_road_trip.html with full Plotly figures,
split comparisons, historical franchise road trip benchmarks, and the official Spurs theme shell.
"""

from __future__ import annotations

from pathlib import Path
import pandas as pd
import plotly.graph_objects as go

import config
from config import TEAM_ABBR, SEASON, season_str
from viz import theme
from analysis.rodeo import (
    segment_rodeo_games,
    rodeo_split_metrics,
    historical_rodeo_comparison,
    HISTORICAL_RODEO_BENCHMARKS,
)


def rodeo_margin_trajectory(segmented_games: pd.DataFrame) -> go.Figure:
    """Cumulative margin trajectory for games in the Active Rodeo Road Trip."""
    if segmented_games.empty:
        return go.Figure()

    rrt = segmented_games[
        (segmented_games["rodeo_split"] == "Active RRT") &
        (segmented_games["status"] == "Final")
    ].sort_values("game_date").reset_index(drop=True)

    if rrt.empty:
        # If no active RRT games finalized yet, show all away games in February or full season road games
        rrt = segmented_games[
            (segmented_games["home_away"] == "A") &
            (segmented_games["status"] == "Final")
        ].sort_values("game_date").reset_index(drop=True)

    if rrt.empty:
        return go.Figure()

    rrt["cum_margin"] = rrt["margin"].cumsum()
    rrt["game_n"] = range(1, len(rrt) + 1)
    colors = [theme.FIESTA_TEAL if m >= 0 else theme.FIESTA_FUSCHIA for m in rrt["margin"]]

    fig = go.Figure()

    # Per-game margin bar
    fig.add_trace(go.Bar(
        x=[f"G{i} ({r.get('opponent_abbr', '')})" for i, r in zip(rrt["game_n"], rrt.to_dict("records"))],
        y=rrt["margin"],
        name="Game Margin",
        marker_color=colors,
        hovertemplate="%{x}<br>Margin: %{y:+d}<extra></extra>",
    ))

    # Cumulative margin line
    fig.add_trace(go.Scatter(
        x=[f"G{i} ({r.get('opponent_abbr', '')})" for i, r in zip(rrt["game_n"], rrt.to_dict("records"))],
        y=rrt["cum_margin"],
        name="Cumulative Margin",
        mode="lines+markers",
        line=dict(color=theme.SPURS_SILVER, width=3),
        marker=dict(size=8, color=theme.FIESTA_ORANGE),
        hovertemplate="%{x}<br>Cumulative: %{y:+d}<extra></extra>",
    ))

    fig.add_hline(y=0, line_color=theme.COURT_LINE, line_width=1.5)

    theme.apply(
        fig,
        title=dict(text="Rodeo Road Trip — Game-by-Game Score Margin Trajectory", font=dict(size=16)),
        xaxis_title="Road Trip Game",
        yaxis_title="Margin (Points)",
    )
    return fig


def historical_rodeo_chart(current_rrt: dict) -> go.Figure:
    """Bar chart comparing historical Spurs rodeo trips against the current season."""
    df = historical_rodeo_comparison(current_rrt)
    if df.empty:
        return go.Figure()

    colors = [
        theme.FIESTA_ORANGE if row["season"] == "Current Season"
        else (theme.FIESTA_TEAL if "🏆" in str(row.get("result", "")) else theme.SPURS_SILVER)
        for _, row in df.iterrows()
    ]

    fig = go.Figure(go.Bar(
        x=df["season"],
        y=df["win_pct"],
        marker_color=colors,
        text=df.apply(lambda r: f"{r['record']} ({r['win_pct']:.3f})", axis=1),
        textposition="outside",
        hovertemplate="%{x}<br>Record: %{text}<br>%{y:.3f} Win%<extra></extra>",
    ))

    fig.add_hline(
        y=0.500,
        line_dash="dot",
        line_color=theme.TEXT_MUTED,
        annotation_text=".500 Baseline",
        annotation_position="bottom right",
    )

    theme.apply(
        fig,
        title=dict(text="Crucible of Champions: Historical Rodeo Road Trip Win%", font=dict(size=16)),
        xaxis_title="Franchise Season",
        yaxis_title="Win Percentage",
        yaxis_range=[0, 1.15],
    )
    return fig


def split_ratings_chart(splits: dict) -> go.Figure:
    """Grouped bar chart comparing Net Rating across Pre-RRT, Active RRT, Post-RRT."""
    if not splits:
        return go.Figure()

    split_names = [s for s in ["Pre-RRT", "Active RRT", "Post-RRT"] if splits.get(s, {}).get("games", 0) > 0]
    if not split_names:
        split_names = ["Pre-RRT", "Active RRT", "Post-RRT"]

    net_rtgs = [splits.get(s, {}).get("net_rtg", 0.0) for s in split_names]
    margins = [splits.get(s, {}).get("avg_margin", 0.0) for s in split_names]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=split_names,
        y=net_rtgs,
        name="Net Rating",
        marker_color=[theme.FIESTA_TEAL if v >= 0 else theme.FIESTA_FUSCHIA for v in net_rtgs],
        text=[f"{v:+.1f}" for v in net_rtgs],
        textposition="outside",
        hovertemplate="%{x}<br>Net Rating: %{y:+.1f}<extra></extra>",
    ))

    fig.add_trace(go.Bar(
        x=split_names,
        y=margins,
        name="Average Margin / Game",
        marker_color=theme.SPURS_SILVER,
        text=[f"{v:+.1f}" for v in margins],
        textposition="outside",
        hovertemplate="%{x}<br>Avg Margin: %{y:+.1f}<extra></extra>",
    ))

    fig.add_hline(y=0, line_color=theme.COURT_LINE, line_width=1.5)

    theme.apply(
        fig,
        barmode="group",
        title=dict(text="Seasonal Fatigue: Rating & Margin by Phase", font=dict(size=16)),
        yaxis_title="Rating / Margin Differential",
    )
    return fig


def build_rodeo_page(
    games: pd.DataFrame,
    season: int = SEASON,
    team_abbr: str = TEAM_ABBR,
    output_path: Path | None = None,
) -> Path:
    """Build and write the interactive Rodeo Road Trip HTML page."""
    if output_path is None:
        output_path = theme.page_path("rodeo", team_abbr, season)

    segmented = segment_rodeo_games(games)
    splits = rodeo_split_metrics(segmented)
    active_m = splits.get("Active RRT", {})

    # 1. Phase KPI Cards
    def _card(title, data, accent_color):
        g = data.get("games", 0)
        rec = data.get("record", "--")
        pct = f"{data.get('win_pct', 0.0):.3f}" if g > 0 else "--"
        net = f"{data.get('net_rtg', 0.0):+.1f}" if g > 0 else "--"
        ppg = f"{data.get('ppg', 0.0):.1f}" if g > 0 else "--"
        opp = f"{data.get('opp_ppg', 0.0):.1f}" if g > 0 else "--"
        return f"""
        <div class="card" style="margin-bottom: 0; border-top: 3px solid {accent_color};">
          <div style="font-family: {theme.FONT_MONO}; font-size: 0.75rem; color: {accent_color}; text-transform: uppercase; letter-spacing: 0.1em;">{title}</div>
          <div style="font-family: {theme.FONT_LED}; font-size: 3.2rem; color: {theme.COURT_WHITE}; margin: 4px 0 2px;">{rec}</div>
          <div style="font-family: {theme.FONT_MONO}; font-size: 0.85rem; color: {theme.TEXT_MUTED};">Win%: {pct} &bull; Net: {net}</div>
          <div style="font-size: 0.8rem; color: {theme.COURT_WHITE}; margin-top: 8px; border-top: 1px solid {theme.COURT_LINE}; padding-top: 6px;">
            PPG: {ppg} &bull; Opp PPG: {opp}
          </div>
        </div>
        """

    cards_html = f"""
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; margin-bottom: 24px;">
      {_card("Phase 1: Pre-RRT (Oct – Jan)", splits.get("Pre-RRT", {}), theme.SPURS_SILVER)}
      {_card("Phase 2: Active Rodeo Road Trip (Feb)", splits.get("Active RRT", {}), theme.FIESTA_ORANGE)}
      {_card("Phase 3: Post-RRT (Mar – Apr)", splits.get("Post-RRT", {}), theme.FIESTA_TEAL)}
    </div>
    """

    # 2. Charts
    fig_margin = rodeo_margin_trajectory(segmented)
    fig_hist = historical_rodeo_chart(active_m)
    fig_ratings = split_ratings_chart(splits)

    fig_margin.update_layout(height=420)
    fig_hist.update_layout(height=400)
    fig_ratings.update_layout(height=400)

    div_margin = theme.chart_html(fig_margin, "rodeo_margin_chart", include_plotlyjs="cdn")
    div_hist = theme.chart_html(fig_hist, "rodeo_historical_chart", include_plotlyjs=False)
    div_ratings = theme.chart_html(fig_ratings, "rodeo_ratings_chart", include_plotlyjs=False)

    # 3. Historical Benchmark Table
    bench_rows = ""
    for h in HISTORICAL_RODEO_BENCHMARKS:
        bench_rows += f"""
        <tr style="border-bottom: 1px solid {theme.COURT_LINE};">
          <td style="padding: 10px 12px; font-family: {theme.FONT_MONO};">{h['season']}</td>
          <td style="padding: 10px 12px; font-weight: 700; color: {theme.FIESTA_TEAL};">{h['record']}</td>
          <td style="padding: 10px 12px; font-family: {theme.FONT_MONO};">{h['win_pct']:.3f}</td>
          <td style="padding: 10px 12px; color: {theme.TEXT_MUTED};">{h['result']}</td>
        </tr>
        """

    hist_table = f"""
    <div class="card">
      <h2>🤠 Historical Rodeo Road Trip Standard (2003–Present)</h2>
      <div style="overflow-x: auto;">
        <table style="width: 100%; border-collapse: collapse; font-size: 0.9rem; text-align: left;">
          <thead>
            <tr style="border-bottom: 2px solid {theme.COURT_LINE}; color: {theme.SPURS_SILVER}; font-family: {theme.FONT_STENCIL}; text-transform: uppercase;">
              <th style="padding: 10px 12px;">Season</th>
              <th style="padding: 10px 12px;">RRT Record</th>
              <th style="padding: 10px 12px;">Win%</th>
              <th style="padding: 10px 12px;">Championship Context</th>
            </tr>
          </thead>
          <tbody>
            {bench_rows}
          </tbody>
        </table>
      </div>
    </div>
    """

    body_content = f"""
    {cards_html}

    <section class="chart-section">
      <h2 class="chart-title">🚚 Rodeo Road Trip: Point Differential & Fatigue Curve</h2>
      {div_margin}
    </section>

    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(460px, 1fr)); gap: 20px;">
      <section class="chart-section" style="margin-bottom: 0;">
        <h2 class="chart-title">🏆 Historical Rodeo Benchmark Standards</h2>
        {div_hist}
      </section>

      <section class="chart-section" style="margin-bottom: 0;">
        <h2 class="chart-title">📊 Seasonal Split Rating Differential</h2>
        {div_ratings}
      </section>
    </div>
    <div style="height: 24px;"></div>

    {hist_table}
    """

    season_s = season_str(season)
    html = theme.page_html(
        title="Rodeo Road Trip",
        subtitle="The February road trip, game by game, against the championship-era trips since 2003.",
        body_content=body_content,
        current_slug="rodeo",
        badge=f"{season_s} Gauntlet",
        games_played=int((games["status"] == "Final").sum()) if not games.empty else 0,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path
