# Audience measurement and reporting

Owner: Cory. Status on November 4: production analytics coverage is unverified.
Cory will inspect Vercel. The repository's documented production host is GitHub
Pages; Vercel dashboard access alone does not establish coverage of this site.

## Production verification — A1/A2

1. In Vercel, identify the project, tracked hostname, enabled analytics product,
   measurement start date, and available dimensions. Check the actual published
   site's HTML/network activity for the corresponding integration.
2. From a normal browser with blockers disabled for this test, visit
   `https://porvida.corygarms.com/?utm_source=qa&utm_medium=test&utm_campaign=sponsor_sprint_202611&utm_content=analytics_check`.
   Open `roster.html` too. Note test timestamp and timezone privately.
3. Within the provider's documented processing window, verify the production
   hostname and both paths in its events/dashboard. Verify tagged campaign
   attribution if the provider exposes it; if not, document which referral
   dimensions are actually available. A synthetic QA visit is not organic growth.
4. Mark pass, partial, or fail in scorecard.csv. “Partial” means page traffic is
   measured but attribution or another required dimension is missing.
5. If the site isn't tracked, implement a compatible integration as a separate
   code task. Check `viz/theme.py`'s shared shell, the standalone landing template
   in `viz/index_viz.py`, and any other HTML builders. Rebuild and validate the
   generated pages, deploy, then repeat this test. Record any new service cost.

Do not extrapolate pre-instrumentation audience or treat GitHub repository views,
Vercel preview visits, or social impressions as production website sessions.

## Tagged links

Use campaign `sponsor_sprint_202611`, medium `social`, and a lowercase source:
`x`, `reddit`, `instagram`, `bluesky`, or `facebook`. Use the calendar content ID
plus variant, for example `s04_chart`. Give each channel its own link.

Example:

`https://porvida.corygarms.com/wemby_lab.html?utm_source=x&utm_medium=social&utm_campaign=sponsor_sprint_202611&utm_content=s04_chart`

For anchors, put the query first, then the fragment:

`https://porvida.corygarms.com/dashboard.html?utm_source=x&utm_medium=social&utm_campaign=sponsor_sprint_202611&utm_content=s02_explainer#honor-roll`

A bio link may only support channel-level attribution. Record it as `bio`, not
as if every visual post had a separately measured link. Referral traffic and UTM
coverage can be incomplete; state limitations rather than forcing attribution.

## Definitions and evidence

| Metric | Definition / evidence |
| --- | --- |
| Visitors | Provider-reported unique visitors for the stated dates; name provider and definition |
| Sessions | Provider-reported visits/sessions; leave unavailable if not offered; never relabel pageviews |
| Pageviews | Provider-reported page loads, separate from visitors and sessions |
| Returning audience | Provider-supported returning metric only; otherwise unavailable |
| Social impressions | Platform-reported impressions; show per channel and window |
| Engagement rate | (Likes + replies/comments + shares/reposts) / impressions × 100; do not mix platform definitions silently |
| Link CTR | Platform-reported link clicks / impressions × 100, where both exist |
| Attributed visits | Provider-reported sessions by campaign/source, or explicitly named substitute metric |
| Outreach conversion | Positive replies / initial approaches sent; keep automatic replies separate |
| Revenue | Agreed fees, invoices issued, and cash collected recorded separately |

Do not sum visitors across platforms as a deduplicated audience. Visits divided
by social clicks is not a reliable conversion rate when tracking scopes differ.
If impressions or denominators are zero, report the rate as unavailable.

Public aggregates go in [scorecard.csv](scorecard.csv). Leave unavailable numeric
cells empty; `notes` explains why. Zero means measured zero. Preserve the baseline
row; append actual week-one and sprint totals using explicit windows. The current
rows are empty templates, not observations.

Private post log CSV header:

```csv
content_id,platform,published_at_et,post_url,destination_url,utm_source,utm_medium,utm_campaign,utm_content,measurement_window,measured_at_et,impressions,engagements,link_clicks,attributed_sessions,evidence_ref,notes
```

Use separate `24h` and `72h` rows per post. Use 72h results for consistent post
comparisons when available; label late posts as pending until their window closes.
Record native analytics exports/screenshots privately. Do not place raw visitor
events or private prospect conversations in the public repository.

## Review cadence

- Nov 6: confirm instrumentation, establish baseline and achievable traffic target.
- Nov 11: first seven distribution sessions; compare available 24h/72h cohorts.
- Nov 18: total actual sprint activity and site traffic; report trailing posts
  whose 72h windows have not closed. Assign Nov 19–21 carryover checks manually.
- Pilot reporting later: use agreed dates and delivered sponsor placements, not
  promised reach. No public signup form exists; subscriber counts are unavailable.
