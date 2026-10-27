"""
Player Avatars — Lotería emblems instead of faces.

Each Spurs player can have an illustrated emblem drawn from his name (Fox ->
El Zorro, Castle -> El Castillo), published at docs/img/players/<slug>.webp.
Anyone without one (new signings, two-way players, opponents) gets an ink
medallion with his initials, so layouts never depend on art being present.

To add or change an emblem: drop the full-resolution image in
docs/img/players_src/<slug>.<jpeg|png>, run `python scripts/prep_art.py`,
and add/confirm the player's entry below.
"""

from __future__ import annotations

import hashlib
from html import escape

import config
from viz import theme

PLAYERS_DIR = "img/players"

# Player name (as it appears in the box scores) -> (image slug, emblem name).
# Lotería-style names: puns on the surname, or Spanish takes on fan nicknames.
PLAYER_EMBLEMS: dict[str, tuple[str, str]] = {
    "De'Aaron Fox":      ("fox",        "El Zorro"),
    "Stephon Castle":    ("castle",     "El Castillo"),
    "Dylan Harper":      ("harper",     "El Arpa"),
    "Victor Wembanyama": ("wembanyama", "El Alien"),
    "Devin Vassell":     ("vassell",    "El Hechicero"),
    "Julian Champagnie": ("champagnie", "La Botella"),
    "Keldon Johnson":    ("johnson",    "El Mesteño"),
    "Luke Kornet":       ("kornet",     "El Elotote"),
    "Carter Bryant":     ("bryant",     "La Supernova"),
    "Harrison Barnes":   ("barnes",     "El Tío"),
}

_INITIALS_COLORS = (theme.FIESTA_TEAL, theme.FIESTA_FUSCHIA, theme.FIESTA_ORANGE, theme.MARIGOLD)


def avatar_src(player_name: str) -> str | None:
    """Relative path to the player's emblem if it has been published, else None."""
    entry = PLAYER_EMBLEMS.get(player_name)
    if entry is None:
        return None
    rel = f"{PLAYERS_DIR}/{entry[0]}.webp"
    return rel if (config.OUTPUT_DIR / rel).exists() else None


def card_name(player_name: str) -> str | None:
    entry = PLAYER_EMBLEMS.get(player_name)
    return entry[1] if entry else None


def initials(player_name: str) -> str:
    """'De'Aaron Fox' -> 'DF', 'Tarris Reed Jr.' -> 'TR'."""
    parts = [p for p in player_name.replace(".", "").split() if p.lower() not in {"jr", "sr", "ii", "iii", "iv"}]
    if not parts:
        return "?"
    return (parts[0][0] + (parts[-1][0] if len(parts) > 1 else "")).upper()


def _initials_color(player_name: str) -> str:
    # Stable per player across builds (Python's hash() is salted per process)
    digest = hashlib.md5(player_name.encode("utf-8")).digest()
    return _INITIALS_COLORS[digest[0] % len(_INITIALS_COLORS)]


def avatar_html(player_name: str, size: str = "md") -> str:
    """
    Round avatar for a player: his emblem if published, otherwise initials.
    size: "sm" (table rows), "md" (lists, tiles), "lg" (feature spots).
    """
    name = escape(player_name)
    src = avatar_src(player_name)
    if src:
        label = escape(card_name(player_name) or player_name)
        return (f'<img class="avatar avatar-{size}" src="{src}" alt="{label} emblem for {name}" '
                f'title="{label}" loading="lazy" decoding="async">')
    return (f'<span class="avatar avatar-{size} avatar-initials" style="--av:{_initials_color(player_name)};" '
            f'title="{name}" aria-hidden="true">{initials(player_name)}</span>')


def avatar_css() -> str:
    """Shared avatar styles; included by theme.page_css()."""
    t = theme
    return f"""
    .avatar {{
      display: inline-block; flex: 0 0 auto; border-radius: 50%; object-fit: cover; vertical-align: middle;
      border: 2px solid {t.LOTERIA_CREAM}; outline: 2px solid {t.LOTERIA_INK};
      box-shadow: 3px 3px 0 rgba(0, 0, 0, 0.45); background: {t.SHADOW_BLACK};
    }}
    .avatar-sm {{ width: 30px; height: 30px; border-width: 1.5px; outline-width: 1.5px; box-shadow: 2px 2px 0 rgba(0,0,0,0.45); }}
    .avatar-md {{ width: 48px; height: 48px; }}
    .avatar-lg {{ width: 76px; height: 76px; border-width: 3px; }}
    .avatar-initials {{
      display: inline-flex; align-items: center; justify-content: center;
      background: {t.LOTERIA_INK}; color: var(--av); font-family: {t.FONT_SLAB}; line-height: 1;
    }}
    .avatar-sm.avatar-initials {{ font-size: 0.72rem; }}
    .avatar-md.avatar-initials {{ font-size: 1.05rem; }}
    .avatar-lg.avatar-initials {{ font-size: 1.6rem; }}
    .with-avatar {{ display: flex; align-items: center; gap: 10px; }}
    """
