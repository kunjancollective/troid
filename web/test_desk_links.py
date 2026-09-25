#!/usr/bin/env python3
"""Shareable desk links (web/public/desklink.js), in Chromium against web/public served locally. Spends nothing.

  python web/test_desk_links.py

- Round trip: for every firm × challenge on troid's desk, set non-default inputs, press "Copy link to this result",
  open the copied link in a fresh page: every input and the whole result come back, with the shared-link notice.
- The link: the inputs are in the fragment only (no query string), and no request to the server carries them.
- Malformed fragments: bad numbers, an unknown side or margin mode, broken percent-encoding, repeated keys, markup
  in a value, a fragment over the length cap, a plain anchor. Each bad field keeps its default, nothing throws, and the
  desk still answers: a verdict, or with no entry (the desk starts with none) its first view.
- A firm or challenge troid no longer lists (rotated out) opens with a notice and a working desk, not a broken page.
- A language in the link counts only when it is live; the first edit after opening removes the notice and the fragment.
"""
import http.server
import json
import re
import socketserver
import sys
import threading
from pathlib import Path
from urllib.parse import unquote

from playwright.sync_api import sync_playwright

PUB = Path(__file__).resolve().parent / "public"
EN = json.loads((Path(__file__).resolve().parent / "i18n" / "en.json").read_text())
SEEN = []                                  # every path the server was asked for


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(PUB), **k)

    def log_message(self, *a):
        pass

    def send_head(self):
        SEEN.append(self.path)
        if self.path.split("?")[0] == "/status.json":             # the status light: not under test
            self.send_error(404)
            return None
        last = self.path.split("?")[0].rsplit("/", 1)[-1]
        if last and "." not in last:
            self.path = self.path.split("?")[0] + ".html"
        return super().send_head()


n = failed = 0


def ok(name, cond, got=None):
    global n, failed
    n += 1
    if not cond:
        failed += 1
        print("FAIL " + name + ("" if got is None else "  " + json.dumps(got, default=str)[:400]))
    else:
        print("ok   " + name)


INPUTS = ["quota", "equity", "daystart", "hirollover", "hwm", "side", "entry", "stop", "targetR", "riskPct", "capPct", "lev", "mode"]


def inputs(pg):
    return pg.evaluate("ids => Object.fromEntries(['firm','profile'].concat(ids).map(i => [i, document.getElementById(i).value]))", INPUTS)


def result(pg):
    # the result without the link row's status message (it says "Link copied" on the page that copied)
    return pg.evaluate("() => { const r = document.getElementById('result').cloneNode(true);"
                       " r.querySelectorAll('.linkmsg').forEach(m => m.textContent = ''); return r.innerHTML }")


def notice(pg):
    return pg.evaluate("() => { const s = document.getElementById('shared'); return s.hidden ? null : s.textContent }")


def answers(pg):
    """The desk answers: a verdict, or, with no entry, "Enter your entry and stop to size a trade." """
    if pg.input_value("#entry") == "":
        return pg.is_visible("#result .d2empty") and pg.inner_text("#result .d2empty") == EN["desk2.js.empty"]
    return pg.is_visible("#result .verdict")


def trade(pg):
    """A trade typed in: the desk starts with no entry and no stop, and a link is offered once a trade is sized."""
    pg.fill("#entry", "77872")
    pg.fill("#stop", "74814")


def main():
    srv = socketserver.TCPServer(("127.0.0.1", 0), Handler)
    port = srv.server_address[1]
    base = f"http://127.0.0.1:{port}"
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    shared = re.sub(r"<[^>]+>", "", EN["index.js.shared"])
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
        ctx = b.new_context(viewport={"width": 1280, "height": 900})
        ctx.grant_permissions(["clipboard-read", "clipboard-write"], origin=base)
        ctx.route("**/*", lambda r: r.abort() if not r.request.url.startswith(base) else r.continue_())
        errors = []

        def page(url):
            pg = ctx.new_page()
            pg.on("pageerror", lambda e: errors.append(f"{url}: {e}"))
            pg.on("dialog", lambda d: (errors.append(f"{url}: dialog {d.message}"), d.dismiss()))
            pg.goto(url, wait_until="load")
            return pg

        # --- round trip: every firm x challenge
        pg = page(base + "/")
        combos = pg.evaluate("() => Object.keys(FIRMS).flatMap(f => Object.keys(FIRMS[f].products).map(p => [f, p]))")
        ok(f"the desk lists firms and challenges ({len(combos)} combinations)", len(combos) >= 3, combos)
        firms = {c[0] for c in combos}
        for i, (f, prod) in enumerate(combos):
            pg.select_option("#firm", f)
            pg.select_option("#profile", prod)
            vals = {"quota": str(50000 + 1000 * i), "equity": str(49000 + 1000 * i), "daystart": str(49500 + 1000 * i),
                    "entry": "3150.5", "stop": "3099.25", "targetR": "2.5", "riskPct": "0.4", "capPct": "30", "lev": "3"}
            if pg.is_visible("#hwm"):
                vals["hwm"] = str(52000 + 1000 * i)
            if pg.is_visible("#hirollover"):
                vals["hirollover"] = str(50500 + 1000 * i)
            for k, v in vals.items():
                pg.fill("#" + k, v)
            pg.select_option("#side", "1" if i % 2 else "-1")
            pg.select_option("#mode", "isolated" if i % 3 == 0 else "cross")
            before, res = inputs(pg), result(pg)
            pg.click("[data-copy-link]")
            pg.wait_for_function("() => document.querySelector('.linkmsg').textContent.length > 0")
            link = pg.evaluate("() => navigator.clipboard.readText()")
            ok(f"{f}/{prod}: the copy says so", pg.text_content(".linkmsg") == re.sub(r"<[^>]+>", "", EN["index.js.share_copied"]),
               pg.text_content(".linkmsg"))
            ok(f"{f}/{prod}: the link is the desk plus a fragment, no query string",
               link.startswith(base + "/#f=" + f + "&p=" + prod + "&") and "?" not in link and len(link.split("#", 1)[1]) <= 400, link)
            q = page(link)
            ok(f"{f}/{prod}: every input comes back", inputs(q) == before, [inputs(q), before])
            ok(f"{f}/{prod}: the same result, recomputed", result(q) == res)
            ok(f"{f}/{prod}: the shared-link notice, alone", notice(q) == shared, notice(q))
            q.close()
        pg.close()
        leaked = [s for s in SEEN if re.search(r"[?&#](f|q|p)=", unquote(s))]
        ok("no request to the server carried the inputs", not leaked, leaked[:3])

        # --- malformed and hostile fragments: each bad field keeps its default, the page works
        pg = page(base + "/")
        defaults = inputs(pg)
        pg.close()
        cases = [
            ("bad numbers, side and mode", "#f=bitfunded&p=1step&q=abc&e=1e5&ds=--5&en=Infinity&st=0x10&r=NaN&sd=sideways&m=hybrid&lv=5",
             {"lev": "5"}, 8),
            ("broken percent-encoding", "#f=bitfunded&p=1step&q=%E0%A4%A&e=90000", {"equity": "90000"}, 1),
            ("repeated keys: the first counts", "#q=60000&q=70000", {"quota": "60000"}, 0),
            ("unknown keys ignored", "#zz=1&q=61000&__proto__=x&constructor=y", {"quota": "61000"}, 0),
            ("a plain anchor is not a desk link", "#firms", {}, None),
            ("empty values ignored", "#f=&p=&q=&e=", {}, 0),
        ]
        for name, frag, want, bad in cases:
            q = page(base + "/" + frag)
            got = inputs(q)
            exp = dict(defaults, **want)
            ok(f"malformed: {name}: the rest at defaults", got == exp, {k: (got[k], exp[k]) for k in got if got[k] != exp[k]})
            nt = notice(q)
            if bad is None:
                ok(f"malformed: {name}: no notice", nt is None, nt)
            elif bad:
                ok(f"malformed: {name}: says {bad} value(s) could not be read", nt is not None and f"({bad})" in nt, nt)
            ok(f"malformed: {name}: the desk still answers", answers(q))
            q.close()
        q = page(base + "/#" + "q=1&" * 200)
        ok("over the length cap: nothing read, and says so", inputs(q) == defaults and notice(q) == EN["index.js.shared_long"], notice(q))
        q.close()
        q = page(base + "/#f=%3Cimg%20src%3Dx%20onerror%3Dalert(1)%3E&q=52000")
        ok("markup in a firm name: not rendered, not echoed", q.evaluate("() => !document.querySelector('#shared img')")
           and "onerror" not in (notice(q) or "") and "?" in (notice(q) or ""), notice(q))
        ok("markup in a firm name: the numbers still apply", inputs(q)["quota"] == "52000")
        q.close()

        # --- rotated out: a firm, then a challenge, troid no longer lists
        q = page(base + "/#f=oldfirm&p=1step&q=55000&e=54000&ds=54000&en=100&st=98")
        first = q.evaluate("() => FIRMS[Object.keys(FIRMS)[0]].name")
        nt = notice(q) or ""
        ok("rotated-out firm: opens with a notice naming it and the firm shown", "oldfirm" in nt and first in nt and shared in nt, nt)
        ok("rotated-out firm: a working desk with the link's numbers", inputs(q)["quota"] == "55000" and q.is_visible("#result .verdict"))
        q.close()
        q = page(base + "/#f=bitfunded&p=retired_step&q=56000")
        nt = notice(q) or ""
        ok("rotated-out challenge: the firm kept, the default challenge shown, a notice naming it",
           inputs(q)["firm"] == "bitfunded" and inputs(q)["profile"] == defaults["profile"] and "retired_step" in nt, nt)
        q.close()

        # --- language: only a live one counts; English builds carry none
        q = page(base + "/")
        live = q.evaluate("() => DESKLINK.decode('#l=zz&q=1', FIRMS, ['en']).lang === null && DESKLINK.decode('#l=zh&q=1', FIRMS, ['en','zh']).lang === 'zh'")
        ok("l=<lang> counts only when that language is live", live)
        trade(q)
        q.click("[data-copy-link]")
        q.wait_for_function("() => document.querySelector('.linkmsg').textContent.length > 0")
        ok("an English page's link carries no l=", "l=" not in q.evaluate("() => navigator.clipboard.readText()").split("#", 1)[1])
        q.close()

        # --- the first edit makes the numbers the reader's: notice and fragment go
        q = page(base + "/#f=bitfunded&p=1step&q=57000")
        q.fill("#quota", "58000")
        ok("after an edit: the notice hides and the fragment is cleared", notice(q) is None and q.evaluate("() => location.hash") == "")
        q.close()

        # --- no clipboard: the link is shown to copy by hand
        q = page(base + "/")
        q.evaluate("() => { Object.defineProperty(navigator, 'clipboard', { value: undefined }) }")
        trade(q)
        q.click("[data-copy-link]")
        v = q.input_value(".linkurl")
        ok("no clipboard: the link shown, selected, to copy by hand", v.startswith(base + "/#f="), v)
        q.close()

        ok("no script errors, no dialogs", not errors, errors[:5])
        b.close()
    srv.shutdown()
    print(f"RESULT: {failed} failed ({n} checks)")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
