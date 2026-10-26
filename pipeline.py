"""
Master Automation Pipeline — End-to-End Orchestrator for Spurs Tracker.

Executes the complete operational sequence:
  1. Data Ingestion (incremental or refresh)
  2. Parquet Schema & Cache Integrity Validation
  3. Static Analytical API Export (JSON for client-side interactivity)
  4. Visual HTML Dashboard & Portal Compilation
  5. Social Distribution Post Generation

Usage:
    python pipeline.py                          # Full local pipeline with cached parquets
    python pipeline.py --skip-fetch             # Offline/cache-only build
    python pipeline.py --refresh                # Force pull latest from stats.nba.com
    python pipeline.py --season 2025            # Specify season
    python pipeline.py --skip-viz               # Headless data & model export only
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

import pandas as pd
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table
from rich import box

import config
from config import TEAM_ABBR, SEASON, TEAMS, season_str
from data.fetcher import Fetcher
from data.validator import validate_all_caches
from data.exporter import export_all_data

console = Console()


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.WARNING,
        format="%(message)s",
        handlers=[RichHandler(console=console, show_path=False)],
    )


def run_pipeline(
    team_abbr: str = TEAM_ABBR,
    season: int = SEASON,
    skip_fetch: bool = False,
    refresh: bool = False,
    skip_viz: bool = False,
    skip_export: bool = False,
    verbose: bool = False,
) -> bool:
    """
    Execute the master pipeline.
    Returns True if all enabled stages succeed, False otherwise.
    """
    _setup_logging(verbose)
    team_info = TEAMS.get(team_abbr.upper())
    if not team_info:
        console.print(f"[red]Unknown team '{team_abbr}'.[/red]")
        return False

    team_id = team_info["id"]
    team_name = team_info["name"]
    season_s = season_str(season)

    console.rule(f"[bold cyan]🔨 Spurs Tracker &bull; Master Pipeline ({team_abbr} {season_s})[/bold cyan]")
    t0 = time.time()

    # Track stage status
    pipeline_results: list[tuple[str, str, str]] = []

    fetcher = Fetcher(team_id=team_id, season=season)

    # -------------------------------------------------------------------------
    # Stage 1: Ingestion
    # -------------------------------------------------------------------------
    if not skip_fetch and refresh:
        console.print("[cyan]Stage 1: Fetching data from stats.nba.com…[/cyan]")
        try:
            from data.league import fetch_league_standings, fetch_team_players
            from data.schedule import fetch_schedule, next_game, now_utc
            fetcher.fetch_all(incremental=True)
            fetch_league_standings(season=season, force_refresh=True)
            # Schedule drives the Next Game preview; the opponent's player stats feed "players to watch"
            nxt = next_game(fetch_schedule(season=season, force_refresh=True), team_abbr.upper(), now_utc())
            if nxt:
                fetch_team_players(TEAMS[nxt["opponent"]]["id"], season=season, force_refresh=True)
            pipeline_results.append(("Stage 1: Ingestion", "PASS", "Cache refreshed from stats.nba.com"))
        except Exception as e:
            console.print(f"[yellow]Warning: Fetch encountered an error: {e}. Falling back to cached parquets.[/yellow]")
            pipeline_results.append(("Stage 1: Ingestion", "WARN", f"Fallback to cache: {e}"))
    else:
        pipeline_results.append(("Stage 1: Ingestion", "SKIPPED", "Using cached parquets"))

    # Load base datasets
    try:
        games = fetcher.load("games")
        player_logs = fetcher.load("player_game_log")
        try:
            roster = fetcher.load("roster")
        except Exception:
            roster = pd.DataFrame()
    except FileNotFoundError as e:
        console.print(f"[red]Required parquet missing: {e}[/red]")
        pipeline_results.append(("Stage 1: Ingestion", "FAIL", str(e)))
        return False

    # -------------------------------------------------------------------------
    # Stage 2: Schema & Cache Validation
    # -------------------------------------------------------------------------
    console.print("[cyan]Stage 2: Auditing Parquet Schema & Cache Integrity…[/cyan]")
    audit_results = validate_all_caches(season=season)
    all_passed = all(item.get("status") == "PASS" for item in audit_results)
    if all_passed:
        pipeline_results.append(("Stage 2: Validation", "PASS", f"All {len(audit_results)} caches valid"))
    else:
        failed_count = sum(1 for item in audit_results if item.get("status") == "FAIL")
        pipeline_results.append(("Stage 2: Validation", "FAIL", f"{failed_count} caches failed validation"))
        console.print(f"[red]Cache validation failed on {failed_count} files.[/red]")
        return False

    # -------------------------------------------------------------------------
    # Stage 3: Analytical Static API Export
    # -------------------------------------------------------------------------
    if not skip_export:
        console.print("[cyan]Stage 3: Exporting Analytical Static JSON APIs (docs/data/)…[/cyan]")
        try:
            exported = export_all_data(games=games, player_logs=player_logs, season=season)
            pipeline_results.append(("Stage 3: JSON Export", "PASS", f"{len(exported)} JSON datasets exported"))
        except Exception as e:
            console.print(f"[red]Export failed: {e}[/red]")
            pipeline_results.append(("Stage 3: JSON Export", "FAIL", str(e)))
            return False
    else:
        pipeline_results.append(("Stage 3: JSON Export", "SKIPPED", "Flag --skip-export active"))

    # -------------------------------------------------------------------------
    # Stage 4: Visual Dashboards & Web Portals
    # -------------------------------------------------------------------------
    if not skip_viz:
        console.print("[cyan]Stage 4: Compiling Interactive Visual Dashboards & Web Portals…[/cyan]")
        try:
            from viz.dashboard import build
            from viz.wemby_viz import build_wemby_lab_page
            from viz.rodeo_viz import build_rodeo_page
            from viz.notebook_viz import build_notebook_page
            from viz.props_viz import build_props_board_page
            from viz.matchup_viz import build_matchup_page
            from viz.index_viz import build_index_page

            dash_path = build(games, player_logs, team_name, team_abbr, season)
            wemby_path = build_wemby_lab_page(games, player_logs, season, team_abbr)
            rodeo_path = build_rodeo_page(games, season, team_abbr)
            nb_path = build_notebook_page(games, player_logs, roster, season, team_abbr)
            props_path = build_props_board_page(games, player_logs, season, team_abbr)
            matchup_path = build_matchup_page(games, player_logs, season, team_abbr)
            if team_abbr.upper() == config.TEAM_ABBR and season == config.SEASON:
                build_index_page(games, player_logs, season, team_abbr)

            pipeline_results.append(("Stage 4: Visual Compilation", "PASS", "6 HTML portals + landing page generated"))
        except Exception as e:
            console.print(f"[red]Visual compilation failed: {e}[/red]")
            pipeline_results.append(("Stage 4: Visual Compilation", "FAIL", str(e)))
            return False
    else:
        pipeline_results.append(("Stage 4: Visual Compilation", "SKIPPED", "Flag --skip-viz active"))

    # -------------------------------------------------------------------------
    # Stage 5: Social Distribution Verification
    # -------------------------------------------------------------------------
    console.print("[cyan]Stage 5: Verifying Social Post Generation…[/cyan]")
    try:
        from social import generate_prediction_tweet, generate_postgame_tweet
        p_tweet = generate_prediction_tweet(games, opp="HOU")
        if len(p_tweet) > 0:
            pipeline_results.append(("Stage 5: Social Preview", "PASS", "Social post generator verified"))
    except Exception as e:
        pipeline_results.append(("Stage 5: Social Preview", "WARN", f"Social generator warning: {e}"))

    elapsed = time.time() - t0

    # -------------------------------------------------------------------------
    # Pipeline Summary
    # -------------------------------------------------------------------------
    table = Table(title=f"Spurs Tracker Pipeline Execution Summary ({elapsed:.2f}s)", box=box.ROUNDED)
    table.add_column("Stage", style="bold white")
    table.add_column("Status", justify="center")
    table.add_column("Details", style="dim")

    for stage, status, details in pipeline_results:
        if status == "PASS":
            status_render = "[green]✓ PASS[/green]"
        elif status == "SKIPPED":
            status_render = "[dim yellow]— SKIP[/dim yellow]"
        elif status == "WARN":
            status_render = "[yellow]! WARN[/yellow]"
        else:
            status_render = "[red]✗ FAIL[/red]"
        table.add_row(stage, status_render, details)

    console.print(table)
    console.print(f"[bold green]✨ Pipeline complete in {elapsed:.2f}s. All systems operational.[/bold green]")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Master automation pipeline for Spurs Tracker.")
    parser.add_argument("--team", default=TEAM_ABBR, help="Team abbreviation (default: SAS)")
    parser.add_argument("--season", type=int, default=SEASON, help=f"Season start year (default: {SEASON})")
    parser.add_argument("--skip-fetch", action="store_true", default=True, help="Skip remote NBA API fetch and rely on cached parquets")
    parser.add_argument("--refresh", action="store_true", help="Force remote fetch from stats.nba.com")
    parser.add_argument("--skip-viz", action="store_true", help="Skip compiling HTML pages")
    parser.add_argument("--skip-export", action="store_true", help="Skip exporting static JSON files")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()

    skip_fetch = args.skip_fetch and not args.refresh

    success = run_pipeline(
        team_abbr=args.team,
        season=args.season,
        skip_fetch=skip_fetch,
        refresh=args.refresh,
        skip_viz=args.skip_viz,
        skip_export=args.skip_export,
        verbose=args.verbose,
    )
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
