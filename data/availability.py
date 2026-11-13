"""Reviewed availability snapshots, scoped to one game so they cannot carry forward."""

from __future__ import annotations

import json

import config


def load_availability(game_id: str, season: int = config.SEASON) -> dict:
    """Return the source-dated report for this game, or no availability claim."""
    path = config.BASE_DIR / "data" / f"availability_{season}.json"
    if not path.exists():
        return {}
    snapshots = json.loads(path.read_text(encoding="utf-8"))
    return snapshots.get(str(game_id), {})


def player_statuses(snapshot: dict, team: str) -> dict[str, str]:
    return {p["name"]: p["status"] for p in snapshot.get("teams", {}).get(team, [])}
