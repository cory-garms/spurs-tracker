"""
Player Props Visualizer — builds docs/props_board.html.

Rotation hit rates against last-season reference lines, adhering to the Spurs theme system.
(The next-game preview lives in viz/matchup_viz.py.)
"""

from __future__ import annotations

from pathlib import Path
import pandas as pd
import numpy as np
import plotly.graph_objects as go

import config
from config import TEAM_ABBR, SEASON, season_str
from viz import theme
from viz.avatars import avatar_html, player_link
from analysis.wemby import get_wemby_logs


# Signature-stat candidates: (label, column, per-game average that makes it notable)
SIGNATURE_STATS = [
    ("Assists", "ast", 4.0),
    ("Rebounds", "reb", 6.0),
    ("3-Pointers Made", "fg3m", 1.5),
    ("Blocks", "blk", 1.5),
]


def _previous_season_logs(team_abbr: str, season: int) -> pd.DataFrame:
    team_id = config.TEAMS[team_abbr.upper()]["id"]
    path = config.CACHE_DIR / f"player_game_log_{team_id}_{season - 1}.parquet"
    return pd.read_parquet(path) if path.exists() else pd.DataFrame()


def _half_point_line(avg: float) -> float:
    """Half-point line at the average's whole number, so there are no pushes: 17.3 -> 17.5, 1.0 -> 1.5."""
    return float(np.floor(avg) + 0.5)


def rotation_props(player_logs: pd.DataFrame, prev_logs: pd.DataFrame, top_n: int = 8,
                   min_prev_games: int = 10) -> list[tuple[str, str, float, str, str]]:
    """
    Points plus a signature stat for the top `top_n` players by minutes.
    Lines come from last season's average where the player has enough games, else this season's.
    Returns (player, stat label, line, column, line basis) rows.
    """
    played = player_logs[player_logs["min"] > 0]
    if played.empty:
        return []
    by_min = played.groupby("player_name")["min"].mean().sort_values(ascending=False).head(top_n)
    prev = prev_logs[prev_logs["min"] > 0] if not prev_logs.empty else prev_logs

    rows = []
    for name in by_min.index:
        cur = played[played["player_name"] == name]
        old = prev[prev["player_name"] == name] if not prev.empty else prev
        use_prev = len(old) >= min_prev_games
        base, basis = (old, "last season") if use_prev else (cur, "this season")

        markets = [("Points", "pts")]
        notable = [(lbl, col, cur[col].mean() / bar) for lbl, col, bar in SIGNATURE_STATS if cur[col].mean() >= bar]
        if notable:
            lbl, col, _ = max(notable, key=lambda m: m[2])
            markets.append((lbl, col))
        for lbl, col in markets:
            rows.append((name, lbl, _half_point_line(float(base[col].mean())), col, basis))
    return rows


def build_props_board_page(
    games: pd.DataFrame,
    player_logs: pd.DataFrame,
    season: int = SEASON,
    team_abbr: str = TEAM_ABBR,
    output_path: Path | None = None,
) -> Path:
    """Build and write the Player Props empirical board HTML page."""
    if output_path is None:
        output_path = theme.page_path("board", team_abbr, season)

    wemby = get_wemby_logs(player_logs)
    if not wemby.empty:
        wemby = wemby[wemby["min"] > 0]

    # 1. Wemby Blocks Distribution Plot: every count from 0 to his high, so gaps show as gaps
    fig_blocks = go.Figure()
    if not wemby.empty:
        blk_counts = wemby["blk"].astype(int).value_counts().reindex(
            range(0, int(wemby["blk"].max()) + 1), fill_value=0
        )
        fig_blocks.add_trace(go.Bar(
            x=list(blk_counts.index),
            y=blk_counts.values,
            marker_color=theme.FIESTA_TEAL,
            text=[f"{v} game{'s' if v != 1 else ''}" if v else "" for v in blk_counts.values],
            textposition="outside",
            hovertemplate="%{x} blocks: %{y} game(s)<extra></extra>",
        ))
        fig_blocks.add_vline(x=3.5, line_dash="dot", line_color=theme.FIESTA_ORANGE, annotation_text="Reference line: 3.5")
        theme.apply(
            fig_blocks,
            xaxis_title="Blocks in a game",
            yaxis_title="Games",
            xaxis_dtick=1,
            yaxis_dtick=1 if blk_counts.max() <= 10 else None,
            yaxis_range=[0, max(blk_counts.values) * 1.25 + 1],
        )

    # 2. Key Players Props Table
    prop_rows = ""
    tracked_props = rotation_props(player_logs, _previous_season_logs(team_abbr, season))

    for player_name, prop_name, line, stat_col, basis in tracked_props:
        # Exact name match (first names collide, e.g. Harrison Barnes / Harrison Ingram)
        # and only games the player actually played (DNPs would deflate hit rates).
        p_df = player_logs[(player_logs["player_name"] == player_name) & (player_logs["min"] > 0)].copy()
        if p_df.empty:
            continue

        p_df = p_df.sort_values("game_date").reset_index(drop=True)
        if stat_col == "stocks":
            p_df["val"] = p_df["stl"].fillna(0) + p_df["blk"].fillna(0)
        elif stat_col == "pts_reb":
            p_df["val"] = p_df["pts"].fillna(0) + p_df["reb"].fillna(0)
        else:
            p_df["val"] = p_df[stat_col].fillna(0)

        total_g = len(p_df)
        over_count = int((p_df["val"] > line).sum())
        over_pct = (over_count / total_g * 100) if total_g > 0 else 0.0

        # Last 5 games
        l5 = p_df.tail(5)
        l5_over = int((l5["val"] > line).sum())
        l5_pct = (l5_over / len(l5) * 100) if not l5.empty else 0.0

        avg_val = float(p_df["val"].mean()) if total_g > 0 else 0.0
        std_val = float(p_df["val"].std()) if total_g > 1 else 0.0

        # Don't color a hit rate as a lean until the sample can support one
        if total_g < theme.SMALL_SAMPLE_GAMES:
            edge_color = theme.COURT_WHITE
        else:
            edge_color = theme.FIESTA_TEAL if over_pct >= 58 else (theme.FIESTA_FUSCHIA if over_pct <= 42 else theme.TEXT_MUTED)

        prop_rows += f"""
        <tr style="border-bottom: 1px solid {theme.COURT_LINE};">
          <td style="padding: 8px 12px; font-weight: 700; color: {theme.COURT_WHITE};"><span class="with-avatar">{avatar_html(player_name, "sm")}<span>{player_link(player_name)}</span></span></td>
          <td style="padding: 10px 12px; color: {theme.SPURS_SILVER};">{prop_name}</td>
          <td style="padding: 10px 12px; font-family: {theme.FONT_MONO}; font-weight: 700; color: {theme.FIESTA_ORANGE};">{line} <span style="font-weight: 400; font-size: 0.75rem; color: {theme.TEXT_MUTED};">{basis}</span></td>
          <td style="padding: 10px 12px; font-family: {theme.FONT_MONO};">{avg_val:.1f} &plusmn; {std_val:.1f}</td>
          <td style="padding: 10px 12px; font-family: {theme.FONT_MONO};">{l5_over}/{len(l5)} ({l5_pct:.0f}%)</td>
          <td style="padding: 10px 12px; font-family: {theme.FONT_MONO}; font-weight: 700; color: {edge_color};">{over_count}/{total_g} ({over_pct:.1f}%)</td>
        </tr>
        """

    fig_blocks.update_layout(height=400)
    div_blocks = theme.chart_html(fig_blocks, "props_blocks_dist", include_plotlyjs="cdn")

    body_content = f"""
    <div class="card" style="border-top: 3px solid {theme.FIESTA_ORANGE}; margin-bottom: 24px;">
      <h2 style="border-bottom: none; margin-bottom: 8px;">🎲 How to read this</h2>
      <p style="color: {theme.SPURS_SILVER}; font-size: 0.95rem; line-height: 1.6;">
        The eight players getting the most minutes, each with points and their signature stat. Each reference line is
        the player's <em>last-season</em> average rounded to the half point, so the hit rate shows who is playing above
        last year's level (new players use this season's average). These are not sportsbook odds, and hit rates are
        colored as a lean only after {theme.SMALL_SAMPLE_GAMES} games. For fun and analysis, not betting advice.
      </p>
    </div>

    <section class="chart-section">
      <h2 class="chart-title">👽 Wemby Blocks per Game</h2>
      {div_blocks}
    </section>

    <div class="card">
      <h2>📊 Prop Hit Rates</h2>
      <div style="overflow-x: auto;">
        <table style="width: 100%; border-collapse: collapse; font-size: 0.9rem; text-align: left;">
          <thead>
            <tr style="border-bottom: 2px solid {theme.COURT_LINE}; color: {theme.SPURS_SILVER}; font-family: {theme.FONT_STENCIL}; text-transform: uppercase;">
              <th style="padding: 10px 12px;">Player</th>
              <th style="padding: 10px 12px;">Stat</th>
              <th style="padding: 10px 12px;">Reference Line</th>
              <th style="padding: 10px 12px;">Season Mean &plusmn; 1&sigma;</th>
              <th style="padding: 10px 12px;">L5 Games</th>
              <th style="padding: 10px 12px;">Season Hit Rate (Over)</th>
            </tr>
          </thead>
          <tbody>
            {prop_rows}
          </tbody>
        </table>
      </div>
    </div>
    """

    season_s = season_str(season)
    html = theme.page_html(
        title="Player Props",
        subtitle="How often players have cleared common prop lines this season. For fun and analysis, not betting advice.",
        body_content=body_content,
        current_slug="board",
        badge=f"{season_s} Props",
        games_played=int((games["status"] == "Final").sum()) if not games.empty else 0,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path
