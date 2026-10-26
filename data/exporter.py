"""
Static Data API Exporter.

Serializes analytical models, predictions, Four Factors, clutch splits,
and roster synergies into structured JSON files inside docs/data/.

Enables ultra-fast, client-side interactive components on GitHub Pages
without requiring a live Python backend.

Exports:
  - docs/data/predictions.json
  - docs/data/four_factors.json
  - docs/data/roster_pulse.json
  - docs/data/clutch.json
  - docs/data/summary.json
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import pandas as pd
import numpy as np

import config
from config import OUTPUT_DIR, TEAM_ABBR, SEASON, season_str
from analysis.predictions import predict_matchup, predict_all_opponents
from analysis.four_factors import team_four_factors_summary, four_factors_diagnostic_table
from analysis.lineups import key_spurs_synergies, starter_bench_deep_split
from analysis.clutch import clutch_game_summary, clutch_player_leaders
from analysis.standings import season_record
from analysis.beautiful_game import team_ball_movement_summary

DATA_DIR = OUTPUT_DIR / "data"


class _NumpyEncoder(json.JSONEncoder):
    """JSON encoder for numpy and pandas dtypes."""
    def default(self, obj: Any) -> Any:
        if isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (pd.Timestamp, pd.Period)):
            return str(obj)
        return super().default(obj)


def export_all_data(
    games: pd.DataFrame,
    player_logs: pd.DataFrame,
    season: int = SEASON,
    output_dir: Path = DATA_DIR,
) -> dict[str, Path]:
    """
    Export all analytical models into static JSON bundles in docs/data/.
    Returns dict mapping dataset name to file path.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    exported_files = {}

    # 1. Predictions & Beatdown Radar
    pred_df = predict_all_opponents(games, is_home=True)
    rivals_data = {}
    for r in ["HOU", "DAL", "LAL", "GSW", "OKC", "BOS"]:
        rivals_data[r] = predict_matchup(games, r, is_home=True, season=season)

    predictions_payload = {
        "season": season_str(season),
        "rival_forecasts": rivals_data,
        "all_opponents": pred_df.to_dict("records"),
    }
    p_path = output_dir / "predictions.json"
    p_path.write_text(json.dumps(predictions_payload, indent=2, cls=_NumpyEncoder), encoding="utf-8")
    exported_files["predictions"] = p_path

    # 2. Four Factors
    ff_summary = team_four_factors_summary(player_logs, games)
    ff_diag = four_factors_diagnostic_table(player_logs, games)
    four_factors_payload = {
        "season": season_str(season),
        "summary": ff_summary,
        "diagnostic_table": ff_diag.to_dict("records") if not ff_diag.empty else [],
    }
    ff_path = output_dir / "four_factors.json"
    ff_path.write_text(json.dumps(four_factors_payload, indent=2, cls=_NumpyEncoder), encoding="utf-8")
    exported_files["four_factors"] = ff_path

    # 3. Roster Pulse & Synergies
    synergies_df = key_spurs_synergies(player_logs)
    sb_split = starter_bench_deep_split(player_logs)
    roster_payload = {
        "season": season_str(season),
        "key_pairings": synergies_df.to_dict("records") if not synergies_df.empty else [],
        "starter_bench_split": sb_split,
    }
    r_path = output_dir / "roster_pulse.json"
    r_path.write_text(json.dumps(roster_payload, indent=2, cls=_NumpyEncoder), encoding="utf-8")
    exported_files["roster_pulse"] = r_path

    # 4. Clutch Playbook
    clutch_sum = clutch_game_summary(games)
    clutch_ldrs = clutch_player_leaders(games, player_logs, min_clutch_games=2)
    clutch_payload = {
        "season": season_str(season),
        "clutch_summary": clutch_sum,
        "clutch_leaders": clutch_ldrs.to_dict("records") if not clutch_ldrs.empty else [],
    }
    c_path = output_dir / "clutch.json"
    c_path.write_text(json.dumps(clutch_payload, indent=2, cls=_NumpyEncoder), encoding="utf-8")
    exported_files["clutch"] = c_path

    # 5. Global Summary & Alamo Heritage Meta
    rec = season_record(games)
    bg = team_ball_movement_summary(games, player_logs)
    summary_payload = {
        "team": TEAM_ABBR,
        "franchise": "San Antonio Spurs",
        "motto": "Pound the Rock",
        "heritage": "Mission San Antonio & The Alamo",
        "season": season_str(season),
        "record": rec,
        "beautiful_game": bg,
    }
    s_path = output_dir / "summary.json"
    s_path.write_text(json.dumps(summary_payload, indent=2, cls=_NumpyEncoder), encoding="utf-8")
    exported_files["summary"] = s_path

    return exported_files
