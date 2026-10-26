"""
Lineup & Rotation Synergy Modeling Engine.

Analyzes 2-man player pairings, starter vs. bench unit production,
plus/minus differentials, and rotation chemistry.

Covers:
  - 2-Man Pairing Net Plus/Minus and Minute Overlap
  - Top rotation synergies from the current roster
  - Starter Unit vs. Second Unit (Bench Mob) Efficiency
"""

from __future__ import annotations

import itertools
import pandas as pd
import numpy as np


def two_man_pairings(player_logs: pd.DataFrame, min_games: int = 5) -> pd.DataFrame:
    """
    Compute 2-man pairing metrics across all qualified rotation players.
    Returns DataFrame sorted by combined plus/minus per game.
    """
    if player_logs.empty:
        return pd.DataFrame()

    # Filter to players who actually saw minutes
    active_logs = player_logs[player_logs["min"] > 0].copy()

    records = []
    # Group by game_id to find players who played in the same game
    by_game = active_logs.groupby("game_id")

    pair_stats: dict[tuple[str, str], dict] = {}

    for _, game_df in by_game:
        players = game_df.sort_values("player_name")[["player_name", "min", "plus_minus", "pts"]].to_dict("records")
        for p1, p2 in itertools.combinations(players, 2):
            key = (p1["player_name"], p2["player_name"])
            if key not in pair_stats:
                pair_stats[key] = {
                    "games": 0,
                    "min_combined": 0.0,
                    "pm_combined": 0,
                    "pts_combined": 0,
                }
            pair_stats[key]["games"] += 1
            pair_stats[key]["min_combined"] += min(p1["min"], p2["min"])  # estimated shared floor time
            pair_stats[key]["pm_combined"] += (p1["plus_minus"] + p2["plus_minus"]) / 2
            pair_stats[key]["pts_combined"] += p1["pts"] + p2["pts"]

    for (p1, p2), stats in pair_stats.items():
        g = stats["games"]
        if g < min_games:
            continue
        records.append({
            "player_1": p1,
            "player_2": p2,
            "pairing": f"{p1.split()[-1]} + {p2.split()[-1]}",
            "games_together": g,
            "est_shared_min_pg": round(stats["min_combined"] / g, 1),
            "net_pm_pg": round(stats["pm_combined"] / g, 2),
            "combined_pts_pg": round(stats["pts_combined"] / g, 1),
        })

    df = pd.DataFrame(records)
    if df.empty:
        return df
    return df.sort_values("net_pm_pg", ascending=False).reset_index(drop=True)


def key_spurs_synergies(player_logs: pd.DataFrame) -> pd.DataFrame:
    """
    Top 2-man pairings drawn from the current roster.

    A pairing qualifies when both players logged minutes together in at least
    half of the team's games, so the list stays meaningful early in the season
    and adapts automatically as the rotation changes.
    """
    if player_logs.empty:
        return pd.DataFrame()

    team_games = player_logs["game_id"].nunique()
    min_games = max(1, int(np.ceil(team_games / 2)))
    return two_man_pairings(player_logs, min_games=min_games)


def starter_bench_deep_split(player_logs: pd.DataFrame) -> dict:
    """
    Detailed aggregate statistics comparing the primary Starting 5 unit
    against the Second Unit (Bench Mob).
    """
    if player_logs.empty:
        return {}

    active_logs = player_logs[player_logs["min"] > 0]
    per_player = active_logs.groupby(["player_id", "player_name"]).agg(
        games=("game_id", "count"),
        avg_min=("min", "mean"),
        total_pts=("pts", "sum"),
        total_reb=("reb", "sum"),
        total_ast=("ast", "sum"),
        avg_pm=("plus_minus", "mean"),
        avg_ts=("ts_pct", "mean"),
    ).reset_index()

    if len(per_player) < 5:
        return {}

    # Define starters as top 5 by average minutes
    top5_ids = set(per_player.nlargest(5, "avg_min")["player_id"])
    starter_df = per_player[per_player["player_id"].isin(top5_ids)]
    bench_df = per_player[~per_player["player_id"].isin(top5_ids)]

    total_pts_all = float(per_player["total_pts"].sum())
    starter_pts = float(starter_df["total_pts"].sum())
    bench_pts = float(bench_df["total_pts"].sum())

    bench_scoring_share = (bench_pts / total_pts_all * 100) if total_pts_all > 0 else 0.0
    starter_scoring_share = (starter_pts / total_pts_all * 100) if total_pts_all > 0 else 0.0

    return {
        "starter_names": starter_df["player_name"].tolist(),
        "bench_names": bench_df["player_name"].tolist(),
        "starter_avg_pts": round(float(starter_df["total_pts"].sum() / starter_df["games"].max()), 1),
        "bench_avg_pts": round(float(bench_df["total_pts"].sum() / bench_df["games"].max()), 1) if not bench_df.empty else 0.0,
        "starter_avg_pm": round(float(starter_df["avg_pm"].mean()), 2),
        "bench_avg_pm": round(float(bench_df["avg_pm"].mean()), 2) if not bench_df.empty else 0.0,
        "starter_ts_pct": round(float(starter_df["avg_ts"].mean()), 3),
        "bench_ts_pct": round(float(bench_df["avg_ts"].mean()), 3) if not bench_df.empty else 0.0,
        "starter_scoring_share_pct": round(starter_scoring_share, 1),
        "bench_scoring_share_pct": round(bench_scoring_share, 1),
    }


def print_lineup_synergies(console, player_logs: pd.DataFrame) -> None:
    """Print rich rotation synergies and 2-man pairings to terminal."""
    from rich.table import Table
    from rich import box

    synergies = key_spurs_synergies(player_logs)
    if synergies.empty:
        console.print("[yellow]No pairing data available.[/yellow]")
        return

    table = Table(title="Spurs Rotation Synergies & 2-Man Pairings", box=box.ROUNDED)
    table.add_column("Pairing", style="bold white", no_wrap=True)
    table.add_column("Games Together", justify="center", style="cyan")
    table.add_column("Shared Min/G", justify="right", style="dim")
    table.add_column("Net +/- per G", justify="right", style="yellow")
    table.add_column("Comb PTS/G", justify="right", style="white")

    for _, r in synergies.iterrows():
        pm_val = float(r["net_pm_pg"])
        pm_color = "green" if pm_val > 0 else "red"
        table.add_row(
            f"{r['player_1']} & {r['player_2']}",
            str(r["games_together"]),
            f"{r['est_shared_min_pg']:.1f}",
            f"[{pm_color}]{pm_val:+.2f}[/{pm_color}]",
            f"{r['combined_pts_pg']:.1f}",
        )

    console.print(table)

