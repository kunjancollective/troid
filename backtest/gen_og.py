#!/usr/bin/env python3
"""Render a language's share image: web/public/og/{lang}.png, 1200x630 — the troid lockup exactly as in
og-image.png, with the tagline (og.tagline) in that language beneath it. troid stays troid in every image.

  (cd tools/og && npm install)          # once: the fonts, from @fontsource (Noto for CJK, Devanagari, Bengali, Arabic)
  python gen_og.py ar                   # after i18n_import.py makes a language live
  python gen_og.py --preview OUT ar zh  # drafts too, into OUT (never web/public)

Chromium lays out the text, so Arabic joins and runs right to left and Devanagari and Bengali shape correctly.
"""
import argparse
import html
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import i18n  # noqa: E402

ROOT = HERE.parent
FONTS = ROOT / "tools" / "og" / "node_modules" / "@fontsource"
PUB = ROOT / "web" / "public"
FAMILY = {"Noto Sans SC": "noto-sans-sc", "Noto Sans Devanagari": "noto-sans-devanagari",
          "Noto Sans Bengali": "noto-sans-bengali", "Noto Sans Arabic": "noto-sans-arabic"}


def card(code, fallback=False):
    T = i18n.Strings(code, fallback=fallback)
    lang = T.lang
    css = [f'<link rel="stylesheet" href="{(FONTS / "inter" / "500.css").as_uri()}">']
    fam = '"Inter"'
    if lang.get("font"):
        css.append(f'<link rel="stylesheet" href="{(FONTS / FAMILY[lang["font"]] / "500.css").as_uri()}">')
        fam = f'"Inter","{lang["font"]}"'
    return f"""<!DOCTYPE html><html lang="{code}" dir="{lang['dir']}"><head><meta charset="utf-8">{''.join(css)}
<style>html,body{{margin:0;width:1200px;height:630px;overflow:hidden}}
body{{background:url('{(PUB / "og-image.png").as_uri()}') no-repeat 0 0/1200px 630px}}
.t{{position:absolute;left:120px;right:120px;top:410px;text-align:center;font-family:{fam},sans-serif;font-weight:500;
font-size:40px;line-height:1.35;color:#e6edf5;letter-spacing:-.01em}}</style></head>
<body><div class="t">{html.escape(T("og.tagline"))}</div></body></html>"""


def render(codes, out, fallback=False):
    from playwright.sync_api import sync_playwright
    if not FONTS.exists():
        sys.exit("fonts missing: run (cd tools/og && npm install) first")
    out.mkdir(parents=True, exist_ok=True)
    tmp = out / "_card.html"
    written = []
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
        pg = b.new_page(viewport={"width": 1200, "height": 630}, device_scale_factor=1)
        for code in codes:
            tmp.write_text(card(code, fallback))
            pg.goto(tmp.as_uri(), wait_until="load")
            pg.evaluate("document.fonts.ready")
            pg.wait_for_timeout(200)
            dest = out / f"{code}.png"
            pg.screenshot(path=str(dest))
            written.append(dest)
        b.close()
    tmp.unlink()
    return written


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("langs", nargs="*")
    ap.add_argument("--preview", metavar="OUT")
    a = ap.parse_args()
    if a.preview:
        codes = a.langs or [l["code"] for l in i18n.LANGS if l["code"] != "en"]
        w = render(codes, Path(a.preview), fallback=True)
    else:
        live = [c for c in i18n.live_codes() if c != "en"]
        codes = [c for c in (a.langs or live) if c in live]
        if a.langs and set(a.langs) - set(codes):
            print(f"not live, skipped: {sorted(set(a.langs) - set(codes))}")
        w = render(codes, PUB / "og") if codes else []
    print("gen_og: " + (", ".join(str(p.relative_to(ROOT)) if ROOT in p.parents else str(p) for p in w) or "nothing to render"))


if __name__ == "__main__":
    main()
