#!/usr/bin/env python3
"""The price strip (web/public/ticker.js), in Chromium against web/public served locally, with /api/ticker answered
by the test. Spends nothing and calls no exchange.

  python web/test_ticker_page.py

- It appears once prices arrive, in the page's dim ink with ▲/▼ (no green, no red), and names its source.
- Before the first answer and after a failed one it is hidden with its space kept: the header's height never changes.
- A price whose age (the CDN's Age header plus the exchange-to-server gap) passes 60 s greys the strip: "delayed".
- On the desk a symbol opens a note; "use as entry" puts the exchange's price in the entry field and the desk
  recomputes. On other pages a symbol is text.
- On a phone the row scrolls, with snap, inside the page; the page never scrolls sideways.
"""
import json
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backtest"))
from i18n_equiv import PUB, serve  # noqa: E402

EN = json.loads((Path(__file__).resolve().parent / "i18n" / "en.json").read_text())
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


def route(ctx, mode):
    """mode: ok | age (Age: 70) | fail | hang (never answers)"""
    def handler(r):
        u = r.request.url
        if "/api/ticker" in u:
            if mode == "fail":
                return r.fulfill(status=502, body='{"error":"prices unavailable"}', content_type="application/json")
            if mode == "hang":
                return None
            return r.fulfill(status=200, body=body(), content_type="application/json",
                             headers={"age": "70" if mode == "age" else "3"})
        if u.endswith("/status.json"):
            return r.fulfill(status=404, body="")
        return r.continue_() if u.startswith("http://127.0.0.1") else r.abort()
    ctx.route("**/*", handler)


def main():
    srv, url = serve(PUB)
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")

        def page(mode, path="/", w=1280, **kw):
            ctx = b.new_context(viewport={"width": w, "height": 900}, **kw)
            route(ctx, mode)
            pg = ctx.new_page()
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto(url + path, wait_until="load")
            pg.wait_for_timeout(400)
            return ctx, pg, errs

        hdr = "()=>document.querySelector('header').getBoundingClientRect().height"
        ctx, pg, errs = page("ok")
        st = pg.evaluate("""()=>{const s=document.getElementById('tk'),c=s.querySelector('.c');return {cls:s.className,vis:getComputedStyle(s).visibility,
          text:s.innerText.replace(/\\s+/g,' '),cColor:getComputedStyle(c).color,dim:getComputedStyle(document.documentElement).getPropertyValue('--dim').trim(),
          buttons:s.querySelectorAll('button[data-sym]').length}}""")
        ok("shown once prices arrive", st["cls"] == "tk" and st["vis"] == "visible", st)
        ok("five prices, the change with ▲/▼", all(x in st["text"] for x in ("BTC 84,496 ▼ 0.17%", "ETH 2,693 ▲ 0.81%", "SOL 117.47 ▲ 2.79%",
                                                                              "XRP 1.5385 ▲ 2.92%", "BNB 780.00 ▲ 1.84%")), st["text"])
        ok("the source and the caveat in the label", EN["ticker.label"].replace("{source}", "Binance.US") in st["text"], st["text"])
        rgb = pg.evaluate("c=>{const d=document.createElement('i');d.style.color=c;document.body.appendChild(d);const v=getComputedStyle(d).color;d.remove();return v}", st["dim"])
        ok("the change is in the page's dim ink, no green or red", st["cColor"] == rgb, [st["cColor"], rgb])
        ok("the desk's symbols are buttons", st["buttons"] == 5, st)
        h_ok = pg.evaluate(hdr)
        # use as entry
        pg.click('#tk [data-sym="ETH"]')
        pg.wait_for_timeout(100)
        note = pg.locator("#tk-use")
        ok("a symbol opens its note", note.is_visible() and "ETH 2,693" in note.inner_text(), note.inner_text() if note.count() else "")
        pg.click("#tk-use button")
        pg.wait_for_timeout(100)
        ok("use as entry: the exchange's price in the entry field, the note closed, the desk recomputed",
           pg.input_value("#entry") == "2692.58" and not note.is_visible() and "stop at or above entry on a long" in pg.inner_text("#result .vsent"),
           [pg.input_value("#entry"), pg.inner_text("#result .vsent")])
        ok("no script errors", not errs, errs)
        ctx.close()

        ctx, pg, errs = page("hang")
        st = pg.evaluate("()=>{const s=document.getElementById('tk');return [s.className,getComputedStyle(s).visibility]}")
        ok("before the first answer: hidden, its space kept", st == ["tk off", "hidden"] and pg.evaluate(hdr) == h_ok, [st, pg.evaluate(hdr), h_ok])
        ctx.unroute_all(behavior="ignoreErrors")        # the unanswered request
        ctx.close()

        ctx, pg, errs = page("fail")
        st = pg.evaluate("()=>{const s=document.getElementById('tk');return [s.className,getComputedStyle(s).visibility]}")
        ok("a failed answer: hidden, not an error, the header the same height", st == ["tk off", "hidden"] and pg.evaluate(hdr) == h_ok and not errs, [st, errs])
        ctx.close()

        ctx, pg, errs = page("age")
        st = pg.evaluate("()=>{const s=document.getElementById('tk');return [s.className,getComputedStyle(s.querySelector('.tkd')).visibility,s.querySelector('.tkd').innerText]}")
        ok("over 60 s old: greyed and 'delayed', and the header keeps its height", "stale" in st[0] and st[1] == "visible"
           and st[2].lower() == EN["ticker.delayed"] and pg.evaluate(hdr) == h_ok, [st, pg.evaluate(hdr), h_ok])
        ctx.close()

        for path in ("/faq", "/compare", "/ledger"):
            ctx, pg, errs = page("ok", path)
            st = pg.evaluate("()=>{const s=document.getElementById('tk');return [s.className,s.querySelectorAll('button').length,s.querySelectorAll('[data-sym]').length]}")
            ok(f"{path}: shown, symbols as text", st == ["tk", 0, 5], st)
            ctx.close()

        ctx, pg, errs = page("ok", "/", w=320, is_mobile=True, has_touch=True, device_scale_factor=2)
        st = pg.evaluate("""()=>{const r=document.querySelector('#tk .tkrow');return {sw:document.documentElement.scrollWidth,W:document.documentElement.clientWidth,
          rowScroll:r.scrollWidth>r.clientWidth,snap:getComputedStyle(r).scrollSnapType,vOver:r.scrollHeight>r.clientHeight}}""")
        ok("phone: the row scrolls with snap, the page doesn't scroll sideways", st["sw"] <= st["W"] and st["rowScroll"] and st["snap"].startswith("x")
           and not st["vOver"], st)
        ctx.close()

        ctx, pg, errs = page("ok", "/", reduced_motion="reduce")
        ok("reduced motion: no transition", pg.evaluate("getComputedStyle(document.getElementById('tk')).transitionDuration") == "0s")
        ctx.close()
        b.close()
    srv.shutdown()
    print(f"RESULT: {len(fails)} failed ({n} checks)")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
