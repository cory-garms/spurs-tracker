"""
Unit tests for Session 3: Static Data API Exporter, Pipeline Orchestrator, and CI/CD Automation.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
import pandas as pd
import pytest

from config import TEAM_ABBR, SEASON
from data.fetcher import Fetcher
from data.exporter import export_all_data, DATA_DIR
from pipeline import run_pipeline


@pytest.fixture
def cached_spurs_data():
    """Load actual cached Spurs data for end-to-end export testing."""
    fetcher = Fetcher(team_id=1610612759, season=2025)
    games = fetcher.load("games")
    player_logs = fetcher.load("player_game_log")
    return games, player_logs


def test_exporter_creates_all_files(cached_spurs_data, tmp_path):
    """Test that export_all_data generates all 5 expected JSON files."""
    games, player_logs = cached_spurs_data
    exported = export_all_data(games, player_logs, season=2025, output_dir=tmp_path)

    expected_keys = ["predictions", "four_factors", "roster_pulse", "clutch", "summary"]
    for k in expected_keys:
        assert k in exported
        assert exported[k].exists()
        assert exported[k].stat().st_size > 0


def test_predictions_json_structure(cached_spurs_data, tmp_path):
    """Validate structure and mathematical bounds in predictions.json."""
    games, player_logs = cached_spurs_data
    exported = export_all_data(games, player_logs, season=2025, output_dir=tmp_path)
    p_data = json.loads(exported["predictions"].read_text(encoding="utf-8"))

    assert "season" in p_data
    assert "rival_forecasts" in p_data
    assert "all_opponents" in p_data

    # Check marquee rivals
    for rival in ["HOU", "DAL", "LAL"]:
        assert rival in p_data["rival_forecasts"]
        item = p_data["rival_forecasts"][rival]
        assert "win_probability_pct" in item
        assert 0.0 <= item["win_probability_pct"] <= 100.0
        assert "prob_double_digit_pct" in item
        assert "projected_margin" in item
        assert "beatdown_tier" in item

    # Check complete 29 opponents list
    opps = p_data["all_opponents"]
    assert len(opps) == 29
    assert any(o["opponent"] == "HOU" for o in opps)
    assert any(o["opponent"] == "BOS" for o in opps)


def test_four_factors_json_structure(cached_spurs_data, tmp_path):
    """Validate Dean Oliver possession metrics in four_factors.json."""
    games, player_logs = cached_spurs_data
    exported = export_all_data(games, player_logs, season=2025, output_dir=tmp_path)
    ff_data = json.loads(exported["four_factors"].read_text(encoding="utf-8"))

    assert "summary" in ff_data
    assert "diagnostic_table" in ff_data
    summary = ff_data["summary"]

    assert "efg_pct" in summary
    assert "tov_pct" in summary
    assert "oreb_pct" in summary
    assert "ftr" in summary
    assert "efg_delta_vs_league" in summary


def test_roster_pulse_json_structure(cached_spurs_data, tmp_path):
    """Validate lineup synergies and starter/bench splits in roster_pulse.json."""
    games, player_logs = cached_spurs_data
    exported = export_all_data(games, player_logs, season=2025, output_dir=tmp_path)
    r_data = json.loads(exported["roster_pulse"].read_text(encoding="utf-8"))

    assert "key_pairings" in r_data
    assert "starter_bench_split" in r_data
    assert isinstance(r_data["key_pairings"], list)

    sb = r_data["starter_bench_split"]
    assert "starter_names" in sb
    assert "bench_names" in sb
    assert "bench_scoring_share_pct" in sb
    assert "starter_avg_pts" in sb


def test_clutch_json_structure(cached_spurs_data, tmp_path):
    """Validate crunch-time metrics and leaders in clutch.json."""
    games, player_logs = cached_spurs_data
    exported = export_all_data(games, player_logs, season=2025, output_dir=tmp_path)
    c_data = json.loads(exported["clutch"].read_text(encoding="utf-8"))

    assert "clutch_summary" in c_data
    assert "clutch_leaders" in c_data
    c_sum = c_data["clutch_summary"]
    assert "clutch_record" in c_sum
    assert "clutch_win_pct" in c_sum
    assert "composure_index" in c_sum


def test_summary_json_structure(cached_spurs_data, tmp_path):
    """Validate top-level franchise summary and identity in summary.json."""
    games, player_logs = cached_spurs_data
    exported = export_all_data(games, player_logs, season=2025, output_dir=tmp_path)
    s_data = json.loads(exported["summary"].read_text(encoding="utf-8"))

    assert s_data["team"] == "SAS"
    assert s_data["franchise"] == "San Antonio Spurs"
    assert s_data["motto"] == "Pound the Rock"
    assert "beautiful_game" in s_data


def test_pipeline_dry_run():
    """Verify master pipeline runs cleanly in offline mode."""
    success = run_pipeline(
        team_abbr=TEAM_ABBR,
        season=SEASON,
        skip_fetch=True,
        refresh=False,
        skip_viz=True,
        skip_export=False,
        verbose=False,
    )
    assert success is True


def test_cache_query_performance():
    """Benchmark: Ensure loading games and computing prediction is < 150ms."""
    fetcher = Fetcher(team_id=1610612759, season=2025)
    t0 = time.perf_counter()
    games = fetcher.load("games")
    from analysis.predictions import predict_matchup
    pred = predict_matchup(games, "HOU", is_home=True)
    t1 = time.perf_counter()
    duration_ms = (t1 - t0) * 1000.0

    assert not games.empty
    assert pred["opponent_abbr"] == "HOU"
    assert duration_ms < 150.0, f"Query took {duration_ms:.2f}ms, expected < 150ms"
