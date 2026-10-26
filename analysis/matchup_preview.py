"""
Next-Game Preview — how the Spurs stack up against their next opponent.

  - Tale of the tape: ratings and Four Factors side by side, with league ranks
  - Projection: one transparent number, not a simulator
  - Players to watch on both sides, ranked by Game Score
  - Last season's series

Projection method: each team's net rating is shrunk toward league average
(0) in proportion to games played, the gap is converted to points at the
average pace of the two teams, and home court is added. The margin's spread
around that estimate is taken as ~12 points, which sets the win probability.
"""

from __future__ import annotations

from math import erf, sqrt

import pandas as pd

import config
from analysis.performers import game_score

HOME_COURT_PTS = 2.0      # recent-era league home advantage, in points
SHRINK_GAMES = 10         # a team's own net rating gets half weight after this many games
MARGIN_SD = 12.0          # typical NBA game margin spread around expectation

# (label, column, higher_is_better, format)
TAPE_ROWS: list[tuple[str, str, bool | None, str]] = [
    ("Net rating",       "nrtg",     True,  "{:+.1f}"),
    ("Offensive rating", "ortg",     True,  "{:.1f}"),
    ("Defensive rating", "drtg",     False, "{:.1f}"),
    ("Pace",             "pace",     None,  "{:.1f}"),
    ("Effective FG%",    "efg_pct",  True,  "{:.1%}"),
    ("Turnover %",       "tov_pct",  False, "{:.1%}"),
    ("Off. rebound %",   "oreb_pct", True,  "{:.1%}"),
    ("Free throw rate",  "fta_rate", True,  "{:.3f}"),
    ("Opp. effective FG%", "opp_efg_pct", False, "{:.1%}"),
]


def tale_of_the_tape(standings: pd.DataFrame, team: str, opponent: str) -> list[dict]:
    """Side-by-side rows with league rank (1 = best) and which side has the edge."""
    if standings.empty or not {team, opponent} <= set(standings["team_abbr"]):
        return []
    s = standings.set_index("team_abbr")
    rows = []
    for label, col, higher_better, fmt in TAPE_ROWS:
        if col not in s.columns or s[col].isna().all():
            continue
        ranks = s[col].rank(ascending=not higher_better if higher_better is not None else False, method="min")
        a, b = float(s.at[team, col]), float(s.at[opponent, col])
        edge = None
        if higher_better is not None and a != b:
            edge = team if (a > b) == higher_better else opponent
        rows.append({
            "label": label,
            "team": fmt.format(a), "opponent": fmt.format(b),
            "team_rank": int(ranks[team]) if higher_better is not None else None,
            "opponent_rank": int(ranks[opponent]) if higher_better is not None else None,
            "edge": edge,
        })
    return rows


def _shrunk_net(row: pd.Series) -> float:
    gp = int(row["wins"] + row["losses"])
    return float(row["nrtg"]) * gp / (gp + SHRINK_GAMES)


def projection(standings: pd.DataFrame, team: str, opponent: str, is_home: bool) -> dict:
    """Projected margin (team's perspective) and win probability."""
    if standings.empty or not {team, opponent} <= set(standings["team_abbr"]):
        return {}
    s = standings.set_index("team_abbr")
    a, b = s.loc[team], s.loc[opponent]
    pace = (float(a["pace"]) + float(b["pace"])) / 2
    margin = (_shrunk_net(a) - _shrunk_net(b)) * pace / 100 + (HOME_COURT_PTS if is_home else -HOME_COURT_PTS)
    win_prob = 0.5 * (1 + erf(margin / (MARGIN_SD * sqrt(2))))
    return {
        "margin": round(margin, 1),
        "win_prob": round(win_prob, 3),
        "games": int(min(a["wins"] + a["losses"], b["wins"] + b["losses"])),
    }


def players_to_watch(players: pd.DataFrame, n: int = 3, min_games: int = 1) -> list[dict]:
    """
    Top `n` by average Game Score from per-game season averages. Game Score is
    linear, so the Game Score of the averages equals the average Game Score.
    """
    if players.empty:
        return []
    p = players[players["gp"] >= min_games].copy()
    if p.empty:
        return []
    p["gmsc"] = game_score(p)
    out = []
    for _, r in p.sort_values("gmsc", ascending=False).head(n).iterrows():
        out.append({
            "player_name": r["player_name"],
            "game_score": round(float(r["gmsc"]), 1),
            "line": f"{r['pts']:.1f} PTS · {r['reb']:.1f} REB · {r['ast']:.1f} AST",
            "gp": int(r["gp"]),
        })
    return out


def spurs_players_from_logs(player_logs: pd.DataFrame) -> pd.DataFrame:
    """Turn our own box-score logs into the same per-game shape as the league player stats."""
    played = player_logs[player_logs["min"] > 0]
    if played.empty:
        return pd.DataFrame()
    cols = ["pts", "reb", "oreb", "dreb", "ast", "stl", "blk", "tov", "pf", "fgm", "fga", "ftm", "fta"]
    agg = played.groupby("player_name")[[c for c in cols if c in played.columns]].mean()
    agg["gp"] = played.groupby("player_name")["game_id"].count()
    return agg.reset_index()


def last_season_series(team_id: int, opponent: str, season: int = config.SEASON) -> list[dict]:
    """Our games against `opponent` last season, from the previous season's cache."""
    path = config.CACHE_DIR / f"games_{team_id}_{season - 1}.parquet"
    if not path.exists():
        return []
    g = pd.read_parquet(path)
    g = g[(g["opponent_abbr"] == opponent) & (g["status"] == "Final")].sort_values("game_date")
    return [{
        "result": r["result"],
        "score": f"{int(r['pts'])}-{int(r['opp_pts'])}",
        "venue": "vs." if r["home_away"] == "H" else "@",
        "opponent": opponent,
        "date": pd.to_datetime(r["game_date"]).strftime("%b %-d, %Y"),
    } for _, r in g.iterrows()]
