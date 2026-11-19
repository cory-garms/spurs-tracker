"""Editorial pregame notes, scoped to an exact game and season."""

from __future__ import annotations

import json

import config


def load_pregame_briefing(game_id: str, season: int = config.SEASON) -> dict:
    path = config.BASE_DIR / "data" / f"pregame_{season}.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8")).get(str(game_id), {})
