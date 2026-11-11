"""
Prop board analytics: reference lines, hit rates with honest uncertainty, and
next-game context.

Two lines per market:
  - Current line: the half point next to this season's median that splits
    his games closest to 50/50, the way a book sets a line. It is the
    "typical night" for the player now, so it pairs with recent form, the
    venue split and tonight's matchup adjustment.
  - Last-season line: last season's average, set at the half point. The
    season hit rate against it answers "is he better than last year?"

Hit rates carry a 95% Wilson score interval. A rate counts as a lean only
when the whole interval sits on one side of 50%, which replaces a fixed
games-played cutoff: 11 of 11 is already a clear lean, 6 of 11 is not.

Tonight's estimate scales the current median by the expected pace of the game
and, for points only, by the opponent's defensive rating. The opponent's
rating is pulled toward league average early in the season, the same way the
Next Game projection treats net rating.
"""

from __future__ import annotations

from math import sqrt

import numpy as np
import pandas as pd

from analysis.matchup_preview import SHRINK_GAMES
from data.schedule import LOCAL_TZ, STATUS_FINAL

# Signature-stat candidates: (label, column, per-game average that makes it notable)
SIGNATURE_STATS = [
    ("Assists", "ast", 4.0),
    ("Rebounds", "reb", 6.0),
    ("3-Pointers Made", "fg3m", 1.5),
    ("Blocks", "blk", 1.5),
]

Z_95 = 1.96
MIN_PREV_GAMES = 10   # last-season games needed before a last-season line is shown
RECENT_GAMES = 5


def half_point_line(value: float) -> float:
    """Half-point line at the value's whole number, so there are no pushes: 17.3 -> 17.5, 1.0 -> 1.5."""
    return float(np.floor(value) + 0.5)


def balanced_line(values: pd.Series) -> float:
    """
    Half-point line beside the median that splits the games closest to 50/50.

    A whole-number median sits between two half points (median 4 -> 3.5 or 4.5);
    always rounding one way would bias every low-count stat toward the under.
    Ties go to the higher line. Lines never drop below 0.5.
    """
    median = float(values.median())
    if median != np.floor(median):           # already a half point (even game count)
        return max(0.5, half_point_line(median))
    candidates = [c for c in (median - 0.5, median + 0.5) if c >= 0.5]
    # |2*overs - n| is the distance from an even split in whole games, so ties are exact
    return min(candidates, key=lambda c: (abs(2 * int((values > c).sum()) - len(values)), -c))


def wilson_interval(hits: int, n: int, z: float = Z_95) -> tuple[float, float]:
    """95% Wilson score interval for a hit rate; (0, 1) when there are no games."""
    if n <= 0:
        return 0.0, 1.0
    p = hits / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    spread = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return max(0.0, (centre - spread) / denom), min(1.0, (centre + spread) / denom)


def lean(hits: int, n: int) -> str | None:
    """'over' or 'under' when the 95% interval excludes 50%, otherwise None."""
    lo, hi = wilson_interval(hits, n)
    if lo > 0.5:
        return "over"
    if hi < 0.5:
        return "under"
    return None


def _played(logs: pd.DataFrame) -> pd.DataFrame:
    return logs[logs["min"] > 0] if not logs.empty else logs


def rotation_markets(player_logs: pd.DataFrame, top_n: int = 8) -> list[tuple[str, str, str]]:
    """
    Points plus the most notable signature stat for the top `top_n` players by minutes.
    Returns (player, stat label, column) rows.
    """
    played = _played(player_logs)
    if played.empty:
        return []
    by_min = played.groupby("player_name")["min"].mean().sort_values(ascending=False).head(top_n)
    rows = []
    for name in by_min.index:
        cur = played[played["player_name"] == name]
        rows.append((name, "Points", "pts"))
        notable = [(lbl, col, cur[col].mean() / bar) for lbl, col, bar in SIGNATURE_STATS if cur[col].mean() >= bar]
        if notable:
            lbl, col, _ = max(notable, key=lambda m: m[2])
            rows.append((name, lbl, col))
    return rows


def matchup_factors(standings: pd.DataFrame, team: str, opponent: str) -> dict:
    """
    Multipliers for tonight's counting stats.

    pace_factor: expected game pace (mean of both teams) over the team's own pace.
    points_factor: pace_factor times the opponent's shrunk defensive rating over league average.
    """
    neutral = {"pace_factor": 1.0, "points_factor": 1.0, "available": False}
    if standings.empty or not {team, opponent} <= set(standings["team_abbr"]):
        return neutral
    s = standings.set_index("team_abbr")
    us, them = s.loc[team], s.loc[opponent]
    league_drtg = float(s["drtg"].mean())
    opp_gp = int(them["wins"] + them["losses"])
    weight = opp_gp / (opp_gp + SHRINK_GAMES)
    opp_drtg_adj = league_drtg + (float(them["drtg"]) - league_drtg) * weight
    game_pace = (float(us["pace"]) + float(them["pace"])) / 2
    pace_factor = game_pace / float(us["pace"])
    def_factor = opp_drtg_adj / league_drtg
    return {
        "available": True,
        "team_pace": float(us["pace"]),
        "opp_pace": float(them["pace"]),
        "game_pace": game_pace,
        "pace_factor": pace_factor,
        "opp_drtg": float(them["drtg"]),
        "opp_drtg_adj": opp_drtg_adj,
        "opp_drtg_rank": int(s["drtg"].rank(method="min").loc[opponent]),   # 1 = stingiest
        "league_drtg": league_drtg,
        "opp_games": opp_gp,
        "def_factor": def_factor,
        "points_factor": pace_factor * def_factor,
        "teams": len(s),
    }


def rest_days(schedule: pd.DataFrame, team: str, tipoff_local) -> int | None:
    """Full days off before `tipoff_local` (0 = second night of a back-to-back); None before a first game."""
    if schedule.empty:
        return None
    mine = schedule[((schedule["home_abbr"] == team) | (schedule["away_abbr"] == team))
                    & (schedule["status"] == STATUS_FINAL)]
    if mine.empty:
        return None
    tips = pd.to_datetime(mine["tipoff_utc"], utc=True).dt.tz_convert(LOCAL_TZ)
    before = tips[tips < pd.Timestamp(tipoff_local)]
    if before.empty:
        return None
    return max(0, (tipoff_local.date() - before.max().date()).days - 1)


def prop_rows(
    player_logs: pd.DataFrame,
    prev_logs: pd.DataFrame,
    games: pd.DataFrame,
    factors: dict | None = None,
    venue: str | None = None,
    top_n: int = 8,
) -> list[dict]:
    """
    One dict per market with both lines and their hit rates.

    `venue` is "H" or "A" for tonight's game; the venue split counts only games
    the team played there. `factors` comes from matchup_factors().
    """
    played = _played(player_logs)
    if played.empty:
        return []
    prev = _played(prev_logs)
    factors = factors or {"pace_factor": 1.0, "points_factor": 1.0}
    venue_of = games.set_index("game_id")["home_away"] if not games.empty else pd.Series(dtype=str)

    rows = []
    for name, label, col in rotation_markets(player_logs, top_n):
        # Exact name match (first names collide) and only games played (DNPs would deflate hit rates)
        df = played[played["player_name"] == name].sort_values("game_date")
        vals = df[col].fillna(0).astype(float)
        n = len(vals)
        median = float(vals.median())
        cur_line = balanced_line(vals)

        recent = vals.tail(RECENT_GAMES)
        at_venue = vals[df["game_id"].map(venue_of).eq(venue).to_numpy()] if venue else vals.iloc[0:0]
        factor = factors["points_factor"] if col == "pts" else factors["pace_factor"]

        old = prev[prev["player_name"] == name] if not prev.empty else prev
        if len(old) >= MIN_PREV_GAMES:
            prev_line = half_point_line(float(old[col].mean()))
            prev_hits = int((vals > prev_line).sum())
        else:
            prev_line, prev_hits = None, None

        rows.append({
            "player_name": name,
            "stat": label,
            "col": col,
            "games": n,
            "mean": float(vals.mean()),
            "median": median,
            "sd": float(vals.std()) if n > 1 else 0.0,
            "current_line": cur_line,
            "recent_hits": int((recent > cur_line).sum()),
            "recent_n": len(recent),
            "venue_hits": int((at_venue > cur_line).sum()),
            "venue_n": len(at_venue),
            "tonight": median * factor,
            "prev_line": prev_line,
            "prev_hits": prev_hits,
            "prev_range": wilson_interval(prev_hits, n) if prev_line is not None else None,
            "prev_lean": lean(prev_hits, n) if prev_line is not None else None,
        })
    return rows
