"""
Offensive analytics — team and player level.

Covers:
  - Team scoring, shooting efficiency, pace
  - Player season averages and leaderboard
  - Hot/cold tracker (5- and 10-game windows)
  - Starter vs. bench splits
  - Rolling stats for trend charting
"""

from __future__ import annotations

import logging

import pandas as pd
from rich.console import Console
from rich.table import Table
from rich import box

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Team-level aggregates
# ---------------------------------------------------------------------------

def team_offense_summary(player_logs: pd.DataFrame, games: pd.DataFrame) -> dict:
    """
    Return team-level offensive stats for the season.

    Keys: pts_per_game, opp_pts_per_game, fg_pct, fg3_pct, ft_pct,
          ts_pct, ast_per_game, pace, ortg
    """
    if player_logs.empty:
        return {}

    f = games[games["status"] == "Final"]
    g = len(f)
    if g == 0:
        return {}

    fgm  = float(player_logs["fgm"].sum())
    fga  = float(player_logs["fga"].sum())
    fg3m = float(player_logs["fg3m"].sum())
    fg3a = float(player_logs["fg3a"].sum())
    ftm  = float(player_logs["ftm"].sum())
    fta  = float(player_logs["fta"].sum())
    pts  = float(player_logs["pts"].sum())
    ast  = float(player_logs["ast"].sum())

    ts_denom = 2 * (fga + 0.44 * fta)
    ts_pct   = round(pts / ts_denom, 3) if ts_denom > 0 else 0.0

    return dict(
        pts_per_game     = round(float(f["pts"].mean()), 1) if g > 0 else 0.0,
        opp_pts_per_game = round(float(f["opp_pts"].mean()), 1) if g > 0 else 0.0,
        fg_pct           = round(fgm / fga, 3) if fga > 0 else 0.0,
        fg3_pct          = round(fg3m / fg3a, 3) if fg3a > 0 else 0.0,
        ft_pct           = round(ftm / fta, 3) if fta > 0 else 0.0,
        ts_pct           = ts_pct,
        ast_per_game     = round(ast / g, 1) if g > 0 else 0.0,
        pace             = round(float(f["pace"].mean()), 1) if "pace" in f else 0.0,
        ortg             = round(float(f["ortg"].mean()), 1) if "ortg" in f else 0.0,
    )


# ---------------------------------------------------------------------------
# Player averages
# ---------------------------------------------------------------------------

def player_season_averages(
    player_logs: pd.DataFrame, min_games: int = 10
) -> pd.DataFrame:
    """Per-game averages for all players with >= min_games appearances."""
    if player_logs.empty:
        return pd.DataFrame()

    agg = player_logs.groupby("player_id").agg(
        player_name=("player_name", "first"),
        games      =("game_id",     "count"),
        min        =("min",         "mean"),
        pts        =("pts",         "mean"),
        reb        =("reb",         "mean"),
        ast        =("ast",         "mean"),
        stl        =("stl",         "mean"),
        blk        =("blk",         "mean"),
        tov        =("tov",         "mean"),
        fgm        =("fgm",         "sum"),
        fga        =("fga",         "sum"),
        fg3m       =("fg3m",        "sum"),
        fg3a       =("fg3a",        "sum"),
        ftm        =("ftm",         "sum"),
        fta        =("fta",         "sum"),
        ts_pct     =("ts_pct",      "mean"),
        usg_pct    =("usg_pct",     "mean"),
    ).reset_index()

    agg = agg[agg["games"] >= min_games].copy()
    agg["fg_pct"]  = (agg["fgm"] / agg["fga"]).where(agg["fga"] > 0, 0.0).round(3)
    agg["fg3_pct"] = (agg["fg3m"] / agg["fg3a"]).where(agg["fg3a"] > 0, 0.0).round(3)
    agg["ft_pct"]  = (agg["ftm"] / agg["fta"]).where(agg["fta"] > 0, 0.0).round(3)

    for col in ("min", "pts", "reb", "ast", "stl", "blk", "tov"):
        agg[col] = agg[col].round(1)
    for col in ("ts_pct", "usg_pct"):
        agg[col] = agg[col].round(3)

    return agg.sort_values("pts", ascending=False).reset_index(drop=True)


def scoring_leaderboard(
    player_logs: pd.DataFrame, min_games: int = 10
) -> pd.DataFrame:
    """Sorted by pts, includes pts/reb/ast/ts_pct/usg_pct."""
    avgs = player_season_averages(player_logs, min_games)
    if avgs.empty:
        return avgs
    cols = ["player_name", "games", "min", "pts", "reb", "ast",
            "stl", "blk", "fg_pct", "fg3_pct", "ts_pct", "usg_pct"]
    available = [c for c in cols if c in avgs.columns]
    return avgs[available].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Hot / cold tracker
# ---------------------------------------------------------------------------

def _rolling_pts(player_logs: pd.DataFrame, player_id: int, window: int) -> float:
    """Average pts over last `window` games for a player."""
    player = (
        player_logs[player_logs["player_id"] == player_id]
        .sort_values("game_date")
        .tail(window)
    )
    if player.empty:
        return 0.0
    return round(float(player["pts"].mean()), 1)


def hot_cold_summary(
    player_logs: pd.DataFrame,
    windows: list[int] | None = None,
    min_games: int = 10,
) -> pd.DataFrame:
    """
    For each qualified player: season pts avg, last-5, last-10, delta, label.
    label = HOT (delta >= +3.0), COLD (delta <= -3.0), or blank.
    Uses 5- and 10-game windows (NBA plays more frequently than MLB).
    """
    if windows is None:
        windows = [5, 10]

    avgs = player_season_averages(player_logs, min_games)
    if avgs.empty:
        return pd.DataFrame()

    rows = []
    for _, srow in avgs.iterrows():
        pid   = srow["player_id"]
        entry = {
            "player_id":   pid,
            "player_name": srow["player_name"],
            "season_pts":  srow["pts"],
        }
        for w in windows:
            entry[f"last_{w}_pts"] = _rolling_pts(player_logs, pid, w)

        delta = round(entry[f"last_{windows[0]}_pts"] - srow["pts"], 1)
        entry["delta"] = delta
        entry["label"] = "HOT" if delta >= 3.0 else ("COLD" if delta <= -3.0 else "")
        rows.append(entry)

    return (
        pd.DataFrame(rows)
        .sort_values("delta", ascending=False)
        .reset_index(drop=True)
    )


# ---------------------------------------------------------------------------
# Starter vs. bench splits
# ---------------------------------------------------------------------------

def lineup_analysis(player_logs: pd.DataFrame) -> pd.DataFrame:
    """
    Average pts/reb/ast/ts_pct split by starters (top 5 by min) vs. bench.

    Starters are defined as the 5 players with highest average minutes per game.
    """
    if player_logs.empty:
        return pd.DataFrame()

    avgs = player_season_averages(player_logs, min_games=5)
    if avgs.empty:
        return pd.DataFrame()

    starters = avgs.nlargest(5, "min")["player_id"].tolist()
    avgs["role"] = avgs["player_id"].apply(lambda p: "Starter" if p in starters else "Bench")

    return (
        avgs.groupby("role")
        .agg(
            players   =("player_name", "count"),
            pts       =("pts",         "mean"),
            reb       =("reb",         "mean"),
            ast       =("ast",         "mean"),
            ts_pct    =("ts_pct",      "mean"),
            usg_pct   =("usg_pct",     "mean"),
        )
        .round(1)
        .reset_index()
    )


# ---------------------------------------------------------------------------
# Rolling stats (for trend charts)
# ---------------------------------------------------------------------------

def rolling_stats(
    player_logs: pd.DataFrame, player_id: int, window: int = 10
) -> pd.DataFrame:
    """Rolling pts/reb/ast for a single player (for trend charts)."""
    player = (
        player_logs[player_logs["player_id"] == player_id]
        .sort_values("game_date")
        .reset_index(drop=True)
    )
    if player.empty:
        return pd.DataFrame()

    return player[["game_date", "pts", "reb", "ast"]].assign(
        pts_roll=lambda df: df["pts"].rolling(window).mean().round(1),
        reb_roll=lambda df: df["reb"].rolling(window).mean().round(1),
        ast_roll=lambda df: df["ast"].rolling(window).mean().round(1),
    ).set_index("game_date")


# ---------------------------------------------------------------------------
# Rich terminal output
# ---------------------------------------------------------------------------

def print_offense(
    console: Console,
    player_logs: pd.DataFrame,
    games: pd.DataFrame,
    roster: pd.DataFrame,
) -> None:
    """Print full offensive dashboard."""
    off = team_offense_summary(player_logs, games)
    if not off:
        console.print("[yellow]No player log data.[/yellow]")
        return

    # Team summary
    team_t = Table(title="Team Offense — Season", box=box.SIMPLE_HEAVY)
    for col in ("Pts/G", "Opp/G", "FG%", "3P%", "FT%", "TS%", "Ast/G", "Pace", "ORtg"):
        team_t.add_column(col, style="white", justify="right")
    team_t.add_row(
        f"{off['pts_per_game']:.1f}",
        f"{off['opp_pts_per_game']:.1f}",
        f"{off['fg_pct']:.3f}",
        f"{off['fg3_pct']:.3f}",
        f"{off['ft_pct']:.3f}",
        f"{off['ts_pct']:.3f}",
        f"{off['ast_per_game']:.1f}",
        f"{off['pace']:.1f}",
        f"{off['ortg']:.1f}",
    )
    console.print(team_t)

    # Scoring leaderboard
    lb = scoring_leaderboard(player_logs, min_games=10)
    if not lb.empty:
        lb_t = Table(title="Scoring Leaderboard  (min 10 games)", box=box.SIMPLE)
        lb_t.add_column("Player",  style="cyan",       min_width=20)
        lb_t.add_column("G",       style="dim",         justify="right")
        lb_t.add_column("Min",     style="dim",         justify="right")
        lb_t.add_column("Pts",     style="bold yellow", justify="right")
        lb_t.add_column("Reb",     style="white",       justify="right")
        lb_t.add_column("Ast",     style="white",       justify="right")
        lb_t.add_column("Stl",     style="green",       justify="right")
        lb_t.add_column("Blk",     style="green",       justify="right")
        lb_t.add_column("FG%",     style="dim",         justify="right")
        lb_t.add_column("3P%",     style="dim",         justify="right")
        lb_t.add_column("TS%",     style="cyan",        justify="right")
        lb_t.add_column("USG%",    style="cyan",        justify="right")
        for _, row in lb.iterrows():
            lb_t.add_row(
                row["player_name"], str(int(row["games"])), f"{row['min']:.0f}",
                f"{row['pts']:.1f}", f"{row['reb']:.1f}", f"{row['ast']:.1f}",
                f"{row.get('stl', 0):.1f}", f"{row.get('blk', 0):.1f}",
                f"{row.get('fg_pct', 0):.3f}", f"{row.get('fg3_pct', 0):.3f}",
                f"{row.get('ts_pct', 0):.3f}", f"{row.get('usg_pct', 0) * 100:.1f}%",
            )
        console.print(lb_t)

    # Hot / cold
    hc = hot_cold_summary(player_logs, windows=[5, 10], min_games=10)
    if not hc.empty:
        hc_t = Table(title="Hot / Cold Tracker  (pts delta vs. season avg)", box=box.SIMPLE)
        hc_t.add_column("Player",   style="cyan",  min_width=20)
        hc_t.add_column("Ssn Pts",  style="white", justify="right")
        hc_t.add_column("L5 Pts",   style="white", justify="right")
        hc_t.add_column("L10 Pts",  style="white", justify="right")
        hc_t.add_column("Delta",    style="bold",  justify="right")
        hc_t.add_column("",         style="bold")

        for _, row in hc.iterrows():
            delta = row["delta"]
            d_col = "green" if delta >= 3.0 else ("red" if delta <= -3.0 else "white")
            d_str = f"[{d_col}]{delta:+.1f}[/{d_col}]"
            label = (
                "[bold green]HOT[/bold green]"  if row["label"] == "HOT"  else
                "[bold red]COLD[/bold red]"     if row["label"] == "COLD" else ""
            )
            hc_t.add_row(
                row["player_name"],
                f"{row['season_pts']:.1f}",
                f"{row['last_5_pts']:.1f}",
                f"{row['last_10_pts']:.1f}",
                d_str, label,
            )
        console.print(hc_t)

    # Starter / bench split
    splits = lineup_analysis(player_logs)
    if not splits.empty:
        sp_t = Table(title="Starter / Bench Split", box=box.SIMPLE)
        sp_t.add_column("Role",    style="cyan")
        sp_t.add_column("Players", style="dim",  justify="right")
        sp_t.add_column("Pts",     style="white",justify="right")
        sp_t.add_column("Reb",     style="white",justify="right")
        sp_t.add_column("Ast",     style="white",justify="right")
        sp_t.add_column("TS%",     style="cyan", justify="right")
        sp_t.add_column("USG%",    style="cyan", justify="right")
        for _, row in splits.iterrows():
            sp_t.add_row(
                row["role"], str(int(row["players"])),
                f"{row['pts']:.1f}", f"{row['reb']:.1f}", f"{row['ast']:.1f}",
                f"{row['ts_pct']:.3f}", f"{row['usg_pct'] * 100:.1f}%",
            )
        console.print(sp_t)
