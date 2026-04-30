"""One-shot helper to generate WebP variants for hero/blog images.

Run with:  python scripts/convert_images.py

Idempotent: it only writes files that don't already exist (or if --force).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
IMAGES_DIR = ROOT / "static" / "images"


# (source_path, [(width, output_path)])  -- WebP variants to generate
JOBS: list[tuple[Path, list[tuple[int, Path]]]] = [
    (
        IMAGES_DIR / "blog" / "electric_bike_alps_man_riding.jpg",
        [
            (1200, IMAGES_DIR / "blog" / "electric_bike_alps_man_riding-1200.webp"),
            (800,  IMAGES_DIR / "blog" / "electric_bike_alps_man_riding-800.webp"),
            (400,  IMAGES_DIR / "blog" / "electric_bike_alps_man_riding-400.webp"),
        ],
    ),
]

# Auto-generate jobs for the category card images at three responsive
# widths. The cards display at ~370 px max, so 800 px is plenty for
# high-DPI displays and 400 px is the mobile target.
_CATEGORIES_DIR = IMAGES_DIR / "categories"
_CATEGORY_SOURCES = sorted(_CATEGORIES_DIR.glob("*_rider.jpg")) + [
    _CATEGORIES_DIR / "electric.jpg",
]
for _src in _CATEGORY_SOURCES:
    if not _src.exists():
        continue
    _stem = _src.stem  # e.g. "gravel_rider" or "electric"
    JOBS.append((
        _src,
        [
            (1200, _CATEGORIES_DIR / f"{_stem}-1200.webp"),
            (800,  _CATEGORIES_DIR / f"{_stem}-800.webp"),
            (400,  _CATEGORIES_DIR / f"{_stem}-400.webp"),
        ],
    ))


def convert(src: Path, width: int, dst: Path, quality: int = 78, force: bool = False) -> None:
    if dst.exists() and not force:
        print(f"  skip (exists): {dst.relative_to(ROOT)}")
        return
    with Image.open(src) as im:
        im = im.convert("RGB")
        if im.width > width:
            ratio = width / im.width
            new_size = (width, round(im.height * ratio))
            im = im.resize(new_size, Image.LANCZOS)
        dst.parent.mkdir(parents=True, exist_ok=True)
        im.save(dst, format="WEBP", quality=quality, method=6)
    print(f"  wrote {dst.relative_to(ROOT)} ({dst.stat().st_size // 1024} KB, {im.width}x{im.height})")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="regenerate even if outputs exist")
    args = parser.parse_args()

    for src, variants in JOBS:
        if not src.exists():
            print(f"WARN: missing source {src}")
            continue
        print(f"Source: {src.relative_to(ROOT)} ({src.stat().st_size // 1024} KB)")
        for width, dst in variants:
            convert(src, width, dst, force=args.force)


if __name__ == "__main__":
    main()
