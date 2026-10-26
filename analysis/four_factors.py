"""
Dean Oliver Four Factors Analytical Engine.

Computes the four foundational pillars of basketball efficiency:
  1. Shooting: Effective Field Goal % (eFG%)
  2. Ball Security: Turnover % (TOV%)
  3. Rebounding: Offensive Rebound % (OREB%)
  4. Free Throws: Free Throw Rate (FTR)

Provides game-by-game tracking, home/away splits, rolling 10-game trends,
and benchmark grades against NBA league standards.
"""

from __future__ import annotations

import pandas as pd
import numpy as np

# NBA league median baselines
LEAGUE_EFG_BENCHMARK = 0.545
LEAGUE_TOV_BENCHMARK = 0.130
LEAGUE_OREB_BENCHMARK = 0.245
LEAGUE_FTR_BENCHMARK = 0.245


def game_four_factors(player_logs: pd.DataFrame) -> pd.DataFrame:
    """
    Compute team-level Four Factors for every game in player_logs.
    Returns DataFrame indexed by game_id with date and four factor metrics.
    """
    if player_logs.empty:
        return pd.DataFrame()

    has_oreb = "oreb" in player_logs.columns
    agg_dict = {
        "game_date": ("game_date", "first"),
        "fgm": ("fgm", "sum"),
        "fga": ("fga", "sum"),
        "fg3m": ("fg3m", "sum"),
        "fg3a": ("fg3a", "sum"),
        "ftm": ("ftm", "sum"),
        "fta": ("fta", "sum"),
        "reb": ("reb", "sum"),
        "ast": ("ast", "sum"),
        "tov": ("tov", "sum"),
        "pts": ("pts", "sum"),
    }
    if has_oreb:
        agg_dict["oreb"] = ("oreb", "sum")

    agg = player_logs.groupby("game_id").agg(**agg_dict).reset_index()
    if not has_oreb:
        agg["oreb"] = (agg["reb"] * 0.23).round()

    agg = agg.sort_values("game_date").reset_index(drop=True)

    # 1. Effective Field Goal %: (FGM + 0.5 * 3PM) / FGA
    agg["efg_pct"] = np.where(agg["fga"] > 0, (agg["fgm"] + 0.5 * agg["fg3m"]) / agg["fga"], 0.0)

    # True Shooting %: PTS / (2 * (FGA + 0.44 * FTA))
    ts_denom = 2 * (agg["fga"] + 0.44 * agg["fta"])
    agg["ts_pct"] = np.where(ts_denom > 0, agg["pts"] / ts_denom, 0.0)

    # 2. Turnover %: TOV / (FGA + 0.44 * FTA + TOV)
    poss_denom = agg["fga"] + 0.44 * agg["fta"] + agg["tov"]
    agg["tov_pct"] = np.where(poss_denom > 0, agg["tov"] / poss_denom, 0.0)

    # 3. Offensive Rebounding Rate (Estimated against league baseline opp dreb ~ 32.5)
    agg["oreb_pct"] = np.where((agg["oreb"] + 32.5) > 0, agg["oreb"] / (agg["oreb"] + 32.5), 0.0)

    # 4. Free Throw Rate: FTA / FGA
    agg["ftr"] = np.where(agg["fga"] > 0, agg["fta"] / agg["fga"], 0.0)

    agg["ast_tov_ratio"] = np.where(agg["tov"] > 0, agg["ast"] / agg["tov"], agg["ast"])

    return agg


def team_four_factors_summary(player_logs: pd.DataFrame, games: pd.DataFrame | None = None) -> dict:
    """
    Calculate season-level Four Factors aggregate, splits, and trends.
    """
    g_ff = game_four_factors(player_logs)
    if g_ff.empty:
        return {}

    total_fgm = float(g_ff["fgm"].sum())
    total_fga = float(g_ff["fga"].sum())
    total_fg3m = float(g_ff["fg3m"].sum())
    total_fta = float(g_ff["fta"].sum())
    total_tov = float(g_ff["tov"].sum())
    total_oreb = float(g_ff["oreb"].sum())
    total_pts = float(g_ff["pts"].sum())

    season_efg = (total_fgm + 0.5 * total_fg3m) / total_fga if total_fga > 0 else 0.0
    season_ts = total_pts / (2 * (total_fga + 0.44 * total_fta)) if (total_fga + 0.44 * total_fta) > 0 else 0.0
    poss_est = total_fga + 0.44 * total_fta + total_tov
    season_tov_pct = total_tov / poss_est if poss_est > 0 else 0.0
    season_ftr = total_fta / total_fga if total_fga > 0 else 0.0
    season_oreb_pct = float(g_ff["oreb_pct"].mean())

    # Rolling last 10 games trend
    l10 = g_ff.tail(10)
    l10_efg = float(l10["efg_pct"].mean()) if not l10.empty else season_efg
    l10_tov = float(l10["tov_pct"].mean()) if not l10.empty else season_tov_pct
    l10_ftr = float(l10["ftr"].mean()) if not l10.empty else season_ftr
    l10_oreb = float(l10["oreb_pct"].mean()) if not l10.empty else season_oreb_pct

    # Home / Road splits if games table is passed
    home_efg = season_efg
    road_efg = season_efg
    if games is not None and not games.empty and "home_away" in games.columns:
        merged = g_ff.merge(games[["game_id", "home_away"]], on="game_id", how="inner")
        home_g = merged[merged["home_away"] == "H"]
        road_g = merged[merged["home_away"] == "A"]
        if not home_g.empty:
            home_efg = float(home_g["efg_pct"].mean())
        if not road_g.empty:
            road_efg = float(road_g["efg_pct"].mean())

    return {
        "games_analyzed": len(g_ff),
        "efg_pct": round(season_efg, 3),
        "ts_pct": round(season_ts, 3),
        "tov_pct": round(season_tov_pct, 3),
        "oreb_pct": round(season_oreb_pct, 3),
        "ftr": round(season_ftr, 3),
        "efg_delta_vs_league": round((season_efg - LEAGUE_EFG_BENCHMARK) * 100, 1),
        "tov_delta_vs_league": round((season_tov_pct - LEAGUE_TOV_BENCHMARK) * 100, 1),
        "oreb_delta_vs_league": round((season_oreb_pct - LEAGUE_OREB_BENCHMARK) * 100, 1),
        "ftr_delta_vs_league": round((season_ftr - LEAGUE_FTR_BENCHMARK) * 100, 1),
        "l10_efg_pct": round(l10_efg, 3),
        "l10_tov_pct": round(l10_tov, 3),
        "l10_oreb_pct": round(l10_oreb, 3),
        "l10_ftr": round(l10_ftr, 3),
        "home_efg_pct": round(home_efg, 3),
        "road_efg_pct": round(road_efg, 3),
    }


def four_factors_diagnostic_table(player_logs: pd.DataFrame, games: pd.DataFrame | None = None) -> pd.DataFrame:
    """
    Format a clean comparison table: Factor, Spurs Value, League Benchmark, Edge, Grade.
    """
    summary = team_four_factors_summary(player_logs, games)
    if not summary:
        return pd.DataFrame()

    def _grade(factor: str, delta: float) -> str:
        # For turnover rate, negative delta (fewer turnovers) is better!
        effective_delta = -delta if factor == "Turnover %" else delta
        if effective_delta >= 2.5:
            return "A+"
        elif effective_delta >= 1.0:
            return "A"
        elif effective_delta >= -1.0:
            return "B"
        elif effective_delta >= -2.5:
            return "C"
        else:
            return "D"

    rows = [
        {
            "factor": "Effective FG% (eFG%)",
            "weight": "40%",
            "spurs_stat": f"{summary['efg_pct']*100:.1f}%",
            "league_avg": f"{LEAGUE_EFG_BENCHMARK*100:.1f}%",
            "delta": f"{summary['efg_delta_vs_league']:+.1f}%",
            "grade": _grade("eFG%", summary['efg_delta_vs_league']),
        },
        {
            "factor": "Turnover % (TOV%)",
            "weight": "25%",
            "spurs_stat": f"{summary['tov_pct']*100:.1f}%",
            "league_avg": f"{LEAGUE_TOV_BENCHMARK*100:.1f}%",
            "delta": f"{summary['tov_delta_vs_league']:+.1f}%",
            "grade": _grade("Turnover %", summary['tov_delta_vs_league']),
        },
        {
            "factor": "Offensive Rebound % (OREB%)",
            "weight": "20%",
            "spurs_stat": f"{summary['oreb_pct']*100:.1f}%",
            "league_avg": f"{LEAGUE_OREB_BENCHMARK*100:.1f}%",
            "delta": f"{summary['oreb_delta_vs_league']:+.1f}%",
            "grade": _grade("OREB%", summary['oreb_delta_vs_league']),
        },
        {
            "factor": "Free Throw Rate (FTR)",
            "weight": "15%",
            "spurs_stat": f"{summary['ftr']:.3f}",
            "league_avg": f"{LEAGUE_FTR_BENCHMARK:.3f}",
            "delta": f"{summary['ftr_delta_vs_league']:+.1f}%",
            "grade": _grade("FTR", summary['ftr_delta_vs_league']),
        },
    ]

    return pd.DataFrame(rows)


def print_four_factors(console, player_logs: pd.DataFrame, games: pd.DataFrame | None = None) -> None:
    """Print rich Four Factors diagnostic panel to terminal."""
    from rich.panel import Panel
    from rich.table import Table
    from rich import box

    summary = team_four_factors_summary(player_logs, games)
    if not summary:
        console.print("[yellow]No Four Factors data available.[/yellow]")
        return

    diag = four_factors_diagnostic_table(player_logs, games)

    table = Table(title="Dean Oliver Four Factors Analysis", box=box.ROUNDED)
    table.add_column("Factor", style="white", no_wrap=True)
    table.add_column("Weight", justify="center", style="dim")
    table.add_column("Spurs", justify="right", style="cyan")
    table.add_column("League Avg", justify="right", style="dim")
    table.add_column("Delta vs. Avg", justify="right", style="yellow")
    table.add_column("Grade", justify="center", style="bold")

    for _, r in diag.iterrows():
        grade_color = "green" if "A" in r["grade"] else ("yellow" if "B" in r["grade"] else "red")
        table.add_row(
            r["factor"],
            r["weight"],
            r["spurs_stat"],
            r["league_avg"],
            r["delta"],
            f"[{grade_color}]{r['grade']}[/{grade_color}]",
        )

    console.print(table)

