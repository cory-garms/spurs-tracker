"""
Standout Performances — who actually had the big night.

Ranks every player by John Hollinger's Game Score, a single-number box score
summary, so the spotlight follows the production rather than the name:

  - Player of the Game: highest Game Score in a game
  - Breakout: the player furthest above their own season norm (needs a baseline)
  - Hot Hand: best average Game Score over the team's last N games

Game Score = PTS + 0.4*FGM - 0.7*FGA - 0.4*(FTA - FTM) + 0.7*OREB + 0.3*DREB
             + STL + 0.7*AST + 0.7*BLK - 0.4*PF - TOV
"""

from __future__ import annotations

import pandas as pd

# A player needs this many earlier games before a night can count as a breakout
MIN_BASELINE_GAMES = 5
# ...and must beat their own average Game Score by at least this much
BREAKOUT_MARGIN = 8.0


def game_score(logs: pd.DataFrame) -> pd.Series:
    """Hollinger Game Score per row. Older caches without the OREB/DREB split use 0.4*REB."""
    f = logs.fillna({c: 0 for c in ("pts", "fgm", "fga", "fta", "ftm", "stl", "ast", "blk", "pf", "tov", "reb")})
    if {"oreb", "dreb"}.issubset(f.columns) and f["oreb"].notna().all() and f["dreb"].notna().all():
        boards = 0.7 * f["oreb"] + 0.3 * f["dreb"]
    else:
        boards = 0.4 * f["reb"]  # league-typical OREB share makes this a close stand-in
    return (
        f["pts"] + 0.4 * f["fgm"] - 0.7 * f["fga"] - 0.4 * (f["fta"] - f["ftm"])
        + boards + f["stl"] + 0.7 * f["ast"] + 0.7 * f["blk"] - 0.4 * f["pf"] - f["tov"]
    ).astype(float)


def _played(player_logs: pd.DataFrame) -> pd.DataFrame:
    f = player_logs[player_logs["min"] > 0].copy()
    f["gmsc"] = game_score(f)
    return f.sort_values("game_date")


def stat_line(row: pd.Series, parts: int = 3) -> str:
    """Compact line led by points, then the player's most notable other numbers: '19 PTS · 9 AST · 3 STL'."""
    extras = [
        ("REB", int(row["reb"]), 5), ("AST", int(row["ast"]), 5),
        ("STL", int(row["stl"]), 3), ("BLK", int(row["blk"]), 3),
    ]
    notable = sorted([e for e in extras if e[1] >= e[2]], key=lambda e: e[1] / e[2], reverse=True)
    if len(notable) < parts - 1:
        fill = sorted([e for e in extras if e not in notable], key=lambda e: e[1] / e[2], reverse=True)
        notable += fill[: parts - 1 - len(notable)]
    line = [f"{int(row['pts'])} PTS"] + [f"{v} {k}" for k, v, _ in notable[: parts - 1]]
    return " · ".join(line)


def _summary(row: pd.Series, **extra) -> dict:
    return {
        "player_name": row["player_name"],
        "last_name": str(row["player_name"]).split()[-1],
        "game_score": round(float(row["gmsc"]), 1),
        "line": stat_line(row),
        "game_id": row["game_id"],
        "game_date": row["game_date"],
        **extra,
    }


def game_performers(player_logs: pd.DataFrame, game_id: str | None = None) -> dict:
    """
    Player of the Game and (if anyone qualifies) a Breakout for one game,
    defaulting to the most recent. Breakout is never the Player of the Game,
    so the spotlight reaches a second player.
    """
    f = _played(player_logs)
    if f.empty:
        return {}
    if game_id is None:
        game_id = f["game_id"].iloc[-1]
    game = f[f["game_id"] == game_id]
    if game.empty:
        return {}

    potg = game.loc[game["gmsc"].idxmax()]
    result = {"player_of_the_game": _summary(potg)}

    game_date = game["game_date"].iloc[0]
    prior = f[f["game_date"] < game_date].groupby("player_name")["gmsc"].agg(["mean", "count"])
    prior = prior[prior["count"] >= MIN_BASELINE_GAMES]
    candidates = game[game["player_name"].isin(prior.index) & (game["player_name"] != potg["player_name"])].copy()
    if not candidates.empty:
        candidates["above"] = candidates["gmsc"] - candidates["player_name"].map(prior["mean"])
        best = candidates.loc[candidates["above"].idxmax()]
        if best["above"] >= BREAKOUT_MARGIN:
            result["breakout"] = _summary(
                best,
                above_avg=round(float(best["above"]), 1),
                season_avg=round(float(prior.loc[best["player_name"], "mean"]), 1),
            )
    return result


def hot_hand(player_logs: pd.DataFrame, last_n: int = 5, min_games: int = 3) -> dict:
    """Best average Game Score over the team's last `last_n` games (min `min_games` played)."""
    f = _played(player_logs)
    if f.empty:
        return {}
    recent_ids = f.drop_duplicates("game_id")["game_id"].tail(last_n)
    recent = f[f["game_id"].isin(recent_ids)]
    games_in_window = len(recent_ids)
    agg = recent.groupby("player_name").agg(
        gmsc=("gmsc", "mean"), games=("game_id", "count"),
        pts=("pts", "mean"), reb=("reb", "mean"), ast=("ast", "mean"),
        stl=("stl", "mean"), blk=("blk", "mean"),
    )
    agg = agg[agg["games"] >= min(min_games, games_in_window)]
    if agg.empty:
        return {}
    name = agg["gmsc"].idxmax()
    r = agg.loc[name]
    return {
        "player_name": name,
        "last_name": name.split()[-1],
        "game_score": round(float(r["gmsc"]), 1),
        "games": int(r["games"]),
        "window": games_in_window,
        "line": f"{r['pts']:.1f} PTS · {r['reb']:.1f} REB · {r['ast']:.1f} AST",
    }


def season_leaders(player_logs: pd.DataFrame, min_games: int = 1) -> pd.DataFrame:
    """Average Game Score per player, best first."""
    f = _played(player_logs)
    if f.empty:
        return pd.DataFrame()
    out = f.groupby("player_name").agg(gmsc=("gmsc", "mean"), games=("game_id", "count"), min=("min", "mean"))
    return out[out["games"] >= min_games].sort_values("gmsc", ascending=False).round(1).reset_index()
