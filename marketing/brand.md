# Brand and creative reference

Public name: **La Tabla Spurs**. “Por vida” is the domain/slogan. Use “GSG” as it
appears in the supplied art; do not rename the publication to Spurs Stats HQ.

| Purpose | Asset / implementation |
| --- | --- |
| Landing page, above title | `docs/img/la_tabla_gsg_logo_card_only.png` |
| Social introductions and pitch materials | `docs/img/la_tabla_gsg_logo_with_banner.png` |
| Default link preview | `docs/img/og/site.png`, rendered from the banner by `viz/share_images.py` |
| Browser tab favicon | `docs/favicon.png`, copied from `assets/incoming/LTS_favicon.png`; linked by `FAVICON_LINK` in `viz/theme.py` |
| Page title type | Rye regular / `FONT_WESTERN` in `viz/theme.py` |
| Colors and shared styling | `viz/theme.py` |

Both published GSG source assets preserve transparency. Keep their proportions
and lettering. The social card places the banner on a dark 1200 × 630 canvas.
Use topic-specific analytical graphics for editorial social posts and the banner
for publication introductions. Do not add prospective sponsors to live branding.

The older `la_tabla_logo.jpeg` remains a historical asset; current templates use
the GSG PNGs. Full-resolution incoming artwork stays ignored in `assets/incoming/`;
published assets need explicit `.gitignore` exceptions.

The favicon is published at the site root, outside the ignored `docs/img/`
directory. Preserve the supplied PNG. When replacing it, bump the version query
in `FAVICON_LINK` and update generated HTML to refresh browser caches. Both the
shared page shell and the standalone landing template include this link.

Changes to default previews must update the generator, rebuild `site.png`, and
regenerate page metadata so its content hash changes. Check deployed HTML and
image availability separately; platform caches can lag deployment.
