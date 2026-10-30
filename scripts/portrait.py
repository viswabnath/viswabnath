#!/usr/bin/env python3
"""Turn a photo into the ASCII portrait used by build.py.

Run locally (macOS + Pillow), only when the photo changes:
    swift scripts/segment.swift photo.png mask.png
    python3 scripts/portrait.py photo.png mask.png

Writes assets/portrait.txt. build.py reads that file, so the daily GitHub
Action doesn't need Pillow.
"""

import sys
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parent.parent

COLS, ROWS = 46, 26
CELL_ASPECT = 8.4 / 18          # glyph width / portrait line height in build.py
CROP_TOP, CROP_HEIGHT = 0.0, 0.54   # fraction of image height
RAMP = " .,:;i1tfLCG08@"


def silhouette(mask):
    """Cells of the largest connected blob in the mask (drops stray corners)."""
    cells = {(x, y) for y in range(mask.height) for x in range(mask.width)
             if mask.getpixel((x, y)) >= 110}
    best = set()
    while cells:
        stack, blob = [cells.pop()], set()
        while stack:
            x, y = stack.pop()
            blob.add((x, y))
            for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if n in cells:
                    cells.remove(n)
                    stack.append(n)
        best = max(best, blob, key=len)
    return best


def portrait(photo, mask):
    img = Image.open(photo).convert("L")
    m = Image.open(mask).convert("L").resize(img.size, Image.LANCZOS)
    w, h = img.size

    crop_h = int(h * CROP_HEIGHT)
    crop_w = int(crop_h * CELL_ASPECT * COLS / ROWS)
    # Centre the crop on the person's mass within the cropped band.
    band = m.crop((0, 0, w, crop_h)).point(lambda v: 255 if v > 128 else 0)
    xs = [x for x in range(w) for y in range(0, crop_h, 4) if band.getpixel((x, y))]
    cx = sum(xs) // len(xs) if xs else w // 2
    left = max(0, min(w - crop_w, cx - crop_w // 2))
    top = int(h * CROP_TOP)
    box = (left, top, left + crop_w, top + crop_h)

    img = img.crop(box)
    m = m.crop(box).filter(ImageFilter.GaussianBlur(1))
    # Local contrast so the face reads, then sharpen edges a little.
    img = ImageOps.autocontrast(img, cutoff=1, mask=m.point(lambda v: 255 if v > 128 else 0))
    img = img.filter(ImageFilter.UnsharpMask(radius=3, percent=120, threshold=3))

    small = img.resize((COLS, ROWS), Image.LANCZOS)
    small_m = m.resize((COLS, ROWS), Image.LANCZOS)
    keep = silhouette(small_m)
    lines = []
    for y in range(ROWS):
        row = []
        for x in range(COLS):
            if (x, y) not in keep:
                row.append(" ")
                continue
            # Ink-style: dark pixels (hair, suit, features) get dense glyphs.
            density = 1 - small.getpixel((x, y)) / 255
            row.append(RAMP[min(int(density * len(RAMP)), len(RAMP) - 1)])
        lines.append("".join(row).rstrip())
    return "\n".join(lines) + "\n"


def main():
    photo, mask = sys.argv[1], sys.argv[2]
    out = ROOT / "assets"
    out.mkdir(exist_ok=True)
    (out / "portrait.txt").write_text(portrait(photo, mask))
    print((out / "portrait.txt").read_text())


if __name__ == "__main__":
    main()
