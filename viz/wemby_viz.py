"""
Wemby Lab Visualizer — Builds the interactive Wemby Lab web portal.

Generates docs/wemby_lab.html with full Plotly figures,
defensive deterrence splits, stocks milestones, and the official Spurs theme shell.
"""

from __future__ import annotations

from pathlib import Path
import pandas as pd
import plotly.graph_objects as go

import config
from config import TEAM_ABBR, SEASON, season_str
from viz import theme
from analysis.wemby import (
    get_wemby_logs,
    stocks_distribution,
    defensive_impact_summary,
    offensive_gravity_summary,
)


def wemby_stocks_timeline(wemby_logs: pd.DataFrame) -> go.Figure:
    """Timeline of steals and blocks per game with rolling stocks average."""
    if wemby_logs.empty:
        return go.Figure()

    fig = go.Figure()

    # Blocks bar
    fig.add_trace(go.Bar(
        x=wemby_logs["game_date"],
        y=wemby_logs["blk"],
        name="Blocks",
        marker_color=theme.FIESTA_TEAL,
        hovertemplate="%{x}<br>Blocks: %{y}<extra></extra>",
    ))

    # Steals bar
    fig.add_trace(go.Bar(
        x=wemby_logs["game_date"],
        y=wemby_logs["stl"],
        name="Steals",
        marker_color=theme.SPURS_SILVER,
        hovertemplate="%{x}<br>Steals: %{y}<extra></extra>",
    ))

    # Rolling 5-game stocks
    fig.add_trace(go.Scatter(
        x=wemby_logs["game_date"],
        y=wemby_logs["roll5_stocks"],
        name="5-Game Rolling Stocks",
        mode="lines",
        line=dict(color=theme.FIESTA_ORANGE, width=2.5),
        hovertemplate="%{x}<br>Rolling Stocks: %{y:.2f}<extra></extra>",
    ))

    # Elite 5.0 stocks threshold
    fig.add_hline(
        y=5.0,
        line_dash="dot",
        line_color=theme.FIESTA_ORANGE,
        annotation_text="5.0 Stocks (DPOY Benchmark)",
        annotation_position="top left",
    )

    theme.apply(
        fig,
        barmode="stack",
        title=dict(text="Victor Wembanyama — Game-by-Game Stocks (Steals + Blocks)", font=dict(size=16)),
        xaxis_title="Game Date",
        yaxis_title="Count",
    )
    return fig


def deterrence_split_chart(impact: dict) -> go.Figure:
    """Compare Defensive Rating and Opponent PPG when Wemby has 5+ stocks vs <5 stocks."""
    if not impact or impact.get("total_tracked_games", 0) == 0:
        return go.Figure()

    categories = ["High Stocks (5+)", "Baseline (<5)"]
    drtg_values = [impact["high_stocks_drtg"], impact["regular_stocks_drtg"]]
    opp_pts_values = [impact["high_stocks_opp_pts"], impact["regular_stocks_opp_pts"]]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=categories,
        y=drtg_values,
        name="Team Defensive Rating",
        marker_color=[theme.FIESTA_TEAL, theme.FIESTA_FUSCHIA],
        text=[f"{v:.1f}" for v in drtg_values],
        textposition="outside",
        hovertemplate="%{x}<br>DRtg: %{y:.1f}<extra></extra>",
    ))

    fig.add_trace(go.Bar(
        x=categories,
        y=opp_pts_values,
        name="Opponent PPG Allowed",
        marker_color=[theme.SPURS_SILVER, theme.TEXT_MUTED],
        text=[f"{v:.1f}" for v in opp_pts_values],
        textposition="outside",
        hovertemplate="%{x}<br>Opp PPG: %{y:.1f}<extra></extra>",
    ))

    theme.apply(
        fig,
        barmode="group",
        title=dict(text="Alien Deterrence: Team Defense Split by Wemby Activity", font=dict(size=16)),
        yaxis_title="Points / Rating (Lower is Better)",
        yaxis_range=[90, max(drtg_values + opp_pts_values) + 15],
    )
    return fig


def milestone_frequency_chart(stocks: dict) -> go.Figure:
    """Frequency of rare milestone defensive achievements."""
    if not stocks or stocks.get("games", 0) == 0:
        return go.Figure()

    tiers = [
        "3+ Blocks",
        "5+ Blocks",
        "7+ Blocks",
        "5+ Stocks",
        "8+ Stocks",
    ]
    counts = [
        stocks["games_3plus_blk"],
        stocks["games_5plus_blk"],
        stocks["games_7plus_blk"],
        stocks["games_5plus_stocks"],
        stocks["games_8plus_stocks"],
    ]
    pcts = [round(c / stocks["games"] * 100, 1) for c in counts]

    fig = go.Figure(go.Bar(
        x=tiers,
        y=counts,
        marker_color=[theme.FIESTA_TEAL, theme.FIESTA_TEAL, theme.FIESTA_ORANGE, theme.SPURS_SILVER, theme.FIESTA_ORANGE],
        text=[f"{c} games ({p}%)" for c, p in zip(counts, pcts)],
        textposition="outside",
        hovertemplate="%{x}<br>%{y} games<extra></extra>",
    ))

    theme.apply(
        fig,
        title=dict(text="Defensive Horizon: Rare Milestone Frequency", font=dict(size=16)),
        yaxis_title="Games Achieved",
        yaxis_range=[0, max(counts) * 1.25 + 1],
    )
    return fig


def build_wemby_lab_page(
    games: pd.DataFrame,
    player_logs: pd.DataFrame,
    season: int = SEASON,
    team_abbr: str = TEAM_ABBR,
    output_path: Path | None = None,
) -> Path:
    """Build and write the interactive Wemby Lab HTML page."""
    if output_path is None:
        output_path = theme.page_path("wemby", team_abbr, season)

    wemby = get_wemby_logs(player_logs)
    if wemby.empty:
        html = theme.page_html(
            title="Wemby Lab",
            subtitle="Victor Wembanyama Defensive & Gravity Lab",
            body_content="<div class='card'><h2>No Player Data Found</h2><p>Victor Wembanyama logs not found in cache.</p></div>",
            current_slug="wemby",
        )
        output_path.write_text(html, encoding="utf-8")
        return output_path

    stocks = stocks_distribution(wemby)
    impact = defensive_impact_summary(games, wemby)
    offense = offensive_gravity_summary(wemby)

    # 1. KPI Metric Banner
    kpi_cards = f"""
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px;">
      <div class="card" style="margin-bottom: 0; text-align: center;">
        <div style="font-family: {theme.FONT_MONO}; font-size: 0.8rem; color: {theme.TEXT_MUTED}; text-transform: uppercase;">Points Per Game</div>
        <div style="font-family: {theme.FONT_LED}; font-size: 3.4rem; color: {theme.COURT_WHITE}; line-height: 1.1;">{offense['ppg']:.1f}</div>
        <div style="font-size: 0.78rem; color: {theme.FIESTA_TEAL}; font-family: {theme.FONT_MONO};">TS%: {offense['true_shooting_pct']:.3f} | eFG%: {offense['effective_fg_pct']:.3f}</div>
      </div>
      <div class="card" style="margin-bottom: 0; text-align: center;">
        <div style="font-family: {theme.FONT_MONO}; font-size: 0.8rem; color: {theme.TEXT_MUTED}; text-transform: uppercase;">Blocks Per Game</div>
        <div style="font-family: {theme.FONT_LED}; font-size: 3.4rem; color: {theme.FIESTA_TEAL}; line-height: 1.1;">{stocks['blocks_per_game']:.2f}</div>
        <div style="font-size: 0.78rem; color: {theme.TEXT_MUTED}; font-family: {theme.FONT_MONO};">Total Blocks: {stocks['total_blocks']}</div>
      </div>
      <div class="card" style="margin-bottom: 0; text-align: center;">
        <div style="font-family: {theme.FONT_MONO}; font-size: 0.8rem; color: {theme.TEXT_MUTED}; text-transform: uppercase;">Stocks (STL + BLK)</div>
        <div style="font-family: {theme.FONT_LED}; font-size: 3.4rem; color: {theme.SPURS_SILVER}; line-height: 1.1;">{stocks['stocks_per_game']:.2f}</div>
        <div style="font-size: 0.78rem; color: {theme.FIESTA_ORANGE}; font-family: {theme.FONT_MONO};">Per 36 Min: {stocks['stocks_per_36']:.2f}</div>
      </div>
      <div class="card" style="margin-bottom: 0; text-align: center;">
        <div style="font-family: {theme.FONT_MONO}; font-size: 0.8rem; color: {theme.TEXT_MUTED}; text-transform: uppercase;">5x5 Watch</div>
        <div style="font-family: {theme.FONT_LED}; font-size: 3.4rem; color: {theme.FIESTA_ORANGE}; line-height: 1.1;">{stocks['five_by_fives']}</div>
        <div style="font-size: 0.78rem; color: {theme.TEXT_MUTED}; font-family: {theme.FONT_MONO};">Near Misses (5x4): {stocks['five_by_fours']}</div>
      </div>
    </div>
    """

    # 2. Charts
    fig_stocks = wemby_stocks_timeline(wemby)
    fig_impact = deterrence_split_chart(impact)
    fig_milestones = milestone_frequency_chart(stocks)

    fig_stocks.update_layout(height=420)
    fig_impact.update_layout(height=380)
    fig_milestones.update_layout(height=380)

    div_stocks = theme.chart_html(fig_stocks, "wemby_stocks_timeline", include_plotlyjs="cdn")
    div_impact = theme.chart_html(fig_impact, "wemby_deterrence_split", include_plotlyjs=False)
    div_milestones = theme.chart_html(fig_milestones, "wemby_milestones", include_plotlyjs=False)

    # 3. Top Defensive Masterclasses Table
    top_performances = wemby.sort_values("stocks", ascending=False).head(8)
    rows_html = ""
    for _, r in top_performances.iterrows():
        date_s = str(r["game_date"])
        min_s = f"{float(r['min']):.1f}m"
        blk_s = f"<span class='badge teal'>{int(r['blk'])} BLK</span>"
        stl_s = f"<span class='badge silver'>{int(r['stl'])} STL</span>"
        stocks_s = f"<span class='badge orange'>{int(r['stocks'])} STOCKS</span>"
        pts_reb = f"{int(r['pts'])} PTS, {int(r['reb'])} REB"
        pm = int(r.get("plus_minus", 0))
        pm_s = f"<span style='color: {'#00B2A9' if pm >= 0 else '#EF426F'};'>{pm:+d}</span>"
        rows_html += f"""
        <tr style="border-bottom: 1px solid {theme.COURT_LINE};">
          <td style="padding: 10px 12px; font-family: {theme.FONT_MONO};">{date_s}</td>
          <td style="padding: 10px 12px;">{min_s}</td>
          <td style="padding: 10px 12px;">{stocks_s}</td>
          <td style="padding: 10px 12px;">{blk_s} {stl_s}</td>
          <td style="padding: 10px 12px; font-family: {theme.FONT_MONO};">{pts_reb}</td>
          <td style="padding: 10px 12px; font-family: {theme.FONT_MONO};">{pm_s}</td>
        </tr>
        """

    table_section = f"""
    <div class="card">
      <h2>🛸 Best Defensive Nights (most steals + blocks)</h2>
      <div style="overflow-x: auto;">
        <table style="width: 100%; border-collapse: collapse; font-size: 0.9rem; text-align: left;">
          <thead>
            <tr style="border-bottom: 2px solid {theme.COURT_LINE}; color: {theme.SPURS_SILVER}; font-family: {theme.FONT_STENCIL}; text-transform: uppercase;">
              <th style="padding: 10px 12px;">Date</th>
              <th style="padding: 10px 12px;">Minutes</th>
              <th style="padding: 10px 12px;">Total Stocks</th>
              <th style="padding: 10px 12px;">Breakdown</th>
              <th style="padding: 10px 12px;">Line</th>
              <th style="padding: 10px 12px;">+/-</th>
            </tr>
          </thead>
          <tbody>
            {rows_html}
          </tbody>
        </table>
      </div>
    </div>
    """

    body_content = f"""
    {kpi_cards}

    <section class="chart-section">
      <h2 class="chart-title">👽 Steals + Blocks, Game by Game</h2>
      {div_stocks}
    </section>

    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(460px, 1fr)); gap: 20px;">
      <section class="chart-section" style="margin-bottom: 0;">
        <h2 class="chart-title">🛡️ Team Defensive Deterrence Split</h2>
        {div_impact}
      </section>

      <section class="chart-section" style="margin-bottom: 0;">
        <h2 class="chart-title">⭐ Defensive Milestone Ledger</h2>
        {div_milestones}
      </section>
    </div>
    <div style="height: 24px;"></div>

    {table_section}
    """

    season_s = season_str(season)
    html = theme.page_html(
        title="Wemby Lab",
        subtitle="Victor Wembanyama's blocks, steals and rim protection, and his biggest nights so far.",
        body_content=body_content,
        current_slug="wemby",
        badge=f"{season_s} Lab",
        games_played=int((games["status"] == "Final").sum()) if not games.empty else 0,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path
