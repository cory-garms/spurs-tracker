"""
Multi-season historical analysis.

Covers:
  - Fetch season records going back to HISTORY_START
  - Records within reach (pace comparison to milestones)
  - Build pace comparison data for charting
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from config import CACHE_DIR, HISTORY_START, TEAMS, season_str

log = logging.getLogger(__name__)

NOTABLE_SEASONS: dict[str, dict[str, str]] = {
    "SAS": {
        "1998-99": "WS Champs (50W lockout)",
        "2002-03": "WS Champs (60W)",
        "2004-05": "WS Champs (59W)",
        "2006-07": "WS Champs (58W)",
        "2013-14": "WS Champs (62W)",
        "2015-16": "67W — best regular season",
    },
    "GSW": {
        "2015-16": "73W record",
        "2017-18": "WS Champs (58W)",
    },
    "LAL": {
        "1999-00": "WS Champs (67W)",
        "2001-02": "WS Champs (58W)",
        "2019-20": "WS Champs (52W in bubble)",
    },
    "BOS": {
        "2007-08": "WS Champs (66W)",
        "2023-24": "WS Champs (64W)",
    },
}


def fetch_season_records(
    team_id: int,
    start_year: int = HISTORY_START,
    end_year: int | None = None,
    force_refresh: bool = False,
) -> pd.DataFrame:
    """
    Fetch and cache W-L records for a range of seasons.

    Cache: history_{team_id}.parquet
    Columns: season, wins, losses, win_pct
    """
    cache_path = CACHE_DIR / f"history_{team_id}.parquet"
    if cache_path.exists() and not force_refresh:
        log.info("Loading history from cache: %s", cache_path)
        return pd.read_parquet(cache_path)

    from client.nba_client import NBAClient
    client = NBAClient()

    if end_year is None:
        from datetime import date
        end_year = date.today().year

    rows: list[dict] = []
    for year in range(start_year, end_year):
        sstr = season_str(year)
        try:
            game_log = client.get_team_game_log(team_id, sstr)
            if game_log.empty:
                continue
            wins   = int((game_log["wl"] == "W").sum())
            losses = int((game_log["wl"] == "L").sum())
            played = wins + losses
            rows.append({
                "season":   sstr,
                "wins":     wins,
                "losses":   losses,
                "win_pct":  round(wins / played, 3) if played > 0 else 0.0,
            })
            log.info("History %s: %d-%d", sstr, wins, losses)
        except Exception as e:
            log.warning("Could not fetch %s: %s", sstr, e)

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df.to_parquet(cache_path, index=False)
    log.info("Cached history (%d seasons) → %s", len(df), cache_path)
    return df


def records_within_reach(
    current_games: pd.DataFrame,
    historical: pd.DataFrame,
    team_abbr: str,
) -> list[dict]:
    """
    Compare current season pace to historical milestones.
    Returns list of dicts describing notable records and how close the team is.
    """
    if current_games.empty or historical.empty:
        return []

    f = current_games[current_games["status"] == "Final"]
    if f.empty:
        return []

    g_played = len(f)
    wins     = int((f["result"] == "W").sum())
    pace_w   = round((wins / g_played) * 82)
    results  = []

    best_wins = int(historical["wins"].max())
    best_season = historical.loc[historical["wins"].idxmax(), "season"]
    results.append({
        "milestone":    f"Most wins in a season ({best_wins} in {best_season})",
        "current_pace": pace_w,
        "milestone_val": best_wins,
        "delta":         pace_w - best_wins,
    })

    worst_wins = int(historical["wins"].min())
    worst_season = historical.loc[historical["wins"].idxmin(), "season"]
    results.append({
        "milestone":    f"Fewest wins in a season ({worst_wins} in {worst_season})",
        "current_pace": pace_w,
        "milestone_val": worst_wins,
        "delta":         pace_w - worst_wins,
    })

    notable = NOTABLE_SEASONS.get(team_abbr, {})
    for ssn, label in notable.items():
        hist_row = historical[historical["season"] == ssn]
        if hist_row.empty:
            continue
        hist_wins = int(hist_row.iloc[0]["wins"])
        results.append({
            "milestone":    f"{label} ({hist_wins}W)",
            "current_pace": pace_w,
            "milestone_val": hist_wins,
            "delta":         pace_w - hist_wins,
        })

    return results


def build_pace_comparison(
    current_games: pd.DataFrame,
    team_id: int,
    reference_years: list[int],
) -> dict[int, pd.DataFrame]:
    """
    Load cached game logs for reference seasons to overlay on pace chart.
    Only returns seasons that have cached data.
    """
    result: dict[int, pd.DataFrame] = {}
    for year in reference_years:
        cache = CACHE_DIR / f"games_{team_id}_{year}.parquet"
        if cache.exists():
            df = pd.read_parquet(cache)
            if not df.empty:
                result[year] = df
        else:
            log.warning(
                "No cached data for %s %s — run `fetch.py --team %s --season %d` first",
                team_id, season_str(year), team_id, year,
            )
    return result
