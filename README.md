# Spurs Tracker

La Tabla Spurs is a San Antonio Spurs analytics site at [porvida.corygarms.com](https://porvida.corygarms.com). Python fetches NBA statistics, caches Parquet snapshots, computes analytics, and generates HTML, JSON, and social preview images without an application server.

## Setup

Use Python 3.10+ in an isolated environment:

```bash
python3 -m venv .spursEnv
source .spursEnv/bin/activate
python -m pip install -r requirements-dev.txt
```

Runtime dependencies are in `requirements.txt`; the development file also installs pytest and HTTP testing helpers. Optional PNG chart exports require Kaleido. An isolated environment avoids conflicts between system pandas and NumPy installations.

## Refresh and build

Defaults in `config.py` are SAS and **2026–27 regular season**. Season arguments use the starting year.

```bash
# Incremental game ingestion, league ratings, schedule, next-opponent stats,
# cache validation, JSON export, complete site, and social generator check.
python pipeline.py --team SAS --season 2026 --refresh

# Rebuild existing caches.
python pipeline.py --team SAS --season 2026 --skip-fetch

# Verify.
python -m pytest
```

The pipeline defaults to cached data. Its `--refresh` enables incremental ingestion; it does not replace all historical boxscores. Remote failures may fall back to existing caches: inspect warnings and verify the latest game date before publishing. Missing league caches may cause build-time analysis to request data even when ingestion is skipped.

Individual entry points:

```bash
# Force a complete boxscore refetch and league ratings refresh.
python fetch.py --team SAS --season 2026 --refresh --league
python report.py --team SAS --season 2026
python viz_report.py --team SAS --season 2026 --open
python fetch.py --list-teams
```

`fetch.py` also supports `--preseason` and `--playoffs`. The master pipeline uses regular-season caches. `viz_report.py` supports `--history`, `--pace 2014 2016`, and optional `--png`; use the master pipeline for the complete landing page, roster/player pages, JSON, and share-image build.

## Site and architecture

The site includes a landing page, season dashboard, roster and individual player pages, Wemby Lab, Rodeo Road Trip splits, props, matchup previews, and data-driven notebook essays. Shared styling, navigation, small-sample notices, and seasonal page visibility live in `viz/theme.py`.

| Location | Responsibility |
| --- | --- |
| `config.py` | Team/season defaults, paths, request settings, public site URL |
| `client/` | NBA Stats HTTP client, browser headers, throttling, retries |
| `data/` | Ingestion, schemas, roster, league ratings, schedule, validation, export |
| `data/cache/` | Versioned current and historical Parquet snapshots |
| `analysis/` | Records, offense/defense, players, predictions, Four Factors, clutch, lineups, Spurs metrics |
| `viz/` | Plotly charts, HTML builders, theme, avatars, share images |
| `blog/`, `posts/` | Generated analytical essays and editorial source material |
| `assets/` | Fonts and supporting visual assets |
| `docs/` | Generated static website, images, and JSON |
| `tests/` | Analysis, navigation, theme, pages, images, and schedule coverage |
| `pipeline.py` | Complete ingestion and site build orchestration |
| `fetch.py`, `report.py`, `viz_report.py`, `social.py` | Individual command-line tools |

Stats come from `stats.nba.com`; schedules come from `cdn.nba.com`. No API key is required. Statistics requests use browser headers, a 0.6-second delay, and retries. Cache names generally follow `{table}_{team_id}_{season}.parquet`; league ratings and schedules use season-only keys.

`docs/data/` contains predictions, Four Factors, roster pulse, clutch, and summary JSON. Cache validation checks readability, empty tables, critical columns, and critical nulls; it does not enforce full schema types. The pipeline requires PASS for every inspected cache in the selected season, including other teams' caches.

All 30 teams are registered for ingestion and basic reporting. Several specialized pages and JSON fields remain Spurs-specific. Current configured pages use stable filenames; historical or alternate-team registered pages receive team/season suffixes. See [CONFIGURE.md](CONFIGURE.md).

## Automation and publishing

A local build updates `docs/`; publishing depends on committing/pushing output and the repository's static-hosting configuration.

Two GitHub Actions workflows currently coexist:

- `pipeline.yml`: daily at **05:00 UTC**, builds the complete site and runs tests, then commits `docs/` and `data/cache/`. Scheduled runs use cached data; manual `refresh_remote` enables remote ingestion. Defaults come from `config.py`.
- `refresh.yml`: daily at **12:00 UTC**, fetches using repository variables `TEAM_ABBR` and `SEASON` (fallback SAS/2025), then builds explicitly for SAS/2025 and commits only `docs/`.

The older workflow therefore does not refresh the configured 2026–27 landing page. UTC schedules shift relative to local time during daylight-saving changes.

`SPURS_BLUEPRINT.md` and `handoff.md` retain historical planning context. This README and the implementation describe the current operating workflow.
