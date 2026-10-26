"""
CLI entry point — generate charts and the interactive HTML dashboard.

Usage:
    python viz_report.py                          # SAS 2025, all charts
    python viz_report.py --team SAS --season 2024
    python viz_report.py --history                # include historical win% chart
    python viz_report.py --pace 2014 2016         # overlay comparison seasons
    python viz_report.py --open                   # open dashboard in browser when done
    python viz_report.py --png                    # also export PNGs (requires kaleido)
"""

from __future__ import annotations

import argparse
import logging
import sys
import webbrowser

from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table
from rich import box

import config
from config import TEAMS
from data.fetcher import Fetcher

console = Console()


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.WARNING,
        format="%(message)s",
        handlers=[RichHandler(console=console, show_path=False)],
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate NBA team dashboard charts.")
    parser.add_argument("--team",    default=config.TEAM_ABBR)
    parser.add_argument("--season",  type=int, default=config.SEASON)
    parser.add_argument("--history", action="store_true",
                        help="Fetch + render historical win%% bar chart")
    parser.add_argument("--pace",    nargs="+", type=int, metavar="YEAR",
                        help="Years to overlay on pace comparison chart (e.g. --pace 2014 2016)")
    parser.add_argument("--open",    action="store_true",
                        help="Open the dashboard in the default browser when done")
    parser.add_argument("--png",     action="store_true",
                        help="Export static PNG images (requires: pip install kaleido)")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    _setup_logging(args.verbose)

    abbr = args.team.upper()
    if abbr not in TEAMS:
        console.print(f"[red]Unknown team '{abbr}'. Run `python fetch.py --list-teams`.[/red]")
        sys.exit(1)

    team_info = TEAMS[abbr]
    team_id   = team_info["id"]
    team_name = team_info["name"]
    season    = args.season

    fetcher = Fetcher(team_id=team_id, season=season)
    try:
        games      = fetcher.load("games")
        player_logs = fetcher.load("player_game_log")
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        sys.exit(1)

    season_s = config.season_str(season)
    console.rule(f"[bold cyan]{team_name} — {season_s} Viz Report[/bold cyan]")

    output_files: list[str] = []

    # -----------------------------------------------------------------------
    # Main dashboard
    # -----------------------------------------------------------------------
    with console.status("[bold green]Building dashboard…[/bold green]"):
        from viz.dashboard import build
        dash_path = build(
            games=games, player_logs=player_logs,
            team_name=team_name, team_abbr=abbr, season=season,
        )
    console.print(f"[green]Dashboard[/green] → [cyan]{dash_path}[/cyan]")
    output_files.append(str(dash_path))

    # -----------------------------------------------------------------------
    # Spurs Intelligence Portals
    # -----------------------------------------------------------------------
    if abbr == "SAS":
        try:
            roster = fetcher.load("roster")
        except Exception:
            roster = pd.DataFrame()

        from viz.wemby_viz import build_wemby_lab_page
        from viz.rodeo_viz import build_rodeo_page
        from viz.notebook_viz import build_notebook_page
        from viz.props_viz import build_props_board_page
        from viz.matchup_viz import build_matchup_page

        with console.status("[bold green]Building Wemby Lab…[/bold green]"):
            wemby_path = build_wemby_lab_page(games, player_logs, season=season, team_abbr=abbr)
            console.print(f"[green]Wemby Lab[/green] → [cyan]{wemby_path}[/cyan]")
            output_files.append(str(wemby_path))

        with console.status("[bold green]Building Rodeo Road Trip…[/bold green]"):
            rodeo_path = build_rodeo_page(games, season=season, team_abbr=abbr)
            console.print(f"[green]Rodeo Road Trip[/green] → [cyan]{rodeo_path}[/cyan]")
            output_files.append(str(rodeo_path))

        with console.status("[bold green]Building Living Notebook…[/bold green]"):
            nb_path = build_notebook_page(games, player_logs, roster, season=season, team_abbr=abbr)
            console.print(f"[green]Notebook[/green] → [cyan]{nb_path}[/cyan]")
            output_files.append(str(nb_path))

        with console.status("[bold green]Building Props & Next Game…[/bold green]"):
            props_path = build_props_board_page(games, player_logs, season=season, team_abbr=abbr)
            matchup_path = build_matchup_page(games, player_logs, season=season, team_abbr=abbr)
            console.print(f"[green]Player Props[/green] → [cyan]{props_path}[/cyan]")
            console.print(f"[green]Next Game[/green] → [cyan]{matchup_path}[/cyan]")
            output_files.append(str(props_path))
            output_files.append(str(matchup_path))

    # -----------------------------------------------------------------------
    # Historical win% chart
    # -----------------------------------------------------------------------
    if args.history:
        with console.status("[bold green]Fetching historical records…[/bold green]"):
            from analysis.history import fetch_season_records, NOTABLE_SEASONS
            from viz.charts import multi_season_win_pct
            from viz.exports import save_html

            historical = fetch_season_records(team_id)
            if not historical.empty:
                notable = NOTABLE_SEASONS.get(abbr, {})
                fig = multi_season_win_pct(historical, team_name, highlight_seasons=notable)
                hist_path = config.OUTPUT_DIR / f"history_{abbr}.html"
                save_html(fig, hist_path)
                console.print(f"[green]History chart[/green] → [cyan]{hist_path}[/cyan]")
                output_files.append(str(hist_path))

    # -----------------------------------------------------------------------
    # Pace comparison chart
    # -----------------------------------------------------------------------
    if args.pace:
        with console.status("[bold green]Building pace comparison…[/bold green]"):
            from analysis.history import build_pace_comparison
            from viz.charts import pace_comparison_chart
            from viz.exports import save_html

            ref_seasons = build_pace_comparison(games, team_id, args.pace)
            if ref_seasons:
                fig = pace_comparison_chart(games, ref_seasons, team_name)
                pace_path = config.OUTPUT_DIR / f"pace_{abbr}_{season}.html"
                save_html(fig, pace_path)
                console.print(f"[green]Pace chart[/green] → [cyan]{pace_path}[/cyan]")
                output_files.append(str(pace_path))
            else:
                console.print(
                    "[yellow]No cached game logs found for requested years "
                    "(fetch them first with fetch.py --season YEAR).[/yellow]"
                )

    # -----------------------------------------------------------------------
    # PNG exports
    # -----------------------------------------------------------------------
    if args.png:
        with console.status("[bold green]Exporting PNGs…[/bold green]"):
            from viz.dashboard import build_png_exports
            pngs = build_png_exports(
                games=games, player_logs=player_logs,
                team_name=team_name, team_abbr=abbr, season=season,
            )
        for p in pngs:
            console.print(f"[green]PNG[/green] → [cyan]{p}[/cyan]")
            output_files.append(str(p))

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    summary = Table(title="Output Files", box=box.SIMPLE, show_lines=False)
    summary.add_column("File", style="cyan")
    for f in output_files:
        summary.add_row(f)
    console.print(summary)

    if args.open:
        import os
        webbrowser.open(f"file://{os.path.abspath(str(dash_path))}")


if __name__ == "__main__":
    main()
