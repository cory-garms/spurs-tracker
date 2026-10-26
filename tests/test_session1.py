"""Unit tests for Session 1 backend pipeline deliverables."""

from __future__ import annotations

from pathlib import Path
import pandas as pd
import pytest

from data.fetcher import Fetcher
from data.league import fetch_league_standings, load_league_standings, LEAGUE_STANDINGS_SCHEMA
from data.validator import validate_table, run_validation


def test_fetcher_season_type_cache_isolation():
    f_reg = Fetcher(team_id=1610612759, season=2025, season_type="Regular Season")
    f_pre = Fetcher(team_id=1610612759, season=2025, season_type="Pre Season")
    f_ply = Fetcher(team_id=1610612759, season=2025, season_type="Playoffs")

    reg_cache = f_reg._cache("games").name
    pre_cache = f_pre._cache("games").name
    ply_cache = f_ply._cache("games").name

    assert reg_cache == "games_1610612759_2025.parquet"
    assert pre_cache == "games_1610612759_2025_preseason.parquet"
    assert ply_cache == "games_1610612759_2025_playoffs.parquet"

    # Ensure none of them overwrite each other
    assert len({reg_cache, pre_cache, ply_cache}) == 3


def test_league_standings_schema_and_count(tmp_path, monkeypatch):
    import config
    monkeypatch.setattr(config, "CACHE_DIR", tmp_path)

    # Ingest baseline
    df = fetch_league_standings(season=2025, force_refresh=True)
    assert not df.empty
    assert len(df) == 30  # All 30 NBA teams

    for col in LEAGUE_STANDINGS_SCHEMA:
        assert col in df.columns, f"Missing {col} in league standings"

    # Test load
    loaded = load_league_standings(season=2025)
    assert len(loaded) == 30


def test_validator_on_synthetic_data(tmp_path):
    # Create valid games parquet
    games_df = pd.DataFrame([{
        "game_id": "0022500001",
        "game_date": "2025-10-25",
        "season": "2025-26",
        "home_away": "H",
        "opponent_id": 1610612745,
        "opponent_abbr": "HOU",
        "result": "W",
        "pts": 118,
        "opp_pts": 105,
        "margin": 13,
        "pace": 100.0,
        "ortg": 118.0,
        "drtg": 105.0,
        "nrtg": 13.0,
        "status": "Final",
    }])

    valid_file = tmp_path / "games_1610612759_2025.parquet"
    games_df.to_parquet(valid_file, index=False)

    res = validate_table(valid_file)
    assert res["status"] == "PASS"
    assert res["rows"] == 1

    # Create invalid games parquet missing critical margin
    bad_df = pd.DataFrame([{"game_id": "002", "pts": 100}])
    bad_file = tmp_path / "games_bad.parquet"
    bad_df.to_parquet(bad_file, index=False)

    bad_res = validate_table(bad_file)
    assert bad_res["status"] == "FAIL"
