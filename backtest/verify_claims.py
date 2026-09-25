#!/usr/bin/env python3
"""Accuracy ledger: re-derive every claim from first principles, independently of
the code that produced it, and classify what troid is entitled to say about each.

Confidence tiers used throughout:
  DERIVED  - follows algebraically from the firm's published rules. Certain.
  SOURCED  - from Bitfunded docs or published industry data. Cite it.
  MEASURED - from troid's backtest on one asset, one regime. Hypothesis only.
  MODELLED - Monte Carlo under assumptions. Conditional on those assumptions.

Anything MEASURED must not be stated as fact in user-facing material.
"""
import math, statistics, random

FAIL = []
def check(tier, claim, got, want, tol=1e-6, unit=""):
    ok = abs(got - want) <= tol * max(1.0, abs(want))
    if not ok: FAIL.append(claim)
    print(f"  [{tier:8}] {'OK ' if ok else 'FAIL'}  {claim}")
    print(f"             derived {got:,.4f}{unit}   published {want:,.4f}{unit}")

print("="*76)
print("  1. RISK MODEL - derivable from the rules alone")
print("="*76)

Q, DAILY, MAXLOSS, FEE, LEV = 100_000.0, 0.04, 0.06, 0.0004, 5

# Crossover: the equity where daily budget == drawdown budget, on a fresh day.
#   Bitfunded FAQ: the daily limit is FIXED at d*Q from the initial balance.
#   daily_budget = dQ + (E - day_start) = dQ on a fresh day
#   dd_budget    = E - Q(1-m)
#   dQ = E - Q(1-m)  ->  E = Q(1 - m + d)
floor = Q*(1-MAXLOSS)
crossover = floor + Q*DAILY
check("DERIVED", "1-Step crossover equity", crossover, 98000.0, 1e-9, "")
check("DERIVED", "room below start before max loss binds", Q-crossover, 2000.0)
check("DERIVED", "room = (max% - daily%) x quota", (MAXLOSS-DAILY)*Q, 2000.0)

for nm,d,m,pub in [("2-Step S1",0.05,0.10,95000.0),("2-Step S2",0.05,0.08,97000.0),
                   ("Express",0.03,0.03,100000.0),("Instant",0.03,0.06,97000.0)]:
    check("DERIVED", f"{nm} crossover", Q*(1-m+d), pub)
print("             -> Express: crossover IS the starting balance. Both ceilings bind from $1 lost.")

# Three daily bases are now on the compare page. On a fresh day (E = day start = high):
#   initial (Bitfunded):      daily floor = D - dQ        -> crossover E = Q(1 - m + d)     (above)
#   day_start (CFT):          daily floor = D(1 - d)      -> E d = E - F  ->  E = F / (1 - d)
#   max_balance_equity (BF):  daily floor = H - dQ        -> with H = E, same crossover as initial
# Trailing drawdown: budget at a fresh high-water mark = HWM m; once locked at initial, budget = E - Q.
print()
check("DERIVED", "day-start basis crossover, 4%/6% static floor (CFT 2-Phase shape)", Q*(1-0.06)/(1-0.04), 97916.6667, 1e-4)
check("DERIVED", "max-balance/equity basis, fresh day, 3% (BF 1-Step) daily budget", Q*0.03, 3000.0)
check("DERIVED", "trailing 6% budget at a fresh $100,000 high-water mark", 100000*0.06, 6000.0)
check("DERIVED", "trailing 6% budget at a $104,000 high-water mark, equity at the high", 104000 - 104000*(1-0.06), 6240.0)
check("DERIVED", "budget once the floor locks at initial (+6% reached), equity $106,000", 106000 - Q, 6000.0)
print("             -> $97,917 is the day-start-basis number. It was wrong for Bitfunded and right for a day-start firm.")

# Fee share of risk. Sizing solves risk = qty*(stop_dist + entry*fee*2), so
#   fees/risk = (entry*2f) / (stop_dist + entry*2f) = 2f / (s + 2f), s = stop as a fraction
print()
for s, pub in [(0.039, 2.01), (0.015, 5.06), (0.003, 21.05)]:
    share = 2*FEE/(s + 2*FEE)*100
    check("DERIVED", f"fee share of risk at a {s*100:.1f}% stop", share, pub, 5e-3, "%")

# Leverage independence: risk depends only on stop distance x quantity.
print()
entry, stop, risk = 78000.0, 74814.0, 500.0
qty = risk/abs(entry-stop)
for lev in (2,5,25):
    loss = abs(entry-stop)*qty
    check("DERIVED", f"loss at stop with {lev}x leverage", loss, 500.0, 1e-9, "")
print("             -> leverage changes margin and liquidation distance, never the loss")

# Liquidation distance approximation
print()
for lev, pub in [(5, 20.0), (25, 4.0)]:
    check("DERIVED", f"approx liquidation distance at {lev}x", (1/lev)*100, pub, 1e-9, "%")

print()
print("="*76)
print("  2. LADDER GEOMETRY - derivable, and it contradicts the usual intuition")
print("="*76)
# Five strength tranches, shared risk, stop anchored at T1 structure.
R, d, a, step = 500.0, 3000.0, 2000.0, 0.5
single = R/d
strength = sum((R/5)/(d + j*step*a) for j in range(5))
check("DERIVED", "single-entry quantity", single, 0.1666667, 1e-5)
check("DERIVED", "5x strength ladder quantity", strength, 0.1092866, 1e-5)
check("DERIVED", "ladder size vs single entry", (strength/single-1)*100, -34.4280, 1e-3, "%")
print("             -> scaling in REDUCES size at fixed risk. Benefit is conditionality.")

print()
print("="*76)
print("  3. SURVIVABILITY - derivable from the cap")
print("="*76)
# Under a cap of c x remaining budget, budget after n losses = B(1-c)^n. Never zero.
c = 0.35
for n in (1,3,5,10):
    print(f"  [DERIVED ] after {n:>2} consecutive losses, {(1-c)**n*100:>5.1f}% of budget remains")
print("             -> ruin is unreachable by realized losses under a proportional cap.")
print("             -> the real failure mode is a stalled account, not a blown one.")

# The published ruin figures (landing page, FAQ, dashboard, README, RESULTS.md, the MCP server), re-simulated with
# income_math.py under the assumptions the landing page states beside them: 45% won at 2:1 (+0.35R), 30 trades a
# month, 12 months, 20,000 paths, seed 7, a 4% daily limit fixed on the initial balance, a 6% static floor, the cap
# at 35% of the remaining budget. The 2% figure was published as 98% until 2026-09-24: that is what the model gave
# under the day-start daily basis it carried before the FAQ correction; under the corrected basis it is 100%.
import income_math as _IM
for _rp, _cap, _pub in [(0.01, False, 68.0), (0.02, False, 100.0), (0.01, True, 0.0), (0.02, True, 0.0)]:
    _pr = _IM.simulate(0.45, 2.0, _rp, 30, 12, capped=_cap)[0] * 100
    check("MODELLED", f"P(ruin) in a year at {_rp:.0%} risk, {'capped' if _cap else 'no cap'}, +0.35R, 30 trades/mo",
          round(_pr), _pub, 0, "%")

# Uncapped: fixed fraction f of quota, floor at m. Ruin after ceil(m/f) losses.
print()
for f, pub in [(0.005,12),(0.01,6),(0.02,3),(0.025,2)]:
    n = math.floor(MAXLOSS/f)
    print(f"  [DERIVED ] uncapped {f*100:>4.1f}% risk: {n:>2} consecutive losses reach the floor"
          f"   (published {pub})")

print()
print("="*76)
print("  4. INCOME ARITHMETIC - derivable")
print("="*76)
for split, pub in [(0.80, 6250.0), (0.90, 5555.5556)]:
    check("DERIVED", f"gross needed for $5,000 net at {split:.0%} split", 5000/split, pub, 1e-4)
check("DERIVED", "monthly target as % of a $100k account", 6250/Q*100, 6.25, 1e-9, "%")
check("DERIVED", "target vs total 6% buffer", 6250/(Q*MAXLOSS), 1.0417, 1e-3, "x")
# R needed = target / (risk_dollars * trades)
for tpm, rp, pub in [(7,0.005,1.7857),(30,0.005,0.4167),(30,0.02,0.1042)]:
    check("DERIVED", f"R/trade needed at {tpm} trades/mo, {rp*100:.1f}% risk",
          6250/(rp*Q)/tpm, pub, 1e-3, "R")
# Seven-account ceiling
caps = [5000,10000,15000,25000,50000,100000,150000]
check("DERIVED", "max capital, one account per level", sum(caps), 355000.0)
check("DERIVED", "aggregate monthly return needed on $355k", 6250/sum(caps)*100, 1.7606, 1e-3, "%")

print()
print("="*76)
print("  5. BACKTEST STATISTICS - the limits of what troid may claim")
print("="*76)
# Re-derived from the PUBLIC JOURNAL, not from the engine. Only the frozen sample counts:
# rows that closed on or before the last bar of data/btc_4h.csv. Rows the daily shadow
# appends after that are the live tail and are excluded, so this measures the published
# sample and fails if journal.csv or the published figures drift from each other.
import csv, pathlib
FROZEN_END = "2026-09-21T12:00:00+00:00"                     # last bar of data/btc_4h.csv
PUB_N, PUB_MEAN, PUB_SD = 78, 0.0335, 0.4029                # STRATEGY.md "What it measured"
PUB_PF, PUB_WIN = 1.29, 32.0
BARS, WARM = 1539, 127                                     # sample length, indicator warm-up
rows = [r for r in csv.DictReader(open(pathlib.Path(__file__).with_name("journal.csv")))
        if r["exit_utc"] <= FROZEN_END]
rs = [float(r["r"]) for r in rows]; pnl = [float(r["pnl"]) for r in rows]
n, mean, sd = len(rs), statistics.mean(rs), statistics.stdev(rs)
gw, gl = sum(x for x in pnl if x > 0), -sum(x for x in pnl if x < 0)
check("MEASURED", "trades in the frozen sample (journal.csv)", n, PUB_N, 0)
check("MEASURED", "mean R per trade", mean, PUB_MEAN, 5e-4, "R")
check("MEASURED", "sd of R per trade", sd, PUB_SD, 5e-4, "R")
check("MEASURED", "profit factor", gw/gl, PUB_PF, 5e-3)
check("MEASURED", "win rate", 100*sum(1 for x in pnl if x > 0)/n, PUB_WIN, 0.5, "%")
flagged = sum(1 for r in rows if int(r.get("filled_bars") or 0) > 0)
print(f"  [MEASURED] {flagged} of {n} trades held through a forward-filled bar (flagged in the journal, not excluded)")
se = sd/math.sqrt(n)
check("DERIVED", "standard error of the mean", se, 0.0456, 1e-3, "R")
check("DERIVED", "t statistic", mean/se, 0.7351, 1e-2)
lo, hi = mean-1.96*se, mean+1.96*se
print(f"  [DERIVED ] 95% CI [{lo:+.3f}R, {hi:+.3f}R] -> contains zero: {lo < 0 < hi}")
# Expected maximum of k independent draws from N(0, se): se * E[max of k standard normals], integrated
# (noise_math.py). The asymptotic se*sqrt(2 ln k) overstated it: +0.119R for k = 30, where it is +0.093R.
from noise_math import expected_max_normal
for k in (10, 30, 52):
    print(f"  [DERIVED ] best of {k:>2} configs under a TRUE zero edge: "
          f"~+{se*expected_max_normal(k):.3f}R by chance alone ({expected_max_normal(k):.4f} SE)")
check("DERIVED", "expected best of 30 independent configs under a zero edge, in SE", expected_max_normal(30), 2.0428, 1e-4)
print(f"             -> troid's best ({mean:+.3f}R) is {'BELOW' if mean < se*expected_max_normal(30) else 'ABOVE'} the best-of-30 noise threshold.")
print(f"             -> claimable: nothing. This is a hypothesis for out-of-sample testing.")

# Frequency, and what the income target would need at it
MONTHS = (BARS-WARM)*4/24/30.44; TPM = n/MONTHS
check("MEASURED", "trades per month on the frozen sample", TPM, 10.1, 5e-2)
print(f"  [DERIVED ] at {TPM:.1f} trades/mo and 0.5% risk, $6,250/mo gross needs {6250/(0.005*Q)/TPM:+.2f}R per trade")

# The holdout, and the shrinkage from it. walkforward.py wrote results/walkforward_BTCUSDT.json
# from the same config on 2021-2026; the config was chosen on 2026, so 2021-2025 is holdout.
import json
wf = json.load(open(pathlib.Path(__file__).parent / "results" / "walkforward_BTCUSDT.json"))
h = wf["holdout"]
check("MEASURED", "holdout trades, BTC 2021-2025 (walkforward_BTCUSDT.json)", h["n"], 504, 0)
check("MEASURED", "holdout mean R per trade", h["exp"], 0.0084, 5e-4, "R")
check("DERIVED", "holdout standard error", h["sd"]/math.sqrt(h["n"]), 0.0161, 5e-4, "R")
check("DERIVED", "in-sample -> holdout shrinkage", (1 - h["exp"]/mean)*100, 75.0, 0.5, "%")
check("DERIVED", "holdout expectancy in dollars per month at $500 risk", h["exp"]*500*h["n"]/h["months"], 35.0, 0.05)
print(f"             -> +{mean:.3f}R on the {n} trades the parameters were chosen against became "
      f"+{h['exp']:.3f}R on the {h['n']} they never saw. Multiple comparisons, measured.")

# Weekly reporting resolution
print()
for per, k in [("week", TPM/4.33), ("month", TPM), ("year", TPM*12)]:
    k = max(k, 1)
    print(f"  [DERIVED ] a {per:<6} of trades (n={k:>5.1f}) has SE {sd/math.sqrt(k):>5.3f}R"
          f"  -> {'meaningless' if sd/math.sqrt(k) > 0.15 else 'marginal'}")

print()
print("="*76)
print("  6. SOURCED CLAIMS - cite, never re-derive")
print("="*76)
for claim, src in [
    ("~14% reach a funded account; ~7% ever get paid", "source not yet recorded: attributed to FPFX Technology aggregate data (300k+ accounts); no document or read date in the repo"),
    ("~70% of failures are loss-limit breaches", "source not yet recorded: no document or read date in the repo; published with that label"),
    ("average 3 attempts, $1,600+ in fees per $100k", "source not yet recorded: no document or read date in the repo"),
    ("0.04% fee per side on notional", "Bitfunded help centre"),
    ("reset 00:00 UTC+8, effective between 00:00 and 00:10 UTC+8 (16:00-16:10 UTC)", "Bitfunded help centre, Criteria to be Success"),
    ("max loss is STATIC, measured from account quota", "Bitfunded help centre"),
    ("min 5 trading days (site displays 0)", "Bitfunded ToU 9(a) - contract governs"),
    ("10 calendar day max position hold (help centre RTP s.1 tiers it 10/7/5; stricter governs)", "Bitfunded ToU 14(d)(x)"),
    ("one active account per challenge level", "Bitfunded ToU 6(b)"),
    ("marketed strategies prohibited", "Bitfunded ToU 14(d)(v)"),
    ("no switching strategies between assessment and funded accounts", "Bitfunded ToU 14(d)(ix)"),
    ("no opposite positions across connected accounts", "Bitfunded ToU 13(c)(v)"),
    ("5 open positions (ToU 14(d)(xi) still says 10, revised 2026-03-24)", "Bitfunded help centre, RTP s.3"),
    ("Trader Stage limits by path: 4/6, 3/3, 5/8, Instant 3/6; breach disqualifies", "Bitfunded help centre, Challenge & Trader Stage"),
    ("refund: 100% at first profit split day, all levels (Terms) vs 2-Step only, 3rd withdrawal (help centre)", "Bitfunded ToU 9(a)/9(b) vs help centre - CONFLICTS"),
    ("no excluded-country list; trader must comply with local law", "Bitfunded ToU 4(b)"),
    ("affiliate 15% (intro) vs 12% (section b)", "Bitfunded AP Policy - CONTRADICTS ITSELF"),
]:
    print(f"  [SOURCED ] {claim}\n             source: {src}")

print()
print("="*76)
print("  7. SITE TEXT - the verbatim disclosures, everywhere they are published")
print("="*76)
# The 4.41 text and the footer line live once, in site_text.py. Every copy must match it byte for byte,
# and the terms page's out-of-sample figures must match the walk-forward output. Drift fails here.
import html as _html, json as _json, pathlib as _pl, sys as _sys
_ROOT = _pl.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT / "backtest"))
import site_text as _T
def _read(rel): return (_ROOT / rel).read_text()
for rel in ("README.md", "backtest/STRATEGY.md", "backtest/WALKFORWARD.md"):
    check("SOURCED", f"17 CFR 4.41(b)(1)(i) verbatim in {rel}", float(_T.HYPO in _read(rel)), 1.0)
for rel in ("web/public/terms.html", "web/public/ledger.html", "web/public/tearsheet.html", "web/public/dashboard.html"):
    check("SOURCED", f"17 CFR 4.41(b)(1)(i) verbatim in {rel}", float(_T.HYPO in _html.unescape(_read(rel))), 1.0)
for page in sorted((_ROOT / "web" / "public").glob("*.html")):
    check("DERIVED", f"footer line on {page.name}", float(_T.FOOTER_TEXT in _html.unescape(page.read_text())), 1.0)
for rel in ("METHODOLOGY.md", "web/public/METHODOLOGY.md", "TROID.md", "web/public/TROID.md"):
    check("DERIVED", f"footer line in {rel}", float(_T.FOOTER_TEXT in _read(rel)), 1.0)
_terms = _html.unescape(_read("web/public/terms.html"))
for sym in ("BTCUSDT", "ETHUSDT"):
    _h = _json.loads(_read(f"backtest/results/walkforward_{sym}.json"))["holdout"]
    check("MEASURED", f"terms section 6 quotes the {sym} holdout n ({_h['n']} trades)", float(f"({_h['n']} trades)" in _terms), 1.0)
    check("MEASURED", f"terms section 6 quotes the {sym} holdout mean ({_h['exp']:+.3f}R)", float(f"{_h['exp']:+.3f}R" in _terms), 1.0)

# ---------------------------------------------------------------------------------------------------------
# 8. Translations (HANDOFF-global-launch). Translation may change words, never figures. Every live language's
# strings meet the contract against en.json (i18n.check_pair: same figures, placeholders, tags and links; troid
# lowercase in Latin script; no exclamation mark; product names in their fixed form), and every published page
# in that language shows the same figures as its English page, apart from the lines only a translated page
# carries (the summary and governing lines before English legal text).
import re as _re
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parent))
import i18n as _i18n
_ROOT = _pl.Path(__file__).resolve().parent.parent


def _page_text(text):
    text = _re.sub(r"(?s)<script.*?</script>|<style.*?</style>|<head>.*?</head>", " ", text)
    text = _re.sub(r'(?s)<span class="gov-(sum|line)">.*?</span>|<p class="governs">.*?</p>|<span class="langs".*?</span>', " ", text)
    return _re.sub(r"<[^>]+>", " ", text)


_live = [c for c in _i18n.live_codes() if c != "en"]
if not _live:
    print("  translations: no language is live yet; English only")
for _c in _live:
    _p = _i18n.check_language(_c)
    check("DERIVED", f"{_c}: every string meets the translation contract ({len(_p)} problem(s))", float(len(_p)), 0.0, 0)
    for _page in ("index", "compare", "ledger", "dashboard", "chat", "faq", "terms"):
        _tp = _ROOT / "web" / "public" / _c / f"{_page}.html"
        _ep = _ROOT / "web" / "public" / f"{_page}.html"
        if _tp.exists() and _ep.exists():
            # the same figures; a month the English names may appear as its number (2026 年 9 月 23 日)
            check("DERIVED", f"{_c}/{_page}: the same figures as the English page",
                  float(_i18n.figures_match(_page_text(_ep.read_text()), _page_text(_tp.read_text()))), 1.0)


# 9. ask troid's conversation record (launch handoff §1). The disclosure is one sentence set in three places, and
# the retention facts must read the same on every surface that states them.
print()
print("="*76)
print("  9. ask troid - the disclosure and the 30-day record, everywhere they are stated")
print("="*76)
_js = (_ROOT / "web" / "api" / "troid.js").read_text()
_disc = _re.search(r'const DISCLOSURE = "(.*?)";', _js).group(1)
_ret = _re.search(r"const RETENTION_S = ([0-9_]+);", _js).group(1).replace("_", "")
check("SOURCED", "store TTL in troid.js is 30 days (2,592,000 s)", float(_ret == "2592000"), 1.0)
_en = _json.loads((_ROOT / "web" / "i18n" / "en.json").read_text())
check("DERIVED", "disclosure: troid.js = en.json ask.disclosure", float(_en["ask.disclosure"] == _disc), 1.0)
_sup = " ".join(l[2:] for l in (_ROOT / "web" / "context" / "support.md").read_text().splitlines() if l.startswith("> "))
check("DERIVED", "disclosure: quoted verbatim in support.md", float(_disc in _sup), 1.0)
check("DERIVED", "disclosure states the 30 days and the session ID", float("kept for 30 days under the session ID" in _disc), 1.0)
_sec10 = _html.unescape(_re.search(r'<section id="ask-troid">(.*?)</section>', _read("web/public/terms.html"), _re.S).group(1))
for _fact in ("for 30 days after its last message", "deletes it automatically", "does not keep your IP address",
              "Only the Operator can read", "never sells conversations", "never uses them for marketing or to train any AI model",
              "delete this conversation", "hello@troid.ai", "which questions come up most", "no quotation and no session ID",
              "does not publish them"):
    check("DERIVED", f"terms section 10 says: {_fact}", float(_fact in _sec10), 1.0)
_faq = _html.unescape(_read("web/public/faq.html"))
check("DERIVED", "FAQ answers 'Does troid keep my conversation with ask troid?'",
      float(_en["faq.keep.q"] in _faq and "30 days" in _faq and "never used for marketing or to train an AI model" in _faq), 1.0)
check("DERIVED", "chat page states the 30-day record", float("30 days after its last message" in _html.unescape(_read("web/public/chat.html"))), 1.0)
check("DERIVED", "disclosure states the weekly topic counts, never quoted", float("counts which topics come up most, never quoting them" in _disc), 1.0)
check("DERIVED", "FAQ states the fourth purpose", float("which questions\ncome up most" in _en["faq.keep.p"] and "never quoting a message" in _en["faq.keep.p"]), 1.0)
check("DERIVED", "chat page states the weekly topic counts", float("counts which topics come up most, never quoting anyone" in " ".join(_html.unescape(_read("web/public/chat.html")).split())), 1.0)
_terms_all = _html.unescape(_read("web/public/terms.html"))
check("SOURCED", "terms section 1 names the operator: Kunjan Patel (owner decision 2026-09-24)", float("troid is operated by Kunjan Patel (“the Operator”)" in _terms_all and "Company" not in _terms_all), 1.0)
for page in sorted((_ROOT / "web" / "public").glob("*.html")):
    check("DERIVED", f"footer carries © 2026 Kunjan Patel on {page.name}", float("© 2026 Kunjan Patel" in _html.unescape(page.read_text())), 1.0)


# 10. What troid.ai serves (HANDOFF-2026-09-24 section 1): every figure on the landing page and in the FAQ carries its
# tier; the compare page's claims about troid's own verification are generated, not written.
print()
print("="*76)
print("  10. troid.ai - tiers beside the figures; generated claims on troid's compare")
print("="*76)
_index = " ".join(_html.unescape(_read("web/public/index.html")).split())
_faqs = " ".join(_faq.split())
check("DERIVED", "landing: the ~70% tile says SOURCED, source not yet recorded", float(_en["index.stats.failures.prov"] in _index and _en["index.stats.failures.prov"].startswith("SOURCED · source not yet recorded")), 1.0)
check("DERIVED", "FAQ: the 70% says SOURCED, source not yet recorded", float(" ".join(_html.unescape(_en["faq.fail.src"]).split()) in _faqs), 1.0)
check("DERIVED", "FAQ: the 14% / 7% say SOURCED, source not yet recorded", float(" ".join(_html.unescape(_en["faq.pass.src"]).split()) in _faqs and _en["faq.pass.src"].startswith("SOURCED · source not yet recorded")), 1.0)
check("DERIVED", "FAQ: the $1,600 says SOURCED, source not yet recorded", float(" ".join(_html.unescape(_en["faq.cost.src"]).split()) in _faqs), 1.0)
check("DERIVED", "research page: the 14% base rate carries its tier", float("14% industry base rate (SOURCED, source not yet recorded)" in " ".join(_html.unescape(_read("web/public/dashboard.html")).split())), 1.0)
check("DERIVED", "landing: the 68% tile says MODELLED with its assumptions and the script", float(all(x in _index for x in ("MODELLED. 20,000 simulated years", "+0.35R a trade", "30 trades a month for 12 months", "1% of balance risked a trade with no cap on remaining budget", "income_math.py"))), 1.0)
check("DERIVED", "FAQ: the ruin figures say MODELLED and name the script", float("MODELLED: 20,000 simulated years" in _faqs and "income_math.py" in _faqs), 1.0)
check("DERIVED", "no page still publishes the pre-correction 98%", float(not any("98%" in _html.unescape(pg.read_text()) for pg in (_ROOT / "web" / "public").glob("*.html"))), 1.0)
import gen_compare as _GC
_cmp = " ".join(_html.unescape(_read("web/public/compare.html")).split())
_ref = _GC.reference()
_nconf = len(_ref.get("_conflicts_found") or [])
check("DERIVED", f"compare: 'reviewed' is the latest read date in firms.json ({_GC.last_read()})", float(f"reviewed {_GC.last_read()}" in _cmp), 1.0)
check("DERIVED", f"compare: the conflict count is the log's length ({_nconf})", float(f"found and logged {_nconf} conflicts" in _cmp and f"disagree · {_nconf} logged" in _cmp), 1.0)
check("DERIVED", "compare: every logged conflict is printed with each side's document", float(all(" ".join(_html.unescape(s["doc"]).split()) in _cmp for c in _ref["_conflicts_found"] for s in c["sides"])), 1.0)
for _pg in ("compare", "index"):
    _t = _html.unescape(_read(f"web/public/{_pg}.html"))
    check("DERIVED", f"{_pg}: no 'most completely', no internal field name", float("most completely" not in _t and "link_live" not in _t), 1.0)
check("DERIVED", "landing: 'the challenge types on troid's compare', not 'every challenge type'", float("challenge types on troid's compare" in _index and "every challenge type" not in _index), 1.0)
_panel = _read("web/public/index.html").split("<!-- firms:start -->")[1].split("<!-- firms:end -->")[0]
for _k in _GC.ORDER:
    _f = _GC.FIRMS[_k]; _p = _f["compare_product"]
    _n = sum(1 for x in _GC.FIELDS if _p.get(x) is not None); _m = sum(1 for x in _GC.FIELDS if _GC.sourced(_f, x, _p))
    check("DERIVED", f"landing panel: {_f['name']} shows '{_n} of {len(_GC.FIELDS)} rules filled · {_m} sourced'", float(f"{_n} of {len(_GC.FIELDS)} rules filled · {_m} sourced" in _panel), 1.0)
_P1 = _GC.FIRMS["bitfunded"]["provenance"]
for _pk, _x in [(p, x) for p in ("1step", "2step_s1", "2step_s2") for x in ("daily_pct", "max_pct", "target_pct", "max_leverage")]:
    _c = _GC.cite(_GC.FIRMS["bitfunded"], _x, _pk)
    check("SOURCED", f"Bitfunded {_pk} {_x}: Challenge & Trader Stage and Terms 9(a), not Criteria to be Success",
          float(bool(_c) and "Challenge & Trader Stage" in _c["c"] and "9(a)" in _c["c"] and "Criteria" not in _c["c"]), 1.0)
for _pg in ("compare", "ledger", "faq", "dashboard", "chat", "terms", "tearsheet"):
    _t = _read(f"web/public/{_pg}.html")
    check("DERIVED", f"{_pg}: previews as itself (its own og:title)", float(f'<meta property="og:title" content="{_html.escape(_en[_pg + ".og.title"], quote=True).replace("&#x27;", chr(39))}">' in _t), 1.0)

# 11. troid's character (TROID-CHARACTER.md): every figure its worked examples state, re-derived. Its method says
# "check it"; the examples are held to the same rule.
print()
print("="*76)
print("  11. troid's character - the worked examples reproduce")
print("="*76)
_ch = " ".join(_read("TROID-CHARACTER.md").split())
_one_r = (77872 - 76580) * 0.3862
check("DERIVED", "example R: 1R = 1,292 x 0.3862 is about $499", _one_r, 498.97, 1e-4, "")
check("DERIVED", "example R: $998 is +2R", 998 / _one_r, 2.0, 1e-3, "R")
check("DERIVED", "example R: the round-trip fee at 0.04% a side is about $24, the desk's 1R about $523", _one_r + 77872 * 0.0004 * 2 * 0.3862, 523.03, 1e-4, "")
check("DERIVED", "example R: eight $500 losses use up Bitfunded 1-Step's $4,000 daily limit", 0.04 * 100_000 / 500, 8.0, 0)
_kelly = 0.45 - 0.55 / 2
check("DERIVED", "example Kelly: p = 0.45, b = 2 gives 17.5%", _kelly * 100, 17.5, 1e-9, "%")
check("DERIVED", "example Kelly: a full-Kelly loss is nearly three times the 6% maximum loss", _kelly / 0.06, 2.9167, 1e-3, "x")
check("DERIVED", "example Kelly: half-Kelly (8.75%) is over the 6% maximum loss in one trade", float(_kelly / 2 > 0.06), 1.0)
check("DERIVED", "example recovery: down 20% needs 25%", 0.2 / 0.8 * 100, 25.0, 1e-9, "%")
check("DERIVED", "example recovery: down 50% needs 100%", 0.5 / 0.5 * 100, 100.0, 1e-9, "%")
_maxes = [p.get("max_pct") for f in _GC.FIRMS.values() if isinstance(f, dict) for p in (f.get("products") or {}).values() if isinstance(p, dict) and p.get("max_pct") is not None]
check("SOURCED", "example recovery: the largest maximum loss troid has read is 10%", max(_maxes), 10.0, 0, "%")
for _t in ("1R = 1,292 × 0.3862 ≈ $499", "about $24", "about $523", "($4,000 ÷ $500)", "f* = 0.45 − 0.55/2 = 0.175", "Half-Kelly is 8.75%",
           "nearly three times", "25% of $80,000", "At 50% down the recovery is 100%", "the largest troid has read is 10%"):
    check("DERIVED", f"TROID-CHARACTER.md states it: {_t}", float(_t in _ch), 1.0)

# the price tape (ticker v3): terms and FAQ say TradingView sees the visitor's connection; every page's strip names the
# sources it was built from (the still row's label, /api/ticker's source; the tape's symbols, firms.json _ticker_universe)
_terms_txt = " ".join(_re.sub(r"<[^>]+>", "", _terms_all).split())
check("DERIVED", "terms 2: the TradingView sentence and its privacy link", float(
    "The price ticker is embedded from TradingView. Your browser connects to TradingView's servers to load it; TradingView's own "
    "privacy policy applies to that connection." in _terms_txt and 'href="https://www.tradingview.com/privacy-policy/"' in _terms_all), 1.0)
check("DERIVED", "FAQ: 'Does troid track me?' names TradingView and its privacy policy",
      float("Does troid track me?" in _faq and "TradingView's privacy policy" in " ".join(_faq.split())), 1.0)
import site_build as _SB
_tv = [s["tv"] for g in _SB.TAPE["groups"] for s in g["symbols"]]
for _pg in [p for p in _SB.PAGES if p != "tearsheet"]:
    _raw = _read(f"web/public/{_pg}.html")
    _h, _m = _html.unescape(_raw), _re.search(r'data-tv="([^"]*)"', _raw)
    _cfg = _json.loads(_html.unescape(_m.group(1))) if _m else {}
    check("DERIVED", f"{_pg}: the tape carries _ticker_universe's symbols in order; the still row names {_SB.TICKER_SOURCE}; TradingView credited",
          float(bool(_m) and [x["proName"] for x in _cfg.get("symbols", [])] == _tv and f'data-source="{_SB.TICKER_SOURCE}"' in _raw
                and f"· {_SB.TICKER_SOURCE} ·" in _h and "Track all markets on TradingView" in _h), 1.0)

# glossary v2: every figure in the desk's glossary examples, reproduced from the desk's own formula and the reference
# firm's recorded rules (its compare product: Bitfunded 1-Step), then found on the desk as published
_gi = _html.unescape(_read("web/public/index.html"))
_rf = _GC.reference()
_cp = _rf["compare_product"]
_Q, _E0, _EN_, _ST, _TR, _RP, _CP = 100_000, 100_000, 77_872, 74_814, 2, 0.5, 35
_dist = _EN_ - _ST
_room = _Q * _cp["daily_pct"] / 100                        # initial-balance daily limit, from a fresh day start
_risk = _E0 * _RP / 100
_notional = _risk / (_dist + _EN_ * _cp["fee_per_side_pct"] / 100 * 2) * _EN_
_mmr = 0.005
_liq = (_E0 / _notional - _mmr) / (1 - _mmr) * 100
for _lab, _v, _want, _txt in [
        ("stop 77,872 − 74,814", _dist, 3058, "3,058"),
        ("target 77,872 + 2 × 3,058", _EN_ + _TR * _dist, 83988, "83,988"),
        ("risk 0.5% of 100,000", _risk, 500, "$500"),
        (f"room: {_rf['name']} {_cp['label']} {_cp['daily_pct']:g}% daily limit on 100,000", _room, 4000, "$4,000"),
        ("budget cap 35% of $4,000", _room * _CP / 100, 1400, "$1,400"),
        (f"notional: $500 ÷ (3,058 + 77,872 × {_cp['fee_per_side_pct']:g}% × 2) × 77,872", round(_notional), 12478, "$12,478"),
        (f"margin at {_cp['max_leverage']:g}× (the firm's cap)", round(_notional / _cp["max_leverage"]), 2496, "$2,496"),
        ("margin at 2×", round(_notional / 2), 6239, "$6,239"),
        ("equity 101,200 − 300", 101_200 - 300, 100900, "equity 100,900"),
        ("day start: the last day's close with nothing open", 101_200 - 300, 100900, "day start 100,900"),
        ("high at rollover max(100,900, 101,300)", max(100_900, 101_300), 101300, "→ 101,300"),
        ("high-water mark after 104,000 then 102,500", max(104_000, 102_500), 104000, "still 104,000")]:
    check("DERIVED", f"glossary example: {_lab} = {_want:,} and the desk says so", float(_v == _want and _txt in _gi), 1.0)
check("DERIVED", f"glossary example: under cross at {_cp['max_leverage']:g}×, the daily limit ({_room / _notional * 100:.2f}% away) comes long before "
      f"liquidation ({_liq:.0f}% away)", float(_room / _notional * 100 < _liq / 10), 1.0)
_tgt = _GC.cite(_rf, "target_pct", _cp["key"])
check("SOURCED", f"glossary example: {_rf['name']} \"{_cp['label']}\" has a {_cp['target_pct']:g}% target, read {max(_tgt['o'])}",
      float(f"{_rf['name']} \"{_cp['label']}\" is a single phase with a {_cp['target_pct']:g}% target (read {max(_tgt['o'])})" in _gi), 1.0)
check("DERIVED", "glossary: every field label and readout figure on the desk opens a note that exists", float(all(
    f'id="g-{t}"' in _read("web/public/index.html") for t in _re.findall(r'data-tip="g-([a-z_]+)"', _read("web/public/index.html") + _read("web/templates/index.html")))), 1.0)

print()
print("="*76)
print(f"  RESULT: {len(FAIL)} failed check(s)" + (f" -> {FAIL}" if FAIL else " - all derivations reproduce"))
print("="*76)
print("""
PUBLISHING RULES THIS IMPLIES

  DERIVED  -> state as fact, show the algebra. A reader can check it in a spreadsheet.
  SOURCED  -> state with the citation and the section number. Link it.
  MODELLED -> state the assumptions in the same sentence as the number.
  MEASURED -> do NOT state as fact. "On one 8-month sample troid measured X, which is
              inside noise" is honest. "troid's strategy returns X" is not.

  And per ToU 14(d)(v), entry logic cannot be marketed at all. Everything above that is
  safe to publish is on the risk side, which is also everything above that is DERIVED.
  The two constraints point the same way.
""")
