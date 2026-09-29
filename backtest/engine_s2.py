#!/usr/bin/env python3
"""troid-shadow-2's signals and states (SHADOW2.md), traded through engine_v2's accounting, unchanged.

  import engine_s2 as S2
  cfg = S2.load_config()
  bars, t0 = S2.load("data/BTCUSDT_4h.csv")
  sigs = S2.signals(bars, t0, cfg)                  # the ensemble; lookbacks=(6,) for one lookback alone
  r = S2.run(bars, t0, sigs, cfg, asset="BTC", challenge=False)

Every decision comes from shadow2_config.json. The accounting is engine_v2.run, the function shadow-1 runs: while it
runs, this module sets engine_v2's switches for a one-entry trade (no ladder, no reverse, one take-profit) and the
config's holding, hold limit, risk and fees, then puts every one back, so shadow-1 in the same process is untouched.

A signal at decision bar i uses bars 0..i only; its trade opens at bar i+1's open, and its stop is placed from that
fill (test_shadow2.py truncates the bars after i and gets the same signal).
"""
from __future__ import annotations

import contextlib
import csv
import json
import math
from bisect import insort, bisect_left
from pathlib import Path

import engine as E
import engine_v2 as V

HERE = Path(__file__).resolve().parent
CONFIG = HERE / "shadow2_config.json"
PER_DAY = 86400 // E.STEP                  # six 4h bars a day
TRADFI = ("XAU", "XAG", "TSLA", "PAXG")    # PAXG: tokenised gold, reported as a gold proxy with TradFi's hold (SHADOW2.md)


def load_config(path=CONFIG):
    return json.loads(Path(path).read_text())


def load(path):
    """t,o,h,l,c bars (fetch_binance.py's format) and their first timestamp. engine.load_bars sets engine's T0 as a
    side effect; the caller keeps it with the bars, since the cross-section loads one asset after another."""
    rows = [r for r in csv.reader(open(path)) if r and not r[0].startswith("#")]
    t0 = int(float(rows[0][0]))
    ts = [int(float(r[0])) for r in rows]
    assert all(b - a == E.STEP for a, b in zip(ts, ts[1:])), f"{path}: bars are not regular 4h"
    return [tuple(map(float, r[1:5])) for r in rows], t0


def asset_class(asset, cfg):
    a = asset.upper()
    return "tradfi" if a in TRADFI else "major" if a in cfg["majors"] else "minor"


def lookback_bars(months, cfg):
    return round(months * cfg["month_days"] * PER_DAY)


# ---------------------------------------------------------------------- inputs, each at bar i from bars 0..i
def daily_vol(c, cfg):
    """sigma[i]: the sample standard deviation of the last vol_days of 4h log returns, scaled to a day."""
    n, w = len(c), cfg["vol_days"] * PER_DAY
    lr = [0.0] + [math.log(c[i] / c[i - 1]) for i in range(1, n)]
    out, s, s2 = [None] * n, 0.0, 0.0
    for i in range(1, n):
        s += lr[i]; s2 += lr[i] * lr[i]
        if i > w:
            s -= lr[i - w]; s2 -= lr[i - w] * lr[i - w]
        if i >= w:
            var = (s2 - s * s / w) / (w - 1)
            out[i] = math.sqrt(max(var, 0.0) * PER_DAY)
    return out


def vol_of_vol(sig, cfg):
    """vov[i]: the coefficient of variation of sigma over the last state_window_days (sample standard deviation over the
    mean), where every sigma in the window exists."""
    n, w = len(sig), cfg["state_window_days"] * PER_DAY
    out, s, s2, k = [None] * n, 0.0, 0.0, 0
    for i in range(n):
        x = sig[i]
        if x is not None:
            s += x; s2 += x * x; k += 1
        if i >= w and sig[i - w] is not None:
            y = sig[i - w]; s -= y; s2 -= y * y; k -= 1
        if k == w and s > 0:
            m = s / w
            out[i] = math.sqrt(max((s2 - s * m) / (w - 1), 0.0)) / m
    return out


def bb_width(c, cfg):
    """Bollinger width at bar i: 2 x bb_k population standard deviations of the last bb_bars closes, over their mean."""
    n, w, k = len(c), cfg["bb_bars"], cfg["bb_k"]
    out = [None] * n
    for i in range(w - 1, n):
        win = c[i - w + 1:i + 1]
        m = sum(win) / w
        sd = math.sqrt(sum((x - m) ** 2 for x in win) / w)
        out[i] = 2 * k * sd / m
    return out


class TrailingMedian:
    """The median of the last `size` values added, the newest included."""

    def __init__(self, size):
        self.size, self.buf, self.sorted = size, [], []

    def add(self, x):
        self.buf.append(x); insort(self.sorted, x)
        if len(self.buf) > self.size:
            old = self.buf.pop(0); del self.sorted[bisect_left(self.sorted, old)]

    def full(self):
        return len(self.buf) == self.size

    def median(self):
        s, k = self.sorted, len(self.sorted)
        return s[k // 2] if k % 2 else (s[k // 2 - 1] + s[k // 2]) / 2


def is_decision(i, t0, cfg):
    hh, mm = map(int, cfg["decide_bar_utc"].split(":"))
    return (t0 + i * E.STEP) % 86400 == hh * 3600 + mm * 60


def signals(bars, t0, cfg, lookbacks=None):
    """One dict per decision bar that takes a trade: {i, side, kind, tranches: [entry], stop, ...} as engine_v2.run reads
    it, plus what shadow-2 records (the votes, sigma, the two states). A decision bar is counted only once every input
    exists (the longest lookback, the vol-of-vol window, a full year of each state's median)."""
    o, h, l, c = zip(*bars)
    n = len(bars)
    Ls = tuple(lookbacks or cfg["lookback_months"])
    nL = {L: lookback_bars(L, cfg) for L in Ls}
    nL_all = {L: lookback_bars(L, cfg) for L in cfg["lookback_months"]}
    sig = daily_vol(c, cfg)
    vov = vol_of_vol(sig, cfg)
    bbw = bb_width(c, cfg)
    med_v, med_b = TrailingMedian(cfg["state_median_days"]), TrailingMedian(cfg["state_median_days"])
    k = cfg["stop_sigmas"]
    out = []
    for i in range(n - 1):
        if not is_decision(i, t0, cfg):
            continue
        if vov[i] is not None:
            med_v.add(vov[i])
        if bbw[i] is not None:
            med_b.add(bbw[i])
        # every input exists, for every lookback of the family: the ensemble and each lookback alone start together
        if i < max(nL_all.values()) or sig[i] is None or not (med_v.full() and med_b.full()):
            continue
        votes = {L: (c[i] > c[i - nL[L]]) - (c[i] < c[i - nL[L]]) for L in Ls}
        v = sum(votes.values())
        side = (v > 0) - (v < 0)
        if not side:
            continue
        entry = o[i + 1]
        stop = entry * (1 - side * k * sig[i])
        out.append(dict(i=i, side=side, kind="tsmom", tranches=[entry], stop=stop,
                        vote=v, votes=votes, sigma=sig[i], vov=vov[i], bbw=bbw[i],
                        vov_state="calm" if vov[i] <= med_v.median() else "unsettled",
                        bb_state="compressed" if bbw[i] <= med_b.median() else "expanded"))
    return out


def first_decision(bars, t0, cfg):
    """The first bar at which a decision can be taken (every input exists), whether or not it trades."""
    o, h, l, c = zip(*bars)
    sig = daily_vol(c, cfg)
    vov = vol_of_vol(sig, cfg)
    bbw = bb_width(c, cfg)
    mv, mb = TrailingMedian(cfg["state_median_days"]), TrailingMedian(cfg["state_median_days"])
    longest = max(lookback_bars(L, cfg) for L in cfg["lookback_months"])
    for i in range(len(bars) - 1):
        if not is_decision(i, t0, cfg):
            continue
        if vov[i] is not None:
            mv.add(vov[i])
        if bbw[i] is not None:
            mb.add(bbw[i])
        if i >= longest and sig[i] is not None and mv.full() and mb.full():
            return i
    return None


# ---------------------------------------------------------------------- the accounting: engine_v2.run, as it is
_V_KEYS = ("LADDER", "REVERSE_AFTER_TP3", "HOLDING", "MAX_HOLD_BARS", "MIN_TRADING_DAYS", "BREAKEVEN_AFTER_TP1", "TPS",
           "LADDER_N", "LADDER_DIR", "REGIME", "BREAKOUT")
_E_KEYS = ("INITIAL", "RISK_PCT", "BUDGET_CAP", "FEE", "MAX_LEV", "TARGET_R", "T0")


@contextlib.contextmanager
def configured(cfg, asset, t0):
    """engine_v2 and engine set for shadow-2 on this asset, for the length of the block, then restored."""
    keep_v = {k: getattr(V, k) for k in _V_KEYS}
    keep_e = {k: getattr(E, k) for k in _E_KEYS}
    try:
        V.LADDER, V.REVERSE_AFTER_TP3 = False, False            # one entry, no reverse: tps = (TARGET_R,)
        V.HOLDING = cfg["holding"]
        V.MAX_HOLD_BARS = cfg["hold_bars"][asset_class(asset, cfg)]
        V.MIN_TRADING_DAYS = cfg["min_trading_days"]
        E.INITIAL, E.RISK_PCT, E.BUDGET_CAP = float(cfg["quota"]), cfg["risk_pct"], cfg["budget_cap"]
        E.FEE, E.MAX_LEV, E.TARGET_R = cfg["fee_per_side"], cfg["max_leverage"], cfg["take_profit_r"]
        E.T0 = t0
        yield
    finally:
        for k, x in keep_v.items():
            setattr(V, k, x)
        for k, x in keep_e.items():
            setattr(E, k, x)


def run(bars, t0, sigs, cfg, asset, challenge=False, start=None):
    """engine_v2.run on shadow-2's signals; each trade carries its signal's record (votes, sigma, states)."""
    with configured(cfg, asset, t0):
        s0 = start if start is not None else (sigs[0]["i"] + 1 if sigs else len(bars) - 1)
        r = V.run(bars, sigs, s0, challenge=challenge, risk_pct=cfg["risk_pct"])
    by_i = {s["i"]: s for s in sigs}
    for t in r.trades:
        s = by_i.get(t["entry_bar"] - 1)
        if s:
            t.update(vote=s["vote"], sigma=s["sigma"], vov_state=s["vov_state"], bb_state=s["bb_state"],
                     stop_sigma_pct=100 * cfg["stop_sigmas"] * s["sigma"])
    return r
