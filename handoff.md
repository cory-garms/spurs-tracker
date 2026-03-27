# Spurs Tracker — Agent Handoff & Blueprint

**Project owner:** Cory Garms (corygarms.com)
**Reference project:** `sox-tracker` (MLB Red Sox tracker — same repo owner, same portfolio - https://github.com/cory-garms/sox-tracker)
**Goal:** Build an analogous suite for the San Antonio Spurs (NBA), reusing the same architecture and 5-day sprint structure.

---

## Context & Design Philosophy

This project is a **public portfolio code demo** — clean, readable, well-structured Python that shows off data engineering and analytics skills. Follow these priorities in order:

1. Correctness over cleverness
2. Minimal dependencies (no heavy ML frameworks)
3. Consistent style throughout — follow the sox-tracker patterns closely
4. Interactive Plotly HTML dashboard as the primary deliverable
5. Keep everything configurable for other NBA teams (30-team support)

**Lessons learned from sox-tracker:**

- Cache everything as `.parquet` files immediately — raw API responses are slow and rate-limited
- Define canonical DataFrame schemas upfront (`data/schema.py`) and enforce them at fetch time
- Separate concerns cleanly: `client/` → raw HTTP, `data/` → fetch/cache/schema, `analysis/` → stats logic, `viz/` → charts
- The GitHub Actions daily refresh workflow is a portfolio highlight — build it
- **Plotly CDN pitfall**: Do NOT hardcode a CDN version string in the dashboard HTML template. Use `include_plotlyjs="cdn"` for the first figure div via `pio.to_html()` so the version always matches the installed package. Hardcoding caused a rendering regression in sox-tracker (charts rendered blank).
- Test with a past season first (`--season 2024`) since the current season may have incomplete data early on
- Rich terminal output (`rich` library) makes the CLI polished and demo-friendly

---

## Data Sources

### Primary: NBA Stats API

Base URL: `https://stats.nba.com/stats/`

- **Free, no auth required**, but requires specific headers to avoid 403s:
  ```python
  headers = {
      "User-Agent": "Mozilla/5.0",
      "Referer": "https://www.nba.com/",
      "Accept": "application/json",
      "Accept-Language": "en-US,en;q=0.9",
      "x-nba-stats-origin": "stats",
      "x-nba-stats-token": "true",
  }
  ```
- Rate-limit friendly: add `time.sleep(0.6)` between requests
- Key endpoints (all return `{resultSets: [{headers, rowSet}]}` structure):

| Endpoint | Purpose |
|---|---|
| `leaguegamefinder?TeamID=&Season=&SeasonType=` | All team game results |
| `teamgamelog?TeamID=&Season=&SeasonType=` | Team game log (pts, reb, ast per game) |
| `boxscoretraditionalv2?GameID=` | Full player boxscore |
| `boxscoreadvancedv2?GameID=` | Advanced stats (TS%, USG%, ORtg, DRtg) |
| `leaguedashteamstats?Season=&PerMode=PerGame` | All-team stat rankings |
| `leaguedashplayerstats?Season=&TeamID=` | Player season averages |
| `leaguestandingsv3?Season=&SeasonType=` | Conference/division standings |
| `playergamelogs?PlayerID=&Season=` | Player game-by-game log |
| `commonteamroster?TeamID=&Season=` | Current roster |
| `shotchartdetail?TeamID=&Season=` | Shot chart data |

### Secondary: Basketball Reference (scraping fallback)

Use only if NBA Stats API is missing historical data. `basketball_reference_web_scraper` PyPI package or direct HTML scraping. Avoid for live/current data.

### San Antonio Spurs team constants

```python
TEAM_ID   = 1610612759   # official NBA Stats API team ID
TEAM_ABBR = "SAS"
TEAM_NAME = "San Antonio Spurs"
SEASON    = "2025-26"    # NBA uses "YYYY-YY" format — important difference from MLB
```

---

## Project Structure

Mirror sox-tracker exactly:

```
spurs_tracker/
├── config.py                  # team selection, paths, API constants
├── fetch.py                   # CLI: fetch + cache all data
├── report.py                  # CLI: terminal dashboard (Rich)
├── viz_report.py              # CLI: build interactive HTML dashboard
├── CONFIGURE.md               # instructions for switching teams
├── requirements.txt
├── .gitignore
├── .github/
│   └── workflows/
│       └── refresh.yml        # daily cron data refresh + commit
├── client/
│   └── nba_client.py          # NBA Stats API wrapper (retry, headers, rate-limit)
├── data/
│   ├── schema.py              # canonical DataFrame schemas
│   ├── roster.py              # roster fetch + position groups
│   ├── fetcher.py             # orchestrator: fetch all → cache → load
│   └── cache/                 # .parquet files (gitignored)
├── analysis/
│   ├── standings.py           # season record, conference standings, pace
│   ├── offense.py             # scoring, shooting efficiency, leaderboards
│   ├── defense.py             # defensive ratings, opponent stats, steals/blocks
│   ├── players.py             # player trends, hot/cold, usage
│   ├── streaks.py             # win/loss streaks, series patterns, monthly splits
│   └── history.py             # multi-season trends, records within reach
├── viz/
│   ├── charts.py              # individual Plotly chart functions (dark theme)
│   ├── dashboard.py           # combined HTML dashboard (see CDN pitfall above)
│   └── exports.py             # save_html(), save_png()
└── notebooks/
    └── demo.ipynb             # interactive walkthrough
```

---

## Canonical DataFrame Schemas

Define these in `data/schema.py` and enforce them at fetch time (same pattern as sox-tracker's `enforce_schema()`).

### `games` — one row per game played

| Column | Type | Notes |
|---|---|---|
| `game_id` | str | NBA game ID (e.g. "0022401001") |
| `game_date` | datetime64 | |
| `home_away` | str | "H" or "A" |
| `opponent_id` | int | |
| `opponent_abbr` | str | |
| `result` | str | "W" or "L" |
| `pts` | int | team points |
| `opp_pts` | int | opponent points |
| `margin` | int | pts - opp_pts |
| `pace` | float | possessions per 48 min |
| `ortg` | float | offensive rating |
| `drtg` | float | defensive rating |
| `nrtg` | float | net rating |
| `status` | str | "Final" or "Scheduled" |
| `season` | str | "2025-26" |

### `player_game_log` — one row per player per game

| Column | Type | Notes |
|---|---|---|
| `game_id` | str | |
| `game_date` | datetime64 | |
| `player_id` | int | |
| `player_name` | str | |
| `min` | float | minutes played |
| `pts` | int | |
| `reb` | int | total rebounds |
| `ast` | int | |
| `stl` | int | |
| `blk` | int | |
| `tov` | int | turnovers |
| `pf` | int | personal fouls |
| `fgm` / `fga` / `fg_pct` | float | |
| `fg3m` / `fg3a` / `fg3_pct` | float | |
| `ftm` / `fta` / `ft_pct` | float | |
| `plus_minus` | int | |
| `ts_pct` | float | true shooting % (computed) |
| `usg_pct` | float | from advanced boxscore |

### `roster` — current season roster

| Column | Type |
|---|---|
| `player_id` | int |
| `player_name` | str |
| `position` | str |
| `position_group` | str | "G" / "F" / "C" |
| `jersey_number` | str |
| `years_of_experience` | int |

---

## Day-by-Day Sprint Plan

### Day 1 — Foundation: Client, Schema, Fetcher, CLI

**Deliverables:**
- `config.py` with all 30 NBA teams and IDs
- `client/nba_client.py` with retry logic (tenacity), correct headers, rate-limit sleep
- `data/schema.py` with the 3 canonical schemas above + `enforce_schema()`
- `data/roster.py` — `fetch_roster()`, `get_position_group()`, `player_id_map()`
- `data/fetcher.py` — `Fetcher` class: `fetch_all()`, `fetch_games()`, `fetch_player_logs()`, `load()`
- `fetch.py` CLI — `--team`, `--season`, `--refresh`, `--list-teams`, `--verbose`
- `requirements.txt`, `.gitignore`, `CONFIGURE.md`

**Key implementation notes:**

```python
# NBA season string format — always "YYYY-YY"
def season_str(year: int) -> str:
    return f"{year}-{str(year + 1)[-2:]}"  # 2025 → "2025-26"

# NBA Stats API response parsing (all endpoints share this structure)
def _parse(response_json: dict, result_set_index: int = 0) -> pd.DataFrame:
    rs = response_json["resultSets"][result_set_index]
    return pd.DataFrame(rs["rowSet"], columns=[c.lower() for c in rs["headers"]])
```

**`fetch.py` usage target:**
```bash
python fetch.py --team SAS --season 2025   # fetches 2025-26 season
python fetch.py --refresh                  # force re-fetch ignoring cache
python fetch.py --list-teams               # print all 30 teams
```

---

### Day 2 — Analysis: Standings, Offense, Defense

**Deliverables:**
- `analysis/standings.py`
- `analysis/offense.py`
- `analysis/defense.py`

#### `analysis/standings.py`

```python
# Key functions:
def season_record(games) -> dict:
    # wins, losses, win_pct, home_w/l, away_w/l, last_10_w/l, last_20_w/l
    # net_rtg (mean nrtg over Final games), avg_margin

def pace_projection(wins, losses) -> tuple[int, int]:
    # project to 82 games (not 162 like MLB)

def pythagorean_record(games, exponent=13.91) -> dict:
    # NBA Pythagorean uses exponent ~13.91
    # pyth_win_pct = pts^exp / (pts^exp + opp_pts^exp)

def conference_standings(season) -> pd.DataFrame:
    # live from leaguestandingsv3 endpoint

def print_overview(console, games, ...) -> None:
```

#### `analysis/offense.py`

```python
# Key functions:
def team_offense_summary(player_logs, games) -> dict:
    # pts_per_game, fg_pct, fg3_pct, ft_pct, ts_pct, ast_per_game
    # oreb_pct, tov_pct, pace, ortg

def player_season_averages(player_logs, min_games=10) -> pd.DataFrame:
    # per-game averages for all players

def scoring_leaderboard(player_logs, min_games=10) -> pd.DataFrame:
    # sorted by pts, includes pts/reb/ast/ts_pct/usg_pct

def hot_cold_summary(player_logs, windows=[5, 10]) -> pd.DataFrame:
    # NOTE: use 5 and 10 game windows (not 7/15 like MLB) — NBA plays more frequently
    # delta = last_5_pts_avg - season_pts_avg

def lineup_analysis(player_logs) -> pd.DataFrame:
    # starting 5 vs bench splits

def rolling_stats(player_logs, player_id, window=10) -> pd.DataFrame:
    # rolling pts/reb/ast for trend charts

def fourth_quarter_scoring(player_logs) -> pd.DataFrame:
    # clutch performance — requires Q4 boxscore data
```

#### `analysis/defense.py`

```python
# Key functions:
def team_defense_summary(games) -> dict:
    # drtg, opp_pts_per_game, opp_fg_pct, steals_per_game, blocks_per_game

def player_defense_stats(player_logs) -> pd.DataFrame:
    # stl, blk, dreb, pf, plus_minus per game

def defensive_ratings_trend(games, window=10) -> pd.DataFrame:
    # rolling drtg for trend chart
```

---

### Day 3 — Analysis: Players, Streaks, History

**Deliverables:**
- `analysis/players.py`
- `analysis/streaks.py`
- `analysis/history.py`

#### `analysis/players.py`

This is the NBA equivalent of splitting offense between team and individual focus.

```python
def player_usage_breakdown(player_logs) -> pd.DataFrame:
    # usg_pct, ts_pct, ast_ratio, tov_ratio

def double_double_tracker(player_logs) -> pd.DataFrame:
    # count double-doubles and triple-doubles per player

def player_consistency_score(player_logs, player_id) -> float:
    # std dev of scoring — lower = more consistent

def starter_bench_split(player_logs) -> pd.DataFrame:
    # pts/reb/ast/ts_pct split by starting vs. bench

def player_vs_opponent_splits(player_logs) -> pd.DataFrame:
    # per-player averages grouped by opponent (find favorable matchups)
```

#### `analysis/streaks.py`

```python
# Mirrors sox-tracker/analysis/streaks.py closely
def current_streak(games) -> tuple[str, int]:       # ("W", 4) or ("L", 2)
def longest_streak(games, result="W") -> int:
def streak_timeline(games) -> pd.DataFrame:          # cumulative streak tracking
def series_results(games) -> pd.DataFrame:           # back-to-back game records
def back_to_back_record(games) -> dict:              # NBA-specific: lots of B2Bs
def monthly_record(games) -> pd.DataFrame:
def scoring_drought_games(games, threshold=100) -> pd.DataFrame:
    # games where team scored under threshold (NBA blowout context)
```

**NBA-specific streak note:** Back-to-back games are especially meaningful in the NBA. `back_to_back_record()` should flag games that are the 2nd of a B2B and compute W-L separately.

#### `analysis/history.py`

```python
# Notable seasons for reference
NOTABLE_SEASONS: dict[str, dict[str, str]] = {
    "SAS": {
        "1998-99": "WS Champs (50W lockout)",
        "2002-03": "WS Champs (60W)",
        "2004-05": "WS Champs (59W)",
        "2006-07": "WS Champs (58W)",
        "2013-14": "WS Champs (62W)",
        "2015-16": "67W — best regular season",
    },
    "GSW": {"2015-16": "73W record", "2017-18": "WS Champs (58W)"},
}

def fetch_season_records(team_id, start_year=2000, ...) -> pd.DataFrame:
    # wins, losses, win_pct, net_rtg, pace, div_rank
    # Cache as history_{team_id}.parquet

def records_within_reach(current_games, historical, team_abbr) -> list[dict]:
    # Most wins in a season, best win%, worst wins (project to 82 games)

def build_pace_comparison(current_games, team_id, reference_years) -> dict:
    # Load cached game logs for reference seasons
```

---

### Day 4 — Visualization

**Deliverables:**
- `viz/charts.py` — all Plotly chart functions
- `viz/dashboard.py` — combined HTML dashboard
- `viz/exports.py` — save helpers

**Dark theme constants** (same as sox-tracker — ensures visual consistency across portfolio):

```python
_BG        = "#0e1117"
_PAPER_BG  = "#161b22"
_GRID      = "#30363d"
_TEXT      = "#e6edf3"
_GREEN     = "#3fb950"
_RED       = "#f85149"
_BLUE      = "#58a6ff"
_YELLOW    = "#d29922"
_DIM       = "#8b949e"
_SPURS_SILVER = "#c4ced4"   # Spurs brand color
_SPURS_BLACK  = "#000000"   # Spurs brand color
```

**Charts to build in `viz/charts.py`:**

| Function | Chart type | Data |
|---|---|---|
| `season_timeline(games, team_name)` | Line: cumulative W-L | games |
| `rolling_win_pct_chart(games, team_name, windows=[5,10])` | Line | games |
| `score_margin_chart(games, team_name)` | Bar (pos/neg colored) | games |
| `streak_timeline_chart(streak_df, team_name)` | Bar (signed streak) | streak_timeline() |
| `scoring_trend_chart(games, team_name, window=10)` | Line: pts + opp_pts rolling | games |
| `player_scoring_leaderboard(player_logs, team_name)` | Heatmap (z-score cols) | player_logs |
| `hot_cold_chart(hc_df, team_name)` | Horizontal bar | hot_cold_summary() |
| `shot_efficiency_chart(player_logs, team_name)` | Scatter: usg_pct vs ts_pct | player_logs |
| `defensive_rating_trend(games, team_name)` | Line: rolling drtg | games |
| `multi_season_win_pct(historical, team_name)` | Bar + annotations | fetch_season_records() |
| `pace_comparison_chart(games, ref_seasons, team_name)` | Multi-line | build_pace_comparison() |

**`viz/dashboard.py` — CDN fix (CRITICAL):**

```python
# CORRECT pattern — do NOT hardcode a CDN version string
for i, (title, fig, height) in enumerate(figures):
    include_js = "cdn" if i == 0 else False
    fig.update_layout(height=height)
    chart_div = pio.to_html(fig, full_html=False, include_plotlyjs=include_js, div_id=div_id)
```

Dashboard sections (top to bottom):
1. Season Timeline
2. Rolling Win%
3. Score Margin per Game
4. Streak Timeline
5. Scoring Trend (pts + opp_pts rolling)
6. Player Scoring Leaderboard (heatmap)
7. Hot / Cold Tracker
8. Shot Efficiency (usg% vs TS%)
9. Defensive Rating Trend

**`viz_report.py` CLI target:**
```bash
python viz_report.py                           # SAS 2025-26
python viz_report.py --team LAL --season 2024
python viz_report.py --history                 # include multi-season chart
python viz_report.py --pace 2014 2016          # overlay comparison seasons
python viz_report.py --open                    # open in browser when done
```

---

### Day 5 — Polish: report.py, GitHub Actions, Notebook, README

**Deliverables:**
- `report.py` — full terminal dashboard using Rich
- `.github/workflows/refresh.yml` — daily data refresh
- `notebooks/demo.ipynb` — interactive walkthrough
- `README.md`, `CONFIGURE.md`

#### `report.py` sections

Mirror sox-tracker's `report.py` dispatcher:

```bash
python report.py                        # all sections
python report.py --section overview
python report.py --section offense
python report.py --section defense
python report.py --section players
python report.py --section streaks
python report.py --section standings
python report.py --team GSW --season 2024
```

Each section calls a corresponding `print_*()` function from the analysis modules. Use Rich `Table`, `Panel`, and color coding throughout (green for good, red for bad, yellow for neutral).

#### `refresh.yml`

```yaml
name: Daily Data Refresh
on:
  schedule:
    - cron: "0 12 * * *"   # 8 AM ET, after overnight games are final
  workflow_dispatch:
jobs:
  refresh:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip
      - run: pip install -r requirements.txt
      - run: python fetch.py --team ${{ vars.TEAM_ABBR || 'SAS' }} --season ${{ vars.SEASON || '2025' }} --refresh
      - run: python viz_report.py --team ${{ vars.TEAM_ABBR || 'SAS' }} --season ${{ vars.SEASON || '2025' }}
      - run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add data/cache/ output/
          git diff --cached --quiet || git commit -m "chore: auto-refresh data $(date -u +%Y-%m-%d)"
          git push
```

**Cron time note:** NBA games typically end by 11 PM ET. 8 AM ET (12:00 UTC) gives enough buffer for box scores to be finalized and for data to be available via the API.

---

## NBA vs MLB Key Differences

These are the places where you cannot blindly copy sox-tracker patterns:

| Concern | MLB (sox-tracker) | NBA (spurs_tracker) |
|---|---|---|
| Season string | `2025` (int) | `"2025-26"` (str) |
| Season length | 162 games | 82 games |
| Rolling windows | 7, 15 games | 5, 10 games |
| Pythagorean exp | 1.83 (default) | 13.91 |
| Pace projection | `w / g * 162` | `w / g * 82` |
| Conference structure | AL/NL → divisions | East/West → divisions |
| "Pitching" analog | pitching.py | defense.py (team drtg) |
| Box score endpoints | One per team per game | Separate advanced endpoint |
| Data headers | camelCase JSON | ALL_CAPS in NBA API |
| B2B games | Rare, not significant | Critical to track separately |
| API rate limits | Relaxed | Strict — must sleep between calls |

---

## `config.py` Template

```python
from pathlib import Path

TEAM_ABBR = "SAS"
SEASON    = 2025          # pass to season_str() → "2025-26"
SEASON_TYPE = "Regular Season"

BASE_DIR   = Path(__file__).parent
CACHE_DIR  = BASE_DIR / "data" / "cache"
OUTPUT_DIR = BASE_DIR / "output"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

NBA_STATS_BASE = "https://stats.nba.com/stats"
NBA_API_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Referer": "https://www.nba.com/",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "x-nba-stats-origin": "stats",
    "x-nba-stats-token": "true",
    "Connection": "keep-alive",
}

HISTORY_START = 1999   # first Spurs championship era

TEAMS = {
    "ATL": {"id": 1610612737, "name": "Atlanta Hawks",          "conf": "East", "div": "Southeast"},
    "BOS": {"id": 1610612738, "name": "Boston Celtics",         "conf": "East", "div": "Atlantic"},
    "BKN": {"id": 1610612751, "name": "Brooklyn Nets",          "conf": "East", "div": "Atlantic"},
    "CHA": {"id": 1610612766, "name": "Charlotte Hornets",      "conf": "East", "div": "Southeast"},
    "CHI": {"id": 1610612741, "name": "Chicago Bulls",          "conf": "East", "div": "Central"},
    "CLE": {"id": 1610612739, "name": "Cleveland Cavaliers",    "conf": "East", "div": "Central"},
    "DAL": {"id": 1610612742, "name": "Dallas Mavericks",       "conf": "West", "div": "Southwest"},
    "DEN": {"id": 1610612743, "name": "Denver Nuggets",         "conf": "West", "div": "Northwest"},
    "DET": {"id": 1610612765, "name": "Detroit Pistons",        "conf": "East", "div": "Central"},
    "GSW": {"id": 1610612744, "name": "Golden State Warriors",  "conf": "West", "div": "Pacific"},
    "HOU": {"id": 1610612745, "name": "Houston Rockets",        "conf": "West", "div": "Southwest"},
    "IND": {"id": 1610612754, "name": "Indiana Pacers",         "conf": "East", "div": "Central"},
    "LAC": {"id": 1610612746, "name": "LA Clippers",            "conf": "West", "div": "Pacific"},
    "LAL": {"id": 1610612747, "name": "Los Angeles Lakers",     "conf": "West", "div": "Pacific"},
    "MEM": {"id": 1610612763, "name": "Memphis Grizzlies",      "conf": "West", "div": "Southwest"},
    "MIA": {"id": 1610612748, "name": "Miami Heat",             "conf": "East", "div": "Southeast"},
    "MIL": {"id": 1610612749, "name": "Milwaukee Bucks",        "conf": "East", "div": "Central"},
    "MIN": {"id": 1610612750, "name": "Minnesota Timberwolves", "conf": "West", "div": "Northwest"},
    "NOP": {"id": 1610612740, "name": "New Orleans Pelicans",   "conf": "West", "div": "Southwest"},
    "NYK": {"id": 1610612752, "name": "New York Knicks",        "conf": "East", "div": "Atlantic"},
    "OKC": {"id": 1610612760, "name": "Oklahoma City Thunder",  "conf": "West", "div": "Northwest"},
    "ORL": {"id": 1610612753, "name": "Orlando Magic",          "conf": "East", "div": "Southeast"},
    "PHI": {"id": 1610612755, "name": "Philadelphia 76ers",     "conf": "East", "div": "Atlantic"},
    "PHX": {"id": 1610612756, "name": "Phoenix Suns",           "conf": "West", "div": "Pacific"},
    "POR": {"id": 1610612757, "name": "Portland Trail Blazers", "conf": "West", "div": "Northwest"},
    "SAC": {"id": 1610612758, "name": "Sacramento Kings",       "conf": "West", "div": "Pacific"},
    "SAS": {"id": 1610612759, "name": "San Antonio Spurs",      "conf": "West", "div": "Southwest"},
    "TOR": {"id": 1610612761, "name": "Toronto Raptors",        "conf": "East", "div": "Atlantic"},
    "UTA": {"id": 1610612762, "name": "Utah Jazz",              "conf": "West", "div": "Northwest"},
    "WAS": {"id": 1610612764, "name": "Washington Wizards",     "conf": "East", "div": "Southeast"},
}
```

---

## `requirements.txt`

```
requests>=2.31.0
pandas>=2.1.0
pyarrow>=14.0.0
plotly>=5.18.0
rich>=13.7.0
tenacity>=8.2.3
python-dateutil>=2.8.2
```

Same as sox-tracker — no new dependencies needed.

---

## Testing Strategy

1. Start with `--season 2024` (full, complete season available)
2. Verify parquet files land in `data/cache/` after `fetch.py` runs
3. Run `report.py` and check each section renders without errors
4. Run `viz_report.py --open` and visually verify all 9 dashboard charts render
5. If any charts are blank: check Plotly CDN version (see "Lessons Learned" above)
6. Test team switching: `python fetch.py --team GSW --season 2024 && python report.py --team GSW --season 2024`

---

## Git Repo Setup (from sox-tracker experience)

```bash
# 1. Create on GitHub: spurs-tracker (public)
git init
git remote add origin git@github.com:<username>/spurs-tracker.git
git add .
git commit -m "feat: initial project scaffold"
git push -u origin main

# 2. Set GitHub Actions vars (Settings → Variables → Actions)
#    TEAM_ABBR = SAS
#    SEASON    = 2025
```

---

*Blueprint authored from sox-tracker build session — March 2026*
