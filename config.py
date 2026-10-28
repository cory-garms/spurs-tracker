from pathlib import Path

TEAM_ABBR   = "SAS"
SEASON      = 2026          # pass to season_str() → "2026-27"
SEASON_TYPE = "Regular Season"

# Public address of the published site (link previews need absolute image URLs)
SITE_URL = "https://porvida.corygarms.com"

BASE_DIR   = Path(__file__).parent
CACHE_DIR  = BASE_DIR / "data" / "cache"
OUTPUT_DIR = BASE_DIR / "docs"
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

REQUEST_TIMEOUT = 30
REQUEST_DELAY   = 0.6   # seconds between API calls (NBA strict rate limit)

HISTORY_START = 1999    # first Spurs championship era

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


def season_str(year: int) -> str:
    """Convert season start year to NBA season string: 2025 → '2025-26'."""
    return f"{year}-{str(year + 1)[-2:]}"
