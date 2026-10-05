#!/usr/bin/env python3
"""Where troid's affiliate links show (geo.json, backtest/geo.py, web/public/geo.js, web/api/where.js; launch handoff
5.3, the owner's decision, 2026-10-03), in Chromium against web/public served locally, /api/where stubbed.

  1. geo.json: firm_terms is firms.json's availability.excluded (BrightFunded CU IR KP SY VN; Bitfunded and Crypto
     Fund Trader none), the embargo list CU IR KP SY and the law list CN BD FR AE IN ID EG for every firm; a
     not_from_terms entry (BrightFunded's PK) and a platform-only exclusion (MT5 for US residents) hide nothing.
  2. Each list, on the desk's line, the landing panel and the compare: a link shows where its firm's country list
     doesn't hold the visitor's country, and "This firm's link isn't shown in your region." (linking the FAQ) where it
     does. The compare's columns, redrawn by its script, stay covered.
  3. Fail closed: no country, an error, a malformed answer, no answer within the timeout: every message, no link.
     Before the answer: neither.
  4. No computed figure changes by country: every desk state in a grid, and the compare at several inputs, read the
     same in every country once the links and messages are set aside.
  5. Every affiliate link on every built page sits inside its firm's [data-geo]; the FAQ's answer and /sources#geo.
  6. The desk's link and its "affiliate link" label are 13px.

    python web/test_geo.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backtest"))
from i18n_equiv import PUB, serve  # noqa: E402
from tv_stub import route_tv  # noqa: E402
import geo  # noqa: E402

FIRMS = json.loads((ROOT / "firms.json").read_text())
G = json.loads((ROOT / "geo.json").read_text())
EN = json.loads((ROOT / "web" / "i18n" / "en.json").read_text())
LIVE = [k for k in G["lists"]["firm_terms"]["firms"]]
fails = 0


def ok(name, cond, info=""):
    global fails
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else f"\n     {str(info)[:600]}"))
    if not cond:
        fails += 1


# what each element shows, by its own computed style (a desk line for an unselected firm is hidden by its parent;
# its own rule still says whether the country allows it)
STATE = """()=>{const o={};document.querySelectorAll('[data-geo],[data-geo-no]').forEach(e=>{
  const k=e.getAttribute('data-geo')||e.getAttribute('data-geo-no'),w=e.hasAttribute('data-geo')?'link':'msg';
  const where=e.closest('#affl')?'desk':e.closest('.colfoot')?'compare':e.closest('.cell')?'panel':'other';
  const id=where+':'+k+':'+w;(o[id]=o[id]||[]).push(getComputedStyle(e).display!=='none')});
  return {state:document.documentElement.getAttribute('data-geo-state'),o}}"""

# the page's text with the links and messages set aside, and every figure the desk or compare shows
TEXT = """()=>{const c=document.body.cloneNode(true);c.querySelectorAll('[data-geo],[data-geo-no],.tk,.cal,script,style').forEach(e=>e.remove());
  return c.innerText.replace(/\\s+/g,' ')}"""


def main():
    # 1. the lists
    ft = G["lists"]["firm_terms"]["firms"]
    ok("geo.check(): firm_terms is firms.json's availability.excluded, codes named, law entries complete", geo.check())
    ok("firm_terms: BrightFunded CU IR KP SY VN; Bitfunded none; Crypto Fund Trader none",
       ft == {"bitfunded": [], "brightfunded": ["CU", "IR", "KP", "SY", "VN"], "crypto_fund_trader": []}, ft)
    ok("embargo, every firm: CU IR KP SY", G["lists"]["embargo"]["countries"] == ["CU", "IR", "KP", "SY"])
    ok("law, every firm: CN BD FR AE IN ID EG", G["lists"]["law"]["countries"] == ["CN", "BD", "FR", "AE", "IN", "ID", "EG"])
    nft = {c for k in LIVE for c in (FIRMS[k]["availability"].get("not_from_terms") or {})}
    plat = {c for k in LIVE for v in (FIRMS[k]["availability"].get("platform") or {}).values() for c in v}
    ok(f"not_from_terms ({sorted(nft)}) and platform-only ({sorted(plat)}) entries are in no firm's own-terms list",
       not any(c in ft[k] for k in LIVE for c in (nft | plat) if c not in (FIRMS[k]["availability"].get("excluded") or [])))
    ok("PK (BrightFunded, not_from_terms) and US (MT5 only) hide no firm's link",
       all("PK" not in geo.hidden(k) and "US" not in geo.hidden(k) for k in LIVE))
    # the countries to visit and what each should show, firm by firm
    cases = {"US": set(), "PK": set(), "DE": set(), "VN": {"brightfunded"}}
    for c in G["lists"]["embargo"]["countries"] + G["lists"]["law"]["countries"]:
        cases[c] = set(LIVE)
    for k, cc in ft.items():
        for c in cc:
            cases.setdefault(c, set()).add(k)
    srv, url = serve(PUB)
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")

        def page(path, where, w=1280):
            """where: a country code, or 'error' / 'null' / 'junk' / 'hang' / 'hold' (answered later by the caller)."""
            ctx = b.new_context(viewport={"width": w, "height": 900}, timezone_id="UTC", locale="en-US")
            held = []

            def handler(r):
                u = r.request.url.split("?")[0]
                if u.endswith("/api/where"):
                    if where == "error":
                        return r.fulfill(status=500, body="")
                    if where == "null":
                        return r.fulfill(status=200, content_type="application/json", body='{"country":null}')
                    if where == "junk":
                        return r.fulfill(status=200, content_type="application/json", body="<html>")
                    if where in ("hang", "hold"):
                        held.append(r)
                        return None
                    return r.fulfill(status=200, content_type="application/json", body=json.dumps({"country": where}))
                if u.endswith("/audit.json"):
                    return r.fulfill(status=200, content_type="application/json", body=(PUB / "audit.json").read_text())
                if u.endswith(("/status.json", "/calendar.json")) or "/api/ticker" in u:
                    return r.fulfill(status=404, body="")
                return r.continue_() if u.startswith("http://127.0.0.1") else r.abort()
            ctx.route("**/*", handler)
            route_tv(ctx, "ok")
            pg = ctx.new_page()
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto(url + path, wait_until="load")
            if where not in ("hang", "hold"):
                pg.wait_for_function("document.documentElement.hasAttribute('data-geo-state')", timeout=5000)
            return ctx, pg, errs, held

        def expect(s, hidden_firms, where_):
            want = {}
            for k in LIVE:
                for w in ("desk", "panel", "compare"):
                    want[f"{w}:{k}:link"] = k not in hidden_firms
                    want[f"{w}:{k}:msg"] = k in hidden_firms
            got = {i: all(v) if all(v) == any(v) else None for i, v in s["o"].items()}
            return {i: (got.get(i), v) for i, v in want.items() if i.split(":")[0] in where_ and got.get(i) != v}

        # 2. each list, on / (the desk's line and the landing panel) and /compare
        for c, hid in sorted(cases.items()):
            for path, where_ in (("/", ("desk", "panel")), ("/compare", ("compare",))):
                ctx, pg, errs, _ = page(path, c)
                s = pg.evaluate(STATE)
                bad = expect(s, hid, where_)
                ok(f"{c} {path}: links hidden for {sorted(hid) or 'no firm'}, the message in their place, every other link shown",
                   s["state"] == "known" and not bad and not errs, (s["state"], bad, errs))
                ctx.close()

        # the message and its link to the FAQ's answer
        ctx, pg, errs, _ = page("/", "FR")
        m = pg.evaluate("()=>{const e=[...document.querySelectorAll('#affl [data-geo-no]')].find(x=>getComputedStyle(x).display!=='none'&&x.offsetParent);"
                        "return e?{t:e.innerText.trim(),h:e.querySelector('a').getAttribute('href')}:null}")
        ok("the message reads \"This firm's link isn't shown in your region.\" and links /faq#regions",
           m and m["t"].startswith("This firm's link isn't shown in your region.") and m["h"] == "/faq#regions", m)
        ctx.close()

        # the compare's script redraws its columns on every input: still covered
        for c, hid in (("US", set()), ("VN", {"brightfunded"}), ("FR", set(LIVE))):
            ctx, pg, errs, _ = page("/compare", c)
            pg.fill("#quota", "50000")
            pg.dispatch_event("#quota", "input")
            pg.wait_for_timeout(100)
            bad = expect(pg.evaluate(STATE), hid, ("compare",))
            ok(f"{c} /compare after its script redraws the columns: still {sorted(hid) or 'no firm'} hidden", not bad, bad)
            ctx.close()

        # 3. fail closed
        for how in ("error", "null", "junk", "hang"):
            ctx, pg, errs, held = page("/", how)
            if how == "hang":
                pg.wait_for_timeout(geo.TIMEOUT_MS + 600)
            s = pg.evaluate(STATE)
            bad = expect(s, set(LIVE), ("desk", "panel"))
            ok(f"/api/where {how}: every link hidden, every message shown (fail closed)", s["state"] == "closed" and not bad, (s["state"], bad))
            for h in held:
                h.abort()
            ctx.close()
            ctx, pg, errs, held = page("/compare", how)
            if how == "hang":
                pg.wait_for_timeout(geo.TIMEOUT_MS + 600)
            bad = expect(pg.evaluate(STATE), set(LIVE), ("compare",))
            ok(f"/compare, /api/where {how}: every link hidden (fail closed)", not bad, bad)
            for h in held:
                h.abort()
            ctx.close()
        ctx, pg, errs, held = page("/", "hold")
        pg.wait_for_timeout(300)
        s = pg.evaluate(STATE)
        ok("before /api/where answers: no link and no message", s["state"] is None and not any(any(v) for v in s["o"].values()), s)
        held[0].fulfill(status=200, content_type="application/json", body='{"country":"US"}') if held else None
        pg.wait_for_function("document.documentElement.getAttribute('data-geo-state')==='known'", timeout=3000)
        ok("…and once it answers US, every link", not expect(pg.evaluate(STATE), set(), ("desk", "panel")))
        ctx.close()

        # a page without script: the head's rule alone, so no link and no message (closed)
        ctx = b.new_context(java_script_enabled=False)
        pg = ctx.new_page()
        for path in ("/", "/compare"):
            pg.goto(url + path)
            d = pg.evaluate("()=>[...document.querySelectorAll('[data-geo],[data-geo-no]')].map(e=>getComputedStyle(e).display)")
            ok(f"{path} without script: {len(d)} links and messages, none shown", d and set(d) == {"none"}, d)
        ctx.close()

        # 4. no computed figure changes by country: the desk across a grid, the compare at several inputs
        firms = None
        countries = ["US", "FR", "VN", "CU", "IN", "error"]
        grid = [{"entry": "", "stop": ""}, {"entry": 60000, "stop": 59400}, {"entry": 60000, "stop": 59990},
                {"entry": 60000, "stop": 60600, "side": "-1"}, {"entry": 60000, "stop": 60000}, {"entry": 3000, "stop": 2950, "riskPct": 2, "lev": 50}]
        texts = {}
        for c in countries:
            ctx, pg, errs, _ = page("/", c)
            firms = pg.eval_on_selector_all("#firm option", "o=>o.map(x=>x.value)")
            out = []
            for fk in firms:
                pg.select_option("#firm", fk)
                pg.dispatch_event("#firm", "change")
                for prof in pg.eval_on_selector_all("#profile option", "o=>o.map(x=>x.value)"):
                    pg.select_option("#profile", prof)
                    pg.dispatch_event("#profile", "change")
                    for g in grid:
                        pg.evaluate("""g=>{for(const [k,v] of Object.entries(g)){const e=document.getElementById(k);e.value=String(v);
                          e.dispatchEvent(new Event(e.tagName==='SELECT'?'change':'input',{bubbles:true}))}}""", g)
                        out.append(pg.evaluate("()=>[document.getElementById('result').innerText,document.getElementById('gauge').getAttribute('aria-label'),"
                                               "document.getElementById('xs').innerText,document.querySelector('.gline').textContent].join('|')"))
            out.append(pg.evaluate(TEXT))
            texts[c] = out
            ctx.close()
        base = texts["US"]
        ok(f"the desk: {len(base) - 1} states (every firm and product, {len(grid)} inputs each) read the same in "
           f"{', '.join(countries)}, the page's text too, links and messages aside",
           all(texts[c] == base for c in countries), {c: next((i for i, (a, x) in enumerate(zip(texts[c], base)) if a != x), None) for c in countries})
        ctexts = {}
        for c in countries:
            ctx, pg, errs, _ = page("/compare", c)
            out = []
            for q, r_, st, lv in ((100000, 0.5, 1.66, 5), (50000, 1, 0.8, 2), (200000, 0.25, 3, 10)):
                for k_, v in (("quota", q), ("risk", r_), ("stop", st), ("lev", lv)):
                    pg.fill("#" + k_, str(v))
                    pg.dispatch_event("#" + k_, "input")
                out.append(pg.evaluate(TEXT))
            ctexts[c] = out
            ctx.close()
        ok(f"the compare at three sets of inputs reads the same in {', '.join(countries)}, links and messages aside",
           all(ctexts[c] == ctexts["US"] for c in countries))

        # 5. every affiliate link on every built page is inside its firm's [data-geo]
        urls = {k: FIRMS[k]["affiliate_url"] for k in LIVE if FIRMS[k].get("affiliate_url")}
        pages = sorted({p_.relative_to(PUB).as_posix() for p_ in PUB.rglob("*.html")})
        loose, found = [], set()
        ctx = b.new_context()
        pg = ctx.new_page()
        pg.route("**/*", lambda r: r.continue_() if r.request.url.startswith("http://127.0.0.1") else r.abort())
        for rel in pages:
            pg.goto(url + "/" + rel, wait_until="domcontentloaded")
            r_ = pg.evaluate("""m=>{const out=[];for(const a of document.querySelectorAll('a[href]'))for(const [k,u] of Object.entries(m))
              if(a.href===new URL(u,location).href){const g=a.closest('[data-geo]');out.push([k,!!g&&g.getAttribute('data-geo')===k])}return out}""", urls)
            found |= {rel for _ in r_}
            loose += [(rel, k) for k, inside in r_ if not inside]
        ctx.close()
        ok(f"every affiliate link on the {len(pages)} built pages sits inside its own firm's [data-geo] (links found on {sorted(found)})",
           not loose and {"index.html", "compare.html"} <= found, loose)

        faq = (PUB / "faq.html").read_text()
        ok("the FAQ answers why some regions don't see links, and that a VPN defeats it (#regions)",
           'id="regions"' in faq and "VPN defeats it" in faq and "good faith, not a guarantee" in faq)
        src = (PUB / "sources.html").read_text()
        codes = set(G["lists"]["embargo"]["countries"]) | set(G["lists"]["law"]["countries"]) | {c for v in ft.values() for c in v}
        ok("/sources#geo lists every country on the three lists, named, with each list's basis",
           'id="geo"' in src and all(f"({c})" in src for c in codes) and all(l["basis"] in src.replace("&#39;", "'") for l in G["lists"].values()))

        # 6. the desk's link and label at 13px
        ctx, pg, errs, _ = page("/", "US")
        sz = pg.evaluate("()=>{const l=document.querySelector('#affl [data-aff]:not([hidden]) .al');return [getComputedStyle(l).fontSize,getComputedStyle(l.querySelector('a')).fontSize]}")
        ok("the desk's link and its 'affiliate link' label: 13px", sz == ["13px", "13px"], sz)
        ctx.close()
        b.close()
    srv.shutdown()
    print(f"\n{'all passed' if not fails else f'{fails} failed'}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
