#!/usr/bin/env python3
"""Self-funded scaling: start with one funded account, reinvest payouts into more
challenges, reach a target monthly income. Monte Carlo over pass-rate luck.

Challenge fee $799 ($100k Expert). Payout split 80%. Funded accounts can also die.
"""
import random, statistics

FEE = 999.0    # 1-Step Expert. The 2-Step Expert is $799.
SPLIT = 0.80

def run(p_pass, gross_per_acct, target_net, months=24, p_acct_death=0.0,
        start_funded=1, n=20000, seed=11):
    rng = random.Random(seed)
    times, spent_l, stalled = [], [], 0
    for _ in range(n):
        funded = start_funded
        cash = 0.0
        pending = []            # challenges in flight (resolve next month)
        spent = 0.0
        hit = None
        for m in range(1, months + 1):
            # resolve challenges bought last month
            for _ in pending:
                if rng.random() < p_pass:
                    funded += 1
            pending = []
            # funded accounts earn, and can blow
            alive = 0
            for _ in range(funded):
                if rng.random() < p_acct_death:
                    continue
                alive += 1
            funded = alive
            income = funded * gross_per_acct * SPLIT
            cash += income
            if funded * gross_per_acct * SPLIT >= target_net and hit is None:
                hit = m
                break
            # reinvest everything spare into challenges
            buy = int(cash // FEE)
            if buy:
                cash -= buy * FEE; spent += buy * FEE; pending = [1] * buy
        times.append(hit if hit else months + 1)
        spent_l.append(spent)
        if hit is None: stalled += 1
    reached = [t for t in times if t <= months]
    return (len(reached) / n, statistics.median(reached) if reached else None,
            statistics.median(spent_l))

if __name__ == "__main__":
    target = 5000.0
    print(f"Target ${target:,.0f}/month net, ${FEE:,.0f} per challenge, {SPLIT:.0%} split")
    print("Starting from ONE funded account, reinvesting all payouts.\n")
    print(f"{'edge':>8} {'gross/acct/mo':>14} {'pass rate':>10} {'reach in 24mo':>14} {'median months':>14} {'median spent':>13}")
    print("-" * 78)
    for label, gross in [("+0.05R", 507), ("+0.15R", 1862), ("+0.35R", 5342)]:
        for p in (0.14, 0.35, 0.50):
            ok, med, spent = run(p, gross, target)
            print(f"{label:>8} {'$'+format(gross,','):>14} {p:>9.0%} {ok:>13.0%} "
                  f"{(str(med)+' mo') if med else '—':>14} {'$'+format(spent,',.0f'):>13}")
    print("\nCost to ACQUIRE one funded account = fee / pass rate:")
    for p in (0.14, 0.35, 0.50):
        print(f"   pass {p:.0%}  ->  ${FEE/p:,.0f} expected, {1/p:.1f} attempts")
