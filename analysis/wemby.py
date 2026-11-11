"""
Victor Wembanyama Defensive & Gravity Lab — Analytics Engine.

Features:
  - Game-by-game stocks tracking (Steals + Blocks) & per-36 projections
  - Rim deterrence proxy & defensive rating differentials
  - 5x5 watch and rare milestone counts (3+ blk, 5+ blk, 8+ stocks)
  - True Shooting %, eFG%, shot volume & 3P gravity metrics
  - Terminal reporting via rich
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

WEMBY_ID = 1641705
WEMBY_NAME = "Victor Wembanyama"


# ---------------------------------------------------------------------------
# Data extraction & enrichment
# ---------------------------------------------------------------------------

def get_wemby_logs(player_logs: pd.DataFrame) -> pd.DataFrame:
    """
    Extract and enrich Victor Wembanyama's game logs from the player logs table.
    Sorts chronologically by game_date.
    """
    if player_logs.empty:
        return pd.DataFrame()

    mask = (
        (player_logs["player_id"] == WEMBY_ID) |
        (player_logs["player_name"].str.contains("Wembanyama", case=False, na=False))
    )
    df = player_logs[mask].copy()
    if df.empty:
        return pd.DataFrame()

    df = df.sort_values("game_date").reset_index(drop=True)
    df["game_n"] = range(1, len(df) + 1)
    df["stl"] = df["stl"].fillna(0).astype(int)
    df["blk"] = df["blk"].fillna(0).astype(int)
    df["stocks"] = df["stl"] + df["blk"]

    # Minutes & Per-36 calculations
    min_col = df["min"].fillna(0.0).astype(float)
    df["min_safe"] = min_col.replace(0.0, np.nan)
    df["pts_per_36"] = ((df["pts"] / df["min_safe"]) * 36.0).round(1).fillna(0.0)
    df["reb_per_36"] = ((df["reb"] / df["min_safe"]) * 36.0).round(1).fillna(0.0)
    df["blk_per_36"] = ((df["blk"] / df["min_safe"]) * 36.0).round(1).fillna(0.0)
    df["stocks_per_36"] = ((df["stocks"] / df["min_safe"]) * 36.0).round(1).fillna(0.0)

    # Rolling averages (5 and 10 games)
    df["roll5_blk"] = df["blk"].rolling(5, min_periods=1).mean().round(2)
    df["roll10_blk"] = df["blk"].rolling(10, min_periods=1).mean().round(2)
    df["roll5_stocks"] = df["stocks"].rolling(5, min_periods=1).mean().round(2)
    df["roll10_stocks"] = df["stocks"].rolling(10, min_periods=1).mean().round(2)

    # Cumulative counts
    df["cum_blk"] = df["blk"].cumsum()
    df["cum_stl"] = df["stl"].cumsum()
    df["cum_stocks"] = df["stocks"].cumsum()

    # Shooting metrics
    fga = df["fga"].fillna(0).astype(int)
    fgm = df["fgm"].fillna(0).astype(int)
    fg3m = df["fg3m"].fillna(0).astype(int)
    fg3a = df["fg3a"].fillna(0).astype(int)
    fta = df["fta"].fillna(0).astype(int)
    pts = df["pts"].fillna(0).astype(int)

    # eFG% = (FGM + 0.5 * 3PM) / FGA
    df["efg_pct"] = np.where(fga > 0, ((fgm + 0.5 * fg3m) / fga).round(3), 0.0)

    # True Shooting % = PTS / (2 * (FGA + 0.44 * FTA))
    denom_ts = 2.0 * (fga + 0.44 * fta)
    df["computed_ts_pct"] = np.where(denom_ts > 0, (pts / denom_ts).round(3), 0.0)
    if "ts_pct" not in df.columns or df["ts_pct"].isna().all():
        df["ts_pct"] = df["computed_ts_pct"]

    return df


# ---------------------------------------------------------------------------
# Stocks Engine & Milestones
# ---------------------------------------------------------------------------

def stocks_distribution(wemby_logs: pd.DataFrame) -> dict:
    """
    Empirical distribution of Wemby stocks (Steals + Blocks) and rare milestones.
    """
    if wemby_logs.empty:
        return {}

    g = len(wemby_logs)
    total_blk = int(wemby_logs["blk"].sum())
    total_stl = int(wemby_logs["stl"].sum())
    total_stocks = int(wemby_logs["stocks"].sum())
    total_min = float(wemby_logs["min"].sum())

    b3 = int((wemby_logs["blk"] >= 3).sum())
    b5 = int((wemby_logs["blk"] >= 5).sum())
    b7 = int((wemby_logs["blk"] >= 7).sum())
    b10 = int((wemby_logs["blk"] >= 10).sum())

    st5 = int((wemby_logs["stocks"] >= 5).sum())
    st8 = int((wemby_logs["stocks"] >= 8).sum())

    # 5x5 check: >=5 in PTS, REB, AST, STL, BLK
    five_by_fives = 0
    five_by_fours = 0
    for _, row in wemby_logs.iterrows():
        categories_over_5 = sum([
            int(row.get("pts", 0)) >= 5,
            int(row.get("reb", 0)) >= 5,
            int(row.get("ast", 0)) >= 5,
            int(row.get("stl", 0)) >= 5,
            int(row.get("blk", 0)) >= 5,
        ])
        if categories_over_5 == 5:
            five_by_fives += 1
        elif categories_over_5 == 4:
            five_by_fours += 1

    blk_per_game = round(total_blk / g, 2) if g > 0 else 0.0
    stl_per_game = round(total_stl / g, 2) if g > 0 else 0.0
    stocks_per_game = round(total_stocks / g, 2) if g > 0 else 0.0
    stocks_per_36 = round((total_stocks / total_min) * 36.0, 2) if total_min > 0 else 0.0

    return {
        "games": g,
        "total_blocks": total_blk,
        "total_steals": total_stl,
        "total_stocks": total_stocks,
        "blocks_per_game": blk_per_game,
        "steals_per_game": stl_per_game,
        "stocks_per_game": stocks_per_game,
        "stocks_per_36": stocks_per_36,
        "games_3plus_blk": b3,
        "pct_3plus_blk": round(b3 / g * 100, 1) if g > 0 else 0.0,
        "games_5plus_blk": b5,
        "pct_5plus_blk": round(b5 / g * 100, 1) if g > 0 else 0.0,
        "games_7plus_blk": b7,
        "games_10plus_blk": b10,
        "games_5plus_stocks": st5,
        "games_8plus_stocks": st8,
        "five_by_fives": five_by_fives,
        "five_by_fours": five_by_fours,
    }


# ---------------------------------------------------------------------------
# Defensive Deterrence & Gravity Metrics
# ---------------------------------------------------------------------------

def defensive_impact_summary(
    games: pd.DataFrame,
    wemby_logs: pd.DataFrame,
) -> dict:
    """
    Examines the team's defensive performance relative to Wemby's presence and activity.
    Compares high-deterrence games (5+ stocks) vs baseline games.
    """
    if games.empty or wemby_logs.empty:
        return {}

    merged = pd.merge(
        games[games["status"] == "Final"],
        wemby_logs[["game_id", "min", "blk", "stl", "stocks", "plus_minus"]],
        on="game_id",
        how="inner",
    )
    if merged.empty:
        return {}

    # High stocks split (>= 5 stocks vs < 5 stocks)
    high_stocks = merged[merged["stocks"] >= 5]
    regular_stocks = merged[merged["stocks"] < 5]

    def _mean_stat(df: pd.DataFrame, col: str) -> float:
        if col in df.columns and not df[df[col].notna()].empty:
            return round(float(df[col].mean()), 1)
        return 0.0

    high_drtg = _mean_stat(high_stocks, "drtg")
    regular_drtg = _mean_stat(regular_stocks, "drtg")
    high_opp_pts = _mean_stat(high_stocks, "opp_pts")
    regular_opp_pts = _mean_stat(regular_stocks, "opp_pts")

    high_w = int((high_stocks["result"] == "W").sum())
    high_l = int((high_stocks["result"] == "L").sum())
    reg_w = int((regular_stocks["result"] == "W").sum())
    reg_l = int((regular_stocks["result"] == "L").sum())

    high_win_pct = round(high_w / (high_w + high_l), 3) if (high_w + high_l) > 0 else 0.0
    reg_win_pct = round(reg_w / (reg_w + reg_l), 3) if (reg_w + reg_l) > 0 else 0.0

    return {
        "total_tracked_games": len(merged),
        "high_stocks_games": len(high_stocks),
        "high_stocks_record": f"{high_w}-{high_l} ({high_win_pct:.3f})",
        "high_stocks_drtg": high_drtg,
        "high_stocks_opp_pts": high_opp_pts,
        "regular_stocks_games": len(regular_stocks),
        "regular_stocks_record": f"{reg_w}-{reg_l} ({reg_win_pct:.3f})",
        "regular_stocks_drtg": regular_drtg,
        "regular_stocks_opp_pts": regular_opp_pts,
        "drtg_delta": round(regular_drtg - high_drtg, 1) if (high_drtg and regular_drtg) else 0.0,
        "opp_pts_suppression": round(regular_opp_pts - high_opp_pts, 1),
    }


def offensive_gravity_summary(wemby_logs: pd.DataFrame) -> dict:
    """
    Usage rate, True Shooting %, 3P pull, and volume distribution.
    """
    if wemby_logs.empty:
        return {}

    g = len(wemby_logs)
    total_pts = int(wemby_logs["pts"].sum())
    total_fga = int(wemby_logs["fga"].sum())
    total_fg3a = int(wemby_logs["fg3a"].sum())
    total_fta = int(wemby_logs["fta"].sum())

    # Shooting percentages pool every shot, so a 25-shot night outweighs a 9-shot one
    shooting = pooled_shooting(wemby_logs)
    ts, efg = round(shooting["ts_pct"], 3), round(shooting["efg_pct"], 3)
    usg = round(float(wemby_logs["usg_pct"].mean()), 3) if "usg_pct" in wemby_logs.columns else 0.0

    three_point_rate = round(total_fg3a / total_fga, 3) if total_fga > 0 else 0.0
    ft_rate = round(total_fta / total_fga, 3) if total_fga > 0 else 0.0

    return {
        "ppg": round(total_pts / g, 1) if g > 0 else 0.0,
        "fga_per_game": round(total_fga / g, 1) if g > 0 else 0.0,
        "fg3a_per_game": round(total_fg3a / g, 1) if g > 0 else 0.0,
        "true_shooting_pct": ts,
        "effective_fg_pct": efg,
        "avg_usage_pct": usg,
        "three_point_attempt_rate": three_point_rate,
        "free_throw_rate": ft_rate,
    }


# ---------------------------------------------------------------------------
# Heat Check: recent form, the blowout minutes tax, best stretches
# ---------------------------------------------------------------------------

HEAT_WINDOW = 5          # games in a "stretch"
CLOSE_GAME_MARGIN = 10   # games decided by this many points or fewer count as competitive
MIN_CLOSE_GAMES = 3      # competitive games needed before their minutes set the projection


def pooled_shooting(logs: pd.DataFrame) -> dict:
    """True shooting and effective FG% over all shots in `logs`, not an average of per-game rates."""
    if logs.empty:
        return {"ts_pct": 0.0, "efg_pct": 0.0}
    pts, fga, fta = logs["pts"].fillna(0).sum(), logs["fga"].fillna(0).sum(), logs["fta"].fillna(0).sum()
    fgm, fg3m = logs["fgm"].fillna(0).sum(), logs["fg3m"].fillna(0).sum()
    ts_denom = 2 * (fga + 0.44 * fta)
    return {
        "ts_pct": float(pts / ts_denom) if ts_denom > 0 else 0.0,
        "efg_pct": float((fgm + 0.5 * fg3m) / fga) if fga > 0 else 0.0,
    }


def _played(logs: pd.DataFrame) -> pd.DataFrame:
    if logs.empty:
        return logs
    return logs[logs["min"].fillna(0) > 0].sort_values("game_date").reset_index(drop=True)


def _comparable_game_score(logs: pd.DataFrame) -> pd.Series:
    """Game Score on total rebounds only, so seasons cached without the OREB/DREB split compare fairly."""
    from analysis.performers import game_score
    return game_score(logs.drop(columns=["oreb", "dreb"], errors="ignore"))


def stretch_line(logs: pd.DataFrame) -> dict:
    """Per-game averages, pooled shooting and per-36 scoring for a set of games."""
    if logs.empty:
        return {}
    minutes = float(logs["min"].sum())
    return {
        "games": len(logs),
        "start": pd.Timestamp(logs["game_date"].min()),
        "end": pd.Timestamp(logs["game_date"].max()),
        "pts": float(logs["pts"].mean()),
        "reb": float(logs["reb"].mean()),
        "blk": float(logs["blk"].mean()),
        "stl": float(logs["stl"].mean()),
        "min": float(logs["min"].mean()),
        "ts_pct": pooled_shooting(logs)["ts_pct"],
        "pts_per_36": float(logs["pts"].sum() / minutes * 36) if minutes > 0 else 0.0,
        "game_score": float(_comparable_game_score(logs).mean()),
    }


def heat_check(wemby_logs: pd.DataFrame, games: pd.DataFrame, prev_logs: pd.DataFrame,
               window: int = HEAT_WINDOW) -> dict:
    """
    The last `window` games against the rest of this season and last season,
    plus what the recent per-minute rates come to at competitive-game minutes.

    Competitive minutes are his average in games decided by CLOSE_GAME_MARGIN
    or fewer this season; with too few of those, last season's average.
    """
    played = _played(wemby_logs)
    if len(played) < window:
        return {}
    margins = games.set_index("game_id")["margin"] if not games.empty else pd.Series(dtype=float)
    played = played.assign(margin=played["game_id"].map(margins))
    last, before = played.tail(window), played.iloc[:-window]
    prev = _played(prev_logs)

    close = played[played["margin"].abs() <= CLOSE_GAME_MARGIN]
    if len(close) >= MIN_CLOSE_GAMES:
        target, target_basis = float(close["min"].mean()), f"his average in {len(close)} games decided by {CLOSE_GAME_MARGIN} or fewer"
    elif not prev.empty:
        target, target_basis = float(prev["min"].mean()), "his average last season"
    else:
        target, target_basis = None, ""

    minutes = float(last["min"].sum())
    projected = ({stat: float(last[stat].sum() / minutes * target) for stat in ("pts", "reb", "blk")}
                 if target and minutes > 0 else {})
    return {
        "window": window,
        "last": stretch_line(last),
        "before": stretch_line(before) if len(before) >= 3 else {},
        "prev": stretch_line(prev),
        "prev_season": str(prev["season"].iloc[0]) if not prev.empty and "season" in prev.columns else "",
        "last_margins": [int(m) for m in last["margin"].dropna()],
        "target_minutes": target,
        "target_basis": target_basis,
        "projected": projected,
    }


def rolling_form(wemby_logs: pd.DataFrame, games: pd.DataFrame, window: int = HEAT_WINDOW,
                 min_periods: int = 3) -> pd.DataFrame:
    """Per-game line with pooled rolling TS% and points per 36 over the last `window` games."""
    played = _played(wemby_logs)
    if played.empty:
        return pd.DataFrame()
    ctx = games.set_index("game_id")[["opponent_abbr", "home_away", "margin"]] if not games.empty else None
    out = played[["game_id", "game_date", "min", "pts", "reb", "blk", "fga", "fta"]].copy()
    if ctx is not None:
        out = out.join(ctx, on="game_id")
    out["ts_pct"] = out["pts"] / (2 * (out["fga"] + 0.44 * out["fta"])).replace(0, np.nan)
    roll = out[["pts", "fga", "fta", "min"]].rolling(window, min_periods=min_periods).sum()
    out["roll_ts_pct"] = roll["pts"] / (2 * (roll["fga"] + 0.44 * roll["fta"])).replace(0, np.nan)
    out["roll_pts_per_36"] = roll["pts"] / roll["min"].replace(0, np.nan) * 36
    return out


def best_stretches(seasons: dict[str, pd.DataFrame], current_season: str, window: int = HEAT_WINDOW,
                   top: int = 5) -> dict:
    """
    Rank every `window`-game stretch inside each season by average Game Score.

    Returns the current stretch's rank among all stretches, how many stretches
    outside the current run beat it (overlapping windows from the same hot run
    don't count), and the best non-overlapping stretches. Rows that overlap the
    current stretch are flagged as part of the current run; if none made the
    list, the current stretch is appended so the run always appears.
    """
    windows = []
    for label, logs in seasons.items():
        played = _played(logs)
        if len(played) < window:
            continue
        gmsc = _comparable_game_score(played)
        for i in range(len(played) - window + 1):
            line = stretch_line(played.iloc[i:i + window])
            line["game_score"] = float(gmsc.iloc[i:i + window].mean())
            windows.append({**line, "season": label, "first": i, "last_idx": i + window - 1})
    if not windows:
        return {}
    windows.sort(key=lambda w: w["game_score"], reverse=True)
    for w in windows:   # ties share a rank: 1 + the number of strictly better stretches
        w["rank"] = 1 + sum(1 for o in windows if o["game_score"] > w["game_score"] + 1e-9)

    current = None
    if current_season in seasons:
        n_cur = len(_played(seasons[current_season]))
        current = next((w for w in windows if w["season"] == current_season and w["last_idx"] == n_cur - 1), None)

    def overlaps(a, b):
        return a["season"] == b["season"] and a["first"] <= b["last_idx"] and b["first"] <= a["last_idx"]

    chosen: list[dict] = []
    for w in windows:
        if len(chosen) >= top:
            break
        if not any(overlaps(w, c) for c in chosen):
            chosen.append(w)
    for w in chosen:
        w["current_run"] = current is not None and overlaps(w, current)
    if current is not None and not any(w["current_run"] for w in chosen):
        chosen.append({**current, "current_run": True})
    return {
        "current_rank": current["rank"] if current else None,
        "better_outside_run": (sum(1 for w in windows if w["rank"] < current["rank"] and not overlaps(w, current))
                               if current else None),
        "total": len(windows),
        "seasons": sorted({w["season"] for w in windows}),
        "rows": chosen,
    }


# ---------------------------------------------------------------------------
# Rich Terminal Reporting
# ---------------------------------------------------------------------------

def print_wemby_lab(
    console: Console,
    player_logs: pd.DataFrame,
    games: pd.DataFrame,
) -> None:
    """Print the Wemby Defensive & Gravity Lab dashboard to the terminal."""
    wemby = get_wemby_logs(player_logs)
    if wemby.empty:
        console.print("[yellow]No game logs found for Victor Wembanyama.[/yellow]")
        return

    stocks = stocks_distribution(wemby)
    impact = defensive_impact_summary(games, wemby)
    offense = offensive_gravity_summary(wemby)

    console.rule("[bold cyan]👽 Victor Wembanyama Defensive & Gravity Lab[/bold cyan]")

    # Overview Metrics Table
    t_overview = Table(title="Core Season Metrics & Deterrence", box=box.SIMPLE)
    t_overview.add_column("Metric", style="white", justify="left")
    t_overview.add_column("Value", style="cyan", justify="right")
    t_overview.add_column("Context / Baseline", style="dim", justify="left")

    t_overview.add_row("Games Tracked", str(stocks["games"]), "Active season appearances")
    t_overview.add_row("Points / Game", f"{offense['ppg']:.1f}", f"TS: {offense['true_shooting_pct']:.3f} | eFG: {offense['effective_fg_pct']:.3f}")
    t_overview.add_row("Blocks / Game", f"{stocks['blocks_per_game']:.2f}", f"Total: {stocks['total_blocks']}")
    t_overview.add_row("Steals / Game", f"{stocks['steals_per_game']:.2f}", f"Total: {stocks['total_steals']}")
    t_overview.add_row("Stocks (STL+BLK) / Game", f"{stocks['stocks_per_game']:.2f}", f"Per 36 Min: {stocks['stocks_per_36']:.2f}")
    t_overview.add_row("3P Attempt Rate", f"{offense['three_point_attempt_rate']:.3f}", f"{offense['fg3a_per_game']:.1f} 3PA / game perimeter gravity")
    console.print(t_overview)

    # Milestone Watch Table
    t_milestones = Table(title="Defensive Milestone Ledger", box=box.SIMPLE)
    t_milestones.add_column("Milestone Tier", style="cyan")
    t_milestones.add_column("Games Achieved", style="green", justify="right")
    t_milestones.add_column("Frequency", style="white", justify="right")

    t_milestones.add_row("3+ Blocks Games", str(stocks["games_3plus_blk"]), f"{stocks['pct_3plus_blk']:.1f}%")
    t_milestones.add_row("5+ Blocks Games", str(stocks["games_5plus_blk"]), f"{stocks['pct_5plus_blk']:.1f}%")
    t_milestones.add_row("7+ Blocks Games", str(stocks["games_7plus_blk"]), f"{stocks['games_7plus_blk'] / stocks['games'] * 100:.1f}%")
    t_milestones.add_row("5+ Stocks Games", str(stocks["games_5plus_stocks"]), f"{stocks['games_5plus_stocks'] / stocks['games'] * 100:.1f}%")
    t_milestones.add_row("8+ Stocks Games", str(stocks["games_8plus_stocks"]), f"{stocks['games_8plus_stocks'] / stocks['games'] * 100:.1f}%")
    t_milestones.add_row("5x5 Games Completed", str(stocks["five_by_fives"]), "All 5 counting stats >= 5")
    t_milestones.add_row("5x4 Games (Near Miss)", str(stocks["five_by_fours"]), "4 counting stats >= 5")
    console.print(t_milestones)

    # Deterrence Impact Panel
    if impact:
        p_text = (
            f"[bold]When Wemby Records 5+ Stocks ({impact['high_stocks_games']} games):[/bold]\n"
            f"  • Team Record: [green]{impact['high_stocks_record']}[/green]\n"
            f"  • Opponent Scoring: [green]{impact['high_stocks_opp_pts']:.1f} PPG[/green] "
            f"([bold cyan]-{impact['opp_pts_suppression']:.1f} PPG suppressed[/bold cyan])\n"
            f"  • Defensive Rating: [green]{impact['high_stocks_drtg']:.1f}[/green] "
            f"([bold cyan]-{impact['drtg_delta']:.1f} DRtg delta[/bold cyan])\n\n"
            f"[dim]When Wemby Records Under 5 Stocks ({impact['regular_stocks_games']} games): "
            f"Record {impact['regular_stocks_record']} | Opp PPG {impact['regular_stocks_opp_pts']:.1f} | DRtg {impact['regular_stocks_drtg']:.1f}[/dim]"
        )
        console.print(Panel(p_text, title="Alien Gravity: Team Defensive Impact Split", border_style="cyan"))
