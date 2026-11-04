# Social distribution calendar — November 5–18

Owner/publisher: Cory. No automated publishing. Primary objective: qualified
visits and return readership at https://porvida.corygarms.com.

## Channel setup — complete Nov 6

| Channel | Handle / selected? | Intended use |
| --- | --- | --- |
| X | TBD | Primary daily insight and conversation, if account available |
| Instagram or another owned visual account | TBD | Four adapted visual posts; bio or story link where supported |
| Bluesky | Optional / TBD | Adapt selected text posts; separate tagged links |
| Facebook page or relevant group | Optional / TBD | Weekly analysis where group rules allow |
| r/NBASpurs | Existing post confirmed by Cory; moderation permission to verify | Return with a concrete feature update; at most one useful contribution per week under this plan |

Use the channels you actually own or can participate in. Do not create accounts
or assume cross-posting permission as part of this plan. If a primary account is
unavailable, name the substitute and adjust post-count targets in the sprint.

## Immediate community update — before the sprint

Cory shared the previous r/NBASpurs introduction, posted roughly a week earlier.
It already described player pages, Wemby Lab, matchup previews, and small-sample
notices. Do not present those as new additions.

[The November 4 update draft](../posts/2026-11-04-community-update.md) focuses on
new season honors, El Compinche, player honor counts, and refreshed branding.
Content ID: `r00_update`; status: draft, not published. If posted Nov 4, record it
outside the Nov 5–18 sprint totals and use it as a pre-sprint comparison.
If published during the sprint, count it once in that period and replace the
first planned Reddit contribution rather than adding another promotional post.

[r/NBASpurs rules](https://www.reddit.com/r/NBASpurs/) checked November 4 require
moderator permission for self-promotion, prior active engagement, participation
in the submission, and appropriate flair. Verify whether existing permission
covers this update; if not, Cory should request it before submitting. The rule
also excludes personal social-media promotion: link the site, not social accounts.
The rules flag low-effort/AI-slop posts; Cory should edit the draft in his own
voice and include a useful screenshot or specific basketball discussion.
No moderator contact has been made by creating this plan.

## Daily publishing workflow

1. Verify the data window and latest completed game before making statistical
   claims. On game days, use the completed result only after cache validation;
   otherwise publish the evergreen topic below. No matchups or dates are assumed.
2. Write one useful observation that stands alone, name its sample/window, then
   link to the relevant page. Invite a specific basketball discussion.
3. Use the banner logo for site introductions; use a readable chart or player
   image for analysis. Adapt aspect ratio and caption to each channel.
4. Publish the primary post around noon ET for evergreen material, or after a
   verified postgame build. These are starting times to test, not proven best times.
5. Adapt eligible posts to selected secondary channels. On Reddit, write a native
   explanation rather than a bare promotional link; check current rules and stop
   promotional posting if moderators or the community object.
6. Spend 15 minutes answering comments and contributing useful analysis. Log
   channel, URL, publication timestamp, content ID, destination, and UTM tags in
   `marketing/private/post-log.csv` using the schema in measurement.md.
7. Capture 24h and 72h results. Posts from Nov 16–18 need a carryover check after
   the sprint. Never add overlapping cumulative snapshots together.

## Fourteen primary posts

Each row is a planned content brief, not a published post. Target one primary
post per day. Visual posts are adaptations of these topics, not extra analyses.

| Date / ID | Primary content brief | Destination | Additional distribution |
| --- | --- | --- | --- |
| Nov 5 / s01 | Introduce La Tabla: one screenshot, what readers can learn, ask which stat they check first | `/` | Visual #1: new banner and concise site walkthrough |
| Nov 6 / s02 | Explain Game Score and how El Valiente is selected; cite one verified example | `/dashboard.html#honor-roll` | Optional Bluesky adaptation |
| Nov 7 / s03 | One roster trend with minutes and sample size; ask what fans are noticing | `/roster.html` | Answer fan questions |
| Nov 8 / s04 | Explain one Wemby metric without overstating causality | `/wemby_lab.html` | Visual #2: metric explainer |
| Nov 9 / s05 | Show why efficiency and scoring volume can tell different stories | `/dashboard.html` | Optional secondary text channel |
| Nov 10 / s06 | Share a player spotlight supported by the latest validated logs | `/roster.html` or verified player URL | Optional r/NBASpurs analysis if permitted and distinct from the feature update; otherwise skip Reddit |
| Nov 11 / s07 | Weekly analysis #1: one basketball question, evidence, limitations, conclusion | Relevant verified article/page URL | Weekly visual summary or permitted Facebook share |
| Nov 12 / s08 | Best question from week one, answered with a chart or table | Relevant verified page | Reply to the person who asked, where appropriate |
| Nov 13 / s09 | One rotation or minutes trend; state date range and avoid injury speculation | `/roster.html` | Visual #3 |
| Nov 14 / s10 | Explain El Compinche / Wingman and why a second player gets recognition | `/dashboard.html#honor-roll` | Optional Bluesky adaptation |
| Nov 15 / s11 | A clutch or team-performance insight; acknowledge small samples | `/dashboard.html` | Basketball discussion rather than another site introduction |
| Nov 16 / s12 | Show how to read a next-game preview, separating estimates from facts | `/matchup.html` | Visual #4; use evergreen walkthrough if preview is stale |
| Nov 17 / s13 | Share one improvement made from reader feedback, or answer a second fan question | Relevant verified page | Optional r/NBASpurs contribution with new substance; do not repeat the feature update |
| Nov 18 / s14 | Weekly analysis #2 and one specific question for the next edition | Relevant verified article/page URL | Optional Facebook/Bluesky summary |

Weekly analyses may be expanded native threads linking an existing relevant site
page. A new essay destination must be published and checked before linking it.
Use `social.py --mode postgame` or `--mode wemby` as draft inputs; review every
claim, data date, wording, and character count before posting.

## Caption structure

> [One specific finding, with the verified date range.]
>
> [Why it might matter, plus the most relevant limitation.]
>
> [One basketball question.] More detail: [tagged destination URL]

Site introduction wording: “I built La Tabla Spurs to follow the season through
stats and lotería-style player cards. Here's [specific useful feature].”
Do not claim a sponsor, live refresh, or a mailing list that does not exist.
