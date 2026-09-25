#!/usr/bin/env python3
"""The desk's glossary (glossary v2 handoff; web/public/pop.js, backtest/regions.glossary_html), in Chromium against
web/public served locally. Spends nothing, calls no one.

  python web/test_glossary_page.py

- Every field label is its own trigger: a button inside the field's label, dotted, reachable by Tab, its note linked by
  aria-describedby and role="tooltip", so a screen reader announces it. No "?" icons are left.
- A note reads in order: what it is, also called (in English, marked so), example, formula.
- Desktop: hover shows it after 300 ms, keyboard focus at once; Esc closes it and keeps focus on the label.
- Phone: a tap opens it inside the window, a tap outside closes it.
- The readout's figures open notes whose "Now" line uses the desk's own numbers, and follows the inputs.
"""
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backtest"))
from i18n_equiv import PUB, serve  # noqa: E402
import regions  # noqa: E402

EN = json.loads((Path(__file__).resolve().parent / "i18n" / "en.json").read_text())
fails, n = [], 0


def ok(name, cond, info=""):
    global n
    n += 1
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else f"  {str(info)[:400]}"))
    if not cond:
        fails.append(name)


def main():
    srv, url = serve(PUB)
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")

        def page(w=1280, **kw):
            ctx = b.new_context(viewport={"width": w, "height": 900}, **kw)
            ctx.route("**/*", lambda r: r.continue_() if r.request.url.startswith("http://127.0.0.1") else r.abort())
            pg = ctx.new_page()
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto(url + "/", wait_until="load")
            pg.wait_for_timeout(300)
            return ctx, pg, errs

        ctx, pg, errs = page()
        fields = pg.evaluate("""()=>[...document.querySelectorAll('#desk .grid label')].map(l=>{const b=l.querySelector('.term'),
          n=b&&document.getElementById(b.dataset.tip);return {tid:b&&b.dataset.tip,for:l.htmlFor,input:!!document.getElementById(l.htmlFor),
          desc:b&&b.getAttribute('aria-describedby'),role:n&&n.getAttribute('role'),dotted:b&&getComputedStyle(b).borderBottomStyle}})""")
        want = [f"g-{t}" for t in regions.GLOSS_FIELDS]
        ok("every field label is a term for its own field: its note exists, is a tooltip and describes the label",
           [f["tid"] for f in fields] == want and all(f["input"] and f["desc"] == f["tid"] and f["role"] == "tooltip" and f["dotted"] == "dotted"
                                                     for f in fields), fields)
        ok("no '?' icons left on the desk", pg.evaluate("document.querySelectorAll('#desk .qm').length") == 0)
        ok("one line above the desk says how", pg.inner_text("#desk .ghint") == EN["glossary.hint"])
        order = pg.evaluate("""()=>[...document.querySelectorAll('.pop.gl')].map(p=>({id:p.id,k:[...p.querySelectorAll('.gk')].map(k=>k.textContent),
          code:!!p.querySelector('code'),first:p.firstElementChild.querySelector('.gk')===null,
          also:(p.querySelector('[lang="en"]')||{}).outerHTML||''}))""")
        rank = {EN["glossary.also_label"]: 1, EN["glossary.ex_label"]: 2, EN["glossary.now_label"]: 2}
        bad = [o["id"] for o in order if not o["first"] or [rank[k] for k in o["k"]] != sorted(rank[k] for k in o["k"])]
        ok("every note reads: what it is, then also called, then the example, then the formula", not bad, bad)
        ok("'also called' is English and marked so in every note that has one",
           all('translate="no"' in o["also"] for o in order if EN["glossary.also_label"] in o["k"]), [o["id"] for o in order])
        ok("every readout figure's note is on the page", all(any(o["id"] == f"g-{t}" for o in order) for t in regions.GLOSS_READOUT))

        # keyboard: Tab reaches every label; focus shows the note at once; Esc closes it, focus stays
        seen = []
        pg.focus("#firm")
        pg.evaluate("document.activeElement.blur()")
        pg.keyboard.press("Tab")
        for _ in range(80):
            d = pg.evaluate("document.activeElement&&document.activeElement.dataset.tip||''")
            if d and d not in seen:
                seen.append(d)
            pg.keyboard.press("Tab")
        visible = [f"g-{t}" for t in regions.GLOSS_FIELDS if t not in ("hirollover", "hwm")]      # shown per product
        ok("Tab reaches every visible field label", all(t in seen for t in visible), [t for t in visible if t not in seen])
        pg.focus('#desk .term[data-tip="g-quota"]')
        pg.keyboard.press("Shift+Tab")
        pg.keyboard.press("Tab")
        ok("keyboard focus shows the note at once", pg.is_visible("#g-quota"))
        pg.keyboard.press("Escape")
        ok("Esc closes it and focus stays on the label", not pg.is_visible("#g-quota")
           and pg.evaluate("document.activeElement.dataset.tip") == "g-quota")

        # hover: after 300 ms, not before
        pg.hover('#desk .term[data-tip="g-target_r"]')
        pg.wait_for_timeout(120)
        early = pg.is_visible("#g-target_r")
        pg.wait_for_timeout(350)
        ok("hover shows the note after 300 ms, not at once", not early and pg.is_visible("#g-target_r"))
        ok("the Target R note's example is the desk's own arithmetic", "77,872 + 2 × 3,058 = 83,988" in pg.inner_text("#g-target_r"))
        pg.mouse.move(5, 5)
        pg.wait_for_timeout(100)

        # the readout: the size note's Now line uses this result's numbers and follows an input
        pg.click('#result .term[data-tip="g-size"]')
        now = pg.inner_text("#gx-size")
        ok("size's Now line: this result's risk, stop distance, fee per unit, size and notional",
           now == "$500.00 ÷ (3,058 + 62.2976) = 0.160241; 0.160241 × 77,872 = $12,478.30." and pg.is_visible("#g-size"), now)
        pg.click("body", position={"x": 5, "y": 5})
        ok("a click outside closes it", not pg.is_visible("#g-size"))
        pg.fill("#riskPct", "0.25")
        pg.dispatch_event("#riskPct", "input")
        ok("the Now line follows the inputs", pg.inner_text("#gx-risk") == "the smaller of $250.00 and $1,400.00: $250.00.", pg.inner_text("#gx-risk"))
        pg.click('#result .term[data-tip="g-room"]')
        pg.fill("#equity", "99000")
        pg.dispatch_event("#equity", "input")
        ok("a note whose figure the desk re-renders closes instead of pointing at nothing", not pg.is_visible("#g-room"))
        ok("room's Now line: equity − floor", pg.inner_text("#gx-room") == "$99,000.00 equity − $96,000.00 floor = $3,000.00.", pg.inner_text("#gx-room"))
        ok("no script errors", not errs, errs)
        ctx.close()

        # phone: a tap opens the note inside the window, a tap outside closes it
        ctx, pg, errs = page(w=288, is_mobile=True, has_touch=True, device_scale_factor=2)
        for tid in ("equity", "leverage", "mode"):
            pg.tap(f'#desk .term[data-tip="g-{tid}"]')
            pg.wait_for_timeout(80)
            r = pg.evaluate(f"()=>{{const e=document.getElementById('g-{tid}').getBoundingClientRect();return [e.left,e.right,document.documentElement.clientWidth]}}")
            ok(f"phone: a tap opens {tid}'s note, inside the window", pg.is_visible(f"#g-{tid}") and r[0] >= 0 and r[1] <= r[2], r)
            pg.tap("h1")
            pg.wait_for_timeout(50)
            ok(f"phone: a tap outside closes {tid}'s note", not pg.is_visible(f"#g-{tid}"))
        ok("phone: tapping a label doesn't focus its field (no keyboard pops up)", pg.evaluate("document.activeElement.tagName") != "INPUT")
        ok("phone: no script errors", not errs, errs)
        ctx.close()
        b.close()
    srv.shutdown()
    print(f"RESULT: {len(fails)} failed ({n} checks)")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
