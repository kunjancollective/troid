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
# Expected maximum of k independent draws from N(0, se) ~ se*sqrt(2 ln k)
for k in (10, 30, 52):
    print(f"  [DERIVED ] best of {k:>2} configs under a TRUE zero edge: "
          f"~+{se*math.sqrt(2*math.log(k)):.3f}R by chance alone")
print(f"             -> troid's best ({mean:+.3f}R) is {'BELOW' if mean < se*math.sqrt(2*math.log(30)) else 'ABOVE'} the best-of-30 noise threshold.")
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
    ("~14% reach a funded account; ~7% ever get paid", "FPFX Technology, 300k+ accounts"),
    ("~70% of failures are loss-limit breaches", "aggregated firm disclosures"),
    ("average 3 attempts, $1,600+ in fees per $100k", "published industry analysis"),
    ("0.04% fee per side on notional", "Bitfunded help centre"),
    ("reset 00:00 UTC+8, may apply until 00:10", "Bitfunded help centre"),
    ("max loss is STATIC, measured from account quota", "Bitfunded help centre"),
    ("min 5 trading days (site displays 0)", "Bitfunded ToU 9(a) - contract governs"),
    ("10 calendar day max position hold", "Bitfunded ToU 14(d)(x)"),
    ("one active account per challenge level", "Bitfunded ToU 6(b)"),
    ("marketed strategies prohibited", "Bitfunded ToU 14(d)(v)"),
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
