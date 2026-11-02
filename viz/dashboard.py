"""
Combined Plotly dashboard — assembles all charts into one self-contained HTML file.

Usage:
    python viz_report.py --team SAS --season 2024
    # → docs/dashboard.html

CDN note: include_plotlyjs="cdn" is set ONLY on the first figure so the Plotly
version always matches the installed package.  Never hardcode a CDN version string.
"""

from __future__ import annotations

from html import escape
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

from config import OUTPUT_DIR, TEAM_ABBR, SEASON
from viz import theme
from viz.charts import (
    season_timeline,
    rolling_win_pct_chart,
    score_margin_chart,
    streak_timeline_chart,
    scoring_trend_chart,
    player_scoring_leaderboard,
    hot_cold_chart,
    shot_efficiency_chart,
    defensive_rating_trend,
    roster_production_matrix,
    clutch_margin_distribution,
    starter_bench_production_chart,
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
        output_path = theme.page_path("dashboard", team_abbr, season)

    figures: list[tuple[str, go.Figure, int]] = []

    final_games = int((games["status"] == "Final").sum()) if not games.empty else 0
    show_trends = final_games >= theme.MIN_TREND_GAMES

    # Per-game margin carries the early season on its own: wins, losses and the
    # running total in one chart. Trend lines join once there is a trend to see.
    fig3 = score_margin_chart(games, team_name)
    figures.append(("Score Margin per Game", fig3, 420))

    if show_trends:
        figures.append(("Season Timeline", season_timeline(games, team_name), 420))
        figures.append(("Rolling Win%", rolling_win_pct_chart(games, team_name, windows=[5, 10]), 380))

    fig_clutch = clutch_margin_distribution(games, team_name)
    if fig_clutch.data:
        figures.append(("Close Games & Margin Distribution", fig_clutch, 380))

    if show_trends:
        figures.append(("Streak Timeline", streak_timeline_chart(streak_timeline(games), team_name), 320))
        figures.append(("Scoring Trend", scoring_trend_chart(games, team_name, window=10), 380))

    # 5b. Roster production matrix
    if not player_logs.empty:
        fig_roster = roster_production_matrix(player_logs, team_name)
        if fig_roster.data:
            figures.append(("Rotation Core Production", fig_roster, fig_roster.layout.height or 440))

        fig_sb = starter_bench_production_chart(player_logs, team_name)
        if fig_sb.data:
            figures.append(("Starter vs. Bench Output", fig_sb, 360))

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
    if show_trends and "drtg" in games.columns and games["drtg"].notna().any():
        fig9 = defensive_rating_trend(games, team_name)
        if fig9.data:
            figures.append(("Defensive Rating Trend", fig9, 380))

    # -----------------------------------------------------------------------
    # Assemble HTML
    # CDN fix: include_plotlyjs="cdn" only on first figure — version always
    # matches installed plotly package, avoids blank-chart regression.
    # -----------------------------------------------------------------------
    # -----------------------------------------------------------------------
    # Analytical Command Center: Four Factors, Synergies & Clutch
    # -----------------------------------------------------------------------
    from analysis.four_factors import (
        team_four_factors_summary,
        LEAGUE_EFG_BENCHMARK,
        LEAGUE_TOV_BENCHMARK,
        LEAGUE_OREB_BENCHMARK,
        LEAGUE_FTR_BENCHMARK,
    )
    from analysis.lineups import key_spurs_synergies, starter_bench_deep_split
    from analysis.clutch import clutch_game_summary

    ff = team_four_factors_summary(player_logs, games) if not player_logs.empty else {}
    synergies = key_spurs_synergies(player_logs).head(3) if not player_logs.empty else pd.DataFrame()
    sb = starter_bench_deep_split(player_logs) if not player_logs.empty else {}
    clutch = clutch_game_summary(games) if not games.empty else {}
    close_n = int(clutch.get("clutch_games_played", 0))
    if close_n >= theme.MIN_GRADE_GAMES:
        composure_html = (
            f'Composure: <strong style="color: {theme.FIESTA_TEAL};">{clutch.get("composure_index", 0):.0f}/100</strong> '
            f'({clutch.get("composure_grade", "—").split(" (")[0]})'
        )
    else:
        composure_html = theme.small_sample_badge(
            f"Composure grade after {theme.MIN_GRADE_GAMES} close games ({close_n} so far)"
        )

    # Synergy rows
    from viz.avatars import avatar_html, player_link
    syn_rows = ""
    if not synergies.empty:
        for _, s in synergies.iterrows():
            p1, p2 = s.get("player_1", ""), s.get("player_2", "")
            pair = (f'<span class="duo">{avatar_html(p1, "sm")}{avatar_html(p2, "sm")}</span>'
                    f'{player_link(p1, p1.split()[-1])} + {player_link(p2, p2.split()[-1])}')
            pm = float(s.get("net_pm_pg", 0.0))
            pm_color = theme.FIESTA_TEAL if pm > 0 else theme.FIESTA_FUSCHIA
            syn_rows += f"""
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 0; border-bottom: 1px solid rgba(255,255,255,0.06); font-family: {theme.FONT_MONO}; font-size: 0.8rem;">
              <span class="with-avatar" style="color: {theme.COURT_WHITE}; font-size: 0.95rem;">{pair}</span>
              <span style="font-weight: 700; color: {pm_color};">{pm:+.2f} +/-</span>
            </div>
            """
    else:
        syn_rows = f'<div style="font-size: 0.8rem; color: {theme.TEXT_MUTED};">No synergy pairings recorded.</div>'

    # Four factors metrics
    efg_v = ff.get("efg_pct", 0.0) * 100
    efg_d = ff.get("efg_delta_vs_league", 0.0)
    efg_color = theme.FIESTA_TEAL if efg_d >= 0 else theme.FIESTA_FUSCHIA

    tov_v = ff.get("tov_pct", 0.0) * 100
    tov_d = ff.get("tov_delta_vs_league", 0.0)
    tov_color = theme.FIESTA_TEAL if tov_d <= 0 else theme.FIESTA_FUSCHIA  # lower tov is better

    oreb_v = ff.get("oreb_pct", 0.0) * 100
    oreb_d = ff.get("oreb_delta_vs_league", 0.0)
    oreb_color = theme.FIESTA_TEAL if oreb_d >= 0 else theme.FIESTA_FUSCHIA

    ftr_v = ff.get("ftr", 0.0)
    ftr_d = ff.get("ftr_delta_vs_league", 0.0)
    ftr_color = theme.FIESTA_TEAL if ftr_d >= 0 else theme.FIESTA_FUSCHIA

    command_center_html = f"""
    <div class="card" style="border-top: 3px solid {theme.FIESTA_TEAL}; margin-bottom: 24px;">
      <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; margin-bottom: 14px;">
        <h2 style="margin-bottom: 0;">Team Snapshot</h2>
      </div>

      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 16px;">
        <!-- Four Factors Pillar -->
        <div style="background: {theme.SHADOW_BLACK}; padding: 16px; border-radius: 6px; border: 1px solid {theme.COURT_LINE};">
          <div style="font-family: {theme.FONT_STENCIL}; font-size: 0.82rem; color: {theme.SPURS_SILVER}; letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 12px;">
            Four Factors <span style="text-transform: none; letter-spacing: 0; color: {theme.TEXT_MUTED};">(vs. league average)</span>
          </div>
          
          <div style="display: flex; flex-direction: column; gap: 10px;">
            <!-- eFG% -->
            <div>
              <div style="display: flex; justify-content: space-between; font-size: 0.78rem; font-family: {theme.FONT_MONO}; margin-bottom: 3px;">
                <span>Effective FG% (40% wt)</span>
                <span style="font-weight: 700; color: {efg_color};">{efg_v:.1f}% ({efg_d:+.1f}%)</span>
              </div>
              <div style="background: rgba(0,0,0,0.5); border-radius: 3px; height: 6px; overflow: hidden;">
                <div style="background: {efg_color}; width: {min(100, max(0, efg_v / 0.65 * 100)):.1f}%; height: 100%;"></div>
              </div>
            </div>

            <!-- TOV% -->
            <div>
              <div style="display: flex; justify-content: space-between; font-size: 0.78rem; font-family: {theme.FONT_MONO}; margin-bottom: 3px;">
                <span>Turnover Rate (25% wt)</span>
                <span style="font-weight: 700; color: {tov_color};">{tov_v:.1f}% ({tov_d:+.1f}%)</span>
              </div>
              <div style="background: rgba(0,0,0,0.5); border-radius: 3px; height: 6px; overflow: hidden;">
                <div style="background: {tov_color}; width: {min(100, max(0, tov_v / 0.20 * 100)):.1f}%; height: 100%;"></div>
              </div>
            </div>

            <!-- OREB% -->
            <div>
              <div style="display: flex; justify-content: space-between; font-size: 0.78rem; font-family: {theme.FONT_MONO}; margin-bottom: 3px;">
                <span>Offensive Rebound % (20% wt)</span>
                <span style="font-weight: 700; color: {oreb_color};">{oreb_v:.1f}% ({oreb_d:+.1f}%)</span>
              </div>
              <div style="background: rgba(0,0,0,0.5); border-radius: 3px; height: 6px; overflow: hidden;">
                <div style="background: {oreb_color}; width: {min(100, max(0, oreb_v / 0.35 * 100)):.1f}%; height: 100%;"></div>
              </div>
            </div>

            <!-- FTR -->
            <div>
              <div style="display: flex; justify-content: space-between; font-size: 0.78rem; font-family: {theme.FONT_MONO}; margin-bottom: 3px;">
                <span>Free Throw Rate (15% wt)</span>
                <span style="font-weight: 700; color: {ftr_color};">{ftr_v:.3f} ({ftr_d:+.1f}%)</span>
              </div>
              <div style="background: rgba(0,0,0,0.5); border-radius: 3px; height: 6px; overflow: hidden;">
                <div style="background: {ftr_color}; width: {min(100, max(0, ftr_v / 0.35 * 100)):.1f}%; height: 100%;"></div>
              </div>
            </div>
          </div>
        </div>

        <!-- Young Core & Rotation Synergies -->
        <div style="background: {theme.SHADOW_BLACK}; padding: 16px; border-radius: 6px; border: 1px solid {theme.COURT_LINE}; display: flex; flex-direction: column; justify-content: space-between;">
          <div>
            <div style="font-family: {theme.FONT_STENCIL}; font-size: 0.82rem; color: {theme.SPURS_SILVER}; letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 8px;">
              Best Duos <span style="text-transform: none; letter-spacing: 0; color: {theme.TEXT_MUTED};">(avg +/- when both play)</span>
            </div>
            {syn_rows}
          </div>

          <div style="margin-top: 12px; padding-top: 10px; border-top: 1px solid rgba(255,255,255,0.08); display: flex; justify-content: space-between; font-family: {theme.FONT_MONO}; font-size: 0.75rem; color: {theme.TEXT_MUTED};">
            <span>Starters: <strong style="color: {theme.COURT_WHITE};">{sb.get('starter_scoring_share_pct', 0.0):.1f}%</strong> pts</span>
            <span>Bench: <strong style="color: {theme.SPURS_SILVER};">{sb.get('bench_scoring_share_pct', 0.0):.1f}%</strong> pts</span>
          </div>
        </div>

        <!-- Clutch Execution & Composure -->
        <div style="background: {theme.SHADOW_BLACK}; padding: 16px; border-radius: 6px; border: 1px solid {theme.COURT_LINE}; display: flex; flex-direction: column; justify-content: space-between;">
          <div>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
              <span style="font-family: {theme.FONT_STENCIL}; font-size: 0.82rem; color: {theme.SPURS_SILVER}; letter-spacing: 0.08em; text-transform: uppercase;">
                Close Games
              </span>
              <span style="font-family: {theme.FONT_MONO}; font-size: 0.72rem; color: {theme.FIESTA_ORANGE};">
                decided by &le; 5
              </span>
            </div>

            <div style="font-size: 1.5rem; font-family: {theme.FONT_MONO}; font-weight: 700; color: {theme.COURT_WHITE}; margin-bottom: 4px;">
              {clutch.get('clutch_record', '0-0')} <span style="font-size: 0.9rem; font-weight: normal; color: {theme.SPURS_SILVER};">({clutch.get('clutch_win_pct', 0.0):.1f}% won)</span>
            </div>
            <div style="font-size: 0.82rem; color: {theme.TEXT_MUTED}; margin-bottom: 12px;">
              {composure_html}
            </div>
          </div>

        </div>
      </div>
    </div>
    """

    divs_html = command_center_html + _spotlight_html(games, player_logs) + _season_honors_html(games, player_logs)
    for i, (title, fig, height) in enumerate(figures):
        div_id    = title.lower().replace(" ", "_").replace("/", "_").replace("%", "pct")
        include_js = "cdn" if i == 0 else False
        fig.update_layout(height=height)
        chart_div = theme.chart_html(fig, div_id, include_plotlyjs=include_js)
        divs_html += f"""
        <section class="chart-section">
            <h2 class="chart-title">{title}</h2>
            {chart_div}
        </section>
        """

    season_s = f"{season}-{str(season + 1)[-2:]}"
    html = theme.page_html(
        title="Season Dashboard",
        subtitle="How the team is playing: results, the four factors, who plays well together, and close games.",
        body_content=divs_html,
        current_slug="dashboard",
        badge=f"{season_s} Season",
        games_played=int((games["status"] == "Final").sum()) if not games.empty else 0,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path


def _spotlight_html(games: pd.DataFrame, player_logs: pd.DataFrame) -> str:
    """Valiente, Compinche, Breakout and Hot Hand from completed games."""
    from analysis.performers import MIN_BASELINE_GAMES, game_performers, hot_hand
    from viz.avatars import avatar_html, player_link

    if player_logs.empty or games.empty:
        return ""
    finals = games[games["status"] == "Final"].sort_values(["game_date", "game_id"])
    if finals.empty:
        return ""
    player_logs = player_logs[player_logs["game_id"].isin(finals["game_id"])]
    perf = game_performers(player_logs, finals.iloc[-1]["game_id"])
    hot = hot_hand(player_logs)
    potg = perf.get("player_of_the_game")
    if not potg:
        return ""

    g = finals.iloc[-1]
    date = pd.to_datetime(g["game_date"])
    matchup = escape(
        f'{date:%b} {date.day} · {g["result"]} {int(g["pts"])}-{int(g["opp_pts"])} '
        f'{"vs." if g["home_away"] == "H" else "@"} {g["opponent_abbr"]}'
    )

    def tile(kicker: str, color: str, name: str, line: str, foot: str) -> str:
        who = name if name == "&mdash;" else f'<span class="with-avatar">{avatar_html(name, "lg")}<span>{player_link(name)}</span></span>'
        return f"""
        <div style="background: {theme.SHADOW_BLACK}; border: 1px solid {theme.COURT_LINE}; border-left: 6px solid {color}; padding: 16px;">
          <div style="font-family: {theme.FONT_HEADING}; font-size: 1.05rem; letter-spacing: 0.14em; text-transform: uppercase; color: {color};">{kicker}</div>
          <div style="font-family: {theme.FONT_DISPLAY}; font-size: 1.5rem; line-height: 1.1; margin: 10px 0 8px; color: {theme.COURT_WHITE};">{who}</div>
          <div style="font-family: {theme.FONT_LED}; font-size: 1.6rem; color: {theme.FIESTA_ORANGE};">{line}</div>
          <div style="font-size: 0.82rem; color: {theme.TEXT_MUTED}; margin-top: 4px;">{foot}</div>
        </div>"""

    tiles = [tile("El Valiente &middot; Player of the Game", theme.FIESTA_TEAL, potg["player_name"], potg["line"],
                  f'{matchup} &middot; Game Score {potg["game_score"]}')]
    compinche = perf.get("compinche")
    if compinche:
        tiles.append(tile("El Compinche &middot; Sidekick", theme.FIESTA_ORANGE, compinche["player_name"], compinche["line"],
                          f'{matchup} &middot; Game Score {compinche["game_score"]}'))
    else:
        tiles.append(tile("El Compinche &middot; Sidekick", theme.FIESTA_ORANGE, "&mdash;", "",
                          "No eligible teammate in this box score."))
    if perf.get("breakout"):
        b = perf["breakout"]
        tiles.append(tile("Breakout", theme.FIESTA_FUSCHIA, b["player_name"], b["line"],
                          f'Game Score {b["game_score"]}, {b["above_avg"]:+.1f} above his {b["season_avg"]} average'))
    else:
        tiles.append(tile("Breakout", theme.FIESTA_FUSCHIA, "&mdash;", "",
                          theme.small_sample_badge(
                              f"Flags a player well above his own average once players have {MIN_BASELINE_GAMES} games")
                          if player_logs["game_id"].nunique() <= MIN_BASELINE_GAMES
                          else "No one far above his usual level last game."))
    if hot:
        tiles.append(tile(f'Hot Hand &middot; last {hot["window"]}', theme.FIESTA_ORANGE, hot["player_name"], hot["line"],
                          f'Average Game Score {hot["game_score"]} over his last {hot["games"]} games'))

    return f"""
    <section class="card" id="spotlight">
      <h2>Player Spotlight</h2>
      <p style="color: {theme.TEXT_MUTED}; font-size: 0.88rem; margin: -6px 0 14px;">
        Last game: El Valiente had the highest Game Score, a one-number box score rating.
        El Compinche is the top teammate alongside him.
        <a href="#honor-roll" style="color: {theme.FIESTA_TEAL};">See every game's honorees &darr;</a>
      </p>
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(min(260px, 100%), 1fr)); gap: 14px;">
        {"".join(tiles)}
      </div>
    </section>
    """


def _season_honors_html(games: pd.DataFrame, player_logs: pd.DataFrame) -> str:
    """Running Valiente and Compinche table, including games awaiting box scores."""
    from analysis.performers import season_game_honors
    from viz.avatars import avatar_html, player_link

    history = season_game_honors(games, player_logs)

    def honoree(honor: dict | None, missing: str) -> str:
        if not honor:
            return f'<span class="honor-note">{missing}</span>'
        return (
            f'<span class="with-avatar">{avatar_html(honor["player_name"], "sm")}'
            f'<span>{player_link(honor["player_name"])}</span></span>'
            f'<div class="honor-note">{escape(honor["line"])} &middot; GmSc {honor["game_score"]:.1f}</div>'
        )

    rows = []
    for game in history:
        date = pd.to_datetime(game["game_date"])
        result = escape(game["result"])
        rows.append(
            f'<tr data-game-id="{escape(str(game["game_id"]), quote=True)}">'
            f'<th scope="row"><time datetime="{date:%Y-%m-%d}">{date:%b} {date.day}</time></th>'
            f'<td>{"vs." if game["home_away"] == "H" else "@"} {escape(game["opponent_abbr"])}'
            f'<div class="honor-note {result}">{result} {int(game["pts"])}-{int(game["opp_pts"])}</div></td>'
            f'<td class="honoree valiente"><div class="honor-label" aria-hidden="true">El Valiente</div>'
            f'{honoree(game.get("player_of_the_game"), "Box score pending")}</td>'
            f'<td class="honoree compinche"><div class="honor-label" aria-hidden="true">El Compinche</div>'
            f'{honoree(game.get("compinche"), "No eligible teammate" if game.get("player_of_the_game") else "Box score pending")}</td>'
            '</tr>'
        )
    table = f"""
      <div class="honors-scroll" role="region" aria-label="Season game honors" tabindex="0">
        <table class="honors-table">
          <thead><tr><th scope="col">Date</th><th scope="col">Game</th>
            <th scope="col">El Valiente <span>Player of the Game</span></th>
            <th scope="col">El Compinche <span>Sidekick</span></th></tr></thead>
          <tbody>{"".join(rows)}</tbody>
        </table>
      </div>""".strip() if rows else '<p class="honor-note">Honors appear after the first completed game.</p>'
    return f"""
    <style>
      #honor-roll .honors-scroll {{ overflow: auto; max-height: 560px; }}
      #honor-roll .honors-scroll:focus-visible {{ outline: 2px solid {theme.FIESTA_TEAL}; outline-offset: 3px; }}
      #honor-roll .honors-table {{ width: 100%; min-width: 660px; border-collapse: collapse; text-align: left; }}
      #honor-roll th, #honor-roll td {{ padding: 12px; border-bottom: 1px solid {theme.COURT_LINE}; vertical-align: top; }}
      #honor-roll thead th {{ position: sticky; top: 0; z-index: 1; background: {theme.SHADOW_BLACK}; font-family: {theme.FONT_HEADING}; font-size: 1.15rem; }}
      #honor-roll thead th:nth-child(3) {{ color: {theme.FIESTA_TEAL}; }}
      #honor-roll thead th:nth-child(4) {{ color: {theme.FIESTA_ORANGE}; }}
      #honor-roll thead span {{ display: block; color: {theme.TEXT_MUTED}; font-size: 0.85rem; }}
      #honor-roll tbody th {{ white-space: nowrap; font-family: {theme.FONT_MONO}; font-weight: normal; }}
      #honor-roll .honor-note {{ color: {theme.TEXT_MUTED}; font-size: 0.8rem; margin-top: 5px; }}
      #honor-roll .honor-label {{ display: none; }}
      #honor-roll .W {{ color: {theme.WIN}; }}
      #honor-roll .L {{ color: {theme.LOSS}; }}
      @media (max-width: 640px) {{
        #honor-roll .honors-table {{ display: block; min-width: 0; }}
        #honor-roll thead {{ position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); }}
        #honor-roll tbody {{ display: block; }}
        #honor-roll tbody tr {{ display: grid; grid-template-columns: auto 1fr; gap: 12px; padding: 14px 0; border-bottom: 1px solid {theme.COURT_LINE}; }}
        #honor-roll tbody th, #honor-roll td {{ padding: 0; border: 0; min-width: 0; }}
        #honor-roll td:nth-child(2) {{ text-align: right; }}
        #honor-roll .honoree {{ grid-column: 1 / -1; }}
        #honor-roll .honor-label {{ display: block; color: {theme.FIESTA_TEAL}; font-family: {theme.FONT_HEADING}; font-size: 1.1rem; margin-bottom: 6px; }}
        #honor-roll .compinche .honor-label {{ color: {theme.FIESTA_ORANGE}; }}
        #honor-roll .with-avatar {{ overflow-wrap: anywhere; }}
      }}
    </style>
    <section class="card" id="honor-roll">
      <h2>El Valiente &amp; El Compinche &middot; Season Honors</h2>
      <p class="honor-note" style="margin-bottom: 16px;">
        Every completed game, newest first. The two highest Game Scores earn the honors;
        ties go to minutes played, then name. Players must have played to qualify.
      </p>
      {table}
    </section>
    """.rstrip() + "\n"


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
