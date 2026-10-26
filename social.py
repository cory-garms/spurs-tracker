"""
Social Post Generator — CLI Tool for Twitter / X Distribution.

Generates ready-to-copy tweets with live data citations, character counts,
and optional matching chart PNG cards for social sharing.

Usage:
    python social.py --mode wemby      # Alien Horizon / Wemby Stocks tweet
    python social.py --mode postgame   # Stonecutter Post-Game Ledger tweet
    python social.py --mode gameday    # Pre-Game Matchup & Prop trend tweet
    python social.py --mode rodeo      # Rodeo Road Trip split tweet
    python social.py --all             # Generate all social formats
"""

from __future__ import annotations

import argparse
import sys
import pandas as pd
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

import config
from config import TEAM_ABBR, SEASON, season_str
from data.fetcher import Fetcher
from analysis.wemby import get_wemby_logs, stocks_distribution, defensive_impact_summary
from analysis.beautiful_game import team_ball_movement_summary, player_pass_contributors
from analysis.standings import season_record
from analysis.rodeo import segment_rodeo_games, rodeo_split_metrics

console = Console()

DEFAULT_SITE_URL = "https://corygarms.com/spurs-tracker"


def generate_wemby_tweet(wemby_logs: pd.DataFrame, games: pd.DataFrame, site_url: str = DEFAULT_SITE_URL) -> str:
    """Generate Alien Horizon / Wemby Stocks tweet."""
    if wemby_logs.empty:
        return "No Wembanyama logs found in cache."

    last_game = wemby_logs.iloc[-1]
    stocks_summary = stocks_distribution(wemby_logs)
    impact = defensive_impact_summary(games, wemby_logs)

    pts = int(last_game.get("pts", 0))
    reb = int(last_game.get("reb", 0))
    ast = int(last_game.get("ast", 0))
    blk = int(last_game.get("blk", 0))
    stl = int(last_game.get("stl", 0))
    game_stocks = blk + stl
    date_s = str(last_game.get("game_date", "recent"))

    tweet = (
        f"👽 WEMBY HORIZON ALERT ({date_s})\n\n"
        f"Victor Wembanyama:\n"
        f"• {pts} PTS | {reb} REB | {ast} AST | {blk} BLK | {stl} STL\n"
        f"• {game_stocks} STOCKS (Season avg: {stocks_summary.get('stocks_per_game', 0.0):.1f} PPG)\n"
        f"• 3+ BLK frequency: {stocks_summary.get('pct_3plus_blk', 0.0):.0f}% of games\n\n"
        f"When Wemby records 5+ stocks, Spurs DRtg drops by -{impact.get('drtg_delta', 0.0):.1f}.\n"
        f"Alien Lab: {site_url}/wemby_lab.html\n"
        f"#GoSpursGo #PorVida #Wemby"
    )
    return tweet


def generate_postgame_tweet(games: pd.DataFrame, player_logs: pd.DataFrame, site_url: str = DEFAULT_SITE_URL) -> str:
    """Generate Stonecutter Post-Game Ledger tweet."""
    if games.empty:
        return "No game logs found in cache."

    f_games = games[games["status"] == "Final"].sort_values("game_date").reset_index(drop=True)
    if f_games.empty:
        return "No completed games found."

    last_game = f_games.iloc[-1]
    game_n = len(f_games)
    rec = season_record(f_games)
    bg = team_ball_movement_summary(f_games, player_logs)

    res = last_game["result"]
    pts = int(last_game["pts"])
    opp_pts = int(last_game["opp_pts"])
    opp = last_game.get("opponent_abbr", "OPP")
    date_s = last_game.get("game_date", "")

    passers = player_pass_contributors(player_logs, min_games=1)
    top_passer = passers.iloc[0]["player_name"] if not passers.empty else "Spurs"
    top_ast = passers.iloc[0]["ast_pg"] if not passers.empty else 0

    tweet = (
        f"🔨 THE STONECUTTER'S LEDGER • GAME {game_n}\n\n"
        f"FINAL: Spurs {pts}, {opp} {opp_pts} ({res})\n"
        f"Record: {rec.get('wins', 0)}-{rec.get('losses', 0)} ({rec.get('win_pct', 0.0):.3f})\n"
        f"• Net Rating: {rec.get('net_rtg', 0.0):+.1f}\n"
        f"• Beautiful Game Index: {bg.get('beautiful_game_index', 0.0):.0f}/100\n"
        f"• Assisted Basket Rate: {bg.get('assisted_fg_pct', 0.0) * 100:.1f}%\n\n"
        f"Another blow on the rock.\n"
        f"📊 {site_url}/dashboard.html\n"
        f"#GoSpursGo #PoundTheRock"
    )
    return tweet


def generate_gameday_tweet(player_logs: pd.DataFrame, site_url: str = DEFAULT_SITE_URL) -> str:
    """Generate Pre-Game Matchup & Prop Intel tweet."""
    wemby = get_wemby_logs(player_logs)
    if wemby.empty:
        return "No player logs found."

    total_g = len(wemby)
    over_3_5 = int((wemby["blk"] > 3.5).sum())
    over_pct = (over_3_5 / total_g * 100) if total_g > 0 else 0.0
    l5 = wemby.tail(5)
    l5_over = int((l5["blk"] > 3.5).sum())

    tweet = (
        f"🎲 SPURS GAMEDAY & PROP INTEL\n\n"
        f"Wemby 3.5 BLK Consensus Line:\n"
        f"• Season Hit Rate: {over_3_5}/{total_g} ({over_pct:.1f}% OVER)\n"
        f"• Last 5 Games: {l5_over}/{len(l5)} OVER\n"
        f"• Season Mean: {wemby['blk'].mean():.2f} ± {wemby['blk'].std():.2f} BLK\n\n"
        f"Strictly empirical numbers with standard deviations.\n"
        f"Props Board: {site_url}/props_board.html\n"
        f"#GoSpursGo #NBATwitter #Props"
    )
    return tweet


def generate_rodeo_tweet(games: pd.DataFrame, site_url: str = DEFAULT_SITE_URL) -> str:
    """Generate Rodeo Road Trip marathon split tweet."""
    segmented = segment_rodeo_games(games)
    splits = rodeo_split_metrics(segmented)
    rrt = splits.get("Active RRT", {})

    tweet = (
        f"🤠 RODEO ROAD TRIP SPLIT TRACKER\n\n"
        f"The February road crucible:\n"
        f"• Active RRT Record: {rrt.get('record', '0-0')}\n"
        f"• Average Margin: {rrt.get('avg_margin', 0.0):+.1f} PPG\n"
        f"• Net Rating: {rrt.get('net_rtg', 0.0):+.1f}\n\n"
        f"Championship Standards:\n"
        f"🏆 2003 Title Team: 8-1\n"
        f"🏆 2014 Title Team: 6-3\n\n"
        f"Historical split & fatigue curve:\n"
        f"🔗 {site_url}/rodeo_road_trip.html\n"
        f"#GoSpursGo #RodeoRoadTrip"
    )
    return tweet


def generate_roster_tweet(player_logs: pd.DataFrame, site_url: str = DEFAULT_SITE_URL) -> str:
    """Generate Young Core & Rotation distribution tweet."""
    if player_logs.empty:
        return "No player logs found in cache."

    # Top rotation players excluding Wemby to highlight the rest of the squad
    non_wemby = player_logs[~player_logs["player_name"].str.contains("Wembanyama", case=False, na=False)]
    agg = non_wemby.groupby("player_name").agg(
        pts=("pts", "mean"),
        ast=("ast", "mean"),
        games=("game_id", "count"),
    ).reset_index()

    agg = agg[agg["games"] >= 3].sort_values("pts", ascending=False)
    leaders = agg.head(3)

    leader_lines = []
    for _, r in leaders.iterrows():
        leader_lines.append(f"• {r['player_name']}: {r['pts']:.1f} PTS | {r['ast']:.1f} AST")

    lines_str = "\n".join(leader_lines)

    tweet = (
        f"🏛️ SPURS ROTATION PULSE\n\n"
        f"Supporting core & young development:\n"
        f"{lines_str}\n\n"
        f"Tracking rotation depth, second-unit scoring, and playmaking chemistry.\n"
        f"Full Roster Matrix:\n"
        f"📊 {site_url}/dashboard.html\n"
        f"#GoSpursGo #PorVida #SpursFamily"
    )
    return tweet


def generate_clutch_tweet(games: pd.DataFrame, site_url: str = DEFAULT_SITE_URL) -> str:
    """Generate Clutch & Late-Game execution tweet."""
    f = games[games["status"] == "Final"].copy()
    if f.empty or "margin" not in f.columns:
        return "No completed games with margin data."

    clutch_games = f[f["margin"].abs() <= 5]
    total_clutch = len(clutch_games)
    clutch_w = int((clutch_games["result"] == "W").sum())
    clutch_l = total_clutch - clutch_w
    clutch_pct = (clutch_w / total_clutch * 100) if total_clutch > 0 else 0.0

    tweet = (
        f"⏱️ SPURS CRUNCH-TIME LEDGER\n\n"
        f"Games decided by 5 points or less:\n"
        f"• Record: {clutch_w}-{clutch_l} ({clutch_pct:.1f}%)\n"
        f"• Total Clutch Contests: {total_clutch}/{len(f)} games\n\n"
        f"How the young Spurs close in the 4th quarter dictates the season ceiling.\n"
        f"Margin & Clutch Split:\n"
        f"📈 {site_url}/dashboard.html\n"
        f"#GoSpursGo #PoundTheRock"
    )
    return tweet


def generate_prediction_tweet(games: pd.DataFrame, opp: str = "HOU", site_url: str = DEFAULT_SITE_URL) -> str:
    """Generate predictive matchup and beatdown forecast tweet."""
    from analysis.predictions import predict_matchup
    pred = predict_matchup(games, opp, is_home=True)
    margin = pred["projected_margin"]
    mar_sign = "+" if margin > 0 else ""

    tweet = (
        f"🎯 MATCHUP & BEATDOWN FORECAST • vs {pred['opponent_abbr']}\n\n"
        f"Model Projections:\n"
        f"• Final: Spurs {pred['projected_spurs_pts']:.0f} - {pred['projected_opp_pts']:.0f} ({mar_sign}{margin:.1f} PTS)\n"
        f"• Win Probability: {pred['win_probability_pct']}%\n"
        f"• Double-Digit (+10) Beatdown Chance: {pred['prob_double_digit_pct']}%\n"
        f"• 15+ Pt Blowout Odds: {pred['prob_blowout_pct']}%\n\n"
        f"Outlook: {pred['beatdown_tier']}\n"
        f"Full 29-Team Radar:\n"
        f"🔗 {site_url}/matchup.html\n"
        f"#GoSpursGo #PorVida #NBAPredictions"
    )
    return tweet


def display_tweet(console: Console, title: str, tweet_text: str) -> None:
    """Display tweet text with character counter and warning if over 280 chars."""
    char_count = len(tweet_text)
    count_style = "green" if char_count <= 280 else "red"

    header = f"{title} [{count_style}]({char_count} / 280 chars)[/{count_style}]"
    console.print(Panel(tweet_text, title=header, border_style=count_style))


def main() -> None:
    parser = argparse.ArgumentParser(description="Spurs Tracker Twitter/X Content Generator.")
    parser.add_argument("--mode", choices=["wemby", "postgame", "gameday", "rodeo", "roster", "clutch", "predict", "all"], default="all")
    parser.add_argument("--opponent", default="HOU", help="Opponent abbreviation for match prediction (default: HOU)")
    parser.add_argument("--team", default=TEAM_ABBR)
    parser.add_argument("--season", type=int, default=SEASON)
    parser.add_argument("--url", default=DEFAULT_SITE_URL, help="Base website URL")
    args = parser.parse_args()

    fetcher = Fetcher(team_id=config.TEAMS[args.team]["id"], season=args.season)
    try:
        games = fetcher.load("games")
        player_logs = fetcher.load("player_game_log")
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        sys.exit(1)

    wemby_logs = get_wemby_logs(player_logs)

    console.rule("[bold cyan]🐦 Spurs Tracker &bull; Twitter / X Content Generator[/bold cyan]")

    modes_to_run = ["postgame", "predict", "roster", "clutch", "gameday", "rodeo", "wemby"] if args.mode == "all" else [args.mode]

    for m in modes_to_run:
        if m == "wemby":
            text = generate_wemby_tweet(wemby_logs, games, args.url)
            display_tweet(console, "👽 Wemby Horizon Alert", text)
        elif m == "postgame":
            text = generate_postgame_tweet(games, player_logs, args.url)
            display_tweet(console, "🔨 Stonecutter Post-Game Ledger", text)
        elif m == "predict":
            text = generate_prediction_tweet(games, args.opponent, args.url)
            display_tweet(console, f"🎯 Beatdown Forecast vs. {args.opponent}", text)
        elif m == "roster":
            text = generate_roster_tweet(player_logs, args.url)
            display_tweet(console, "🏛️ Young Core & Rotation Pulse", text)
        elif m == "clutch":
            text = generate_clutch_tweet(games, args.url)
            display_tweet(console, "⏱️ Crunch-Time & Margin Ledger", text)
        elif m == "gameday":
            text = generate_gameday_tweet(player_logs, args.url)
            display_tweet(console, "🎲 Gameday Matchup & Props", text)
        elif m == "rodeo":
            text = generate_rodeo_tweet(games, args.url)
            display_tweet(console, "🤠 Rodeo Road Trip Tracker", text)


if __name__ == "__main__":
    main()
