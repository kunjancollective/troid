#!/usr/bin/env python3
"""troid-shadow-2's own tests (SHADOW2.md): no signal looks ahead, the stop is the configured volatility multiple from the
fill, the accounting is engine_v2's and leaves shadow-1's engine as it found it, and the config is the one fixed.

  python backtest/test_shadow2.py
Reads files only.
"""
from __future__ import annotations

import json
import math
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import engine as E  # noqa: E402
import engine_s2 as S2  # noqa: E402
import engine_v2 as V  # noqa: E402

fails, n = [], 0


def ok(name, cond, info=""):
    global n
    n += 1
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else f"  {str(info)[:400]}"))
    if not cond:
        fails.append(name)


cfg = S2.load_config()
ok("the config is troid-shadow-2's, fixed: the four lookbacks, 2 sigmas, 3R, swing, the desk's risk",
   cfg["name"] == "troid-shadow-2" and cfg["lookback_months"] == [3, 6, 9, 12] and cfg["stop_sigmas"] == 2.0
   and cfg["take_profit_r"] == 3.0 and cfg["holding"] == "swing" and cfg["risk_pct"] == 0.005 and cfg["budget_cap"] == 0.35
   and cfg["exit_on_flip"] is False and cfg["holdout_from"] == "2025-01-01")
one = json.loads((HERE / "strategy_config.json").read_text())
ok("shadow-1's config is untouched: still troid-shadow-1", one["name"] == "troid-shadow-1" and one["holding"] == "swing_safe")
ok("hold limits by class, from the firm's tiers (majors 60 bars, other crypto 42, TradFi 30)",
   [cfg["hold_bars"][S2.asset_class(a, cfg)] for a in ("BTC", "SOL", "LINK", "PAXG")] == [60, 60, 42, 30])

bars, t0 = S2.load(HERE / "data" / "BTCUSDT_4h.csv")
sigs = S2.signals(bars, t0, cfg)
ok("signals exist and are daily decisions at the 20:00 UTC bar, entered at 00:00 UTC",
   len(sigs) > 300 and all((t0 + s["i"] * E.STEP) % 86400 == 20 * 3600 for s in sigs), len(sigs))

# no look-ahead: cut the bars after each sampled decision bar (keeping the entry bar's open) and rebuild
cut_ok, sampled = True, sigs[:: max(1, len(sigs) // 12)]
for s in sampled:
    cut = list(bars[: s["i"] + 1]) + [(bars[s["i"] + 1][0],) * 4]          # only the next open is known
    again = {x["i"]: x for x in S2.signals(cut, t0, cfg)}
    x = again.get(s["i"])
    if not x or any(x[k] != s[k] for k in ("side", "vote", "stop", "sigma", "vov_state", "bb_state")):
        cut_ok = False
        break
ok(f"no look-ahead: {len(sampled)} decisions rebuilt from the bars up to them (and the entry's open) are identical", cut_ok, s)

s = sigs[len(sigs) // 2]
c = [b[3] for b in bars]
lr = [math.log(c[j] / c[j - 1]) for j in range(s["i"] - 179, s["i"] + 1)]
ok("volatility: the last 30 days of 4h log returns, sample deviation, scaled to a day",
   abs(statistics.stdev(lr) * math.sqrt(6) - s["sigma"]) < 1e-12)
entry = bars[s["i"] + 1][0]
ok("the stop is 2 daily deviations from the fill, on the losing side",
   abs(abs(entry - s["stop"]) / entry - 2 * s["sigma"]) < 1e-12 and (entry - s["stop"]) * s["side"] > 0)
nl = S2.lookback_bars(12, cfg)
ok("the vote: each lookback's sign, 12 months = 2192 bars", nl == 2192 and s["votes"][12] == ((c[s["i"]] > c[s["i"] - nl]) - (c[s["i"]] < c[s["i"] - nl])))
ok("a tie is no trade: every signal has a nonzero vote whose sign is its side",
   all(x["vote"] != 0 and (x["vote"] > 0) == (x["side"] > 0) for x in sigs))

# the accounting, and engine_v2 put back as it was
before = ({k: getattr(V, k) for k in S2._V_KEYS}, {k: getattr(E, k) for k in S2._E_KEYS})
r = S2.run(bars, t0, sigs, cfg, asset="BTC", challenge=False, start=S2.first_decision(bars, t0, cfg) + 1)
after = ({k: getattr(V, k) for k in S2._V_KEYS}, {k: getattr(E, k) for k in S2._E_KEYS})
ok("engine_v2 and engine are left as they were found", before == after, [before, after])
tr = r.trades
ok("every trade is one entry with one take-profit at 3R, closed by stop, 3R, the 60-bar hold or the data's end",
   tr and all(t["fills"] == 1 and len(t["tp_prices"]) == 1 for t in tr)
   and {t["reason"] for t in tr} <= {"stop", "tp1", "max_hold_10d", "eod"}
   and all(abs((t["tp_prices"][0] - t["entry_price"]) - 3 * (t["entry_price"] - t["stop_price"])) < 1e-6 for t in tr),
   {t["reason"] for t in tr})
ok("no trade outlives the hold limit", max(t["bars"] for t in tr) <= 60, max(t["bars"] for t in tr))
ok("the desk's risk: 0.5% of the balance at entry (continuous run, uncapped), fees inside the R",
   abs(tr[0]["risk_usd"] - 500) < 1e-6 and all(t["r"] > -1.2 for t in tr), (tr[0]["risk_usd"], min(t["r"] for t in tr)))
ok("each trade carries its entry's states", all(t.get("vov_state") in ("calm", "unsettled") and t.get("bb_state") in ("compressed", "expanded")
                                                 for t in tr if t["reason"] != "eod"))

# shadow-1's replay is the same before and after shadow-2 ran in this process
import forward  # noqa: E402
forward.apply_config()
b1 = E.load_bars(str(HERE / "data" / "btc_4h.csv"))
e20, e120, atr = E.indicators(b1)
s1 = V.build_signals(b1, e20, e120, atr)
warm = max(E.EMA_TREND + E.TREND_SLOPE_BARS, V.RANGE_BARS) + 1
r1 = V.run(b1, s1, warm, challenge=True, risk_pct=forward.CFG["risk_pct"], atr=atr)
S2.run(bars, t0, sigs, cfg, asset="BTC")
forward.apply_config()
b1 = E.load_bars(str(HERE / "data" / "btc_4h.csv"))
r2 = V.run(b1, V.build_signals(b1, *E.indicators(b1)), warm, challenge=True, risk_pct=forward.CFG["risk_pct"], atr=E.indicators(b1)[2])
ok("shadow-1's replay of its frozen sample is identical after shadow-2 ran", [(t["bar"], round(t["pnl"], 6)) for t in r1.trades]
   == [(t["bar"], round(t["pnl"], 6)) for t in r2.trades] and len(r1.trades) > 50, (len(r1.trades), len(r2.trades)))

# the cross-section's statistics and data rule
import random  # noqa: E402
import tempfile  # noqa: E402
import cross_section as X  # noqa: E402
rng = random.Random(7)
tr = [dict(r=rng.gauss(0.1, 1.0), k=j) for j in range(200)]
iid = statistics.stdev([t["r"] for t in tr]) / math.sqrt(len(tr))
ok("clustered SE with one trade a cluster is the plain standard error", abs(X.clustered(tr, lambda t: t["k"])["se"] - iid) < 1e-12)
twins = [dict(r=t["r"], k=t["k"]) for t in tr] + [dict(r=t["r"], k=t["k"]) for t in tr]
ok("a trade repeated in its own cluster doesn't shrink the error (clustering sees the copies)",
   X.clustered(twins, lambda t: t["k"])["se"] > 0.99 * iid)
a_, b_ = tr[:100], tr[100:]
d = X.clustered_diff(a_, b_, lambda t: t["k"])
welch = math.sqrt(statistics.variance([t["r"] for t in a_]) / 100 + statistics.variance([t["r"] for t in b_]) / 100)
ok("the clustered difference with singleton clusters is Welch's, to within the degrees-of-freedom factor", abs(d["se"] / welch - 1) < 0.02, (d, welch))
tmp = Path(tempfile.mkdtemp())
rows = [(1609459200 + j * 14400, 10.0 + (j % 5), 11.0 + (j % 5), 9.0 + (j % 5), 10.5 + (j % 5)) for j in range(6000)]
for j in range(3000, 3010):
    rows[j] = (rows[j][0], 12.0, 12.0, 12.0, 12.0)                      # a ten-bar forward-filled gap
f = tmp / "GAPUSDT_4h.csv"
f.write_text('"# GAPUSDT 4h from https://api.binance.us, t,o,h,l,c, gaps forward-filled: 10"\n' + "\n".join(",".join(map(str, r)) for r in rows))
gb, gt = S2.load(f)
ok("the data rule refuses a gap longer than a day", "gap of 10 bars" in (X.qualify(f, gb, gt) or ""), X.qualify(f, gb, gt))
f.write_text('"# GAPUSDT 4h from https://api.binance.com, t,o,h,l,c, gaps forward-filled: 0"\n' + "\n".join(",".join(map(str, r)) for r in rows[:2000]))
gb, gt = S2.load(f)
ok("the data rule refuses a second feed", "not api.binance.us" in (X.qualify(f, gb, gt) or ""), X.qualify(f, gb, gt))
bb, bt = S2.load(HERE / "data" / "BTCUSDT_4h.csv")
ok("BTC's file qualifies", X.qualify(HERE / "data" / "BTCUSDT_4h.csv", bb, bt) is None)

print(f"\n{n - len(fails)} of {n} checks passed" + (f"; FAILED: {fails}" if fails else ""))
sys.exit(1 if fails else 0)
