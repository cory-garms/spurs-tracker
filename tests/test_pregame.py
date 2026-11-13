"""Game-day context must stay scoped to the right game and availability report."""

import json
from datetime import datetime, timezone

import pandas as pd
import pytest

import config
from data.availability import load_availability, player_statuses
from data.schedule import next_game
from viz import index_viz, matchup_viz, props_viz
from viz.availability import availability_html


@pytest.fixture
def snapshot():
    return {
        "reported_at": "2026-11-13T17:45:00-05:00",
        "source_url": "https://example.com/report.pdf",
        "teams": {"GSW": [{"name": "Out Player", "status": "Out", "reason": "Rest"}],
                  "SAS": [{"name": "Guard", "status": "Questionable", "reason": "Hip soreness"}]},
    }


@pytest.fixture
def schedule():
    def row(gid, tip, status, home, away):
        return {"game_id": gid, "tipoff_utc": tip, "status": status, "home_abbr": home,
                "away_abbr": away, "home_score": 115, "away_score": 108,
                "arena": "Frost Bank Center", "city": "San Antonio", "tv": "Prime Video"}
    return pd.DataFrame([
        row("previous", "2026-11-12T01:00:00Z", 3, "HOU", "GSW"),
        row("ours", "2026-11-12T01:00:00Z", 3, "CHI", "SAS"),
        row("tonight", "2026-11-14T02:30:00Z", 1, "SAS", "GSW"),
    ])


@pytest.fixture
def logs():
    return pd.DataFrame([
        {"game_id": "ours", "game_date": "2026-11-11", "player_name": name, "gp": 12,
         "min": 30., "pts": pts, "reb": 5, "oreb": 1, "dreb": 4, "ast": 3, "stl": 1,
         "blk": 1, "tov": 1, "pf": 1, "fgm": 8, "fga": 16, "ftm": 2, "fta": 2}
        for name, pts in [("Out Player", 40), ("Guard", 30), ("Wing", 20), ("Big", 10)]
    ])


def test_availability_cannot_carry_to_a_different_game(tmp_path, monkeypatch, snapshot):
    monkeypatch.setattr(config, "BASE_DIR", tmp_path)
    (tmp_path / "data").mkdir()
    (tmp_path / "data/availability_2026.json").write_text(json.dumps({"tonight": snapshot}))
    assert player_statuses(load_availability("tonight", 2026), "GSW") == {"Out Player": "Out"}
    assert load_availability("next-game", 2026) == {}
    assert load_availability("tonight", 2025) == {}
    html = availability_html(snapshot)
    assert "4:45 PM CT" in html and 'href="https://example.com/report.pdf"' in html


def test_preview_excludes_absences_but_labels_uncertain_players(tmp_path, monkeypatch, snapshot, schedule, logs):
    now = datetime(2026, 11, 13, 23, tzinfo=timezone.utc)
    monkeypatch.setattr(matchup_viz, "now_utc", lambda: now)
    monkeypatch.setattr(matchup_viz, "load_schedule", lambda season: schedule)
    monkeypatch.setattr(matchup_viz, "load_availability", lambda game_id, season: snapshot)
    monkeypatch.setattr(matchup_viz, "load_team_players", lambda team_id, season: logs)
    monkeypatch.setattr(matchup_viz, "last_season_series", lambda *args: [])
    monkeypatch.setattr(matchup_viz, "load_league_standings", lambda season: pd.DataFrame([
        {"team_abbr": team, "wins": wins, "losses": losses, "nrtg": net, "pace": 100.}
        for team, wins, losses, net in [("GSW", 8, 4, 7.5), ("SAS", 10, 2, 11.)]
    ]))
    html = matchup_viz.build_matchup_page(pd.DataFrame({"status": ["Final"]}), logs,
                                        output_path=tmp_path / "preview.html").read_text()
    watch = html.split("<h2>Players to Watch</h2>", 1)[1].split("</section>", 1)[0]
    warriors = watch.split("<h3>Warriors</h3>", 1)[1]
    assert "Out Player" not in warriors and all(name in warriors for name in ("Guard", "Wing", "Big"))
    assert 'class="badge orange">Questionable' in watch
    assert "Season baseline:" in html and "without injury or lineup adjustments" in html
    assert "108-115 @ HOU" in html and '<div class="rec">8-4</div>' in html


@pytest.mark.parametrize("day,label", [(13, "Tonight"), (12, "Next game")])
def test_home_strip_uses_schedule_and_central_date(tmp_path, monkeypatch, schedule, day, label):
    monkeypatch.setattr(index_viz, "now_utc", lambda: datetime(2026, 11, day, 23, tzinfo=timezone.utc))
    monkeypatch.setattr(index_viz, "load_schedule", lambda season: schedule)
    html = index_viz.build_index_page(pd.DataFrame(columns=["status", "game_date", "result"]),
                                     pd.DataFrame(), output_path=tmp_path / "index.html").read_text()
    assert html.index('class="game-strip"') < html.index('<main class="deck"')
    strip = html.split('class="game-strip"', 1)[1].split("</a>", 1)[0]
    assert label in strip and "GSW at SAS" in strip and "8:30 PM CT" in strip and "Prime Video" in strip
    assert 'href="matchup.html"' in strip


def test_props_use_latest_rest_and_skip_confirmed_absences(schedule):
    nxt = next_game(schedule, "SAS", datetime(2026, 11, 13, 23, tzinfo=timezone.utc))
    rows = [{"player_name": name, "venue_hits": 1, "venue_n": 2, "stat": "Points", "current_line": 20.5,
             "median": 20, "tonight": 20., "recent_hits": 2, "recent_n": 5} for name in ("Out Player", "Guard")]
    html = props_viz._tonight_section(nxt, {"available": False}, rows, pd.DataFrame(), schedule,
                                     "SAS", {"Out Player": "Out", "Guard": "Questionable"})
    assert "Out Player" not in html and 'class="badge orange">Questionable' in html
    assert "Warriors: 1 day." in html
    assert "do not adjust for injuries or lineup changes" in html
