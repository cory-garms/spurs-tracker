"""
Link-Preview Images — what a shared link looks like on Reddit, X and Discord.

Draws 1200x630 PNGs at build time with Pillow:
  - img/og/latest.png: last result, record and the Player of the Game's emblem
  - img/og/next.png:   the next game, tip time and the projection

Pages reference them through og_image_url(), which adds a content hash so
platforms re-fetch the image when it changes instead of showing a stale card.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont

import config
from config import TEAMS
from viz import theme
from viz.avatars import avatar_src, card_name, initials

W, H = 1200, 630
FONTS = config.BASE_DIR / "assets" / "fonts"
OG_DIR = "img/og"


def _font(name: str, size: int, weight: int | None = None) -> ImageFont.FreeTypeFont:
    f = ImageFont.truetype(str(FONTS / name), size)
    if weight is not None:
        f.set_variation_by_axes([weight])
    return f


def _fit(draw: ImageDraw.ImageDraw, text: str, name: str, size: int, max_w: int,
         weight: int | None = None) -> ImageFont.FreeTypeFont:
    """Largest font at or below `size` that fits `text` within `max_w` pixels."""
    while size > 12:
        f = _font(name, size, weight)
        if draw.textlength(text, font=f) <= max_w:
            return f
        size -= 2
    return _font(name, 12, weight)


def _canvas() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    im = Image.new("RGB", (W, H), theme.FROST_BANK_FLOOR)
    d = ImageDraw.Draw(im)
    for x in range(-H, W, 24):  # faint diagonal court texture
        d.line([(x, H), (x + H, 0)], fill="#10141A", width=3)
    band = [theme.FIESTA_TEAL, theme.FIESTA_FUSCHIA, theme.FIESTA_ORANGE]
    for i, c in enumerate(band):  # sarape band across the top
        d.rectangle([0, i * 8, W, i * 8 + 8], fill=c)
    for i, x in enumerate(range(0, W, 60)):  # sarape ribbon along the bottom
        d.rectangle([x, H - 10, x + 60, H], fill=band[i % 3])
    return im, d


def _emblem(im: Image.Image, player_name: str | None, center: tuple[int, int], r: int) -> None:
    """Player emblem (or initials) in a cream ring with an ink outline and offset shadow."""
    d = ImageDraw.Draw(im)
    cx, cy = center
    d.ellipse([cx - r + 14, cy - r + 14, cx + r + 14, cy + r + 14], fill="#05070A")
    d.ellipse([cx - r - 6, cy - r - 6, cx + r + 6, cy + r + 6], fill=theme.LOTERIA_INK)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=theme.LOTERIA_CREAM)
    inner = r - 10
    src = avatar_src(player_name) if player_name else None
    if src:
        art = Image.open(config.OUTPUT_DIR / src).convert("RGB").resize((inner * 2, inner * 2), Image.LANCZOS)
        mask = Image.new("L", art.size, 0)
        ImageDraw.Draw(mask).ellipse([0, 0, inner * 2 - 1, inner * 2 - 1], fill=255)
        im.paste(art, (cx - inner, cy - inner), mask)
    else:
        d.ellipse([cx - inner, cy - inner, cx + inner, cy + inner], fill=theme.LOTERIA_INK)
        label = initials(player_name) if player_name else "SA"
        f = _font("BowlbyOne-Regular.ttf", int(inner * 0.8))
        d.text((cx, cy), label, font=f, fill=theme.FIESTA_ORANGE, anchor="mm")


def _url(d: ImageDraw.ImageDraw) -> None:
    host = config.SITE_URL.split("://", 1)[-1]
    d.text((W - 40, H - 34), host, font=_font("CourierPrime-Bold.ttf", 24), fill=theme.TEXT_MUTED, anchor="rs")


def _header(d: ImageDraw.ImageDraw, x: int, kicker: str) -> None:
    d.text((x, 60), "Spurs Stats HQ", font=_font("Rye-Regular.ttf", 46), fill=theme.LOTERIA_CREAM)
    d.text((x, 128), kicker, font=_font("Teko[wght].ttf", 34, 600), fill=theme.SPURS_SILVER)


def render_latest_game(games: pd.DataFrame, player_logs: pd.DataFrame, out: Path) -> Path | None:
    """Last result, record and the Player of the Game."""
    from analysis.performers import game_performers
    from analysis.standings import season_record

    final = games[games["status"] == "Final"].sort_values("game_date") if not games.empty else games
    if final.empty:
        return None
    g = final.iloc[-1]
    rec = season_record(games)
    potg = game_performers(player_logs, g["game_id"]).get("player_of_the_game") if not player_logs.empty else None

    im, d = _canvas()
    x, max_w = 540, W - 540 - 40
    _emblem(im, potg["player_name"] if potg else None, (270, 330), 190)
    _header(d, x, f"FINAL  ·  {pd.to_datetime(g['game_date']):%b} {pd.to_datetime(g['game_date']).day}")

    venue = "vs." if g["home_away"] == "H" else "@"
    score = f"{g['result']} {int(g['pts'])}-{int(g['opp_pts'])} {venue} {g['opponent_abbr']}"
    d.text((x, 162), score, font=_fit(d, score, "VT323-Regular.ttf", 112, max_w),
           fill=theme.FIESTA_TEAL if g["result"] == "W" else theme.FIESTA_FUSCHIA)
    d.text((x, 272), f"Record {rec.get('wins', 0)}-{rec.get('losses', 0)}",
           font=_font("Teko[wght].ttf", 40, 500), fill=theme.SPURS_SILVER)

    for xx in range(x, W - 40, 18):
        d.line([(xx, 336), (xx + 9, 336)], fill=theme.COURT_LINE, width=3)
    if potg:
        d.text((x, 352), "PLAYER OF THE GAME", font=_font("Teko[wght].ttf", 34, 600), fill=theme.FIESTA_TEAL)
        d.text((x, 392), potg["player_name"], font=_fit(d, potg["player_name"], "BowlbyOne-Regular.ttf", 54, max_w),
               fill=theme.COURT_WHITE)
        emblem = card_name(potg["player_name"])
        if emblem:
            d.text((x, 462), emblem, font=_font("Rye-Regular.ttf", 36), fill=theme.MARIGOLD)
        d.text((x, 508), potg["line"], font=_fit(d, potg["line"], "VT323-Regular.ttf", 56, max_w),
               fill=theme.FIESTA_ORANGE)
    _url(d)
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out, "PNG", optimize=True)
    return out


def render_next_game(player_logs: pd.DataFrame, season: int, team_abbr: str, out: Path) -> Path | None:
    """The next game, tip time, records and the projection, fronted by the Spurs' hot hand."""
    from analysis.matchup_preview import projection
    from analysis.performers import hot_hand
    from data.league import load_league_standings
    from data.schedule import load_schedule, next_game, now_utc

    team = team_abbr.upper()
    nxt = next_game(load_schedule(season), team, now_utc())
    if nxt is None:
        return None
    standings = load_league_standings(season)
    opp = nxt["opponent"]
    hot = hot_hand(player_logs) if not player_logs.empty else {}

    im, d = _canvas()
    x, max_w = 540, W - 540 - 40
    _emblem(im, hot.get("player_name"), (270, 330), 190)
    _header(d, x, "NEXT GAME")

    away, home = (opp, team) if nxt["is_home"] else (team, opp)
    matchup = f"{away} @ {home}"
    f = _fit(d, matchup, "BowlbyOne-Regular.ttf", 104, max_w)
    for dx, c in ((8, theme.FIESTA_TEAL), (4, theme.FIESTA_FUSCHIA), (0, theme.COURT_WHITE)):
        d.text((x + dx, 168 + dx), matchup, font=f, fill=c)

    when = nxt["when"].replace(" · ", "  ·  ")
    d.text((x, 300), when, font=_fit(d, when, "Teko[wght].ttf", 44, max_w, 500), fill=theme.SPURS_SILVER)

    def rec(abbr: str) -> str:
        r = standings[standings["team_abbr"] == abbr]
        return f"{int(r['wins'].iloc[0])}-{int(r['losses'].iloc[0])}" if not r.empty else ""
    records = f"{away} {rec(away)}   {home} {rec(home)}"
    d.text((x, 352), records, font=_font("VT323-Regular.ttf", 52), fill=theme.FIESTA_ORANGE)

    proj = projection(standings, team, opp, nxt["is_home"])
    if proj:
        us, them = TEAMS[team]["name"].split()[-1], TEAMS[opp]["name"].split()[-1]
        fav, pts = (us, proj["margin"]) if proj["margin"] >= 0 else (them, -proj["margin"])
        win = proj["win_prob"] if proj["margin"] >= 0 else 1 - proj["win_prob"]
        line = f"Projection: {fav} by {pts:.1f}  ·  {win:.0%}"
        d.text((x, 432), line, font=_fit(d, line, "Teko[wght].ttf", 46, max_w, 600), fill=theme.COURT_WHITE)
    if hot:
        tag = f"Hot hand: {hot['player_name']}"
        d.text((x, 500), tag, font=_fit(d, tag, "Teko[wght].ttf", 36, max_w, 500), fill=theme.MARIGOLD)
    _url(d)
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out, "PNG", optimize=True)
    return out


def build_share_images(games: pd.DataFrame, player_logs: pd.DataFrame,
                       season: int = config.SEASON, team_abbr: str = config.TEAM_ABBR) -> list[Path]:
    """Render every preview image; returns the paths written."""
    base = config.OUTPUT_DIR / OG_DIR
    written = [
        render_latest_game(games, player_logs, base / "latest.png"),
        render_next_game(player_logs, season, team_abbr, base / "next.png"),
    ]
    return [p for p in written if p]


def og_image_url(name: str = "latest") -> str | None:
    """Absolute URL for a preview image, versioned by content so platforms refresh it."""
    path = config.OUTPUT_DIR / OG_DIR / f"{name}.png"
    if not path.exists():
        return None
    digest = hashlib.md5(path.read_bytes()).hexdigest()[:8]
    return f"{config.SITE_URL}/{OG_DIR}/{name}.png?v={digest}"
