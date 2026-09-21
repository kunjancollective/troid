#!/usr/bin/env python3
"""troid shadow runner — the strategy, run forward on live bars, as a public log.

Deterministic by design: every run replays from the anchor date on the current bar
file, so the result is a pure function of (config, bars). New bars extend it; the
journal records the diff. Nothing here places an order.

  python fetch_binance.py BTCUSDT 2026-01-08T04:00:00 data/fresh_4h.csv    # live feed
  python stitch_bars.py data/btc_4h.csv data/fresh_4h.csv data/live_4h.csv   # frozen + tail
  python forward.py live_4h.csv                                              # replay + journal

The bar file is the frozen sample the journal was built on, extended with live bars after
its last bar (see stitch_bars.py). Replaying history on a different feed is a different
sample, not more of the same one. The journal is keyed on exit time, not bar index, so a
misaligned file cannot re-append trades it already holds.

Outputs:
  journal.csv   every closed trade, appended once, never rewritten
  state.json    open position, budgets, binding ceiling, last bar processed
  stdout        a daily summary suitable for the worked-example post
"""
from __future__ import annotations
import csv, json, sys, datetime as dt
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import engine as E, engine_v2 as V

CFG = json.load(open(Path(__file__).parent / "strategy_config.json"))
BARS = Path(__file__).parent / "data" / (sys.argv[1] if len(sys.argv) > 1 else "btc_4h.csv")
JOURNAL = Path(__file__).parent / "journal.csv"
STATE = Path(__file__).parent / "state.json"


def apply_config():
    V.REGIME, V.BREAKOUT, V.LADDER = CFG["regime"], CFG["breakout"], CFG["ladder"]
    V.COMPRESS_K, V.MIN_COMP = CFG["compress_k"], CFG["min_compressed_bars"]
    V.LADDER_DIR, V.LADDER_N = CFG["ladder_dir"], CFG["ladder_n"]
    V.BREAKEVEN_AFTER_TP1, V.TPS = CFG["breakeven_after_tp1"], tuple(CFG["take_profits_r"])
    V.REVERSE_AFTER_TP3, V.REVERSE_TRIGGER = CFG["reverse"], CFG["reverse_trigger"]
    V.HOLDING = CFG["holding"]
    V.MAX_HOLD_BARS, V.MIN_TRADING_DAYS = CFG["max_hold_bars"], CFG["min_trading_days"]
    E.INITIAL, E.RISK_PCT, E.BUDGET_CAP = float(CFG["quota"]), CFG["risk_pct"], CFG["budget_cap"]
    E.FEE, E.MAX_LEV = CFG["fee_per_side"], CFG["max_leverage"]


def bar_time(i):
    return dt.datetime.fromtimestamp(E.T0 + i * E.STEP, dt.timezone.utc)


def main():
    apply_config()
    bars = E.load_bars(str(BARS))
    e20, e120, atr = E.indicators(bars)
    sigs = V.build_signals(bars, e20, e120, atr)
    warm = max(E.EMA_TREND + E.TREND_SLOPE_BARS, V.RANGE_BARS) + 1
    r = V.run(bars, sigs, warm, challenge=True, risk_pct=CFG["risk_pct"], atr=atr)

    # ---- journal: append only trades not already logged
    # Keyed on (exit_utc, side, kind): bar indices depend on where the bar file starts,
    # exit times do not, so a file that starts earlier cannot duplicate the journal.
    seen = set()
    if JOURNAL.exists():
        with JOURNAL.open() as fh:
            for row in csv.DictReader(fh):
                seen.add((row["exit_utc"], row["side"], row["kind"]))
    new = [t for t in r.trades
           if (bar_time(t["bar"]).isoformat(timespec="seconds"),
               "long" if t["side"] > 0 else "short", t["kind"]) not in seen]
    write_header = not JOURNAL.exists()
    with JOURNAL.open("a", newline="") as fh:
        w = csv.writer(fh)
        if write_header:
            w.writerow(["logged_utc", "exit_utc", "exit_bar", "kind", "side", "fills",
                        "tps_hit", "bars_held", "reason", "pnl", "r"])
        for t in new:
            w.writerow([dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                        bar_time(t["bar"]).isoformat(timespec="seconds"), t["bar"], t["kind"],
                        "long" if t["side"] > 0 else "short", t["fills"], t["tps_hit"],
                        t["bars"], t["reason"], round(t["pnl"], 2), round(t["r"], 3)])

    # ---- state
    last = len(bars) - 1
    floor_total = E.INITIAL * (1 - E.MAXLOSS_PCT)
    state = {"strategy": CFG["name"], "as_of_bar_utc": bar_time(last).isoformat(),
             "outcome": r.outcome, "balance": round(r.balance, 2),
             "trades_total": len(r.trades), "trades_new_this_run": len(new),
             "trading_days": len(r.trading_days),
             "distance_to_floor": round(r.balance - floor_total, 2),
             "max_drawdown": round(r.trough_dd, 2)}
    STATE.write_text(json.dumps(state, indent=2))

    # ---- summary for the daily post
    st = E.trade_stats(r.trades) if r.trades else {}
    print(f"troid-shadow-1  ·  as of {state['as_of_bar_utc']}  ·  {state['outcome'].upper()}")
    print(f"  balance ${r.balance:,.2f}   floor ${floor_total:,.0f}   room ${state['distance_to_floor']:,.0f}")
    if st:
        print(f"  {st['n']} trades   exp {st['exp_r']:+.3f}R   PF {st['profit_factor']:.2f}   "
              f"win {st['win_rate']:.0f}%   maxDD ${r.trough_dd:,.0f}")
    print(f"  {len(new)} new trade(s) journaled")
    for t in new[-3:]:
        print(f"    {bar_time(t['bar']):%Y-%m-%d %H:%M}  {t['kind']:<9} "
              f"{'long ' if t['side']>0 else 'short'}  {t['reason']:<18} {t['r']:+.2f}R")
    print(f"  journal: {JOURNAL.name} ({len(seen)+len(new)} rows)   state: {STATE.name}")
    print("\n  This is a shadow. It places nothing. Compare it against the trial account.")


if __name__ == "__main__":
    main()
