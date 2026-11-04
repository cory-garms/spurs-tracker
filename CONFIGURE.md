# Configuring Spurs Tracker

## Defaults

`config.py` currently selects `TEAM_ABBR = "SAS"`, `SEASON = 2026`, and `SEASON_TYPE = "Regular Season"`. Season integers refer to the starting year: 2026 becomes `2026-27` through `season_str()`.

Other settings include `SITE_URL` for absolute share-image URLs, `CACHE_DIR` (`data/cache/`), `OUTPUT_DIR` (`docs/`), NBA browser headers, timeout, and request delay. Preserve the required headers and at least 0.6 seconds between Stats API requests.

## Refresh the current site

Sync `master` before refreshing, especially after work in another session or an
automated build. Check `git status --short`, preserve any local work, then use
`git pull --ff-only origin master` when the branch can fast-forward. Resolve any
divergence deliberately; generated pages can be rebuilt from the merged code and
latest caches. Do not restore older stashed generators over newer site changes.

Activate `.spursEnv` and install dependencies as described in [README.md](README.md), then run:

```bash
python pipeline.py --team SAS --season 2026 --refresh
python -m pytest
```

This incrementally fetches game data and refreshes league ratings, the schedule, and next-opponent player statistics before rebuilding the site. Check fallback warnings and the latest cached game date: a successful build alone does not establish data freshness.

Before publishing, confirm the expected game date, opponent and result, reconcile
player points with the final team score, and check the landing-page record and
next-game preview. Run the tests and `git diff --check`, then commit and push the
updated `data/cache/` and `docs/` along with any source changes. GitHub Pages
publishes asynchronously after the push. If an automated commit arrives first,
fetch and integrate it, then regenerate output before retrying the push.

Use `python pipeline.py --skip-fetch` to rebuild existing caches. For a full boxscore replacement, run `python fetch.py --team SAS --season 2026 --refresh --league`, then rebuild with the pipeline. Standalone fetching does not refresh the schedule or next-opponent player cache.

## Other teams and seasons

```bash
python fetch.py --list-teams
python fetch.py --team GSW --season 2024
python report.py --team GSW --season 2024
python viz_report.py --team GSW --season 2024
```

CLI flags override defaults for that command. All 30 teams are registered, but specialized Spurs features and some JSON fields remain Spurs-specific; changing the default team is not a complete rebrand.

Registered pages for the configured team and season use stable filenames. Other builds use suffixes such as `dashboard_GSW_2024.html`. The complete configured-site build, including landing page, roster/player pages, and share images, runs through `pipeline.py`.

`fetch.py --preseason` and `fetch.py --playoffs` use separate season-type caches. The master pipeline uses regular-season data.

## Automation and hosting

Audience tracking and social distribution are part of the active
[November 5–18 growth sprint](marketing/sprint-2026-11-05.md). See
[measurement setup and verification](marketing/measurement.md) for the production
hostname test and UTM conventions. Vercel analytics coverage is currently
unverified; a Vercel project does not automatically measure GitHub Pages visits.
Any instrumentation change must cover shared page templates and the standalone
landing page, be rebuilt and deployed, then pass the actual-domain test.

The marketing calendar is a manual work plan, not a scheduled publishing job.
No new tracking integration, signup service, or sponsor placement has been added
by documenting this initiative. Keep service credentials and raw exports private.

`.github/workflows/pipeline.yml` runs at 05:00 UTC using `config.py` defaults. Scheduled runs rebuild caches; its manual `refresh_remote` input enables remote ingestion. It runs tests and commits pages plus cache snapshots.

The older `.github/workflows/refresh.yml` runs at 12:00 UTC. Repository variables `TEAM_ABBR` and `SEASON` affect only its fetch step, with fallbacks SAS/2025. Its build step is hardcoded to SAS/2025 and it commits only `docs/`. Repository variables do not change the master workflow's defaults.

Both schedules stay fixed in UTC through daylight-saving changes. Local builds update files only; publishing uses the repository's static-hosting deployment process. Keep `SITE_URL` consistent with the public hosting address.

## Branding and social previews

`docs/favicon.png` is a tightly framed enlargement of the supplied
`assets/incoming/LTS_favicon.png`. `viz/theme.py` defines `FAVICON_LINK`, used in both the shared shell and
the standalone landing page. Keep its version query and generated HTML in sync
when replacing the favicon. Browser tab icons are separate from social previews.

Keep `docs/img/la_tabla_gsg_logo_card_only.png` above the landing title and use
`docs/img/la_tabla_gsg_logo_with_banner.png` for site branding on social channels.
Both are published transparent PNGs; `.gitignore` explicitly permits them.
The shared shell and landing page reference the original banner directly, using
a content-hashed absolute URL and its actual dimensions. `viz/share_images.py`
also builds the optional composed `img/og/site.png` asset. Regenerate metadata
when changing the banner. See [brand guidance](marketing/brand.md).

Social campaign links use `utm_campaign=sponsor_sprint_202611`,
`utm_medium=social`, channel-specific `utm_source`, and content IDs from
[the calendar](marketing/social-calendar.md). Put query parameters before URL
fragments. Confirm destination pages and production analytics after deployment.

## Custom domain and HTTPS

The site uses `porvida.corygarms.com`, recorded in `docs/CNAME`. Its DNS CNAME should point to `cory-garms.github.io`. `config.SITE_URL` is `https://porvida.corygarms.com` for generated share-image URLs.

The public site name is **La Tabla Spurs**; “por vida” is the domain/slogan.
HTTPS enforcement was enabled and verified during the October 28 session:
HTTPS returned 200 with certificate validation, and HTTP redirected with 301.

GitHub Pages provisions the custom-domain TLS certificate. In repository **Settings → Pages**, confirm the custom domain passes its DNS check and enable **Enforce HTTPS** when available. This redirects HTTP requests to HTTPS. Changing HTML or `SITE_URL` alone does not provision a certificate or enable that redirect.

If HTTPS reports a certificate hostname mismatch, check certificate provisioning in Pages settings. GitHub documents provisioning delays and DNS troubleshooting in [Securing your GitHub Pages site with HTTPS](https://docs.github.com/en/pages/getting-started-with-github-pages/securing-your-github-pages-site-with-https).
