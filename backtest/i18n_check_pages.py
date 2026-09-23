#!/usr/bin/env python3
"""Every page of a language in Chromium at 390 px and 1280 px, from a preview build (drafts included):
no horizontal scroll, Latin digits only, lang/dir set, no script errors; on the desk and compare, the country
selector (preselected from the browser's language), a firm excluded by its recorded terms shown as "not available
in <country> per the firm's terms" in place of its link, and the reader's local time beside UTC.

  python i18n_check_pages.py ar            # one language
  python i18n_check_pages.py               # every language with a file
  python i18n_check_pages.py ar --shots OUT   # keep full-page screenshots

Fonts load from tools/og/node_modules/@fontsource when it is installed ((cd tools/og && npm install)), so the
screenshots show the scripts as readers see them; the checks themselves do not depend on it. Nothing leaves the
machine: every request that is not to the local preview server is aborted or served locally.
"""
import argparse
import re
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import i18n  # noqa: E402
import site_build  # noqa: E402
from i18n_equiv import serve  # noqa: E402

FONTS = HERE.parent / "tools" / "og" / "node_modules" / "@fontsource"
LOCALE = {"ar": "ar-SA", "fr": "fr-FR", "zh": "zh-CN", "hi": "hi-IN", "bn": "bn-BD", "es": "es-MX", "pt": "pt-BR",
          "ru": "ru-RU", "id": "id-ID", "en": "en-US"}
PAGES = ["", "/compare", "/ledger", "/faq", "/dashboard", "/terms", "/chat", "/tearsheet"]
NATIVE = re.compile(r"[٠-٩۰-۹०-९০-৯]")
# A firm and a country its recorded terms exclude (firms.json availability), and one it excludes on a platform only.
EXCLUDED, PLATFORM = ("brightfunded", "VN"), ("brightfunded", "US")


def font_css(url):
    fam = re.search(r"family=([^:&]+)", url).group(1).replace("+", " ")
    slug = fam.lower().replace(" ", "-")
    return "".join((FONTS / slug / f"{w}.css").read_text().replace("url(./files/", f"url(/_fonts/{slug}/files/")
                   for w in (400, 500, 600, 700) if (FONTS / slug / f"{w}.css").exists())


def check_language(b, url, code, shots, fails):
    def check(cond, msg):
        print(("ok   " if cond else "FAIL ") + msg)
        if not cond:
            fails.append(msg)
    region = LOCALE[code].split("-")[1]
    for vw in (390, 1280):
        ctx = b.new_context(viewport={"width": vw, "height": 900}, locale=LOCALE[code], timezone_id="Asia/Kolkata")

        def route(r):
            u = r.request.url
            if u.startswith(url):
                return r.continue_()
            if "fonts.googleapis.com/css2" in u and FONTS.exists():
                return r.fulfill(status=200, content_type="text/css", body=font_css(u))
            return r.abort()
        ctx.route("**/*", route)
        errors = []
        for page in PAGES:
            name = f"{code}{page or '/'} {vw}px"
            pg = ctx.new_page()
            pg.on("pageerror", lambda e: errors.append(str(e)))
            pg.goto(f"{url}/{code}{page}", wait_until="load")
            pg.wait_for_timeout(300)
            sw = pg.evaluate("document.documentElement.scrollWidth")
            check(sw <= vw, f"{name}: no horizontal scroll (scrollWidth {sw})")
            check(not NATIVE.search(pg.evaluate("document.body.innerText")), f"{name}: Latin digits only")
            check(pg.evaluate("[document.documentElement.lang, document.documentElement.dir]")
                  == [code, i18n.BY_CODE[code]["dir"]], f"{name}: lang and dir")
            if vw == 390 and page in ("", "/compare"):
                sel = pg.locator("[data-country] select")
                check(sel.count() == 1, f"{name}: one country selector")
                check(sel.input_value() == region, f"{name}: country preselected from the browser's language ({sel.input_value()})")
                firm, cc = EXCLUDED
                pg.select_option("[data-country] select", cc)
                blk = pg.locator(f'[data-avail="{firm}"]')
                check(blk.locator(".avail.no").count() == 1 and blk.locator("[data-avail-link]").is_hidden(),
                      f"{name}: {firm} shown as not available in {cc}, link hidden")
                if page == "/compare":
                    pg.fill("#quota", "50000")
                    pg.wait_for_timeout(100)
                    check(blk.locator(".avail.no").count() == 1, f"{name}: still not available after a re-render")
                    check(pg.locator(".tlocal").count() >= 1, f"{name}: local reset time beside UTC")
                firm, cc = PLATFORM
                pg.select_option("[data-country] select", cc)
                check(blk.locator("[data-avail-link]").is_visible() and "MT5" in blk.inner_text(),
                      f"{name}: {firm} platform-only note in {cc}, link shown")
                bf = pg.locator('[data-avail="bitfunded"]')
                check(bf.locator(".avail").count() == 1 and bf.locator(".avail.no").count() == 0
                      and bf.locator("[data-avail-link]").is_visible(),
                      f"{name}: bitfunded shows its own note (its Terms list no countries), link shown")
                pg.select_option("[data-country] select", region)
            if vw == 390 and page == "/ledger":
                check(pg.locator(".tlocal").count() >= 2, f"{name}: local times beside UTC")
            if shots:
                pg.screenshot(path=str(Path(shots) / f"{code}-{(page.strip('/') or 'index')}-{vw}.png"), full_page=True)
            pg.close()
        check(not errors, f"{code} {vw}px: no script errors {errors[:3]}")
        ctx.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("langs", nargs="*")
    ap.add_argument("--shots", metavar="OUT")
    a = ap.parse_args()
    codes = a.langs or [c for c in site_build.targets(preview=True) if c != "en"]
    if a.shots:
        Path(a.shots).mkdir(parents=True, exist_ok=True)
    from playwright.sync_api import sync_playwright
    fails = []
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        site_build.render_static(site_build.targets(preview=True, only=["en", *codes]), out, preview=True)
        live = site_build.targets(preview=True)
        for code in codes:
            T = i18n.Strings(code, fallback=True)
            for page in site_build.GENERATED:
                text = site_build.render_page(page, T, live, preview=True)
                if text is not None:
                    q = site_build.out_path(code, page, out); q.parent.mkdir(parents=True, exist_ok=True); q.write_text(text)
        for f in site_build.PUB.iterdir():
            if f.is_file() and not (out / f.name).exists():
                (out / f.name).write_bytes(f.read_bytes())
        if FONTS.exists():
            import shutil
            for fam in FONTS.iterdir():
                shutil.copytree(fam, out / "_fonts" / fam.name)
        srv, url = serve(out)
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
            for code in codes:
                check_language(b, url, code, a.shots, fails)
            b.close()
        srv.shutdown()
    print(f"RESULT: {len(fails)} failed")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
