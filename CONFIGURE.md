# Configuring Spurs Tracker

## Defaults

`config.py` currently selects `TEAM_ABBR = "SAS"`, `SEASON = 2026`, and `SEASON_TYPE = "Regular Season"`. Season integers refer to the starting year: 2026 becomes `2026-27` through `season_str()`.

Other settings include `SITE_URL` for absolute share-image URLs, `CACHE_DIR` (`data/cache/`), `OUTPUT_DIR` (`docs/`), NBA browser headers, timeout, and request delay. Preserve the required headers and at least 0.6 seconds between Stats API requests.

## Refresh the current site

Activate `.spursEnv` and install dependencies as described in [README.md](README.md), then run:

```bash
python pipeline.py --team SAS --season 2026 --refresh
python -m pytest
```

This incrementally fetches game data and refreshes league ratings, the schedule, and next-opponent player statistics before rebuilding the site. Check fallback warnings and the latest cached game date: a successful build alone does not establish data freshness.

Use `python pipeline.py --skip-fetch` to rebuild existing caches. For a full boxscore replacement, run `python fetch.py --team SAS --season 2026 --refresh --league`, then rebuild with the pipeline. Standalone fetching does not refresh the schedule or next-opponent player cache.

## Other teams and seasons

```bash
python fetch.py --list-teams
python fetch.py --team GSW --season 2024
python report.py --team GSW --season 2024
python viz_report.py --team GSW --season 2024
```

CLI flags override defaults for that command. All 30 teams are registered, but specialized Spurs features and some JSON fields remain Spurs-specific; changing the default team is not a complete rebrand.

Registered pages for the configured team and season use stable filenames. Other builds use suffixes such as `dashboard_GSW_2024.html`. The complete configured-site build, including landing page, roster/player pages, and share images, runs through `pipeline.py`.

`fetch.py --preseason` and `fetch.py --playoffs` use separate season-type caches. The master pipeline uses regular-season data.

## Automation and hosting

`.github/workflows/pipeline.yml` runs at 05:00 UTC using `config.py` defaults. Scheduled runs rebuild caches; its manual `refresh_remote` input enables remote ingestion. It runs tests and commits pages plus cache snapshots.

The older `.github/workflows/refresh.yml` runs at 12:00 UTC. Repository variables `TEAM_ABBR` and `SEASON` affect only its fetch step, with fallbacks SAS/2025. Its build step is hardcoded to SAS/2025 and it commits only `docs/`. Repository variables do not change the master workflow's defaults.

Both schedules stay fixed in UTC through daylight-saving changes. Local builds update files only; publishing uses the repository's static-hosting deployment process. Keep `SITE_URL` consistent with the public hosting address.
