"""
Streak, back-to-back, and monthly pattern analysis.

Covers:
  - Current win/loss streak
  - Longest streak (win or loss)
  - Streak timeline for charting
  - Back-to-back game records (critical for NBA schedule)
  - Monthly record splits
  - Scoring drought games (scored below threshold)
"""

from __future__ import annotations

import pandas as pd
from rich.console import Console
from rich.table import Table
from rich import box

from config import TEAMS

_ID_TO_ABBR: dict[int, str] = {v["id"]: k for k, v in TEAMS.items()}


# ---------------------------------------------------------------------------
# Team win/loss streaks
# ---------------------------------------------------------------------------

def current_streak(games: pd.DataFrame) -> tuple[str, int]:
    """
    Return (type, length) for the current streak.
    type = 'W' or 'L', length = consecutive games.
    Returns ('', 0) if no games played.
    """
    finished = games[games["status"] == "Final"].sort_values("game_date")
    if finished.empty:
        return ("", 0)
    results = finished["result"].tolist()
    last    = results[-1]
    count   = 0
    for r in reversed(results):
        if r == last:
            count += 1
        else:
            break
    return (last, count)


def longest_streak(games: pd.DataFrame, streak_type: str = "W") -> int:
    """Longest win or loss streak in the season."""
    finished = games[games["status"] == "Final"].sort_values("game_date")
    if finished.empty:
        return 0

    longest = current = 0
    for r in finished["result"]:
        if r == streak_type:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def streak_timeline(games: pd.DataFrame) -> pd.DataFrame:
    """
    One row per game with signed streak value:
      positive = win streak length at that game
      negative = -1 * loss streak length at that game
    """
    finished = games[games["status"] == "Final"].sort_values("game_date").reset_index(drop=True)
    if finished.empty:
        return pd.DataFrame()

    streaks = []
    current = 0
    last_result = None

    for _, row in finished.iterrows():
        r = row["result"]
        if r == last_result:
            current += 1 if r == "W" else -1
        else:
            current = 1 if r == "W" else -1
            last_result = r
        streaks.append(current)

    finished = finished.copy()
    finished["streak_value"] = streaks
    return finished[["game_date", "result", "streak_value"]]


# ---------------------------------------------------------------------------
# Back-to-back games
# ---------------------------------------------------------------------------

def back_to_back_record(games: pd.DataFrame) -> dict:
    """
    NBA-specific: identify games that are the 2nd night of a back-to-back
    and compute W-L for those games separately.

    Returns: b2b_games (count), b2b_w, b2b_l, rest_w, rest_l
    """
    finished = games[games["status"] == "Final"].sort_values("game_date").reset_index(drop=True)
    if finished.empty:
        return {}

    finished["game_date_dt"] = pd.to_datetime(finished["game_date"])
    finished["prev_date"]    = finished["game_date_dt"].shift(1)
    finished["days_rest"]    = (
        finished["game_date_dt"] - finished["prev_date"]
    ).dt.days.fillna(99)

    b2b  = finished[finished["days_rest"] == 1]
    rest = finished[finished["days_rest"] != 1]

    def wl(df):
        return int((df["result"] == "W").sum()), int((df["result"] == "L").sum())

    b2b_w,  b2b_l  = wl(b2b)
    rest_w, rest_l = wl(rest)

    return dict(
        b2b_games=len(b2b),
        b2b_w=b2b_w, b2b_l=b2b_l,
        rest_w=rest_w, rest_l=rest_l,
    )


# ---------------------------------------------------------------------------
# Monthly record
# ---------------------------------------------------------------------------

def monthly_record(games: pd.DataFrame) -> pd.DataFrame:
    """W-L record broken down by calendar month."""
    finished = games[games["status"] == "Final"].copy()
    if finished.empty:
        return pd.DataFrame()

    finished["month"] = pd.to_datetime(finished["game_date"]).dt.to_period("M")
    agg = finished.groupby("month").apply(
        lambda df: pd.Series({
            "w":  int((df["result"] == "W").sum()),
            "l":  int((df["result"] == "L").sum()),
            "pts_avg": round(float(df["pts"].mean()), 1),
            "opp_pts_avg": round(float(df["opp_pts"].mean()), 1),
        })
    ).reset_index()
    agg["win_pct"] = (agg["w"] / (agg["w"] + agg["l"])).round(3)
    return agg


# ---------------------------------------------------------------------------
# Scoring drought games
# ---------------------------------------------------------------------------

def scoring_drought_games(games: pd.DataFrame, threshold: int = 100) -> pd.DataFrame:
    """Games where team scored below threshold (blowout / poor offense context)."""
    finished = games[games["status"] == "Final"]
    return (
        finished[finished["pts"] < threshold]
        .sort_values("pts")
        [["game_date", "opponent_abbr", "pts", "opp_pts", "margin", "result"]]
        .reset_index(drop=True)
    )


# ---------------------------------------------------------------------------
# Rich terminal output
# ---------------------------------------------------------------------------

def print_streaks(
    console: Console,
    games: pd.DataFrame,
    player_logs: pd.DataFrame | None = None,
) -> None:
    streak_t, streak_l = current_streak(games)
    long_w = longest_streak(games, "W")
    long_l = longest_streak(games, "L")
    b2b    = back_to_back_record(games)

    # Streak summary
    s_col = "green" if streak_t == "W" else "red"
    console.print(
        f"\nCurrent streak: [{s_col}]{streak_t}{streak_l}[/{s_col}]  |  "
        f"Longest W-streak: [green]{long_w}[/green]  |  "
        f"Longest L-streak: [red]{long_l}[/red]\n"
    )

    # Back-to-back table
    if b2b:
        b2b_t = Table(title="Back-to-Back Record (2nd night of B2B)", box=box.SIMPLE)
        b2b_t.add_column("Situation", style="cyan")
        b2b_t.add_column("W",         style="green", justify="right")
        b2b_t.add_column("L",         style="red",   justify="right")
        b2b_t.add_column("Win%",      style="white", justify="right")

        b2b_played = b2b["b2b_w"] + b2b["b2b_l"]
        rest_played = b2b["rest_w"] + b2b["rest_l"]
        b2b_pct  = b2b["b2b_w"]  / b2b_played  if b2b_played  > 0 else 0.0
        rest_pct = b2b["rest_w"] / rest_played if rest_played > 0 else 0.0

        b2b_t.add_row("B2B (2nd night)", str(b2b["b2b_w"]), str(b2b["b2b_l"]), f"{b2b_pct:.3f}")
        b2b_t.add_row("Normal rest",    str(b2b["rest_w"]),str(b2b["rest_l"]),f"{rest_pct:.3f}")
        console.print(b2b_t)

    # Monthly record
    monthly = monthly_record(games)
    if not monthly.empty:
        mt = Table(title="Monthly Record", box=box.SIMPLE)
        mt.add_column("Month",     style="cyan")
        mt.add_column("W",         style="green", justify="right")
        mt.add_column("L",         style="red",   justify="right")
        mt.add_column("Win%",      style="white", justify="right")
        mt.add_column("Pts/G",     style="dim",   justify="right")
        mt.add_column("Opp Pts/G", style="dim",   justify="right")
        for _, row in monthly.iterrows():
            mt.add_row(
                str(row["month"]),
                str(int(row["w"])), str(int(row["l"])),
                f"{row['win_pct']:.3f}",
                f"{row['pts_avg']:.1f}", f"{row['opp_pts_avg']:.1f}",
            )
        console.print(mt)

    # Drought games
    drought = scoring_drought_games(games, threshold=100)
    if not drought.empty:
        dt = Table(title="Scoring Drought Games (< 100 pts)", box=box.SIMPLE)
        dt.add_column("Date",      style="cyan")
        dt.add_column("Opponent",  style="dim")
        dt.add_column("Pts",       style="red",   justify="right")
        dt.add_column("Opp Pts",   style="dim",   justify="right")
        dt.add_column("Margin",    style="dim",   justify="right")
        dt.add_column("Result",    style="white", justify="right")
        for _, row in drought.iterrows():
            dt.add_row(
                str(row["game_date"]), str(row.get("opponent_abbr", "")),
                str(int(row["pts"])), str(int(row["opp_pts"])),
                str(int(row["margin"])), row["result"],
            )
        console.print(dt)
