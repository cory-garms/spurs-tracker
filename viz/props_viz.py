"""
Props & Market Intelligence Visualizer — Builds Matchup Intel & Player Props web portals.

Generates:
  - docs/matchup.html
  - docs/props_board.html
Both adhering to the Spurs theme system and MODE_PROPS navigation bar.
"""

from __future__ import annotations

from pathlib import Path
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.io as pio

import config
from config import TEAM_ABBR, SEASON, season_str
from viz import theme
from analysis.wemby import get_wemby_logs


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

    # 1. Wemby Blocks Distribution Plot
    fig_blocks = go.Figure()
    if not wemby.empty:
        blk_counts = wemby["blk"].value_counts().sort_index()
        fig_blocks.add_trace(go.Bar(
            x=[str(x) for x in blk_counts.index],
            y=blk_counts.values,
            marker_color=theme.FIESTA_TEAL,
            text=[f"{v} games" for v in blk_counts.values],
            textposition="outside",
            hovertemplate="%{x} Blocks: %{y} games<extra></extra>",
        ))
        fig_blocks.add_vline(x=3.5, line_dash="dot", line_color=theme.FIESTA_ORANGE, annotation_text="Market Line: 3.5 BLK")
        theme.apply(
            fig_blocks,
            title=dict(text="Victor Wembanyama — Single-Game Block Distribution", font=dict(size=16)),
            xaxis_title="Blocks Recorded",
            yaxis_title="Games",
            yaxis_range=[0, max(blk_counts.values) * 1.25 + 1],
        )

    # 2. Key Players Props Table
    prop_rows = ""
    tracked_props = [
        ("Victor Wembanyama", "Blocks", 3.5, "blk"),
        ("Victor Wembanyama", "Stocks (STL+BLK)", 4.5, "stocks"),
        ("Victor Wembanyama", "Points + Rebounds", 34.5, "pts_reb"),
        ("Victor Wembanyama", "Points", 22.5, "pts"),
        ("Stephon Castle", "Assists", 4.5, "ast"),
        ("Stephon Castle", "Points", 14.5, "pts"),
        ("Devin Vassell", "Points", 16.5, "pts"),
        ("Devin Vassell", "3-Pointers Made", 2.5, "fg3m"),
        ("Keldon Johnson", "Points + Rebounds", 18.5, "pts_reb"),
        ("Harrison Barnes", "Points", 11.5, "pts"),
    ]

    for player_name, prop_name, line, stat_col in tracked_props:
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

        edge_color = theme.FIESTA_TEAL if over_pct >= 58 else (theme.FIESTA_FUSCHIA if over_pct <= 42 else theme.TEXT_MUTED)

        prop_rows += f"""
        <tr style="border-bottom: 1px solid {theme.COURT_LINE};">
          <td style="padding: 10px 12px; font-weight: 700; color: {theme.COURT_WHITE};">{player_name}</td>
          <td style="padding: 10px 12px; color: {theme.SPURS_SILVER};">{prop_name}</td>
          <td style="padding: 10px 12px; font-family: {theme.FONT_MONO}; font-weight: 700; color: {theme.FIESTA_ORANGE};">{line}</td>
          <td style="padding: 10px 12px; font-family: {theme.FONT_MONO};">{avg_val:.1f} &plusmn; {std_val:.1f}</td>
          <td style="padding: 10px 12px; font-family: {theme.FONT_MONO};">{l5_over}/{len(l5)} ({l5_pct:.0f}%)</td>
          <td style="padding: 10px 12px; font-family: {theme.FONT_MONO}; font-weight: 700; color: {edge_color};">{over_count}/{total_g} ({over_pct:.1f}%)</td>
        </tr>
        """

    fig_blocks.update_layout(height=400)
    div_blocks = pio.to_html(fig_blocks, full_html=False, include_plotlyjs="cdn", div_id="props_blocks_dist")

    body_content = f"""
    <div class="card" style="border-top: 3px solid {theme.FIESTA_ORANGE}; margin-bottom: 24px;">
      <h2 style="border-bottom: none; font-size: 1.25rem; margin-bottom: 8px;">🎲 Empirical Prop Model &amp; Distribution Horizon</h2>
      <p style="color: {theme.TEXT_MUTED}; font-size: 0.95rem; line-height: 1.6;">
        All prop lines are evaluated strictly on empirical game-log distributions. No speculative calls are published
        without measured standard deviations. Over/Under probabilities reflect season-long frequencies and L5 rolling velocity.
      </p>
    </div>

    <section class="chart-section">
      <h2 class="chart-title">👽 Wemby Blocks Prop Horizon</h2>
      {div_blocks}
    </section>

    <div class="card">
      <h2>📊 Empirical Player Prop Hit Rates</h2>
      <div style="overflow-x: auto;">
        <table style="width: 100%; border-collapse: collapse; font-size: 0.9rem; text-align: left;">
          <thead>
            <tr style="border-bottom: 2px solid {theme.COURT_LINE}; color: {theme.SPURS_SILVER}; font-family: {theme.FONT_STENCIL}; text-transform: uppercase;">
              <th style="padding: 10px 12px;">Player</th>
              <th style="padding: 10px 12px;">Market Prop</th>
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
        title="Player Props Intelligence",
        subtitle="Empirical Player Prop Horizon & Historical Hit-Rate Analytics",
        body_content=body_content,
        current_slug="board",
        badge=f"{season_s} Market",
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path


import json
from config import TEAMS
from data.league import load_league_standings
from analysis.predictions import predict_matchup, predict_all_opponents


def build_matchup_page(
    games: pd.DataFrame,
    season: int = SEASON,
    team_abbr: str = TEAM_ABBR,
    output_path: Path | None = None,
) -> Path:
    """Build and write the Matchup Intelligence & Beatdown Predictor HTML page."""
    if output_path is None:
        output_path = theme.page_path("matchup", team_abbr, season)

    # Spurs baseline stats
    f_games = games[games["status"] == "Final"].copy() if not games.empty else pd.DataFrame()
    spurs_ortg = float(f_games["ortg"].mean()) if not f_games.empty and "ortg" in f_games else 112.0
    spurs_drtg = float(f_games["drtg"].mean()) if not f_games.empty and "drtg" in f_games else 113.0
    spurs_pace = float(f_games["pace"].mean()) if not f_games.empty and "pace" in f_games else 99.8

    # Opponents league data
    league_df = load_league_standings(season=season)
    opponents_json_data: dict[str, dict] = {}
    for abbr, info in sorted(TEAMS.items()):
        if abbr == team_abbr:
            continue
        row = league_df[league_df["team_abbr"] == abbr] if not league_df.empty else pd.DataFrame()
        o_ortg = float(row.iloc[0]["ortg"]) if not row.empty else 112.5
        o_drtg = float(row.iloc[0]["drtg"]) if not row.empty else 112.5
        o_pace = float(row.iloc[0]["pace"]) if not row.empty else 99.5
        o_w = int(row.iloc[0]["wins"]) if not row.empty else 0
        o_l = int(row.iloc[0]["losses"]) if not row.empty else 0

        h2h = f_games[f_games["opponent_abbr"] == abbr] if not f_games.empty else pd.DataFrame()
        h2h_g = len(h2h)
        h2h_w = int((h2h["result"] == "W").sum()) if h2h_g > 0 else 0
        h2h_margin = float(h2h["margin"].mean()) if h2h_g > 0 else 0.0

        opponents_json_data[abbr] = {
            "abbr": abbr,
            "name": info["name"],
            "conf": info["conf"],
            "ortg": round(o_ortg, 1),
            "drtg": round(o_drtg, 1),
            "pace": round(o_pace, 1),
            "wins": o_w,
            "losses": o_l,
            "h2h_g": h2h_g,
            "h2h_w": h2h_w,
            "h2h_margin": round(h2h_margin, 1),
        }

    teams_data_serialized = json.dumps(opponents_json_data)
    spurs_base_serialized = json.dumps({
        "ortg": round(spurs_ortg, 1),
        "drtg": round(spurs_drtg, 1),
        "pace": round(spurs_pace, 1),
    })

    # Options for opponent select dropdown
    opp_options_html = ""
    for abbr, data in sorted(opponents_json_data.items(), key=lambda x: x[1]["name"]):
        selected = ' selected="selected"' if abbr == "HOU" else ""
        opp_options_html += f'<option value="{abbr}"{selected}>{data["name"]} ({abbr}) — {data["conf"]}</option>\n'

    # 1. Predictions for marquee Texas / Western rivals
    rivals = ["HOU", "DAL", "LAL", "GSW"]
    rival_cards_html = ""

    for opp in rivals:
        pred = predict_matchup(games, opp, is_home=True)
        margin_str = f"{pred['projected_margin']:+.1f}"
        margin_color = theme.FIESTA_TEAL if pred["projected_margin"] > 0 else theme.FIESTA_FUSCHIA

        rival_cards_html += f"""
        <div style="background: {theme.SILVER_SLATE}; border: 1px solid {theme.COURT_LINE}; border-top: 3px solid {pred['badge_color']}; border-radius: 6px; padding: 20px; display: flex; flex-direction: column; justify-content: space-between;">
          <div>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
              <span style="font-family: {theme.FONT_MONO}; font-size: 0.75rem; color: {theme.SPURS_STEEL}; text-transform: uppercase;">Home Matchup</span>
              <span style="font-family: {theme.FONT_MONO}; font-size: 0.72rem; padding: 2px 8px; border-radius: 3px; background: rgba(0,0,0,0.4); color: {pred['badge_color']}; border: 1px solid {pred['badge_color']};">{pred['beatdown_tier']}</span>
            </div>
            <h3 style="font-family: {theme.FONT_TITLE}; font-size: 1.4rem; color: {theme.COURT_WHITE}; margin-bottom: 4px;">Spurs vs. {pred['opponent_name']} ({pred['opponent_abbr']})</h3>
            <p style="font-size: 0.85rem; color: {theme.TEXT_MUTED}; margin-bottom: 16px;">{pred['beatdown_desc']}</p>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 16px; background: {theme.SHADOW_BLACK}; padding: 12px; border-radius: 4px; border: 1px solid {theme.COURT_LINE};">
              <div>
                <div style="font-size: 0.72rem; font-family: {theme.FONT_MONO}; color: {theme.SPURS_STEEL};">PROJECTED SCORE</div>
                <div style="font-size: 1.15rem; font-weight: 700; font-family: {theme.FONT_MONO}; color: {theme.COURT_WHITE};">SAS {pred['projected_spurs_pts']:.0f} - {pred['projected_opp_pts']:.0f}</div>
              </div>
              <div>
                <div style="font-size: 0.72rem; font-family: {theme.FONT_MONO}; color: {theme.SPURS_STEEL};">EXPECTED MARGIN</div>
                <div style="font-size: 1.15rem; font-weight: 700; font-family: {theme.FONT_MONO}; color: {margin_color};">{margin_str} PTS</div>
              </div>
            </div>

            <div style="margin-bottom: 12px;">
              <div style="display: flex; justify-content: space-between; font-size: 0.78rem; font-family: {theme.FONT_MONO}; margin-bottom: 4px;">
                <span style="color: {theme.SPURS_SILVER};">Win Probability</span>
                <span style="font-weight: 700; color: {theme.COURT_WHITE};">{pred['win_probability_pct']}%</span>
              </div>
              <div style="background: rgba(0,0,0,0.5); border-radius: 3px; height: 8px; overflow: hidden; border: 1px solid {theme.COURT_LINE};">
                <div style="background: linear-gradient(90deg, {theme.FIESTA_TEAL}, {theme.FIESTA_ORANGE}); width: {pred['win_probability_pct']}%; height: 100%;"></div>
              </div>
            </div>

            <div style="display: flex; justify-content: space-between; font-size: 0.75rem; font-family: {theme.FONT_MONO}; color: {theme.TEXT_MUTED};">
              <span>+10 Double-Digit: <strong style="color: {theme.COURT_WHITE};">{pred['prob_double_digit_pct']}%</strong></span>
              <span>+15 Blowout: <strong style="color: {theme.COURT_WHITE};">{pred['prob_blowout_pct']}%</strong></span>
              <span>+20 Rout: <strong style="color: {theme.COURT_WHITE};">{pred['prob_demolition_pct']}%</strong></span>
            </div>
          </div>
        </div>
        """

    # 2. Comprehensive 29-Team Prediction Table
    pred_df = predict_all_opponents(games, is_home=True)
    table_rows = ""

    for _, r in pred_df.iterrows():
        mar = float(r["proj_margin"])
        mar_color = theme.FIESTA_TEAL if mar > 0 else theme.FIESTA_FUSCHIA
        win_p = float(r["win_prob"])
        dd_p = float(r["double_digit_pct"])
        bo_p = float(r["blowout_pct"])

        table_rows += f"""
        <tr class="opp-row" data-conf="{r['conf']}" style="border-bottom: 1px solid {theme.COURT_LINE};">
          <td style="padding: 12px; font-weight: 700; color: {theme.COURT_WHITE}; font-family: {theme.FONT_MONO};">
            {r['opponent']} <span style="font-weight: normal; color: {theme.TEXT_MUTED}; font-size: 0.8rem;">({r['name']})</span>
          </td>
          <td style="padding: 12px; font-family: {theme.FONT_MONO}; color: {theme.SPURS_STEEL};">{r['conf']}</td>
          <td style="padding: 12px; font-family: {theme.FONT_MONO}; color: {theme.SPURS_SILVER};">{r['h2h_record']}</td>
          <td style="padding: 12px; font-family: {theme.FONT_MONO}; color: {theme.COURT_WHITE};">{r['proj_spurs']:.0f} - {r['proj_opp']:.0f}</td>
          <td style="padding: 12px; font-family: {theme.FONT_MONO}; font-weight: 700; color: {mar_color};">{mar:+.1f}</td>
          <td style="padding: 12px; font-family: {theme.FONT_MONO}; font-weight: 700; color: {theme.COURT_WHITE};">{win_p:.1f}%</td>
          <td style="padding: 12px; font-family: {theme.FONT_MONO}; color: {theme.SPURS_SILVER};">{dd_p:.1f}%</td>
          <td style="padding: 12px; font-family: {theme.FONT_MONO}; color: {theme.FIESTA_ORANGE}; font-weight: 700;">{bo_p:.1f}%</td>
          <td style="padding: 12px; font-family: {theme.FONT_MONO}; font-size: 0.8rem; color: {theme.COURT_WHITE};">{r['tier']}</td>
        </tr>
        """

    body_content = f"""
    <!-- Interactive Beatdown Simulator Console -->
    <div class="card" style="border-top: 3px solid {theme.FIESTA_TEAL}; margin-bottom: 28px;">
      <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; margin-bottom: 16px;">
        <div>
          <div style="font-family: {theme.FONT_MONO}; font-size: 0.75rem; letter-spacing: 0.1em; color: {theme.FIESTA_TEAL}; text-transform: uppercase;">Real-Time Simulation Lab</div>
          <h2 style="font-size: 1.55rem; margin-bottom: 4px;">🎮 Interactive Matchup &amp; Beatdown Simulator</h2>
        </div>
        <span style="font-family: {theme.FONT_MONO}; font-size: 0.72rem; padding: 4px 10px; border-radius: 4px; background: rgba(0, 178, 169, 0.12); color: {theme.FIESTA_TEAL}; border: 1px solid rgba(0, 178, 169, 0.3);">CALIBRATED V2 ENGINE</span>
      </div>
      <p style="color: {theme.TEXT_MUTED}; font-size: 0.92rem; line-height: 1.6; margin-bottom: 20px;">
        Test game outcomes, score margins, and blowout probabilities against any NBA opponent. Adjust court venue and rest fatigue days to see live analytical swings based on actual 30-team Net Ratings and pace factors.
      </p>

      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px; align-items: stretch;">
        <!-- Controls Column -->
        <div style="background: {theme.SHADOW_BLACK}; padding: 20px; border-radius: 6px; border: 1px solid {theme.COURT_LINE}; display: flex; flex-direction: column; gap: 16px;">
          <div>
            <label style="display: block; font-family: {theme.FONT_MONO}; font-size: 0.75rem; color: {theme.SPURS_STEEL}; text-transform: uppercase; margin-bottom: 6px;">Select Opponent</label>
            <select id="simOpponent" onchange="recalculateSim()" style="width: 100%; background: {theme.SILVER_SLATE}; border: 1px solid {theme.COURT_LINE}; color: {theme.COURT_WHITE}; padding: 10px; border-radius: 4px; font-family: {theme.FONT_MONO}; font-size: 0.9rem;">
              {opp_options_html}
            </select>
          </div>

          <div>
            <label style="display: block; font-family: {theme.FONT_MONO}; font-size: 0.75rem; color: {theme.SPURS_STEEL}; text-transform: uppercase; margin-bottom: 6px;">Game Venue / Location</label>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
              <button type="button" id="btnVenueHome" onclick="setVenue(true)" style="padding: 10px; border-radius: 4px; font-family: {theme.FONT_STENCIL}; font-size: 0.85rem; font-weight: 700; text-transform: uppercase; border: 1px solid {theme.FIESTA_TEAL}; background: rgba(0, 178, 169, 0.18); color: {theme.COURT_WHITE}; cursor: pointer;">
                🏠 Frost Bank (Home +2.8)
              </button>
              <button type="button" id="btnVenueAway" onclick="setVenue(false)" style="padding: 10px; border-radius: 4px; font-family: {theme.FONT_STENCIL}; font-size: 0.85rem; font-weight: 700; text-transform: uppercase; border: 1px solid {theme.COURT_LINE}; background: {theme.SILVER_SLATE}; color: {theme.TEXT_MUTED}; cursor: pointer;">
                ✈️ On the Road (Away -2.8)
              </button>
            </div>
          </div>

          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
            <div>
              <label style="display: block; font-family: {theme.FONT_MONO}; font-size: 0.72rem; color: {theme.SPURS_STEEL}; text-transform: uppercase; margin-bottom: 6px;">Spurs Rest Days</label>
              <select id="simSpursRest" onchange="recalculateSim()" style="width: 100%; background: {theme.SILVER_SLATE}; border: 1px solid {theme.COURT_LINE}; color: {theme.COURT_WHITE}; padding: 8px; border-radius: 4px; font-family: {theme.FONT_MONO}; font-size: 0.82rem;">
                <option value="0">0 Days (Back-to-Back: -2.4 pts)</option>
                <option value="1" selected="selected">1 Day (Normal Rest: 0.0 pts)</option>
                <option value="2">2+ Days (Well-Rested: +1.5 pts)</option>
              </select>
            </div>
            <div>
              <label style="display: block; font-family: {theme.FONT_MONO}; font-size: 0.72rem; color: {theme.SPURS_STEEL}; text-transform: uppercase; margin-bottom: 6px;">Opponent Rest Days</label>
              <select id="simOppRest" onchange="recalculateSim()" style="width: 100%; background: {theme.SILVER_SLATE}; border: 1px solid {theme.COURT_LINE}; color: {theme.COURT_WHITE}; padding: 8px; border-radius: 4px; font-family: {theme.FONT_MONO}; font-size: 0.82rem;">
                <option value="0">0 Days (Opp B2B Fatigue: +2.4 pts)</option>
                <option value="1" selected="selected">1 Day (Normal Rest: 0.0 pts)</option>
                <option value="2">2+ Days (Opp Well-Rested: -1.5 pts)</option>
              </select>
            </div>
          </div>

          <div style="border-top: 1px solid {theme.COURT_LINE}; padding-top: 12px; display: flex; justify-content: space-between; font-size: 0.75rem; font-family: {theme.FONT_MONO}; color: {theme.TEXT_MUTED};">
            <span>Model Spread Std Dev: &sigma; = 11.5</span>
            <span id="simNetRtgDelta">Spread: +0.0 Net</span>
          </div>
        </div>

        <!-- Live Scoreboard Display -->
        <div id="simBoard" style="background: {theme.SHADOW_BLACK}; padding: 22px; border-radius: 6px; border: 1px solid {theme.COURT_LINE}; display: flex; flex-direction: column; justify-content: space-between;">
          <div>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
              <span id="simVenueLabel" style="font-family: {theme.FONT_MONO}; font-size: 0.75rem; color: {theme.SPURS_STEEL}; text-transform: uppercase;">HOME CONTEST</span>
              <span id="simTierBadge" style="font-family: {theme.FONT_MONO}; font-size: 0.75rem; padding: 3px 10px; border-radius: 4px; background: rgba(0, 178, 169, 0.15); color: {theme.FIESTA_TEAL}; border: 1px solid {theme.FIESTA_TEAL}; font-weight: 700;">
                🔨 Decisive Beatdown
              </span>
            </div>

            <!-- Big LED Scoreboard -->
            <div style="background: {theme.FROST_BANK_FLOOR}; border: 1px solid {theme.COURT_LINE}; border-radius: 6px; padding: 16px; margin-bottom: 16px;">
              <div style="display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; text-align: center; gap: 8px;">
                <div>
                  <div style="font-family: {theme.FONT_STENCIL}; font-size: 0.85rem; color: {theme.SPURS_SILVER}; letter-spacing: 0.08em; text-transform: uppercase;">SPURS</div>
                  <div id="simSpursScore" style="font-family: {theme.FONT_DISPLAY}; font-size: 3.2rem; font-weight: 700; color: {theme.COURT_WHITE}; line-height: 1.0;">116</div>
                </div>
                <div style="font-family: {theme.FONT_MONO}; font-size: 1.2rem; color: {theme.COURT_LINE};">VS</div>
                <div>
                  <div id="simOppNameShort" style="font-family: {theme.FONT_STENCIL}; font-size: 0.85rem; color: {theme.TEXT_MUTED}; letter-spacing: 0.08em; text-transform: uppercase;">ROCKETS</div>
                  <div id="simOppScore" style="font-family: {theme.FONT_DISPLAY}; font-size: 3.2rem; font-weight: 700; color: {theme.TEXT_MUTED}; line-height: 1.0;">108</div>
                </div>
              </div>
              <div style="margin-top: 10px; text-align: center; font-family: {theme.FONT_MONO}; font-size: 0.95rem; font-weight: 700;">
                PROJECTED SPREAD: <span id="simMarginVal" style="color: {theme.FIESTA_TEAL};">+8.0 PTS</span>
              </div>
            </div>

            <!-- Win Probability Meter -->
            <div style="margin-bottom: 16px;">
              <div style="display: flex; justify-content: space-between; font-size: 0.8rem; font-family: {theme.FONT_MONO}; margin-bottom: 5px;">
                <span style="color: {theme.SPURS_SILVER};">Win Probability</span>
                <span id="simWinPct" style="font-weight: 700; color: {theme.COURT_WHITE};">75.6%</span>
              </div>
              <div style="background: rgba(0,0,0,0.6); border-radius: 4px; height: 10px; overflow: hidden; border: 1px solid {theme.COURT_LINE};">
                <div id="simWinBar" style="background: linear-gradient(90deg, {theme.FIESTA_TEAL}, {theme.FIESTA_ORANGE}); width: 75.6%; height: 100%; transition: width 0.3s ease;"></div>
              </div>
            </div>

            <!-- Beatdown Probability Multi-Gauge -->
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; text-align: center; background: {theme.SILVER_SLATE}; padding: 10px; border-radius: 4px; border: 1px solid {theme.COURT_LINE}; margin-bottom: 12px;">
              <div>
                <div style="font-size: 0.68rem; font-family: {theme.FONT_MONO}; color: {theme.SPURS_STEEL};">+10 WIN</div>
                <div id="simDoubleDigitPct" style="font-size: 1.05rem; font-weight: 700; font-family: {theme.FONT_MONO}; color: {theme.COURT_WHITE};">44.8%</div>
              </div>
              <div>
                <div style="font-size: 0.68rem; font-family: {theme.FONT_MONO}; color: {theme.SPURS_STEEL};">+15 BLOWOUT</div>
                <div id="simBlowoutPct" style="font-size: 1.05rem; font-weight: 700; font-family: {theme.FONT_MONO}; color: {theme.FIESTA_ORANGE};">28.4%</div>
              </div>
              <div>
                <div style="font-size: 0.68rem; font-family: {theme.FONT_MONO}; color: {theme.SPURS_STEEL};">+20 ROUT</div>
                <div id="simDemolitionPct" style="font-size: 1.05rem; font-weight: 700; font-family: {theme.FONT_MONO}; color: {theme.FIESTA_FUSCHIA};">15.9%</div>
              </div>
            </div>
          </div>

          <div id="simTierDesc" style="font-size: 0.82rem; color: {theme.TEXT_MUTED}; font-style: italic; border-left: 2px solid {theme.FIESTA_TEAL}; padding-left: 10px;">
            Spurs strongly favored to pull away by double-digits in the second half.
          </div>
        </div>
      </div>
    </div>

    <!-- Key Rivalries Section -->
    <div style="margin-bottom: 28px;">
      <h2 style="font-family: {theme.FONT_TITLE}; font-size: 1.5rem; text-transform: uppercase; color: {theme.SPURS_SILVER}; margin-bottom: 14px;">
        ⚔️ Key Western &amp; Texas Rivalry Forecasts
      </h2>
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 18px;">
        {rival_cards_html}
      </div>
    </div>

    <!-- 29-Team Complete Table -->
    <div class="card">
      <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 14px; margin-bottom: 16px;">
        <h2 style="margin-bottom: 0;">📊 Complete 29-Team Opponent Beatdown Radar</h2>
        <div style="display: flex; gap: 8px;">
          <input type="text" id="oppSearch" placeholder="Search opponent..." style="background: {theme.SHADOW_BLACK}; border: 1px solid {theme.COURT_LINE}; color: {theme.COURT_WHITE}; padding: 6px 12px; border-radius: 4px; font-family: {theme.FONT_MONO}; font-size: 0.85rem;" onkeyup="filterOpponents()">
        </div>
      </div>

      <div style="overflow-x: auto;">
        <table style="width: 100%; border-collapse: collapse; font-size: 0.88rem; text-align: left;" id="oppTable">
          <thead>
            <tr style="border-bottom: 2px solid {theme.COURT_LINE}; color: {theme.SPURS_SILVER}; font-family: {theme.FONT_STENCIL}; text-transform: uppercase;">
              <th style="padding: 10px 12px;">Opponent</th>
              <th style="padding: 10px 12px;">Conf</th>
              <th style="padding: 10px 12px;">H2H Rec</th>
              <th style="padding: 10px 12px;">Proj Score</th>
              <th style="padding: 10px 12px;">Proj Margin</th>
              <th style="padding: 10px 12px;">Win Prob</th>
              <th style="padding: 10px 12px;">+10 Pt Win %</th>
              <th style="padding: 10px 12px;">+15 Blowout %</th>
              <th style="padding: 10px 12px;">Outlook Tier</th>
            </tr>
          </thead>
          <tbody>
            {table_rows}
          </tbody>
        </table>
      </div>
    </div>

    <script>
      const TEAMS_DATA = {teams_data_serialized};
      const SPURS_BASE = {spurs_base_serialized};
      let isHomeGame = true;

      function erf(x) {{
        const a1 =  0.254829592;
        const a2 = -0.284496736;
        const a3 =  1.421413741;
        const a4 = -1.453152027;
        const a5 =  1.061405429;
        const p  =  0.3275911;
        const sign = (x < 0) ? -1 : 1;
        const ax = Math.abs(x);
        const t = 1.0 / (1.0 + p * ax);
        const y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * Math.exp(-ax * ax);
        return sign * y;
      }}

      function normCdf(x) {{
        return 0.5 * (1.0 + erf(x / Math.SQRT2));
      }}

      function restAdj(days) {{
        if (days === 0) return -2.4;
        if (days >= 2) return 1.5;
        return 0.0;
      }}

      function setVenue(isHome) {{
        isHomeGame = isHome;
        const btnHome = document.getElementById("btnVenueHome");
        const btnAway = document.getElementById("btnVenueAway");
        if (isHome) {{
          btnHome.style.borderColor = "{theme.FIESTA_TEAL}";
          btnHome.style.background = "rgba(0, 178, 169, 0.18)";
          btnHome.style.color = "{theme.COURT_WHITE}";
          btnAway.style.borderColor = "{theme.COURT_LINE}";
          btnAway.style.background = "{theme.SILVER_SLATE}";
          btnAway.style.color = "{theme.TEXT_MUTED}";
        }} else {{
          btnAway.style.borderColor = "{theme.FIESTA_TEAL}";
          btnAway.style.background = "rgba(0, 178, 169, 0.18)";
          btnAway.style.color = "{theme.COURT_WHITE}";
          btnHome.style.borderColor = "{theme.COURT_LINE}";
          btnHome.style.background = "{theme.SILVER_SLATE}";
          btnHome.style.color = "{theme.TEXT_MUTED}";
        }}
        recalculateSim();
      }}

      function recalculateSim() {{
        const oppSelect = document.getElementById("simOpponent");
        const oppAbbr = oppSelect.value;
        const opp = TEAMS_DATA[oppAbbr];
        if (!opp) return;

        const spursRestDays = parseInt(document.getElementById("simSpursRest").value, 10);
        const oppRestDays = parseInt(document.getElementById("simOppRest").value, 10);

        const homeBoost = isHomeGame ? 2.8 : -2.8;
        const restBoost = restAdj(spursRestDays) - restAdj(oppRestDays);
        const gamePace = (SPURS_BASE.pace + opp.pace) / 2.0;

        const spursExpRtg = (SPURS_BASE.ortg + opp.drtg) / 2.0 + (homeBoost / 2.0) + (restBoost / 2.0);
        const oppExpRtg   = (opp.ortg + SPURS_BASE.drtg) / 2.0 - (homeBoost / 2.0) - (restBoost / 2.0);

        const spursPts = (spursExpRtg * gamePace) / 100.0;
        const oppPts = (oppExpRtg * gamePace) / 100.0;

        let projMargin = spursPts - oppPts;
        if (opp.h2h_g > 0) {{
          projMargin = (projMargin * 0.70) + (opp.h2h_margin * 0.30);
        }}

        const stdDev = 11.5;
        const zWin = projMargin / stdDev;
        const winProb = (normCdf(zWin) * 100).toFixed(1);

        const z10 = (projMargin - 9.5) / stdDev;
        const doubleDigit = (normCdf(z10) * 100).toFixed(1);

        const z15 = (projMargin - 14.5) / stdDev;
        const blowout = (normCdf(z15) * 100).toFixed(1);

        const z20 = (projMargin - 19.5) / stdDev;
        const demo = (normCdf(z20) * 100).toFixed(1);

        // Update DOM
        document.getElementById("simVenueLabel").innerText = isHomeGame ? "FROST BANK CENTER (HOME)" : "ROAD CONTEST (AWAY)";
        document.getElementById("simSpursScore").innerText = Math.round(spursPts);
        document.getElementById("simOppScore").innerText = Math.round(oppPts);
        document.getElementById("simOppNameShort").innerText = opp.name.toUpperCase();

        const marginEl = document.getElementById("simMarginVal");
        marginEl.innerText = (projMargin >= 0 ? "+" : "") + projMargin.toFixed(1) + " PTS";
        marginEl.style.color = projMargin >= 0 ? "{theme.FIESTA_TEAL}" : "{theme.FIESTA_FUSCHIA}";

        document.getElementById("simWinPct").innerText = winProb + "%";
        document.getElementById("simWinBar").style.width = winProb + "%";

        document.getElementById("simDoubleDigitPct").innerText = doubleDigit + "%";
        document.getElementById("simBlowoutPct").innerText = blowout + "%";
        document.getElementById("simDemolitionPct").innerText = demo + "%";

        const badgeEl = document.getElementById("simTierBadge");
        const descEl = document.getElementById("simTierDesc");
        const boardEl = document.getElementById("simBoard");

        let tier = "";
        let desc = "";
        let color = "";

        if (projMargin >= 12.0 || blowout >= 40.0) {{
          tier = "💥 Complete Demolition";
          desc = "Spurs hold overwhelming statistical matchup advantages across paint and pace.";
          color = "{theme.FIESTA_TEAL}";
        }} else if (projMargin >= 5.0 || doubleDigit >= 45.0) {{
          tier = "🔨 Decisive Beatdown";
          desc = "Spurs strongly favored to pull away by double-digits in the second half.";
          color = "{theme.SPURS_SILVER}";
        }} else if (projMargin >= -1.0) {{
          tier = "⏱️ Crunch-Time Battle";
          desc = "Projected 4th-quarter nail-biter decided by clutch execution and free throws.";
          color = "{theme.FIESTA_ORANGE}";
        }} else {{
          tier = "⚠️ High-Stakes Dogfight";
          desc = "Upset alert required: Spurs must dominate rim protection and turnover margins.";
          color = "{theme.FIESTA_FUSCHIA}";
        }}

        badgeEl.innerText = tier;
        badgeEl.style.color = color;
        badgeEl.style.borderColor = color;
        descEl.innerText = desc;
        descEl.style.borderLeftColor = color;
        boardEl.style.borderTop = "3px solid " + color;

        document.getElementById("simNetRtgDelta").innerText = "Rest Diff: " + (restBoost >= 0 ? "+" : "") + restBoost.toFixed(1) + " pts";
      }}

      function filterOpponents() {{
        var input = document.getElementById("oppSearch");
        var filter = input.value.toUpperCase();
        var rows = document.getElementsByClassName("opp-row");
        for (var i = 0; i < rows.length; i++) {{
          var txt = rows[i].textContent || rows[i].innerText;
          rows[i].style.display = txt.toUpperCase().indexOf(filter) > -1 ? "" : "none";
        }}
      }}

      // Initialize on page load
      document.addEventListener("DOMContentLoaded", function() {{
        recalculateSim();
      }});
      // Also execute immediately in case DOM is already ready
      setTimeout(recalculateSim, 50);
    </script>
    """

    season_s = season_str(season)
    html = theme.page_html(
        title="Matchup & Beatdown Predictor",
        subtitle="Empirical Opponent Scoring Margin Simulations & Blowout Likelihood Matrices",
        body_content=body_content,
        current_slug="matchup",
        badge=f"{season_s} Predictor",
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path


