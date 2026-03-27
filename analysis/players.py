"""
Player-focused analytics.

Covers:
  - Usage + efficiency breakdown
  - Double-double / triple-double tracker
  - Player consistency score (scoring std dev)
  - Starter vs. bench splits (detailed)
  - Per-opponent splits
"""

from __future__ import annotations

import pandas as pd
from rich.console import Console
from rich.table import Table
from rich import box


# ---------------------------------------------------------------------------
# Usage & efficiency
# ---------------------------------------------------------------------------

def player_usage_breakdown(
    player_logs: pd.DataFrame, min_games: int = 10
) -> pd.DataFrame:
    """usg_pct, ts_pct, ast/tov ratio per player."""
    if player_logs.empty:
        return pd.DataFrame()

    agg = player_logs.groupby("player_id").agg(
        player_name=("player_name", "first"),
        games      =("game_id",     "count"),
        usg_pct    =("usg_pct",     "mean"),
        ts_pct     =("ts_pct",      "mean"),
        ast        =("ast",         "mean"),
        tov        =("tov",         "mean"),
    ).reset_index()

    agg = agg[agg["games"] >= min_games].copy()
    agg["ast_tov"] = (agg["ast"] / agg["tov"].replace(0, 1)).round(1)
    for col in ("ast", "tov"):
        agg[col] = agg[col].round(1)
    for col in ("usg_pct", "ts_pct"):
        agg[col] = agg[col].round(3)

    return agg.sort_values("usg_pct", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Double-double / triple-double tracker
# ---------------------------------------------------------------------------

def _is_dd(row: pd.Series) -> bool:
    cats = sum(1 for c in ("pts", "reb", "ast", "stl", "blk") if int(row.get(c, 0)) >= 10)
    return cats >= 2


def _is_td(row: pd.Series) -> bool:
    cats = sum(1 for c in ("pts", "reb", "ast", "stl", "blk") if int(row.get(c, 0)) >= 10)
    return cats >= 3


def double_double_tracker(player_logs: pd.DataFrame, min_games: int = 5) -> pd.DataFrame:
    """Count double-doubles and triple-doubles per player."""
    if player_logs.empty:
        return pd.DataFrame()

    player_logs = player_logs.copy()
    player_logs["dd"] = player_logs.apply(_is_dd, axis=1)
    player_logs["td"] = player_logs.apply(_is_td, axis=1)

    agg = player_logs.groupby("player_id").agg(
        player_name=("player_name", "first"),
        games      =("game_id",     "count"),
        dd         =("dd",          "sum"),
        td         =("td",          "sum"),
    ).reset_index()

    return (
        agg[agg["games"] >= min_games]
        .sort_values("dd", ascending=False)
        .reset_index(drop=True)
    )


# ---------------------------------------------------------------------------
# Consistency score
# ---------------------------------------------------------------------------

def player_consistency_score(
    player_logs: pd.DataFrame, player_id: int
) -> float:
    """
    Standard deviation of scoring — lower = more consistent.
    Returns 0.0 if player not found or < 5 games.
    """
    games = player_logs[player_logs["player_id"] == player_id]["pts"]
    if len(games) < 5:
        return 0.0
    return round(float(games.std()), 1)


def consistency_table(
    player_logs: pd.DataFrame, min_games: int = 10
) -> pd.DataFrame:
    """Scoring std dev for all qualified players."""
    if player_logs.empty:
        return pd.DataFrame()

    agg = player_logs.groupby("player_id").agg(
        player_name=("player_name", "first"),
        games      =("game_id",     "count"),
        pts_avg    =("pts",         "mean"),
        pts_std    =("pts",         "std"),
        pts_min    =("pts",         "min"),
        pts_max    =("pts",         "max"),
    ).reset_index()

    agg = agg[agg["games"] >= min_games].copy()
    for col in ("pts_avg", "pts_std"):
        agg[col] = agg[col].round(1)

    return agg.sort_values("pts_avg", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Starter vs. bench (detailed)
# ---------------------------------------------------------------------------

def starter_bench_split(player_logs: pd.DataFrame) -> pd.DataFrame:
    """
    Detailed pts/reb/ast/ts_pct split for each player classified as
    starter (top 5 by minutes) vs. bench.
    """
    if player_logs.empty:
        return pd.DataFrame()

    per_game = player_logs.groupby("player_id").agg(
        player_name=("player_name", "first"),
        games      =("game_id",     "count"),
        avg_min    =("min",         "mean"),
        pts        =("pts",         "mean"),
        reb        =("reb",         "mean"),
        ast        =("ast",         "mean"),
        ts_pct     =("ts_pct",      "mean"),
        usg_pct    =("usg_pct",     "mean"),
    ).reset_index()

    per_game = per_game[per_game["games"] >= 5].copy()
    top5_ids = per_game.nlargest(5, "avg_min")["player_id"].tolist()
    per_game["role"] = per_game["player_id"].apply(
        lambda p: "Starter" if p in top5_ids else "Bench"
    )

    for col in ("pts", "reb", "ast", "avg_min"):
        per_game[col] = per_game[col].round(1)
    for col in ("ts_pct", "usg_pct"):
        per_game[col] = per_game[col].round(3)

    return per_game[
        ["role", "player_name", "games", "avg_min", "pts", "reb", "ast", "ts_pct", "usg_pct"]
    ].sort_values(["role", "pts"], ascending=[True, False]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Per-opponent splits
# ---------------------------------------------------------------------------

def player_vs_opponent_splits(
    player_logs: pd.DataFrame, player_id: int
) -> pd.DataFrame:
    """Per-player averages grouped by opponent (find favorable matchups)."""
    player = player_logs[player_logs["player_id"] == player_id]
    if player.empty:
        return pd.DataFrame()

    return (
        player.groupby("opponent_abbr" if "opponent_abbr" in player.columns else "game_id")
        .agg(
            games =("game_id", "count"),
            pts   =("pts",     "mean"),
            reb   =("reb",     "mean"),
            ast   =("ast",     "mean"),
            ts_pct=("ts_pct",  "mean"),
        )
        .round(1)
        .reset_index()
        .sort_values("pts", ascending=False)
    )


# ---------------------------------------------------------------------------
# Rich terminal output
# ---------------------------------------------------------------------------

def print_players(
    console: Console,
    player_logs: pd.DataFrame,
    roster: pd.DataFrame,
) -> None:
    # Usage breakdown
    ub = player_usage_breakdown(player_logs)
    if not ub.empty:
        t = Table(title="Player Usage & Efficiency  (min 10 games)", box=box.SIMPLE)
        t.add_column("Player",    style="cyan",  min_width=20)
        t.add_column("G",         style="dim",   justify="right")
        t.add_column("USG%",      style="yellow",justify="right")
        t.add_column("TS%",       style="cyan",  justify="right")
        t.add_column("Ast",       style="white", justify="right")
        t.add_column("Tov",       style="red",   justify="right")
        t.add_column("Ast/Tov",   style="green", justify="right")
        for _, row in ub.iterrows():
            t.add_row(
                row["player_name"], str(int(row["games"])),
                f"{row['usg_pct'] * 100:.1f}%", f"{row['ts_pct']:.3f}",
                f"{row['ast']:.1f}", f"{row['tov']:.1f}", f"{row['ast_tov']:.1f}",
            )
        console.print(t)

    # Double-double tracker
    dd = double_double_tracker(player_logs)
    if not dd.empty:
        ddt = Table(title="Double-Double / Triple-Double Tracker", box=box.SIMPLE)
        ddt.add_column("Player",   style="cyan",   min_width=20)
        ddt.add_column("G",        style="dim",    justify="right")
        ddt.add_column("DD",       style="yellow", justify="right")
        ddt.add_column("TD",       style="green",  justify="right")
        for _, row in dd.head(15).iterrows():
            ddt.add_row(
                row["player_name"], str(int(row["games"])),
                str(int(row["dd"])), str(int(row["td"])),
            )
        console.print(ddt)

    # Consistency
    cons = consistency_table(player_logs)
    if not cons.empty:
        ct = Table(title="Scoring Consistency  (lower std dev = more consistent)", box=box.SIMPLE)
        ct.add_column("Player",  style="cyan",  min_width=20)
        ct.add_column("G",       style="dim",   justify="right")
        ct.add_column("Pts Avg", style="white", justify="right")
        ct.add_column("Std Dev", style="yellow",justify="right")
        ct.add_column("Min",     style="dim",   justify="right")
        ct.add_column("Max",     style="dim",   justify="right")
        for _, row in cons.iterrows():
            ct.add_row(
                row["player_name"], str(int(row["games"])),
                f"{row['pts_avg']:.1f}", f"{row['pts_std']:.1f}",
                str(int(row["pts_min"])), str(int(row["pts_max"])),
            )
        console.print(ct)
