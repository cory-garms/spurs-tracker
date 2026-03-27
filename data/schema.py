"""
Canonical DataFrame schemas for the NBA tracker.

Each constant is a dict mapping column name → pandas dtype string.
Used by fetcher.py to enforce consistent shape when building / loading cache.

Tables
------
GAMES_SCHEMA          one row per team-game
PLAYER_GAME_LOG_SCHEMA one row per player per game
ROSTER_SCHEMA         current season roster snapshot
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# GAMES  — team-level game results
# ---------------------------------------------------------------------------
GAMES_SCHEMA: dict[str, str] = {
    "game_id":       "object",    # NBA game ID string, e.g. "0022401001"
    "game_date":     "object",    # YYYY-MM-DD string; cast to datetime when needed
    "season":        "object",    # "2024-25"
    "home_away":     "object",    # "H" or "A"
    "opponent_id":   "Int64",
    "opponent_abbr": "object",
    "result":        "object",    # "W" or "L"
    "pts":           "Int64",     # team points
    "opp_pts":       "Int64",     # opponent points
    "margin":        "Int64",     # pts - opp_pts
    "pace":          "Float64",   # possessions per 48 min
    "ortg":          "Float64",   # offensive rating
    "drtg":          "Float64",   # defensive rating
    "nrtg":          "Float64",   # net rating
    "status":        "object",    # "Final" or "Scheduled"
}

# ---------------------------------------------------------------------------
# PLAYER_GAME_LOG  — per-player per-game stats
# ---------------------------------------------------------------------------
PLAYER_GAME_LOG_SCHEMA: dict[str, str] = {
    "game_id":    "object",
    "game_date":  "object",
    "season":     "object",
    "player_id":  "Int64",
    "player_name":"object",
    "min":        "Float64",   # minutes played
    "pts":        "Int64",
    "reb":        "Int64",     # total rebounds
    "ast":        "Int64",
    "stl":        "Int64",
    "blk":        "Int64",
    "tov":        "Int64",     # turnovers
    "pf":         "Int64",     # personal fouls
    "fgm":        "Int64",
    "fga":        "Int64",
    "fg_pct":     "Float64",
    "fg3m":       "Int64",
    "fg3a":       "Int64",
    "fg3_pct":    "Float64",
    "ftm":        "Int64",
    "fta":        "Int64",
    "ft_pct":     "Float64",
    "plus_minus": "Int64",
    "ts_pct":     "Float64",   # true shooting % (computed)
    "usg_pct":    "Float64",   # usage rate (from advanced boxscore)
}

# ---------------------------------------------------------------------------
# ROSTER  — current season roster snapshot
# ---------------------------------------------------------------------------
ROSTER_SCHEMA: dict[str, str] = {
    "player_id":        "Int64",
    "player_name":      "object",
    "jersey_number":    "object",
    "position":         "object",        # G, F, C, G-F, F-C, etc.
    "position_group":   "object",        # "G", "F", "C"
    "years_of_experience": "Int64",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def enforce_schema(df, schema: dict[str, str]):
    """
    Cast a DataFrame to the given schema, adding missing columns as NA
    and dropping extra columns.
    """
    import pandas as pd

    for col, dtype in schema.items():
        if col not in df.columns:
            df[col] = pd.NA
        try:
            df[col] = df[col].astype(dtype)
        except (ValueError, TypeError):
            pass  # leave as-is if cast fails (will surface in analysis)

    return df[list(schema.keys())]
