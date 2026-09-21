#!/usr/bin/env python3
"""Accuracy ledger: re-derive every claim from first principles, independently of
the code that produced it, and classify what we're entitled to say about each.

Confidence tiers used throughout:
  DERIVED  - follows algebraically from the firm's published rules. Certain.
  SOURCED  - from Bitfunded docs or published industry data. Cite it.
  MEASURED - from our backtest on one asset, one regime. Hypothesis only.
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
for tpm, rp, pub in [(7,0.005,1.7857),(9.2,0.005,1.3587),(30,0.005,0.4167),(30,0.02,0.1042)]:
    check("DERIVED", f"R/trade needed at {tpm} trades/mo, {rp*100:.1f}% risk",
          6250/(rp*Q)/tpm, pub, 1e-3, "R")
# Seven-account ceiling
caps = [5000,10000,15000,25000,50000,100000,150000]
check("DERIVED", "max capital, one account per level", sum(caps), 355000.0)
check("DERIVED", "aggregate monthly return needed on $355k", 6250/sum(caps)*100, 1.7606, 1e-3, "%")

print()
print("="*76)
print("  5. STATISTICS OF OUR OWN BACKTEST - the limits of what we may claim")
print("="*76)
# Reproduce the significance test from the reported summary statistics.
n, mean, sd = 71, 0.038, 0.378
se = sd/math.sqrt(n)
print(f"  [MEASURED] n={n}, mean {mean:+.3f}R, sd {sd:.3f}R")
check("DERIVED", "standard error of the mean", se, 0.0449, 1e-3, "R")
check("DERIVED", "t statistic", mean/se, 0.8470, 1e-2)
lo, hi = mean-1.96*se, mean+1.96*se
print(f"  [DERIVED ] 95% CI [{lo:+.3f}R, {hi:+.3f}R] -> contains zero: {lo < 0 < hi}")
# Expected maximum of k independent draws from N(0, se) ~ se*sqrt(2 ln k)
for k in (10, 30, 52):
    print(f"  [DERIVED ] best of {k:>2} configs under a TRUE zero edge: "
          f"~+{se*math.sqrt(2*math.log(k)):.3f}R by chance alone")
print(f"             -> our best ({mean:+.3f}R) is BELOW the best-of-30 noise threshold.")
print(f"             -> claimable: nothing. This is a hypothesis for out-of-sample testing.")

# Weekly reporting resolution
print()
for per, tpm in [("week", 9.2/4.33), ("month", 9.2), ("year", 110)]:
    k = max(tpm,1)
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
print(f"  RESULT: {len(FAIL)} failed check(s)" + (f" -> {FAIL}" if FAIL else " - all derivations reproduce"))
print("="*76)
print("""
PUBLISHING RULES THIS IMPLIES

  DERIVED  -> state as fact, show the algebra. A reader can check it in a spreadsheet.
  SOURCED  -> state with the citation and the section number. Link it.
  MODELLED -> state the assumptions in the same sentence as the number.
  MEASURED -> do NOT state as fact. "On one 8-month sample we saw X, which is inside
              noise" is honest. "Our strategy returns X" is not.

  And per ToU 14(d)(v), entry logic cannot be marketed at all. Everything above that is
  safe to publish is on the risk side, which is also everything above that is DERIVED.
  The two constraints point the same way.
""")
