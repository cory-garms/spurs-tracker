"""
Matchup & Margin Predictor Engine.

Calculates game projections, expected score margins, win probabilities,
and 'Beatdown / Blowout' likelihoods for any NBA opponent.

Key Metrics:
  - Projected Final Score (Spurs vs Opponent)
  - Projected Margin (+/- points)
  - Win Probability (%)
  - Beatdown Likelihood (Chance of +10, +15, +20 point victory)
  - Tactical Matchup Advantage Analysis
"""

from __future__ import annotations

import math
from typing import Any
import pandas as pd
import numpy as np

import config
from config import TEAMS
from data.league import load_league_standings


NBA_SPREAD_STD_DEV = 11.5   # Standard deviation of NBA single-game score margins
HOME_COURT_ADVANTAGE = 2.8  # Average NBA home court point differential swing


def _normal_cdf(x: float) -> float:
    """Standard normal cumulative distribution function using math.erf."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _rest_adjustment(days_rest: int) -> float:
    """Margin adjustment based on rest days (0 = back-to-back, 1 = normal, 2+ = rested)."""
    if days_rest == 0:
        return -2.4  # B2B fatigue penalty
    elif days_rest >= 2:
        return 1.5   # Fresh legs advantage
    return 0.0


def predict_matchup(
    games: pd.DataFrame,
    opponent_abbr: str,
    is_home: bool = True,
    season: int = config.SEASON,
    spurs_rest_days: int = 1,
    opp_rest_days: int = 1,
) -> dict[str, Any]:
    """
    Generate matchup projection and margin/blowout likelihood against an opponent (V2).

    Parameters:
      games: DataFrame of Spurs completed games.
      opponent_abbr: 3-letter abbreviation of opponent (e.g. 'LAL', 'HOU', 'BOS').
      is_home: True if game is at Frost Bank Center, False if Road.
      season: NBA season year for league ratings lookup.
      spurs_rest_days: Days of rest for Spurs before this contest.
      opp_rest_days: Days of rest for opponent.

    Returns dict of predictive metrics.
    """
    opp = opponent_abbr.upper()
    opp_info = TEAMS.get(opp, {"name": opp, "conf": "NBA", "div": "NBA"})

    # Load live 30-team league standings & ratings
    league_df = load_league_standings(season=season)
    opp_row = league_df[league_df["team_abbr"] == opp] if not league_df.empty else pd.DataFrame()

    opp_ortg = float(opp_row.iloc[0]["ortg"]) if not opp_row.empty else 112.5
    opp_drtg = float(opp_row.iloc[0]["drtg"]) if not opp_row.empty else 112.5
    opp_pace = float(opp_row.iloc[0]["pace"]) if not opp_row.empty else 99.5
    opp_w = int(opp_row.iloc[0]["wins"]) if not opp_row.empty else 0
    opp_l = int(opp_row.iloc[0]["losses"]) if not opp_row.empty else 0

    # Spurs baseline stats
    f_games = games[games["status"] == "Final"].copy() if not games.empty else pd.DataFrame()
    spurs_ortg = float(f_games["ortg"].mean()) if not f_games.empty and "ortg" in f_games else 112.0
    spurs_drtg = float(f_games["drtg"].mean()) if not f_games.empty and "drtg" in f_games else 113.0
    spurs_pace = float(f_games["pace"].mean()) if not f_games.empty and "pace" in f_games else 99.8

    home_boost = HOME_COURT_ADVANTAGE if is_home else -HOME_COURT_ADVANTAGE
    rest_boost = _rest_adjustment(spurs_rest_days) - _rest_adjustment(opp_rest_days)

    # Game pace expectation
    game_pace = (spurs_pace + opp_pace) / 2.0

    # Possessions per 100 efficiency model
    # Spurs expected points per 100 poss = (Spurs ORtg + Opp DRtg) / 2
    spurs_exp_rtg = (spurs_ortg + opp_drtg) / 2.0 + (home_boost / 2.0) + (rest_boost / 2.0)
    opp_exp_rtg   = (opp_ortg + spurs_drtg) / 2.0 - (home_boost / 2.0) - (rest_boost / 2.0)

    proj_spurs_pts = (spurs_exp_rtg * game_pace) / 100.0
    proj_opp_pts   = (opp_exp_rtg * game_pace) / 100.0

    # Head-to-head empirical weighting
    h2h_games = f_games[f_games["opponent_abbr"] == opp] if not f_games.empty else pd.DataFrame()
    h2h_g = len(h2h_games)
    h2h_wins = 0
    h2h_avg_margin = 0.0

    if h2h_g > 0:
        h2h_wins = int((h2h_games["result"] == "W").sum())
        h2h_avg_margin = float(h2h_games["margin"].mean())
        # Blend 70% rating model + 30% empirical H2H
        projected_margin = (proj_spurs_pts - proj_opp_pts) * 0.70 + (h2h_avg_margin) * 0.30
    else:
        projected_margin = proj_spurs_pts - proj_opp_pts

    # Win Probability via normal distribution of score margin
    # P(Margin > 0)
    z_win = projected_margin / NBA_SPREAD_STD_DEV
    win_prob = round(_normal_cdf(z_win) * 100, 1)

    # Beatdown Probabilities:
    # P(Margin >= 10)
    z_10 = (projected_margin - 9.5) / NBA_SPREAD_STD_DEV
    prob_double_digit = round(_normal_cdf(z_10) * 100, 1)

    # P(Margin >= 15) -> Blowout
    z_15 = (projected_margin - 14.5) / NBA_SPREAD_STD_DEV
    prob_blowout = round(_normal_cdf(z_15) * 100, 1)

    # P(Margin >= 20) -> Demolition
    z_20 = (projected_margin - 19.5) / NBA_SPREAD_STD_DEV
    prob_demolition = round(_normal_cdf(z_20) * 100, 1)

    # Beatdown Outlook Tier
    if projected_margin >= 12.0 or prob_blowout >= 40.0:
        tier = "💥 Complete Demolition"
        tier_desc = "Spurs hold overwhelming statistical matchup advantages across paint and pace."
        badge_color = "#00B2A9"  # Fiesta Teal
    elif projected_margin >= 5.0 or prob_double_digit >= 45.0:
        tier = "🔨 Decisive Beatdown"
        tier_desc = "Spurs strongly favored to pull away by double-digits in the second half."
        badge_color = "#C4CED4"  # Spurs Silver
    elif projected_margin >= -1.0:
        tier = "⏱️ Crunch-Time Battle"
        tier_desc = "Projected 4th-quarter nail-biter decided by clutch execution and free throws."
        badge_color = "#FF8200"  # Fiesta Orange
    else:
        tier = "⚠️ High-Stakes Dogfight"
        tier_desc = "Upset alert required: Spurs must dominate rim protection and turnover margins."
        badge_color = "#EF426F"  # Fiesta Fuschia

    return {
        "opponent_abbr": opp,
        "opponent_name": opp_info["name"],
        "conference": opp_info["conf"],
        "division": opp_info["div"],
        "is_home": is_home,
        "location_str": "Frost Bank Center (Home)" if is_home else "On the Road (Away)",
        "projected_spurs_pts": round(proj_spurs_pts, 1),
        "projected_opp_pts": round(proj_opp_pts, 1),
        "projected_margin": round(projected_margin, 1),
        "win_probability_pct": win_prob,
        "prob_double_digit_pct": prob_double_digit,
        "prob_blowout_pct": prob_blowout,
        "prob_demolition_pct": prob_demolition,
        "h2h_games_played": h2h_g,
        "h2h_record": f"{h2h_wins}-{h2h_g - h2h_wins}" if h2h_g > 0 else "0-0",
        "h2h_avg_margin": round(h2h_avg_margin, 1),
        "beatdown_tier": tier,
        "beatdown_desc": tier_desc,
        "badge_color": badge_color,
    }


def predict_all_opponents(games: pd.DataFrame, is_home: bool = True) -> pd.DataFrame:
    """
    Generate predictions against all 29 NBA opponents, sorted from
    highest projected Spurs margin ('biggest beatdown') to lowest.
    """
    records = []
    for abbr in TEAMS:
        if abbr == config.TEAM_ABBR:
            continue
        pred = predict_matchup(games, abbr, is_home=is_home)
        records.append({
            "opponent": pred["opponent_abbr"],
            "name": pred["opponent_name"],
            "conf": pred["conference"],
            "proj_spurs": pred["projected_spurs_pts"],
            "proj_opp": pred["projected_opp_pts"],
            "proj_margin": pred["projected_margin"],
            "win_prob": pred["win_probability_pct"],
            "double_digit_pct": pred["prob_double_digit_pct"],
            "blowout_pct": pred["prob_blowout_pct"],
            "h2h_record": pred["h2h_record"],
            "tier": pred["beatdown_tier"],
        })

    df = pd.DataFrame(records)
    return df.sort_values("proj_margin", ascending=False).reset_index(drop=True)
