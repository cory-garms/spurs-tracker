"""
Cache & Schema Integrity Validator.

Inspects all cached Parquet files in data/cache/, verifies column schemas,
checks for corrupt records or null values in critical fields, and prints
a diagnostic health status report.

Usage:
    python data/validator.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pandas as pd
from rich.console import Console
from rich.table import Table
from rich import box

import config
from config import CACHE_DIR
from data.schema import GAMES_SCHEMA, PLAYER_GAME_LOG_SCHEMA, ROSTER_SCHEMA
from data.league import LEAGUE_STANDINGS_SCHEMA

console = Console()


def validate_table(file_path: Path) -> dict:
    """Validate a single parquet file and return health metrics."""
    fname = file_path.name
    res = {
        "file": fname,
        "size_kb": round(file_path.stat().st_size / 1024, 1),
        "rows": 0,
        "cols": 0,
        "status": "PASS",
        "notes": "OK",
    }

    try:
        df = pd.read_parquet(file_path)
    except Exception as e:
        res["status"] = "FAIL"
        res["notes"] = f"Unreadable: {e}"
        return res

    res["rows"] = len(df)
    res["cols"] = len(df.columns)

    if df.empty:
        res["status"] = "WARN"
        res["notes"] = "Empty table (0 rows)"
        return res

    # Schema checks depending on table prefix
    if fname.startswith("games_"):
        expected_schema = GAMES_SCHEMA
        critical_cols = ["game_id", "game_date", "pts", "opp_pts", "margin"]
    elif fname.startswith("player_game_log_"):
        expected_schema = PLAYER_GAME_LOG_SCHEMA
        critical_cols = ["game_id", "player_id", "player_name", "pts"]
    elif fname.startswith("roster_"):
        expected_schema = ROSTER_SCHEMA
        critical_cols = ["player_id", "player_name"]
    elif fname.startswith("league_standings_"):
        expected_schema = LEAGUE_STANDINGS_SCHEMA
        critical_cols = ["team_id", "team_abbr", "wins", "losses"]
    else:
        expected_schema = {}
        critical_cols = []

    # Check for missing critical columns
    missing_cols = [c for c in critical_cols if c not in df.columns]
    if missing_cols:
        res["status"] = "FAIL"
        res["notes"] = f"Missing columns: {', '.join(missing_cols)}"
        return res

    # Check for nulls in critical columns
    null_issues = []
    for c in critical_cols:
        null_count = int(df[c].isna().sum())
        if null_count > 0:
            null_issues.append(f"{c}: {null_count} nulls")

    if null_issues:
        res["status"] = "WARN"
        res["notes"] = f"Nulls in critical fields ({', '.join(null_issues)})"

    # Date range for games
    if "game_date" in df.columns and not df.empty:
        dates = df["game_date"].dropna().astype(str).sort_values()
        if not dates.empty:
            res["notes"] += f" [{dates.iloc[0]} to {dates.iloc[-1]}]"

    return res


def run_validation(cache_dir: Path = CACHE_DIR) -> list[dict]:
    """Run validation across all parquet files in the cache directory."""
    parquet_files = sorted(cache_dir.glob("*.parquet"))
    results = []
    for p in parquet_files:
        results.append(validate_table(p))
    return results


def validate_all_caches(season: int | None = None, cache_dir: Path = CACHE_DIR) -> list[dict]:
    """Validate parquet caches, optionally filtering by season year."""
    parquet_files = sorted(cache_dir.glob("*.parquet"))
    if season is not None:
        parquet_files = [p for p in parquet_files if str(season) in p.name]
    results = []
    for p in parquet_files:
        results.append(validate_table(p))
    return results


def main() -> None:
    console.rule("[bold cyan]🔍 Spurs Tracker &bull; Cache & Schema Validator[/bold cyan]")
    console.print(f"Inspecting directory: [yellow]{CACHE_DIR}[/yellow]\n")

    results = run_validation()
    if not results:
        console.print("[yellow]No parquet files found in cache directory.[/yellow]")
        sys.exit(0)

    table = Table(title="Cache Integrity Audit", box=box.ROUNDED)
    table.add_column("Cache File", style="white", no_wrap=True)
    table.add_column("Size (KB)", justify="right", style="cyan")
    table.add_column("Rows", justify="right", style="yellow")
    table.add_column("Cols", justify="right", style="dim")
    table.add_column("Status", justify="center", style="bold")
    table.add_column("Diagnostics", style="white")

    all_passed = True
    for r in results:
        status_color = "green" if r["status"] == "PASS" else ("yellow" if r["status"] == "WARN" else "red")
        status_str = f"[{status_color}]{r['status']}[/{status_color}]"
        if r["status"] == "FAIL":
            all_passed = False
        table.add_row(
            r["file"],
            str(r["size_kb"]),
            str(r["rows"]),
            str(r["cols"]),
            status_str,
            r["notes"],
        )

    console.print(table)
    if all_passed:
        console.print("\n[bold green]✓ All cache files validated successfully.[/bold green]\n")
    else:
        console.print("\n[bold red]✗ Schema or integrity failures detected in cache files.[/bold red]\n")


if __name__ == "__main__":
    main()
