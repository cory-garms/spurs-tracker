"""
Prepare player emblem art for the site.

Reads full-resolution images from docs/img/players_src/ (kept out of git), named
either by slug (fox.jpeg) or by emblem name (El_Zorro.jpeg, El Tío.png ...),
trims any printed border the image model added (cream paper or dark keylines),
center-crops to a square and writes small WebPs to docs/img/players/, which
viz/avatars.py picks up on the next build.

Usage:
    python scripts/prep_art.py            # process new or changed images
    python scripts/prep_art.py --force    # reprocess everything
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from viz.avatars import PLAYER_EMBLEMS  # noqa: E402  (needs the repo root on the path)
SRC = ROOT / "docs" / "img" / "players_src"
OUT = ROOT / "docs" / "img" / "players"
SIZE = 320           # px; displayed at up to ~160px, so this covers 2x screens
ROUND_SIZE = 96      # px; transparent-cornered copy for chart labels, which can't round with CSS
MAX_TRIM = 0.2       # never trim more than 20% from any side
BORDER_FRAC = 0.6    # a row/column is border if this share of its pixels look like border


def _is_border(px: tuple[int, int, int]) -> bool:
    r, g, b = px
    cream = r > 200 and g > 185 and b > 150 and r - b < 70
    dark = r < 70 and g < 70 and b < 70
    return cream or dark


def _trim_border(im: Image.Image) -> Image.Image:
    """Walk in from each edge while the row/column is mostly paper or keyline."""
    w, h = im.size
    px = im.load()
    step = max(1, min(w, h) // 300)

    def frac_row(y: int) -> float:
        xs = range(w // 4, 3 * w // 4, step)
        return sum(_is_border(px[x, y]) for x in xs) / len(xs)

    def frac_col(x: int) -> float:
        ys = range(h // 4, 3 * h // 4, step)
        return sum(_is_border(px[x, y]) for y in ys) / len(ys)

    def walk(n: int, frac, index) -> int:
        limit = int(n * MAX_TRIM)
        i = 0
        while i < limit and frac(index(i)) >= BORDER_FRAC:
            i += step
        return i

    left = walk(w, frac_col, lambda i: i)
    right = walk(w, frac_col, lambda i: w - 1 - i)
    top = walk(h, frac_row, lambda i: i)
    bottom = walk(h, frac_row, lambda i: h - 1 - i)
    return im.crop((left, top, w - right, h - bottom))


def _square(im: Image.Image) -> Image.Image:
    w, h = im.size
    side = min(w, h)
    return im.crop(((w - side) // 2, (h - side) // 2, (w + side) // 2, (h + side) // 2))


def _norm(text: str) -> str:
    """'El_Tío' / 'el tio' / 'EL-TIO' -> 'eltio'."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", text.lower())


def resolve_slug(stem: str) -> str | None:
    """Match a file name to an emblem slug by slug or emblem name; extra words are ignored."""
    key = _norm(stem)
    for slug, emblem in PLAYER_EMBLEMS.values():
        if key == slug or key.startswith(_norm(emblem)):
            return slug
    for slug, emblem in PLAYER_EMBLEMS.values():
        if key.startswith(slug):
            return slug
    return None


def process(src: Path, force: bool = False) -> Path | None:
    slug = resolve_slug(src.stem)
    if slug is None:
        print(f"  skipped {src.name}: no matching player in viz/avatars.py PLAYER_EMBLEMS")
        return None
    out = OUT / f"{slug}.webp"
    if not force and out.exists() and out.stat().st_mtime >= src.stat().st_mtime:
        return None
    im = Image.open(src).convert("RGB")
    im = _square(_trim_border(im)).resize((SIZE, SIZE), Image.LANCZOS)
    OUT.mkdir(parents=True, exist_ok=True)
    im.save(out, "WEBP", quality=82, method=6)
    _round_copy(im, OUT / f"{slug}_round.png")
    return out


def _round_copy(im: Image.Image, out: Path) -> None:
    """Circle-cropped PNG with transparent corners (drawn at 4x then downsampled for a smooth edge)."""
    from PIL import ImageDraw
    big = ROUND_SIZE * 4
    mask = Image.new("L", (big, big), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, big - 1, big - 1], fill=255)
    rgba = im.resize((big, big), Image.LANCZOS).convert("RGBA")
    rgba.putalpha(mask)
    rgba.resize((ROUND_SIZE, ROUND_SIZE), Image.LANCZOS).save(out, "PNG", optimize=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--force", action="store_true", help="reprocess images that are already up to date")
    args = parser.parse_args()

    if not SRC.exists():
        print(f"No source folder yet: {SRC.relative_to(ROOT)} (drop emblem images there, named <slug>.jpeg)")
        return 0
    sources = sorted(p for p in SRC.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"})
    done = [p for p in (process(s, args.force) for s in sources) if p]
    for p in done:
        print(f"  wrote {p.relative_to(ROOT)} ({p.stat().st_size // 1024} KB)")
    print(f"{len(done)} processed, {len(sources) - len(done)} already up to date.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
