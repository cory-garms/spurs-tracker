"""
Standings & season overview analysis.

Covers:
  - Current W-L, win%, net rating, margin, Pythagorean record
  - Home/away, conference/division splits
  - Rolling 5/10-game win% trend
  - Live conference standings
"""

from __future__ import annotations

import pandas as pd
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.columns import Columns
from rich import box

from config import TEAMS, season_str

# {team_id: {abbr, name, conf, div}}
_ID_TO_TEAM: dict[int, dict] = {v["id"]: {**v, "abbr": k} for k, v in TEAMS.items()}


def _div_peer_ids(team_id: int) -> set[int]:
    me = _ID_TO_TEAM.get(team_id, {})
    return {
        info["id"]
        for info in _ID_TO_TEAM.values()
        if info["id"] != team_id
        and info["conf"] == me.get("conf")
        and info["div"]  == me.get("div")
    }


def _conf_peer_ids(team_id: int) -> set[int]:
    me = _ID_TO_TEAM.get(team_id, {})
    return {
        info["id"]
        for info in _ID_TO_TEAM.values()
        if info["id"] != team_id and info["conf"] == me.get("conf")
    }


# ---------------------------------------------------------------------------
# Pythagorean & pace
# ---------------------------------------------------------------------------

def pythagorean_record(pts: int, opp_pts: int, games: int, exponent: float = 13.91) -> tuple[int, int]:
    """NBA Pythagorean expectation (exponent ~13.91)."""
    if pts + opp_pts == 0:
        return 0, 0
    pct = pts ** exponent / (pts ** exponent + opp_pts ** exponent)
    w = round(pct * games)
    return w, games - w


def pace_projection(wins: int, losses: int, total_games: int = 82) -> tuple[int, int]:
    """Project final W-L based on current win rate over 82-game season."""
    played = wins + losses
    if played == 0:
        return 0, 0
    w = round((wins / played) * total_games)
    return w, total_games - w


# ---------------------------------------------------------------------------
# Season record
# ---------------------------------------------------------------------------

def season_record(games: pd.DataFrame) -> dict:
    """
    Full season record dict from the cached games table.

    Keys: wins, losses, win_pct, games_played,
          net_rtg, avg_margin, pts_per_game, opp_pts_per_game,
          pyth_wins, pyth_losses,
          home_w, home_l, away_w, away_l,
          last_10_w, last_10_l, last_20_w, last_20_l
    """
    f = games[games["status"] == "Final"].copy()
    if f.empty:
        return {}

    def wl(df: pd.DataFrame) -> tuple[int, int]:
        return int((df["result"] == "W").sum()), int((df["result"] == "L").sum())

    w, l   = wl(f)
    g      = w + l
    total_pts     = int(f["pts"].sum())
    total_opp_pts = int(f["opp_pts"].sum())
    pyth_w, pyth_l = pythagorean_record(total_pts, total_opp_pts, g)
    hw, hl = wl(f[f["home_away"] == "H"])
    aw, al = wl(f[f["home_away"] == "A"])
    l10w, l10l = wl(f.sort_values("game_date").tail(10))
    l20w, l20l = wl(f.sort_values("game_date").tail(20))

    return dict(
        wins=w, losses=l, games_played=g,
        win_pct=w / g if g > 0 else 0.0,
        net_rtg=round(float(f["nrtg"].mean()), 2) if "nrtg" in f else 0.0,
        avg_margin=round(float(f["margin"].mean()), 2) if g > 0 else 0.0,
        pts_per_game=round(total_pts / g, 1) if g > 0 else 0.0,
        opp_pts_per_game=round(total_opp_pts / g, 1) if g > 0 else 0.0,
        pyth_wins=pyth_w, pyth_losses=pyth_l,
        home_w=hw, home_l=hl,
        away_w=aw, away_l=al,
        last_10_w=l10w, last_10_l=l10l,
        last_20_w=l20w, last_20_l=l20l,
    )


def conference_splits(games: pd.DataFrame, team_id: int) -> dict:
    """W-L splits vs. division and conference opponents."""
    f      = games[games["status"] == "Final"].copy()
    div_ids  = _div_peer_ids(team_id)
    conf_ids = _conf_peer_ids(team_id) - div_ids

    def wl(df):
        return int((df["result"] == "W").sum()), int((df["result"] == "L").sum())

    div_w,  div_l  = wl(f[f["opponent_id"].isin(div_ids)])
    conf_w, conf_l = wl(f[f["opponent_id"].isin(conf_ids)])
    opp_w,  opp_l  = wl(f[~f["opponent_id"].isin(div_ids | conf_ids | {team_id})])

    return dict(
        div_w=div_w,   div_l=div_l,
        conf_w=conf_w, conf_l=conf_l,
        opp_w=opp_w,   opp_l=opp_l,
    )


def rolling_win_pct(games: pd.DataFrame, window: int = 10) -> pd.Series:
    """Rolling win% over a sliding window, indexed by game_date."""
    f = games[games["status"] == "Final"].sort_values("game_date").copy()
    f["win_flag"] = (f["result"] == "W").astype(int)
    return f.set_index("game_date")["win_flag"].rolling(window).mean()


# ---------------------------------------------------------------------------
# Live standings
# ---------------------------------------------------------------------------

def conference_standings(team_id: int, season: int) -> list[dict]:
    """
    Pull live standings for the conference containing team_id.
    Returns list of dicts sorted by conference rank.
    """
    from client.nba_client import NBAClient
    client = NBAClient()
    sstr   = season_str(season)

    try:
        df = client.get_standings(sstr)
    except Exception as e:
        return []

    if df.empty:
        return []

    # Determine our conference
    me_info = _ID_TO_TEAM.get(team_id, {})
    my_conf = me_info.get("conf", "West")

    rows: list[dict] = []
    for _, row in df.iterrows():
        conf = str(row.get("conference", row.get("team_conference", ""))).title()
        if conf != my_conf:
            continue

        tid   = int(row.get("teamid", row.get("team_id", 0)))
        wins  = int(row.get("wins", row.get("w", 0)))
        losses= int(row.get("losses", row.get("l", 0)))
        played= wins + losses
        pw, pl = pace_projection(wins, losses)

        city = str(row.get("teamcity", row.get("team_city", "")))
        name = str(row.get("teamname", row.get("team_name", "")))
        rows.append(dict(
            team_id   = tid,
            team_name = f"{city} {name}".strip(),
            wins      = wins,
            losses    = losses,
            win_pct   = wins / played if played > 0 else 0.0,
            conf_rank = int(row.get("playoffrank", row.get("playoff_rank", row.get("conference_rank", 99)))),
            pace_w    = pw,
            pace_l    = pl,
        ))

    return sorted(rows, key=lambda r: r["conf_rank"])


# ---------------------------------------------------------------------------
# Rich terminal output
# ---------------------------------------------------------------------------

def print_overview(
    console: Console,
    games: pd.DataFrame,
    team_info: dict,
    team_id: int | None = None,
    player_logs: pd.DataFrame | None = None,
) -> None:
    from analysis.streaks import current_streak

    rec = season_record(games)
    if not rec:
        console.print("[yellow]No completed games found in cache.[/yellow]")
        return

    tid = team_id or team_info.get("id", 0)
    w, l = rec["wins"], rec["losses"]
    proj_w, proj_l = pace_projection(w, l)
    streak_type, streak_len = current_streak(games)
    streak_color = "green" if streak_type == "W" else "red"
    streak_label = f"[{streak_color}]{streak_type}{streak_len}[/{streak_color}]"

    nrtg = rec.get("net_rtg", 0.0)
    nrtg_str = f"[green]+{nrtg:.1f}[/green]" if nrtg >= 0 else f"[red]{nrtg:.1f}[/red]"

    rec_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    rec_table.add_column("Metric", style="cyan",  min_width=18)
    rec_table.add_column("Value",  style="white", justify="right")

    rec_table.add_row("Record",         f"[bold]{w}-{l}[/bold]  ({rec['win_pct']:.3f})")
    rec_table.add_row("Streak",         streak_label)
    rec_table.add_row("Net Rating",     nrtg_str)
    rec_table.add_row("Pts/G | Opp/G",  f"{rec['pts_per_game']}  |  {rec['opp_pts_per_game']}")
    rec_table.add_row("Avg Margin",     f"{rec['avg_margin']:+.1f}")
    rec_table.add_row("Pythagorean",    f"{rec['pyth_wins']}-{rec['pyth_losses']}")
    rec_table.add_row("82-Game Pace",   f"[bold]{proj_w}-{proj_l}[/bold]")

    splits = conference_splits(games, tid)
    split_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    split_table.add_column("Split",  style="cyan",  min_width=14)
    split_table.add_column("W-L",    style="white", justify="right")

    split_table.add_row("Home",       f"{rec['home_w']}-{rec['home_l']}")
    split_table.add_row("Away",       f"{rec['away_w']}-{rec['away_l']}")
    split_table.add_row("vs Div",     f"{splits['div_w']}-{splits['div_l']}")
    split_table.add_row("vs Conf",    f"{splits['conf_w']}-{splits['conf_l']}")
    split_table.add_row("vs Opp Conf",f"{splits['opp_w']}-{splits['opp_l']}")
    split_table.add_row("Last 10",    f"{rec['last_10_w']}-{rec['last_10_l']}")
    split_table.add_row("Last 20",    f"{rec['last_20_w']}-{rec['last_20_l']}")

    console.print(Panel(
        Columns([rec_table, split_table], equal=False, expand=False),
        title=f"[bold cyan]{team_info['name']} — Season Overview[/bold cyan]",
        border_style="cyan",
    ))

    if player_logs is not None and not player_logs.empty:
        from analysis.offense import team_offense_summary
        off = team_offense_summary(player_logs, games)
        if off:
            _print_team_offense_row(console, off)


def _print_team_offense_row(console: Console, off: dict) -> None:
    t = Table(title="Team Offense", box=box.SIMPLE, show_header=True, padding=(0, 1))
    for col in ("Pts/G", "Opp Pts/G", "FG%", "3P%", "FT%", "TS%", "Pace", "ORtg"):
        t.add_column(col, style="white", justify="right")
    t.add_row(
        f"{off.get('pts_per_game', 0):.1f}",
        f"{off.get('opp_pts_per_game', 0):.1f}",
        f"{off.get('fg_pct', 0):.3f}",
        f"{off.get('fg3_pct', 0):.3f}",
        f"{off.get('ft_pct', 0):.3f}",
        f"{off.get('ts_pct', 0):.3f}",
        f"{off.get('pace', 0):.1f}",
        f"{off.get('ortg', 0):.1f}",
    )
    console.print(t)


def print_standings(console: Console, team_id: int, season: int) -> None:
    """Fetch live conference standings and render as a Rich table."""
    with console.status("[bold green]Fetching standings…[/bold green]"):
        rows = conference_standings(team_id, season)

    if not rows:
        console.print("[yellow]Could not retrieve standings.[/yellow]")
        return

    t = Table(
        title=f"Conference Standings — {season_str(season)}",
        box=box.SIMPLE_HEAVY,
        show_lines=False,
    )
    t.add_column("Team",   style="white",  min_width=24)
    t.add_column("W",      style="green",  justify="right")
    t.add_column("L",      style="red",    justify="right")
    t.add_column("PCT",    style="white",  justify="right")
    t.add_column("Pace",   style="dim",    justify="right")

    for row in rows:
        is_us    = row["team_id"] == team_id
        name_str = (
            f"[bold cyan]{row['team_name']}[/bold cyan]" if is_us else row["team_name"]
        )
        t.add_row(
            name_str,
            str(row["wins"]),
            str(row["losses"]),
            f"{row['win_pct']:.3f}",
            f"{row['pace_w']}-{row['pace_l']}",
        )

    console.print(t)
