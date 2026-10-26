"""
Dedicated Clutch Playbook Engine.

Analyzes late-game crunch-time performance and tight contest execution:
  - Games decided by 5 points or less (and 1-possession games <= 3 pts)
  - Clutch scoring leaders & crunch-time shot selection
  - Clutch free throw shooting under pressure
  - Clutch Composure Index (0-100 scale measuring crunch-time composure)
"""

from __future__ import annotations

import pandas as pd
import numpy as np


def clutch_game_summary(games: pd.DataFrame) -> dict:
    """
    Season-level summary of performance in games decided by 5 points or less.
    """
    f = games[games["status"] == "Final"].copy()
    if f.empty or "margin" not in f.columns:
        return {}

    total_games = len(f)
    clutch = f[f["margin"].abs() <= 5]
    one_possession = f[f["margin"].abs() <= 3]

    clutch_n = len(clutch)
    clutch_w = int((clutch["result"] == "W").sum())
    clutch_l = clutch_n - clutch_w
    clutch_pct = round(clutch_w / clutch_n * 100, 1) if clutch_n > 0 else 0.0

    one_pos_n = len(one_possession)
    one_pos_w = int((one_possession["result"] == "W").sum())
    one_pos_l = one_pos_n - one_pos_w

    avg_clutch_margin = float(clutch["margin"].mean()) if clutch_n > 0 else 0.0

    # Composure Index (0-100):
    # Combines clutch win rate (60%), average margin (+/- 5 mapped to 0-25),
    # and 1-possession execution (15%)
    base_score = clutch_pct * 0.60
    margin_bonus = max(0.0, min(25.0, (avg_clutch_margin + 5.0) * 2.5))
    one_pos_score = (one_pos_w / one_pos_n * 15.0) if one_pos_n > 0 else 7.5
    composure_index = round(min(100.0, base_score + margin_bonus + one_pos_score), 0)

    if composure_index >= 70:
        composure_grade = "Ice Cold (Elite Closing Execution)"
    elif composure_index >= 50:
        composure_grade = "Poised (Solid Late-Game Execution)"
    elif composure_index >= 35:
        composure_grade = "Developing (Young Core Learning to Finish)"
    else:
        composure_grade = "Shaky (High Turnover & Missed FT Rate in Crunch Time)"

    return {
        "total_games": total_games,
        "clutch_games_played": clutch_n,
        "clutch_record": f"{clutch_w}-{clutch_l}",
        "clutch_win_pct": clutch_pct,
        "clutch_frequency_pct": round(clutch_n / total_games * 100, 1) if total_games > 0 else 0.0,
        "one_possession_record": f"{one_pos_w}-{one_pos_l}",
        "avg_clutch_margin": round(avg_clutch_margin, 2),
        "composure_index": composure_index,
        "composure_grade": composure_grade,
    }


def clutch_player_leaders(games: pd.DataFrame, player_logs: pd.DataFrame, min_clutch_games: int = 3) -> pd.DataFrame:
    """
    Player performance specifically inside clutch games (games decided by <= 5 pts).
    """
    f = games[games["status"] == "Final"].copy()
    if f.empty or player_logs.empty:
        return pd.DataFrame()

    clutch_game_ids = set(f[f["margin"].abs() <= 5]["game_id"])
    if not clutch_game_ids:
        return pd.DataFrame()

    clutch_logs = player_logs[player_logs["game_id"].isin(clutch_game_ids)].copy()

    agg = clutch_logs.groupby(["player_id", "player_name"]).agg(
        clutch_games=("game_id", "count"),
        clutch_pts_pg=("pts", "mean"),
        clutch_reb_pg=("reb", "mean"),
        clutch_ast_pg=("ast", "mean"),
        clutch_plus_minus_pg=("plus_minus", "mean"),
        clutch_ts_pct=("ts_pct", "mean"),
        clutch_ftm=("ftm", "sum"),
        clutch_fta=("fta", "sum"),
    ).reset_index()

    agg = agg[agg["clutch_games"] >= min_clutch_games].copy()
    if agg.empty:
        agg = clutch_logs.groupby(["player_id", "player_name"]).agg(
            clutch_games=("game_id", "count"),
            clutch_pts_pg=("pts", "mean"),
            clutch_reb_pg=("reb", "mean"),
            clutch_ast_pg=("ast", "mean"),
            clutch_plus_minus_pg=("plus_minus", "mean"),
            clutch_ts_pct=("ts_pct", "mean"),
            clutch_ftm=("ftm", "sum"),
            clutch_fta=("fta", "sum"),
        ).reset_index()

    agg["clutch_ft_pct"] = np.where(agg["clutch_fta"] > 0, agg["clutch_ftm"] / agg["clutch_fta"], 0.0)

    for col in ("clutch_pts_pg", "clutch_reb_pg", "clutch_ast_pg", "clutch_plus_minus_pg"):
        agg[col] = agg[col].round(1)
    for col in ("clutch_ts_pct", "clutch_ft_pct"):
        agg[col] = agg[col].round(3)

    return agg.sort_values("clutch_pts_pg", ascending=False).reset_index(drop=True)


def print_clutch_report(console, games: pd.DataFrame, player_logs: pd.DataFrame) -> None:
    """Print rich clutch performance breakdown to terminal."""
    from rich.panel import Panel
    from rich.table import Table
    from rich import box

    summary = clutch_game_summary(games)
    if not summary:
        console.print("[yellow]No clutch game data available.[/yellow]")
        return

    text = (
        f"[bold white]Record in <= 5 Pt Games:[/bold white] [cyan]{summary['clutch_record']}[/cyan] ({summary['clutch_win_pct']}%)\n"
        f"[bold white]1-Possession Games (<= 3 Pts):[/bold white] [cyan]{summary['one_possession_record']}[/cyan]\n"
        f"[bold white]Clutch Game Frequency:[/bold white] {summary['clutch_frequency_pct']}% of all games\n"
        f"[bold white]Average Clutch Margin:[/bold white] {summary['avg_clutch_margin']:+.2f} PPG\n"
        f"[bold white]Composure Index:[/bold white] [yellow]{summary['composure_index']:.0f}/100[/yellow] — {summary['composure_grade']}"
    )
    console.print(Panel(text, title="⏱️ Spurs Crunch-Time & Clutch Execution", border_style="cyan"))

    leaders = clutch_player_leaders(games, player_logs, min_clutch_games=2)
    if not leaders.empty:
        table = Table(title="Clutch Scoring Leaders (<= 5 Pt Contests)", box=box.ROUNDED)
        table.add_column("Player", style="white", no_wrap=True)
        table.add_column("Clutch G", justify="center", style="dim")
        table.add_column("PTS/G", justify="right", style="cyan")
        table.add_column("REB/G", justify="right", style="dim")
        table.add_column("AST/G", justify="right", style="dim")
        table.add_column("+/- / G", justify="right", style="yellow")
        table.add_column("FT%", justify="right", style="white")

        for _, r in leaders.head(6).iterrows():
            pm_val = float(r["clutch_plus_minus_pg"])
            pm_color = "green" if pm_val > 0 else "red"
            table.add_row(
                r["player_name"],
                str(r["clutch_games"]),
                f"{r['clutch_pts_pg']:.1f}",
                f"{r['clutch_reb_pg']:.1f}",
                f"{r['clutch_ast_pg']:.1f}",
                f"[{pm_color}]{pm_val:+.1f}[/{pm_color}]",
                f"{r['clutch_ft_pct']*100:.1f}%",
            )
        console.print(table)

