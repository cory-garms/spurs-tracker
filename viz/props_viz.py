"""
Player Props Visualizer — builds docs/props_board.html.

Tonight's board (current-season lines in next-game context) and a
year-over-year board (last-season lines with 95% hit-rate ranges), adhering
to the Spurs theme system. The analytics live in analysis/props.py; the
next-game preview lives in viz/matchup_viz.py.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

import config
from config import TEAM_ABBR, SEASON, season_str
from viz import theme
from viz.avatars import avatar_html, player_link
from viz.matchup_viz import _short
from analysis.matchup_preview import SHRINK_GAMES
from analysis.props import (
    MIN_PREV_GAMES, RECENT_GAMES, balanced_line, half_point_line, matchup_factors, prop_rows, rest_days,
)
from analysis.wemby import get_wemby_logs
from data.league import load_league_standings
from data.schedule import load_schedule, next_game, now_utc


def _previous_season_logs(team_abbr: str, season: int) -> pd.DataFrame:
    team_id = config.TEAMS[team_abbr.upper()]["id"]
    path = config.CACHE_DIR / f"player_game_log_{team_id}_{season - 1}.parquet"
    return pd.read_parquet(path) if path.exists() else pd.DataFrame()


def _pct_change(factor: float) -> str:
    return f"{(factor - 1) * 100:+.1f}%"


def _days(n: int | None) -> str:
    if n is None:
        return "—"
    return "Back-to-back" if n == 0 else f"{n} day{'s' if n != 1 else ''}"


def _css() -> str:
    t = theme
    return f"""
    <style>
      .pb-when {{ color: {t.SPURS_SILVER}; margin: -4px 0 16px; font-size: 0.95rem; }}
      .pb-chips {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; }}
      .pb-chip {{ background: {t.SHADOW_BLACK}; border: 1px solid {t.COURT_LINE}; padding: 12px 14px; }}
      .pb-chip .lbl {{ font-family: {t.FONT_HEADING}; font-size: 1.05rem; letter-spacing: 0.08em; text-transform: uppercase;
                       color: {t.SPURS_SILVER}; }}
      .pb-chip .val {{ font-family: {t.FONT_LED}; font-size: 2rem; color: {t.COURT_WHITE}; line-height: 1.1; }}
      .pb-chip .val .chg {{ font-size: 1.3rem; color: {t.FIESTA_ORANGE}; margin-left: 6px; }}
      .pb-chip .sub {{ color: {t.TEXT_MUTED}; font-size: 0.8rem; line-height: 1.4; }}
      .pb-how {{ color: {t.TEXT_MUTED}; font-size: 0.85rem; line-height: 1.5; margin-top: 12px; }}
      .pb-table {{ width: 100%; border-collapse: collapse; font-size: 0.9rem; text-align: left; }}
      .pb-table th, .pb-table td {{ padding: 9px 10px; border-bottom: 1px solid {t.COURT_LINE}; }}
      .pb-table th {{ font-family: {t.FONT_STENCIL}; text-transform: uppercase; color: {t.SPURS_SILVER};
                      border-bottom-width: 2px; white-space: nowrap; }}
      .pb-table td.num {{ font-family: {t.FONT_MONO}; white-space: nowrap; }}
      .pb-table td.line {{ font-family: {t.FONT_MONO}; font-weight: 700; color: {t.FIESTA_ORANGE}; white-space: nowrap; }}
      .pb-table .sub {{ display: block; font-family: {t.FONT_BODY}; font-weight: 400; font-size: 0.72rem; color: {t.TEXT_MUTED}; }}
      .pb-table td.stat {{ color: {t.SPURS_SILVER}; }}
      .pb-table td.who {{ font-weight: 700; color: {t.COURT_WHITE}; }}
      .pb-over {{ color: {t.FIESTA_TEAL}; font-weight: 700; }}
      .pb-under {{ color: {t.FIESTA_FUSCHIA}; font-weight: 700; }}
      .pb-close {{ color: {t.TEXT_MUTED}; }}
      .pb-rng {{ position: relative; display: inline-block; width: 110px; height: 10px; vertical-align: middle;
                 background: {t.SHADOW_BLACK}; border: 1px solid {t.COURT_LINE}; margin-right: 8px; }}
      .pb-rng .band {{ position: absolute; top: 1px; bottom: 1px; opacity: 0.55; }}
      .pb-rng .mid {{ position: absolute; left: 50%; top: -3px; bottom: -3px; width: 1px; background: {t.SPURS_SILVER}; }}
      .pb-rng .dot {{ position: absolute; top: 50%; width: 8px; height: 8px; margin: -4px 0 0 -4px; border-radius: 50%; }}
      .pb-note {{ color: {t.TEXT_MUTED}; font-size: 0.85rem; margin-top: 10px; }}
      .pb-short {{ display: none; }}
      .pb-nocase {{ text-transform: none; }}
      @media (max-width: 640px) {{
        .pb-table {{ font-size: 0.82rem; }}
        .pb-table th, .pb-table td {{ padding: 7px 5px; }}
        .pb-table .avatar, .pb-wide, .pb-long {{ display: none; }}
        .pb-short {{ display: inline; }}
        .pb-rng {{ width: 56px; margin-right: 4px; }}
      }}
    </style>"""


def _range_bar(hits: int, n: int, lo: float, hi: float, lean: str | None) -> str:
    color = {"over": theme.FIESTA_TEAL, "under": theme.FIESTA_FUSCHIA}.get(lean, theme.SPURS_STEEL)
    point = hits / n * 100 if n else 50
    return (
        f'<span class="pb-rng" role="img" aria-label="95% range {lo:.0%} to {hi:.0%}">'
        f'<span class="band" style="left:{lo * 100:.1f}%; width:{(hi - lo) * 100:.1f}%; background:{color};"></span>'
        f'<span class="mid"></span>'
        f'<span class="dot" style="left:{point:.1f}%; background:{color};"></span></span>'
        f'<span class="pb-long">{lo:.0%}&ndash;{hi:.0%}</span>'
    )


STAT_SHORT = {"Points": "PTS", "Assists": "AST", "Rebounds": "REB", "3-Pointers Made": "3PM", "Blocks": "BLK"}


def _stat_cell(label: str) -> str:
    """Full stat name on wide screens, box-score abbreviation on phones."""
    return (f'<td class="stat"><span class="pb-long">{label}</span>'
            f'<span class="pb-short">{STAT_SHORT.get(label, label)}</span></td>')


def _player_cell(name: str) -> str:
    return f'<td class="who"><span class="with-avatar">{avatar_html(name, "sm")}<span>{player_link(name)}</span></span></td>'


def _tonight_section(nxt: dict, factors: dict, rows: list[dict], games: pd.DataFrame,
                     schedule: pd.DataFrame, team: str) -> str:
    opp = nxt["opponent"]
    us, them = _short(team), _short(opp)
    venue_word = "Home" if nxt["is_home"] else "Road"
    at = "vs." if nxt["is_home"] else "@"

    finals = games[games["status"] == "Final"] if not games.empty else games
    side = finals[finals["home_away"] == ("H" if nxt["is_home"] else "A")] if not finals.empty else finals
    side_w = int((side["result"] == "W").sum()) if not side.empty else 0
    side_rec = f"{side_w}-{len(side) - side_w}"

    chips = []
    if factors["available"]:
        chips.append(f"""
        <div class="pb-chip"><div class="lbl">Expected pace</div>
          <div class="val">{factors['game_pace']:.1f}<span class="chg">{_pct_change(factors['pace_factor'])}</span></div>
          <div class="sub">{us} {factors['team_pace']:.1f} &middot; {them} {factors['opp_pace']:.1f} possessions per 48.
            Scales every stat.</div></div>""")
        chips.append(f"""
        <div class="pb-chip"><div class="lbl">{them} defense</div>
          <div class="val">{factors['opp_drtg_adj']:.1f}<span class="chg">{_pct_change(factors['def_factor'])}</span></div>
          <div class="sub">{factors['opp_drtg']:.1f} allowed per 100 ({factors['opp_drtg_rank']} of {factors['teams']}),
            weighted toward league {factors['league_drtg']:.1f} over {factors['opp_games']} games. Scales points.</div></div>""")
    rest_us = rest_days(schedule, team, nxt["tipoff_local"])
    rest_them = rest_days(schedule, opp, nxt["tipoff_local"])
    chips.append(f"""
        <div class="pb-chip"><div class="lbl">Rest</div>
          <div class="val">{_days(rest_us)}</div>
          <div class="sub">Days off for the {us} before tip. {them}: {_days(rest_them).lower()}.</div></div>""")
    chips.append(f"""
        <div class="pb-chip"><div class="lbl">Venue</div>
          <div class="val">{venue_word}</div>
          <div class="sub">{us} are {side_rec} in {venue_word.lower()} games. The {venue_word} column counts only those.</div></div>""")

    body_rows = ""
    for r in rows:
        venue_cell = f'{r["venue_hits"]}/{r["venue_n"]}' if r["venue_n"] else "&mdash;"
        body_rows += f"""
          <tr>{_player_cell(r['player_name'])}
            {_stat_cell(r['stat'])}
            <td class="line">{r['current_line']:g}<span class="sub">median {r['median']:g}</span></td>
            <td class="num">{r['tonight']:.1f}<span class="sub">{r['tonight'] - r['median']:+.1f}<span class="pb-long"> from matchup</span></span></td>
            <td class="num">{r['recent_hits']}/{r['recent_n']}</td>
            <td class="num">{venue_cell}</td>
          </tr>"""

    how = (
        "The line is the half point beside his season median that splits his games closest to 50/50. "
        "Tonight est. is that median scaled by the pace change"
        + (" and, for points, by the opponent's defense" if factors["available"] else "")
        + f". Defense is pulled toward league average until about {SHRINK_GAMES} games are in, as in the "
        f"Next Game projection. Last {RECENT_GAMES} and {venue_word} count games over the line."
    )
    if not factors["available"]:
        how += " League ratings aren't cached yet, so no matchup adjustment is applied."

    return f"""
    <section class="card" style="border-top: 3px solid {theme.FIESTA_TEAL};">
      <h2>🎯 Tonight's Board &middot; {at} {opp}</h2>
      <p class="pb-when">{nxt['when']} &middot; {nxt['arena']}, {nxt['city']}</p>
      <div class="pb-chips">{''.join(chips)}</div>
      <p class="pb-how">{how}</p>
      <div style="overflow-x: auto; margin-top: 16px;">
        <table class="pb-table">
          <thead><tr><th>Player</th><th>Stat</th><th>Line</th><th><span class="pb-long">Tonight est.</span><span class="pb-short">Tonight</span></th>
            <th>Last {RECENT_GAMES}</th><th>{venue_word}</th></tr></thead>
          <tbody>{body_rows}</tbody>
        </table>
      </div>
    </section>"""


def _last_year_section(rows: list[dict]) -> str:
    with_prev = [r for r in rows if r["prev_line"] is not None]
    without = sorted({r["player_name"] for r in rows if r["prev_line"] is None})

    body_rows = ""
    for r in with_prev:
        n, hits, lean = r["games"], r["prev_hits"], r["prev_lean"]
        lo, hi = r["prev_range"]
        cls = {"over": "pb-over", "under": "pb-under"}.get(lean, "pb-close")
        read = {"over": "Over", "under": "Under"}.get(lean, "Too close")
        body_rows += f"""
          <tr>{_player_cell(r['player_name'])}
            {_stat_cell(r['stat'])}
            <td class="line">{r['prev_line']:g}</td>
            <td class="num pb-wide">{r['mean']:.1f} &plusmn; {r['sd']:.1f}</td>
            <td class="num {cls}">{hits}/{n}<span class="pb-long"> ({hits / n:.0%})</span></td>
            <td class="num">{_range_bar(hits, n, lo, hi, lean)}</td>
            <td class="{cls}">{read}</td>
          </tr>"""

    note = ""
    if without:
        note = (f'<p class="pb-note">No last-season line for {", ".join(without)}: fewer than '
                f'{MIN_PREV_GAMES} games with the Spurs last season.</p>')
    table = (f"""
      <div style="overflow-x: auto;">
        <table class="pb-table">
          <thead><tr><th>Player</th><th>Stat</th><th><span class="pb-long">Last-season line</span><span class="pb-short">Line</span></th><th class="pb-wide">This season &plusmn; 1<span class="pb-nocase">&sigma;</span></th>
            <th>Over</th><th><span class="pb-long">95% range</span><span class="pb-short">Range</span></th><th>Read</th></tr></thead>
          <tbody>{body_rows}</tbody>
        </table>
      </div>""" if with_prev else '<p class="pb-note">No last-season baselines yet.</p>')

    return f"""
    <section class="card">
      <h2>📈 Ahead of Last Year?</h2>
      <p class="pb-how" style="margin: -4px 0 14px;">How often each player has cleared last season's average this season.
        The bar shows where his true hit rate plausibly sits given the games so far; the line through it is 50%.
        A read of Over or Under needs the whole range on one side of 50%.</p>
      {table}{note}
    </section>"""


def _blocks_chart(wemby: pd.DataFrame, prev_wemby: pd.DataFrame) -> go.Figure:
    """Every block count from 0 to his high, so gaps show as gaps, with both reference lines."""
    fig = go.Figure()
    if wemby.empty:
        return fig
    counts = wemby["blk"].astype(int).value_counts().reindex(range(0, int(wemby["blk"].max()) + 1), fill_value=0)
    fig.add_trace(go.Bar(
        x=list(counts.index), y=counts.values, marker_color=theme.FIESTA_TEAL,
        text=[f"{v} game{'s' if v != 1 else ''}" if v else "" for v in counts.values],
        textposition="outside", hovertemplate="%{x} blocks: %{y} game(s)<extra></extra>",
    ))
    cur = balanced_line(wemby["blk"].astype(float))
    prev = half_point_line(float(prev_wemby["blk"].mean())) if len(prev_wemby) >= MIN_PREV_GAMES else None
    if prev is None or prev == cur:
        label = f"Line {cur:g}" + (" (this season and last)" if prev == cur else "")
        fig.add_vline(x=cur, line_dash="dot", line_color=theme.FIESTA_ORANGE, annotation_text=label)
    else:
        fig.add_vline(x=cur, line_dash="dot", line_color=theme.FIESTA_ORANGE,
                      annotation_text=f"This season {cur:g}", annotation_position="top right")
        fig.add_vline(x=prev, line_dash="dash", line_color=theme.SPURS_SILVER,
                      annotation_text=f"Last season {prev:g}", annotation_position="top left")
    theme.apply(
        fig, xaxis_title="Blocks in a game", yaxis_title="Games", xaxis_dtick=1,
        yaxis_dtick=1 if counts.max() <= 10 else None, yaxis_range=[0, max(counts.values) * 1.25 + 1],
    )
    return fig


def build_props_board_page(
    games: pd.DataFrame,
    player_logs: pd.DataFrame,
    season: int = SEASON,
    team_abbr: str = TEAM_ABBR,
    output_path: Path | None = None,
) -> Path:
    """Build and write the Player Props board HTML page."""
    if output_path is None:
        output_path = theme.page_path("board", team_abbr, season)
    team = team_abbr.upper()

    prev_logs = _previous_season_logs(team, season)
    schedule = load_schedule(season)
    nxt = next_game(schedule, team, now_utc())
    factors = (matchup_factors(load_league_standings(season), team, nxt["opponent"])
               if nxt else {"pace_factor": 1.0, "points_factor": 1.0, "available": False})
    venue = ("H" if nxt["is_home"] else "A") if nxt else None
    rows = prop_rows(player_logs, prev_logs, games, factors, venue)

    wemby = get_wemby_logs(player_logs)
    wemby = wemby[wemby["min"] > 0] if not wemby.empty else wemby
    prev_wemby = get_wemby_logs(prev_logs)
    prev_wemby = prev_wemby[prev_wemby["min"] > 0] if not prev_wemby.empty else prev_wemby
    fig_blocks = _blocks_chart(wemby, prev_wemby)
    fig_blocks.update_layout(height=400)
    div_blocks = theme.chart_html(fig_blocks, "props_blocks_dist", include_plotlyjs="cdn")

    tonight_html = (_tonight_section(nxt, factors, rows, games, schedule, team) if nxt and rows else
                    '<section class="card"><h2>🎯 Tonight\'s Board</h2>'
                    '<p class="pb-note">No upcoming game on the schedule.</p></section>')

    body_content = _css() + f"""
    <div class="card" style="border-top: 3px solid {theme.FIESTA_ORANGE}; margin-bottom: 24px;">
      <h2 style="border-bottom: none; margin-bottom: 8px;">🎲 How to read this</h2>
      <p style="color: {theme.SPURS_SILVER}; font-size: 0.95rem; line-height: 1.6;">
        The eight players getting the most minutes, each with points and their most notable other stat. Every market
        has two lines, both at the half point so there are no pushes. <strong>Tonight's Board</strong> sets its line
        at the player's typical night this season and adjusts for the next opponent.
        <strong>Ahead of Last Year?</strong> uses last season's average and shows how sure we can be about each hit
        rate. These are not sportsbook odds. For fun and analysis, not betting advice.
      </p>
    </div>
    {tonight_html}
    {_last_year_section(rows)}
    <section class="chart-section">
      <h2 class="chart-title">👽 Wemby Blocks per Game</h2>
      {div_blocks}
    </section>
    """

    season_s = season_str(season)
    html = theme.page_html(
        title="Player Props",
        subtitle="Tonight's lines in context, and who is beating last season. For fun and analysis, not betting advice.",
        body_content=body_content,
        current_slug="board",
        badge=f"{season_s} Props",
        games_played=int((games["status"] == "Final").sum()) if not games.empty else 0,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path
