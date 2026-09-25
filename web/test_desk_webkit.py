#!/usr/bin/env python3
"""troid's desk in WebKit, laid out as an iPhone lays it out (Playwright's iPhone 13 profile: 390 x 664, touch, Safari's
user agent). The owner tests on iPhone Safari; Chromium can't show what WebKit does with sticky positioning inside the
desk, with a tap outside a note, or with a field's text size. web/public is served locally, /api/ticker and TradingView's
script are answered by the test: spends nothing, calls no one.

  python web/test_desk_webkit.py            # needs Playwright's WebKit: python -m playwright install --with-deps webkit
  python web/test_desk_webkit.py --path /desk-preview

.github/workflows/webkit.yml runs it on GitHub's runners, where WebKit installs; the container troid is built in has only
Chromium, and there it says it did not run instead of passing.

- The gauge stays pinned under the tape while the desk scrolls under it, down and back up (the owner's iPhone check,
  kept as a regression test), and a note opened on the desk closes on a tap on the page with the gauge still in view.
- Every desk field is 16 px, so Safari doesn't zoom into it; "use" fills the entry without focusing it.
- The first view has no example trade; a tape tap selects the asset without the shared-link notice; nothing is wider
  than the phone.
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backtest"))
from i18n_equiv import PUB, serve  # noqa: E402
from tv_stub import route_tv  # noqa: E402

EN = json.loads((Path(__file__).resolve().parent / "i18n" / "en.json").read_text())
fails, n = [], 0


def ok(name, cond, info=""):
    global n
    n += 1
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else f"  {str(info)[:400]}"))
    if not cond:
        fails.append(name)


def tick():
    now = int(time.time() * 1000)
    rows = [("BTC", "84496.41"), ("ETH", "2692.58"), ("SOL", "117.47"), ("XRP", "1.5385"), ("BNB", "780")]
    return json.dumps({"source": "Binance.US", "quote": "USDT", "as_of": now, "served": now,
                       "items": [{"sym": s, "pair": s + "USDT", "last": p, "chg_pct": 0.5, "at": now} for s, p in rows]})


GAUGE = """()=>{const g=document.getElementById('gauge').getBoundingClientRect(),d=document.getElementById('desk').getBoundingClientRect();
  return {top:g.top,bottom:g.bottom,h:g.height,deskTop:d.top,deskBottom:d.bottom,vh:innerHeight}}"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", default="/")
    a = ap.parse_args()
    from playwright.sync_api import sync_playwright
    srv, url = serve(PUB)
    with sync_playwright() as p:
        try:
            b = p.webkit.launch()
        except Exception as e:                       # no WebKit here: say so, don't pass
            print(f"NOT RUN: WebKit isn't installed here ({str(e).splitlines()[0][:120]})")
            srv.shutdown()
            sys.exit(2)
        phone = p.devices["iPhone 13"]

        def page(path=a.path, **kw):
            ctx = b.new_context(**{**phone, **kw})

            def handler(r):
                u = r.request.url
                if "/api/ticker" in u:
                    return r.fulfill(status=200, body=tick(), content_type="application/json")
                if u.endswith("/status.json") or u.endswith("/calendar.json"):
                    return r.fulfill(status=404, body="")
                return r.continue_() if u.startswith("http://127.0.0.1") else r.abort()
            ctx.route("**/*", handler)
            route_tv(ctx, "ok")
            pg = ctx.new_page()
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto(url + path, wait_until="load")
            pg.wait_for_timeout(800)
            return ctx, pg, errs

        # the gauge stays pinned while the desk scrolls, down and back up
        ctx, pg, errs = page()
        pg.fill("#entry", "77872")
        pg.fill("#stop", "74814")
        pg.evaluate("document.getElementById('st-account').open=true;document.getElementById('st-risk').open=true")
        start = pg.evaluate("document.getElementById('desk').getBoundingClientRect().top+scrollY")
        end = pg.evaluate("document.getElementById('desk').getBoundingClientRect().bottom+scrollY")
        bad = []
        for y in list(range(int(start), int(end) - 300, 160)) + list(range(int(end) - 300, int(start), -160)):
            pg.evaluate(f"scrollTo(0,{y})")
            pg.wait_for_timeout(60)
            g = pg.evaluate(GAUGE)
            if g["deskTop"] < 0 and g["deskBottom"] > g["h"] + 40 and not (-1 <= g["top"] <= 1 and g["bottom"] <= g["vh"]):
                bad.append((y, round(g["top"], 1)))
        ok("scrolling down through the desk and back up, the gauge stays pinned under the tape", not bad, bad[:5])

        # a note on the desk closes on a tap on the page; the gauge is still there
        pg.evaluate("scrollTo(0,0)")
        pg.evaluate("document.querySelector('#st-trade').scrollIntoView({block:'center'})")
        pg.wait_for_timeout(150)
        pg.tap('label[for="entry"] .term')
        pg.wait_for_timeout(150)
        opened = not pg.evaluate("document.getElementById('g-entry').hidden")
        box = pg.evaluate("(()=>{const r=document.getElementById('how').getBoundingClientRect();return [r.left+20,Math.min(r.top+20,innerHeight-20)]})()")
        pg.evaluate("scrollBy(0,40)")
        pg.tap("body", position={"x": 8, "y": 300})
        pg.wait_for_timeout(150)
        closed = pg.evaluate("document.getElementById('g-entry').hidden")
        g = pg.evaluate(GAUGE)
        ok("a note opened by a tap closes on a tap on the page, and the gauge is still in view",
           opened and closed and g["bottom"] > 0 and g["top"] < g["vh"], (opened, closed, g, box))
        ok("every desk field is 16 px: Safari doesn't zoom into it",
           set(pg.evaluate("()=>[...document.querySelectorAll('#desk input,#desk select')].map(e=>getComputedStyle(e).fontSize)")) == {"16px"})
        ok("no page error", not errs, errs)
        ctx.close()

        # the tape's "use as entry" note: opens on a tap, closes on a tap outside (reduced motion shows the still row)
        ctx, pg, errs = page(reduced_motion="reduce")
        pg.tap('#tk .tki[data-sym="ETH"]')
        pg.wait_for_timeout(150)
        opened = not pg.evaluate("document.getElementById('tk-use').hidden")
        pg.tap("body", position={"x": 8, "y": 600})
        pg.wait_for_timeout(150)
        ok("the tape's \"use as entry\" note closes on a tap outside it", opened and pg.evaluate("document.getElementById('tk-use').hidden"))
        pg.tap('#tk .tki[data-sym="ETH"]')
        pg.wait_for_timeout(150)
        pg.tap("#tk-use button")
        pg.wait_for_timeout(200)
        ok("\"use\" fills the entry and selects the asset without focusing the field (no zoom)", pg.input_value("#entry") == "2692.58"
           and pg.input_value("#asset") == "ETH" and pg.evaluate("document.activeElement.id") != "entry", pg.evaluate("document.activeElement.id"))
        ctx.close()

        # the chip: the same, from the entry field
        ctx, pg, errs = page()
        pg.tap("#chipb")
        pg.wait_for_timeout(200)
        ok("the chip fills the entry without focusing it", pg.input_value("#entry") == "84496.41" and pg.evaluate("document.activeElement.id") != "entry")
        ctx.close()

        # the first view, a tape tap, the width
        ctx, pg, errs = page()
        ok("the first view: entry and stop empty, \"Enter your entry and stop to size a trade.\"", pg.input_value("#entry") == "" and pg.input_value("#stop") == ""
           and pg.inner_text("#result").startswith(EN["desk2.js.empty"]))
        ok("nothing is wider than the phone", pg.evaluate("document.scrollingElement.scrollWidth<=innerWidth"))
        ctx.close()
        base = a.path.split("#")[0]
        ctx, pg, errs = page(f"{base}?tvwidgetsymbol=BINANCEUS:ETHUSDT#desk&utm_source=troid.ai&utm_medium=widget")
        ok("a tape tap: ETH selected, \"ETH selected · live … · use\" by the entry, no shared-link notice",
           pg.input_value("#asset") == "ETH" and pg.inner_text("#chipb").startswith("ETH selected · live") and pg.evaluate("document.getElementById('shared').hidden"))
        ctx.close()
        b.close()
    srv.shutdown()
    print(f"\n{n - len(fails)}/{n} passed (WebKit, iPhone 13)")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
