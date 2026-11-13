"""Shared, source-dated availability context for matchup and props pages."""

from __future__ import annotations

from datetime import datetime
from html import escape

import config
from data.schedule import LOCAL_TZ


def status_badge(status: str) -> str:
    if not status:
        return ""
    color = "fuschia" if status == "Out" else "teal" if status == "Available" else "orange"
    return f' <span class="badge {color}">{escape(status)}</span>'


def availability_html(snapshot: dict) -> str:
    if not snapshot:
        return ""
    reported = datetime.fromisoformat(snapshot["reported_at"]).astimezone(LOCAL_TZ)
    when = f"{reported:%b} {reported.day}, {reported.year} · {reported:%-I:%M %p} CT"
    teams = []
    for team, players in snapshot["teams"].items():
        rows = "".join(
            f'<li><strong>{escape(p["name"])}</strong>{status_badge(p["status"])}'
            f'<small>{escape(p["reason"])}</small></li>' for p in players
        )
        teams.append(f'<div><h3>{escape(config.TEAMS[team]["name"])}</h3><ul>{rows}</ul></div>')
    return f"""<section class="card game-availability" aria-label="Player availability">
      <h2>Availability</h2>
      <p class="availability-source">NBA injury report as of <time datetime="{escape(snapshot['reported_at'], quote=True)}">{when}</time>.
        <a href="{escape(snapshot['source_url'], quote=True)}" target="_blank" rel="noopener">Official report</a></p>
      <div class="availability-teams">{''.join(teams)}</div>
      <p class="availability-source">Report snapshot; statuses may change before tipoff.</p>
    </section>"""
