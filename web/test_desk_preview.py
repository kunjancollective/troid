#!/usr/bin/env python3
"""troid's next desk at /desk-preview (partials/_desk2.html, web/public/desk2.js; ticker v2 handoff, sections E and F;
design handoff 2026-09-24, section 4), in Chromium against web/public served locally. /api/ticker is answered by the
test and TradingView's script by backtest/tv_stub.py: spends nothing, calls no one.

  python web/test_desk_preview.py

- The same figures as the live desk: the 84 desk states give the same result, byte for byte, once the preview's own
  additions (the ladder and the fee bar, marked d2x) are set aside; the live desk's page is unchanged by the preview.
- The Asset field: firms.json's listed symbols, grouped; changing it changes the hold-limit line and the availability
  note only, each with its source's link and read date.
- The entry chip: a crypto asset's spot price from /api/ticker, "live … · use", "delayed" past 60 s, gone when the price
  can't be had; gold, oil and stocks point to the tape. A tap fills the entry; a stop the new entry leaves on the wrong
  side or more than 25% away is cleared and the desk says "Set your stop", never BLOCK, never a suggested stop.
- A tapped tape symbol (?tvwidgetsymbol=) selects the asset; a stock no firm lists says so; the still row's "use as
  entry" selects the asset too. The preview's tape opens the preview, the live desk's the live desk.
- The gauge draws the result to scale (the dot at equity, the floors, the drop at the stop against the room), in its
  state's colour, with every figure in its label; the ladder orders the breakers, marks one before the stop and states
  an off-scale one; the fee bar splits the risk as the readout does; the explainer uses the result's own numbers.
- Step cards: a phone opens on the trade with the account and risk folded to summaries; a card whose input stops the
  sizing says so. The gauge pins under the tape on a phone. noindex, in no sitemap, linked from nowhere.
"""
import json
import re
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backtest"))
from i18n_equiv import DESK_GRID, PUB, serve  # noqa: E402
from tv_stub import route_tv  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
EN = json.loads((ROOT / "web" / "i18n" / "en.json").read_text())
FIRMS = json.loads((ROOT / "firms.json").read_text())
UNI = FIRMS["_asset_universe"]
fails, n = [], 0


def ok(name, cond, info=""):
    global n
    n += 1
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else f"  {str(info)[:500]}"))
    if not cond:
        fails.append(name)


def tick(age_ms=900):
    now = int(time.time() * 1000)
    rows = [("BTC", "84496.41"), ("ETH", "2692.58"), ("SOL", "117.47"), ("XRP", "1.5385"), ("BNB", "780")]
    return json.dumps({"source": "Binance.US", "quote": "USDT", "as_of": now - age_ms, "served": now,
                       "items": [{"sym": s, "pair": s + "USDT", "last": p, "chg_pct": 0.5, "at": now - age_ms} for s, p in rows]})


CLEAN = """()=>{const r=document.getElementById('result').cloneNode(true);r.querySelectorAll('.d2x').forEach(e=>e.remove());return r.innerHTML}"""
NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")


def nums(s):
    return {round(float(x.replace(",", "")), 2) for x in NUM.findall(s)}


def main():
    srv, url = serve(PUB)
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")

        def page(path="/desk-preview", w=1280, api="ok", age=900, **kw):
            ctx = b.new_context(viewport={"width": w, "height": 900}, **kw)

            def handler(r):
                u = r.request.url
                if "/api/ticker" in u:
                    if api == "fail":
                        return r.fulfill(status=502, body="{}", content_type="application/json")
                    return r.fulfill(status=200, body=tick(age), content_type="application/json")
                if u.endswith("/status.json") or u.endswith("/calendar.json"):
                    return r.fulfill(status=404, body="")
                return r.continue_() if u.startswith("http://127.0.0.1") else r.abort()
            ctx.route("**/*", handler)
            route_tv(ctx, "ok")
            pg = ctx.new_page()
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto(url + path, wait_until="load")
            pg.wait_for_timeout(700)
            return ctx, pg, errs

        def states(pg, clean):
            out = []
            for f in pg.eval_on_selector_all("#firm option", "e=>e.map(x=>x.value)"):
                pg.select_option("#firm", f)
                for pr in pg.eval_on_selector_all("#profile option", "e=>e.map(x=>x.value)"):
                    pg.select_option("#profile", pr)
                    for g in DESK_GRID:
                        pg.evaluate("""g=>{for(const k of ['quota','equity','daystart','entry','stop','lev']){document.getElementById(k).value=g[k];}
                          document.getElementById('side').value=g.side;document.getElementById('mode').value=g.mode;
                          document.getElementById('quota').dispatchEvent(new Event('input'));}""", g)
                        out.append((f, pr, str(g), pg.evaluate(clean)))
                    pg.evaluate("()=>{const d=document.querySelector('#result details.work');if(d){d.open=true;}"
                                "document.getElementById('quota').dispatchEvent(new Event('input'))}")
                    out.append((f, pr, "working open", pg.evaluate(clean)))
            return out

        # 1. the same figures as the live desk
        ctx, live, _ = page("/")
        base = states(live, "()=>document.getElementById('result').innerHTML")
        ctx.close()
        ctx, pg, errs = page()
        mine = states(pg, CLEAN)
        diff = [a[:3] for a, c in zip(base, mine) if a != c]
        ok(f"the {len(base)} desk states: the preview's result is the live desk's, byte for byte, its own additions aside",
           len(base) == len(mine) == 84 and not diff, diff[:3])
        ok("no page error across the 84 states", not errs, errs)
        ctx.close()

        # 2. the Asset field: firms.json's listed symbols, grouped; it changes the two lines only
        ctx, pg, errs = page()
        groups = pg.evaluate("()=>[...document.querySelectorAll('#asset optgroup')].map(g=>[g.label,[...g.querySelectorAll('option')].map(o=>o.value)])")
        want = [[EN["desk2.group." + g["group"]], [s["sym"] for s in g["symbols"]]] for g in UNI["groups"]]
        ok("the Asset field lists firms.json's symbols, grouped, and none of the tape's unlisted stocks", groups == want
           and not any(s in json.dumps(groups) for s in UNI["not_listed"]), groups)
        ok("the Asset field is first in your trade", pg.evaluate("document.querySelector('#st-trade .grid select').id") == "asset")
        res0, aria0 = pg.evaluate(CLEAN), pg.evaluate("document.getElementById('gauge').getAttribute('aria-label')")
        seen = {}
        for g in UNI["groups"]:
            for s in g["symbols"]:
                pg.select_option("#asset", s["sym"])
                pg.wait_for_timeout(30)
                seen[s["sym"]] = pg.inner_text("#assetnote")
                if pg.evaluate(CLEAN) != res0 or pg.evaluate("document.getElementById('gauge').getAttribute('aria-label')") != aria0:
                    seen["_changed"] = s["sym"]
        ok("changing the asset changes neither the result nor the gauge", "_changed" not in seen, seen.get("_changed"))
        ok("changing the asset changes the asset lines", len(set(seen.values())) == len(seen), seen)

        def src(fk, sid):
            s = FIRMS[fk]["provenance"]["sources"][sid]
            return s["url"], s["read_on"]
        bf, br, cft = (FIRMS[k]["name"] for k in ("bitfunded", "brightfunded", "crypto_fund_trader"))
        rtp_url, rtp_date = src("bitfunded", "rtp_0924")
        hold_url, hold_date = src("bitfunded", "rtp")
        pg.select_option("#firm", "bitfunded")
        cases = [("BTC", [f"{bf} lists BTC as “BTC (Major Crypto Assets)”", f"read {rtp_date}", f"Hold limit at {bf}: {FIRMS['bitfunded']['hold_cap_days']['major']} days for BTC, one of its Major Crypto Assets", f"read {hold_date}"]),
                 ("XAU", [f"{bf} lists Gold as “XAU (Traditional Trading Pairs)”", f"{FIRMS['bitfunded']['hold_cap_days']['tradfi']} days for Gold, one of its Traditional Trading Pairs"]),
                 ("TSLA", [f"{FIRMS['bitfunded']['hold_cap_days']['tradfi']} days for TSLA"]),
                 ("WTI", ["WTI oil isn't on the Bitfunded pages troid has read.", f"Listed by {br}."])]
        for sym, parts in cases:
            pg.select_option("#asset", sym)
            t = pg.inner_text("#assetnote")
            ok(f"{bf}, {sym}: {parts[0]}", all(x in t for x in parts) and (sym != "WTI" or "Hold limit" not in t), t)
        links = pg.evaluate("()=>{document.getElementById('asset').value='BTC';document.getElementById('asset').dispatchEvent(new Event('change'));return [...document.querySelectorAll('#assetnote a')].map(a=>a.href)}")
        ok("each asset line links its source", links == [rtp_url, hold_url], links)
        pg.select_option("#firm", "brightfunded")
        t = pg.inner_text("#assetnote")
        ok(f"{br}, BTC: listed as “BTC/USD”; no hold limit found", f"{br} lists BTC as “BTC/USD”" in t and f"Hold limit at {br}: none found" in t, t)
        pg.select_option("#firm", "crypto_fund_trader")
        t = pg.inner_text("#assetnote")
        faq_url, faq_date = src("crypto_fund_trader", "faq_0924")
        tc_url, tc_date = src("crypto_fund_trader", "tc")
        ok(f"{cft}: its symbols are named only inside its platform (its FAQ, read {faq_date}); no hold limit stated in its Terms (read {tc_date})",
           f"{cft} names its symbols only inside its platform" in t and f"read {faq_date}" in t and f"Listed by {bf} and {br}." in t
           and f"Hold limit at {cft}: none stated in its Terms and Conditions (read {tc_date})" in t, t)
        ok("no page error", not errs, errs)
        ctx.close()

        # 3. the entry chip and the stale-stop rule
        ctx, pg, errs = page()
        ok("the chip: live BTC from /api/ticker", pg.inner_text("#chipb") == "live 84,496.41 · use" and not pg.evaluate("document.getElementById('chipb').hidden"))
        pg.click("#chipb")
        pg.wait_for_timeout(50)
        ok("a tap fills the entry with the price as quoted; a stop within 25% stays; the desk recomputes",
           pg.input_value("#entry") == "84496.41" and pg.input_value("#stop") == "74814" and "11.46%" in pg.inner_text("#result"), pg.inner_text("#result")[:300])
        pg.select_option("#asset", "ETH")
        pg.wait_for_timeout(30)
        ok("the chip follows the asset", pg.inner_text("#chipb") == "live 2,692.58 · use")
        pg.click("#chipb")
        pg.wait_for_timeout(50)
        v = pg.inner_text("#result .verdict")
        ok("a new entry that leaves the stop on the wrong side clears it: \"Set your stop\", not BLOCK, no stop suggested",
           pg.input_value("#stop") == "" and v.startswith(EN["desk2.js.set_tag"]) and "BLOCK" not in v and EN["desk2.js.set_cleared"] in v
           and not re.search(r"\d{3,}", v.split("\n")[1] if "\n" in v else v), v)
        ok("the empty stop shows its placeholder, and the trade card says the step needs it",
           pg.get_attribute("#stop", "placeholder") == EN["desk2.js.stop_ph"] and pg.evaluate("document.getElementById('st-trade').classList.contains('err')"))
        ok("with no stop, the gauge draws no drop and says to set one", pg.evaluate("document.getElementById('gauge').className") == "gauge sSET"
           and "set your stop" in pg.inner_text(".gline"))
        pg.fill("#stop", "2600")
        pg.wait_for_timeout(50)
        ok("a stop typed in sizes the trade again", pg.inner_text("#result .verdict").startswith(("OK", "REDUCE")) and not pg.evaluate("document.getElementById('st-trade').classList.contains('err')"))
        pg.fill("#stop", "2000")                                    # 25.7% away
        pg.evaluate("DESK2.use('2692.58')")
        ok("more than 25% away is cleared too", pg.input_value("#stop") == "")
        pg.select_option("#side", "-1")
        pg.fill("#stop", "2800")
        pg.evaluate("DESK2.use('2692.58')")
        ok("a short's stop above the entry and within 25% stays", pg.input_value("#stop") == "2800")
        for sym in ("XAU", "WTI", "TSLA"):
            pg.select_option("#asset", sym)
            ok(f"{sym}: no fill button; the field points to the tape", pg.evaluate("document.getElementById('chipb').hidden")
               and pg.inner_text("#chipm") == EN["desk2.js.chip_manual"])
        ok("no page error", not errs, errs)
        ctx.close()
        ctx, pg, errs = page(age=90_000)
        ok("a price over 60 s old: \"delayed\"", pg.inner_text("#chipb").startswith("delayed 84,496.41"))
        ctx.close()
        ctx, pg, errs = page(api="fail")
        ok("no price: no chip, no error", pg.evaluate("document.getElementById('chipb').hidden") and not errs, errs)
        ctx.close()

        # 4. a tapped tape symbol, and the still row's "use as entry"
        for q, want_asset, note in [("BINANCEUS:ETHUSDT", "ETH", None), ("OANDA:XAUUSD", "XAU", None), ("OANDA:WTICOUSD", "WTI", None),
                                    ("NASDAQ:NVDA", "BTC", "NVDA is on the tape as market context"), ("NASDAQ:NOPE", "BTC", None)]:
            ctx, pg, errs = page(f"/desk-preview?tvwidgetsymbol={q}#desk")
            t = pg.inner_text("#assetnote")
            ok(f"?tvwidgetsymbol={q}: asset {want_asset}" + (f", \"{note}…\"" if note else ""), pg.input_value("#asset") == want_asset
               and ((note in t) if note else "market context" not in t) and not errs, (pg.input_value("#asset"), t, errs))
            ctx.close()
        tv = lambda pg: json.loads(pg.get_attribute("#tk", "data-tv"))["largeChartUrl"]
        ctx, pg, _ = page()
        ok("the preview's tape opens the preview", tv(pg) == "https://troid.ai/desk-preview?tvwidgetsymbol={symbolname}#desk", tv(pg))
        ok("the preview's tape line says how to use it here", EN["desk2.tape_hint"] in pg.inner_text(".tkc"))
        ctx.close()
        ctx, pg, _ = page("/")
        ok("the live desk's tape still opens the live desk", tv(pg) == "https://troid.ai/?tvwidgetsymbol={symbolname}#desk", tv(pg))
        ctx.close()
        ctx, pg, errs = page(reduced_motion="reduce")
        pg.click('#tk .tki[data-sym="ETH"]')
        pg.click("#tk-use button")
        pg.wait_for_timeout(50)
        ok("the still row's \"use as entry\" selects the asset and applies the stop rule", pg.input_value("#asset") == "ETH"
           and pg.input_value("#entry") == "2692.58" and pg.input_value("#stop") == "", (pg.input_value("#asset"), pg.input_value("#entry")))
        ctx.close()

        # 5. the gauge, the ladder, the fee bar, the explainer
        ctx, pg, errs = page()
        g = pg.evaluate("""()=>{const y=s=>{const m=new DOMMatrix(getComputedStyle(document.querySelector(s)).transform);return [m.m42,m.d]};
          return {dot:y('.gdot')[0],d:y('.gfl[data-g=d]')[0],m:y('.gfl[data-g=m]')[0],q:y('.gq')[0],seg:y('.gseg'),L:document.querySelector('.gtr').clientHeight,
            cls:document.getElementById('gauge').className,aria:document.getElementById('gauge').getAttribute('aria-label'),
            labs:[...document.querySelectorAll('.glab')].map(e=>e.innerText.replace(/\\n/g,' '))}}""")
        ok("the gauge, vertical on a wide screen: quota at the top, then equity, the daily floor, the max-loss floor",
           g["q"] <= g["dot"] < g["d"] < g["m"], g)
        room_px, seg_px = g["d"] - g["dot"], g["seg"][1] * g["L"]
        ok("the drop at the stop against the room, to scale: $500 of $4,000", abs(room_px / seg_px - 8) < 0.05, (room_px, seg_px))
        ok("its labels carry the result's figures", all(x in " | ".join(g["labs"]) for x in ("$100,000.00", "$96,000.00", "$94,000.00", "$4,000.00")), g["labs"])
        ok("OK: the signal blue; the gauge states it in words", g["cls"] == "gauge sOK" and "room $4,000.00" in g["aria"] and "$500.00" in g["aria"], g)
        pg.fill("#riskPct", "5")
        pg.wait_for_timeout(700)                                      # the gauge's move (--dur-slow)
        r = pg.evaluate("""()=>{const s=q=>new DOMMatrix(getComputedStyle(document.querySelector(q)).transform).d;
          return {cls:document.getElementById('gauge').className,seg:s('.gseg'),ghost:s('.gghost'),op:getComputedStyle(document.querySelector('.gghost')).opacity}}""")
        ok("REDUCE: amber, the drop trimmed to the cap with the intended risk behind it ($1,400 of $5,000)",
           r["cls"] == "gauge sREDUCE" and r["op"] == "1" and abs(r["ghost"] / r["seg"] - 5000 / 1400) < 0.01, r)
        pg.fill("#riskPct", "0.5")
        pg.fill("#equity", "95000")
        pg.wait_for_timeout(50)
        ok("BLOCK past the floor: red, and the account card says so", pg.evaluate("document.getElementById('gauge').className") == "gauge sBLOCK"
           and pg.evaluate("document.getElementById('st-account').classList.contains('err')"))
        pg.fill("#equity", "100000")
        pg.fill("#stop", "80000")
        pg.wait_for_timeout(50)
        ok("BLOCK on a stop the trader typed on the wrong side stays BLOCK (the stale rule is for a new entry only)",
           pg.inner_text("#result .verdict").startswith("BLOCK") and pg.evaluate("document.getElementById('st-trade').classList.contains('err')"))
        pg.fill("#stop", "74814")
        pg.wait_for_timeout(50)
        lad = pg.evaluate("()=>[...document.querySelectorAll('.lad .lr')].map(r=>[r.className,r.querySelector('.ln').innerText,r.querySelector('.lv').innerText])")
        brk = pg.evaluate("()=>document.querySelector('#result .brk').innerText")
        ok("the ladder: the readout's breakers in order, the stop first, liquidation under cross off-scale",
           bool(lad) and lad[0][0] == "lr first" and "off" in lad[-1][0] and lad[-1][2] == "→ 804.92%, off-scale"
           and all(x[2].replace("→ ", "").replace(", off-scale", "") in brk for x in lad), (lad, brk))
        pg.select_option("#firm", "crypto_fund_trader")                # up to 100x at $50,000 and over
        pg.select_option("#mode", "isolated")
        pg.fill("#lev", "100")
        pg.wait_for_timeout(50)
        lad = pg.evaluate("()=>[...document.querySelectorAll('.lad .lr')].map(r=>[r.className,r.innerText])")
        ok("a breaker before the stop (isolated at 100x) is red and says so", any("bad" in c and EN["desk2.js.l_before"] in t for c, t in lad), lad)
        pg.select_option("#firm", "bitfunded")
        pg.select_option("#mode", "cross")
        pg.fill("#lev", "5")
        pg.wait_for_timeout(50)
        fb = pg.evaluate("""()=>({t:document.querySelector('.feebar').innerText,k:new DOMMatrix(getComputedStyle(document.querySelector('.fbar i')).transform).a,
          cell:[...document.querySelectorAll('#result .cell')].find(c=>/fees/i.test(c.querySelector('.k').innerText)).querySelector('.v').innerText})""")
        ok("the fee bar: the fee share the readout states, drawn to scale", fb["cell"] in fb["t"] and abs(fb["k"] - float(fb["cell"].rstrip("%")) / 100) < 0.001, fb)
        how = pg.inner_text("#xs")
        full = pg.evaluate("()=>document.getElementById('result').innerHTML.replace(/<[^>]+>/g,' ')+' '+[...document.querySelectorAll('#desk input')].map(i=>i.value).join(' ')")   # its working too
        cross = 100000 * (1 - 6 / 100 + 4 / 100)
        extra = nums(how) - nums(full) - {1.0, round(cross, 2)}
        ok("the explainer quotes only the result's numbers, its inputs and the crossover ($98,000)", not extra and "$98,000.00" in how, extra)
        ok("the explainer: six steps on a sized trade", pg.evaluate("document.querySelectorAll('#xs li').length") == 6)
        ok("no page error", not errs, errs)
        ctx.close()

        # 6. a phone: the cards, the pinned gauge, noindex and nothing linking here
        ctx, pg, errs = page(w=390, is_mobile=True, has_touch=True)
        cards = pg.evaluate("()=>['st-account','st-trade','st-risk'].map(i=>[document.getElementById(i).open,document.querySelector('#'+i+' .ss').innerText])")
        ok("a phone opens on the trade: account and risk folded, their summaries showing", [c[0] for c in cards] == [False, True, False]
           and cards[0][1].startswith(FIRMS["bitfunded"]["name"]) and "cap 35%" in cards[2][1], cards)
        pg.evaluate("document.getElementById('st-trade').scrollIntoView()")
        pg.evaluate("scrollBy(0,300)")
        pg.wait_for_timeout(100)
        ok("the gauge pins under the tape while the desk is on screen", abs(pg.evaluate("document.getElementById('gauge').getBoundingClientRect().top")) < 1)
        ok("375 px wide or less, nothing scrolls sideways", pg.evaluate("document.scrollingElement.scrollWidth<=innerWidth"))
        ok("noindex", pg.get_attribute('meta[name="robots"]', "content") == "noindex,nofollow")
        ok("the title says it is a preview", pg.title() == EN["desk-preview.meta.title"])
        ctx.close()
        linked = [f.name for f in PUB.rglob("*.html") if f.name != "desk-preview.html" and "desk-preview" in f.read_text()]
        ok("no other page links to it, and it is in no sitemap", not linked and "desk-preview" not in (PUB / "sitemap.xml").read_text(), linked)
        size = sum((PUB / f).stat().st_size for f in ("ticker.js", "calendar.js", "desk2.js"))
        ok(f"the header strips' and the preview's scripts: {size / 1024:.1f} KB, under the 40 KB budget", size < 40 * 1024)
        b.close()
    srv.shutdown()
    print(f"\n{n - len(fails)}/{n} passed")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
