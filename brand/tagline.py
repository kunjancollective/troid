#!/usr/bin/env python3
"""Redraw the line on the X header and the Reddit banner from the site's own text (web/i18n/en.json og.tagline), so the
banners, the home page and the share image say the same thing (the owner, 2026-09-26).

Each banner's background is a vertical gradient with every row one colour, so the strip the line sits in is erased row
by row to that row's own colour, then the line is drawn back in IBM Plex Mono Regular (PlexMono-Regular.ttf, OFL), in
the site's dim ink, centred where the banners set it under the wordmark; the letters that spell troid ("tr" in trade,
"oid" in droid) in the dot's blue and the rest of those two words in the wordmark's ink, as on the home page. The
wordmark, its floors and troid.ai are not touched. Running it again redraws the same strip, so a new line only needs en.json changed and this run.

  python brand/tagline.py            # brand/banner-*.png and their copies in brand/social/
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "backtest"))
import site_text  # noqa: E402  the letters that spell troid (TAGLINE_MARKS), the same rule as the home page's

DIM = (125, 138, 160)            # --dim, #7d8aa0, as the banners were set
COLOUR = {None: DIM, "ink": (230, 237, 245), "signal": (77, 163, 255)}   # the wordmark's ink and dot (README colours)
FONT = HERE / "PlexMono-Regular.ttf"

# file and its copy, the rows of the line's strip (clear of the floors above and troid.ai below), the type size, the
# baseline and the centre, all measured from the owner's banners of 24 Sep 2026
BANNERS = [
    (("banner-x-1500x500.png", "social/x-header-1500x500.png"), (280, 332), 27, 313, 800),
    (("banner-reddit-1920x384.png", "social/reddit-banner-1920x384.png"), (218, 272), 26, 251, 960),
]


def draw(line):
    for (name, copy), (top, bottom), size, base, cx in BANNERS:
        im = Image.open(HERE / name).convert("RGB")
        px = im.load()
        for y in range(top, bottom):
            c = px[2, y]
            assert all(px[x, y] == c for x in (0, 1, im.width - 1)), f"{name}: row {y} is not one colour"
            for x in range(im.width):
                px[x, y] = c
        f = ImageFont.truetype(str(FONT), size)
        w = f.getlength(line)
        assert w < im.width - 200, f"{name}: the line is {w:.0f} px wide"
        x, d = cx - w / 2, ImageDraw.Draw(im)
        for text, role in site_text.tagline_parts(line):     # "dr" and "ade" in the ink, "oid" and "tr" in the blue
            d.text((x, base), text, font=f, fill=COLOUR[role], anchor="ls")
            x += f.getlength(text)
        for out in (name, copy):
            im.save(HERE / out, optimize=True)
        print(f"{name} (= {copy}): {line!r}, {size} px, {w:.0f} px wide, centred at x {cx}")


if __name__ == "__main__":
    draw(json.loads((ROOT / "web" / "i18n" / "en.json").read_text())["og.tagline"])
