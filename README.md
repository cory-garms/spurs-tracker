# spurs-tracker

NBA analytics suite for the San Antonio Spurs — built as a public portfolio demo for [corygarms.com](https://corygarms.com).

Mirrors the architecture of [sox-tracker](https://github.com/cgarms/sox-tracker) (MLB Red Sox) with NBA-specific adaptations.

---

## What it does

Fetches data from the **NBA Stats API** (free, no key required), caches it as Parquet files, and produces:

- **Terminal dashboard** — Rich-formatted tables via `report.py`
- **Interactive HTML dashboard** — 9 Plotly charts via `viz_report.py`
- **GitHub Actions daily refresh** — auto-fetches and commits updated data at 8 AM ET

---

## Quick start

```bash
# Install
pip install -r requirements.txt

# Fetch a complete season (2024-25)
python fetch.py --team SAS --season 2024

# Terminal dashboard
python report.py --team SAS --season 2024

# Interactive HTML dashboard
python viz_report.py --team SAS --season 2024 --open
```

---

## CLI reference

### `fetch.py`

```
python fetch.py                          # SAS, current season
python fetch.py --team GSW --season 2024 # switch team / season
python fetch.py --refresh                # force re-fetch (ignore cache)
python fetch.py --list-teams             # show all 30 team abbreviations
```

### `report.py`

```
python report.py                         # all sections
python report.py --section overview
python report.py --section offense
python report.py --section defense
python report.py --section players
python report.py --section streaks
python report.py --section standings
```

### `viz_report.py`

```
python viz_report.py                     # build HTML dashboard
python viz_report.py --open              # build + open in browser
python viz_report.py --history           # include historical win% chart
python viz_report.py --pace 2014 2016    # overlay past seasons
python viz_report.py --png               # export PNGs (requires kaleido)
```

---

## Dashboard sections

| # | Section | Data |
|---|---|---|
| 1 | Season Timeline (cumulative W-L) | games |
| 2 | Rolling Win% (5-game, 10-game) | games |
| 3 | Score Margin per Game | games |
| 4 | Streak Timeline | games |
| 5 | Scoring Trend (rolling pts + opp pts) | games |
| 6 | Player Stats Heatmap (z-score) | player_game_log |
| 7 | Hot / Cold Tracker | player_game_log |
| 8 | Shot Efficiency (USG% vs TS%) | player_game_log |
| 9 | Defensive Rating Trend | games |

---

## Project structure

```
spurs_tracker/
├── config.py              # team selection, paths, API constants
├── fetch.py               # CLI: fetch + cache
├── report.py              # CLI: terminal dashboard
├── viz_report.py          # CLI: HTML dashboard
├── CONFIGURE.md           # switching to other teams
├── requirements.txt
├── client/
│   └── nba_client.py      # NBA Stats API wrapper
├── data/
│   ├── schema.py          # canonical DataFrame schemas
│   ├── roster.py          # roster fetch + caching
│   ├── fetcher.py         # orchestrator: fetch all → cache → load
│   └── cache/             # .parquet files (gitignored)
├── analysis/
│   ├── standings.py       # record, splits, pythagorean, conference standings
│   ├── offense.py         # scoring, shooting, hot/cold, starter/bench
│   ├── defense.py         # defensive ratings, player defense stats
│   ├── players.py         # usage, double-doubles, consistency
│   ├── streaks.py         # win/loss streaks, back-to-backs, monthly splits
│   └── history.py         # multi-season records, pace comparison
├── viz/
│   ├── charts.py          # individual Plotly chart functions (dark theme)
│   ├── dashboard.py       # combined HTML dashboard builder
│   └── exports.py         # save_html(), save_png()
├── notebooks/
│   └── demo.ipynb         # interactive walkthrough
└── .github/workflows/
    └── refresh.yml        # daily cron data refresh
```

---

## Switching teams

See [CONFIGURE.md](CONFIGURE.md) for full instructions. The short version:

```bash
python fetch.py --team LAL --season 2024
python report.py --team LAL --season 2024
```

Supports all 30 NBA teams. See `python fetch.py --list-teams`.

---

## Data source

All data comes from the public [NBA Stats API](https://stats.nba.com/stats/).
No API key required. A 0.6-second delay between requests respects rate limits.

---

## GitHub Actions setup

1. Push this repo to GitHub
2. Go to **Settings → Variables → Actions**
3. Add `TEAM_ABBR` (e.g. `SAS`) and `SEASON` (e.g. `2025`)
4. The workflow runs daily at 8 AM ET

---

*Built with Python, Pandas, Plotly, and Rich.*
