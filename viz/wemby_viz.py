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
    HEAT_WINDOW,
    best_stretches,
    get_wemby_logs,
    heat_check,
    rolling_form,
    stocks_distribution,
    defensive_impact_summary,
    offensive_gravity_summary,
)

HISTORY_SEASONS = 3   # how many earlier seasons to search for best stretches, when cached


# ---------------------------------------------------------------------------
# Heat Check
# ---------------------------------------------------------------------------

def _season_logs(team_abbr: str, season: int) -> pd.DataFrame:
    team_id = config.TEAMS[team_abbr.upper()]["id"]
    path = config.CACHE_DIR / f"player_game_log_{team_id}_{season}.parquet"
    return get_wemby_logs(pd.read_parquet(path)) if path.exists() else pd.DataFrame()


def _game_label(r: pd.Series) -> str:
    """Hover title for one game, e.g. 'Nov 9 @ PHX'."""
    venue = "@" if r.get("home_away") == "A" else "vs."
    return f"{pd.Timestamp(r['game_date']):%b %-d} {venue} {r.get('opponent_abbr', '')}"


def _date_range(start: pd.Timestamp, end: pd.Timestamp) -> str:
    if start.year == end.year:
        return f"{start:%b %-d} &ndash; {end:%b %-d}, {end.year}"
    return f"{start:%b %-d}, {start.year} &ndash; {end:%b %-d}, {end.year}"


def ts_form_chart(form: pd.DataFrame, prev_ts: float | None, prev_label: str) -> go.Figure:
    """Per-game true shooting with the pooled rolling line and last season as a reference."""
    fig = go.Figure()
    if form.empty:
        return fig
    x, labels = form["game_date"], [_game_label(r) for _, r in form.iterrows()]
    fig.add_trace(go.Scatter(
        x=x, y=form["ts_pct"], mode="markers", name="Single game",
        marker=dict(color=theme.SPURS_SILVER, size=8, opacity=0.6),
        customdata=list(zip(labels, form["pts"], form["fga"], form["fta"])),
        hovertemplate="%{customdata[0]}<br>%{y:.1%} TS: %{customdata[1]} PTS on %{customdata[2]} FGA, "
                      "%{customdata[3]} FTA<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=x, y=form["roll_ts_pct"], mode="lines+markers", name=f"Last {HEAT_WINDOW} games",
        line=dict(color=theme.FIESTA_TEAL, width=3), marker=dict(size=6), customdata=labels,
        hovertemplate=f"Through %{{customdata}}<br>Last {HEAT_WINDOW}: %{{y:.1%}} TS<extra></extra>",
    ))
    if prev_ts:
        fig.add_hline(y=prev_ts, line_dash="dash", line_color=theme.FIESTA_ORANGE,
                      annotation_text=f"{prev_label}: {prev_ts:.1%}", annotation_position="bottom right")
    theme.apply(fig, yaxis_tickformat=".0%", yaxis_title="True shooting", xaxis_tickformat="%b %-d",
                legend=dict(orientation="h", y=1.12, x=0))
    return fig


def minutes_tax_chart(form: pd.DataFrame, target: float | None) -> go.Figure:
    """Actual points per game, with the same per-minute scoring at competitive-game minutes."""
    fig = go.Figure()
    if form.empty:
        return fig
    x, labels = form["game_date"], [_game_label(r) for _, r in form.iterrows()]
    margin = form["margin"] if "margin" in form.columns else pd.Series([0] * len(form))
    fig.add_trace(go.Bar(
        x=x, y=form["pts"], name="Points", marker_color=theme.FIESTA_TEAL,
        customdata=list(zip(labels, form["min"].round(1), margin)),
        hovertemplate="%{customdata[0]}<br>%{y} PTS in %{customdata[1]} min<br>"
                      "Spurs margin %{customdata[2]:+}<extra></extra>",
    ))
    if target:
        short = form["min"] < target
        scaled = (form["pts"] / form["min"] * target).where(short)
        fig.add_trace(go.Scatter(
            x=x, y=scaled, mode="markers", name=f"At {target:.1f} min",
            marker=dict(symbol="diamond-open", size=11, color=theme.FIESTA_ORANGE, line=dict(width=2)),
            customdata=labels, hovertemplate=f"%{{customdata}}<br>%{{y:.1f}} PTS at {target:.1f} min<extra></extra>",
        ))
    theme.apply(fig, yaxis_title="Points", xaxis_tickformat="%b %-d",
                legend=dict(orientation="h", y=1.12, x=0), bargap=0.35)
    return fig


def _css() -> str:
    t = theme
    return f"""
    <style>
      .hc-head {{ font-family: {t.FONT_LED}; font-size: clamp(1.5rem, 4.5vw, 2.2rem); color: {t.COURT_WHITE}; line-height: 1.2; }}
      .hc-rank {{ color: {t.SPURS_SILVER}; margin: 6px 0 18px; font-size: 0.95rem; }}
      .hc-rank strong {{ color: {t.FIESTA_ORANGE}; }}
      .hc-table {{ width: 100%; border-collapse: collapse; font-size: 0.92rem; }}
      .hc-table th, .hc-table td {{ padding: 8px 10px; border-bottom: 1px solid {t.COURT_LINE}; text-align: right; white-space: nowrap; }}
      .hc-table th:first-child, .hc-table td:first-child {{ text-align: left; }}
      .hc-table th {{ font-family: {t.FONT_STENCIL}; text-transform: uppercase; color: {t.SPURS_SILVER}; border-bottom-width: 2px; }}
      .hc-table th .sub {{ display: block; font-family: {t.FONT_BODY}; text-transform: none; font-weight: 400;
                          font-size: 0.72rem; color: {t.TEXT_MUTED}; }}
      .hc-table td {{ font-family: {t.FONT_MONO}; }}
      .hc-table td:first-child {{ font-family: {t.FONT_BODY}; color: {t.SPURS_SILVER}; }}
      .hc-table .hot {{ color: {t.FIESTA_TEAL}; font-weight: 700; background: rgba(0, 178, 169, 0.08); }}
      .hc-table tr.run td {{ background: rgba(255, 130, 0, 0.08); }}
      .hc-tax {{ margin-top: 18px; padding: 14px 16px; background: {t.SHADOW_BLACK}; border-left: 3px solid {t.FIESTA_ORANGE};
                 color: {t.SPURS_SILVER}; font-size: 0.92rem; line-height: 1.6; }}
      .hc-tax strong {{ color: {t.COURT_WHITE}; }}
      .hc-tax .proj {{ font-family: {t.FONT_MONO}; color: {t.FIESTA_ORANGE}; font-weight: 700; }}
      .hc-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(min(460px, 100%), 1fr)); gap: 20px; }}
      .hc-note {{ color: {t.TEXT_MUTED}; font-size: 0.82rem; margin-top: 10px; line-height: 1.5; }}
      .hc-short {{ display: none; }}
      @media (max-width: 640px) {{
        .hc-table {{ font-size: 0.82rem; }}
        .hc-table th, .hc-table td {{ padding: 7px 5px; }}
        .hc-table td.when {{ white-space: normal; }}
        .hc-table td.when .badge {{ display: table; margin-top: 4px; }}
        .hc-wide, .hc-long {{ display: none; }}
        .hc-short {{ display: inline; }}
      }}
    </style>"""


def heat_check_html(heat: dict, stretches: dict, current_label: str) -> str:
    """Headline, last-N comparison table and the blowout-minutes note."""
    last, before, prev = heat["last"], heat["before"], heat["prev"]
    n = heat["window"]
    headline = (f"Last {n}: {last['pts']:.1f} PTS &middot; {last['reb']:.1f} REB &middot; {last['blk']:.1f} BLK "
                f"on {last['ts_pct']:.1%} true shooting")

    rank_html = ""
    if stretches and stretches.get("current_rank"):
        since = stretches["seasons"][0]
        rank, total, outside = stretches["current_rank"], stretches["total"], stretches["better_outside_run"]
        if rank == 1:
            rank_html = f"His best {n}-game stretch since {since}, <strong>#1 of {total}</strong> by Game Score."
        else:
            rank_html = f"<strong>#{rank} of {total}</strong> {n}-game stretches since {since} by Game Score."
            if outside == 0:
                rank_html += " Every stretch ranked above it is part of this same run."

    cols = [(f"Last {n}", f"{current_label}", last, True)]
    if before:
        cols.append(("Earlier", f"{before['games']} games", before, False))
    if prev:
        cols.append((heat["prev_season"] or "Last season", f"{prev['games']} games", prev, False))
    stat_rows = [
        ("Points", "pts", "{:.1f}"), ("Rebounds", "reb", "{:.1f}"), ("Blocks", "blk", "{:.1f}"),
        ("Minutes", "min", "{:.1f}"), ("True shooting", "ts_pct", "{:.1%}"),
        ("Points per 36", "pts_per_36", "{:.1f}"), ("Game Score", "game_score", "{:.1f}"),
    ]
    head = "".join(f'<th>{name}<span class="sub">{sub}</span></th>' for name, sub, _, _ in cols)
    body = "".join(
        "<tr><td>{}</td>{}</tr>".format(
            label, "".join(f'<td class="{"hot" if hot else ""}">{fmt.format(line[key])}</td>' for _, _, line, hot in cols))
        for label, key, fmt in stat_rows
    )

    tax = ""
    if heat["projected"]:
        p = heat["projected"]
        margins = ", ".join(f"{m:+d}" for m in heat["last_margins"])
        tax = f"""
      <div class="hc-tax"><strong>The blowout tax.</strong> Spurs margins in his last {n}: {margins}. Lopsided games
        cut his minutes to {last['min']:.1f} a night. At {heat['target_minutes']:.1f} minutes, {heat['target_basis']},
        the same per-minute rates come to
        <span class="proj">{p['pts']:.1f} PTS &middot; {p['reb']:.1f} REB &middot; {p['blk']:.1f} BLK</span>.
        Treat that as a ceiling, not a forecast: per-minute rates rarely hold up over heavier minutes against starters.</div>"""

    return f"""
    <section class="card" style="border-top: 3px solid {theme.FIESTA_ORANGE};">
      <h2>🔥 Heat Check</h2>
      <div class="hc-head">{headline}</div>
      <p class="hc-rank">{rank_html}</p>
      <div style="overflow-x: auto;">
        <table class="hc-table"><thead><tr><th></th>{head}</tr></thead><tbody>{body}</tbody></table>
      </div>
      {tax}
      <p class="hc-note">Shooting percentages pool every shot in the span. Game Score here uses total rebounds for every
        season, because older box scores in the cache don't split offensive and defensive boards.</p>
    </section>"""


def best_stretches_html(stretches: dict) -> str:
    if not stretches or not stretches.get("rows"):
        return ""
    rows = ""
    for w in stretches["rows"]:
        tag = ' <span class="badge orange">This run</span>' if w["current_run"] else ""
        rows += f"""
          <tr class="{'run' if w['current_run'] else ''}">
            <td class="when">{_date_range(w['start'], w['end'])}{tag}</td>
            <td>#{w['rank']}</td><td>{w['game_score']:.1f}</td><td>{w['pts']:.1f}</td><td class="hc-wide">{w['reb']:.1f}</td>
            <td>{w['blk']:.1f}</td><td>{w['ts_pct']:.1%}</td><td class="hc-wide">{w['min']:.1f}</td>
          </tr>"""
    return f"""
    <section class="card">
      <h2>🏆 Best {HEAT_WINDOW}-Game Stretches Since {stretches['seasons'][0]}</h2>
      <div style="overflow-x: auto;">
        <table class="hc-table">
          <thead><tr><th>Games</th><th>Rank</th><th><span class="hc-long">Game Score</span><span class="hc-short">GmSc</span></th>
            <th>PTS</th><th class="hc-wide">REB</th><th>BLK</th><th>TS%</th><th class="hc-wide">MIN</th></tr></thead>
          <tbody>{rows}</tbody>
        </table>
      </div>
      <p class="hc-note">Out of {stretches['total']} stretches of {HEAT_WINDOW} straight games he played, within a season,
        ranked by average Game Score. Overlapping stretches are collapsed to the best one.</p>
    </section>"""


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

    # Heat Check: recent form against earlier this season, last season and his best stretches
    season_label = season_str(season)
    heat = heat_check(wemby, games, _season_logs(team_abbr, season - 1))
    history = {season_str(y): _season_logs(team_abbr, y) for y in range(season - HISTORY_SEASONS, season)}
    history = {label: logs for label, logs in history.items() if not logs.empty}
    stretches = best_stretches({**history, season_label: wemby}, season_label)
    heat_html = ""
    if heat:
        form = rolling_form(wemby, games)
        prev = heat["prev"]
        fig_ts = ts_form_chart(form, prev.get("ts_pct"), heat["prev_season"] or "Last season")
        fig_tax = minutes_tax_chart(form, heat["target_minutes"])
        fig_ts.update_layout(height=360)
        fig_tax.update_layout(height=360)
        heat_html = _css() + heat_check_html(heat, stretches, season_label) + f"""
    <div class="hc-grid">
      <section class="chart-section" style="margin-bottom: 0;">
        <h2 class="chart-title">🎯 True Shooting, Rolling {HEAT_WINDOW} Games</h2>
        {theme.chart_html(fig_ts, "wemby_ts_form", include_plotlyjs="cdn")}
      </section>
      <section class="chart-section" style="margin-bottom: 0;">
        <h2 class="chart-title">⏱️ Points, and Points at Full Minutes</h2>
        {theme.chart_html(fig_tax, "wemby_minutes_tax", include_plotlyjs=False)}
      </section>
    </div>
    <div style="height: 24px;"></div>
    {best_stretches_html(stretches)}"""

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

    div_stocks = theme.chart_html(fig_stocks, "wemby_stocks_timeline", include_plotlyjs=False if heat_html else "cdn")
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
    {heat_html}

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
        subtitle="Victor Wembanyama's scoring form, blocks, steals and rim protection, and his biggest nights so far.",
        body_content=body_content,
        current_slug="wemby",
        badge=f"{season_s} Lab",
        games_played=int((games["status"] == "Final").sum()) if not games.empty else 0,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path
