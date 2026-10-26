"""
League Schedule — next game, recent results and head-to-head meetings.

Pulls the NBA's public season schedule (cdn.nba.com), keeps regular-season games
only, and caches a compact table at data/cache/league_schedule_{season}.parquet.
Completed games carry final scores, so the same table answers "recent form" for
any team without extra box-score requests.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests

import config
from config import CACHE_DIR

log = logging.getLogger(__name__)

SCHEDULE_URL = "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json"
LOCAL_TZ = ZoneInfo("America/Chicago")  # San Antonio

STATUS_SCHEDULED, STATUS_LIVE, STATUS_FINAL = 1, 2, 3


def _cache_path(season: int) -> Path:
    return CACHE_DIR / f"league_schedule_{season}.parquet"


def _tv(broadcasters: dict) -> str:
    """National TV if any, else the home and away local TV feeds."""
    national = [b["broadcasterDisplay"] for b in broadcasters.get("nationalBroadcasters", [])
                if b.get("broadcasterMedia") == "tv"]
    if national:
        return ", ".join(national)
    local = [b["broadcasterDisplay"] for key in ("homeTvBroadcasters", "awayTvBroadcasters")
             for b in broadcasters.get(key, [])]
    return ", ".join(dict.fromkeys(local))


def fetch_schedule(season: int = config.SEASON, force_refresh: bool = False) -> pd.DataFrame:
    """Fetch and cache the regular-season schedule; keeps the last cache if the feed is down."""
    path = _cache_path(season)
    if not force_refresh and path.exists():
        return pd.read_parquet(path)
    try:
        resp = requests.get(SCHEDULE_URL, headers=config.NBA_API_HEADERS, timeout=config.REQUEST_TIMEOUT)
        resp.raise_for_status()
        sched = resp.json()["leagueSchedule"]
    except Exception as e:
        if path.exists():
            log.warning("Schedule fetch failed (%s); keeping last cache", e)
            return pd.read_parquet(path)
        raise

    rows = []
    for day in sched["gameDates"]:
        for g in day["games"]:
            if not g["gameId"].startswith("002"):  # 001 preseason, 004 playoffs, 006 cup final...
                continue
            home, away = g["homeTeam"], g["awayTeam"]
            rows.append({
                "game_id": g["gameId"],
                "tipoff_utc": g["gameDateTimeUTC"],
                "status": int(g["gameStatus"]),
                "home_abbr": home["teamTricode"],
                "away_abbr": away["teamTricode"],
                "home_score": int(home.get("score") or 0),
                "away_score": int(away.get("score") or 0),
                "arena": g.get("arenaName", ""),
                "city": g.get("arenaCity", ""),
                "tv": _tv(g.get("broadcasters", {})),
            })
    df = pd.DataFrame(rows).sort_values("tipoff_utc").reset_index(drop=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    log.info("Cached %d regular-season games → %s", len(df), path)
    return df


def load_schedule(season: int = config.SEASON) -> pd.DataFrame:
    path = _cache_path(season)
    return pd.read_parquet(path) if path.exists() else pd.DataFrame()


def _team_games(schedule: pd.DataFrame, team: str) -> pd.DataFrame:
    return schedule[(schedule["home_abbr"] == team) | (schedule["away_abbr"] == team)]


def next_game(schedule: pd.DataFrame, team: str, now: datetime | None = None) -> dict | None:
    """The team's next game that isn't final (a game in progress counts as next)."""
    if schedule.empty:
        return None
    upcoming = _team_games(schedule, team)
    upcoming = upcoming[upcoming["status"] != STATUS_FINAL]
    if now is not None:
        upcoming = upcoming[pd.to_datetime(upcoming["tipoff_utc"], utc=True) >= now - pd.Timedelta(hours=4)]
    if upcoming.empty:
        return None
    g = upcoming.iloc[0]
    home = g["home_abbr"] == team
    tip = pd.to_datetime(g["tipoff_utc"], utc=True).to_pydatetime().astimezone(LOCAL_TZ)
    return {
        "game_id": g["game_id"],
        "opponent": g["away_abbr"] if home else g["home_abbr"],
        "is_home": bool(home),
        "tipoff_local": tip,
        "when": f"{tip:%A}, {tip:%b} {tip.day} · {tip:%-I:%M %p} CT",
        "arena": g["arena"],
        "city": g["city"],
        "tv": g["tv"],
        "status": int(g["status"]),
    }


def recent_results(schedule: pd.DataFrame, team: str, n: int = 5) -> list[dict]:
    """Last `n` completed games for a team, most recent first."""
    if schedule.empty:
        return []
    done = _team_games(schedule, team)
    done = done[done["status"] == STATUS_FINAL].tail(n).iloc[::-1]
    out = []
    for _, g in done.iterrows():
        home = g["home_abbr"] == team
        us, them = (g["home_score"], g["away_score"]) if home else (g["away_score"], g["home_score"])
        tip = pd.to_datetime(g["tipoff_utc"], utc=True).to_pydatetime().astimezone(LOCAL_TZ)
        out.append({
            "result": "W" if us > them else "L",
            "score": f"{us}-{them}",
            "opponent": g["away_abbr"] if home else g["home_abbr"],
            "venue": "vs." if home else "@",
            "date": f"{tip:%b} {tip.day}",
        })
    return out


def head_to_head(schedule: pd.DataFrame, team: str, opponent: str) -> list[dict]:
    """Completed meetings this season between two teams, oldest first, from `team`'s side."""
    if schedule.empty:
        return []
    meet = schedule[
        (((schedule["home_abbr"] == team) & (schedule["away_abbr"] == opponent))
         | ((schedule["home_abbr"] == opponent) & (schedule["away_abbr"] == team)))
        & (schedule["status"] == STATUS_FINAL)
    ]
    return [r for r in reversed(recent_results(meet, team, n=len(meet)))]


def now_utc() -> datetime:
    return datetime.now(timezone.utc)
