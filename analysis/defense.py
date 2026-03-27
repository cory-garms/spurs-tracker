"""
Defensive analytics.

Covers:
  - Team defensive rating, opponent points, steals/blocks
  - Player defensive stats (stl, blk, dreb, plus_minus)
  - Defensive rating trend (rolling drtg)
"""

from __future__ import annotations

import pandas as pd
from rich.console import Console
from rich.table import Table
from rich import box


# ---------------------------------------------------------------------------
# Team defense summary
# ---------------------------------------------------------------------------

def team_defense_summary(games: pd.DataFrame) -> dict:
    """
    Team-level defensive stats.

    Keys: drtg, opp_pts_per_game, avg_margin, stl_per_game,
          blk_per_game, dreb_per_game
    Note: stl/blk/dreb come from player_logs if passed, else from games.
    """
    f = games[games["status"] == "Final"]
    if f.empty:
        return {}
    g = len(f)
    return dict(
        drtg           = round(float(f["drtg"].mean()), 1) if "drtg" in f.columns else 0.0,
        opp_pts_per_game = round(float(f["opp_pts"].mean()), 1) if g > 0 else 0.0,
        avg_margin     = round(float(f["margin"].mean()), 2) if g > 0 else 0.0,
    )


def player_defense_stats(player_logs: pd.DataFrame, min_games: int = 10) -> pd.DataFrame:
    """
    Per-game defensive averages: stl, blk, dreb, pf, plus_minus.
    """
    if player_logs.empty:
        return pd.DataFrame()

    agg = player_logs.groupby("player_id").agg(
        player_name=("player_name", "first"),
        games      =("game_id",     "count"),
        stl        =("stl",         "mean"),
        blk        =("blk",         "mean"),
        tov        =("tov",         "mean"),
        pf         =("pf",          "mean"),
        plus_minus =("plus_minus",  "mean"),
    ).reset_index()

    agg = agg[agg["games"] >= min_games].copy()
    for col in ("stl", "blk", "tov", "pf", "plus_minus"):
        agg[col] = agg[col].round(1)

    return agg.sort_values("plus_minus", ascending=False).reset_index(drop=True)


def defensive_ratings_trend(games: pd.DataFrame, window: int = 10) -> pd.DataFrame:
    """Rolling defensive rating for trend chart."""
    f = games[games["status"] == "Final"].sort_values("game_date").copy()
    if f.empty or "drtg" not in f.columns:
        return pd.DataFrame()
    f["rolling_drtg"] = f["drtg"].rolling(window).mean().round(1)
    return f[["game_date", "drtg", "rolling_drtg"]].set_index("game_date")


# ---------------------------------------------------------------------------
# Rich terminal output
# ---------------------------------------------------------------------------

def print_defense(
    console: Console,
    games: pd.DataFrame,
    player_logs: pd.DataFrame,
    roster: pd.DataFrame,
) -> None:
    summary = team_defense_summary(games)
    if not summary:
        console.print("[yellow]No game data for defense summary.[/yellow]")
        return

    team_t = Table(title="Team Defense — Season", box=box.SIMPLE_HEAVY)
    for col in ("DRtg", "Opp Pts/G", "Avg Margin"):
        team_t.add_column(col, style="white", justify="right")
    drtg = summary["drtg"]
    drtg_style = "green" if drtg < 110.0 else "red"
    margin = summary["avg_margin"]
    margin_style = "green" if margin > 0 else "red"
    team_t.add_row(
        f"[{drtg_style}]{drtg:.1f}[/{drtg_style}]",
        f"{summary['opp_pts_per_game']:.1f}",
        f"[{margin_style}]{margin:+.1f}[/{margin_style}]",
    )
    console.print(team_t)

    def_stats = player_defense_stats(player_logs, min_games=10)
    if not def_stats.empty:
        dt = Table(title="Player Defense  (min 10 games · sorted by +/-)", box=box.SIMPLE)
        dt.add_column("Player",    style="cyan",  min_width=20)
        dt.add_column("G",         style="dim",   justify="right")
        dt.add_column("Stl",       style="green", justify="right")
        dt.add_column("Blk",       style="green", justify="right")
        dt.add_column("Tov",       style="red",   justify="right")
        dt.add_column("PF",        style="dim",   justify="right")
        dt.add_column("+/-",       style="bold",  justify="right")

        for _, row in def_stats.iterrows():
            pm = row["plus_minus"]
            pm_style = "green" if pm > 0 else ("red" if pm < 0 else "white")
            dt.add_row(
                row["player_name"], str(int(row["games"])),
                f"{row['stl']:.1f}", f"{row['blk']:.1f}",
                f"{row['tov']:.1f}", f"{row['pf']:.1f}",
                f"[{pm_style}]{pm:+.1f}[/{pm_style}]",
            )
        console.print(dt)
