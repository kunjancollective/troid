#!/usr/bin/env python3
"""v2: regime-switched pullback / breakout with laddered entries and take-profits.

Regime
  width = (highest high − lowest low over RANGE_BARS) / ATR
  compressed  -> breakout mode  (pullback OFF)
  otherwise   -> pullback mode  (breakout OFF)

Ladder (LADDER=True)
  3 tranches: T1 at next open (market), T2 and T3 as resting limits below/above.
  Shared stop beyond all tranches. Each tranche sized to 1/3 of the risk budget
  at the shared stop, net of fees. Unfilled tranches cancel after LADDER_TTL bars
  or once TP1 prints.
  3 take-profits at 1R / 2R / 3R measured from T1:
     TP1 closes 1/3 of what's held, TP2 half of the remainder, TP3 the rest.
     After TP1, stop moves to average entry.

Holding: swing_safe (hold through the 16:00 UTC reset if floating >= 0, close if
underwater). Bitfunded accounting identical to engine.py.

Ablation flags: REGIME, BREAKOUT, LADDER.
"""
from __future__ import annotations
import csv, statistics, sys, json
from dataclasses import dataclass, field

sys.path.insert(0, ".")
import engine as E   # indicators, constants, trade_stats

RANGE_BARS   = 90        # 15 days of 4h
COMPRESS_K   = 8.0       # range narrower than this many ATRs = compressed
MIN_COMP     = 18        # must be compressed >= 3 days before a breakout counts
BO_COOLDOWN  = 45        # bars to wait after a breakout signal
LADDER_TTL   = 6         # bars unfilled limits stay live
PB_STEP      = 0.5       # ATR spacing between pullback tranches
BO_STEP      = 0.5
LADDER_STOP_BUF = 0.5    # ATR beyond the last tranche / structure
PB_MAX_STOP  = 2.5       # ATRs from T1, skip if wider
BO_MAX_STOP  = 3.0
TPS          = (1.0, 2.0, 3.0)

REGIME, BREAKOUT, LADDER = True, True, True
HOLDING = "swing_safe"          # intraday | swing | swing_safe
LADDER_DIR = "weakness"         # weakness | strength | none
LADDER_N   = 3                  # tranches in the ladder
REVERSE_AFTER_TP3 = False       # master switch for the reverse
REVERSE_TRIGGER = "tp3"         # tp3 | tp2 | stop | any  - what counts as exhaustion
REV_STOP_BUF = 0.5              # ATRs beyond the move's extreme for the reverse stop
REV_MAX_STOP = 3.0              # skip the reverse if its stop is wider than this (ATRs)
MAX_HOLD_BARS = 60              # RTP s.1: majors 10d (60 bars), other crypto 7d (42), TradFi 5d (30). Set per asset.
MIN_TRADING_DAYS = 5            # ToU 9(a): required to clear a stage
BREAKEVEN_AFTER_TP1 = True


def regime(bars, atr):
    o, h, l, c = zip(*bars)
    n = len(bars)
    comp = [False] * n
    width = [None] * n
    hi = [None] * n; lo = [None] * n
    for i in range(RANGE_BARS, n):
        if atr[i] is None: continue
        hh = max(h[i - RANGE_BARS:i]); ll = min(l[i - RANGE_BARS:i])   # excludes bar i
        hi[i], lo[i] = hh, ll
        width[i] = (hh - ll) / atr[i]
        comp[i] = width[i] < COMPRESS_K
    return comp, hi, lo, width


def build_signals(bars, e20, e120, atr):
    """Return list of dicts: {i, side, kind, tranches[], stop} with entry at i+1 open."""
    o, h, l, c = zip(*bars)
    comp, rhi, rlo, width = regime(bars, atr)
    base = E.signals(bars, e20, e120, atr)            # v1 pullback signals
    base_at = {i: (s, d) for i, s, d in base}
    out = []
    comp_run = 0
    cooldown = 0
    warm = max(E.EMA_TREND + E.TREND_SLOPE_BARS, RANGE_BARS)
    for i in range(warm, len(bars) - 1):
        a = atr[i]
        if a is None: continue
        comp_run = comp_run + 1 if comp[i] else 0
        cooldown = max(0, cooldown - 1)
        t1 = o[i + 1]

        # ---------- breakout in compression
        if BREAKOUT and REGIME and comp_run >= MIN_COMP and cooldown == 0:
            side = +1 if c[i] > rhi[i] else (-1 if c[i] < rlo[i] else 0)
            if side:
                edge = rhi[i] if side > 0 else rlo[i]
                mid = (rhi[i] + rlo[i]) / 2
                if LADDER and LADDER_DIR == "weakness":
                    tr = [t1, edge, edge - side * BO_STEP * a]   # retest of the broken edge
                    stop = tr[-1] - side * LADDER_STOP_BUF * a
                    stop = max(stop, mid) if side > 0 else min(stop, mid)
                elif LADDER and LADDER_DIR == "strength":
                    tr = [t1, t1 + side * BO_STEP * a, t1 + side * 2 * BO_STEP * a]
                    stop = edge - side * LADDER_STOP_BUF * a
                    stop = max(stop, mid) if side > 0 else min(stop, mid)
                else:
                    tr = [t1]
                    stop = t1 - side * 1.5 * a
                    stop = max(stop, mid) if side > 0 else min(stop, mid)
                if abs(t1 - stop) <= BO_MAX_STOP * a and (t1 - stop) * side > 0:
                    out.append(dict(i=i, side=side, kind="breakout", tranches=tr, stop=stop))
                    cooldown = BO_COOLDOWN
                continue

        # ---------- pullback in trend
        if i in base_at and not (REGIME and comp[i]):
            side, d = base_at[i]
            lo_w = min(l[i - E.STRUCT_BARS + 1:i + 1]); hi_w = max(h[i - E.STRUCT_BARS + 1:i + 1])
            struct = lo_w if side > 0 else hi_w
            if LADDER and LADDER_DIR == "weakness":
                tr = [t1 - side * j * PB_STEP * a for j in range(LADDER_N)]
                anchor = min(struct, tr[-1]) if side > 0 else max(struct, tr[-1])
                stop = anchor - side * LADDER_STOP_BUF * a
            elif LADDER and LADDER_DIR == "strength":
                # add only as it proves out; stop stays anchored to T1's structure
                tr = [t1 + side * j * PB_STEP * a for j in range(LADDER_N)]
                stop = struct - side * LADDER_STOP_BUF * a
            else:
                tr = [t1]; stop = t1 - side * d
            if abs(t1 - stop) > PB_MAX_STOP * a: continue
            out.append(dict(i=i, side=side, kind="pullback", tranches=tr, stop=stop))
    return out


@dataclass
class Tranche:
    price: float; qty: float; filled: bool = False; fill_above: bool = False

@dataclass
class Pos:
    side: int; kind: str; tranches: list; stop: float; tps: list; tp_done: int = 0
    bar: int = 0; risk: float = 0.0; r_dist: float = 0.0; realized: float = 0.0
    is_reverse: bool = False; extreme: float = 0.0
    def held(self): return sum(t.qty for t in self.tranches if t.filled)
    def avg(self):
        q = self.held()
        return sum(t.price * t.qty for t in self.tranches if t.filled) / q if q else 0.0
    def flt(self, px): return (px - self.avg()) * self.held() * self.side


@dataclass
class Result:
    start: int; outcome: str = "running"; end_bar: int | None = None; fail_note: str = ""
    balance: float = E.INITIAL; peak: float = E.INITIAL; trough_dd: float = 0.0
    trades: list = field(default_factory=list); trading_days: set = field(default_factory=set)
    rollover_breach: bool = False
    # state at the last bar, captured BEFORE any open position is marked to the last close
    realized_balance: float = E.INITIAL; realized_today: float = 0.0; day_start: float = E.INITIAL
    open_position: dict | None = None


def run(bars, sigs, start, challenge=True, risk_pct=E.RISK_PCT, capped=True, atr=None):
    o, h, l, c = zip(*bars)
    sig_at = {s["i"]: s for s in sigs}
    r = Result(start)
    pending_rev = None; prev_pos = None
    bal = E.INITIAL; realized_today = 0.0; pos: Pos | None = None
    day_start = E.INITIAL
    daily_limit = E.INITIAL * E.DAILY_PCT; floor_total = E.INITIAL * (1 - E.MAXLOSS_PCT)   # fixed from initial
    n = len(bars)

    def book(p, px, qty, i, reason):
        """Close qty at px; when the position is fully out, log one trade record."""
        nonlocal bal, realized_today
        pnl = (px - p.avg()) * qty * p.side - qty * px * E.FEE
        bal += pnl; realized_today += pnl; p.realized += pnl
        # remove qty proportionally from filled tranches (avg entry unchanged)
        held = p.held(); frac = qty / held
        for t in p.tranches:
            if t.filled: t.qty *= (1 - frac)
        if p.held() < 1e-9 or reason in ("stop", "reset_flat_loser", "eod"):
            for t in p.tranches: t.qty = 0.0
            r.trades.append(dict(side=p.side, kind=p.kind, pnl=p.realized, r=p.realized / p.risk,
                                 bars=i - p.bar, reason=reason, bar=i,
                                 tps_hit=p.tp_done, fills=sum(1 for t in p.tranches if t.filled)))
            return None
        return p

    for i in range(start, n):
        t = E.T0 + i * E.STEP
        is_reset = (t % 86400) == E.RESET_SEC
        if is_reset:
            # 1. policy flatten (holding policy is a parameter; see HOLDING)
            if pos and HOLDING == "intraday":
                pos = book(pos, o[i], pos.held(), i, "reset_flat")
            elif pos and HOLDING == "swing_safe" and pos.flt(o[i]) < 0:
                pos = book(pos, o[i], pos.held(), i, "reset_flat_loser")
            # 2. that close belongs to the OLD day
            if challenge and -realized_today >= daily_limit:
                r.outcome, r.end_bar, r.fail_note = "fail_daily", i, "realized at reset"
                return r
            # 3. roll the day and rebase the limit
            realized_today = 0.0
            day_start = bal
            # daily_limit stays fixed at INITIAL * DAILY_PCT (Bitfunded FAQ)
            # 4. surviving floating vs the NEW limit
            if pos and challenge and -pos.flt(o[i]) >= daily_limit:
                r.outcome, r.end_bar, r.fail_note, r.rollover_breach = "fail_daily", i, "floating carried across reset", True
                return r

        # ---------- new position
        if pos is None and pending_rev and i > pending_rev["bar"] and i < n - 1 and atr is not None and atr[i]:
            rv = pending_rev; pending_rev = None
            s = rv["side"]; t1r = o[i]; stop_r = rv["stop"]
            if (t1r - stop_r) * s > 0 and abs(t1r - stop_r) <= REV_MAX_STOP * atr[i]:
                sg = dict(i=i - 1, side=s, kind="reverse",
                          tranches=[t1r + s * j * PB_STEP * atr[i] for j in range(LADDER_N if LADDER else 1)],
                          stop=stop_r)
            else:
                sg = None
        elif pos is None and (i - 1) in sig_at and i < n - 1:
            sg = sig_at[i - 1]
        else:
            sg = None
        if sg is not None:
            s = sg["side"]
            daily_budget = daily_limit + realized_today
            eff = min(daily_budget, bal - floor_total)
            skip = challenge and eff <= 0
            risk = min(risk_pct * bal, E.BUDGET_CAP * eff) if (challenge and capped) else risk_pct * bal
            if risk <= 0: skip = True
            if not skip:
                k = len(sg["tranches"]); per = risk / k
                trs = []
                above = (s > 0) == (LADDER_DIR == "strength")
                for j, px in enumerate(sg["tranches"]):
                    d = (px - sg["stop"]) * s
                    if d <= 0: continue
                    trs.append(Tranche(px, per / (d + px * E.FEE * 2),
                                       fill_above=(above if j else False)))
                if trs:
                    notional = sum(tr.price * tr.qty for tr in trs)
                    if notional > E.MAX_LEV * bal:
                        scale = E.MAX_LEV * bal / notional
                        for tr in trs: tr.qty *= scale
                    t1 = trs[0]; t1.filled = True
                    fee = t1.qty * t1.price * E.FEE
                    bal -= fee; realized_today -= fee
                    r_dist = (t1.price - sg["stop"]) * s
                    tps = [t1.price + s * m * r_dist for m in (TPS if LADDER else (E.TARGET_R,))]
                    pos = Pos(s, sg["kind"], trs, sg["stop"], tps, bar=i, risk=risk, r_dist=r_dist, realized=-fee,
                              is_reverse=(sg["kind"] == "reverse"), extreme=(h[i] if s > 0 else l[i]))
                    r.trading_days.add((t - E.RESET_SEC) // 86400)


        prev_pos = pos if pos else prev_pos
        if pos:
            p = pos; s = p.side
            # 1) resting limit fills (price reaches them before any stop below them)
            if i - p.bar < LADDER_TTL and p.tp_done == 0:
                for tr in p.tranches:
                    if not tr.filled and ((h[i] >= tr.price) if tr.fill_above else (l[i] <= tr.price)):
                        tr.filled = True
                        fee = tr.qty * tr.price * E.FEE
                        bal -= fee; realized_today -= fee; p.realized -= fee
            else:
                for tr in p.tranches:
                    if not tr.filled: tr.qty = 0.0
            if p.held() <= 0:
                pos = None
            else:
                p.extreme = max(p.extreme, h[i]) if s > 0 else (min(p.extreme, l[i]) if p.extreme else l[i])
                worst = max(l[i], p.stop) if s > 0 else min(h[i], p.stop)
                wf = p.flt(worst)
                if challenge:
                    if -(realized_today + wf) >= daily_limit:
                        r.outcome, r.end_bar, r.fail_note = "fail_daily", i, "floating hit daily limit"; return r
                    if bal + wf <= floor_total:
                        r.outcome, r.end_bar, r.fail_note = "fail_maxloss", i, "floating hit max loss floor"; return r
                if i - p.bar >= MAX_HOLD_BARS:
                    pos = book(p, o[i], p.held(), i, "max_hold_10d")
                elif (l[i] <= p.stop if s > 0 else h[i] >= p.stop):
                    px = p.stop * (1 - E.SLIP_STOP * s)
                    pos = book(p, px, p.held(), i, "stop")
                else:
                    moved = False
                    while pos and p.tp_done < len(p.tps):
                        tp = p.tps[p.tp_done]
                        if (s > 0 and h[i] >= tp) or (s < 0 and l[i] <= tp):
                            held = p.held()
                            k = p.tp_done
                            last = (k == len(p.tps) - 1)
                            qty = held if last else (held / 3 if k == 0 else held / 2)
                            p.tp_done += 1
                            pos = book(p, tp, qty, i, f"tp{k+1}")
                            if k == 0: moved = True
                        else:
                            break
                    if pos and moved and BREAKEVEN_AFTER_TP1:
                        p.stop = p.avg()          # breakeven after TP1, effective next bar

        # ---- arm a reverse when a position has just fully closed
        if (REVERSE_AFTER_TP3 and pos is None and prev_pos is not None
                and not prev_pos.is_reverse and atr is not None and atr[i] and r.trades):
            last = r.trades[-1]
            fired = (REVERSE_TRIGGER == "any"
                     or (REVERSE_TRIGGER == "stop" and last["reason"] == "stop")
                     or (REVERSE_TRIGGER == "tp2" and last["tps_hit"] >= 2)
                     or (REVERSE_TRIGGER == "tp3" and last["tps_hit"] >= 3))
            if fired:
                ext = prev_pos.extreme or (h[i] if prev_pos.side > 0 else l[i])
                pending_rev = dict(side=-prev_pos.side,
                                   stop=ext + prev_pos.side * REV_STOP_BUF * atr[i], bar=i)
        prev_pos = pos

        if challenge:
            if -realized_today >= daily_limit:
                r.outcome, r.end_bar, r.fail_note = "fail_daily", i, "realized"; return r
            if bal <= floor_total:
                r.outcome, r.end_bar, r.fail_note = "fail_maxloss", i, "realized"; return r
            if (pos is None and bal >= E.INITIAL * (1 + E.TARGET_PCT)
                    and len(r.trading_days) >= MIN_TRADING_DAYS):
                r.outcome, r.end_bar, r.balance = "pass", i, bal; return r
        r.peak = max(r.peak, bal); r.trough_dd = min(r.trough_dd, bal - r.peak)

    r.realized_balance, r.realized_today, r.day_start = bal, realized_today, day_start
    if pos:
        r.open_position = dict(entry_bar=pos.bar, fills=sum(1 for t in pos.tranches if t.filled),
                               tranches=len(pos.tranches), kind=pos.kind, side=pos.side)
        pos = book(pos, c[n - 1], pos.held(), n - 1, "eod")   # marked to the last close; reason "eod"
    r.balance = bal
    if r.outcome == "running":
        r.end_bar = n - 1
        eff = min(daily_limit + realized_today, bal - floor_total)
        if challenge and eff < E.ZOMBIE_PCT * E.INITIAL:
            r.outcome = "zombie"
    return r


def evaluate(bars, label, risk_pct=E.RISK_PCT):
    e20, e120, atr = E.indicators(bars)
    sigs = build_signals(bars, e20, e120, atr)
    warm = max(E.EMA_TREND + E.TREND_SLOPE_BARS, RANGE_BARS) + 1
    cont = run(bars, sigs, warm, challenge=False, risk_pct=risk_pct)
    st = E.trade_stats(cont.trades)
    kinds = {}
    for tr in cont.trades:
        kinds.setdefault(tr["kind"], []).append(tr["r"])
    starts = list(range(warm, len(bars) - 120, 18))
    runs = [run(bars, sigs, s, risk_pct=risk_pct) for s in starts]
    oc = {}
    for x in runs: oc[x.outcome] = oc.get(x.outcome, 0) + 1
    return dict(label=label, n=st.get("n", 0), win=st.get("win_rate", 0), exp=st.get("exp_r", 0),
                pf=st.get("profit_factor", 0), net=st.get("net", 0), maxdd=cont.trough_dd,
                streak=st.get("worst_streak", 0), by_kind={k: (len(v), statistics.mean(v)) for k, v in kinds.items()},
                by_side=st.get("by_side", {}), exits=st.get("reasons", {}),
                challenge=oc, n_starts=len(runs),
                rollover=sum(1 for x in runs if x.rollover_breach))


if __name__ == "__main__":
    bars = E.load_bars(sys.argv[1] if len(sys.argv) > 1 else "data/btc_4h.csv")
    configs = [("A  v1 pullback only (swing_safe)", False, False, False),
               ("B  + regime filter (pullback off in compression)", True, False, False),
               ("C  + breakout in compression", True, True, False),
               ("D  + 3-entry ladder, 3 TPs", True, True, True)]
    results = []
    for label, rg, bo, ld in configs:
        REGIME, BREAKOUT, LADDER = rg, bo, ld
        for rp in (0.005, 0.01):
            res = evaluate(bars, label, rp); res["risk"] = rp; results.append(res)
    json.dump(results, open("results_v2.json", "w"), indent=1, default=str)
    for res in results:
        if res["risk"] != 0.005: continue
        print(f"{res['label']}")
        print(f"   {res['n']:3d} trades  win {res['win']:.0f}%  exp {res['exp']:+.2f}R  PF {res['pf']:.2f}  "
              f"net ${res['net']:,.0f}  maxDD ${res['maxdd']:,.0f}  streak {res['streak']}")
        print(f"   by kind: " + ", ".join(f"{k} n={v[0]} exp {v[1]:+.2f}R" for k, v in res["by_kind"].items()))
        print(f"   by side: " + ", ".join(f"{k} n={v['n']} win {v['win']:.0f}% exp {v['exp_r']:+.2f}R" for k, v in res["by_side"].items()))
        print(f"   exits: {res['exits']}")
        ch1 = [x for x in results if x["label"] == res["label"] and x["risk"] == 0.01][0]
        print(f"   challenge @0.5%: {res['challenge']}   @1.0%: {ch1['challenge']}  rollover@1%: {ch1['rollover']}")
        print()
