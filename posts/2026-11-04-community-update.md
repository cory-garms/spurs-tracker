# r/NBASpurs — La Tabla Spurs feature update

Status: draft for Cory to edit and publish manually. No post has been submitted.
Content ID: `r00_update`. Baseline: Cory's prior introduction roughly one week ago,
which already covered team trends, player pages, Wemby Lab, matchup previews, and
small-sample notices. Those are not new features in this update.

Before submitting, confirm current subreddit permission and flair as described
in [the social calendar](../marketing/social-calendar.md). Suggested attachment:
a screenshot of `dashboard.html#honor-roll` showing the new season honors.

## Title

La Tabla Spurs is growing and we want your feedback [OC]

## Body

Hey Spurs fans,

I shared La Tabla Spurs here last week and wanted to follow up with a few things
I've added since then:

- **A season honors board:** every completed game now has a row showing the
  result, Player of the Game, and his top teammate, with their stat lines and
  Game Scores together.
- **El Compinche / Wingman:** alongside El Valiente, the Player of the Game,
  there's now recognition for the next-highest Game Score on the team. I wanted
  a way to highlight the supporting performances too.
- **Honors on player pages:** you can see how many times each player has earned
  those awards over the season.
- **Refreshed artwork:** updated player emblems and a new GSG lotería logo.

The honors are based on Game Score, so they're a consistent box-score measure,
not a claim to capture everything a player did defensively or away from the ball.

Here's the honors board:

https://porvida.corygarms.com/dashboard.html#honor-roll

What would you add alongside Game Score to give the supporting players their
due? I'd be interested in what you think the box score misses.

Still a personal project, and I'm happy to hear what's useful or needs work.

GSG!!

## Tracking and claim verification

Optional tagged version of the destination, using the same campaign convention:

`https://porvida.corygarms.com/dashboard.html?utm_source=reddit&utm_medium=social&utm_campaign=sponsor_sprint_202611&utm_content=r00_update#honor-roll`

The copy uses no current score, record, opponent, or “last night” claim, so it
does not become stale after the next game. If adding an example, check the
deployed table and explicitly name the game's date first.

Feature evidence: commit `f588077` added Compinche awards, the season-honors
table, and player tallies; `03840fa` uses “Wingman.” Commit `fe24eec` refreshed
player emblems; `6926a0c` supplied the GSG landing and social logos.
The separate Compinche landing card and landing honors link were subsequently
removed intentionally; the draft points directly to the dashboard table.
