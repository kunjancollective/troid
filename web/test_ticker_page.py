#!/usr/bin/env python3
"""The price tape (web/public/ticker.js; ticker v3 handoff), in Chromium against web/public served locally. TradingView's
widget script is answered by backtest/tv_stub.py and /api/ticker by the test: spends nothing, calls no one.

  python web/test_ticker_page.py

- The tape loads after the page with troid's settings: firms.json _ticker_universe's symbols in order, transparent,
  adaptive, no logos, the page's theme and language, and a tap opens troid's desk, never TradingView's site.
- TradingView's attribution sits under it, in the dim ink.
- The header is the same height with the widget loading, loaded, failed, paused and under reduced motion.
- A failed widget gives way to troid's still row; so do pause (WCAG 2.2.2) and reduced motion, where the widget isn't
  even requested until the visitor presses play. /api/ticker is asked only while the still row shows.
- The still row: the same symbols, crypto priced from /api/ticker in the dim ink with ▲/▼, "delayed" past 60 s; on the
  desk a crypto symbol opens "use as entry", which fills the entry field and recomputes the desk.
- On a phone the box is the tape's 72 px, the row scrolls with snap, and the page never scrolls sideways.
"""
import json
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backtest"))
from i18n_equiv import PUB, serve  # noqa: E402
from tv_stub import route_tv  # noqa: E402
import site_build  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
EN = json.loads((ROOT / "web" / "i18n" / "en.json").read_text())
TAPE = [s["tv"] for g in json.loads((ROOT / "firms.json").read_text())["_ticker_universe"]["groups"] for s in g["symbols"]]
fails, n = [], 0


def ok(name, cond, info=""):
    global n
    n += 1
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else f"  {str(info)[:300]}"))
    if not cond:
        fails.append(name)


def body(age_gap_ms=900):
    now = int(time.time() * 1000)
    rows = [("BTC", "84496.41", -0.172), ("ETH", "2692.58", 0.805), ("SOL", "117.47", 2.791), ("XRP", "1.5385", 2.923), ("BNB", "780", 1.844)]
    return json.dumps({"source": "Binance.US", "quote": "USDT", "as_of": now - age_gap_ms, "served": now,
                       "items": [{"sym": s, "pair": s + "USDT", "last": p, "chg_pct": c, "at": now - age_gap_ms} for s, p, c in rows]})


def main():
    srv, url = serve(PUB)
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")

        def page(tv="ok", api="ok", path="/", w=1280, **kw):
            ctx = b.new_context(viewport={"width": w, "height": 900}, **kw)
            asked = []

            def handler(r):
                u = r.request.url
                if "/api/ticker" in u:
                    asked.append(u)
                    if api == "fail":
                        return r.fulfill(status=502, body='{"error":"prices unavailable"}', content_type="application/json")
                    return r.fulfill(status=200, body=body(), content_type="application/json", headers={"age": "70" if api == "age" else "3"})
                if u.endswith("/status.json"):
                    return r.fulfill(status=404, body="")
                return r.continue_() if u.startswith("http://127.0.0.1") else r.abort()
            ctx.route("**/*", handler)
            route_tv(ctx, tv)                                   # registered last, so it answers the widget first
            pg = ctx.new_page()
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto(url + path, wait_until="load")
            pg.wait_for_timeout(600)
            return ctx, pg, errs, asked

        hdr = "()=>document.querySelector('header').getBoundingClientRect().height"
        state = """()=>{const s=document.getElementById('tk'),v=(q)=>{const e=s.querySelector(q);return e&&getComputedStyle(e).visibility==='visible'&&+getComputedStyle(e).opacity>0};
          return {cls:s.className,iframe:!!s.querySelector('#tv iframe'),tape:v('#tv'),row:v('.tkrow'),credit:v('.tkc'),still:v('.tks'),btn:v('.tkp'),
                  label:s.querySelector('.tkp').getAttribute('aria-label'),box:s.querySelector('.tkbox').getBoundingClientRect().height}}"""

        # loaded: the tape, with troid's settings
        ctx, pg, errs, asked = page("ok", color_scheme="dark")
        st, cfg = pg.evaluate(state), pg.evaluate("window.__tv && window.__tv.cfg")
        h_ok = pg.evaluate(hdr)
        ok("loaded: the tape shows, the still row doesn't, pause is offered", st["iframe"] and st["tape"] and not st["row"] and st["btn"]
           and st["label"] == EN["ticker.pause_label"], st)
        ok("the tape's symbols are _ticker_universe's, in order: crypto, commodities, stocks", cfg and [x["proName"] for x in cfg["symbols"]] == TAPE, cfg)
        ok("the tape's settings: transparent, adaptive, no logos, English, the page's dark theme",
           cfg and cfg["isTransparent"] is True and cfg["displayMode"] == "adaptive" and cfg["showSymbolLogo"] is False
           and cfg["locale"] == "en" and cfg["colorTheme"] == "dark", cfg)
        ok("a tapped symbol opens troid's desk with the symbol named, never TradingView's site",
           cfg and cfg["largeChartUrl"] == "https://troid.ai/?tvwidgetsymbol={symbolname}#desk", cfg and cfg["largeChartUrl"])
        ok("the box is the tape's height on a wide screen: 44 px", st["box"] == 44, st)
        a = pg.evaluate("""()=>{const a=document.querySelector('#tk .tkc a'),c=getComputedStyle(a).color,d=document.createElement('i');
          d.style.color=getComputedStyle(document.documentElement).getPropertyValue('--dim');document.body.appendChild(d);const v=getComputedStyle(d).color;d.remove();
          return {href:a.href,text:a.textContent,c,v}}""")
        ok("TradingView's attribution under the tape, its link kept, in the dim ink", st["credit"] and a["href"] == "https://www.tradingview.com/"
           and a["text"] == EN["ticker.credit"] and a["c"] == a["v"], a)
        ok("while the tape shows, /api/ticker isn't asked", not asked, asked)
        ok("no script errors", not errs, errs)
        # pause: the frame goes, troid's still row takes its place, the header doesn't move
        pg.click("#tk .tkp")
        pg.wait_for_timeout(700)
        st = pg.evaluate(state)
        ok("pause: the frame is removed and the still row shows, priced; play is offered; same header height",
           not st["iframe"] and st["row"] and "still" in st["cls"] and st["still"] and not st["credit"] and st["label"] == EN["ticker.play_label"]
           and pg.evaluate(hdr) == h_ok and asked, [st, pg.evaluate(hdr), h_ok, len(asked)])
        text = pg.evaluate("document.querySelector('#tk .tkrow').innerText.replace(/\\s+/g,' ')")
        ok("the still row: five prices with ▲/▼, then gold and oil, then the stocks, groups apart",
           all(x in text for x in ("BTC 84,496 ▼ 0.17%", "ETH 2,693 ▲ 0.81%", "SOL 117.47 ▲ 2.79%", "XRP 1.5385 ▲ 2.92%", "BNB 780.00 ▲ 1.84%"))
           and text.index("BNB") < text.index(EN["ticker.sym.XAU"]) < text.index(EN["ticker.sym.WTI"]) < text.index("NVDA") < text.index("AMZN")
           and text.count("│") == 2, text)
        rgb = pg.evaluate("""()=>{const c=getComputedStyle(document.querySelector('#tk .c')).color,d=document.createElement('i');
          d.style.color=getComputedStyle(document.documentElement).getPropertyValue('--dim');document.body.appendChild(d);const v=getComputedStyle(d).color;d.remove();return [c,v]}""")
        ok("the still row's change is in the dim ink, no green or red", rgb[0] == rgb[1], rgb)
        ok("the still row's label names its source", EN["ticker.still"].replace("{source}", "Binance.US") in pg.inner_text("#tk .tks"), pg.inner_text("#tk .tks"))
        # use as entry, from the still row on the desk
        pg.click('#tk [data-sym="ETH"]')
        pg.wait_for_timeout(100)
        note = pg.locator("#tk-use")
        ok("the desk: a symbol opens its note", note.is_visible() and "ETH 2,693" in note.inner_text(), note.inner_text() if note.count() else "")
        pg.click("#tk-use button")
        pg.wait_for_timeout(100)
        ok("use as entry: the exchange's price in the entry field, the note closed, the desk recomputed",
           pg.input_value("#entry") == "2692.58" and not note.is_visible() and "stop at or above entry on a long" in pg.inner_text("#result .vsent"),
           [pg.input_value("#entry"), pg.inner_text("#result .vsent")])
        # play: the tape comes back
        pg.click("#tk .tkp")
        pg.wait_for_timeout(700)
        st = pg.evaluate(state)
        ok("play: the tape is back, the header the same height", st["iframe"] and st["tape"] and not st["row"] and pg.evaluate(hdr) == h_ok
           and pg.evaluate("window.__tv.loads") == 2, [st, pg.evaluate(hdr)])
        ok("no script errors, paused and played", not errs, errs)
        ctx.close()

        ctx, pg, errs, asked = page("ok", color_scheme="light")
        ok("light theme: the tape is asked for TradingView's light theme", pg.evaluate("window.__tv.cfg.colorTheme") == "light")
        ctx.close()

        # loading: the widget hasn't answered; nothing shows yet and the header keeps its height
        ctx, pg, errs, asked = page("hang")
        st = pg.evaluate(state)
        ok("loading: the box is reserved and empty, the header the same height", not st["iframe"] and not st["row"] and st["box"] == 44
           and pg.evaluate(hdr) == h_ok, [st, pg.evaluate(hdr), h_ok])
        ctx.unroute_all(behavior="ignoreErrors")
        ctx.close()

        # failed: the still row fades in where the tape was; no pause button, since nothing moves
        ctx, pg, errs, asked = page("fail")
        pg.wait_for_timeout(700)
        st = pg.evaluate(state)
        ok("failed: the still row takes the tape's place, priced, no pause, same height, not an error",
           "fail" in st["cls"] and "still" in st["cls"] and st["row"] and not st["btn"] and pg.evaluate(hdr) == h_ok and not errs,
           [st, pg.evaluate(hdr), errs])
        ctx.close()

        ctx, pg, errs, asked = page("fail", api="fail")
        st = pg.evaluate(state)
        ok("widget and prices both failed: an empty box, the header the same height, no error",
           not st["row"] and not st["still"] and pg.evaluate(hdr) == h_ok and not errs, [st, errs])
        ctx.close()

        ctx, pg, errs, asked = page("fail", api="age")
        pg.wait_for_timeout(300)
        st = pg.evaluate("()=>{const s=document.getElementById('tk');return [s.className,getComputedStyle(s.querySelector('.tkd')).visibility,s.querySelector('.tkd').innerText]}")
        ok("a still-row price over 60 s old: greyed and 'delayed', the header the same height", "stale" in st[0] and st[1] == "visible"
           and st[2].lower() == EN["ticker.delayed"] and pg.evaluate(hdr) == h_ok, [st, pg.evaluate(hdr)])
        ctx.close()

        # reduced motion: the still row by default, the widget not even asked for until play
        ctx, pg, errs, asked = page("ok", reduced_motion="reduce")
        st = pg.evaluate(state)
        ok("reduced motion: the still row, play offered, the widget never requested, same height",
           "still" in st["cls"] and st["row"] and not st["iframe"] and pg.evaluate("!window.__tv") and st["label"] == EN["ticker.play_label"]
           and pg.evaluate(hdr) == h_ok, [st, pg.evaluate(hdr)])
        ok("reduced motion: no transition", pg.evaluate("getComputedStyle(document.querySelector('#tk .tkrow')).transitionDuration") == "0s")
        pg.click("#tk .tkp")
        pg.wait_for_timeout(500)
        ok("reduced motion, play pressed: the tape loads", pg.evaluate("!!document.querySelector('#tv iframe')") and pg.evaluate(hdr) == h_ok)
        ctx.close()

        for path in ("/faq", "/compare", "/ledger"):
            ctx, pg, errs, asked = page("fail", path=path)
            st = pg.evaluate("()=>{const s=document.getElementById('tk');return [s.querySelectorAll('.tkrow button').length,s.querySelectorAll('[data-sym]').length,!!document.getElementById('tk-use')]}")
            ok(f"{path}: the still row's symbols are text, no 'use as entry'", st == [0, 5, False], st)
            ctx.close()

        ctx, pg, errs, asked = page("ok", "ok", "/", w=320, is_mobile=True, has_touch=True, device_scale_factor=2)
        st = pg.evaluate(state)
        h_ph = pg.evaluate(hdr)
        ok("phone: the box is the tape's compact 72 px, and the tape fills it", st["box"] == 72 and pg.evaluate("document.querySelector('#tv iframe').getBoundingClientRect().height") == 72, st)
        pg.click("#tk .tkp")
        pg.wait_for_timeout(700)
        st = pg.evaluate("""()=>{const r=document.querySelector('#tk .tkrow');return {sw:document.documentElement.scrollWidth,W:document.documentElement.clientWidth,
          rowScroll:r.scrollWidth>r.clientWidth,snap:getComputedStyle(r).scrollSnapType}}""")
        ok("phone, paused: the row scrolls with snap inside the page; the page doesn't scroll sideways; same height",
           st["sw"] <= st["W"] and st["rowScroll"] and st["snap"].startswith("x") and pg.evaluate(hdr) == h_ph, [st, pg.evaluate(hdr), h_ph])
        ctx.close()
        b.close()
    srv.shutdown()

    # every language troid publishes gets a locale TradingView's widgets carry (its Ticker Tape page, read 2026-09-24)
    tv = set("ar_AE,br,ca_ES,de_DE,en,es,fr,he_IL,id,in,it,ja,kr,ms_MY,pl,ru,th_TH,tr,vi_VN,zh_CN,zh_TW".split(","))
    codes = [x["code"] for x in json.loads((ROOT / "web" / "i18n" / "languages.json").read_text())["languages"]]
    ok("every language troid publishes maps to a TradingView widget locale (Hindi and Bengali to English)",
       len(codes) == 10 and all(site_build.TV_LOCALE.get(c, "en") in tv for c in codes)
       and [site_build.TV_LOCALE.get(c, "en") for c in ("zh", "ar", "pt", "hi", "bn")] == ["zh_CN", "ar_AE", "br", "en", "en"], codes)
    print(f"RESULT: {len(fails)} failed ({n} checks)")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
