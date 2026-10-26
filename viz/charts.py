"""
Individual Plotly chart functions — dark theme.

Each function accepts DataFrames from the analysis modules and returns
a plotly.graph_objects.Figure ready to display or export.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

from viz import theme

# ---------------------------------------------------------------------------
# Spurs Silver & Black + Fiesta design system (mapped from viz.theme)
# ---------------------------------------------------------------------------

_BG           = theme.FROST_BANK_FLOOR
_PAPER_BG     = theme.SILVER_SLATE
_SHADOW_BG    = theme.SHADOW_BLACK
_GRID         = theme.COURT_LINE
_TEXT         = theme.COURT_WHITE
_GREEN        = theme.FIESTA_TEAL
_RED          = theme.FIESTA_FUSCHIA
_BLUE         = theme.SPURS_SILVER
_YELLOW       = theme.FIESTA_ORANGE
_DIM          = theme.TEXT_MUTED
_SPURS_SILVER = theme.SPURS_SILVER
_SPURS_STEEL  = theme.SPURS_STEEL
_SPURS_BLACK  = theme.FROST_BANK_FLOOR
_GOLD         = theme.HARDWOOD_GOLD


def _apply_theme(fig: go.Figure, **extra) -> go.Figure:
    """Apply the official Spurs theme layout to a Plotly figure."""
    return theme.apply(fig, **extra)


# ---------------------------------------------------------------------------
# Season timeline  (cumulative W-L)
# ---------------------------------------------------------------------------

def season_timeline(games: pd.DataFrame, team_name: str) -> go.Figure:
    """Cumulative wins and losses with a .500 pace reference line."""
    f = games[games["status"] == "Final"].sort_values("game_date").reset_index(drop=True)
    if f.empty:
        return go.Figure()

    f["cum_w"]    = (f["result"] == "W").cumsum()
    f["cum_l"]    = (f["result"] == "L").cumsum()
    f["game_n"]   = range(1, len(f) + 1)
    f["pace_500"] = f["game_n"] / 2

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=f["game_n"], y=f["cum_w"],
        name="Wins", mode="lines",
        line=dict(color=_GREEN, width=2),
        hovertemplate="Game %{x}<br>Wins: %{y}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=f["game_n"], y=f["cum_l"],
        name="Losses", mode="lines",
        line=dict(color=_RED, width=2),
        hovertemplate="Game %{x}<br>Losses: %{y}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=f["game_n"], y=f["pace_500"],
        name=".500 Pace", mode="lines",
        line=dict(color=_DIM, width=1, dash="dot"),
    ))
    _apply_theme(fig,
        title=dict(text=f"{team_name} — Season Timeline", font=dict(size=16)),
        xaxis_title="Game Number",
        yaxis_title="Cumulative Total",
    )
    return fig


# ---------------------------------------------------------------------------
# Rolling win%  (5-game and 10-game windows)
# ---------------------------------------------------------------------------

def rolling_win_pct_chart(
    games: pd.DataFrame,
    team_name: str,
    windows: list[int] | None = None,
) -> go.Figure:
    """Rolling win% for each window with a .500 reference line."""
    if windows is None:
        windows = [5, 10]

    f = games[games["status"] == "Final"].sort_values("game_date").reset_index(drop=True)
    if f.empty:
        return go.Figure()

    f["win_flag"] = (f["result"] == "W").astype(int)
    colors = [_GREEN, _BLUE, _YELLOW, _GOLD]

    fig = go.Figure()
    for i, w in enumerate(windows):
        roll = f["win_flag"].rolling(w).mean()
        fig.add_trace(go.Scatter(
            x=f["game_date"], y=roll,
            name=f"{w}-Game Win%",
            mode="lines",
            line=dict(color=colors[i % len(colors)], width=2),
            hovertemplate="%{x}<br>Win%%: %{y:.3f}<extra></extra>",
        ))

    fig.add_hline(y=0.500, line_dash="dot", line_color=_DIM, annotation_text=".500")
    _apply_theme(fig,
        title=dict(text=f"{team_name} — Rolling Win%", font=dict(size=16)),
        xaxis_title="Date",
        yaxis_title="Win%",
        yaxis_range=[0, 1],
    )
    return fig


# ---------------------------------------------------------------------------
# Score margin per game (bar chart)
# ---------------------------------------------------------------------------

def score_margin_chart(games: pd.DataFrame, team_name: str) -> go.Figure:
    """
    Per-game bar chart: margin (positive = win, negative = loss).
    Overlays cumulative margin as a line.
    """
    f = games[games["status"] == "Final"].sort_values("game_date").reset_index(drop=True)
    if f.empty:
        return go.Figure()

    f["cum_margin"] = f["margin"].cumsum()
    f["color"]      = f["result"].map({"W": _GREEN, "L": _RED})
    f["game_n"]     = range(1, len(f) + 1)
    f["hover"]      = f.apply(
        lambda r: f"Game {int(r['game_n'])} ({r['game_date']})<br>"
                  f"{int(r['pts'])}-{int(r['opp_pts'])}  {r['result']}  "
                  f"vs {r.get('opponent_abbr', '')}",
        axis=1,
    )

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(
            x=f["game_n"], y=f["margin"],
            marker_color=f["color"].tolist(),
            name="Margin",
            hovertext=f["hover"],
            hoverinfo="text",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=f["game_n"], y=f["cum_margin"],
            name="Cumulative",
            mode="lines",
            line=dict(color=_BLUE, width=2),
            hovertemplate="Game %{x}<br>Cumulative: %{y:+d}<extra></extra>",
        ),
        secondary_y=True,
    )
    fig.add_hline(y=0, line_color=_DIM, line_width=1)
    _apply_theme(fig,
        title=dict(text=f"{team_name} — Score Margin per Game", font=dict(size=16)),
        xaxis_title="Game Number",
    )
    fig.update_yaxes(title_text="Game Margin", secondary_y=False, gridcolor=_GRID)
    fig.update_yaxes(title_text="Cumulative",  secondary_y=True,  gridcolor=_GRID)
    return fig


# ---------------------------------------------------------------------------
# Streak timeline
# ---------------------------------------------------------------------------

def streak_timeline_chart(streak_df: pd.DataFrame, team_name: str) -> go.Figure:
    """
    Bar chart: positive = win-streak length, negative = loss-streak length.
    """
    if streak_df.empty:
        return go.Figure()

    colors = [_GREEN if v > 0 else _RED for v in streak_df["streak_value"]]
    fig = go.Figure(go.Bar(
        x=streak_df["game_date"],
        y=streak_df["streak_value"],
        marker_color=colors,
        hovertemplate="%{x}<br>Streak: %{y}<extra></extra>",
    ))
    fig.add_hline(y=0, line_color=_DIM, line_width=1)
    _apply_theme(fig,
        title=dict(text=f"{team_name} — Streak Timeline", font=dict(size=16)),
        xaxis_title="Date",
        yaxis_title="Loss Streak  |  Win Streak",
    )
    return fig


# ---------------------------------------------------------------------------
# Scoring trend (rolling pts + opp pts)
# ---------------------------------------------------------------------------

def scoring_trend_chart(
    games: pd.DataFrame, team_name: str, window: int = 10
) -> go.Figure:
    """Rolling points scored vs. opponent points over the season."""
    f = games[games["status"] == "Final"].sort_values("game_date").reset_index(drop=True)
    if f.empty:
        return go.Figure()

    f["roll_pts"]     = f["pts"].rolling(window).mean()
    f["roll_opp_pts"] = f["opp_pts"].rolling(window).mean()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=f["game_date"], y=f["roll_pts"],
        name=f"Pts ({window}-game avg)", mode="lines",
        line=dict(color=_GREEN, width=2),
        hovertemplate="%{x}<br>Pts avg: %{y:.1f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=f["game_date"], y=f["roll_opp_pts"],
        name=f"Opp Pts ({window}-game avg)", mode="lines",
        line=dict(color=_RED, width=2),
        hovertemplate="%{x}<br>Opp Pts avg: %{y:.1f}<extra></extra>",
    ))
    _apply_theme(fig,
        title=dict(text=f"{team_name} — Scoring Trend ({window}-Game Rolling)", font=dict(size=16)),
        xaxis_title="Date",
        yaxis_title="Points",
    )
    return fig


# ---------------------------------------------------------------------------
# Player scoring leaderboard heatmap
# ---------------------------------------------------------------------------

def player_scoring_leaderboard(
    player_logs: pd.DataFrame, team_name: str, min_games: int = 10
) -> go.Figure:
    """
    Heatmap: players (rows) x stats (cols), z-score shading.
    Green = above team average, red = below.
    """
    from analysis.offense import player_season_averages

    avgs = player_season_averages(player_logs, min_games)
    if avgs.empty:
        return go.Figure()

    stats  = ["pts", "reb", "ast", "stl", "blk", "fg_pct", "fg3_pct", "ts_pct", "usg_pct"]
    labels = ["PTS", "REB", "AST", "STL", "BLK", "FG%", "3P%", "TS%", "USG%"]

    df = avgs.sort_values("pts", ascending=False).reset_index(drop=True)
    available       = [s for s in stats if s in df.columns]
    avail_labels    = [labels[stats.index(s)] for s in available]

    z_matrix    = []
    text_matrix = []
    for stat in available:
        col  = df[stat].fillna(0).astype(float)
        std  = col.std()
        mean = col.mean()
        z    = (col - mean) / std if std > 0 else col * 0
        z_matrix.append(z.tolist())
        text_matrix.append([
            f"{v:.3f}" if stat in ("fg_pct", "fg3_pct", "ts_pct") else
            f"{v:.1f}%" if stat == "usg_pct" else
            f"{v:.1f}"
            for v in col
        ])

    fig = go.Figure(go.Heatmap(
        z=list(map(list, zip(*z_matrix))),
        x=avail_labels,
        y=df["player_name"].tolist(),
        text=list(map(list, zip(*text_matrix))),
        texttemplate="%{text}",
        colorscale=[[0, _RED], [0.5, _BG], [1, _GREEN]],
        showscale=False,
        hovertemplate="%{y}  %{x}: %{text}<extra></extra>",
    ))
    _apply_theme(fig,
        title=dict(text=f"{team_name} — Player Stats (z-score shading)", font=dict(size=16)),
        height=max(400, len(df) * 30 + 100),
    )
    return fig


# ---------------------------------------------------------------------------
# Hot / cold chart
# ---------------------------------------------------------------------------

def hot_cold_chart(hot_cold: pd.DataFrame, team_name: str) -> go.Figure:
    """Horizontal bar: each player's L5 pts delta vs. season average."""
    if hot_cold.empty:
        return go.Figure()

    df = hot_cold.sort_values("delta").reset_index(drop=True)
    colors = [
        _GREEN if d >= 3.0 else (_RED if d <= -3.0 else _DIM)
        for d in df["delta"]
    ]

    fig = go.Figure(go.Bar(
        x=df["delta"],
        y=df["player_name"],
        orientation="h",
        marker_color=colors,
        hovertemplate="%{y}<br>Delta Pts: %{x:+.1f}<extra></extra>",
    ))
    fig.add_vline(x=0,    line_color=_DIM,   line_width=1)
    fig.add_vline(x=3.0,  line_dash="dot", line_color=_GREEN, annotation_text="Hot")
    fig.add_vline(x=-3.0, line_dash="dot", line_color=_RED,   annotation_text="Cold")

    _apply_theme(fig,
        title=dict(text=f"{team_name} — Hot / Cold (L5 Pts vs. Season Avg)", font=dict(size=16)),
        xaxis_title="Pts Delta",
        height=max(400, len(df) * 25 + 100),
    )
    return fig


# ---------------------------------------------------------------------------
# Shot efficiency scatter (usg_pct vs ts_pct)
# ---------------------------------------------------------------------------

def shot_efficiency_chart(player_logs: pd.DataFrame, team_name: str) -> go.Figure:
    """
    Scatter: usage rate (x) vs. true shooting % (y).
    Quadrant lines at team-average usg and ts.
    """
    from analysis.offense import player_season_averages

    avgs = player_season_averages(player_logs, min_games=10)
    if avgs.empty or "usg_pct" not in avgs.columns:
        return go.Figure()

    avg_usg = float(avgs["usg_pct"].mean())
    avg_ts  = float(avgs["ts_pct"].mean())

    fig = go.Figure(go.Scatter(
        x=avgs["usg_pct"],
        y=avgs["ts_pct"],
        mode="markers+text",
        text=avgs["player_name"],
        textposition="top center",
        marker=dict(
            size=10,
            color=avgs["pts"],
            colorscale=[[0, _DIM], [0.5, _BLUE], [1, _GREEN]],
            showscale=True,
            colorbar=dict(title="Pts/G"),
        ),
        hovertemplate="%{text}<br>USG%: %{x:.1f}<br>TS%: %{y:.3f}<extra></extra>",
    ))

    fig.add_vline(x=avg_usg, line_dash="dot", line_color=_DIM,
                  annotation_text=f"Avg USG {avg_usg:.1f}%")
    fig.add_hline(y=avg_ts,  line_dash="dot", line_color=_DIM,
                  annotation_text=f"Avg TS {avg_ts:.3f}")

    _apply_theme(fig,
        title=dict(text=f"{team_name} — Usage Rate vs. True Shooting%", font=dict(size=16)),
        xaxis_title="Usage Rate (%)",
        yaxis_title="True Shooting%",
    )
    return fig


# ---------------------------------------------------------------------------
# Defensive rating trend
# ---------------------------------------------------------------------------

def defensive_rating_trend(games: pd.DataFrame, team_name: str) -> go.Figure:
    """Rolling defensive rating trend chart."""
    from analysis.defense import defensive_ratings_trend

    trend = defensive_ratings_trend(games, window=10)
    if trend.empty:
        return go.Figure()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=trend.index, y=trend["drtg"],
        name="DRtg (game)", mode="lines",
        line=dict(color=_DIM, width=1),
        opacity=0.4,
    ))
    fig.add_trace(go.Scatter(
        x=trend.index, y=trend["rolling_drtg"],
        name="DRtg (10-game avg)", mode="lines",
        line=dict(color=_BLUE, width=2),
        hovertemplate="%{x}<br>10-Game DRtg: %{y:.1f}<extra></extra>",
    ))
    # Lower is better for defensive rating
    avg_drtg = float(trend["drtg"].mean())
    fig.add_hline(y=avg_drtg, line_dash="dot", line_color=_YELLOW,
                  annotation_text=f"Season avg {avg_drtg:.1f}")

    _apply_theme(fig,
        title=dict(text=f"{team_name} — Defensive Rating Trend (10-Game Rolling)", font=dict(size=16)),
        xaxis_title="Date",
        yaxis_title="Defensive Rating",
    )
    return fig


# ---------------------------------------------------------------------------
# Historical win% bar chart
# ---------------------------------------------------------------------------

def multi_season_win_pct(
    historical: pd.DataFrame,
    team_name: str,
    highlight_seasons: dict[str, str] | None = None,
) -> go.Figure:
    """Bar chart of win% per season with notable season annotations."""
    if historical.empty:
        return go.Figure()

    df = historical.sort_values("season")
    colors = [
        _YELLOW if (highlight_seasons and s in highlight_seasons) else _BLUE
        for s in df["season"]
    ]

    fig = go.Figure(go.Bar(
        x=df["season"].astype(str),
        y=df["win_pct"],
        marker_color=colors,
        text=df.apply(lambda r: f"{r['wins']}-{r['losses']}", axis=1),
        textposition="outside",
        hovertemplate="%{x}: %{y:.3f} Win%<br>%{text}<extra></extra>",
    ))

    if highlight_seasons:
        for ssn, label in highlight_seasons.items():
            row = df[df["season"] == ssn]
            if not row.empty:
                fig.add_annotation(
                    x=ssn, y=float(row["win_pct"].iloc[0]) + 0.025,
                    text="*", showarrow=False, font=dict(size=16, color=_YELLOW),
                )

    fig.add_hline(y=0.500, line_dash="dot", line_color=_DIM, annotation_text=".500")
    _apply_theme(fig,
        title=dict(text=f"{team_name} — Win% by Season", font=dict(size=16)),
        xaxis_title="Season",
        yaxis_title="Win%",
        yaxis_range=[0, 0.85],
        xaxis_tickangle=45,
        height=500,
    )
    return fig


# ---------------------------------------------------------------------------
# Pace comparison chart
# ---------------------------------------------------------------------------

def pace_comparison_chart(
    current_games: pd.DataFrame,
    historical_seasons: dict[int, pd.DataFrame],
    team_name: str,
) -> go.Figure:
    """Multi-line cumulative win% by game number."""
    fig = go.Figure()
    colors_pool = [_BLUE, _YELLOW, _GREEN, _RED, "#a371f7", "#79c0ff"]

    def _cum_win_pct(df: pd.DataFrame) -> pd.Series:
        f = df[df["status"] == "Final"].sort_values("game_date").reset_index(drop=True)
        f["win_flag"] = (f["result"] == "W").astype(int)
        f["game_n"]   = range(1, len(f) + 1)
        f["cum_pct"]  = f["win_flag"].expanding().mean()
        return f.set_index("game_n")["cum_pct"]

    for i, (year, df) in enumerate(historical_seasons.items()):
        pct = _cum_win_pct(df)
        fig.add_trace(go.Scatter(
            x=pct.index, y=pct.values,
            name=str(year),
            mode="lines",
            line=dict(color=colors_pool[i % len(colors_pool)], width=1, dash="dot"),
            opacity=0.6,
        ))

    curr_pct = _cum_win_pct(current_games)
    season   = current_games["season"].iloc[0] if not current_games.empty else "Current"
    fig.add_trace(go.Scatter(
        x=curr_pct.index, y=curr_pct.values,
        name=f"{season} (current)",
        mode="lines",
        line=dict(color=_TEXT, width=3),
    ))

    fig.add_hline(y=0.500, line_dash="dot", line_color=_DIM, annotation_text=".500")
    _apply_theme(fig,
        title=dict(text=f"{team_name} — Season Pace Comparison", font=dict(size=16)),
        xaxis_title="Game Number",
        yaxis_title="Cumulative Win%",
        yaxis_range=[0.2, 0.9],
    )
    return fig


# ---------------------------------------------------------------------------
# Full Roster Production Matrix
# ---------------------------------------------------------------------------

def roster_production_matrix(player_logs: pd.DataFrame, team_name: str, top_n: int = 10) -> go.Figure:
    """
    Multi-metric comparison for top rotation players: PPG, RPG, APG, and TS%.
    Provides a full-team view beyond any single player.
    """
    if player_logs.empty:
        return go.Figure()

    agg = player_logs.groupby("player_name").agg(
        games=("game_id", "count"),
        pts=("pts", "mean"),
        reb=("reb", "mean"),
        ast=("ast", "mean"),
        ts_pct=("ts_pct", "mean"),
        plus_minus=("plus_minus", "mean"),
        minutes=("min", "mean"),
    ).reset_index()

    # Filter to players with at least 5 games or top by minutes
    agg = agg[agg["games"] >= 3].sort_values("pts", ascending=True).tail(top_n)
    if agg.empty:
        return go.Figure()

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=agg["player_name"],
        x=agg["pts"].round(1),
        name="PTS",
        orientation="h",
        marker=dict(color=_SPURS_SILVER),
        hovertemplate="%{y}<br>PTS: %{x:.1f}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        y=agg["player_name"],
        x=agg["reb"].round(1),
        name="REB",
        orientation="h",
        marker=dict(color=_GREEN),
        hovertemplate="%{y}<br>REB: %{x:.1f}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        y=agg["player_name"],
        x=agg["ast"].round(1),
        name="AST",
        orientation="h",
        marker=dict(color=_YELLOW),
        hovertemplate="%{y}<br>AST: %{x:.1f}<extra></extra>",
    ))

    _apply_theme(fig,
        title=dict(text=f"{team_name} — Rotation Core Production (Top {len(agg)} Players)", font=dict(size=16)),
        barmode="group",
        xaxis_title="Per Game Average",
        yaxis_title="",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=max(400, len(agg) * 36 + 100),
    )
    return fig


# ---------------------------------------------------------------------------
# Clutch & Margin Distribution
# ---------------------------------------------------------------------------

def clutch_margin_distribution(games: pd.DataFrame, team_name: str) -> go.Figure:
    """
    Distribution of game outcomes by margin:
      - Blowout Wins (+15+)
      - Decisive Wins (+6 to +14)
      - Clutch Wins (+1 to +5)
      - Clutch Losses (-1 to -5)
      - Decisive Losses (-6 to -14)
      - Blowout Losses (-15+)
    Adapts to any season outcome (blowout heavy, nail-biter heavy, etc.).
    """
    f = games[games["status"] == "Final"].copy()
    if f.empty or "margin" not in f.columns:
        return go.Figure()

    bins = [-999, -15, -6, 0, 5, 14, 999]
    labels = [
        "Blowout Loss (-15+)",
        "Decisive Loss (-6 to -14)",
        "Clutch Loss (-1 to -5)",
        "Clutch Win (+1 to +5)",
        "Decisive Win (+6 to +14)",
        "Blowout Win (+15+)",
    ]
    colors = [
        _RED,
        "#d35d79",
        "#a87c88",
        "#69b8b2",
        _GREEN,
        _YELLOW,
    ]

    f["margin_bucket"] = pd.cut(f["margin"], bins=bins, labels=labels)
    counts = f["margin_bucket"].value_counts().reindex(labels, fill_value=0)

    fig = go.Figure(go.Bar(
        x=counts.index,
        y=counts.values,
        marker=dict(color=colors),
        text=counts.values,
        textposition="outside",
        hovertemplate="%{x}: %{y} games<extra></extra>",
    ))

    _apply_theme(fig,
        title=dict(text=f"{team_name} — Game Margin & Clutch Distribution", font=dict(size=16)),
        xaxis_title="Outcome Tier",
        yaxis_title="Number of Games",
        xaxis_tickangle=-20,
        height=380,
    )
    return fig


# ---------------------------------------------------------------------------
# Starter vs. Bench Contribution Split
# ---------------------------------------------------------------------------

def starter_bench_production_chart(player_logs: pd.DataFrame, team_name: str) -> go.Figure:
    """
    Compare aggregate scoring, rebounding, and playmaking between
    starting rotation and second unit.
    """
    if player_logs.empty:
        return go.Figure()

    per_game = player_logs.groupby(["player_id", "player_name"]).agg(
        games=("game_id", "count"),
        avg_min=("min", "mean"),
        pts=("pts", "mean"),
        reb=("reb", "mean"),
        ast=("ast", "mean"),
    ).reset_index()

    if len(per_game) < 5:
        return go.Figure()

    top5_ids = set(per_game.nlargest(5, "avg_min")["player_id"])
    starters = per_game[per_game["player_id"].isin(top5_ids)]
    bench = per_game[~per_game["player_id"].isin(top5_ids)]

    categories = ["Total PTS/G", "Total REB/G", "Total AST/G"]
    starter_vals = [
        round(starters["pts"].sum(), 1),
        round(starters["reb"].sum(), 1),
        round(starters["ast"].sum(), 1),
    ]
    bench_vals = [
        round(bench["pts"].sum(), 1),
        round(bench["reb"].sum(), 1),
        round(bench["ast"].sum(), 1),
    ]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=categories,
        y=starter_vals,
        name="Starting 5 Unit",
        marker=dict(color=_SPURS_SILVER),
        text=starter_vals,
        textposition="outside",
    ))
    fig.add_trace(go.Bar(
        x=categories,
        y=bench_vals,
        name="Second Unit (Bench)",
        marker=dict(color=_GREEN),
        text=bench_vals,
        textposition="outside",
    ))

    _apply_theme(fig,
        title=dict(text=f"{team_name} — Starting 5 vs. Second Unit Output", font=dict(size=16)),
        barmode="group",
        yaxis_title="Aggregate Output",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=360,
    )
    return fig

