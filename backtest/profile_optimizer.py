#!/usr/bin/env python3
"""Optimal risk per challenge profile.

One strategy. Three rule sets. The entry logic is rule-agnostic - what changes is
how hard you can push before the constraint structure kills you. This finds the
risk level that maximises P(pass) for an assumed edge, per profile.

Not a strategy fit. A sizing schedule derived from known constraints.
"""
import random, statistics

PROFILES = [("1-Step",        0.04, 0.06, 0.10, 999),
            ("2-Step Stage 1",0.05, 0.10, 0.08, 799),
            ("2-Step Stage 2",0.05, 0.08, 0.05,   0),
            ("Express",       0.03, 0.03, 0.03,   0)]
QUOTA, BUDGET_CAP, MIN_DAYS = 100_000.0, 0.35, 5

def sim(win, payoff, risk_pct, daily, maxloss, target, tpm=9, months=6,
        capped=True, n=6000, seed=3):
    rng = random.Random(seed)
    floor = QUOTA * (1 - maxloss); goal = QUOTA * (1 + target)
    out = {"pass":0,"fail":0,"run":0}; days_to_pass = []
    for _ in range(n):
        bal, day_start, realized, tdays, dead, passed = QUOTA, QUOTA, 0.0, 0, False, None
        for t in range(int(tpm*months)):
            if t % max(int(tpm/21*30.44/21),1) == 0:
                day_start, realized = bal, 0.0; tdays += 1
            dl = QUOTA*daily            # fixed from initial (Bitfunded FAQ)
            eff = min(dl+realized, bal-floor)
            if eff <= 0: dead=True; break
            r = min(risk_pct*bal, BUDGET_CAP*eff) if capped else risk_pct*bal
            if r <= 0: dead=True; break
            pnl = r*payoff if rng.random()<win else -r
            bal += pnl; realized += pnl
            if -realized >= dl or bal <= floor: dead=True; break
            if bal >= goal and tdays >= MIN_DAYS:
                passed = t/tpm*30.44; break
        if dead: out["fail"] += 1
        elif passed is not None: out["pass"] += 1; days_to_pass.append(passed)
        else: out["run"] += 1
    return (out["pass"]/n, out["fail"]/n,
            statistics.median(days_to_pass) if days_to_pass else None)

if __name__ == "__main__":
    for lbl, win, payoff in [("realistic good  +0.15R", 0.383, 2.0),
                             ("very strong     +0.35R", 0.45, 2.0)]:
        print(f"\n{'='*74}\n  {lbl}   9 trades/month, 6-month window, desk cap on\n{'='*74}")
        print(f"{'profile':<16}{'risk':>7}{'P(pass)':>9}{'P(fail)':>9}{'median days':>13}")
        for name, d, m, t, fee in PROFILES:
            best = None
            for rp in (0.005,0.0075,0.01,0.015,0.02,0.025,0.03,0.04):
                p,f,md = sim(win,payoff,rp,d,m,t)
                if best is None or p > best[1]: best = (rp,p,f,md)
                print(f"{name if rp==0.005 else '':<16}{rp*100:>6.2f}%{p:>8.1%}{f:>8.1%}"
                      f"{(f'{md:.0f}' if md else '—'):>13}")
            print(f"{'':<16}{'-> best':>7} {best[0]*100:.2f}% risk, "
                  f"{best[1]:.0%} pass, {best[2]:.0%} fail\n")
