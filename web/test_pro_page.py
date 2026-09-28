#!/usr/bin/env python3
"""troid Pro's waitlist page (web/pro/waitlist.html, from web/templates/pro.html; launch handoff 2026-09-26, 6.4 step 1)
in Chromium, served from a copy of the site with the page at /pro and /pro/leave, as web/api/pro/page.js serves it;
/api/pro/waitlist is answered by the test (web/test_pro_waitlist.js tests the function itself). Spends nothing, calls no
one.

  python web/test_pro_page.py

- The page: in preparation, the free desk stays free, the four additions, $19/month or $190/year with tax included,
  "Not investment advice.", troid for agents, the privacy line; no price tape; nothing wider than a phone.
- Join: a bad email or an unticked first box is answered on the page and nothing is sent; a join sends the email and
  both choices and shows the leave link; the service's refusals (a bad email, too many tries, the store down) read as such.
- /pro/leave?t=…: the leave button only; it sends the token, and says it's done or that the link isn't valid; with no
  token there is no button.
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backtest"))
from i18n_equiv import PUB, serve  # noqa: E402

fails, n = [], 0


def ok(name, cond, info=""):
    global n
    n += 1
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else f"  {str(info)[:400]}"))
    if not cond:
        fails.append(name)


def main():
    d = Path(tempfile.mkdtemp())
    for f in PUB.iterdir():
        if f.is_file():
            shutil.copy(f, d / f.name)
    page_html = (ROOT / "web" / "pro" / "waitlist.html").read_text()
    (d / "pro").mkdir()                       # the test server maps /pro to pro/index.html once pro/ exists
    (d / "pro" / "index.html").write_text(page_html)
    (d / "pro" / "leave.html").write_text(page_html)
    srv, url = serve(d)
    sent, reply = [], {"v": (200, {})}
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")

        def new(w=1280):
            ctx = b.new_context(viewport={"width": w, "height": 900})

            def handler(r):
                u = r.request.url
                if not u.startswith(url):
                    return r.abort()
                if "/api/pro/waitlist" in u:
                    sent.append(json.loads(r.request.post_data or "null"))
                    st, body = reply["v"]
                    return r.fulfill(status=st, body=json.dumps(body), content_type="application/json")
                if "/api/" in u or u.endswith("/status.json"):
                    return r.fulfill(status=404, body="{}", content_type="application/json")
                return r.continue_()
            ctx.route("**/*", handler)
            return ctx.new_page()

        pg = new()
        pg.goto(url + "/pro")
        body = pg.inner_text("body")
        for want in ("troid Pro is in preparation.", "The free desk stays free.", "Saved accounts, up to five", "Rule-change alerts",
                     "Journal check", "ask troid at a higher daily limit", "$19/month or $190/year, tax included.",
                     "troid Pro — risk-calculation software. Not investment advice.", "troid for agents",
                     "your trades never leave your device", "Never sold, never shared"):
            ok(f"the page reads {want!r}", want in body)
        ok("no price tape on the page", pg.evaluate("() => !document.querySelector('.tk, .tradingview-widget-container, script[src*=tradingview]')"))
        ok("no hype: no exclamation mark, no 'get funded', no 'pass your challenge'",
           "!" not in body and "get funded" not in body.lower() and "pass your challenge" not in body.lower())

        def said():
            return pg.inner_text("#said")

        sent.clear()
        pg.fill("#em", "not-an-email")
        pg.check("#wpro")
        pg.click("#go")
        ok("a bad email is answered on the page, nothing sent", said() == "That email doesn't look right." and not sent, [said(), sent])
        pg.fill("#em", "trader@example.com")
        pg.uncheck("#wpro")
        pg.click("#go")
        ok("the first box unticked is answered on the page, nothing sent", said() == "Tick the first box to join." and not sent, [said(), sent])
        pg.check("#wpro")
        pg.check("#wag")
        reply["v"] = (200, {"joined": True, "leave_url": "/pro/leave?t=" + "a" * 64 + "." + "B" * 43})
        pg.click("#go")
        pg.wait_for_function("() => /on the list/.test(document.getElementById('said').innerText)")
        link = pg.evaluate("() => { const a = document.querySelector('#said a'); return a && [a.getAttribute('href'), a.innerText] }")
        ok("a join sends the email and both choices", sent == [{"email": "trader@example.com", "pro": True, "agents": True}], sent)
        ok("the joined message carries the leave link, in full", link and link[0] == "/pro/leave?t=" + "a" * 64 + "." + "B" * 43
           and link[1] == url + link[0] and said().startswith("You're on the list. To leave, at any time, one click: "), [link, said()])
        for st, body_, want in ((400, {"field": "email"}, "That email doesn't look right."), (429, {}, "Too many tries from here. Try again in an hour."),
                                (503, {}, "The waitlist couldn't be reached. Try again in a minute.")):
            reply["v"] = (st, body_)
            pg.click("#go")
            pg.wait_for_function("(w) => document.getElementById('said').innerText === w", arg=want)
            ok(f"the service's {st} reads as such", said() == want and not pg.is_disabled("#go"), said())

        pg = new()
        sent.clear()
        tok = "c" * 64 + "." + "D" * 43
        pg.goto(url + "/pro/leave?t=" + tok)
        ok("/pro/leave: the leave button, not the form", pg.is_visible("#bye") and not pg.is_visible("#wl"))
        reply["v"] = (200, {"left": True})
        pg.click("#bye")
        pg.wait_for_function("() => /Done/.test(document.getElementById('said2').innerText)")
        ok("leave: sends the token, says it's done, the button gone", sent == [{"leave": tok}] and pg.inner_text("#said2") == "Done. troid no longer keeps your email."
           and not pg.is_visible("#bye"), [sent, pg.inner_text("#said2")])
        pg = new()
        pg.goto(url + "/pro/leave?t=" + tok)
        reply["v"] = (403, {"left": False})
        pg.click("#bye")
        pg.wait_for_function("() => /valid/.test(document.getElementById('said2').innerText)")
        ok("leave with a link troid didn't make: says so", pg.inner_text("#said2").startswith("This leave link isn't valid."), pg.inner_text("#said2"))
        pg = new()
        pg.goto(url + "/pro/leave")
        ok("/pro/leave with no token: no button, says the link isn't valid", not pg.is_visible("#bye") and pg.inner_text("#said2").startswith("This leave link isn't valid."))

        for w in (375, 390):
            pg = new(w)
            pg.goto(url + "/pro")
            over = pg.evaluate("() => document.documentElement.scrollWidth - document.documentElement.clientWidth")
            ok(f"nothing wider than a {w} px phone", over <= 0, over)
        b.close()
    srv.shutdown()
    shutil.rmtree(d, ignore_errors=True)
    print(f"\n{n - len(fails)} of {n} checks passed" + (f"; FAILED: {fails}" if fails else ""))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
