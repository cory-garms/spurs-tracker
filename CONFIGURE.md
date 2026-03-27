# Configuring for a Different NBA Team

By default this tracker follows the **San Antonio Spurs**. To switch to any other
NBA team, pass CLI flags — no code edits required.

## Quick start

```bash
# Fetch data for Golden State Warriors, 2024-25 season
python fetch.py --team GSW --season 2024

# Print terminal dashboard
python report.py --team GSW --season 2024

# Generate HTML dashboard
python viz_report.py --team GSW --season 2024
```

## Supported teams

Run `python fetch.py --list-teams` to see all 30 team abbreviations.

| Conference | Teams |
|---|---|
| West | DAL, DEN, GSW, HOU, LAC, LAL, MEM, MIN, NOP, OKC, PHX, POR, SAC, SAS, UTA |
| East | ATL, BOS, BKN, CHA, CHI, CLE, DET, IND, MIA, MIL, NYK, ORL, PHI, TOR, WAS |

## Changing defaults in config.py

Edit the top of `config.py` to change the default team/season:

```python
TEAM_ABBR = "GSW"   # change default team
SEASON    = 2024    # change default season year (2024 → "2024-25")
```

## Season format

The NBA uses `"YYYY-YY"` season strings (e.g. `"2024-25"`). The `SEASON` config
value is an **integer** (e.g. `2024`) that gets converted automatically via
`season_str()`. Always pass `--season` as the start year (e.g. `--season 2024`
for the 2024-25 season).

## GitHub Actions auto-refresh

Set repository variables in **Settings → Variables → Actions**:

| Variable     | Value         |
|---|---|
| `TEAM_ABBR`  | e.g. `GSW`    |
| `SEASON`     | e.g. `2025`   |

The workflow runs daily at 8 AM ET (noon UTC), fetches fresh data, and
commits updated parquet + HTML files.
