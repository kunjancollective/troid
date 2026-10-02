#!/usr/bin/env python3
"""The affiliate line by the desk (the owner, 2026-10-01), in Chromium against web/public served locally.

One element (#affl, regions.desk_aff_html), never inside the verdict, readout or working: on a phone directly under
the result, above the "Calculators audited" line; from 1100 px under the Your risk card, in the left column beside the
result; the same element moved by CSS. Only the selected firm's line shows, and only for a firm whose link is live:
the sentence, "<firm> challenges ↗ · affiliate link", "· code X" where the firm has one, "· how troid is funded" (the
FAQ's answer). It reads the same in every state (empty, OK, REDUCE, BLOCK, pending) and changes only with the firm
selector. rel="sponsored noopener", a new tab, nothing tracked. The link and its label are a size up from the desk's
small text (11px -> 11.5px), and the firms panel's and the compare's links a size up from theirs (10.5px -> 11px,
11.5px -> 12px). At 390 px nothing runs off sideways and the link is no mis-tap beside an input.

    python web/test_desk_aff.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backtest"))
from i18n_equiv import PUB, serve  # noqa: E402
from tv_stub import route_tv  # noqa: E402
from gen_compare import FIRMS, ORDER, link_live  # noqa: E402
from claim_check import RETIRED_SELLING  # noqa: E402

EN = json.loads((ROOT / "web" / "i18n" / "en.json").read_text())
WHY = EN["desk2.aff.why"]
fails = 0


def ok(name, cond, info=""):
    global fails
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else f"\n     {info}"))
    if not cond:
        fails += 1


def code_of(f):
    return f.get("affiliate_code") or (f.get("affiliate_agreement") or {}).get("customer_code")


def want_line(k):
    f = FIRMS[k]
    bits = [f"{f['name']} challenges ↗", "affiliate link"] + ([f"code {code_of(f)}"] if code_of(f) else []) + ["how troid is funded"]
    return " · ".join(bits)


READ = """()=>{const a=document.getElementById('affl'),res=document.getElementById('result'),g=document.getElementById('gauge');
  const vis=e=>!!e&&!e.hidden&&getComputedStyle(e).display!=='none'&&e.getClientRects().length>0;
  const shown=a?[...a.querySelectorAll('[data-aff]')].filter(vis):[];
  return {n:document.querySelectorAll('#affl').length,vis:vis(a),text:a&&vis(a)?a.innerText.trim().replace(/\\n+/g,'\\n'):'',
    shown:shown.map(d=>d.dataset.aff),state:(g.className.match(/\\bs([A-Z]+)\\b/)||[])[1]||'',
    inside:!!(a&&(res.contains(a)||a.closest('#result,.work,.readout,.verdict'))),
    sw:document.scrollingElement.scrollWidth,iw:innerWidth}}"""

RECTS = """()=>{const r=id=>{const e=document.getElementById(id);if(!e||e.hidden)return null;const b=e.getBoundingClientRect();
    return {l:b.left,r:b.right,t:b.top+scrollY,b:b.bottom+scrollY,w:b.width}};
  return {affl:r('affl'),result:r('result'),audit:r('audit'),rules:r('rulesread'),risk:r('st-risk'),din:document.querySelector('.d2in').getBoundingClientRect().left}}"""

# the link's tap box (its padding included) against every form control: none closer than 8 px
TAP = """()=>{const a=document.querySelector('#affl [data-aff]:not([hidden]) a[rel~=sponsored]');if(!a)return null;
  const A=a.getBoundingClientRect(),near=[];
  for(const c of document.querySelectorAll('#desk input,#desk select,#desk summary,#desk button')){const C=c.getBoundingClientRect();
    if(!C.width||!C.height)continue;const dx=Math.max(0,C.left-A.right,A.left-C.right),dy=Math.max(0,C.top-A.bottom,A.top-C.bottom);
    if(Math.max(dx,dy)<8)near.push(c.id||c.tagName)}
  return {h:A.height,near}}"""


def set_inputs(pg, **kw):
    # set as the desk's own links set them (a value, then its input event): a phone's folded step cards hold no focus
    pg.evaluate("""kw=>{for(const [k,v] of Object.entries(kw)){const e=document.getElementById(k);e.value=String(v);
      e.dispatchEvent(new Event('input',{bubbles:true}))}}""", kw)
    pg.wait_for_timeout(60)


def main():
    srv, url = serve(PUB)
    live = [k for k in ORDER if link_live(FIRMS[k])]
    raw = (PUB / "index.html").read_text()

    # the page as built, before its script
    ok("one #affl in the page", raw.count('id="affl"') == 1)
    ok("a line for each firm whose link is live, and none for the rest",
       all(f'data-aff="{k}"' in raw for k in live) and all(f'data-aff="{k}"' not in raw for k in ORDER if k not in live), live)
    seg = raw[raw.index('id="affl"'):raw.index("</div>\n", raw.index('data-aff="' + live[-1] + '"')) + 6] if live else ""
    ok("each link is rel=\"sponsored noopener\" and opens a new tab",
       seg.count('rel="sponsored noopener" target="_blank"') == len(live), seg[:400])
    ok("nothing tracked: no query string added to a firm's link, no ping, no onclick",
       all(f'href="{FIRMS[k]["affiliate_url"]}"' in seg for k in live) and " ping=" not in seg and "onclick" not in seg)
    ok("the sentence is the owner's, word for word", WHY == "troid is free. If the desk earned its place, a challenge "
       "bought through troid's link keeps it that way, and doesn't raise the price." and WHY in seg)
    for k in live:
        req = (FIRMS[k].get("required_disclaimer") or "").strip()
        if req:
            blk = seg[seg.index(f'data-aff="{k}"'):]
            blk = blk[:blk.index("</div>")]
            ok(f"{FIRMS[k]['name']}: its required wording sits under its link in the line", req in blk and blk.index(req) > blk.index("affiliate link"))
    hit = RETIRED_SELLING.search(seg)
    ok("RETIRED_SELLING finds nothing in the line, every firm's included", hit is None, hit and hit.group(0))
    ok("'how troid is funded' links the FAQ's answer", '<a href="/faq#money">how troid is funded</a>' in seg
       and '<div class="q" id="money">' in (PUB / "faq.html").read_text())
    ok("the line is outside the desk's output column: the grid's last child, after .d2out",
       raw.index('id="affl"') > raw.index('id="rulesread"'))

    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")

        def page(w, h=900, **kw):
            ctx = b.new_context(viewport={"width": w, "height": h}, timezone_id="UTC", locale="en-US", **kw)

            def handler(r):
                u = r.request.url.split("?")[0]
                if u.endswith(("/status.json", "/calendar.json", "/audit.json")) or "/api/ticker" in u:
                    if u.endswith("/audit.json"):
                        return r.fulfill(status=200, content_type="application/json", body=(PUB / "audit.json").read_text())
                    return r.fulfill(status=404, body="")
                return r.continue_() if u.startswith("http://127.0.0.1") else r.abort()
            ctx.route("**/*", handler)
            route_tv(ctx, "ok")
            pg = ctx.new_page()
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto(url + "/", wait_until="load")
            pg.wait_for_timeout(400)
            return ctx, pg, errs

        # every state, every firm, at a desktop width: the line is the selected firm's and the same in each state
        ctx, pg, errs = page(1280)
        firms = pg.eval_on_selector_all("#firm option", "o=>o.map(x=>x.value)")
        STATES = {"empty": {"entry": "", "stop": ""},
                  "OK": {"entry": 60000, "stop": 59400, "riskPct": 0.5, "lev": 5, "quota": 100000, "equity": 100000, "daystart": 100000},
                  "REDUCE": {"entry": 60000, "stop": 59990, "riskPct": 0.5, "lev": 5, "quota": 100000, "equity": 100000, "daystart": 100000},
                  "BLOCK": {"entry": 60000, "stop": 60000}}
        seen = set()
        for fk in firms:
            pg.select_option("#firm", fk)
            pg.dispatch_event("#firm", "change")
            pg.wait_for_timeout(60)
            texts = {}
            for name, kw in STATES.items():
                set_inputs(pg, **{k: v for k, v in kw.items()})
                s = pg.evaluate(READ)
                texts[name] = s["text"]
                seen.add(s["state"])
                ok(f"{fk} · {name} (gauge s{s['state']}): one element, outside the verdict, readout and working",
                   s["n"] == 1 and not s["inside"], s)
            # pending: each of the firm's products, at OK inputs, where the desk reads one as pending
            prods = pg.eval_on_selector_all("#profile option", "o=>o.map(x=>x.value)")
            set_inputs(pg, **STATES["OK"])
            for pk in prods:
                pg.select_option("#profile", pk)
                pg.dispatch_event("#profile", "change")
                pg.wait_for_timeout(60)
                s = pg.evaluate(READ)
                seen.add(s["state"])
                texts[f"{pk} ({s['state']})"] = s["text"]
            pg.select_option("#profile", prods[0])
            pg.dispatch_event("#profile", "change")
            set_inputs(pg, **STATES["OK"])
            # pending: a product with neither limit recorded (none today; the desk's PENDING path, set up in the page)
            pg.evaluate("""()=>{const p=FIRMS[document.getElementById('firm').value].products[document.getElementById('profile').value];
              window.__dm=[p.d,p.m,p.basis,p.dd];p.d=p.m=p.basis=p.dd=null;render()}""")
            pg.wait_for_timeout(60)
            s = pg.evaluate(READ)
            seen.add(s["state"])
            texts[f"pending ({s['state']})"] = s["text"]
            ok(f"{fk} · pending (gauge s{s['state']}): one element, outside the verdict, readout and working",
               s["n"] == 1 and not s["inside"] and s["state"] == "PENDING", s)
            pg.evaluate("""()=>{const p=FIRMS[document.getElementById('firm').value].products[document.getElementById('profile').value];
              [p.d,p.m,p.basis,p.dd]=window.__dm;render()}""")
            pg.select_option("#profile", prods[0])
            pg.dispatch_event("#profile", "change")
            if fk in live:
                want = WHY + "\n" + want_line(fk)
                req = (FIRMS[fk].get("required_disclaimer") or "").strip()
                if req:
                    want += "\n" + req
                ok(f"{fk}: the line in every state and product is its own, identical: {want_line(fk)}",
                   set(texts.values()) == {want}, texts)
            else:
                ok(f"{fk}: no live link, so no line in any state", set(texts.values()) == {""}, texts)
        ok("the states seen include OK, REDUCE, BLOCK and an empty desk", {"OK", "REDUCE", "BLOCK"} <= seen and ({"EMPTY", "SET"} & seen), seen)
        ok("a pending state is among them", "PENDING" in seen, seen)

        # a firm with no live link: the whole element hides
        pg.evaluate("()=>{const d=document.querySelector('#affl [data-aff]');window.__k=d.dataset.aff;d.setAttribute('data-aff','none')}")
        k0 = pg.evaluate("()=>window.__k")
        pg.select_option("#firm", k0)
        pg.dispatch_event("#firm", "change")
        pg.wait_for_timeout(60)
        ok("a firm without a live link shows no line at all (the sentence hides with it)", not pg.evaluate(READ)["vis"])
        ok("no page error", not errs, errs)
        ctx.close()

        # where it sits: from 1100 px, under the Your risk card in the left column, beside the result
        ctx, pg, errs = page(1280)
        set_inputs(pg, **STATES["OK"])
        r = pg.evaluate(RECTS)
        ok("1280 px: under the Your risk card", r["affl"]["t"] >= r["risk"]["b"] - 1 and r["affl"]["t"] - r["risk"]["b"] < 40, r)
        ok("1280 px: in the left column, beside the result", abs(r["affl"]["l"] - r["din"]) < 1 and r["affl"]["r"] <= r["result"]["l"], r)
        size = pg.evaluate("()=>{const g=s=>getComputedStyle(document.querySelector(s)).fontSize;"
                           "return {al:g('#affl [data-aff]:not([hidden]) .al'),a:g('#affl [data-aff]:not([hidden]) .al a'),"
                           "aw:g('#affl .aw'),audit:g('#rulesread'),panel:g('.cell .s.aff')}}")
        ok("the link and 'affiliate link' are 11.5px, a size up from the desk's 11px small text, and the same as each other",
           size["al"] == size["a"] == "11.5px" and size["audit"] == size["aw"] == "11px", size)
        ok("the firms panel's affiliate links: 11px, a size up from 10.5px", size["panel"] == "11px", size)
        ctx.close()

        ctx, pg, errs = page(1280)
        pg.goto(url + "/compare", wait_until="load")
        pg.wait_for_timeout(300)
        cf = pg.evaluate("()=>[...document.querySelectorAll('.colfoot a[rel~=sponsored]')].map(a=>getComputedStyle(a).fontSize)")
        ok("the compare's affiliate links: 12px, a size up from 11.5px", cf and set(cf) == {"12px"}, cf)
        ctx.close()

        # a phone: directly under the result, above "Calculators audited"; nothing sideways; no mis-tap
        for w in (390, 375):
            ctx, pg, errs = page(w, 844, device_scale_factor=3, is_mobile=True, has_touch=True)
            for name in ("empty", "OK"):
                set_inputs(pg, **STATES[name])
                r = pg.evaluate(RECTS)
                ok(f"{w} px · {name}: directly under the result, above the audit line",
                   r["result"]["b"] - 1 <= r["affl"]["t"] and r["affl"]["b"] <= r["audit"]["t"] + 1 and r["audit"]["t"] - r["affl"]["b"] < 30
                   and r["affl"]["t"] - r["result"]["b"] < 30, r)
                s = pg.evaluate(READ)
                ok(f"{w} px · {name}: no sideways scroll", s["sw"] <= s["iw"], s)
            t = pg.evaluate(TAP)
            ok(f"{w} px: the link is at least 24 px tall and no input, select or button within 8 px of it",
               t and t["h"] >= 24 and not t["near"], t)
            ctx.close()
        b.close()
    srv.shutdown()
    print(f"\n{'all passed' if not fails else f'{fails} failed'}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
