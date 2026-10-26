"""
CLI entry point — fetch and cache all data for a team/season.

Usage:
    python fetch.py                          # SAS 2025 (defaults from config.py)
    python fetch.py --team GSW --season 2024
    python fetch.py --refresh                # force re-fetch, ignore cache
    python fetch.py --list-teams             # print all 30 team abbreviations
    python fetch.py --verbose                # show debug-level logging
"""

from __future__ import annotations

import argparse
import logging
import sys

from rich.console import Console
from rich.table import Table
from rich.logging import RichHandler

import config
from config import TEAMS
from data.fetcher import Fetcher

console = Console()


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[RichHandler(console=console, rich_tracebacks=True, show_path=False)],
    )


def _print_teams() -> None:
    table = Table(title="NBA Teams", show_lines=True)
    table.add_column("Abbr", style="bold cyan", width=6)
    table.add_column("ID",   style="yellow",    width=12)
    table.add_column("Name", style="white")
    table.add_column("Conf", style="dim",       width=5)
    table.add_column("Div",  style="dim",       width=12)

    west = {k: v for k, v in TEAMS.items() if v["conf"] == "West"}
    east = {k: v for k, v in TEAMS.items() if v["conf"] == "East"}

    for abbr, info in sorted(west.items()):
        table.add_row(abbr, str(info["id"]), info["name"], "West", info["div"])
    for abbr, info in sorted(east.items()):
        table.add_row(abbr, str(info["id"]), info["name"], "East", info["div"])

    console.print(table)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch and cache NBA stats for a team/season."
    )
    parser.add_argument("--team",       default=config.TEAM_ABBR,
                        help=f"Team abbreviation (default: {config.TEAM_ABBR})")
    parser.add_argument("--season",     type=int, default=config.SEASON,
                        help=f"Season start year (default: {config.SEASON})")
    parser.add_argument("--season-type", default=config.SEASON_TYPE,
                        choices=["Regular Season", "Pre Season", "Playoffs"],
                        help=f"Season type (default: {config.SEASON_TYPE})")
    parser.add_argument("--preseason",   action="store_const", const="Pre Season", dest="season_type",
                        help="Shorthand for --season-type 'Pre Season'")
    parser.add_argument("--playoffs",    action="store_const", const="Playoffs", dest="season_type",
                        help="Shorthand for --season-type 'Playoffs'")
    parser.add_argument("--league",      action="store_true",
                        help="Also fetch and cache 30-team league standings & ratings")
    parser.add_argument("--refresh",    action="store_true",
                        help="Force re-fetch, ignoring cached data")
    parser.add_argument("--list-teams", action="store_true",
                        help="Print all 30 team abbreviations and exit")
    parser.add_argument("--verbose",    action="store_true",
                        help="Show debug-level logging")
    args = parser.parse_args()

    _setup_logging(args.verbose)
    log = logging.getLogger(__name__)

    if args.list_teams:
        _print_teams()
        return

    abbr = args.team.upper()
    if abbr not in TEAMS:
        console.print(f"[red]Unknown team '{abbr}'. Run with --list-teams to see options.[/red]")
        sys.exit(1)

    team_info   = TEAMS[abbr]
    team_id     = team_info["id"]
    season      = args.season
    season_s    = config.season_str(season)
    season_type = args.season_type

    console.rule(f"[bold cyan]{team_info['name']} — {season_s} ({season_type})[/bold cyan]")
    console.print(f"  Team ID     : [yellow]{team_id}[/yellow]")
    console.print(f"  Season      : [yellow]{season_s}[/yellow]")
    console.print(f"  Season Type : [yellow]{season_type}[/yellow]")
    console.print(f"  Cache       : [dim]{config.CACHE_DIR}[/dim]\n")

    fetcher = Fetcher(
        team_id=team_id,
        season=season,
        force_refresh=args.refresh,
        season_type=season_type,
    )

    with console.status("[bold green]Fetching data (incremental check)...[/bold green]"):
        tables = fetcher.fetch_all(incremental=not args.refresh)

    if args.league:
        from data.league import fetch_league_standings
        with console.status("[bold green]Fetching 30-team league standings...[/bold green]"):
            league_df = fetch_league_standings(season=season, force_refresh=args.refresh)
            tables["league_standings"] = league_df

    summary = Table(title="Fetch Summary", show_lines=False)
    summary.add_column("Table",   style="cyan")
    summary.add_column("Rows",    style="yellow", justify="right")
    summary.add_column("Columns", style="dim",    justify="right")

    for name, df in tables.items():
        summary.add_row(name, str(len(df)), str(len(df.columns)))

    console.print(summary)
    console.print(
        "\n[bold green]Done.[/bold green] "
        "Run [cyan]python report.py[/cyan] or [cyan]python viz_report.py[/cyan]."
    )


if __name__ == "__main__":
    main()
