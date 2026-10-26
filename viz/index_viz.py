"""
Spurs Stats HQ Landing Page — the Lotería board.

Generates docs/index.html: a live scoreboard strip (record, last result, streak,
Wemby's line) above a deck of Lotería cards, one per page in the suite. Every
number on the cards is computed from the parquet cache at build time.
"""

from __future__ import annotations

from html import escape, unescape
from pathlib import Path

import pandas as pd

import config
from config import TEAM_ABBR, SEASON, TEAMS, season_str
from viz import theme
from analysis.standings import season_record
from analysis.wemby import get_wemby_logs, stocks_distribution
from analysis.rodeo import segment_rodeo_games, rodeo_split_metrics
from analysis.performers import game_performers, hot_hand
from data.schedule import load_schedule, next_game, now_utc


def _last_game(games: pd.DataFrame) -> dict:
    f = games[games["status"] == "Final"].sort_values("game_date")
    if f.empty:
        return {}
    g = f.iloc[-1]
    venue = "vs." if g["home_away"] == "H" else "@"
    date = pd.to_datetime(g["game_date"])
    return {
        "result": g["result"],
        "score": f"{int(g['pts'])}-{int(g['opp_pts'])}",
        "matchup": f"{venue} {g['opponent_abbr']}",
        "date": f"{date:%b} {date.day}",
    }


def _streak(games: pd.DataFrame) -> str:
    results = games[games["status"] == "Final"].sort_values("game_date")["result"].tolist()
    if not results:
        return "—"
    last, n = results[-1], 0
    for r in reversed(results):
        if r != last:
            break
        n += 1
    return f"{last}{n}"


# Illustrated card art (docs/img/loteria/<slug>.webp) and where the stat medallion
# sits (a corner, top/bottom center, centered, on the tablet face, or a stack of
# small badges up the right edge) so it stays clear of the illustration's subject.
CARD_ART: dict[str, str] = {
    "tablero": "tablet",   # stamped on the carved tally face
    "alien":   "stack-right",  # several small badges up the right edge, below the ball
    "rodeo":   "left",
    "libreta": "bottom",
    "duelo":   "top",      # stands in for the sun, clear of both players
    "mercado": "center",   # papel picado spans both top corners
    "valiente": "right",
}


def _art_src(slug: str) -> str | None:
    """Relative image path if the card's illustration has been added, else None."""
    rel = f"img/loteria/{slug}.webp"
    return rel if (config.OUTPUT_DIR / rel).exists() else None


def _size(stat: str) -> str:
    # Names ("Champagnie") need a smaller face than scores ("1-2") to fit the card
    n = len(unescape(stat))
    return " xlong" if n > 7 else (" long" if n > 4 else "")


def _card(num: int, slug: str, name: str, href: str, color: str, ink: str,
          stat: str, caption: str, blurb: str, badges: list[tuple[str, str]] | None = None) -> str:
    """
    One Lotería card. `stat`/`caption` is the headline number; `badges` optionally
    replaces it on illustrated cards with several small medallions.
    """
    src = _art_src(slug)
    size = _size(stat)
    if src:
        # Illustrated card: stats become ink medallions stamped onto the art
        place = CARD_ART.get(slug, "right")
        if badges:
            minis = "".join(
                f'<div class="medallion mini"><div class="stat{_size(v)}">{v}</div><div class="caption">{c}</div></div>'
                for v, c in badges
            )
            stamps = f'<div class="medallions {place}">{minis}</div>'
        else:
            stamps = (f'<div class="medallion {place}">'
                      f'<div class="stat{size}">{stat}</div><div class="caption">{caption}</div></div>')
        art = (
            f'<div class="art has-img">'
            f'<img src="{src}" alt="" loading="lazy" decoding="async">{stamps}</div>'
        )
    else:
        art = f'<div class="art"><div class="stat{size}">{stat}</div><div class="caption">{caption}</div></div>'
    # Cream numerals get an ink drop shadow; ink numerals on light cards stand on their own
    shadow = "transparent" if ink == theme.LOTERIA_INK else theme.LOTERIA_INK
    return f"""
      <a class="loteria" href="{href}" style="--c:{color}; --ink:{ink}; --sh:{shadow};">
        <div class="frame">
          <div class="num">{num}</div>
          {art}
          <div class="name">{name}</div>
        </div>
        <p class="blurb">{blurb}</p>
      </a>"""


def _index_css() -> str:
    t = theme
    return f"""
    html, body {{
      background:
        repeating-linear-gradient(45deg, rgba(0,0,0,0.09) 0 2px, transparent 2px 14px),
        {t.ADOBE_TERRACOTTA};
    }}
    .hq-hero {{ text-align: center; padding: 18px 0 6px; }}
    .hq-hero h1 {{
      font-family: {t.FONT_WESTERN}; font-weight: 400;
      font-size: clamp(2.6rem, 9vw, 5rem); line-height: 1;
      color: {t.LOTERIA_CREAM}; text-shadow: 4px 4px 0 {t.LOTERIA_INK};
    }}
    .hq-hero .sub {{
      font-family: {t.FONT_TYPE}; font-weight: 700; color: {t.MARIGOLD};
      font-size: clamp(0.75rem, 2.2vw, 0.95rem); letter-spacing: 0.2em; text-transform: uppercase;
      margin-top: 12px;
    }}
    .hq-hero .season {{
      font-family: {t.FONT_TYPE}; font-weight: 700; color: {t.LOTERIA_CREAM};
      font-size: clamp(0.7rem, 2vw, 0.85rem); letter-spacing: 0.3em; text-transform: uppercase;
      margin-top: 6px; opacity: 0.85;
    }}
    .hq-hero .lede {{
      max-width: 640px; margin: 14px auto 0; color: {t.LOTERIA_CREAM}; opacity: 0.9;
      font-size: clamp(0.9rem, 2vw, 1.02rem); line-height: 1.55;
    }}

    .scoreboard {{
      display: grid; grid-template-columns: repeat(4, 1fr);
      background: {t.FROST_BANK_FLOOR}; border: 4px solid {t.LOTERIA_INK};
      outline: 3px solid {t.LOTERIA_CREAM}; outline-offset: -9px;
      margin: 30px auto 40px; max-width: 980px; padding: 14px 10px;
      box-shadow: 8px 8px 0 {t.LOTERIA_INK};
    }}
    .scoreboard > div {{ text-align: center; padding: 6px 8px; }}
    .scoreboard > div + div {{ border-left: 2px dashed {t.COURT_LINE}; }}
    .scoreboard .k {{
      font-family: {t.FONT_HEADING}; font-weight: 600; font-size: 1rem; line-height: 1;
      letter-spacing: 0.2em; text-transform: uppercase; color: {t.SPURS_SILVER};
    }}
    .scoreboard .v {{
      font-family: {t.FONT_LED}; font-size: clamp(2rem, 5vw, 2.8rem); line-height: 1.05;
      color: {t.FIESTA_ORANGE}; text-shadow: 0 0 14px rgba(255, 130, 0, 0.5);
    }}
    .scoreboard .v.W {{ color: {t.FIESTA_TEAL}; text-shadow: 0 0 14px rgba(0, 178, 169, 0.5); }}
    .scoreboard .v.L {{ color: {t.FIESTA_FUSCHIA}; text-shadow: 0 0 14px rgba(239, 66, 111, 0.5); }}
    .scoreboard .sep {{ color: {t.COURT_LINE}; margin: 0 0.25em; text-shadow: none; }}
    .scoreboard .d {{ font-family: {t.FONT_MONO}; font-size: 0.78rem; color: {t.TEXT_MUTED}; }}

    .deck {{
      display: grid; gap: clamp(16px, 2.4vw, 28px);
      grid-template-columns: repeat(var(--per-row), minmax(0, 1fr));
      max-width: calc(var(--per-row) * 270px); margin: 0 auto;
    }}
    .loteria {{ text-decoration: none; color: inherit; display: block; }}
    @media (max-width: 1100px) {{
      .deck {{ grid-template-columns: repeat(3, minmax(0, 1fr)); max-width: 820px; }}
    }}
    .loteria .frame {{
      background: {t.LOTERIA_CREAM}; color: {t.LOTERIA_INK};
      border: 6px solid {t.LOTERIA_INK}; outline: 3px solid {t.LOTERIA_CREAM};
      padding: 10px; aspect-ratio: 5 / 7; display: flex; flex-direction: column;
      transition: transform 0.15s ease, box-shadow 0.15s ease;
    }}
    .loteria:hover .frame, .loteria:focus-visible .frame {{
      transform: translate(-3px, -3px) rotate(-1deg);
      box-shadow: 10px 10px 0 {t.LOTERIA_INK};
    }}
    .loteria .num {{ font-family: {t.FONT_TYPE}; font-weight: 700; font-size: 1.15rem; line-height: 1; }}
    .loteria .art {{
      flex: 1; margin: 8px 0; border: 3px solid {t.LOTERIA_INK};
      background:
        repeating-conic-gradient(from 0deg at 50% 55%, rgba(255,255,255,0.13) 0 7.5deg, transparent 7.5deg 15deg),
        var(--c);
      display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px;
      color: var(--ink);
    }}
    .loteria .art.has-img {{
      position: relative; overflow: hidden; display: block; background: var(--c);
    }}
    .loteria .art.has-img img {{
      position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover;
      transition: transform 0.25s ease;
    }}
    .loteria:hover .art.has-img img {{ transform: scale(1.04); }}
    .loteria .medallion {{
      position: absolute; top: 8px; width: 42%; aspect-ratio: 1;
      border-radius: 50%; background: {t.LOTERIA_INK}; color: {t.LOTERIA_CREAM};
      border: 3px solid {t.LOTERIA_CREAM}; outline: 2px solid {t.LOTERIA_INK};
      display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 2px;
      box-shadow: 3px 3px 0 rgba(0, 0, 0, 0.35);
    }}
    .loteria .medallion.left  {{ left: 8px;  transform: rotate(-7deg); }}
    .loteria .medallion.right {{ right: 8px; transform: rotate(7deg); }}
    .loteria .medallion.top {{ left: 50%; transform: translateX(-50%) rotate(-4deg); }}
    .loteria .medallion.bottom {{ left: 50%; top: auto; bottom: 8px; transform: translateX(-50%) rotate(3deg); }}
    .loteria .medallion.tablet {{ left: 67%; top: 76%; transform: translate(-50%, -50%) rotate(-6deg); }}
    .loteria .medallions.stack-right {{
      position: absolute; right: 7px; bottom: 7px; top: 22%; width: 25%;
      display: flex; flex-direction: column; justify-content: flex-end; gap: 6px;
    }}
    .loteria .medallion.mini {{ position: static; width: 100%; border-width: 2px; gap: 0; }}
    .loteria .medallion.mini:nth-child(odd)  {{ transform: rotate(-5deg); }}
    .loteria .medallion.mini:nth-child(even) {{ transform: rotate(5deg); }}
    .loteria .medallion.mini .stat {{ font-size: clamp(0.85rem, 1.5vw, 1.05rem); }}
    .loteria .medallion.mini .caption {{ font-size: 0.5rem; letter-spacing: 0.08em; }}
    .loteria .medallion.center {{ left: 50%; top: 44%; transform: translate(-50%, -50%) rotate(-4deg); }}
    .loteria .medallion .stat {{
      font-size: clamp(1.3rem, 2.6vw, 1.75rem); text-shadow: 2px 2px 0 var(--c);
    }}
    .loteria .medallion .caption {{
      background: none; padding: 0; font-size: 0.55rem; letter-spacing: 0.1em;
      max-width: 86%; text-align: center; line-height: 1.15;
    }}
    .loteria .stat {{
      font-family: {t.FONT_SLAB}; font-size: clamp(2.6rem, 6vw, 3.6rem); line-height: 1;
      text-shadow: 3px 3px 0 var(--sh);
    }}
    .loteria .stat.long  {{ font-size: clamp(1.9rem, 4.2vw, 2.6rem); }}
    .loteria .stat.xlong {{ font-size: clamp(1.4rem, 3vw, 1.9rem); }}
    .loteria .medallion .stat.long  {{ font-size: clamp(0.95rem, 1.8vw, 1.2rem); }}
    .loteria .medallion .stat.xlong {{ font-size: clamp(0.75rem, 1.4vw, 0.95rem); }}
    .loteria .caption {{
      font-family: {t.FONT_TYPE}; font-weight: 700; font-size: 0.78rem;
      letter-spacing: 0.16em; text-transform: uppercase;
      background: {t.LOTERIA_INK}; color: {t.LOTERIA_CREAM}; padding: 3px 8px;
    }}
    .loteria .name {{
      font-family: {t.FONT_WESTERN}; font-size: clamp(1.3rem, 3vw, 1.65rem); line-height: 1.1;
      text-align: center; border-top: 3px solid {t.LOTERIA_INK}; padding-top: 8px;
    }}
    .loteria .blurb {{
      color: {t.LOTERIA_CREAM}; font-size: 0.88rem; line-height: 1.45; margin-top: 14px; opacity: 0.92;
    }}

    footer {{ color: {t.LOTERIA_CREAM}; }}
    footer .credit {{ color: {t.LOTERIA_CREAM}; }}
    .alamo-footer-seal .alamo-icon-svg {{ color: {t.LOTERIA_CREAM}; }}

    @media (max-width: 640px) {{
      .deck {{ grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }}
      .loteria .frame {{ border-width: 4px; padding: 6px; }}
      .loteria .stat {{ font-size: 2.2rem; text-shadow: 2px 2px 0 var(--sh); }}
      .loteria .stat.long {{ font-size: 1.6rem; }}
      .loteria .stat.xlong {{ font-size: 1.15rem; }}
      .loteria .medallion {{ border-width: 2px; }}
      .loteria .medallion.left, .loteria .medallion.right, .loteria .medallion.top {{ top: 5px; }}
      .loteria .medallion.bottom {{ bottom: 5px; }}
      .loteria .medallions.stack-right {{ right: 4px; bottom: 4px; gap: 4px; width: 27%; }}
      .loteria .medallion.mini .stat {{ font-size: 0.68rem; }}
      .loteria .medallion.mini .caption {{ font-size: 0.36rem; }}
      .loteria .medallion .stat {{ font-size: 1.05rem; text-shadow: 1px 1px 0 var(--c); }}
      .loteria .medallion .stat.long {{ font-size: 0.8rem; }}
      .loteria .medallion .stat.xlong {{ font-size: 0.62rem; }}
      .loteria .medallion .caption {{ font-size: 0.42rem; letter-spacing: 0.04em; }}
      .loteria .medallion.left {{ left: 5px; }}
      .loteria .medallion.right {{ right: 5px; }}
      .loteria .caption {{ font-size: 0.6rem; letter-spacing: 0.08em; padding: 2px 5px; }}
      .loteria .name {{ font-size: 1.05rem; padding-top: 5px; }}
      .loteria .blurb {{ font-size: 0.78rem; margin-top: 10px; }}
      .scoreboard {{ grid-template-columns: repeat(2, 1fr); row-gap: 10px; }}
      .scoreboard > div:nth-child(3) {{ border-left: none; }}
    }}
    """


def build_index_page(
    games: pd.DataFrame,
    player_logs: pd.DataFrame,
    season: int = SEASON,
    team_abbr: str = TEAM_ABBR,
    output_path: Path | None = None,
) -> Path:
    """Build and write the Spurs Stats HQ landing page."""
    if output_path is None:
        output_path = config.OUTPUT_DIR / "index.html"

    season_s = season_str(season)
    team_name = TEAMS[team_abbr.upper()]["name"]
    rec = season_record(games)
    record = f"{rec.get('wins', 0)}-{rec.get('losses', 0)}" if rec else "0-0"
    last = _last_game(games)
    streak = _streak(games)

    wemby = get_wemby_logs(player_logs)
    wemby = wemby[wemby["min"] > 0] if not wemby.empty else wemby
    stocks = stocks_distribution(wemby) if not wemby.empty else {}
    wemby_ppg = f"{wemby['pts'].mean():.1f}" if not wemby.empty else "0.0"
    wemby_rpg = f"{wemby['reb'].mean():.1f}" if not wemby.empty else "0.0"
    wemby_spg = f"{stocks.get('stocks_per_game', 0.0):.1f}"

    nxt = next_game(load_schedule(season), team_abbr.upper(), now_utc())
    if nxt:
        opp_name = TEAMS[nxt["opponent"]]["name"].split()[-1]
        duelo_stat = f'{"vs." if nxt["is_home"] else "@"} {nxt["opponent"]}'
        duelo_caption = f'{nxt["tipoff_local"]:%a} {nxt["tipoff_local"]:%-I:%M %p}'
        duelo_blurb = (f'Next up: {opp_name} {"at Spurs" if nxt["is_home"] else "host the Spurs"}, {nxt["when"]}. '
                       f"Tale of the tape, recent form and players to watch.")
    else:
        duelo_stat, duelo_caption = "—", "Season complete"
        duelo_blurb = "The next-game preview returns with next season's schedule."
    potg = game_performers(player_logs).get("player_of_the_game") if not player_logs.empty else None
    hot = hot_hand(player_logs) if not player_logs.empty else {}

    rodeo = rodeo_split_metrics(segment_rodeo_games(games)) if not games.empty else {}
    active_rrt = rodeo.get("Active RRT", {}) if isinstance(rodeo, dict) else {}
    rodeo_stat, rodeo_caption = (
        (active_rrt["record"], "Rodeo record") if active_rrt.get("games") else ("FEB", "Hits the road")
    )

    last_v = f'{last["result"]} {last["score"]}' if last else "—"
    last_d = f'{last["matchup"]} &middot; {last["date"]}' if last else "No games yet"

    pages = theme.PAGES
    deck = [
        ("dashboard", _card(1, "tablero", "El Tablero", pages["dashboard"][0], theme.FIESTA_TEAL, theme.LOTERIA_CREAM,
              record, "Record",
              "The season dashboard: four factors, rotation pairings, clutch ledger, scoring and defensive trends.")),
        ("wemby", _card(2, "alien", "El Alien", pages["wemby"][0], theme.FIESTA_FUSCHIA, theme.LOTERIA_CREAM,
              wemby_spg, "Stocks / game",
              "The Wemby Lab: rim deterrence, stocks timeline, milestone watch and his best defensive nights.",
              badges=[(wemby_ppg, "PTS"), (wemby_rpg, "REB"), (wemby_spg, "STOCKS")])),
        ("valiente", _card(7, "valiente", "El Valiente", pages["dashboard"][0] + "#spotlight",
              theme.ADOBE_TERRACOTTA, theme.LOTERIA_CREAM,
              hot.get("last_name", "—"), f"Hot hand &middot; last {hot.get('window', 5)}",
              f"Whoever is playing best right now: {hot['player_name']} leads the team in Game Score over the last "
              f"{hot['window']} games ({hot['game_score']})." if hot else "Whoever is playing best right now, by Game Score.")),
        ("rodeo", _card(3, "rodeo", "El Rodeo", pages["rodeo"][0], theme.FIESTA_ORANGE, theme.LOTERIA_CREAM,
              rodeo_stat, rodeo_caption,
              "The February Rodeo Road Trip, split against the championship-era trips since 2003.")),
        ("notebook", _card(4, "libreta", "La Libreta", pages["notebook"][0], theme.LOTERIA_INK, theme.LOTERIA_CREAM,
              "&#9998;", "Essays",
              "The Notebook: living essays where every number is recomputed from the data at build time.")),
        ("matchup", _card(5, "duelo", "El Duelo", pages["matchup"][0], theme.MARIGOLD, theme.LOTERIA_INK,
              duelo_stat, duelo_caption, duelo_blurb)),
        ("board", _card(6, "mercado", "El Mercado", pages["board"][0], theme.SPURS_SILVER, theme.LOTERIA_INK,
              "O/U", "Prop board",
              "Player prop hit rates from game logs. For fun and analysis, not betting advice.")),
    ]
    featured = [card for slug, card in deck if slug not in theme.PAGES or theme.is_featured(slug)]
    cards = "".join(featured)
    # One row of up to five cards; a sixth splits the deck into two even rows of three
    per_row = len(featured) if len(featured) <= 5 else -(-len(featured) // 2)

    description = (
        f"{team_name} {season_s}: {record}. Who's playing well, the rotation "
        f"and close games, rebuilt after every game."
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Spurs Stats HQ — San Antonio Spurs Analytics</title>
  <meta name="description" content="{escape(description)}">
  <meta property="og:type" content="website">
  <meta property="og:title" content="Spurs Stats HQ · {season_s} · {record}">
  <meta property="og:description" content="{escape(description)}">
  <meta name="twitter:card" content="summary">
  <meta name="twitter:title" content="Spurs Stats HQ · {season_s} · {record}">
  <meta name="twitter:description" content="{escape(description)}">
  {theme.FONTS_LINK}
  <style>
{theme.page_css()}
{_index_css()}
  </style>
</head>
<body>
  <div class="sarape-band" aria-hidden="true"></div>
  <div class="page">
    <section class="hq-hero">
      <h1>Spurs Stats HQ</h1>
      <div class="sub">&#9733; Putting hammer to stone since 2024 &#9733;</div>
      <div class="season">{season_s} season</div>
      <p class="lede">The San Antonio Spurs, by the numbers: who's playing well, how the rotation
        fits together and what happens in close games, rebuilt from the box scores after every game.</p>
    </section>

    <section class="scoreboard" aria-label="Season at a glance">
      <div><div class="k">Record</div><div class="v">{record}</div><div class="d">{season_s}</div></div>
      <div><div class="k">Last game</div><div class="v {last.get('result', '')}">{last_v}</div><div class="d">{last_d}</div></div>
      <div><div class="k">Streak</div><div class="v {streak[:1]}">{streak}</div><div class="d">current run</div></div>
      <div><div class="k">Top performer</div><div class="v">{potg["last_name"] if potg else "—"}</div><div class="d">{potg["line"].replace(" · ", " &middot; ") if potg else "last game"}</div></div>
    </section>

    <main class="deck" style="--per-row:{per_row};">
      {cards}
    </main>
    {theme.page_footer()}
  </div>
</body>
</html>
"""
    output_path.write_text(html, encoding="utf-8")
    return output_path
