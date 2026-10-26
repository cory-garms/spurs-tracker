# Project Rules & Agent Guidelines — NBA Team Tracker (`spurs_tracker`)

> [!IMPORTANT]
> **Core Directive — Execution Constraints**:
> - **No Background Execution**: NEVER run terminal commands in the background or launch background tasks.
> - **No Timers / Schedules**: NEVER use background timers or schedule tools (`schedule`, `sleep` loops, etc.).
> - **Synchronous Foreground Execution Only**: Any terminal command must be executed in the foreground with explicit user confirmation/approval where required, waiting synchronously for completion.
> - **No Unrequested Code Runs**: Do not execute scripts or commands unless explicitly requested or approved by the user.

---

## 🚀 1. Project Overview & Environment

- **Repository**: `spurs_tracker` (San Antonio Spurs NBA Performance & Analytics Suite)
- **Primary Target**: San Antonio Spurs (`TEAM_ID = 1610612759`, `TEAM_ABBR = "SAS"`)
- **Virtual Environment**: `.spursEnv` (Python 3.10+)
- **Key Dependencies**: `pandas`, `pyarrow`, `rich`, `plotly`, `requests`, `tenacity`
- **Motto / Identity**: *"Pound the Rock"* (Jacob Riis Stonecutter Creed)

---

## 🏗️ 2. Repository Architecture & Component Responsibilities

```
spurs_tracker/
├── config.py              # Configuration defaults (Team ID, season, paths, NBA API headers)
├── fetch.py               # Data ingestion CLI (fetches from stats.nba.com into parquet cache)
├── report.py              # Rich terminal dashboard CLI
├── viz_report.py          # Interactive Plotly HTML dashboard & PNG export CLI
├── .agents/
│   └── AGENTS.md          # Agent rules, constraints, and repository guidance
├── client/
│   └── nba_client.py      # Rate-limited wrapper around stats.nba.com/stats with browser headers
├── data/
│   ├── schema.py          # PyArrow/Pandas DataFrame schemas & type casting
│   ├── roster.py          # Roster management & active player tracking
│   ├── fetcher.py         # Multi-table parquet cache orchestrator
│   └── cache/             # Auto-generated parquet cache files
├── analysis/
│   ├── standings.py       # Win%, Net Rating, Pythagorean/expected wins, pace, conference rank
│   ├── offense.py         # Offensive rating, True Shooting %, eFG%, shot distribution, hot/cold
│   ├── defense.py         # Defensive rating, opponent shot quality, rim frequency allowed
│   ├── wemby.py           # Victor Wembanyama Defensive & Gravity Lab (rim deterrence, stocks, on/off)
│   ├── rodeo.py           # Rodeo Road Trip split tracker (Feb fatigue vs historical road trips)
│   ├── beautiful_game.py  # Ball movement index: passes per poss, assist points created, hockey assists
│   ├── clutch.py          # Clutch splits (last 5 min, score within 5 pts)
│   ├── players.py         # Individual player profiles, scoring leaderboards, rotation pairs
│   ├── streaks.py         # Win/loss streaks, margin distribution, home/road splits
│   └── history.py         # Multi-decade franchise context (1999–present championship standard)
├── viz/
│   ├── theme.py           # Single source of truth: Silver & Black + Fiesta design system & nav
│   ├── charts.py          # Plotly figure builders adhering strictly to viz/theme.py
│   ├── dashboard.py       # Responsive HTML dashboard generator
│   └── exports.py         # Static file exporter (HTML / PNG)
├── blog/
│   └── posts.py           # Dynamic notebook essays evaluating statistics at build time
└── tests/
    ├── conftest.py        # Shared fixtures, simulated NBA games, and mock clients
    ├── test_navigation.py # Navigation registry integrity, mode grouping, valid file targets
    └── test_theme.py      # Theme contrast, categorical palettes, CSS validation
```

---

## 💾 3. Data Ingestion & Caching Conventions

1. **Parquet Caching Strategy**:
   - Data stored in `data/cache/` using Parquet format for sub-millisecond loading and low disk footprint.
   - Cache keys strictly follow the naming scheme: `{table}_{team_id}_{season}.parquet` (e.g., `games_1610612759_2025.parquet`).
2. **API Interaction & Throttling**:
   - All NBA Stats API calls must pass through `NBAClient` in `client/nba_client.py`.
   - **MANDATORY**: Include legitimate browser headers (`User-Agent`, `Referer`, `x-nba-stats-origin`, `x-nba-stats-token`) or NBA stats endpoints will return 403 or hang indefinitely.
   - Maintain `REQUEST_DELAY` throttling (>= 0.60s) and `tenacity` exponential backoff retries.
3. **Data Integrity & Safe Calculations**:
   - Standardize statistical formulas:
     - TS% = PTS / (2 * (FGA + 0.44 * FTA))
     - eFG% = (FGM + 0.5 * 3PM) / FGA
     - Pace = 48 * (Possessions / Minutes)
   - Prevent division-by-zero errors across all rate calculations by returning `0.0` or `NaN` appropriately.

---

## 📊 4. Analytical Standards & Spurs Core Metrics

- **The Wemby Factor**:
  - Rim protection deterrence delta: opponent FG% inside 6 feet when contested by Wembanyama vs season average.
  - "Stocks" (Steals + Blocks) per 36 minutes and on-court defensive rating differential.
- **Rodeo Road Trip (RRT) Split**:
  - Automatically segment regular season games into Pre-RRT, Active RRT (February), and Post-RRT splits.
  - Compare current RRT performance against historical Spurs road trips (2003–present).
- **The "Beautiful Game" Metric**:
  - Pass tracking: assist-to-turnover ratio, secondary assists, assist points created per 100 possessions.
- **Hot / Cold Classification**:
  - HOT: Last-5-game True Shooting % is >= +5.0% above season average.
  - COLD: Last-5-game True Shooting % is <= -5.0% below season average.

---

## 🎨 5. User Interface & Reporting Guidelines

- **Single Source of Truth (`viz/theme.py`)**:
  - **NEVER** hardcode generic `#0e1117` GitHub dark mode or default browser fonts.
  - Primary Court Background: `#0B0E11` (Deep Court Black).
  - Cards & Plots: `#161A1F` (Silver Slate), `#1D232A` (Shadow Black).
  - Spurs Colors: `#C4CED4` (Spurs Silver), `#8A9399` (Spurs Steel), `#F6F8FA` (Chalk White).
  - Vintage Fiesta Accents: `#00B2A9` (Fiesta Teal), `#EF426F` (Fiesta Fuschia), `#FF8200` (Fiesta Rowdy Orange).
  - Typography: Google Fonts `Barlow Condensed`, `Teko`, `Share Tech Mono`, `Graduate`.
- **Navigation & Dual Mode**:
  - Dual modes in navbar: `🏀 Court Intelligence` (season overview, player tracking, Wemby lab) vs `🎲 Props & Market Intelligence` (player lines, matchups).
  - Strict compliance with `tests/test_navigation.py` — every page registered in `theme.PAGES` must exist and match registry order.
- **Terminal Output**: Use `rich` Console, Tables, and Panels for clean presentation in `report.py`.
- **Links & Markdown**: Always use GitHub-style Markdown links for file references (e.g., `[theme.py](file:///path/to/theme.py)`).
