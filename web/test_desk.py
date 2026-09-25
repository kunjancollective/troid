#!/usr/bin/env python3
"""troid's desk (partials/_desk2.html, web/public/desk2.js; design handoff 2026-09-24, section 4; ticker v2 handoff,
sections E and F; the owner's iPhone test of the preview), in Chromium against web/public served locally. /api/ticker
is answered by the test and TradingView's script by backtest/tv_stub.py: spends nothing, calls no one. The same
behaviours on WebKit, as an iPhone lays them out: web/test_desk_webkit.py.

  python web/test_desk.py

- The same figures as before the redesign: the 84 desk states give the result the old desk gave, byte for byte, once the
  desk's own additions (the ladder and the fee bar, marked d2x) are set aside (against OLD, the last revision whose home
  page was the old desk, served from git).
- A first view with no example trade: entry and stop empty with a grey 0.00 placeholder, the account on the gauge and
  "Enter your entry and stop to size a trade." in the readout; an entry alone is "Set your stop"; a stop alone is the
  first view. The settings keep their defaults and their notes say whose they are.
- The Asset field: firms.json's listed symbols, grouped; it changes the hold-limit line and the availability note only.
- The entry chip: a crypto asset's spot price, "live … · use", "delayed" past 60 s, gone when there is none; gold, oil and
  stocks point to the tape. A tap fills the entry, lights it and leaves focus where it was; a stop the new entry leaves
  on the wrong side or more than 25% away is cleared ("Set your stop"), never BLOCK, never a suggested stop.
- A tapped tape symbol (?tvwidgetsymbol=…; every symbol's real link, captured from TradingView's tape, web/tape_captured.json,
  as it was and as the bare largeChartUrl gives it) selects the asset, brings it into
  view lit, says "ETH selected · live … · use" or that live fill isn't available, fills nothing, shows no shared-link
  notice and leaves a clean address; a tab the tape opened hands the address to troid's tab and closes. The symbol counts
  wherever it arrives (the query, or after the #), never an unfilled {symbolname}; one the desk can't read keeps the
  default asset and says so by the Asset field, never silently.
- A shared link restores the sharer's numbers and says so; #desk alone doesn't.
- The gauge, the ladder, the fee bar and the explainer draw the result's own numbers; the step cards; the pinned gauge;
  16 px fields on a phone; nothing sideways.
"""
import json
import re
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backtest"))
from i18n_equiv import DESK_GRID, PUB, baseline, serve  # noqa: E402
from tv_stub import route_tv  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
EN = json.loads((ROOT / "web" / "i18n" / "en.json").read_text())
FIRMS = json.loads((ROOT / "firms.json").read_text())
UNI = FIRMS["_asset_universe"]
DESK = "/"                      # the redesigned desk, troid's home page since 2026-09-25
OLD = "1eefe86"                 # the last revision whose home page was the old desk: the figures the new one must give
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


def trade(pg, entry="77872", stop="74814"):
    """The example trade the old desk started with, typed in as a trader would."""
    pg.fill("#entry", entry)
    pg.fill("#stop", stop)
    pg.wait_for_timeout(40)


def main():
    srv, url = serve(PUB)
    old_dir = tempfile.TemporaryDirectory()
    baseline(OLD, Path(old_dir.name))
    srv0, url0 = serve(old_dir.name)
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")

        def page(path=DESK, w=1280, api="ok", age=900, ctx=None, root=None, **kw):
            ctx = ctx or b.new_context(viewport={"width": w, "height": 900}, **kw)

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
            pg.goto((root or url) + path, wait_until="load")
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
        state = "()=>({cls:document.getElementById('gauge').className,line:document.querySelector('.gline').textContent,res:document.getElementById('result').innerText})"

        # 1. the same figures as the desk before the redesign
        ctx, old, _ = page("/", root=url0)
        base = states(old, "()=>document.getElementById('result').innerHTML")
        ctx.close()
        ctx, pg, errs = page()
        mine = states(pg, CLEAN)
        diff = [a[:3] for a, c in zip(base, mine) if a != c]
        ok(f"the {len(base)} desk states: the result the old desk gave, byte for byte, the desk's own additions aside",
           len(base) == len(mine) == 84 and not diff, diff[:3])
        ok("no page error across the 84 states", not errs, errs)
        ctx.close()

        # 2. a first view with no example trade
        ctx, pg, errs = page()
        f = pg.evaluate("""()=>['entry','stop'].map(i=>{const e=document.getElementById(i);return [e.value,e.placeholder,e.inputMode]})""")
        ok("entry and stop start empty, 0.00 a grey placeholder, a decimal keypad", f == [["", "0.00", "decimal"]] * 2, f)
        keep = pg.evaluate("()=>['quota','equity','daystart','targetR','riskPct','capPct','lev','mode'].map(i=>document.getElementById(i).value)")
        ok("the account keeps 100,000 and the settings their defaults", keep == ["100000", "100000", "100000", "2", "0.5", "35", "5", "cross"], keep)
        s = pg.evaluate(state)
        ok("the readout: \"Enter your entry and stop to size a trade.\", no verdict, no size, no ladder",
           s["res"].startswith(EN["desk2.js.empty"]) and pg.evaluate("!document.querySelector('#result .verdict,#result .read,.lad,.feebar')"), s["res"][:200])
        ok("the gauge: the account only, the room in dollars", s["cls"] == "gauge sEMPTY" and s["line"] == "room $4,000.00 before the daily loss limit"
           and pg.evaluate("getComputedStyle(document.querySelector('.gdot')).opacity") == "1"
           and pg.evaluate("getComputedStyle(document.querySelector('.gseg')).opacity") == "0", s)
        ok("no card flags an error on a first view", not pg.evaluate("document.querySelector('.step.err')"))
        pg.fill("#entry", "77872")
        pg.wait_for_timeout(40)
        s = pg.evaluate(state)
        ok("an entry alone: \"Set your stop\", nothing sized, no stop suggested", s["res"].startswith(EN["desk2.js.set_tag"]) and s["cls"] == "gauge sSET"
           and EN["desk2.js.set_cleared"] not in s["res"] and pg.input_value("#stop") == "", s["res"][:200])
        pg.fill("#entry", "")
        pg.fill("#stop", "74814")
        pg.wait_for_timeout(40)
        s = pg.evaluate(state)
        ok("a stop alone: the first view again", s["res"].startswith(EN["desk2.js.empty"]) and s["cls"] == "gauge sEMPTY", s["res"][:120])
        pg.fill("#entry", "77872")
        pg.wait_for_timeout(40)
        ok("both: sized", pg.inner_text("#result .verdict").startswith("OK"))
        notes = pg.evaluate("()=>Object.fromEntries(['target_r','risk_pct','cap_pct','leverage','mode','entry','stop'].map(t=>[t,document.getElementById('g-'+t).innerText]))")
        ok("the settings' notes say \"troid's default — change it to yours.\"; entry's and stop's don't",
           all(EN["glossary.default"] in notes[k] for k in ("target_r", "risk_pct", "cap_pct", "leverage", "mode"))
           and not any(EN["glossary.default"] in notes[k] for k in ("entry", "stop")), notes)
        ok("entry's note says where the live price is", EN["glossary.entry.chip"] in notes["entry"])
        ok("no page error", not errs, errs)
        ctx.close()

        # 3. the Asset field: firms.json's listed symbols, grouped; it changes the two lines only
        ctx, pg, errs = page()
        trade(pg)
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
        hd = FIRMS["bitfunded"]["hold_cap_days"]
        for sym, parts in [("BTC", [f"{bf} lists BTC as “BTC (Major Crypto Assets)”", f"read {rtp_date}", f"Hold limit at {bf}: {hd['major']} days for BTC, one of its Major Crypto Assets", f"read {hold_date}"]),
                           ("XAU", [f"{bf} lists Gold as “XAU (Traditional Trading Pairs)”", f"{hd['tradfi']} days for Gold, one of its Traditional Trading Pairs"]),
                           ("TSLA", [f"{hd['tradfi']} days for TSLA"]),
                           ("WTI", ["WTI oil isn't on the Bitfunded pages troid has read.", f"Listed by {br}."])]:
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

        # 4. the entry chip, the highlight and the stale-stop rule
        ctx, pg, errs = page()
        ok("the chip: live BTC from /api/ticker", pg.inner_text("#chipb") == "live 84,496.41 · use" and not pg.evaluate("document.getElementById('chipb').hidden"))
        pg.fill("#stop", "74814")
        pg.click("#chipb")
        pg.wait_for_timeout(50)
        ok("a tap fills the entry with the price as quoted; a stop within 25% stays; the desk sizes it",
           pg.input_value("#entry") == "84496.41" and pg.input_value("#stop") == "74814" and "11.46%" in pg.inner_text("#result"), pg.inner_text("#result")[:300])
        ok("the entry lights up and focus doesn't move into it (a phone would zoom)", pg.evaluate("document.querySelector('#entry').closest('.fi').classList.contains('on')")
           and pg.evaluate("document.activeElement.id") != "entry", pg.evaluate("document.activeElement.id"))
        pg.wait_for_timeout(1300)
        ok("the light goes out", not pg.evaluate("document.querySelector('#entry').closest('.fi').classList.contains('on')"))
        pg.select_option("#asset", "ETH")
        pg.wait_for_timeout(30)
        ok("the chip follows the asset", pg.inner_text("#chipb") == "live 2,692.58 · use")
        pg.click("#chipb")
        pg.wait_for_timeout(50)
        v = pg.inner_text("#result .verdict")
        ok("a new entry that leaves the stop on the wrong side clears it: \"Set your stop\", not BLOCK, no stop suggested",
           pg.input_value("#stop") == "" and v.startswith(EN["desk2.js.set_tag"]) and "BLOCK" not in v and EN["desk2.js.set_cleared"] in v, v)
        ok("the trade card says the step needs its stop; the gauge draws no drop", pg.evaluate("document.getElementById('st-trade').classList.contains('err')")
           and pg.evaluate("document.getElementById('gauge').className") == "gauge sSET" and "set your stop" in pg.inner_text(".gline"))
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

        # 5. a tapped tape symbol: TradingView adds its own parameters after #desk
        TV = "&utm_source=troid.ai&utm_medium=widget&utm_campaign=ticker-tape"
        MISS = EN["desk2.js.tape_miss"]
        for q, want_asset, chip, note in [
                ("BINANCEUS:ETHUSDT", "ETH", "ETH selected · live 2,692.58 · use", None),
                ("OANDA:XAUUSD", "XAU", None, None),
                ("OANDA:WTICOUSD", "WTI", None, None),
                ("NASDAQ:NVDA", "BTC", None, "NVDA is on the tape as market context"),
                ("NASDAQ:NOPE", "BTC", None, MISS),
                ("{symbolname}", "BTC", None, MISS),                            # a placeholder the widget never filled
                ("%7Bsymbolname%7D#desk?tvwidgetsymbol=BINANCEUS%3AXRPUSDT", "XRP", "XRP selected · live 1.5385 · use", None)]:  # the real symbol after the #
            ctx, pg, errs = page(f"{DESK}?tvwidgetsymbol={q}" + ("" if "#" in q else f"#desk{TV}"), w=390, is_mobile=True, has_touch=True)
            t = pg.inner_text("#assetnote")
            got = pg.evaluate("""()=>{const r=e=>{const b=e.getBoundingClientRect();return b.top>=0&&b.bottom<=innerHeight};
              return {asset:document.getElementById('asset').value,entry:document.getElementById('entry').value,shared:document.getElementById('shared').hidden,
                chip:document.getElementById('chipb').hidden?null:document.getElementById('chipb').innerText,chipm:document.getElementById('chipm').hidden?null:document.getElementById('chipm').innerText,
                lit:document.querySelector('#asset').closest('.fi').classList.contains('on'),inview:r(document.getElementById('asset')),noteview:r(document.getElementById('assetnote')),
                addr:location.pathname+location.search+location.hash}}""")
            label = f"a tape tap on {q}"
            ok(f"{label}: asset {want_asset}, nothing filled, no shared-link notice, a clean address", got["asset"] == want_asset and got["entry"] == ""
               and got["shared"] and got["addr"] == DESK + "#desk" and not errs, (got, errs))
            if note == MISS:
                ok(f"{label}: never a silent fallback: \"{MISS}\" by the Asset field, in view, nothing lit", t.startswith(MISS) and got["noteview"] and not got["lit"], (t, got))
                pg.select_option("#asset", "SOL")
                ok(f"{label}: choosing an asset clears the note", MISS not in pg.inner_text("#assetnote"))
            elif want_asset in ("ETH", "XRP"):
                ok(f"{label}: the asset in view and lit; by the entry \"{chip}\"", got["inview"] and got["lit"] and got["chip"] == chip, got)
            elif want_asset in ("XAU", "WTI"):
                name = EN[f"ticker.sym.{want_asset}"]
                ok(f"{label}: \"Live fill isn't available for {name} — enter your price from the tape above.\"", got["inview"] and got["lit"]
                   and got["chipm"] == EN["desk2.js.chip_no_fill"].format(asset=name) and got["chip"] is None, got)
            elif note:
                ok(f"{label}: \"{note}…\", in view", note in t and got["noteview"] and MISS not in t, (t, got))
            ctx.close()
        # 5b. every tape symbol as TradingView's real tape links it (captured 2026-09-25, web/tape_captured.json): the link
        # as it was (the symbol after the #, an unfilled {symbolname} in the query) and the link the bare largeChartUrl gives
        CAP = json.loads((ROOT / "web" / "tape_captured.json").read_text())
        listed = {s["sym"] for g in UNI["groups"] for s in g["symbols"]}
        for sym, link in CAP["links"].items():
            u = urlsplit(link)
            forms = {"as captured": f"{u.path}?{u.query}#{u.fragment}", "from the bare page": "/?" + u.fragment.split("?", 1)[1]}
            res = {}
            for form, path in forms.items():
                ctx, pg, errs = page(path, w=390, is_mobile=True, has_touch=True)
                res[form] = pg.evaluate("""()=>({asset:document.getElementById('asset').value,note:document.getElementById('assetnote').innerText,
                  chip:document.getElementById('chipb').hidden?null:document.getElementById('chipb').innerText,
                  chipm:document.getElementById('chipm').hidden?null:document.getElementById('chipm').innerText,
                  shared:document.getElementById('shared').hidden,addr:location.pathname+location.search+location.hash})""")
                res[form]["errs"] = errs
                ctx.close()
            def good(g):
                if g["errs"] or MISS in g["note"] or not g["shared"] or g["addr"] != "/#desk":
                    return False
                if sym not in listed:
                    return g["asset"] == "BTC" and g["note"].startswith(f"{sym} is on the tape as market context")
                if sym in ("XAU", "WTI"):
                    return g["asset"] == sym and g["chipm"] == EN["desk2.js.chip_no_fill"].format(asset=EN[f"ticker.sym.{sym}"])
                return g["asset"] == sym and (g["chip"] or "").startswith(f"{sym} selected · live")
            what = "selected" if sym in listed else "named as market context"
            ok(f"the real tape's {sym} link, as captured and from the bare page: {sym} {what}, never unread, no shared-link notice",
               all(good(g) for g in res.values()), res)

        ctx = b.new_context(viewport={"width": 1280, "height": 900})
        ctx, first, errs = page(ctx=ctx)
        with ctx.expect_page() as info:
            first.evaluate(f"window.open('{url}{DESK}?tvwidgetsymbol=BINANCEUS:SOLUSDT#desk{TV}')")
        tab = info.value
        first.wait_for_timeout(1500)
        ok("a tab the tape opened hands its address to troid's tab and closes: one tab, SOL selected there",
           tab.is_closed() and first.input_value("#asset") == "SOL" and first.evaluate("location.hash") == "#desk", (tab.is_closed(), first.url))
        ctx.close()

        # 6. a shared link says so; #desk alone doesn't
        ctx, pg, errs = page(f"{DESK}#f=bitfunded&p=1step&en=77872&st=74814")
        ok("a shared link restores the sharer's entry and stop, sizes them and says so", not pg.evaluate("document.getElementById('shared').hidden")
           and pg.input_value("#entry") == "77872" and pg.input_value("#stop") == "74814" and pg.inner_text("#result .verdict").startswith("OK"))
        ctx.close()
        for frag in ("#desk", "#firms"):
            ctx, pg, errs = page(DESK + frag)
            ok(f"{frag} alone: no shared-link notice", pg.evaluate("document.getElementById('shared').hidden"))
            ctx.close()

        # 7. the gauge, the ladder, the fee bar, the explainer
        ctx, pg, errs = page()
        trade(pg)
        pg.wait_for_timeout(700)
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
        ok("a stop the trader typed on the wrong side stays BLOCK (the stale rule is for a new entry only)",
           pg.inner_text("#result .verdict").startswith("BLOCK") and pg.evaluate("document.getElementById('st-trade').classList.contains('err')"))
        pg.fill("#stop", "74814")
        pg.wait_for_timeout(50)
        lad = pg.evaluate("()=>[...document.querySelectorAll('.lad .lr')].map(r=>[r.className,r.querySelector('.ln').innerText,r.querySelector('.lv').innerText])")
        brk = pg.evaluate("()=>document.querySelector('#result .brk').textContent")
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
        full = pg.evaluate("()=>document.getElementById('result').innerHTML.replace(/<[^>]+>/g,' ')+' '+[...document.querySelectorAll('#desk input')].map(i=>i.value).join(' ')")
        cross = 100000 * (1 - 6 / 100 + 4 / 100)
        extra = nums(how) - nums(full) - {1.0, round(cross, 2)}
        ok("the explainer quotes only the result's numbers, its inputs and the crossover ($98,000)", not extra and "$98,000.00" in how, extra)
        ok("the explainer: six steps on a sized trade", pg.evaluate("document.querySelectorAll('#xs li').length") == 6)
        ok("no page error", not errs, errs)
        ctx.close()

        # 8. a phone: the cards, the pinned gauge, 16 px fields, nothing sideways
        ctx, pg, errs = page(w=390, is_mobile=True, has_touch=True)
        cards = pg.evaluate("()=>['st-account','st-trade','st-risk'].map(i=>[document.getElementById(i).open,document.querySelector('#'+i+' .ss').innerText])")
        ok("a phone opens on the trade: account and risk folded, their summaries showing", [c[0] for c in cards] == [False, True, False]
           and cards[0][1].startswith(FIRMS["bitfunded"]["name"]) and "cap 35%" in cards[2][1], cards)
        sizes = pg.evaluate("()=>[...document.querySelectorAll('#desk input,#desk select')].map(e=>getComputedStyle(e).fontSize)")
        ok("every desk field is 16 px on a phone, so focusing one doesn't zoom the page", set(sizes) == {"16px"}, set(sizes))
        ok("the page stays zoomable: no maximum-scale, no user-scalable=no",
           not re.search(r"maximum-scale|user-scalable", pg.get_attribute('meta[name="viewport"]', "content")))
        pg.evaluate("document.getElementById('st-trade').scrollIntoView()")
        pg.evaluate("scrollBy(0,300)")
        pg.wait_for_timeout(100)
        ok("the gauge pins under the tape while the desk is on screen", abs(pg.evaluate("document.getElementById('gauge').getBoundingClientRect().top")) < 1)
        ok("375 px wide or less, nothing scrolls sideways", pg.evaluate("document.scrollingElement.scrollWidth<=innerWidth"))
        ctx.close()
        ctx, pg, errs = page(w=1280)
        ok("on a wide screen the fields keep the desk's 14 px", pg.evaluate("getComputedStyle(document.getElementById('entry')).fontSize") == "14px")
        ctx.close()
        size = sum((PUB / f).stat().st_size for f in ("ticker.js", "calendar.js", "desk2.js"))
        ok(f"the header strips' and the desk's scripts: {size / 1024:.1f} KB, under the 40 KB budget", size < 40 * 1024)
        b.close()
    srv.shutdown()
    srv0.shutdown()
    old_dir.cleanup()
    print(f"\n{n - len(fails)}/{n} passed")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
