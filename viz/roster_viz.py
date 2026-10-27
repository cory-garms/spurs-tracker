"""
La Baraja — the roster as a Lotería deck, plus a page for every player.

Generates docs/roster.html (one emblem card per player, ordered by minutes) and
docs/player_<slug>.html (emblem, season line, Game Score by game, game log and
spotlight honors). Built before the other pages so their player names can link
here.
"""

from __future__ import annotations

from html import escape
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

import config
from config import SEASON, TEAM_ABBR, season_str
from viz import theme
from viz.avatars import avatar_html, card_name, player_page
from analysis.performers import game_performers, game_score


def _season_table(player_logs: pd.DataFrame) -> pd.DataFrame:
    """Per-player season averages over games played, plus Game Score."""
    played = player_logs[player_logs["min"] > 0].copy()
    if played.empty:
        return pd.DataFrame()
    played["gmsc"] = game_score(played)
    played["stocks"] = played["stl"] + played["blk"]
    agg = played.groupby("player_name").agg(
        gp=("game_id", "count"), min=("min", "mean"), pts=("pts", "mean"), reb=("reb", "mean"),
        ast=("ast", "mean"), stocks=("stocks", "mean"), gmsc=("gmsc", "mean"),
        fgm=("fgm", "sum"), fga=("fga", "sum"), fg3m=("fg3m", "sum"), fg3a=("fg3a", "sum"),
        ftm=("ftm", "sum"), fta=("fta", "sum"),
    )
    pct = lambda m, a: (agg[m] / agg[a]).where(agg[a] > 0)
    agg["fg_pct"], agg["fg3_pct"], agg["ft_pct"] = pct("fgm", "fga"), pct("fg3m", "fg3a"), pct("ftm", "fta")
    return agg


def _honors(player_logs: pd.DataFrame) -> dict[str, dict[str, int]]:
    """Player of the Game and Breakout counts per player across the season."""
    counts: dict[str, dict[str, int]] = {}
    for gid in player_logs.drop_duplicates("game_id")["game_id"]:
        perf = game_performers(player_logs, gid)
        for key in ("player_of_the_game", "breakout"):
            if key in perf:
                name = perf[key]["player_name"]
                counts.setdefault(name, {"player_of_the_game": 0, "breakout": 0})[key] += 1
    return counts


def _bio(roster: pd.DataFrame, name: str) -> dict:
    row = roster[roster["player_name"] == name] if not roster.empty else roster
    if row.empty:
        return {"jersey": "", "position": "", "exp": None}
    r = row.iloc[0]
    exp = r.get("years_of_experience")
    return {"jersey": str(r.get("jersey_number") or ""), "position": str(r.get("position") or ""),
            "exp": int(exp) if pd.notna(exp) else None}


def _bio_line(bio: dict, with_number: bool = True) -> str:
    parts = []
    if bio["jersey"] and with_number:
        parts.append(f"#{bio['jersey']}")
    if bio["position"]:
        parts.append(bio["position"])
    if bio["exp"] is not None:
        parts.append("Rookie" if bio["exp"] == 0 else f"{bio['exp']} yr{'s' if bio['exp'] != 1 else ''} exp")
    return " &middot; ".join(parts)


def _css() -> str:
    t = theme
    return f"""
    <style>
      .deck-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 250px), 1fr)); gap: 22px; }}
      .pcard {{ position: relative; display: flex; flex-direction: column; align-items: center; text-align: center; gap: 6px;
                background: {t.SHADOW_BLACK}; border: 2px solid {t.COURT_LINE}; padding: 20px 14px 16px;
                color: inherit; text-decoration: none; transition: transform .12s ease, box-shadow .12s ease, border-color .12s; }}
      a.pcard:hover, a.pcard:focus-visible {{ border-color: {t.COURT_WHITE}; transform: translate(-3px, -3px);
                box-shadow: 6px 6px 0 {t.FIESTA_TEAL}; }}
      /* Jersey number in the card's corner, where a Lotería card prints its number */
      .jersey {{ font-family: {t.FONT_DISPLAY}; line-height: 1; color: {t.COURT_WHITE};
                 text-shadow: 2px 2px 0 {t.FIESTA_FUSCHIA}, 4px 4px 0 {t.FIESTA_TEAL}; }}
      .jersey .hash {{ font-size: 0.55em; vertical-align: 0.55em; margin-right: 1px; color: {t.SPURS_SILVER}; text-shadow: none; }}
      .pcard .jersey {{ position: absolute; top: 10px; left: 14px; font-size: 2.6rem; }}
      .hero .jersey {{ font-size: 4.5rem; }}
      .pcard .emblem {{ font-family: {t.FONT_WESTERN}; font-size: 1.25rem; color: {t.MARIGOLD}; margin-top: 8px; min-height: 1.4em; }}
      .pcard .who {{ font-family: {t.FONT_HEADING}; font-size: 1.45rem; font-weight: 600; letter-spacing: 0.04em;
                     text-transform: uppercase; line-height: 1.05; }}
      .pcard .bio {{ font-family: {t.FONT_MONO}; font-size: 0.78rem; color: {t.TEXT_MUTED}; }}
      .pcard .line {{ font-family: {t.FONT_LED}; font-size: 1.35rem; color: {t.FIESTA_ORANGE}; margin-top: 4px; }}
      .pcard .gs {{ font-size: 0.8rem; color: {t.SPURS_SILVER}; }}
      .pcard.dim {{ opacity: 0.7; }}
      .hero {{ display: flex; gap: 28px; align-items: center; flex-wrap: wrap; }}
      .hero .emblem {{ font-family: {t.FONT_WESTERN}; font-size: 2rem; color: {t.MARIGOLD}; }}
      .tiles {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(96px, 1fr)); gap: 10px; flex: 1; min-width: 260px; }}
      .tile {{ background: {t.SHADOW_BLACK}; border: 1px solid {t.COURT_LINE}; padding: 10px; text-align: center; }}
      .tile .k {{ font-family: {t.FONT_HEADING}; font-size: 1rem; letter-spacing: 0.12em; text-transform: uppercase; color: {t.SPURS_SILVER}; }}
      .tile .v {{ font-family: {t.FONT_LED}; font-size: 2rem; line-height: 1.05; color: {t.COURT_WHITE}; }}
      .honors {{ display: flex; gap: 10px; flex-wrap: wrap; margin-top: 14px; }}
      .log {{ width: 100%; border-collapse: collapse; font-size: 0.88rem; }}
      .log th, .log td {{ padding: 8px 8px; border-bottom: 1px solid {t.COURT_LINE}; text-align: center; white-space: nowrap; }}
      .log th {{ font-family: {t.FONT_HEADING}; font-size: 1.05rem; letter-spacing: 0.08em; color: {t.SPURS_SILVER}; font-weight: 600; }}
      .log td {{ font-family: {t.FONT_MONO}; }}
      .log td.first, .log th.first {{ text-align: left; }}
      .log .W {{ color: {t.FIESTA_TEAL}; }} .log .L {{ color: {t.FIESTA_FUSCHIA}; }}
      .hero-id {{ display: flex; align-items: flex-start; gap: 14px; }}
      @media (max-width: 640px) {{ .hero-id {{ margin: 0 auto; }} .hero .jersey {{ font-size: 3.4rem; }} }}
      .back {{ display: inline-block; margin-bottom: 18px; font-family: {t.FONT_HEADING}; font-size: 1.15rem;
               letter-spacing: 0.08em; text-transform: uppercase; color: {t.MARIGOLD}; text-decoration: none; }}
    </style>"""


def _gmsc_chart(logs: pd.DataFrame, games: pd.DataFrame, name: str) -> go.Figure:
    f = logs.merge(games[["game_id", "result", "opponent_abbr", "home_away"]], on="game_id", how="left")
    f = f.sort_values("game_date")
    f["label"] = [f"{pd.to_datetime(d):%b} {pd.to_datetime(d).day} {'vs' if ha == 'H' else '@'} {o}"
                  for d, ha, o in zip(f["game_date"], f["home_away"], f["opponent_abbr"])]
    colors = [theme.FIESTA_TEAL if r == "W" else theme.FIESTA_FUSCHIA for r in f["result"]]
    fig = go.Figure(go.Bar(x=f["label"], y=f["gmsc"].round(1), marker_color=colors,
                           hovertemplate="%{x}<br>Game Score %{y}<extra></extra>"))
    avg = float(f["gmsc"].mean())
    fig.add_hline(y=avg, line_dash="dot", line_color=theme.MARIGOLD, annotation_text=f"Season avg {avg:.1f}")
    theme.apply(fig, xaxis_title="", yaxis_title="Game Score", showlegend=False, height=340)
    return fig


def build_player_page(name: str, player_logs: pd.DataFrame, games: pd.DataFrame, roster: pd.DataFrame,
                      season_row: pd.Series | None, honors: dict, season: int) -> Path:
    out = config.OUTPUT_DIR / player_page(name)
    season_s = season_str(season)
    bio = _bio(roster, name)
    emblem = card_name(name)
    logs = player_logs[(player_logs["player_name"] == name) & (player_logs["min"] > 0)].copy()
    if not logs.empty:
        logs["gmsc"] = game_score(logs)

    if season_row is not None:
        def tile(k, v):
            return f'<div class="tile"><div class="k">{k}</div><div class="v">{v}</div></div>'
        pct = lambda v: "—" if pd.isna(v) else f"{v:.1%}"
        tiles = "".join([
            tile("GP", int(season_row["gp"])), tile("MIN", f"{season_row['min']:.1f}"),
            tile("PTS", f"{season_row['pts']:.1f}"), tile("REB", f"{season_row['reb']:.1f}"),
            tile("AST", f"{season_row['ast']:.1f}"), tile("STL+BLK", f"{season_row['stocks']:.1f}"),
            tile("FG%", pct(season_row["fg_pct"])), tile("3P%", pct(season_row["fg3_pct"])),
            tile("GmSc", f"{season_row['gmsc']:.1f}"),
        ])
    else:
        tiles = f'<p style="color: {theme.TEXT_MUTED};">Hasn\'t played yet this season.</p>'

    h = honors.get(name, {})
    badges = []
    if h.get("player_of_the_game"):
        badges.append(f'<span class="badge teal">Player of the Game &times;{h["player_of_the_game"]}</span>')
    if h.get("breakout"):
        badges.append(f'<span class="badge fuschia">Breakout &times;{h["breakout"]}</span>')
    honors_html = f'<div class="honors">{"".join(badges)}</div>' if badges else ""

    hero = f"""
    <a class="back" href="{theme.PAGES['roster'][0]}">&larr; La Baraja</a>
    <section class="card">
      <div class="hero">
        <div class="hero-id">
          {f'<div class="jersey"><span class="hash">#</span>{escape(bio["jersey"])}</div>' if bio["jersey"] else ""}
          <div style="text-align: center;">{avatar_html(name, "xl")}
            {f'<div class="emblem">{escape(emblem)}</div>' if emblem else ""}</div>
        </div>
        <div class="tiles">{tiles}</div>
      </div>
      {honors_html}
    </section>"""

    chart = log_html = ""
    if not logs.empty:
        chart = f"""
    <section class="chart-section">
      <h2 class="chart-title">Game Score by Game</h2>
      {theme.chart_html(_gmsc_chart(logs, games, name), f"gmsc_{player_page(name)[7:-5]}", include_plotlyjs="cdn")}
    </section>"""
        g = logs.merge(games[["game_id", "result", "opponent_abbr", "home_away", "pts", "opp_pts"]]
                       .rename(columns={"pts": "team_pts"}), on="game_id", how="left").sort_values("game_date", ascending=False)
        rows = "".join(
            f'<tr><td class="first">{pd.to_datetime(r["game_date"]):%b} {pd.to_datetime(r["game_date"]).day}</td>'
            f'<td>{"vs." if r["home_away"] == "H" else "@"} {r["opponent_abbr"]}</td>'
            f'<td class="{r["result"]}">{r["result"]} {int(r["team_pts"])}-{int(r["opp_pts"])}</td>'
            f'<td>{r["min"]:.0f}</td><td>{int(r["pts"])}</td><td>{int(r["reb"])}</td><td>{int(r["ast"])}</td>'
            f'<td>{int(r["stl"])}</td><td>{int(r["blk"])}</td><td>{int(r["fgm"])}-{int(r["fga"])}</td>'
            f'<td>{int(r["fg3m"])}-{int(r["fg3a"])}</td><td>{int(r["plus_minus"]):+d}</td><td>{r["gmsc"]:.1f}</td></tr>'
            for _, r in g.iterrows()
        )
        log_html = f"""
    <section class="card">
      <h2>Game Log</h2>
      <div style="overflow-x: auto;"><table class="log">
        <thead><tr><th class="first">Date</th><th>Opp</th><th>Result</th><th>MIN</th><th>PTS</th><th>REB</th>
          <th>AST</th><th>STL</th><th>BLK</th><th>FG</th><th>3PT</th><th>+/-</th><th>GmSc</th></tr></thead>
        <tbody>{rows}</tbody></table></div>
    </section>"""

    subtitle = _bio_line(bio) + (f" &middot; {escape(emblem)}" if emblem else "")
    html = theme.page_html(
        title=escape(name), subtitle=subtitle or "San Antonio Spurs",
        body_content=_css() + hero + chart + log_html, current_slug="player",
        badge=f"{season_s} Season", games_played=int((games["status"] == "Final").sum()) if not games.empty else 0,
    )
    out.write_text(html, encoding="utf-8")
    return out


def build_roster_pages(games: pd.DataFrame, player_logs: pd.DataFrame, roster: pd.DataFrame,
                       season: int = SEASON, team_abbr: str = TEAM_ABBR) -> list[Path]:
    """Write roster.html and every player page; returns the paths written."""
    if team_abbr.upper() != config.TEAM_ABBR or season != config.SEASON:
        return []  # player pages use flat, season-less filenames; only the live season gets them
    season_s = season_str(season)
    table = _season_table(player_logs) if not player_logs.empty else pd.DataFrame()
    honors = _honors(player_logs) if not player_logs.empty else {}

    names = list(table.sort_values("min", ascending=False).index) if not table.empty else []
    others = [n for n in (roster["player_name"].tolist() if not roster.empty else []) if n not in names]
    written = [build_player_page(n, player_logs, games, roster, table.loc[n] if n in table.index else None,
                                 honors, season) for n in names + others]

    def card(n: str) -> str:
        bio = _bio(roster, n)
        emblem = card_name(n)
        if n in table.index:
            r = table.loc[n]
            line = f"{r['pts']:.1f} PTS · {r['reb']:.1f} REB · {r['ast']:.1f} AST"
            potg = honors.get(n, {}).get("player_of_the_game", 0)
            gs = f"GmSc {r['gmsc']:.1f} &middot; {int(r['gp'])} GP" + (f" &middot; &#9733;&times;{potg}" if potg else "")
            dim = ""
        else:
            line, gs, dim = "&nbsp;", "Yet to play", " dim"
        number = f'<span class="jersey"><span class="hash">#</span>{escape(bio["jersey"])}</span>' if bio["jersey"] else ""
        return (f'<a class="pcard{dim}" href="{player_page(n)}">{number}{avatar_html(n, "lg")}'
                f'<div class="emblem">{escape(emblem) if emblem else ""}</div>'
                f'<div class="who">{escape(n)}</div><div class="bio">{_bio_line(bio, with_number=False)}</div>'
                f'<div class="line">{line}</div><div class="gs">{gs}</div></a>')

    body = _css() + f"""
    <section class="card">
      <h2>The Deck</h2>
      <p style="color: {theme.TEXT_MUTED}; font-size: 0.9rem; margin: -6px 0 18px;">
        Every player gets a Lotería emblem. Ordered by minutes per game; tap a card for his season.
        &#9733; counts Player of the Game honors.</p>
      <div class="deck-grid">{"".join(card(n) for n in names)}</div>
    </section>"""
    if others:
        body += f"""
    <section class="card">
      <h2>Yet to Play</h2>
      <div class="deck-grid">{"".join(card(n) for n in others)}</div>
    </section>"""

    html = theme.page_html(
        title="La Baraja", subtitle="The roster as a Lotería deck: every player, his emblem and his season so far.",
        body_content=body, current_slug="roster", badge=f"{season_s} Roster",
        games_played=int((games["status"] == "Final").sum()) if not games.empty else 0,
    )
    out = theme.page_path("roster", team_abbr, season)
    out.write_text(html, encoding="utf-8")
    return [out] + written
