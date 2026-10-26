"""
Rodeo Road Trip (RRT) Split Tracker — Analytics Engine.

Every February, the San Antonio Stock Show & Rodeo displaces the Spurs from
Frost Bank Center for an iconic multi-week road trip (historically 6 to 9 consecutive
away games). This split is a legendary crucible in Spurs franchise lore.

Features:
  - Automatic game segmentation: Pre-RRT, Active RRT (February), and Post-RRT
  - Performance degradation vs. road trip momentum metrics
  - Historical benchmark comparisons against Spurs championship teams (2003–present)
  - Terminal presentation via rich
"""

from __future__ import annotations

import pandas as pd
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

# Historical Rodeo Road Trip benchmarks for San Antonio Spurs
HISTORICAL_RODEO_BENCHMARKS = [
    {"season": "2002-03", "record": "8-1", "win_pct": 0.889, "result": "🏆 NBA Champions (Tim Duncan MVP)"},
    {"season": "2004-05", "record": "6-1", "win_pct": 0.857, "result": "🏆 NBA Champions (Manu Ginobili breakout)"},
    {"season": "2006-07", "record": "4-4", "win_pct": 0.500, "result": "🏆 NBA Champions (Ignited 13-game W streak)"},
    {"season": "2011-12", "record": "8-1", "win_pct": 0.889, "result": "Western Conference Finals"},
    {"season": "2013-14", "record": "6-3", "win_pct": 0.667, "result": "🏆 NBA Champions ('Beautiful Game')"},
    {"season": "2015-16", "record": "7-1", "win_pct": 0.875, "result": "Franchise-record 67-15 regular season"},
    {"season": "2023-24", "record": "1-8", "win_pct": 0.111, "result": "Victor Wembanyama rookie gauntlet"},
]


# ---------------------------------------------------------------------------
# Split segmentation
# ---------------------------------------------------------------------------

def segment_rodeo_games(games: pd.DataFrame) -> pd.DataFrame:
    """
    Classify each game into 'Pre-RRT', 'Active RRT', or 'Post-RRT'.

    The Rodeo Road Trip is defined as February away games (or the extended
    consecutive road stretch surrounding February).
    """
    if games.empty:
        return pd.DataFrame()

    df = games.sort_values("game_date").reset_index(drop=True).copy()
    df["game_date_dt"] = pd.to_datetime(df["game_date"])

    # Determine February road window
    feb_away = df[(df["game_date_dt"].dt.month == 2) & (df["home_away"] == "A")]

    if not feb_away.empty:
        start_date = feb_away["game_date_dt"].min()
        end_date = feb_away["game_date_dt"].max()

        def _assign_split(dt, ha):
            if dt < start_date:
                return "Pre-RRT"
            elif dt <= end_date and ha == "A":
                return "Active RRT"
            elif dt > end_date:
                return "Post-RRT"
            else:
                # Home games in February before/after the road trip
                return "Pre-RRT" if dt < (start_date + (end_date - start_date)/2) else "Post-RRT"

        df["rodeo_split"] = [
            _assign_split(row["game_date_dt"], row["home_away"])
            for _, row in df.iterrows()
        ]
    else:
        # Fallback if no February road games yet: tag by month
        def _fallback_split(dt):
            if dt.month in (10, 11, 12, 1):
                return "Pre-RRT"
            elif dt.month == 2:
                return "Active RRT"
            else:
                return "Post-RRT"
        df["rodeo_split"] = df["game_date_dt"].apply(_fallback_split)

    return df


# ---------------------------------------------------------------------------
# Split Statistics & Aggregation
# ---------------------------------------------------------------------------

def rodeo_split_metrics(segmented_games: pd.DataFrame) -> dict[str, dict]:
    """
    Calculate performance summaries across Pre-RRT, Active RRT, and Post-RRT.
    """
    if segmented_games.empty:
        return {}

    final_games = segmented_games[segmented_games["status"] == "Final"].copy()
    splits = ["Pre-RRT", "Active RRT", "Post-RRT"]
    results = {}

    for split in splits:
        sdf = final_games[final_games["rodeo_split"] == split]
        g = len(sdf)
        if g == 0:
            results[split] = {
                "games": 0, "record": "0-0", "win_pct": 0.0,
                "ppg": 0.0, "opp_ppg": 0.0, "avg_margin": 0.0,
                "ortg": 0.0, "drtg": 0.0, "net_rtg": 0.0, "pace": 0.0,
            }
            continue

        w = int((sdf["result"] == "W").sum())
        l = int((sdf["result"] == "L").sum())
        win_pct = round(w / g, 3) if g > 0 else 0.0

        ppg = round(float(sdf["pts"].mean()), 1)
        opp_ppg = round(float(sdf["opp_pts"].mean()), 1)
        margin = round(float(sdf["margin"].mean()), 2)

        ortg = round(float(sdf["ortg"].mean()), 1) if "ortg" in sdf.columns else 0.0
        drtg = round(float(sdf["drtg"].mean()), 1) if "drtg" in sdf.columns else 0.0
        net_rtg = round(ortg - drtg, 1) if (ortg and drtg) else round(float(sdf["nrtg"].mean()), 1) if "nrtg" in sdf.columns else 0.0
        pace = round(float(sdf["pace"].mean()), 1) if "pace" in sdf.columns else 0.0

        results[split] = {
            "games": g,
            "record": f"{w}-{l}",
            "wins": w,
            "losses": l,
            "win_pct": win_pct,
            "ppg": ppg,
            "opp_ppg": opp_ppg,
            "avg_margin": margin,
            "ortg": ortg,
            "drtg": drtg,
            "net_rtg": net_rtg,
            "pace": pace,
        }

    return results


def historical_rodeo_comparison(current_rrt_metrics: dict) -> pd.DataFrame:
    """
    Combine historical Spurs rodeo trips with the current season split.
    """
    rows = list(HISTORICAL_RODEO_BENCHMARKS)
    if current_rrt_metrics and current_rrt_metrics.get("games", 0) > 0:
        rows.append({
            "season": "Current Season",
            "record": current_rrt_metrics["record"],
            "win_pct": current_rrt_metrics["win_pct"],
            "result": f"Margin: {current_rrt_metrics['avg_margin']:+.1f} | Net: {current_rrt_metrics['net_rtg']:+.1f}",
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Rich Terminal Reporting
# ---------------------------------------------------------------------------

def print_rodeo_report(console: Console, games: pd.DataFrame) -> None:
    """Print the Rodeo Road Trip intelligence report to the terminal."""
    if games.empty:
        console.print("[yellow]No games available for Rodeo Road Trip analysis.[/yellow]")
        return

    segmented = segment_rodeo_games(games)
    splits = rodeo_split_metrics(segmented)

    console.rule("[bold cyan]🤠 San Antonio Spurs — Rodeo Road Trip Split Tracker[/bold cyan]")

    t_splits = Table(title="Regular Season Gauntlet Splits", box=box.SIMPLE)
    t_splits.add_column("Split Phase", style="cyan")
    t_splits.add_column("Games", justify="right")
    t_splits.add_column("Record", justify="center", style="white")
    t_splits.add_column("Win%", justify="right")
    t_splits.add_column("PPG", justify="right")
    t_splits.add_column("Opp PPG", justify="right")
    t_splits.add_column("Margin", justify="right")
    t_splits.add_column("Net Rating", justify="right")

    for name in ("Pre-RRT", "Active RRT", "Post-RRT"):
        m = splits.get(name, {})
        if m.get("games", 0) == 0:
            t_splits.add_row(name, "0", "--", "--", "--", "--", "--", "--")
            continue

        margin_style = "green" if m["avg_margin"] > 0 else "red"
        net_style = "green" if m["net_rtg"] > 0 else "red"
        t_splits.add_row(
            name,
            str(m["games"]),
            m["record"],
            f"{m['win_pct']:.3f}",
            f"{m['ppg']:.1f}",
            f"{m['opp_ppg']:.1f}",
            f"[{margin_style}]{m['avg_margin']:+.1f}[/{margin_style}]",
            f"[{net_style}]{m['net_rtg']:+.1f}[/{net_style}]",
        )
    console.print(t_splits)

    # Historical context table
    t_hist = Table(title="Historical Spurs Rodeo Benchmarks (Championship Standard)", box=box.SIMPLE)
    t_hist.add_column("Season", style="white")
    t_hist.add_column("RRT Record", style="cyan", justify="center")
    t_hist.add_column("Win%", justify="right")
    t_hist.add_column("Franchise Context / Outcome", style="dim")

    for h in HISTORICAL_RODEO_BENCHMARKS:
        t_hist.add_row(h["season"], h["record"], f"{h['win_pct']:.3f}", h["result"])

    console.print(t_hist)

    # Narrative callout
    p_text = (
        "[bold]The Rodeo Road Trip Heritage:[/bold]\n"
        "Instituted in 2003 when the San Antonio Stock Show & Rodeo took over the AT&T / Frost Bank Center,\n"
        "the RRT forged all five Spurs championship teams. Gregg Popovich traditionally used the trip to\n"
        "tighten defensive rotations and solidify championship chemistry for the spring playoff push."
    )
    console.print(Panel(p_text, title="Crucible of Champions", border_style="cyan"))
