"""
Next Game Visualizer — builds docs/matchup.html, a preview of the Spurs' next game.

Tale of the tape, recent form, players to watch on both sides, head-to-head and
one transparent projection. Everything is computed from the cached schedule,
league ratings and box scores at build time.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

import config
from config import TEAM_ABBR, SEASON, TEAMS, season_str
from viz import theme
from viz.avatars import avatar_html
from analysis.matchup_preview import (
    HOME_COURT_PTS, SHRINK_GAMES, last_season_series, players_to_watch, projection,
    spurs_players_from_logs, tale_of_the_tape,
)
from data.league import load_league_standings, load_team_players
from data.schedule import head_to_head, load_schedule, next_game, now_utc, recent_results


def _short(abbr: str) -> str:
    """'San Antonio Spurs' -> 'Spurs', 'Portland Trail Blazers' -> 'Trail Blazers'."""
    name = TEAMS[abbr]["name"]
    return "Trail Blazers" if name.endswith("Trail Blazers") else name.split()[-1]


def _record(standings: pd.DataFrame, abbr: str) -> str:
    row = standings[standings["team_abbr"] == abbr]
    return f"{int(row['wins'].iloc[0])}-{int(row['losses'].iloc[0])}" if not row.empty else ""


def _css() -> str:
    t = theme
    return f"""
    <style>
      .ng-teams {{ display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; gap: 12px; text-align: center; }}
      .ng-team .abbr {{ font-family: {t.FONT_DISPLAY}; font-size: clamp(2.2rem, 7vw, 3.6rem); line-height: 1;
                        transform: skewX(-9deg); text-shadow: 3px 3px 0 {t.FIESTA_FUSCHIA}, 6px 6px 0 {t.FIESTA_TEAL}; }}
      .ng-team .name {{ font-family: {t.FONT_HEADING}; font-size: 1.3rem; letter-spacing: 0.1em; text-transform: uppercase;
                        color: {t.SPURS_SILVER}; margin-top: 8px; }}
      .ng-team .rec {{ font-family: {t.FONT_LED}; font-size: 2rem; color: {t.FIESTA_ORANGE}; }}
      .ng-vs {{ font-family: {t.FONT_HEADING}; font-size: 1.6rem; color: {t.TEXT_MUTED}; }}
      .ng-proj {{ margin-top: 20px; padding-top: 16px; border-top: 2px dashed {t.COURT_LINE}; text-align: center; }}
      .ng-proj .big {{ font-family: {t.FONT_LED}; font-size: clamp(1.8rem, 5vw, 2.6rem); color: {t.COURT_WHITE}; }}
      .ng-proj .how {{ color: {t.TEXT_MUTED}; font-size: 0.85rem; max-width: 640px; margin: 6px auto 0; line-height: 1.5; }}
      .ng-table {{ width: 100%; border-collapse: collapse; font-size: 0.95rem; }}
      .ng-table th, .ng-table td {{ padding: 9px 10px; border-bottom: 1px solid {t.COURT_LINE}; }}
      .ng-table th {{ font-family: {t.FONT_HEADING}; font-size: 1.1rem; letter-spacing: 0.08em; text-transform: uppercase;
                      color: {t.SPURS_SILVER}; font-weight: 600; }}
      .ng-table td.num {{ font-family: {t.FONT_MONO}; text-align: center; white-space: nowrap; }}
      .ng-table td.num .rk {{ color: {t.TEXT_MUTED}; font-size: 0.75rem; margin-left: 4px; }}
      .ng-table td.edge {{ color: {t.FIESTA_TEAL}; font-weight: 700; }}
      .ng-table td.edge.them {{ color: {t.FIESTA_FUSCHIA}; }}
      .ng-cols {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 18px; }}
      .ng-cols h3 {{ font-family: {t.FONT_HEADING}; font-size: 1.25rem; letter-spacing: 0.1em; text-transform: uppercase;
                     color: {t.SPURS_SILVER}; margin-bottom: 10px; font-weight: 600; }}
      .ng-list {{ list-style: none; display: flex; flex-direction: column; gap: 8px; }}
      .ng-list li {{ display: flex; align-items: baseline; gap: 10px; background: {t.SHADOW_BLACK};
                     border: 1px solid {t.COURT_LINE}; padding: 8px 12px; }}
      .ng-list li.with-avatar {{ align-items: center; }}
      .ng-list .wl {{ font-family: {t.FONT_LED}; font-size: 1.4rem; width: 1.2em; }}
      .ng-list .wl.W {{ color: {t.FIESTA_TEAL}; }} .ng-list .wl.L {{ color: {t.FIESTA_FUSCHIA}; }}
      .ng-list .main {{ font-family: {t.FONT_MONO}; }}
      .ng-list .sub {{ margin-left: auto; color: {t.TEXT_MUTED}; font-size: 0.8rem; font-family: {t.FONT_MONO}; }}
      .ng-player .who {{ font-weight: 700; }}
      .ng-player .line {{ font-family: {t.FONT_MONO}; font-size: 0.85rem; color: {t.SPURS_SILVER}; }}
      .ng-empty {{ color: {t.TEXT_MUTED}; font-size: 0.9rem; }}
      @media (max-width: 640px) {{ .ng-table {{ font-size: 0.85rem; }} .ng-table th, .ng-table td {{ padding: 7px 5px; }} }}
    </style>"""


def _results_list(items: list[dict], empty: str) -> str:
    if not items:
        return f'<p class="ng-empty">{empty}</p>'
    lis = "".join(
        f'<li><span class="wl {r["result"]}">{r["result"]}</span>'
        f'<span class="main">{r["score"]} {r["venue"]} {r.get("opponent", "")}</span>'
        f'<span class="sub">{r["date"]}</span></li>'
        for r in items
    )
    return f'<ul class="ng-list">{lis}</ul>'


def _players_list(items: list[dict], empty: str) -> str:
    if not items:
        return f'<p class="ng-empty">{empty}</p>'
    lis = "".join(
        f'<li class="ng-player with-avatar">{avatar_html(p["player_name"], "md")}'
        f'<div><div class="who">{p["player_name"]}</div>'
        f'<div class="line">{p["line"]}</div></div>'
        f'<span class="sub">GmSc {p["game_score"]}</span></li>'
        for p in items
    )
    return f'<ul class="ng-list">{lis}</ul>'


def build_matchup_page(
    games: pd.DataFrame,
    player_logs: pd.DataFrame,
    season: int = SEASON,
    team_abbr: str = TEAM_ABBR,
    output_path: Path | None = None,
) -> Path:
    """Build and write the Next Game preview page."""
    if output_path is None:
        output_path = theme.page_path("matchup", team_abbr, season)

    team = team_abbr.upper()
    season_s = season_str(season)
    games_played = int((games["status"] == "Final").sum()) if not games.empty else 0
    schedule = load_schedule(season)
    nxt = next_game(schedule, team, now_utc())
    standings = load_league_standings(season)

    if nxt is None:
        body = f"""{_css()}
        <section class="card"><h2>No upcoming game</h2>
          <p class="ng-empty">There's no {season_s} regular-season game left on the schedule.</p></section>"""
        html = theme.page_html(title="Next Game", subtitle="The season's schedule is complete.",
                               body_content=body, current_slug="matchup", badge=f"{season_s} Season")
        output_path.write_text(html, encoding="utf-8")
        return output_path

    opp = nxt["opponent"]
    us, them = _short(team), _short(opp)
    home, away = (team, opp) if nxt["is_home"] else (opp, team)

    # ---- Matchup header + projection ----
    proj = projection(standings, team, opp, nxt["is_home"])
    if proj:
        fav, pts = (us, proj["margin"]) if proj["margin"] >= 0 else (them, -proj["margin"])
        win = proj["win_prob"] if proj["margin"] >= 0 else 1 - proj["win_prob"]
        early = (theme.small_sample_badge(f"Only {proj['games']} games of data per team, so treat this loosely")
                 if proj["games"] < theme.SMALL_SAMPLE_GAMES else "")
        proj_html = f"""
        <div class="ng-proj">
          <div class="big">Projection: {fav} by {pts:.1f} &middot; {win:.0%} win chance</div>
          <p class="how">From each team's net rating, pulled toward league average until about {SHRINK_GAMES} games are in,
            converted to points at the two teams' pace, plus {HOME_COURT_PTS:.0f} points for home court.</p>
          {early}
        </div>"""
    else:
        proj_html = '<p class="ng-empty">Team ratings aren\'t available yet.</p>'

    header = f"""
    <section class="card">
      <h2>{_short(away)} at {_short(home)}</h2>
      <div class="ng-teams">
        <div class="ng-team"><div class="abbr">{away}</div><div class="name">{_short(away)}</div>
          <div class="rec">{_record(standings, away)}</div></div>
        <div class="ng-vs">@</div>
        <div class="ng-team"><div class="abbr">{home}</div><div class="name">{_short(home)}</div>
          <div class="rec">{_record(standings, home)}</div></div>
      </div>
      {proj_html}
    </section>"""

    # ---- Tale of the tape ----
    tape = tale_of_the_tape(standings, team, opp)
    if tape:
        def cell(val: str, rank: int | None, is_edge: bool, theirs: bool) -> str:
            rk = f'<span class="rk">#{rank}</span>' if rank else ""
            cls = "num edge" + (" them" if theirs else "") if is_edge else "num"
            return f'<td class="{cls}">{val}{rk}</td>'
        rows = "".join(
            f'<tr><td>{r["label"]}</td>'
            f'{cell(r["team"], r["team_rank"], r["edge"] == team, False)}'
            f'{cell(r["opponent"], r["opponent_rank"], r["edge"] == opp, True)}</tr>'
            for r in tape
        )
        edges = sum(r["edge"] == team for r in tape), sum(r["edge"] == opp for r in tape)
        tape_html = f"""
    <section class="card">
      <h2>Tale of the Tape</h2>
      <p class="ng-empty" style="margin: -6px 0 12px;">League rank in small type (1 = best of 30). Highlighted values mark
        who has the edge: {us} {edges[0]}, {them} {edges[1]}.</p>
      <div style="overflow-x: auto;">
        <table class="ng-table">
          <thead><tr><th></th><th style="text-align:center;">{us}</th><th style="text-align:center;">{them}</th></tr></thead>
          <tbody>{rows}</tbody>
        </table>
      </div>
    </section>"""
    else:
        tape_html = ""

    # ---- Recent form ----
    form_html = f"""
    <section class="card">
      <h2>Recent Form</h2>
      <div class="ng-cols">
        <div><h3>{us}</h3>{_results_list(recent_results(schedule, team), "No games yet.")}</div>
        <div><h3>{them}</h3>{_results_list(recent_results(schedule, opp), "No games yet.")}</div>
      </div>
    </section>"""

    # ---- Players to watch ----
    opp_players = load_team_players(TEAMS[opp]["id"], season)
    watch_html = f"""
    <section class="card">
      <h2>Players to Watch</h2>
      <p class="ng-empty" style="margin: -6px 0 12px;">Top three on each side by average Game Score this season.</p>
      <div class="ng-cols">
        <div><h3>{us}</h3>{_players_list(players_to_watch(spurs_players_from_logs(player_logs)), "No games yet.")}</div>
        <div><h3>{them}</h3>{_players_list(players_to_watch(opp_players), "Player stats not fetched yet.")}</div>
      </div>
    </section>"""

    # ---- Head to head ----
    this_season = head_to_head(schedule, team, opp)
    last = last_season_series(TEAMS[team]["id"], opp, season)
    last_w = sum(r["result"] == "W" for r in last)
    h2h_html = f"""
    <section class="card">
      <h2>Head to Head</h2>
      <div class="ng-cols">
        <div><h3>This season</h3>{_results_list(this_season, "First meeting of the season.")}</div>
        <div><h3>Last season{f" ({last_w}-{len(last) - last_w})" if last else ""}</h3>
          {_results_list(last, "No meetings on record.")}</div>
      </div>
    </section>"""

    subtitle = f'{nxt["when"]} &middot; {nxt["arena"]}, {nxt["city"]}' + (f' &middot; TV: {nxt["tv"]}' if nxt["tv"] else "")
    html = theme.page_html(
        title="Next Game",
        subtitle=subtitle,
        body_content=_css() + header + tape_html + form_html + watch_html + h2h_html,
        current_slug="matchup",
        badge=f"vs. {opp}" if nxt["is_home"] else f"@ {opp}",
        games_played=games_played,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path
