#!/usr/bin/env python3
"""The calendar strip (web/public/calendar.js; ticker v2 handoff, section D), in Chromium against web/public served
locally. /calendar.json is answered by the test with events placed around the moment it runs, TradingView's script by
backtest/tv_stub.py and /api/ticker by a fixed body: spends nothing, calls no one.

  python web/test_calendar_page.py

- The next 7 days only, in order: kind, period, the reader's local time with UTC beside it (UTC once for a reader in UTC).
- On the desk, and only there, each event says how long before or after the selected firm's nearest reset it lands,
  from firms.json reset_clock, in the firm's own zone; it follows the firm field.
- A tap opens the note: what and when, the MEASURED finding with its sample and what it doesn't show, inside or outside
  the 12:00-16:00 UTC bar, and the agency's schedule with its read date.
- No events in 7 days: the empty line. A schedule that fails or is over 14 days old: hidden, its space kept. The header
  is the same height in every one of those states.
- When the events don't fit it moves, a copy following it that is out of the Tab order and hidden from screen readers,
  by exactly the distance from the first event to its copy; it holds on hover, resumes 3 s after; keyboard focus, the
  tape's pause and reduced motion each make it a still row that swipes; right to left it moves the other way.
- The page never scrolls sideways on a phone, and every page with the tape has the strip and one working note.
"""
import datetime as dt
import json
import sys
import time
from pathlib import Path
from zoneinfo import ZoneInfo

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backtest"))
from i18n_equiv import PUB, serve  # noqa: E402
from tv_stub import route_tv  # noqa: E402
import site_build  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
EN = json.loads((ROOT / "web" / "i18n" / "en.json").read_text())
FIRMS = json.loads((ROOT / "firms.json").read_text())
UTC = dt.timezone.utc
fails, n = [], 0


def ok(name, cond, info=""):
    global n
    n += 1
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else f"  {str(info)[:400]}"))
    if not cond:
        fails.append(name)


NOW = dt.datetime.now(UTC).replace(second=0, microsecond=0)
D1 = (NOW + dt.timedelta(days=1)).replace(hour=12, minute=30)        # inside the 12:00-16:00 UTC bar
D2 = (NOW + dt.timedelta(days=2)).replace(hour=18, minute=0)         # outside it
TODAY = NOW.strftime("%Y-%m-%d")


def ev(kind, at, source="BLS", url="https://www.bls.gov/schedule/news_release/cpi.htm", **kw):
    return {"kind": kind, **kw, "utc": at.strftime("%Y-%m-%dT%H:%MZ"), "source": source, "url": url, "read": TODAY}


BASE = [ev("cpi", NOW - dt.timedelta(hours=2), period="2026-07"),                                           # passed
        ev("cpi", D1, period="2026-08"),
        ev("fomc", D2, source="Federal Reserve", url="https://www.federalreserve.gov/newsevents/calendar.htm"),
        ev("jobs", NOW + dt.timedelta(days=9), period="2026-09",
           url="https://www.bls.gov/schedule/news_release/empsit.htm")]                                    # past 7 days
MANY = BASE + [ev(k, (NOW + dt.timedelta(days=d)).replace(hour=h, minute=m), **kw) for k, d, h, m, kw in [
    ("ppi", 3, 12, 30, {"period": "2026-08"}), ("jolts", 4, 14, 0, {"period": "2026-08"}),
    ("gdp", 5, 12, 30, {"period": "2026-Q3", "estimate": "advance", "source": "BEA", "url": "https://www.bea.gov/news/schedule"}),
    ("pce", 5, 12, 31, {"period": "2026-08", "source": "BEA", "url": "https://www.bea.gov/news/schedule"})]]


def doc(events, read=TODAY):
    return json.dumps({"read": read, "reads": {}, "events": sorted(events, key=lambda e: e["utc"])})


def tick():
    now = int(time.time() * 1000)
    return json.dumps({"source": "Binance.US", "quote": "USDT", "as_of": now, "served": now,
                       "items": [{"sym": "BTC", "pair": "BTCUSDT", "last": "84496.41", "chg_pct": -0.17, "at": now}]})


def main():
    srv, url = serve(PUB)
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")

        def page(cal=None, status=200, path="/faq", w=1280, tz="UTC", rtl=False, **kw):
            ctx = b.new_context(viewport={"width": w, "height": 900}, timezone_id=tz, locale="en-US", **kw)

            def handler(r):
                u = r.request.url
                if u.endswith("/calendar.json"):
                    return r.fulfill(status=status, body=cal if cal is not None else doc(BASE), content_type="application/json")
                if "/api/ticker" in u:
                    return r.fulfill(status=200, body=tick(), content_type="application/json")
                if u.endswith("/status.json"):
                    return r.fulfill(status=404, body="")
                return r.continue_() if u.startswith("http://127.0.0.1") else r.abort()
            ctx.route("**/*", handler)
            route_tv(ctx, "ok")
            if rtl:
                ctx.add_init_script("document.addEventListener('readystatechange',()=>{document.documentElement.dir='rtl'},{once:true})")
            pg = ctx.new_page()
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto(url + path, wait_until="load")
            pg.wait_for_timeout(700)
            return ctx, pg, errs

        strip = """()=>{const c=document.getElementById('cal'),r=c.querySelector('.calrow');
          return {cls:c.className,vis:getComputedStyle(c).visibility,h:c.getBoundingClientRect().height,
            lines:[...r.querySelectorAll('.cale:not(.calclone)')].map(b=>b.textContent),
            clones:[...r.querySelectorAll('.cale.calclone')].map(b=>[b.getAttribute('aria-hidden'),b.tabIndex,b.textContent]),
            empty:(r.querySelector('.calempty')||{}).textContent||null,x:c.style.getPropertyValue('--calx'),
            t:c.style.getPropertyValue('--calt'),anim:getComputedStyle(r).animationName,play:getComputedStyle(r).animationPlayState,
            sw:r.scrollWidth,cw:r.clientWidth,ov:getComputedStyle(r).overflowX}}"""
        hdr = "()=>document.querySelector('h1').getBoundingClientRect().top+scrollY"   # nothing under the strip moves

        def wd(t, tz):
            return t.astimezone(ZoneInfo(tz)).strftime("%a %H:%M")

        # the next 7 days, in order, local time with UTC once or beside it
        ctx, pg, errs = page()
        s = pg.evaluate(strip)
        want = [f"CPI (Aug) · {wd(D1, 'UTC')} UTC", f"FOMC statement · {wd(D2, 'UTC')} UTC"]
        ok("the strip shows once the schedule loads", "off" not in s["cls"] and s["vis"] == "visible", s)
        ok("only the next 7 days, in order; a reader in UTC sees UTC once; no reset phrase off the desk", s["lines"] == want, s["lines"])
        ok("the strip is 32 px tall", abs(s["h"] - 32) < 0.5, s["h"])
        h_live = pg.evaluate(hdr)
        # the note: CPI lands inside the bar the finding is about, FOMC outside
        pg.click("#cal .cale >> nth=0")
        note = pg.evaluate("""()=>{const n=document.getElementById('cal-note');return {hidden:n.hidden,txt:n.textContent,
          href:n.querySelector('.cn3 a')&&n.querySelector('.cn3 a').getAttribute('href'),exp:document.querySelector('#cal .cale').getAttribute('aria-expanded')}}""")
        cn1 = EN["calendar.note.what"].format(when=D1.strftime("%a, %b %-d, %H:%M") + " UTC", what=EN["calendar.long.cpi"] + " (August 2026)", source="BLS")
        ok("a tap opens the note, its button expanded", not note["hidden"] and note["exp"] == "true", note)
        ok("the note says what and when", cn1 in note["txt"], (cn1, note["txt"]))
        ok("the note carries the MEASURED finding and what it doesn't show",
           EN["calendar.note.measured"] in note["txt"] and EN["calendar.note.cause"] in note["txt"] and "Scheduled releases move prices" not in note["txt"])
        ok("a release at 12:30 UTC lands inside the bar", EN["calendar.note.inside"] in note["txt"])
        ok("the note links the agency's schedule with the read date",
           note["href"] == BASE[1]["url"] and f"read {TODAY}" in note["txt"] and "never a forecast" in note["txt"], note)
        pg.click("#cal .cale >> nth=1")
        ok("a release at 18:00 UTC lands outside it", EN["calendar.note.outside"] in pg.text_content("#cal-note"))
        pg.click("#cal .cale >> nth=1")
        ok("a second tap closes it (pop.js runs once)", pg.evaluate("document.getElementById('cal-note').hidden"))
        ok("no page error", not errs, errs)
        ctx.close()

        # a reader elsewhere: local time first, UTC beside it
        ctx, pg, errs = page(tz="Asia/Tokyo")
        s = pg.evaluate(strip)
        ok("a reader in Tokyo sees local time, then UTC", s["lines"][0] == f"CPI (Aug) · {wd(D1, 'Asia/Tokyo')} · {D1:%H:%M} UTC", s["lines"])
        ctx.close()

        # the desk: before or after the selected firm's reset, in the firm's own zone, following the firm field
        def reset_phrase(t, key):
            f = FIRMS[key]
            z = ZoneInfo(f["reset_clock"]["tz"])
            hh, mm = map(int, f["reset_clock"]["time"].split(":"))
            day = t.astimezone(z).replace(hour=hh, minute=mm)
            r = min((day + dt.timedelta(days=k) for k in (-1, 0, 1)), key=lambda x: (abs((x - t).total_seconds()), x < t))
            m = round(abs((r - t).total_seconds()) / 60)
            span = EN["calendar.m"].format(m=m) if m < 60 else EN["calendar.h"].format(h=m // 60) if m % 60 == 0 else EN["calendar.hm"].format(h=m // 60, m=m % 60)
            return EN["calendar.before" if r > t else "calendar.after"].format(t=span, firm=f["name"])
        ctx, pg, errs = page(path="/")
        s = pg.evaluate(strip)
        firm0 = pg.evaluate("document.getElementById('firm').value")
        ok(f"the desk adds the reset phrase ({FIRMS[firm0]['name']}: {reset_phrase(D1, firm0)})",
           s["lines"][0] == f"CPI (Aug) · {wd(D1, 'UTC')} UTC · {reset_phrase(D1, firm0)}", s["lines"])
        for key in [k for k in FIRMS if isinstance(FIRMS[k], dict) and FIRMS[k].get("reset_clock") and k != firm0]:
            pg.select_option("#firm", key)
            pg.wait_for_timeout(100)
            s = pg.evaluate(strip)
            ok(f"the phrase follows the firm field: {FIRMS[key]['name']}, {reset_phrase(D1, key)} / {reset_phrase(D2, key)}",
               s["lines"] == [f"CPI (Aug) · {wd(D1, 'UTC')} UTC · {reset_phrase(D1, key)}", f"FOMC statement · {wd(D2, 'UTC')} UTC · {reset_phrase(D2, key)}"], s["lines"])
        ok("no page error on the desk", not errs, errs)
        ctx.close()

        # empty, failed, stale: the header keeps its height
        for name, kw, want_off in [("no events in 7 days", {"cal": doc(BASE[3:])}, False),
                                   ("the schedule fails", {"status": 404, "cal": "{}"}, True),
                                   ("the schedule is over 14 days old", {"cal": doc(BASE, read=(NOW - dt.timedelta(days=15)).strftime("%Y-%m-%d"))}, True),
                                   ("the schedule is broken", {"cal": "not json"}, True)]:
            ctx, pg, errs = page(**kw)
            s = pg.evaluate(strip)
            if want_off:
                ok(f"{name}: hidden, its space kept", "off" in s["cls"] and s["vis"] == "hidden" and abs(s["h"] - 32) < 0.5, s)
            else:
                ok(f"{name}: the empty line", s["empty"] == EN["calendar.empty"] and s["vis"] == "visible" and not s["lines"], s)
            ok(f"{name}: the page under the strip sits where it does with events", abs(pg.evaluate(hdr) - h_live) < 0.5, (pg.evaluate(hdr), h_live))
            ctx.close()

        # a phone: the events don't fit, so the row moves
        ctx, pg, errs = page(cal=doc(MANY), w=375, tz="America/New_York", is_mobile=True, has_touch=True)
        s = pg.evaluate(strip)
        ok("375 px: the page never scrolls sideways", pg.evaluate("document.scrollingElement.scrollWidth<=innerWidth"))
        ok("375 px: events that don't fit move", "mv" in s["cls"] and s["anim"] == "calmv" and s["play"] == "running", s)
        ok("the copy is out of the Tab order and hidden from screen readers, and says the same",
           len(s["clones"]) == len(s["lines"]) == 6 and all(c[0] == "true" and c[1] == -1 for c in s["clones"])
           and [c[2] for c in s["clones"]] == s["lines"], s["clones"])
        gap = pg.evaluate("""()=>{const r=document.querySelector('#cal .calrow');r.style.animation='none';
          const a=r.querySelector('.cale:not(.calclone)').getBoundingClientRect().left,z=r.querySelector('.cale.calclone').getBoundingClientRect().left;
          r.style.animation='';return a-z}""")
        ok("it moves by exactly the distance from the first event to its copy, at about 40 px/s",
           abs(float(s["x"][:-2]) - gap) < 0.5 and gap < 0 and abs(float(s["t"][:-1]) - abs(gap) / 40) < 0.1, (s["x"], s["t"], gap))
        pg.dispatch_event("#cal .cale.calclone >> nth=0", "click")   # it is moving: a click event, not a pointer
        ok("tapping the copy opens the same note", not pg.evaluate("document.getElementById('cal-note').hidden")
           and "Consumer Price Index" in pg.text_content("#cal-note .cn1"))
        pg.mouse.click(5, 800)
        ctx.close()

        ctx, pg, errs = page(cal=doc(MANY), w=375)
        pg.hover("#cal")
        ok("hover holds it", pg.evaluate("document.getElementById('cal').classList.contains('hold')")
           and pg.evaluate("getComputedStyle(document.querySelector('#cal .calrow')).animationPlayState") == "paused")
        pg.mouse.move(5, 800)
        pg.wait_for_timeout(1500)
        ok("still held 1.5 s after", pg.evaluate("document.getElementById('cal').classList.contains('hold')"))
        pg.wait_for_timeout(1800)
        ok("moving again 3 s after", not pg.evaluate("document.getElementById('cal').classList.contains('hold')"))
        for _ in range(60):                                   # Tab until focus is in the strip
            pg.keyboard.press("Tab")
            if pg.evaluate("!!document.activeElement.closest('#cal')"):
                break
        s = pg.evaluate(strip)
        ok("keyboard focus makes it a still row, no copy, and the focused event stays in view",
           "mv" not in s["cls"] and not s["clones"] and s["ov"] == "auto" and pg.evaluate(
               "(()=>{const r=document.activeElement.getBoundingClientRect(),c=document.getElementById('cal').getBoundingClientRect();return r.left>=c.left-1&&r.right<=c.right+1})()"), s)
        pg.keyboard.press("Enter")
        ok("Enter opens the note from the keyboard", not pg.evaluate("document.getElementById('cal-note').hidden"))
        pg.keyboard.press("Escape")
        ctx.close()

        ctx, pg, errs = page(cal=doc(MANY), w=375)
        pg.click(".tkp")
        pg.wait_for_timeout(200)
        s = pg.evaluate(strip)
        ok("the tape's pause stops the strip too", "mv" not in s["cls"] and not s["clones"] and s["sw"] > s["cw"], s)
        pg.click(".tkp")
        pg.wait_for_timeout(200)
        ok("play moves it again", "mv" in pg.evaluate(strip)["cls"])
        ctx.close()

        # a phone (the owner's Android check): a tap is reported as a hover that never ends, so a note opened and closed
        # by touch must leave the strip moving again within 4 s, however the note is closed
        moved = """async()=>{const r=document.querySelector('#cal .calrow'),x=()=>new DOMMatrix(getComputedStyle(r).transform).m41;
          const a=x();await new Promise(f=>setTimeout(f,400));return {held:document.getElementById('cal').classList.contains('hold'),
          play:getComputedStyle(r).animationPlayState,moved:Math.abs(x()-a)}}"""

        def tap_event(pg):                                    # the middle of an event that is on the screen now
            return pg.evaluate("""()=>{const c=document.getElementById('cal').getBoundingClientRect();
              for(const b of document.querySelectorAll('#cal .cale')){const r=b.getBoundingClientRect(),x=Math.max(r.left,c.left)+Math.min(r.right-Math.max(r.left,c.left),c.right-Math.max(r.left,c.left))/2;
                if(r.right>c.left+20&&r.left<c.right-20)return [x,r.top+r.height/2]}}""")
        for how in ("the same event again", "somewhere else", "Esc"):
            ctx, pg, errs = page(cal=doc(MANY), w=390, is_mobile=True, has_touch=True)
            x, y = tap_event(pg)
            pg.touchscreen.tap(x, y)
            pg.wait_for_timeout(250)
            opened = not pg.evaluate("document.getElementById('cal-note').hidden")
            held = pg.evaluate("document.getElementById('cal').classList.contains('hold')")
            pg.wait_for_timeout(3500)
            still_held = pg.evaluate("document.getElementById('cal').classList.contains('hold')")
            if how == "the same event again":
                pg.touchscreen.tap(x, y)
            elif how == "somewhere else":
                pg.touchscreen.tap(195, 700)
            else:
                pg.keyboard.press("Escape")
            pg.wait_for_timeout(250)
            closed = pg.evaluate("document.getElementById('cal-note').hidden")
            pg.wait_for_timeout(3750)                             # 4 s after the note closed
            m = pg.evaluate(moved)
            ok(f"touch: a note opened by a tap holds the strip, and closed by tapping {how} it moves again within 4 s" if how != "Esc"
               else "touch: a note opened by a tap and closed with Esc: the strip moves again within 4 s",
               opened and held and still_held and closed and not m["held"] and m["play"] == "running" and m["moved"] > 5,
               dict(opened=opened, held_open=held, still_held=still_held, closed=closed, after=m))
            ctx.close()
        ctx, pg, errs = page(cal=doc(MANY), w=390, is_mobile=True, has_touch=True)
        x, y = tap_event(pg)
        pg.touchscreen.tap(x, y)
        pg.touchscreen.tap(x, y)
        pg.wait_for_timeout(4000)
        ok("touch: a tap on the strip with no note left open moves again within 4 s", not pg.evaluate(moved)["held"])
        ctx.close()

        ctx, pg, errs = page(cal=doc(MANY), w=375, reduced_motion="reduce")
        s = pg.evaluate(strip)
        ok("reduced motion: a still row that swipes", "mv" not in s["cls"] and not s["clones"] and s["ov"] == "auto" and s["sw"] > s["cw"], s)
        ctx.close()

        ctx, pg, errs = page(cal=doc(MANY), w=375, rtl=True)
        s = pg.evaluate(strip)
        ok("right to left it moves the other way", "mv" in s["cls"] and float(s["x"][:-2]) > 0, s)
        ok("right to left, the page never scrolls sideways", pg.evaluate("document.scrollingElement.scrollWidth<=innerWidth"))
        ctx.close()

        # every page with the tape has the strip, pop.js once, and a note that opens and closes
        for pgname in [x for x in site_build.PAGES if x != "tearsheet"]:
            path = {"index": "/"}.get(pgname, "/" + pgname)
            ctx, pg, errs = page(path=path)
            got = pg.evaluate("""()=>({cal:!!document.getElementById('cal'),n:document.querySelectorAll('#cal').length,
              pops:[...document.scripts].filter(s=>/\\/pop\\.js$/.test(s.src)).length,loaded:!!window.troidPop,
              lines:document.querySelectorAll('#cal .cale').length})""")
            pg.click("#cal .cale >> nth=0")
            opened = not pg.evaluate("document.getElementById('cal-note').hidden")
            pg.click("#cal .cale >> nth=0")
            closed = pg.evaluate("document.getElementById('cal-note').hidden")
            ok(f"{pgname}: the strip, pop.js once, a note that opens and closes", got["n"] == 1 and got["pops"] == 1
               and got["loaded"] and got["lines"] == 2 and opened and closed and not errs, (got, opened, closed, errs))
            ctx.close()
        b.close()
    srv.shutdown()
    print(f"\n{n - len(fails)}/{n} passed")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
