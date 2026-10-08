#!/usr/bin/env python3
"""troid's desk (partials/_desk2.html, web/public/desk2.js; design handoff 2026-09-24, section 4; ticker v2 handoff,
sections E and F; the owner's iPhone test of the preview), in Chromium against web/public served locally. /api/ticker
is answered by the test and TradingView's script by backtest/tv_stub.py: spends nothing, calls no one. The same
behaviours on WebKit, as an iPhone lays them out: web/test_desk_webkit.py.

  python web/test_desk.py

- The 84 desk states against OLD, the revision the calculator audit checked (29 Sep 2026; its results are the old desk's
  of 1eefe86 byte for byte), served from git with today's firms.json rules in its FIRMS, the desk's own additions (the ladder and the fee bar, marked d2x) set aside
  on both: the structure and wording byte for byte with every figure masked, where only the audit's named rewordings are
  mapped back and its rules applied (F3: a pending drawdown type with a known max is the static floor, labelled as the
  loosest reading, the type not counted as a rule used; F5: a long's liquidation at or past 100% is "none above zero";
  the margin check and the loss at the stop are new rows); every figure the audit didn't change equals the old desk's;
  the loss at the stop is the risk to the cent. The figures it changed are held by the independent audit (audit/).
- The audit's cases as regressions (F1-F7 and the leverage held where no class is recorded), each read from the page.
- A first view with no example trade: entry and stop empty with a grey 0.00 placeholder, the account on the gauge and
  "Enter your entry and stop to size a trade." in the readout; an entry alone is "Set your stop"; a stop alone is the
  first view. The settings keep their defaults and their notes say whose they are.
- The Asset field: firms.json's listed symbols, grouped; it changes the hold-limit line and the availability note only.
- The entry chip: a crypto asset's spot price, "live … · use", "delayed" past 60 s, gone when there is none; gold, oil and
  stocks point to the tape. A tap fills the entry, lights it and leaves focus where it was; a stop the new entry leaves
  on the wrong side or more than 25% away is cleared ("Set your stop"), never BLOCK, never a suggested stop.
- The price on the chip always belongs to the asset in the field (the owner's Android test, 2026-09-25: a tapped NVDA
  left BTC in the field and the chip offered BTC's price for an Nvidia trade): checked on every asset, after a price
  update, after tape taps and "use", and with the field changed behind the chip's back; a price without its asset fills
  nothing.
- A tapped tape symbol (?tvwidgetsymbol=…; every symbol's real link, captured from TradingView's tape, web/tape_captured.json,
  as it was and as the bare largeChartUrl gives it) selects the asset, brings it into
  view lit, says "ETH selected · live … · use" or that live fill isn't available, fills nothing, shows no shared-link
  notice and leaves a clean address; a tab the tape opened hands the address to troid's tab and closes. The symbol counts
  wherever it arrives (the query, or after the #), never an unfilled {symbolname}; one the desk can't read keeps the
  default asset and says so by the Asset field, never silently. A stock no firm lists (NVDA, AAPL, GOOGL, MSFT, AMZN) is
  in the field as "NVDA · not offered by troid's firms", with no chip and no line about another asset, and the readout
  says there are no firm rules to size it against, whatever the entry and stop; choosing another asset removes it.
- A shared link restores the sharer's numbers and says so; #desk alone doesn't.
- The gauge, the ladder, the fee bar and the explainer draw the result's own numbers; the step cards; the pinned gauge;
  16 px fields on a phone; nothing sideways.
"""
import html
import json
import re
import subprocess
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
OLD = "9c8d447"                 # the revision the calculator audit checked: its 84 states are 1eefe86's (the old desk's)
fails, n = [], 0


def ok(name, cond, info=""):
    global n
    n += 1
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else f"  {str(info)[:500]}"))
    if not cond:
        fails.append(name)


PRICE = {"BTC": "84496.41", "ETH": "2692.58", "SOL": "117.47", "XRP": "1.5385", "BNB": "780"}


def tick(age_ms=900):
    now = int(time.time() * 1000)
    return json.dumps({"source": "Binance.US", "quote": "USDT", "as_of": now - age_ms, "served": now,
                       "items": [{"sym": s, "pair": s + "USDT", "last": p, "chg_pct": 0.5, "at": now - age_ms} for s, p in PRICE.items()]})


# the chip as drawn, and the asset in the field
CHIP = """()=>{const b=document.getElementById('chipb'),a=document.getElementById('asset').value;
  return {hidden:b.hidden,asset:a,sym:b.getAttribute('data-sym'),last:b.getAttribute('data-last'),label:b.getAttribute('aria-label')||'',
    text:b.innerText,name:(DESK2DATA.assets[a]||{}).name||null}}"""


def shown(p):
    """A quote as the chip shows it: 84496.41 → 84,496.41."""
    i, _, f = p.partition(".")
    return f"{int(i):,}" + (f".{f}" if f else "")


def chip_bad(pg):
    """None when the chip is hidden or shows the price of the asset in the field (its own price, its name, drawn for it);
    otherwise what it shows."""
    c = pg.evaluate(CHIP)
    if c["hidden"]:
        return None
    p = PRICE.get(c["asset"])
    good = p and c["sym"] == c["asset"] and c["last"] == p and shown(p) in c["text"] and c["label"].startswith(f"Use {c['name']} at {shown(p)},")
    return None if good else c


CLEAN = """()=>{const r=document.getElementById('result').cloneNode(true);r.querySelectorAll('.d2x').forEach(e=>e.remove());return r.innerHTML}"""
# a state as section 1 compares it: the result without the desk's own additions, and its working table's rows
GRAB = """()=>{const r=document.getElementById('result').cloneNode(true);r.querySelectorAll('.d2x').forEach(e=>e.remove());
  return {html:r.innerHTML,rows:[...r.querySelectorAll('details.work tr')].map(t=>[...t.children].map(td=>td.textContent))}}"""
NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")
EN0 = json.loads(subprocess.run(["git", "show", f"{OLD}:web/i18n/en.json"], cwd=ROOT, capture_output=True, text=True, check=True).stdout)

# The calculator audit (29 Sep 2026) as rules, never a list of states. F3 on the old desk: a product whose drawdown type
# is pending and whose max is known is sized as the static floor, and the type isn't a rule used (its provenance)
F3_OLD = """()=>{for(const f in FIRMS)for(const k in FIRMS[f].products){const p=FIRMS[f].products[k];if(p.dd==null&&p.m!=null){p.dd='static';p._loose=1}}
  const pb=window.provBlock;window.provBlock=function(f,p,used,formula,assumed){return pb(f,p,p._loose?used.filter(u=>u[0]!=='dd'):used,formula,assumed)}}"""
FIG = re.compile(r"[−-]?\$?\d[\d,]*(?:\.\d+)?")
REWORDED = ["index.js.f_fpu", "index.js.f_size", "index.js.f_left",                 # F6, F6, F7
            "index.js.n_lev_held", "index.js.f_lev_pending_held"]                    # held to the lowest cap, not the highest
# reworded where a placeholder carries markup ({n} is a glossary term), so mapped back by its parts
REWORDED_TPL = ["index.js.n_left"]                                                     # this one included (the owner, 2026-10-08)
NEW_ROWS = ["index.js.st_margin_check", "index.js.st_loss"]                            # F1, F6
# the working table's rows, by label, whose figures the audit left as they were
KEPT = ["inputs", "high at rollover", "high-water mark", "daily floor", "daily budget", "max-loss floor", "drawdown budget",
        "binding", "intended risk", "cap", "risk", "stop distance", "leverage used", "budget used", "target"]


def mask(s):
    return FIG.sub("#", s)


def _key(k, en):
    """A string as a result carries it, figures masked: its placeholders filled with a figure, escaped as innerHTML is."""
    return html.escape(mask(re.sub(r"\{\w+\}", "0", en[k])), quote=False)


def _tpl_back(h, k):
    """A reworded string whose placeholders carry markup, mapped back: its literal parts matched around each placeholder's
    value, the old string's parts written around the same values."""
    rx = "(?<=<div>)" + "".join("(?P<%s>(?:(?!</?div>).)*?)" % x[1:-1] if x.startswith("{") else re.escape(html.escape(mask(x), quote=False))
                 for x in re.split(r"(\{\w+\})", EN[k]) if x)
    return re.sub(rx + "(?=</div>)", lambda m: "".join(m.group(x[1:-1]) if x.startswith("{") else html.escape(mask(x), quote=False)
                                                   for x in re.split(r"(\{\w+\})", EN0[k]) if x), h)


def as_old(h):
    """The new desk's result, figures masked, written as the old desk wrote it: the new rows out, the named rewordings
    back, "none above zero" and a long's floor "not reached above zero" (the review, 2026-09-30) percentages again, the
    loosest reading's label and note out."""
    h = mask(h)
    for k in NEW_ROWS:
        h = re.sub(r"<tr><td>" + re.escape(EN[k]) + r"</td>.*?</tr>", "", h)
    for k in REWORDED:
        h = h.replace(_key(k, EN), _key(k, EN0))
    for k in REWORDED_TPL:
        h = _tpl_back(h, k)
    h = h.replace(_key("index.js.n_isolated_none", EN), _key("index.js.n_isolated", EN0)).replace(EN["index.js.v_liq_none"], "#%").replace(EN["index.js.v_floor_none"], "#%")
    h = h.replace(_key("index.js.f_dd_loosest", EN), _key("index.js.f_dd_static", EN0))
    return h.replace("<div>" + _key("index.js.n_dd_loosest", EN) + "</div>", "").replace('<div class="notes"></div>', "")


def usd(s):
    return float(s.replace("$", "").replace(",", "").replace("−", "-"))


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
    # the old desk's code with today's rules: firms.json's data (a newly recorded source, a rule filled in) is held by the
    # audit and verify_claims, so section 1 measures only what the desk's code does with it
    oi, rx = Path(old_dir.name) / "index.html", re.compile(r"<!-- profiles:start -->.*?<!-- profiles:end -->", re.S)
    oi.write_text(rx.sub(lambda m: rx.search((PUB / "index.html").read_text()).group(0), oi.read_text(), count=1))
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
                if u.endswith("/status.json") or u.endswith("/calendar.json") or u.endswith("/audit.json"):
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
                        out.append((f, pr, str(g), pg.evaluate(clean), g))
                    pg.evaluate("()=>{const d=document.querySelector('#result details.work');if(d){d.open=true;}"
                                "document.getElementById('quota').dispatchEvent(new Event('input'))}")
                    out.append((f, pr, "working open", pg.evaluate(clean), DESK_GRID[-1]))
            return out
        state = "()=>({cls:document.getElementById('gauge').className,line:document.querySelector('.gline').textContent,res:document.getElementById('result').innerText})"

        # 1. the 84 states against the revision the calculator audit checked, the old desk's figures, as the audit changed them
        ctx, old, _ = page("/", root=url0)
        old.evaluate(F3_OLD)
        levb = old.evaluate("()=>Object.fromEntries(Object.entries(FIRMS).flatMap(([f,x])=>Object.entries(x.products).map(([k,p])=>[f+'/'+k,p.levb])))")
        base = states(old, GRAB)
        ctx.close()
        ctx, pg, errs = page()
        mine = states(pg, GRAB)
        diff = [a[:3] for a, c in zip(base, mine) if mask(a[3]["html"]) != as_old(c[3]["html"])]
        ok(f"the {len(base)} desk states: the old desk's structure and wording, byte for byte, every figure masked; only the audit's "
           "rewordings mapped back and its rules applied (F3's loosest reading, F5's \"none above zero\", the two new rows)",
           len(base) == len(mine) == 84 and not diff, diff[:3])

        def covers(b, q):
            return (b.get("max_quota") is None or q <= b["max_quota"]) and (b.get("min_quota") is None or q >= b["min_quota"])
        moved, liq, loss = [], [], []
        for a, c in zip(base, mine):
            ro, rn = [r for r in a[3]["rows"] if r[0] in KEPT], [r for r in c[3]["rows"] if r[0] in KEPT]
            if [r[0] for r in ro] != [r[0] for r in rn]:
                moved.append((a[:3], [r[0] for r in ro], [r[0] for r in rn]))
            for x, y in zip(ro, rn):
                want, g, bands = x[2], a[4], levb[f"{a[0]}/{a[1]}"]
                if x[0] == "leverage used" and bands and not any(covers(b, g["quota"]) for b in bands):
                    want = f"{min(float(g['lev']), min(b['lev'] for b in bands)):g}×"      # the lowest recorded cap, not the highest
                if y[2] != want:
                    moved.append((a[:3], x[0], x[2], y[2]))
            lo, ln = [r[2] for r in a[3]["rows"] if r[0].startswith("exchange liq")], [r[2] for r in c[3]["rows"] if r[0].startswith("exchange liq")]
            if lo:
                past = a[4]["side"] == "1" and lo[0].endswith("%") and float(lo[0].rstrip("%").replace(",", "")) >= 100
                if past != (ln[0] == EN["index.js.v_liq_none"]):
                    liq.append((a[:3], lo[0], ln[0]))
            for lab in (EN["index.js.st_daily_dist"], EN["index.js.st_dd_dist"], EN["index.js.st_trailing_dist"]):
                fo, fn = [r[2] for r in a[3]["rows"] if r[0] == lab], [r[2] for r in c[3]["rows"] if r[0] == lab]
                if fo:
                    past = a[4]["side"] == "1" and float(fo[0].rstrip("%").replace(",", "")) >= 100
                    if past != (fn[0] == EN["index.js.v_floor_none"]):
                        liq.append((a[:3], lab, fo[0], fn[0]))
            rr = {r[0]: r for r in c[3]["rows"]}
            if EN["index.js.st_loss"] in rr and not (rr[EN["index.js.st_qty"]][1] == EN["index.js.f_qty_margin"] or rr[EN["index.js.st_loss"]][2] == rr["risk"][2]):
                loss.append((a[:3], rr["risk"][2], rr[EN["index.js.st_loss"]][2]))
        ok("the figures the audit didn't change are the old desk's in every state: inputs, floors, budgets, binding, intended risk, cap, "
           "risk, stop distance, leverage used (held to the lowest recorded cap where no class covers the quota), budget used, target",
           not moved, moved[:4])
        ok("\"none above zero\" exactly where a long's liquidation was at or past 100%, and a long's floor distances \"not reached above zero\" "
           "exactly where they were (the review, 2026-09-30); shorts and nearer ones as computed", not liq, liq[:4])
        ok("in every sized state, the loss at the stop is the risk to the cent", not loss, loss[:4])
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
        br_tc_url, br_tc_date = src("brightfunded", "tc_0926")
        ok(f"{br}, BTC: listed as “BTC/USD”; no hold limit stated in its Terms and 1-Step pages (read {br_tc_date})",
           f"{br} lists BTC as “BTC/USD”" in t and f"Hold limit at {br}: none stated in its Terms and Conditions and 1-Step pages (read {br_tc_date})" in t, t)
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
        pg.evaluate("DESK2.use('2692.58','ETH')")
        ok("more than 25% away is cleared too", pg.input_value("#stop") == "")
        pg.select_option("#side", "-1")
        pg.fill("#stop", "2800")
        pg.evaluate("DESK2.use('2692.58','ETH')")
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

        # 4b. the price on the chip belongs to the asset in the field, whatever happened before (the owner's Android test,
        # 2026-09-25: a tapped NVDA left BTC in the field, and "use" would have put BTC's price in an Nvidia trade)
        ctx, pg, errs = page()
        bad = {}
        def look(when):
            c = chip_bad(pg)
            if c:
                bad[when] = c
        look("first view")
        for sym in pg.eval_on_selector_all("#asset option", "e=>e.map(x=>x.value)"):
            pg.select_option("#asset", sym)
            pg.wait_for_timeout(20)
            look(f"{sym} chosen")
            pg.evaluate("document.dispatchEvent(new Event('visibilitychange'))")      # a price update with it selected
            pg.wait_for_timeout(60)
            look(f"{sym} after a price update")
        pg.evaluate("DESK2.use('84496.41','BTC')")
        look("\"use\" from the tape's still row")
        ok("every asset, chosen and after a price update, and after \"use\": the chip shows the field's asset's own price or nothing",
           not bad and pg.input_value("#asset") == "BTC" and pg.input_value("#entry") == "84496.41", bad)
        pg.fill("#entry", "")
        pg.evaluate("document.getElementById('asset').value='ETH'")               # the field changed behind the chip's back
        pg.click("#chipb")
        pg.wait_for_timeout(40)
        ok("a chip drawn for another asset than the field's fills nothing, and is redrawn for the field's",
           pg.input_value("#entry") == "" and chip_bad(pg) is None and pg.evaluate(CHIP)["sym"] == "ETH", pg.evaluate(CHIP))
        pg.evaluate("DESK2.use('84496.41')")
        pg.evaluate("DESK2.use('84496.41','NVDA')")
        ok("a price without its asset, or with one the desk doesn't list, fills nothing", pg.input_value("#entry") == "" and pg.input_value("#asset") == "ETH")
        ok("no page error", not errs, errs)
        ctx.close()

        # 5. a tapped tape symbol: TradingView adds its own parameters after #desk
        TV = "&utm_source=troid.ai&utm_medium=widget&utm_campaign=ticker-tape"
        MISS = EN["desk2.js.tape_miss"]
        for q, want_asset, chip, note in [
                ("BINANCEUS:ETHUSDT", "ETH", "ETH selected · live 2,692.58 · use", None),
                ("OANDA:XAUUSD", "XAU", None, None),
                ("OANDA:WTICOUSD", "WTI", None, None),
                ("NASDAQ:NVDA", "NVDA", None, EN["desk2.js.tape_only"].format(sym="NVDA")),
                ("NASDAQ:NOPE", "BTC", None, MISS),
                ("{symbolname}", "BTC", None, MISS),                            # a placeholder the widget never filled
                ("%7Bsymbolname%7D#desk?tvwidgetsymbol=BINANCEUS%3AXRPUSDT", "XRP", "XRP selected · live 1.5385 · use", None)]:  # the real symbol after the #
            ctx, pg, errs = page(f"{DESK}?tvwidgetsymbol={q}" + ("" if "#" in q else f"#desk{TV}"), w=390, is_mobile=True, has_touch=True)
            t = pg.inner_text("#assetnote").strip()
            got = pg.evaluate("""()=>{const r=e=>{const b=e.getBoundingClientRect();return b.top>=0&&b.bottom<=innerHeight};
              return {asset:document.getElementById('asset').value,entry:document.getElementById('entry').value,shared:document.getElementById('shared').hidden,
                opt:document.getElementById('asset').selectedOptions[0].textContent,res:document.getElementById('result').innerText,
                chip:document.getElementById('chipb').hidden?null:document.getElementById('chipb').innerText,chipm:document.getElementById('chipm').hidden?null:document.getElementById('chipm').innerText,
                lit:document.querySelector('#asset').closest('.fi').classList.contains('on'),inview:r(document.getElementById('asset')),noteview:r(document.getElementById('assetnote')),
                addr:location.pathname+location.search+location.hash,sideways:document.documentElement.scrollWidth-innerWidth}}""")
            label = f"a tape tap on {q}"
            ok(f"{label}: asset {want_asset}, nothing filled, no shared-link notice, a clean address; the chip, if any, is {want_asset}'s price",
               got["asset"] == want_asset and got["entry"] == "" and got["shared"] and got["addr"] == DESK + "#desk" and not errs and chip_bad(pg) is None,
               (got, errs, chip_bad(pg)))
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
            elif want_asset in UNI["not_listed"]:
                opt, none = EN["desk2.js.tape_opt"].format(sym=want_asset), EN["desk2.js.tape_none"].format(sym=want_asset)
                ok(f"{label}: the field shows \"{opt}\", in view and lit", got["opt"] == opt and got["inview"] and got["lit"] and got["noteview"]
                   and pg.evaluate("document.querySelectorAll('#asset option[data-tape]').length") == 1 and not got["sideways"], got)
                shown_lab = pg.evaluate("""()=>{const l=document.querySelector('#asset').closest('.fi').querySelector('.aopt'),r=l.getBoundingClientRect(),
                  a=document.getElementById('asset').getBoundingClientRect(),cs=getComputedStyle(l);
                  return {text:l.textContent,lines:Math.round(r.height/parseFloat(cs.lineHeight)),fits:l.scrollWidth<=l.clientWidth,
                    top:document.elementFromPoint(r.left+r.width/2,r.top+r.height/2).id,same:[a.left,a.top,a.width,a.height].join()==[r.left,r.top,r.width,r.height].join()}}""")
                ok(f"{label}: on a phone the whole label shows, wrapped, and a tap on it reaches the Asset field itself",
                   shown_lab["text"] == opt and shown_lab["fits"] and shown_lab["top"] == "asset" and shown_lab["same"], shown_lab)
                ok(f"{label}: no chip, no line about another asset: the tape note alone by the field", got["chip"] is None and got["chipm"] is None and t == note, (t, got))
                ok(f"{label}: the readout says \"{none}\"", got["res"].startswith(none) and not pg.evaluate("document.querySelector('#result .verdict,#result .read,.lad,.feebar')"), got["res"][:200])
                trade(pg, "180", "170")
                ok(f"{label}: an entry and a stop typed in size nothing; the readout still says so", pg.inner_text("#result").startswith(none)
                   and not pg.evaluate("document.querySelector('#result .verdict,#result .read,.lad,.feebar')") and chip_bad(pg) is None
                   and pg.evaluate("document.getElementById('gauge').className") == "gauge sEMPTY", pg.inner_text("#result")[:200])
                pg.select_option("#asset", "SOL")
                pg.wait_for_timeout(40)
                ok(f"{label}: choosing SOL removes the temporary option and restores the desk: SOL's lines, its price, the trade sized",
                   not pg.evaluate("document.querySelector('#asset option[data-tape],.aopt,.fi.tape')") and "lists SOL" in pg.inner_text("#assetnote")
                   and want_asset not in pg.inner_text("#assetnote") and pg.inner_text("#chipb") == "live 117.47 · use" and chip_bad(pg) is None
                   and pg.inner_text("#result .verdict").startswith(("OK", "REDUCE")), pg.inner_text("#assetnote"))
            elif note:
                ok(f"{label}: \"{note}…\", in view", note in t and got["noteview"] and MISS not in t, (t, got))
            ctx.close()
        # a tapped stock, then the tape's still row: "use" brings the price with its own asset and the stock leaves the field
        ctx, pg, errs = page(f"{DESK}?tvwidgetsymbol=NASDAQ%3AAAPL#desk", w=390, is_mobile=True, has_touch=True)
        pg.evaluate("DESK2.use('2692.58','ETH')")
        ok("after a tapped AAPL, \"use\" on ETH's price: ETH in the field, the temporary option gone, the chip ETH's",
           pg.input_value("#asset") == "ETH" and pg.input_value("#entry") == "2692.58" and not pg.evaluate("document.querySelector('#asset option[data-tape]')")
           and chip_bad(pg) is None and not pg.evaluate("document.getElementById('chipb').hidden") and not errs, (pg.evaluate(CHIP), errs))
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
                res[form] = pg.evaluate("""()=>({asset:document.getElementById('asset').value,note:document.getElementById('assetnote').innerText.trim(),
                  opt:document.getElementById('asset').selectedOptions[0].textContent,res:document.getElementById('result').innerText.slice(0,200),
                  chip:document.getElementById('chipb').hidden?null:document.getElementById('chipb').innerText,
                  chipm:document.getElementById('chipm').hidden?null:document.getElementById('chipm').innerText,
                  shared:document.getElementById('shared').hidden,addr:location.pathname+location.search+location.hash})""")
                res[form]["errs"], res[form]["chip_bad"] = errs, chip_bad(pg)
                ctx.close()
            def good(g):
                if g["errs"] or MISS in g["note"] or not g["shared"] or g["addr"] != "/#desk" or g["chip_bad"]:
                    return False
                if sym not in listed:           # the stock in the field, no chip, the tape note alone, nothing to size it against
                    return (g["asset"] == sym and g["opt"] == EN["desk2.js.tape_opt"].format(sym=sym) and g["chip"] is None and g["chipm"] is None
                            and g["note"] == EN["desk2.js.tape_only"].format(sym=sym) and g["res"].startswith(EN["desk2.js.tape_none"].format(sym=sym)))
                if sym in ("XAU", "WTI"):
                    return g["asset"] == sym and g["chipm"] == EN["desk2.js.chip_no_fill"].format(asset=EN[f"ticker.sym.{sym}"])
                return g["asset"] == sym and (g["chip"] or "").startswith(f"{sym} selected · live")
            what = ("selected" if sym in listed else
                    f"in the field as \"{EN['desk2.js.tape_opt'].format(sym=sym)}\", no chip, no other asset's lines, nothing to size it against")
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
        ok("the ladder: the readout's breakers in order, the stop first; a long's liquidation under cross past 100%: none above zero",
           bool(lad) and lad[0][0] == "lr first" and "off" in lad[-1][0] and lad[-1][2] == EN["index.js.v_liq_none"]
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
        # 9. the calculator audit's cases (29 Sep 2026) as regressions, each read from the page: the verdict, its sentence, the
        # notes, the working table, the readout, the ladder and the step cards
        ctx, pg, errs = page()
        READ = """()=>{const r=document.getElementById('result');return {
          v:(r.querySelector('.verdict')||{className:''}).className.replace('verdict ',''),sent:(r.querySelector('.vsent')||{}).textContent||'',
          notes:[...r.querySelectorAll('.notes > div')].map(d=>d.textContent),brk:(r.querySelector('.brk')||{}).textContent||'',
          rows:Object.fromEntries([...r.querySelectorAll('details.work tr')].map(t=>{const c=[...t.children].map(d=>d.textContent);return [c[0],c.slice(1)]})),
          cells:Object.fromEntries([...r.querySelectorAll('.cell')].map(c=>[c.querySelector('.k').textContent,c.querySelector('.v').textContent])),
          lad:[...document.querySelectorAll('.lad .lr .lv')].map(e=>e.textContent),prov:(r.querySelector('.prov')||{}).textContent||'',
          liqline:!document.getElementById('gx-liq').parentNode.hidden,
          cards:['st-account','st-trade','st-risk'].filter(i=>document.getElementById(i).classList.contains('err'))}}"""

        def desk(firm="bitfunded", prod="1step", side="1", mode="cross", **v):
            pg.select_option("#firm", firm)
            pg.select_option("#profile", prod)
            vals = dict(quota=100000, equity=100000, daystart=100000, hwm="", hirollover="", entry="", stop="", targetR=2, riskPct=0.5, capPct=35, lev=5)
            vals.update(v)
            pg.evaluate("""([v,side,mode])=>{for(const k in v)document.getElementById(k).value=v[k];document.getElementById('side').value=side;
              document.getElementById('mode').value=mode;document.getElementById('quota').dispatchEvent(new Event('input'))}""",
                        [{k: str(x) for k, x in vals.items()}, side, mode])
            pg.wait_for_timeout(30)
            return pg.evaluate(READ)
        E = EN.get
        CHECK, LOSS, QTY, LIQ = E("index.js.st_margin_check"), E("index.js.st_loss"), E("index.js.st_qty"), E("index.js.br_liq")
        NONE = E("index.js.v_liq_none")

        # F1: a margin above equity is cut to what equity carries at this leverage, never "Fits"
        r = desk(entry=60000, stop=59990)
        rw = r["rows"]
        ok("F1: Bitfunded 1-Step, $100,000, long 60,000, stop 59,990 at 5×: REDUCE; quantity 100,000 × 5 ÷ 60,000; margin within equity",
           r["v"] == "vREDUCE" and rw[QTY] == [E("index.js.f_qty_margin"), "8.333333"] and usd(rw["margin"][1]) <= 100000
           and usd(r["cells"]["margin"]) <= 100000, r)
        ok("F1: the margin check shows the risk-based size's margin above equity, and the sentence says the margin cut it",
           rw[CHECK][0] == E("index.js.f_margin_cut").format(lev=5) and usd(rw[CHECK][1]) > 100000
           and r["sent"] == E("index.js.vs_margin").format(lev=5, max="$500,000.00", risk=rw[LOSS][1]) and r["cells"]["risk"] == rw[LOSS][1], r)
        r = desk(entry=77872, stop=74814)
        ok("F1: a trade whose margin fits: OK, the margin check says so", r["v"] == "vOK" and r["rows"][CHECK][0] == E("index.js.f_margin_fits")
           and r["rows"][CHECK][1] == r["rows"]["margin"][1] and r["rows"][QTY][0] == E("index.js.f_qty"), r["rows"].get(CHECK))

        # F2: out of range is BLOCK, naming the field, and its step card is flagged
        attrs = pg.evaluate("()=>Object.fromEntries(['quota','equity','daystart','entry','stop','riskPct','capPct','lev'].map(i=>{const e=document.getElementById(i);return [i,[e.min,e.max]]}))")
        ok("F2: the fields carry the bounds: quota, equity, day start, entry, stop min 0; risk % and budget cap % 0 to 100; leverage min 1",
           attrs == {"quota": ["0", ""], "equity": ["0", ""], "daystart": ["0", ""], "entry": ["0", ""], "stop": ["0", ""], "riskPct": ["0", "100"],
                     "capPct": ["0", "100"], "lev": ["1", ""]}, attrs)
        # the account's fields with a day start below equity, so that no budget is spent and only the range check can flag
        # the account card; for them the whole sentence, so a false "already breached" beside it fails (the review,
        # 2026-09-30). An entry or a stop out of range keeps the trade's other reasons (a stop now above entry)
        for fid, bad, key, lab, card in [("riskPct", -1, "b_pct", "risk_pct", "st-risk"), ("capPct", 150, "b_pct", "cap_pct", "st-risk"),
                                         ("lev", 0, "b_lev", "leverage", "st-risk"), ("quota", 0, "b_gt0", "quota", "st-account"),
                                         ("equity", 0, "b_gt0", "equity", "st-account"), ("daystart", "", "b_gt0", "daystart", "st-account"),
                                         ("entry", 0, "b_gt0", "entry", "st-trade"), ("stop", -5, "b_gt0", "stop", "st-trade")]:
            reason = E("index.js." + key).format(field=E("index.calc." + lab))
            r = desk(**dict({"entry": 77872, "stop": 74814, "daystart": 99000}, **{fid: bad}))
            ok(f"F2: {E('index.calc.' + lab)} {bad if bad != '' else 'blank'}: BLOCK, exactly \"{reason}\", the {card[3:]} card flagged, no link",
               r["v"] == "vBLOCK" and (r["sent"] == E("index.js.vs_block").format(reasons=reason) if card == "st-account" else reason in r["sent"])
               and reason in r["notes"] and r["cards"] == [card]
               and not r["cells"] and not pg.query_selector("#result [data-copy-link]"), r)
        r = desk(quota=-100000)
        g = pg.evaluate("document.getElementById('gauge').getAttribute('aria-label')")
        ok("F2: a refused quota computes no floor: none in the working table or on the gauge (the review, 2026-09-30)",
           r["v"] == "vBLOCK" and E("index.js.daily_floor") not in r["rows"] and E("index.js.dd_floor") not in r["rows"]
           and "floor" not in g and not r["prov"], (g, r["rows"]))
        r = desk(riskPct=-1)
        ok("F2: before an entry is typed too", r["v"] == "vBLOCK" and r["sent"] == E("index.js.vs_block").format(
            reasons=E("index.js.b_pct").format(field=E("index.calc.risk_pct"))) and r["cards"] == ["st-risk"], r)
        r = desk(entry=77872, stop=74814)
        ok("F2: back in range, the desk sizes again and no card is flagged", r["v"] == "vOK" and not r["cards"], r["cards"])

        # F3: a pending drawdown type with a known max is sized against the static floor, the loosest reading. The
        # handoff's case is at a 100% cap, whose risk would take the whole $100 of room: since the review (2026-09-30)
        # that is refused (the cap case below), so the sizing is read at 50%
        m = FIRMS["crypto_fund_trader"]["products"]["instant"]["max_pct"]
        loosest = E("index.js.f_dd_loosest").format(m=f"{m:g}")
        r = desk(firm="crypto_fund_trader", prod="instant", quota=10000, equity=9500, daystart=9500, riskPct=2, capPct=100, entry=77872, stop=74814)
        ok(f"F3: CFT Instant, $10,000, equity and day start $9,500, 2% at a 100% cap: the {m:g}% max loss's floor at $9,400 binds, room $100, "
           "and a risk of the whole room is refused",
           r["rows"]["max-loss floor"] == [loosest, "$9,400.00"] and r["rows"]["binding"][1].endswith("$100.00") and r["v"] == "vBLOCK", r)
        r = desk(firm="crypto_fund_trader", prod="instant", quota=10000, equity=9500, daystart=9500, riskPct=2, capPct=50, entry=77872, stop=74814)
        how, gfloor = pg.inner_text("#xs"), pg.text_content("#gx-floor")
        ok("F3: at a 50% cap the risk is $50, the note says which reading it is, and so do the explainer and the floor's note; "
           "the explainer shows no crossover for a pending type (the review, 2026-09-30)",
           r["rows"]["max-loss floor"] == [loosest, "$9,400.00"] and r["cells"]["risk"] == "$50.00"
           and E("index.js.n_dd_loosest").format(m=f"{m:g}") in r["notes"] and E("index.js.n_dd_pending") not in r["notes"]
           and E("index.js.u_dd") not in r["prov"] and loosest in how and loosest in gfloor
           and E("desk2.js.x3_pending").split("{product}")[1] in how
           and E("desk2.js.x3_none").split("{product}")[1] not in how, (how, gfloor, r))

        # F4: a high-water mark or a high at rollover below what the account has reached is raised, and says so
        r = desk(firm="brightfunded", prod="1step", equity=103000, daystart=103000, hwm=100000)
        ok("F4: BrightFunded trails on equity: a high-water mark of 100,000 with equity 103,000 is raised to 103,000, the trailing floor 97,000",
           r["rows"]["high-water mark"][1] == "$103,000.00" and r["rows"]["max-loss floor"][1] == "$97,000.00"
           and E("index.js.n_hwm_raised_equity").format(typed="$100,000.00", hwm="$103,000.00") in r["notes"], r)
        r = desk(firm="brightfunded", prod="1step", equity=95500, daystart=95500, hwm=95000)
        ok("F4: a high-water mark of 95,000 is raised to the quota: the floor 94,000, not 89,000",
           r["rows"]["high-water mark"][1] == "$100,000.00" and r["rows"]["max-loss floor"][1] == "$94,000.00"
           and E("index.js.n_hwm_raised").format(typed="$95,000.00", hwm="$100,000.00") in r["notes"], r)
        r = desk(firm="brightfunded", prod="1step", hirollover=99000)
        ok("F4: a high at rollover of 99,000 below the day start is raised to it: the daily floor 97,000",
           r["rows"]["high at rollover"][1] == "$100,000.00" and r["rows"]["daily floor"][1] == "$97,000.00"
           and E("index.js.n_hi_raised").format(typed="$99,000.00", hi="$100,000.00") in r["notes"], r)
        r = desk(firm="brightfunded", prod="1step", equity=103000, daystart=103000, hwm=104000)
        ok("F4: one above both stays as typed, with no note", r["rows"]["high-water mark"][1] == "$104,000.00"
           and not any("raised" in x for x in r["notes"]), r["notes"])

        # F5: a long can't fall more than 100%
        cross, iso = E("index.js.cross"), E("index.js.isolated")
        r = desk(entry=77872, stop=74814)
        ok("F5: a cross long past 100%: \"none above zero\" in the working table, the breakers and the ladder; no live line",
           r["rows"][LIQ.format(mode=cross)][1] == NONE and r["brk"].endswith(NONE) and r["lad"][-1] == NONE and not r["liqline"], r)
        r = desk(entry=77872, stop=74814, lev=1, mode="isolated")
        ok("F5: isolated at 1× (100.00% before): none above zero, and the note says the position's own margin covers a fall to zero",
           r["rows"][LIQ.format(mode=iso)][1] == NONE and r["lad"][-1] == NONE and E("index.js.n_isolated_none").format(lev=1) in r["notes"], r)
        r = desk(side="-1", entry=77872, stop=85659.2)
        v = r["rows"][LIQ.format(mode=cross)][1]
        ok("F5: a short's liquidation past 100% is shown as computed", v.endswith("%") and float(v.rstrip("%").replace(",", "")) > 100
           and NONE not in r["brk"] and r["lad"][-1] == E("desk2.js.l_off").format(pct=v) and r["liqline"], (v, r["lad"]))

        # F6: the exit fee on the exit price: the loss at the stop is the risk to the cent, long or short
        for side, pct in [("1", 1), ("-1", 1), ("1", 0.2), ("-1", 0.2)]:
            e = 77872
            st = round(e * (1 - int(side) * pct / 100), 6)
            r = desk(side=side, entry=e, stop=st)
            fu = f"{0.0004 * (e + st):,.6f}".rstrip("0").rstrip(".")
            ok(f"F6: a {'long' if side == '1' else 'short'} with a {pct:g}% stop: fee per unit (entry + stop) × 0.04% = {fu}; the loss at the stop, "
               "$500.00, is the risk", r["rows"]["fee per unit"] == [E("index.js.f_fpu").format(fee="0.04"), fu]
               and r["rows"][LOSS] == [E("index.js.f_loss"), "$500.00"] and r["rows"]["risk"][1] == "$500.00" and r["cells"]["risk"] == "$500.00", r["rows"])

        # F7: losses that leave equity above the floor
        r = desk(entry=77872, stop=74814, riskPct=5, capPct=25)
        ok("F7: a 25% cap makes the risk a quarter of the room ($1,000 of $4,000): 3 losses left, not 4 (the 4th reaches the limit)",
           r["rows"]["risk"][1] == "$1,000.00" and r["rows"]["losses left"] == [E("index.js.f_left"), "3"]
           and E("index.js.n_left").format(n="3", bind=E("index.js.bind_daily")) in r["notes"], r["rows"].get("losses left"))

        # no leverage class recorded at this size: held to the lowest recorded cap, and says so
        low = min(b["lev"] for b in FIRMS["crypto_fund_trader"]["calc"]["lev_bands"])
        r = desk(firm="crypto_fund_trader", prod="1phase", quota=30000, equity=30000, daystart=30000, lev=200, entry=77872, stop=74814)
        ok(f"CFT 1-Phase, $30,000 at 200×: no class recorded at this size, so leverage is held to {low}×, the lowest cap the firm records",
           r["rows"]["leverage used"] == [E("index.js.f_lev_pending_held").format(lev=low), f"{low}×"]
           and E("index.js.n_lev_held").format(lev=low) in r["notes"] and r["cells"]["margin"] == r["rows"]["margin"][1], r)
        # the review's cases (2026-09-30), each read from the page. A margin cut: the explainer shows the cut, never "the
        # loss is the same either way", and every figure called the trade's risk is the loss its cell shows
        r = desk(entry=60000, stop=59990)
        loss, how = r["rows"][LOSS][1], pg.inner_text("#xs")
        gr = pg.text_content("#gx-risk")
        ok("F1 in the explainer: the margin set the size, the loss at the stop is the verdict's, no \"either way\"",
           E("desk2.js.x6_code").rsplit("}", 1)[1].strip() not in how and E("desk2.js.x6_h_cut") in how and loss in how
           and r["rows"][CHECK][1] in how and "8.333333" in how and loss in r["sent"], how)
        ok("F1: the risk note ends on the loss, and the provenance gives the margin's formula",
           gr == E("index.js.gx_risk_cut").format(intended="$500.00", cap="$1,400.00", rb="$500.00", lev=5, risk=loss)
           and E("index.js.f_margin_cut").format(lev=5) in r["prov"], (gr, r["prov"]))
        ok("the leverage note says the loss is unchanged only while the margin fits", E("glossary.leverage.what") in pg.text_content("#g-leverage")
           and "margin fits" in E("glossary.leverage.what"))
        r = desk(entry=60000, stop=59990, riskPct=2, capPct=25)
        loss, gr = r["rows"][LOSS][1], pg.text_content("#gx-risk")
        ok("both cuts at once (budget cap, then margin): the note and the risk note end on the loss the verdict states",
           E("index.js.n_cut_margin").format(**{"from": "$2,000.00", "to": "$1,000.00", "bind": E("index.js.bind_daily"), "loss": loss}) in r["notes"]
           and not any(x == E("index.js.n_cut").format(**{"from": "$2,000.00", "to": "$1,000.00", "bind": E("index.js.bind_daily")}) for x in r["notes"])
           and gr.endswith(loss + ".") and loss in r["sent"] and r["cells"]["risk"] == loss, (r["notes"], gr))
        # a 100% cap whose risk takes the whole room: the loss would land on the floor, which F7 counts as a breach
        r = desk(entry=60000, stop=59000, riskPct=5, capPct=100)
        ok("a 100% cap with the whole room at risk: BLOCK, the reason names the limit and the cap, the risk card flagged, the link kept",
           r["v"] == "vBLOCK" and r["sent"] == E("index.js.vs_block").format(reasons=E("index.js.b_reaches").format(bind=E("index.js.bind_daily")))
           and r["cards"] == ["st-risk"] and not r["cells"] and pg.query_selector("#result [data-copy-link]") is not None, r)
        r = desk(entry=60000, stop=59000, riskPct=5, capPct=99)
        ok("at 99% it sizes, one loss left", r["v"] == "vREDUCE" and r["rows"]["losses left"][1] == "1" and not r["cards"], r["rows"].get("losses left"))
        # a long's floor more than 100% below entry isn't reached above zero; a short's is shown as computed
        FN, DDD = E("index.js.v_floor_none"), E("index.js.st_dd_dist")
        r = desk(entry=60000, stop=54000)
        fl_hidden = pg.evaluate("document.getElementById('gx-floor').parentNode.hidden")
        ok("a long's max-loss floor 120.91% below entry: \"not reached above zero\" in the table, the breakers and the ladder; its live line hidden; "
           "the daily limit's 80.61% as computed", r["rows"][DDD][1] == FN and FN in r["brk"] and FN in r["lad"] and fl_hidden
           and r["rows"][E("index.js.st_daily_dist")][1] == "80.61%", (r["rows"].get(DDD), r["brk"], r["lad"]))
        r = desk(side="-1", entry=60000, stop=66000)
        v = r["rows"][DDD][1]
        ok("a short's floor distance past 100% is shown as computed", v.endswith("%") and float(v.rstrip("%").replace(",", "")) > 100 and FN not in r["brk"], v)
        ok("no page error in the audit's cases", not errs, errs)
        ctx.close()
        # a tapped stock no firm lists, with a field out of range: the readout stays, the reason is named, the gauge blocks
        ctx, pg, errs = page(f"{DESK}?tvwidgetsymbol=NASDAQ:NVDA#desk")
        pg.fill("#riskPct", "-1")
        pg.wait_for_timeout(40)
        res, reason = pg.inner_text("#result"), E("index.js.b_pct").format(field=E("index.calc.risk_pct"))
        ok("a tapped NVDA with Risk % −1: \"No compared firm offers NVDA…\", then the reason; the gauge's BLOCK line",
           res.startswith(E("desk2.js.tape_none").format(sym="NVDA")) and reason in res
           and pg.evaluate("document.getElementById('gauge').className") == "gauge sBLOCK" and not errs, (res[:300], errs))
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
