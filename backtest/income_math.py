#!/usr/bin/env python3
"""What does $X/month actually require on a Bitfunded funded account, and what
does it cost in ruin probability?

Three parts:
  1. Deterministic: the expectancy x frequency x risk surface that hits the target.
  2. Monte Carlo: probability of hitting the static floor, under the real rules.
  3. The frontier: expected income vs P(ruin) per risk level, and accounts needed.

Rules modelled: daily loss 4% of day-start balance, static max loss 6% of quota,
both on realized + floating; fees 0.04%/side are assumed already inside the R
multiples (the backtest measures them that way).

  python income_math.py --target 5000 --split 0.80
"""
from __future__ import annotations
import argparse, random, statistics

QUOTA = 100_000.0
DAILY_PCT, MAXLOSS_PCT = 0.04, 0.06
BUDGET_CAP = 0.35


# ----------------------------------------------------------- part 1: the surface

def required_expectancy(target_gross, risk_pct, trades_per_month, balance=QUOTA):
    """R per trade needed to earn target_gross in a month."""
    risk_dollars = risk_pct * balance
    r_needed = target_gross / risk_dollars
    return r_needed / trades_per_month, risk_dollars


def surface(target_gross):
    print(f"\nR-per-trade required for ${target_gross:,.0f}/month gross on ${QUOTA:,.0f}")
    print("(a strong discretionary system runs +0.10 to +0.30R; above +0.50R is"
          " not credible on any sustained sample)\n")
    freqs = [7, 15, 30, 60, 120]
    risks = [0.005, 0.0075, 0.01, 0.015, 0.02]
    print(f"{'risk/trade':>12} │" + "".join(f"{f:>9}/mo" for f in freqs))
    print(" " * 13 + "┼" + "─" * (11 * len(freqs)))
    for rp in risks:
        row = f"{rp*100:>10.2f}% │"
        for f in freqs:
            r, _ = required_expectancy(target_gross, rp, f)
            mark = "  " if r <= 0.30 else ("* " if r <= 0.50 else "! ")
            row += f"{r:>8.2f}R{mark}"
        print(row)
    print("\n  blank = plausible    * = very aggressive    ! = not credible")


# ------------------------------------------------- part 2: Monte Carlo the rules

def simulate(win_rate, payoff, risk_pct, trades_per_month, months,
             capped=True, withdraw=True, n_paths=20_000, seed=7):
    """Return (p_ruin, median_income, p_any_losing_month, median_worst_dd)."""
    rng = random.Random(seed)
    floor = QUOTA * (1 - MAXLOSS_PCT)
    tpd = max(trades_per_month / 21.0, 0.01)
    ruins = 0; incomes = []; worst_dds = []; losing_months = 0
    for _ in range(n_paths):
        bal = QUOTA
        total_withdrawn = 0.0
        peak = bal
        worst = 0.0
        dead = False
        for m in range(months):
            month_start = bal
            day_start = bal
            realized_today = 0.0
            day_frac = 0.0
            for t in range(int(trades_per_month)):
                day_frac += 1.0 / tpd
                if day_frac >= 1.0:                       # new trading day
                    day_frac = 0.0
                    day_start = bal
                    realized_today = 0.0
                daily_limit = QUOTA * DAILY_PCT        # fixed from initial (Bitfunded FAQ)
                eff = min(daily_limit + realized_today, bal - floor)
                if eff <= 0:
                    dead = True; break
                intended = risk_pct * bal
                risk = min(intended, BUDGET_CAP * eff) if capped else intended
                if risk <= 0:
                    dead = True; break
                won = rng.random() < win_rate
                pnl = risk * payoff if won else -risk
                bal += pnl
                realized_today += pnl
                if -realized_today >= daily_limit or bal <= floor:
                    dead = True; break
                peak = max(peak, bal)
                worst = min(worst, bal - peak)
            if dead:
                break
            if bal < month_start:
                losing_months += 1
            if withdraw and bal > QUOTA:                  # pay out, reset the base
                total_withdrawn += bal - QUOTA
                bal = QUOTA
        if dead:
            ruins += 1
        # when banking rather than withdrawing, income is equity growth over the run,
        # otherwise the comparison reports $0 by construction
        earned = total_withdrawn if withdraw else max(bal - QUOTA, 0.0)
        incomes.append(earned / max(months, 1))
        worst_dds.append(worst)
    return (ruins / n_paths,
            statistics.median(incomes),
            losing_months / (n_paths * months),
            statistics.median(worst_dds))


def frontier(win_rate, payoff, trades_per_month, months, target_net, split):
    exp_r = win_rate * payoff - (1 - win_rate)
    target_gross = target_net / split
    print(f"\nEdge assumed: {win_rate:.0%} win, {payoff:.2f}:1 payoff  =>  "
          f"{exp_r:+.3f}R per trade, {trades_per_month} trades/month, {months} months")
    print(f"Target: ${target_net:,.0f}/month net at a {split:.0%} split "
          f"= ${target_gross:,.0f} gross\n")
    print(f"{'risk':>6} {'sizing':>8} {'P(ruin)':>9} {'med income/mo':>15} "
          f"{'accounts':>9} {'losing mo':>10}")
    print("─" * 62)
    for rp in (0.0025, 0.005, 0.0075, 0.01, 0.015, 0.02, 0.025):
        for capped in (True, False):
            p_ruin, med, p_lose, _ = simulate(win_rate, payoff, rp,
                                              trades_per_month, months, capped=capped)
            acc = ("—" if med <= 0 else f"{target_gross / med:,.1f}")
            print(f"{rp*100:>5.2f}% {'capped' if capped else 'naive':>8} "
                  f"{p_ruin:>8.1%} {'$'+format(med, ',.0f'):>15} {acc:>9} {p_lose:>9.0%}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=float, default=5000, help="net income per month")
    ap.add_argument("--split", type=float, default=0.80, help="trader's profit share")
    ap.add_argument("--win", type=float, default=0.35)
    ap.add_argument("--payoff", type=float, default=2.0, help="avg win / avg loss in R")
    ap.add_argument("--trades", type=int, default=30, help="trades per month")
    ap.add_argument("--months", type=int, default=12)
    a = ap.parse_args()

    gross = a.target / a.split
    print("=" * 62)
    print(f"  ${a.target:,.0f}/month net  =  ${gross:,.0f}/month gross at "
          f"{a.split:.0%}  =  {gross/QUOTA:.2%} of a ${QUOTA:,.0f} account")
    print(f"  Monthly target vs total drawdown buffer: ${gross:,.0f} vs "
          f"${QUOTA*MAXLOSS_PCT:,.0f}  =  {gross/(QUOTA*MAXLOSS_PCT):.2f}x")
    print("=" * 62)
    surface(gross)
    frontier(a.win, a.payoff, a.trades, a.months, a.target, a.split)


if __name__ == "__main__":
    main()
