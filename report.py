"""
CLI entry point — print the team dashboard to the terminal.

Reads from local cache (run fetch.py first).

Usage:
    python report.py                         # SAS 2025
    python report.py --team GSW --season 2024
    python report.py --section overview
    python report.py --section offense
    python report.py --section defense
    python report.py --section players
    python report.py --section streaks
    python report.py --section standings
"""

from __future__ import annotations

import argparse
import logging
import sys

from rich.console import Console
from rich.logging import RichHandler

import config
from config import TEAMS
from data.fetcher import Fetcher

console = Console()

SECTIONS = (
    "overview", "four_factors", "lineups", "clutch", "offense", "defense", "players", "streaks",
    "standings", "wemby", "rodeo", "ball_movement",
)


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.WARNING,
        format="%(message)s",
        handlers=[RichHandler(console=console, show_path=False)],
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Print the NBA team dashboard.")
    parser.add_argument("--team",    default=config.TEAM_ABBR)
    parser.add_argument("--season",  type=int, default=config.SEASON)
    parser.add_argument("--section", choices=SECTIONS, default=None,
                        help="Print only one section (default: all)")
    args = parser.parse_args()

    _setup_logging()

    abbr = args.team.upper()
    if abbr not in TEAMS:
        console.print(f"[red]Unknown team '{abbr}'.[/red]")
        sys.exit(1)

    team_info = TEAMS[abbr]
    team_id   = team_info["id"]
    season    = args.season
    season_s  = config.season_str(season)

    fetcher = Fetcher(team_id=team_id, season=season)

    try:
        games       = fetcher.load("games")
        player_logs = fetcher.load("player_game_log")
        roster      = fetcher.load("roster")
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        sys.exit(1)

    console.rule(f"[bold cyan]{team_info['name']} — {season_s}[/bold cyan]")

    sections_to_run = [args.section] if args.section else list(SECTIONS)

    for section in sections_to_run:
        if section == "overview":
            from analysis.standings import print_overview
            print_overview(console, games, team_info,
                           team_id=team_id, player_logs=player_logs)

        elif section == "four_factors":
            from analysis.four_factors import print_four_factors
            print_four_factors(console, player_logs, games)

        elif section == "lineups":
            from analysis.lineups import print_lineup_synergies
            print_lineup_synergies(console, player_logs)

        elif section == "clutch":
            from analysis.clutch import print_clutch_report
            print_clutch_report(console, games, player_logs)

        elif section == "standings":
            from analysis.standings import print_standings
            print_standings(console, team_id, season)

        elif section == "offense":
            from analysis.offense import print_offense
            print_offense(console, player_logs, games, roster)

        elif section == "defense":
            from analysis.defense import print_defense
            print_defense(console, games, player_logs, roster)

        elif section == "players":
            from analysis.players import print_players
            print_players(console, player_logs, roster)

        elif section == "streaks":
            from analysis.streaks import print_streaks
            print_streaks(console, games, player_logs)

        elif section == "wemby":
            from analysis.wemby import print_wemby_lab
            print_wemby_lab(console, player_logs, games)

        elif section == "rodeo":
            from analysis.rodeo import print_rodeo_report
            print_rodeo_report(console, games)

        elif section == "ball_movement":
            from analysis.beautiful_game import print_ball_movement
            print_ball_movement(console, player_logs, games)


if __name__ == "__main__":
    main()
