#!/usr/bin/env python3
"""ask troid's page (web/public/chat.html) at the launch caps (launch handoff 2026-09-26, 5.4), in Chromium against
web/public served locally; /api/troid is answered by the test. Spends nothing, calls no one.

  python web/test_chat_page.py

- On: the disclosure shows, the box opens.
- Resting when the page opens (GET says resting): the service's message, "ask troid is resting until 00:00 UTC; the FAQ
  and sources are open.", with links to the FAQ and the sources; no disclosure; the box closed.
- Resting on a send (POST answers 429 resting): the message in the conversation and in the status line, the links, the
  box closed, and what the visitor typed back in the box.
- Busy (503) is not resting: the box stays open.
"""
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backtest"))
from i18n_equiv import PUB, serve  # noqa: E402

RESTING = "ask troid is resting until 00:00 UTC; the FAQ and sources are open."
DISCLOSURE = "This is ask troid, an automated assistant."
fails, n = [], 0


def ok(name, cond, info=""):
    global n
    n += 1
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else f"  {str(info)[:400]}"))
    if not cond:
        fails.append(name)


def state(pg):
    return pg.evaluate("""() => ({status: document.getElementById('status').innerText,
      links: [...document.querySelectorAll('#status a')].map(a => a.getAttribute('href')),
      q: document.getElementById('q').value, qOff: document.getElementById('q').disabled, sendOff: document.getElementById('send').disabled,
      chat: document.getElementById('chat').innerText})""")


def main():
    srv, url = serve(PUB)
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")

        def page(get, post=None):
            ctx = b.new_context()

            def handler(r):
                u = r.request.url
                if not u.startswith(url):
                    return r.abort()
                if "/api/troid" in u:
                    if r.request.method == "GET":
                        return r.fulfill(status=200, body=json.dumps(get), content_type="application/json")
                    st, body = post
                    return r.fulfill(status=st, body=json.dumps(body), content_type="application/json")
                if "/api/" in u:
                    return r.fulfill(status=404, body="{}", content_type="application/json")
                return r.continue_()
            ctx.route("**/*", handler)
            pg = ctx.new_page()
            pg.goto(url + "/chat")
            pg.wait_for_function("() => !/checking/i.test(document.getElementById('status').innerText)")
            return pg

        on = {"enabled": True, "disclosure": DISCLOSURE, "limit_per_hour": 20, "max_messages": 20, "max_chars": 2000,
              "context": {"firms": ["a", "b", "c"]}, "resting": False}
        pg = page(on)
        s = state(pg)
        ok("on: the disclosure shows and the box opens", DISCLOSURE in s["chat"] and not s["qOff"] and not s["sendOff"], s)

        pg = page(dict(on, resting=True, resting_text=RESTING))
        s = state(pg)
        ok("resting when the page opens: the service's words in the status line", s["status"].startswith(RESTING), s)
        ok("resting when the page opens: links to the FAQ and the sources", s["links"] == ["/faq", "/sources"], s["links"])
        ok("resting when the page opens: no disclosure, the box closed", DISCLOSURE not in s["chat"] and s["qOff"] and s["sendOff"], s)

        pg = page(on, (429, {"resting": True, "error": RESTING}))
        pg.fill("#q", "What is the crossover?")
        pg.click("#send")
        pg.wait_for_function("() => document.getElementById('q').disabled")
        s = state(pg)
        ok("resting on a send: the message in the conversation and the status line", RESTING in s["chat"] and s["status"].startswith(RESTING), s)
        ok("resting on a send: links to the FAQ and the sources, the box closed", s["links"] == ["/faq", "/sources"] and s["qOff"] and s["sendOff"], s)
        ok("resting on a send: what the visitor typed is back in the box", s["q"] == "What is the crossover?", s["q"])

        pg = page(on, (503, {"enabled": True, "error": "ask troid is busy. Try again in a minute."}))
        pg.fill("#q", "hi")
        pg.click("#send")
        pg.wait_for_function("() => /busy/.test(document.getElementById('chat').innerText)")
        pg.wait_for_timeout(100)
        s = state(pg)
        ok("busy is not resting: the box stays open, no links", not s["qOff"] and not s["sendOff"] and not s["links"], s)
        b.close()
    srv.shutdown()
    print(f"\n{n - len(fails)} of {n} checks passed" + (f"; FAILED: {fails}" if fails else ""))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
