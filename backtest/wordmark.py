#!/usr/bin/env python3
"""The tr●id wordmark's letters as SVG paths, from brand/PlexMono-SemiBold.ttf (design handoff 2026-09-24, 1c).

The header's wordmark was live text in IBM Plex Mono: on a phone with a cold cache "tr" and "id" painted in the system
mono first, then swapped to Plex at a different width, and the dot between them jumped. As paths it has no font to
wait for. Each pair is drawn as the text was: two cells of Plex Mono's 600-unit advance, each less the wordmark's
-0.04em letter spacing (so 560 units a letter, 1,120 a pair), in Plex's own line box: 1,025 units above the baseline and
275 below. site_build.mark sets each pair as a 1.12em × 1.3em SVG whose baseline is the text's.

  python wordmark.py      # rewrites wordmark_paths.json (needs fontTools; the build reads only the JSON)
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
FONT = HERE.parent / "brand" / "PlexMono-SemiBold.ttf"
OUT = HERE / "wordmark_paths.json"
CELL = 560                  # 600-unit advance, -40 letter spacing (-0.04em)
ASCENT, DESCENT = 1025, 275  # hhea: the line box the text had


def paths():
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.transformPen import TransformPen
    from fontTools.ttLib import TTFont
    f = TTFont(str(FONT))
    assert f["head"].unitsPerEm == 1000 and f["hhea"].ascent == ASCENT and -f["hhea"].descent == DESCENT
    gs, cmap = f.getGlyphSet(), f.getBestCmap()

    def pair(a, b):
        pen = SVGPathPen(gs, ntos=lambda v: str(round(v)))
        for i, ch in enumerate((a, b)):
            gs[cmap[ord(ch)]].draw(TransformPen(pen, (1, 0, 0, -1, i * CELL, 0)))   # y down, baseline at 0
        return pen.getCommands()
    return {"tr": pair("t", "r"), "id": pair("i", "d"), "width": 2 * CELL, "ascent": ASCENT, "descent": DESCENT,
            "source": "brand/PlexMono-SemiBold.ttf (IBM Plex Mono SemiBold, OFL), by backtest/wordmark.py"}


if __name__ == "__main__":
    OUT.write_text(json.dumps(paths(), indent=1) + "\n")
    print(f"{OUT}: {OUT.stat().st_size} bytes")
