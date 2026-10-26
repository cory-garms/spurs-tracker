"""
The 'Beautiful Game' Ball Movement Engine — Analytics Engine.

Inspired by the iconic 2014 San Antonio Spurs championship offense, known worldwide
as the zenith of selfless passing, extra passes, and motion basketball.

Features:
  - Assist-to-Field-Goal ratio (Target: >65% assisted baskets)
  - Team & player Assist-to-Turnover ratios
  - Estimated Assist Points Created (APC)
  - The "Beautiful Game Index" (0–100 score calibrated to 2014 Spurs Finals baseline)
  - Terminal presentation via rich
"""

from __future__ import annotations

import pandas as pd
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

# 2014 Spurs Championship baseline constants
BG_2014_AST_PCT   = 0.653  # 65.3% of field goals assisted
BG_2014_AST_TOV   = 1.71   # Regular season AST/TOV (approached 2.1 in 2014 Finals)
BG_2014_AST_PG    = 25.2   # Assists per game in 2014


def team_ball_movement_summary(
    games: pd.DataFrame,
    player_logs: pd.DataFrame,
) -> dict:
    """
    Compute comprehensive ball movement and assist metrics for the team.
    """
    if games.empty and player_logs.empty:
        return {}

    final_games = games[games["status"] == "Final"]
    g = len(final_games)
    if g == 0 and not player_logs.empty:
        g = player_logs["game_id"].nunique()

    # Aggregate from player_logs or games
    if not player_logs.empty:
        total_ast = int(player_logs["ast"].sum())
        total_tov = int(player_logs["tov"].sum())
        total_fgm = int(player_logs["fgm"].sum())
        total_fg3m = int(player_logs["fg3m"].sum())
        total_pts = int(player_logs["pts"].sum())
    else:
        total_ast = int(final_games["ast"].sum()) if "ast" in final_games.columns else 0
        total_tov = int(final_games["tov"].sum()) if "tov" in final_games.columns else 1
        total_fgm = int(final_games["fgm"].sum()) if "fgm" in final_games.columns else 1
        total_fg3m = int(final_games["fg3m"].sum()) if "fg3m" in final_games.columns else 0
        total_pts = int(final_games["pts"].sum())

    ast_pg = round(total_ast / g, 1) if g > 0 else 0.0
    tov_pg = round(total_tov / g, 1) if g > 0 else 0.0
    ast_tov_ratio = round(total_ast / total_tov, 2) if total_tov > 0 else 0.0

    # Assisted Field Goal Percentage (AST%)
    ast_pct = round(total_ast / total_fgm, 3) if total_fgm > 0 else 0.0

    # Estimated Assist Points Created (APC)
    # Conservatively estimate 80% of 3PM are assisted and 55% of 2PM are assisted
    est_ast_3pm = total_fg3m * 0.82
    est_ast_2pm = max(0, total_ast - est_ast_3pm)
    apc_total = round(est_ast_2pm * 2.0 + est_ast_3pm * 3.0)
    apc_pg = round(apc_total / g, 1) if g > 0 else 0.0
    apc_share = round((apc_total / total_pts) * 100, 1) if total_pts > 0 else 0.0

    # Beautiful Game Index (0 to 100 scale)
    # Calibrated: 100 = 2014 Spurs Finals perfection
    ast_pct_score = min(40.0, (ast_pct / BG_2014_AST_PCT) * 40.0)
    ast_tov_score = min(35.0, (ast_tov_ratio / BG_2014_AST_TOV) * 35.0)
    vol_score = min(25.0, (ast_pg / BG_2014_AST_PG) * 25.0)
    bgi = round(ast_pct_score + ast_tov_score + vol_score, 1)

    return {
        "games": g,
        "assists_per_game": ast_pg,
        "turnovers_per_game": tov_pg,
        "ast_tov_ratio": ast_tov_ratio,
        "assisted_fg_pct": ast_pct,
        "assist_points_created_total": apc_total,
        "assist_points_created_pg": apc_pg,
        "apc_scoring_share_pct": apc_share,
        "beautiful_game_index": bgi,
    }


def player_pass_contributors(
    player_logs: pd.DataFrame,
    min_games: int = 10,
) -> pd.DataFrame:
    """
    Ranks individual ball movers and pass creators by AST, AST/TOV, and per-36 numbers.
    """
    if player_logs.empty:
        return pd.DataFrame()

    agg = player_logs.groupby("player_id").agg(
        player_name=("player_name", "first"),
        games=("game_id", "count"),
        total_min=("min", "sum"),
        total_ast=("ast", "sum"),
        total_tov=("tov", "sum"),
        total_pts=("pts", "sum"),
    ).reset_index()

    agg = agg[agg["games"] >= min_games].copy()
    agg["ast_pg"] = (agg["total_ast"] / agg["games"]).round(1)
    agg["tov_pg"] = (agg["total_tov"] / agg["games"]).round(1)
    agg["ast_tov"] = (agg["total_ast"] / agg["total_tov"].replace(0, 1)).round(2)
    agg["ast_per_36"] = ((agg["total_ast"] / agg["total_min"].replace(0, 1)) * 36.0).round(1)

    return agg.sort_values("ast_pg", ascending=False).reset_index(drop=True)


def print_ball_movement(
    console: Console,
    player_logs: pd.DataFrame,
    games: pd.DataFrame,
) -> None:
    """Print the Beautiful Game ball movement report to the terminal."""
    team_metrics = team_ball_movement_summary(games, player_logs)
    if not team_metrics:
        console.print("[yellow]No data available for ball movement analysis.[/yellow]")
        return

    console.rule("[bold cyan]🏀 The 'Beautiful Game' Ball Movement Index[/bold cyan]")

    bgi = team_metrics["beautiful_game_index"]
    color = "green" if bgi >= 80 else ("yellow" if bgi >= 65 else "red")

    summary_text = (
        f"[bold]Beautiful Game Index (BGI):[/bold] [{color}]{bgi} / 100[/{color}]\n"
        f"  • Team Assists: [cyan]{team_metrics['assists_per_game']} APG[/cyan] (Turnovers: {team_metrics['turnovers_per_game']} TPG)\n"
        f"  • AST / TOV Ratio: [cyan]{team_metrics['ast_tov_ratio']}[/cyan] (2014 Championship benchmark: 1.71)\n"
        f"  • Assisted Basket Rate: [cyan]{team_metrics['assisted_fg_pct'] * 100:.1f}%[/cyan] (2014 benchmark: 65.3%)\n"
        f"  • Assist Points Created (APC): [cyan]{team_metrics['assist_points_created_pg']} PPG[/cyan] "
        f"({team_metrics['apc_scoring_share_pct']}% of total team points)"
    )
    console.print(Panel(summary_text, title="Team Flow & Passing Velocity", border_style="cyan"))

    if not player_logs.empty:
        passers = player_pass_contributors(player_logs, min_games=10)
        t_passers = Table(title="Top Playmakers & Passing Hubs", box=box.SIMPLE)
        t_passers.add_column("Player", style="white")
        t_passers.add_column("Games", justify="right")
        t_passers.add_column("AST/G", justify="right", style="cyan")
        t_passers.add_column("TOV/G", justify="right")
        t_passers.add_column("AST / TOV", justify="right", style="green")
        t_passers.add_column("AST / 36m", justify="right")

        for _, r in passers.head(10).iterrows():
            t_passers.add_row(
                str(r["player_name"]),
                str(r["games"]),
                f"{r['ast_pg']:.1f}",
                f"{r['tov_pg']:.1f}",
                f"{r['ast_tov']:.2f}",
                f"{r['ast_per_36']:.1f}",
            )
        console.print(t_passers)
