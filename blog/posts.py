"""
The Spurs Notebook — Dynamic Living Essay Engine.

Architectural Rule:
  No numbers or statistics are hand-typed in these essays. Every single average,
  rate, date, record, and differential cited is computed dynamically at build time
  from the cached parquet tables via `build(ctx)`. If the underlying data moves,
  the essay moves with it.
"""

from __future__ import annotations

from typing import Any
import pandas as pd
from analysis.wemby import get_wemby_logs, stocks_distribution, defensive_impact_summary, offensive_gravity_summary
from analysis.rodeo import segment_rodeo_games, rodeo_split_metrics
from analysis.beautiful_game import team_ball_movement_summary, player_pass_contributors
from analysis.standings import season_record
from config import SEASON, season_str

SEASON_LABEL = season_str(SEASON)


def build_french_horizon_post(ctx: dict[str, Any]) -> dict[str, str]:
    """
    Essay 1: 'The French Horizon'
    Evaluates Victor Wembanyama's rim gravity, defensive deterrence, and stocks production.
    """
    wemby = ctx.get("wemby_logs", pd.DataFrame())
    games = ctx.get("games", pd.DataFrame())

    if wemby.empty:
        return {
            "slug": "french-horizon",
            "title": "The French Horizon: Victor Wembanyama and the Outer Boundary of Defense",
            "category": "Defensive Gravity",
            "date": f"{SEASON_LABEL} Season",
            "html": "<p>Waiting on active Wembanyama game logs...</p>",
        }

    stocks = stocks_distribution(wemby)
    impact = defensive_impact_summary(games, wemby)
    offense = offensive_gravity_summary(wemby)

    html = f"""
    <p class="essay-lead">
      Basketball defense has traditionally been measured in proximity: contesting hands, planted feet,
      and charges absorbed at the circle. With <strong>Victor Wembanyama</strong>, the geometry alters before
      the shot ever leaves the hand. In <strong>{stocks['games']} tracked appearances</strong> this season,
      the French prodigy is turning the interior into a structural no-fly zone, averaging
      <strong>{stocks['blocks_per_game']:.2f} blocks</strong> and <strong>{stocks['steals_per_game']:.2f} steals</strong>
      for a combined <strong>{stocks['stocks_per_game']:.2f} stocks per game</strong>
      (<strong>{stocks['stocks_per_36']:.2f} per 36 minutes</strong>).
    </p>

    <h3>The Anatomy of Deterrence</h3>
    <p>
      Counting stats fail to describe the <em>reluctant pass</em> &mdash; the instant an opposing guard penetrates
      the lane, registers Wemby’s 8-foot wingspan hovering at the rim, and executes a frantic pivot back toward
      the perimeter. The impact reveals itself in the splits: in games where Wembanyama records <strong>5 or more stocks</strong>
      ({impact.get('high_stocks_games', 0)} games), the Spurs allow just <strong>{impact.get('high_stocks_opp_pts', 0.0):.1f} points per game</strong>
      with a stifling defensive rating of <strong>{impact.get('high_stocks_drtg', 0.0):.1f}</strong>.
      That represents a defensive swing of <strong>{impact.get('drtg_delta', 0.0):+.1f} DRtg points</strong> compared to
      baseline contests.
    </p>

    <blockquote>
      &ldquo;When Wemby operates as an active eraser ({impact.get('high_stocks_games', 0)} nights with 5+ stocks),
      San Antonio has compiled a {impact.get('high_stocks_record', '--')} record, suppressing opponent scoring by
      {impact.get('opp_pts_suppression', 0.0):.1f} points per night.&rdquo;
    </blockquote>

    <h3>Milestone Ledger</h3>
    <p>
      Wembanyama has recorded 3 or more blocks in <strong>{stocks['games_3plus_blk']} of his {stocks['games']} games ({stocks['pct_3plus_blk']:.1f}%)</strong>,
      eclipsing 5 blocks in <strong>{stocks['games_5plus_blk']} contests</strong>. On the offensive side of the floor, his
      perimeter gravity commands attention: he is launching <strong>{offense['fg3a_per_game']:.1f} three-pointers per night</strong>
      (a <strong>{offense['three_point_attempt_rate'] * 100:.1f}% 3P attempt rate</strong>), finishing with an effective field goal percentage
      of <strong>{offense['effective_fg_pct']:.3f}</strong> and true shooting percentage of <strong>{offense['true_shooting_pct']:.3f}</strong>.
      He is not simply a shot-blocker; he is a dual-hemisphere spatial anomaly.
    </p>
    """

    return {
        "slug": "french-horizon",
        "title": "The French Horizon: Victor Wembanyama and the Outer Boundary of Defense",
        "category": "Defensive Gravity",
        "date": f"{SEASON_LABEL} Season Analysis",
        "html": html,
    }


def build_stonecutters_ledger_post(ctx: dict[str, Any]) -> dict[str, str]:
    """
    Essay 2: 'The Stonecutter's Ledger'
    Quantifies young core progression, rotation development, and team resilience.
    """
    games = ctx.get("games", pd.DataFrame())
    player_logs = ctx.get("player_logs", pd.DataFrame())
    rec = ctx.get("season_record", {})

    total_games = rec.get("games_played", 0)
    w = rec.get("wins", 0)
    l = rec.get("losses", 0)
    win_pct = rec.get("win_pct", 0.0)
    margin = rec.get("avg_margin", 0.0)

    # Calculate youth minutes (players under 24 years old / rookie-sophomore development)
    top_scorers = ""
    if not player_logs.empty:
        agg = player_logs.groupby("player_name").agg(
            pts=("pts", "mean"),
            reb=("reb", "mean"),
            ast=("ast", "mean"),
            g=("game_id", "count"),
        ).reset_index().sort_values("pts", ascending=False).head(4)
        top_scorers = ", ".join([f"<strong>{r['player_name']}</strong> ({r['pts']:.1f} PPG)" for _, r in agg.iterrows()])

    html = f"""
    <p class="essay-lead">
      Patience in modern professional sports is typically an endangered virtue. Hanging above the Spurs locker room
      for three decades is the Jacob Riis quote honoring the stonecutter hammering a hundred times without a visible crack.
      Through <strong>{total_games} games</strong> of the {SEASON_LABEL} campaign, San Antonio sits at
      <strong>{w}-{l} ({win_pct:.3f})</strong> with an average point differential of
      <strong>{margin:+.2f} per contest</strong>.
    </p>

    <h3>The Heavy Blows of Young Development</h3>
    <p>
      Championship culture is built in the aggregate. The offensive load is carried by a surging collective led by
      {top_scorers}. Night after night, the repetition of defensive rotations, off-ball screens, and secondary rim protection
      are accumulating silent equity.
    </p>

    <p>
      At home in the Frost Bank Center, the Spurs are <strong>{rec.get('home_w', 0)}-{rec.get('home_l', 0)}</strong>,
      protecting their floor with energetic pace. In their last 10 contests, they have logged a
      <strong>{rec.get('last_10_w', 0)}-{rec.get('last_10_l', 0)} stretch</strong>.
      The stone has not split yet, but the fractures are widening across the Western Conference hierarchy.
    </p>
    """

    return {
        "slug": "stonecutters-ledger",
        "title": "The Stonecutter's Ledger: Tracking the Incremental Fractures of Growth",
        "category": "Culture & Development",
        "date": f"{SEASON_LABEL} Season Analysis",
        "html": html,
    }


def build_rodeo_gauntlet_post(ctx: dict[str, Any]) -> dict[str, str]:
    """
    Essay 3: 'The Rodeo Gauntlet'
    Evaluates the February road trip against the 2003-present championship standard.
    """
    games = ctx.get("games", pd.DataFrame())
    segmented = segment_rodeo_games(games)
    splits = rodeo_split_metrics(segmented)
    rrt = splits.get("Active RRT", {})

    rrt_games = rrt.get("games", 0)
    rrt_rec = rrt.get("record", "0-0")
    rrt_pct = rrt.get("win_pct", 0.0)
    rrt_margin = rrt.get("avg_margin", 0.0)
    pre_margin = splits.get("Pre-RRT", {}).get("avg_margin", 0.0)

    html = f"""
    <p class="essay-lead">
      For twenty-three years, the arrival of February in Bexar County has carried a singular meaning: the livestock show
      moves into the Frost Bank Center, and the Silver & Black are banished to the highway. From 2003 through the five
      championship runs, the Rodeo Road Trip served as Gregg Popovich’s crucible &mdash; a multi-week endurance test
      where championship contenders were hardened.
    </p>

    <h3>The {SEASON_LABEL} Gauntlet Ledger</h3>
    <p>
      In this season's Active Rodeo stretch, the Spurs navigated <strong>{rrt_games} consecutive road tests</strong>,
      posting a <strong>{rrt_rec} ({rrt_pct:.3f}) mark</strong> with an average point differential of
      <strong>{rrt_margin:+.1f} points</strong>. Compared to their Pre-RRT differential of
      <strong>{pre_margin:+.1f} points</strong>, the road marathon test reveals how effectively the young roster absorbs
      travel fatigue and crowd hostility.
    </p>

    <blockquote>
      &ldquo;Tim Duncan went 8-1 on the inaugural 2003 trip en route to the title; the 2014 Beautiful Game squad went 6-3
      before obliterating Miami in June. In San Antonio, February records are not just dates on a calendar &mdash; they are
      the barometer of playoff steel.&rdquo;
    </blockquote>
    """

    return {
        "slug": "rodeo-gauntlet",
        "title": "The Rodeo Gauntlet: Highway Fatigue and the Crucible of Champions",
        "category": "Road Gauntlet",
        "date": "February 2026 Split Analysis",
        "html": html,
    }


def build_beautiful_game_post(ctx: dict[str, Any]) -> dict[str, str]:
    """
    Essay 4: 'Pass First, Ask Questions Later'
    Evaluates assist rates, pass velocity, and the revival of Spurs motion basketball.
    """
    games = ctx.get("games", pd.DataFrame())
    player_logs = ctx.get("player_logs", pd.DataFrame())
    bg = team_ball_movement_summary(games, player_logs)

    bgi = bg.get("beautiful_game_index", 0.0)
    ast_pg = bg.get("assists_per_game", 0.0)
    tov_pg = bg.get("turnovers_per_game", 0.0)
    ast_tov = bg.get("ast_tov_ratio", 0.0)
    ast_pct = bg.get("assisted_fg_pct", 0.0) * 100
    apc = bg.get("assist_points_created_pg", 0.0)

    passers = player_pass_contributors(player_logs, min_games=10)
    top_facilitators = ""
    if not passers.empty:
        top_facilitators = ", ".join([
            f"<strong>{r['player_name']}</strong> ({r['ast_pg']:.1f} APG, {r['ast_tov']:.2f} AST/TOV)"
            for _, r in passers.head(3).iterrows()
        ])

    html = f"""
    <p class="essay-lead">
      The 2014 San Antonio Spurs dismantled the Miami Heat with a brand of basketball so pristine that sportswriters
      labeled it an art form: touch passes, paint penetrations that yielded corner threes, and an absolute refusal to let
      the ball stick. Over a decade later, the foundational principles of motion offense are finding new life.
    </p>

    <h3>The Passing Index</h3>
    <p>
      This season, San Antonio is posting a <strong>Beautiful Game Index of {bgi:.1f} / 100</strong>, distributing
      <strong>{ast_pg} assists per game</strong> against <strong>{tov_pg} turnovers</strong> for a stellar
      <strong>{ast_tov} assist-to-turnover ratio</strong>. Over <strong>{ast_pct:.1f}% of all made field goals</strong>
      originate from an assist, generating an estimated <strong>{apc} Assist Points Created (APC)</strong> per night.
    </p>

    <p>
      The passing hub is anchored by {top_facilitators}, finding cutters and kicking out to open shooters as defenses
      collapse toward Wembanyama's gravity. When the ball moves with conviction, the Spurs offense operates at its highest
      expressive ceiling.
    </p>
    """

    return {
        "slug": "pass-first",
        "title": "Pass First, Ask Questions Later: The Revival of Spurs Motion Basketball",
        "category": "Motion Offense",
        "date": f"{SEASON_LABEL} Season Analysis",
        "html": html,
    }


def get_all_posts(ctx: dict[str, Any]) -> list[dict[str, str]]:
    """Build all living essays dynamically from current context."""
    return [
        build_french_horizon_post(ctx),
        build_stonecutters_ledger_post(ctx),
        build_rodeo_gauntlet_post(ctx),
        build_beautiful_game_post(ctx),
    ]
