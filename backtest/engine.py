#!/usr/bin/env python3
"""4h pullback-continuation on BTCUSDT, backtested under Bitfunded Apex rules.

Rules modelled (the 1-Step figures from the help centre's Challenge & Trader Stage, One Step table, and
Terms of Use 9(a); the mechanics from the help centre's "Criteria to be Success"):
  - Max daily loss 4%  = realized loss today + floating loss of open positions
  - Max loss 6% STATIC = realized + floating, measured from the initial quota
  - Both auto-fail on FLOATING loss touching the line (no close required)
  - Daily reset at 00:00 UTC+8 = 16:00 UTC. Floating loss carries into the new
    day at full size; yesterday's profit does not.
  - Fees 0.04% of notional per side
  - Max leverage 5x; profit target 10% realized, flat to clear

Variants:
  intraday   - forced flat at the 16:00 UTC reset, no entries in the last bar
  swing      - hold through resets (exposed to the rollover trap)
  swing_safe - hold winners through the reset, close anything underwater

Entry at next bar's open after a signal close. Stop/target checked intrabar,
stop assumed first if both touch. Stop fills take 0.03% slippage.
"""
from __future__ import annotations
import csv, math, statistics, sys, json
from dataclasses import dataclass, field

T0, STEP = 1767844800, 14400
RESET_SEC = 16 * 3600                     # 16:00 UTC == 00:00 UTC+8
INITIAL = 100_000.0
DAILY_PCT, MAXLOSS_PCT, TARGET_PCT = 0.04, 0.06, 0.10
FEE = 0.0004
MAX_LEV = 5.0
SLIP_STOP = 0.0003
ZOMBIE_PCT = 0.01          # eff budget below this share of quota = can't fail, can't recover

# strategy parameters
EMA_FAST, EMA_TREND, ATR_N = 20, 120, 14
TREND_SLOPE_BARS = 6
PULLBACK_BARS = 3          # touch of EMA20 must be within this many bars
PULLBACK_TOL = 0.25        # in ATRs
STRUCT_BARS = 6            # bars for pullback low/high
STOP_BUF = 0.25            # ATRs beyond structure
STOP_MIN, STOP_MAX = 0.75, 1.5   # clamp stop distance, in ATRs
TARGET_R = 2.0
RISK_PCT = 0.005           # of balance
BUDGET_CAP = 0.35          # of remaining effective budget


def load_bars(path):
    """Accepts o,h,l,c rows (T0 from the constant) or t,o,h,l,c rows (T0 from the file).
    Bars must be regular 4h; fetch_binance.py forward-fills gaps to guarantee that."""
    global T0
    rows = [r for r in csv.reader(open(path)) if r and not r[0].startswith("#")]
    if len(rows[0]) == 5:
        T0 = int(float(rows[0][0]))
        ts = [int(float(r[0])) for r in rows]
        assert all(b - a == STEP for a, b in zip(ts, ts[1:])), "bars are not regular 4h"
        return [tuple(map(float, r[1:5])) for r in rows]
    return [tuple(map(float, r[:4])) for r in rows]


def indicators(bars):
    n = len(bars)
    o, h, l, c = zip(*bars)
    ema = lambda k: _ema(c, k)
    e20, e120 = ema(EMA_FAST), ema(EMA_TREND)
    tr = [h[0] - l[0]] + [max(h[i] - l[i], abs(h[i] - c[i-1]), abs(l[i] - c[i-1]))
                          for i in range(1, n)]
    atr = [None] * n
    a = sum(tr[:ATR_N]) / ATR_N
    atr[ATR_N - 1] = a
    for i in range(ATR_N, n):
        a = (a * (ATR_N - 1) + tr[i]) / ATR_N
        atr[i] = a
    return e20, e120, atr


def _ema(x, k):
    out = [None] * len(x)
    m = 2 / (k + 1)
    s = sum(x[:k]) / k
    out[k - 1] = s
    for i in range(k, len(x)):
        s = x[i] * m + s * (1 - m)
        out[i] = s
    return out


def signals(bars, e20, e120, atr):
    """Return list of (bar_index_of_signal_close, side, stop_dist) — entry at next open."""
    o, h, l, c = zip(*bars)
    out = []
    warm = EMA_TREND + TREND_SLOPE_BARS
    for i in range(warm, len(bars) - 1):
        a = atr[i]
        if a is None or a <= 0:
            continue
        up = c[i] > e120[i] and e120[i] > e120[i - TREND_SLOPE_BARS]
        dn = c[i] < e120[i] and e120[i] < e120[i - TREND_SLOPE_BARS]
        if not (up or dn):
            continue
        lo_w = min(l[i - STRUCT_BARS + 1:i + 1])
        hi_w = max(h[i - STRUCT_BARS + 1:i + 1])
        if up:
            touched = any(l[j] <= e20[j] + PULLBACK_TOL * a for j in range(i - PULLBACK_BARS + 1, i + 1))
            trigger = c[i] > h[i - 1] and c[i] > e20[i]
            if touched and trigger:
                entry = o[i + 1]
                d = entry - lo_w + STOP_BUF * a
                d = min(max(d, STOP_MIN * a), STOP_MAX * a)
                out.append((i, +1, d))
        else:
            touched = any(h[j] >= e20[j] - PULLBACK_TOL * a for j in range(i - PULLBACK_BARS + 1, i + 1))
            trigger = c[i] < l[i - 1] and c[i] < e20[i]
            if touched and trigger:
                entry = o[i + 1]
                d = hi_w - entry + STOP_BUF * a
                d = min(max(d, STOP_MIN * a), STOP_MAX * a)
                out.append((i, -1, d))
    return out


@dataclass
class Pos:
    side: int; entry: float; stop: float; target: float; qty: float; bar: int; risk: float


@dataclass
class Result:
    variant: str
    start: int
    outcome: str = "running"       # pass | fail_daily | fail_maxloss | running
    end_bar: int | None = None
    fail_note: str = ""
    balance: float = INITIAL
    peak: float = INITIAL
    trough_dd: float = 0.0
    trades: list = field(default_factory=list)   # dicts
    trading_days: set = field(default_factory=set)
    rollover_breach: bool = False


def run(bars, sigs, variant, start, stop_at=None, challenge=True):
    o, h, l, c = zip(*bars)
    sig_at = {}
    for i, side, d in sigs:
        sig_at.setdefault(i, (side, d))
    r = Result(variant, start)
    bal = INITIAL
    day_start = INITIAL
    realized_today = 0.0
    pos: Pos | None = None
    daily_limit = INITIAL * DAILY_PCT        # FIXED from initial (Bitfunded FAQ); never rebased
    floor_total = INITIAL * (1 - MAXLOSS_PCT)
    n = len(bars) if stop_at is None else stop_at

    def flt(p, price):
        return (price - p.entry) * p.qty * p.side

    def close(p, price, i, reason):
        nonlocal bal, realized_today
        pnl = flt(p, price) - p.qty * price * FEE
        bal += pnl
        realized_today += pnl
        r.trades.append(dict(side=p.side, entry=p.entry, exit=price, pnl=pnl,
                             r=pnl / p.risk, bars=i - p.bar, reason=reason, bar=i))

    for i in range(start, n):
        t = T0 + i * STEP
        is_reset = (t % 86400) == RESET_SEC

        # --- reset handling at the OPEN of the 16:00 UTC bar.
        # Order matters and is deliberate; see RESULTS.md "merged reset block".
        if is_reset:
            # 1. policy flatten. A close here is realized BEFORE the new day begins.
            if pos and variant == "intraday":
                close(pos, o[i], i, "reset_flat"); pos = None
            elif pos and variant == "swing_safe" and flt(pos, o[i]) < 0:
                close(pos, o[i], i, "reset_flat_loser"); pos = None
            # 2. that close belongs to the OLD day - test it against the OLD limit
            if challenge and -realized_today >= daily_limit:
                r.outcome, r.end_bar, r.fail_note = "fail_daily", i, "realized at reset"
                return r
            # 3. roll the day: zero, rebase, recompute the limit off the new day_start
            realized_today = 0.0
            day_start = bal
            # daily_limit stays INITIAL * DAILY_PCT - the FAQ says initial balance, not day-start
            # 4. a SURVIVING position's floating now counts in full against the NEW
            #    limit - yesterday's profit does not carry. Unreachable under
            #    swing_safe by design: it has already flattened every loser.
            if pos and challenge and -flt(pos, o[i]) >= daily_limit:
                r.outcome, r.end_bar = "fail_daily", i
                r.fail_note = "floating loss carried across reset"
                r.rollover_breach = True
                return r

        # --- new entry at this bar's open if the previous close signalled
        if pos is None and (i - 1) in sig_at and i < n - 1:
            side, d = sig_at[i - 1]
            next_t = T0 + (i + 1) * STEP
            skip = variant == "intraday" and (next_t % 86400) == RESET_SEC
            entry = o[i]
            # budgets per the two-ceiling model
            daily_budget = daily_limit + realized_today      # profit today expands it
            total_budget = bal - floor_total
            eff = min(daily_budget, total_budget)
            if challenge and eff <= 0: skip = True
            risk = min(RISK_PCT * bal, BUDGET_CAP * eff) if challenge else RISK_PCT * bal
            if risk <= 0: skip = True
            if not skip:
                qty = risk / (d + entry * FEE * 2)
                qty = min(qty, MAX_LEV * bal / entry)
                bal -= qty * entry * FEE
                realized_today -= qty * entry * FEE
                stop = entry - side * d
                target = entry + side * TARGET_R * d
                pos = Pos(side, entry, stop, target, qty, i, risk)
                r.trading_days.add((t - RESET_SEC) // 86400)


        # --- manage open position on this bar
        if pos:
            p = pos
            hit_stop = l[i] <= p.stop if p.side > 0 else h[i] >= p.stop
            hit_tgt = h[i] >= p.target if p.side > 0 else l[i] <= p.target
            worst = (max(l[i], p.stop) if p.side > 0 else min(h[i], p.stop))
            worst_flt = flt(p, worst)
            # breach checks on the worst path, with the stop as the floor
            if challenge:
                if -(realized_today + worst_flt) >= daily_limit and not (hit_stop and -(realized_today + flt(p, p.stop)) < daily_limit):
                    r.outcome, r.end_bar = "fail_daily", i
                    r.fail_note = "floating hit daily limit"
                    return r
                if bal + worst_flt <= floor_total:
                    r.outcome, r.end_bar = "fail_maxloss", i
                    r.fail_note = "floating hit max loss floor"
                    return r
            if hit_stop:
                px = p.stop * (1 - SLIP_STOP * p.side)
                close(p, px, i, "stop"); pos = None
            elif hit_tgt:
                close(p, p.target, i, "target"); pos = None

        # --- realized breach / pass checks
        if challenge:
            if -realized_today >= daily_limit:
                r.outcome, r.end_bar, r.fail_note = "fail_daily", i, "realized"; return r
            if bal <= floor_total:
                r.outcome, r.end_bar, r.fail_note = "fail_maxloss", i, "realized"; return r
            if pos is None and bal >= INITIAL * (1 + TARGET_PCT):
                r.outcome, r.end_bar = "pass", i
                r.balance = bal
                return r

        r.peak = max(r.peak, bal)
        r.trough_dd = min(r.trough_dd, bal - r.peak)

    if pos:  # end of data: mark to close
        close(pos, c[n - 1], n - 1, "eod")
    r.balance = bal
    if r.outcome == "running":
        r.end_bar = n - 1
        eff = min(daily_limit + realized_today, bal - floor_total)
        if challenge and eff < ZOMBIE_PCT * INITIAL:
            r.outcome = "zombie"
            r.fail_note = f"effective budget ${eff:,.0f} < {ZOMBIE_PCT:.0%} of quota"
    return r


# ------------------------------------------------------------------ reporting

def trade_stats(trades):
    if not trades:
        return {}
    rs = [t["r"] for t in trades]
    wins = [x for x in rs if x > 0]; losses = [x for x in rs if x <= 0]
    gw = sum(t["pnl"] for t in trades if t["pnl"] > 0)
    gl = -sum(t["pnl"] for t in trades if t["pnl"] < 0)
    streak = worst = 0
    for x in rs:
        streak = streak + 1 if x <= 0 else 0
        worst = max(worst, streak)
    by_side = {}
    for s in (+1, -1):
        sub = [t["r"] for t in trades if t["side"] == s]
        if sub:
            by_side["long" if s > 0 else "short"] = dict(
                n=len(sub), win=sum(1 for x in sub if x > 0) / len(sub) * 100,
                exp_r=statistics.mean(sub))
    reasons = {}
    for t in trades:
        reasons[t["reason"]] = reasons.get(t["reason"], 0) + 1
    return dict(n=len(trades), win_rate=len(wins) / len(rs) * 100,
                avg_win_r=statistics.mean(wins) if wins else 0,
                avg_loss_r=statistics.mean(losses) if losses else 0,
                exp_r=statistics.mean(rs), profit_factor=(gw / gl) if gl else float("inf"),
                worst_streak=worst, net=sum(t["pnl"] for t in trades),
                by_side=by_side, reasons=reasons)


def main():
    bars = load_bars(sys.argv[1] if len(sys.argv) > 1 else "data/btc_4h.csv")
    e20, e120, atr = indicators(bars)
    sigs = signals(bars, e20, e120, atr)
    warm = EMA_TREND + TREND_SLOPE_BARS + 1
    out = {"n_bars": len(bars), "n_signals": len(sigs),
           "signals_long": sum(1 for s in sigs if s[1] > 0),
           "signals_short": sum(1 for s in sigs if s[1] < 0), "variants": {}}

    for variant in ("intraday", "swing", "swing_safe"):
        # 1) continuous run, no challenge stops, fixed 0.5% risk: the raw edge
        cont = run(bars, sigs, variant, warm, challenge=False)
        # 2) rolling challenge starts every 3 days (18 bars)
        starts = list(range(warm, len(bars) - 6 * 20, 18))
        runs = [run(bars, sigs, variant, s) for s in starts]
        outcomes = {}
        for x in runs:
            outcomes[x.outcome] = outcomes.get(x.outcome, 0) + 1
        passes = [x for x in runs if x.outcome == "pass"]
        fails = [x for x in runs if x.outcome.startswith("fail")]
        days_to_pass = [(x.end_bar - x.start) * STEP / 86400 for x in passes]
        days_to_fail = [(x.end_bar - x.start) * STEP / 86400 for x in fails]
        under5 = sum(1 for x in passes if len(x.trading_days) < 5)
        rollover = sum(1 for x in runs if x.rollover_breach)
        notes = {}
        for x in fails:
            notes[x.fail_note] = notes.get(x.fail_note, 0) + 1
        out["variants"][variant] = dict(
            continuous=dict(final_balance=cont.balance, max_dd=cont.trough_dd,
                            **trade_stats(cont.trades)),
            challenge=dict(starts=len(runs), outcomes=outcomes,
                           pass_rate=len(passes) / len(runs) * 100,
                           fail_rate=len(fails) / len(runs) * 100,
                           median_days_to_pass=statistics.median(days_to_pass) if days_to_pass else None,
                           median_days_to_fail=statistics.median(days_to_fail) if days_to_fail else None,
                           passes_under_5_trading_days=under5,
                           rollover_breaches=rollover, fail_causes=notes))
    json.dump(out, open("results.json", "w"), indent=1, default=str)
    return out


if __name__ == "__main__":
    res = main()
    print(f"bars {res['n_bars']}  signals {res['n_signals']} "
          f"(L {res['signals_long']} / S {res['signals_short']})\n")
    for v, d in res["variants"].items():
        c, ch = d["continuous"], d["challenge"]
        print(f"=== {v.upper()} ===")
        print(f" continuous 0.5%/trade: {c['n']} trades, win {c['win_rate']:.0f}%, "
              f"exp {c['exp_r']:+.2f}R, PF {c['profit_factor']:.2f}, "
              f"worst streak {c['worst_streak']}, net ${c['net']:,.0f}, maxDD ${c['max_dd']:,.0f}")
        for s, bs in c["by_side"].items():
            print(f"    {s:5s}: {bs['n']:3d} trades  win {bs['win']:.0f}%  exp {bs['exp_r']:+.2f}R")
        print(f"    exits: {c['reasons']}")
        print(f" challenge x{ch['starts']} starts: pass {ch['pass_rate']:.0f}%  "
              f"fail {ch['fail_rate']:.0f}%  {ch['outcomes']}")
        print(f"    median days to pass {ch['median_days_to_pass']}, to fail {ch['median_days_to_fail']}")
        print(f"    fail causes {ch['fail_causes']}  rollover breaches {ch['rollover_breaches']}"
              f"  passes with <5 trading days {ch['passes_under_5_trading_days']}")
        print()
