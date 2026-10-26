# 🏀 Project Blueprint: San Antonio Spurs Analytics Suite (`spurs_tracker`)

> **Handoff Document for Future Agent Implementation**  
> *Target Team*: San Antonio Spurs (`TEAM_ID = 1610612759`, `TEAM_ABBR = "SAS"`)  
> *Inspiration*: Boston Red Sox Analytics Suite (`sox_tracker` / *Dirty Water*)  
> *Core Motto*: **"Pound The Rock"** &mdash; *The Stonecutter's Ledger*

---

## 🏛️ 1. Vision, Culture & Design System

Like `sox_tracker` leaned into Fenway's Green Monster, brass manual scoreboards, and vintage ticket-stubs, `spurs_tracker` must reek of San Antonio basketball culture: the five championship banners, the timeless stonecutter creed, the 2014 "Beautiful Game" ball movement, and the modern celestial phenomenon of **Victor Wembanyama**.

### 🎨 Color Palette & Visual Language
- **Primary Turf / Background**: Deep Arena Slate (`#0B0E11` and `#14181D`)
- **Primary Metallic**: Spurs Brushed Silver (`#C4CED4` and `#8A9399`)
- **Accent Chrome**: Clean White (`#F6F8FA`)
- **Court Accent**: Hardwood Honey / Maple (`#D4A373`)
- **Fiesta Vintage Accents** (Subtle badges, highlights, and borders):
  - Fiesta Turquoise: `#00B2A9`
  - Fiesta Fuschia: `#EF426F`
  - Fiesta Mango Orange: `#FF8200`
- **Stonecutter Aesthetic**:
  - Cards framed with crisp silver-dashed borders (`2px dashed #C4CED4`) or subtle Fiesta gradient accents.
  - Ticket stubs styled like Frost Bank Center court-side passes.
  - Subtle granite / stonecutter textured subtle CSS gradients.

### 🔤 Typography (Google Fonts)
- **Display / Headers**: `'Barlow Condensed'`, `'Teko'`, or `'Alfa Slab One'` (Bold, towering, industrial like the Frost Bank Center rafters)
- **Numbers & Data Values**: `'Share Tech Mono'` or `'Space Mono'` (Crisp LED arena scoreboard style)
- **Subheaders & Badges**: `'Graduate'` or `'Oswald'` (Classic collegiate championship tradition)
- **Body & Essays**: Clean, readable modern serif or crisp sans (`Inter` or `Georgia`)

---

## 🏗️ 2. Repository Architecture & Layout

```
spurs_tracker/
├── config.py                 # Spurs TEAM_ID (1610612759), season defaults, colors, API endpoints
├── fetch.py                  # CLI data ingestor (nba_api + The Odds API -> Parquet cache)
├── report.py                 # Rich terminal dashboard CLI
├── viz_report.py             # Plotly interactive dashboard generator
├── wemby_report.py           # Specialized Wembanyama defensive & gravity lab
├── matchup_report.py         # Game-day pre-game intelligence report
├── betting_report.py         # Prop modeler (Wemby blocks/points/stocks)
├── blog_report.py            # Dynamic Notebook generator
├── .agents/
│   └── AGENTS.md             # Execution constraints (Synchronous only, no unrequested runs)
├── client/
│   ├── nba_client.py         # Rate-limited wrapper around stats.nba.com (nba_api) with user-agent rotation
│   └── odds_client.py        # The Odds API props aggregator
├── data/
│   ├── schema.py             # PyArrow/Pandas schemas for box scores, shot logs, tracking
│   ├── roster.py             # Spurs active roster & depth chart manager
│   ├── fetcher.py            # Parquet cache manager (`data/cache/`)
│   └── cache/                # Parquet storage
├── analysis/
│   ├── wemby.py              # Rim deterrence (D-FG% within 6ft), block tracking, gravity metrics
│   ├── ball_movement.py      # "Beautiful Game" metric: passes/possession, secondary assists, paint-to-great
│   ├── lineups.py            # 2-man and 5-man net rating, clutch efficiency
│   ├── rodeo.py              # Historic Rodeo Road Trip split tracker (February road marathon)
│   ├── shot_chart.py         # Hexbin shot efficiency vs. league average
│   └── standings.py          # Western Conference playoff/play-in race, net rating pace
├── viz/
│   ├── theme.py              # Silver, Black & Fiesta design system, nav bar, page registry
│   ├── charts.py             # Plotly figures (shot charts, rolling net rating, defensive radius)
│   └── dashboard.py          # Complete HTML dashboard generator
└── docs/                     # Static site output (hosted on Render / Edge CDN)
    ├── index.html            # Landing page
    ├── dashboard_SAS_2027.html
    ├── wemby_SAS_2027.html
    ├── matchup_SAS_2027.html
    ├── notebook_SAS_2027.html
    ├── rodeo_SAS_2027.html
    └── props_SAS_2027.html
```

---

## ⚡ 3. Key Analytical Engines & Signature Features

### 👽 1. The Wemby Defensive Horizon (`analysis/wemby.py`)
Victor Wembanyama is the singular gravitational force in modern basketball. The site needs tools nobody else builds:
- **Rim Deterrence Delta**: Opponent field goal percentage inside 6 feet when Wemby is on court vs. off court, and vs. the NBA league average.
- **The "Reluctant Pass" Metric**: Quantifying possessions where an opponent drives into the paint, sees Wemby, and turns back out.
- **Stocks Engine**: Tracking combined Steals + Blocks distributions with Poisson confidence intervals.

### 🎯 2. The "Beautiful Game" Ball Movement Engine (`analysis/ball_movement.py`)
Inspired by the 2014 Spurs:
- **Passes Per Possession**: Tracking team ball movement vs. NBA pace.
- **Hockey Assist Rate**: Tracking secondary assists that unlock open corner threes.
- **Paint-Touch-to-Corner-3 Conversion**: How effectively drives result in high-expected-value perimeter looks.

### 🤠 3. The Rodeo Road Trip Tracker (`analysis/rodeo.py`)
Every February, the San Antonio Stock Show & Rodeo kicks the Spurs out of their arena for a gruelling 3-week road trip (8–10 consecutive away games).
- Historical record across all Rodeo trips since 2003.
- Cumulative net rating, travel fatigue degradation, and second-half turnaround momentum.

### 🎲 4. Wemby Prop Modeler (`analysis/betting.py`)
- Empirical prop models for **Wemby Blocks** (e.g. Over/Under 3.5 or 4.5) and **Points + Rebounds**.
- Published strictly with measured error bars and a strict `NO CALL` rule when market consensus sits inside the margin of error.

---

## 📖 4. "The Notebook" Living Essay Engine (`blog/posts.py`)

Every post in the notebook must follow the exact constraint from `sox_tracker`:
> **Rule**: No numbers are hand-typed. Every single statistic, date, and rate cited in a post is computed at build time from the parquet cache via a `build(ctx)` function. If the data moves, the essay moves with it.

### Planned Capstone Essay Topics:
1. **"The French Horizon"**: Wemby's rim deterrence rate vs. historic Defensive Player of the Year baselines (Gobert, Howard, Duncan).
2. **"The Stonecutter's Ledger"**: Quantifying cumulative progress in Stephon Castle and young core developmental minutes.
3. **"The Rodeo Gauntlet"**: Tracking the February road trip game by game against historical franchise performance.
4. **"Pass First, Ask Questions Later"**: Assist-to-turnover ratios on corner threes and the revival of Spurs motion offense.

---

## 🛡️ 5. Rules & Operating Constraints for the Next Agent

When handing this project to an autonomous coding agent, include these strict rules in its `.agents/AGENTS.md`:

1. **Synchronous Foreground Execution Only**:
   - NEVER run commands or background watchers (`&`, background daemons, or unmonitored scripts).
   - Only execute CLI commands when explicitly requested or approved by the user.
2. **No Faked or Hand-Coded Stats**:
   - All charts, tables, and notebook essays must resolve directly from `data/cache/*.parquet`.
   - Never mock numbers in production HTML files.
3. **Statcast / NBA API Rate Limiting**:
   - `stats.nba.com` is notoriously aggressive with 429/403 throttling.
   - All requests must include modern browser headers (`User-Agent`, `Referer`, `Origin`) and minimum 0.5s delays with `tenacity` exponential backoff.
4. **Navigation Consistency & Parity**:
   - A single source of truth (`viz/theme.PAGES`) must govern `docs/index.html` and the global navigation bar.
   - Tests must assert that every page linked exists and matches registry order.

---

## 🚀 6. First Sprint Milestones

- [ ] **Milestone 1**: Set up `spurs_tracker` skeleton, `.soxEnv` or `.spursEnv`, `config.py` (Spurs team constants), and `client/nba_client.py`.
- [ ] **Milestone 2**: Ingest 2026–2027 Spurs schedule, box scores, and active roster into `data/cache/` using Parquet format.
- [ ] **Milestone 3**: Build `viz/theme.py` with Silver & Black + Fiesta color system and typography tokens.
- [ ] **Milestone 4**: Implement `viz/dashboard.py` (rolling net rating, Wemby impact curve, shooting heatmaps) and generate initial `docs/dashboard_SAS_2027.html`.
- [ ] **Milestone 5**: Implement `docs/index.html` landing page and `blog_report.py` notebook.
