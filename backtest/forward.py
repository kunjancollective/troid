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
  journal.csv   every closed trade, appended once, never rewritten; filled_bars counts
                the forward-filled (flat, gap-substitute) bars the trade held through.
                When the schema widens, existing rows gain the new columns from the same
                deterministic replay and keep their logged_utc: a widening, not a data change.
  runs.csv      one row per shadow run (TROID_RUN=shadow), for the ledger's runs table
  state.json    open position, budgets, binding ceiling, last bar processed
  stdout        a daily summary suitable for the worked-example post
"""
from __future__ import annotations
import csv, json, os, sys, datetime as dt
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import engine as E, engine_v2 as V

CFG = json.load(open(Path(__file__).parent / "strategy_config.json"))
BARS = Path(__file__).parent / "data" / (sys.argv[1] if len(sys.argv) > 1 else "btc_4h.csv")
JOURNAL = Path(__file__).parent / "journal.csv"
RUNS = Path(__file__).parent / "runs.csv"
STATE = Path(__file__).parent / "state.json"
JOURNAL_COLS = ["logged_utc", "exit_utc", "exit_bar", "kind", "side", "fills", "tps_hit", "bars_held",
                "reason", "pnl", "r", "filled_bars",
                # added 2026-09-22 for the visual ledger; every row is from the same replay
                "entry_utc", "entry_price", "avg_entry", "stop_price", "tp_prices", "exit_price",
                "risk_usd", "binding_at_entry", "room_at_entry", "fee_share_pct", "tranches"]


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
    # A position still open at the last bar is marked to the close with reason "eod". It is
    # not a closed trade: it stays out of the journal and shows as the heartbeat's position.
    closed = [t for t in r.trades if t["reason"] != "eod"]

    # ---- forward-filled bars: fetch_binance.py fills a feed gap with a flat bar at the
    # previous close (o == h == l == c). A real 4h bar never has zero range, so flat is the
    # fill signature. A trade that held through one is flagged, never excluded.
    flat = [i for i, b in enumerate(bars) if b[0] == b[1] == b[2] == b[3]]

    def filled_bars(t):
        return sum(1 for i in flat if t["bar"] - t["bars"] <= i <= t["bar"])

    # ---- journal: append only trades not already logged
    # Keyed on (exit_utc, side, kind): bar indices depend on where the bar file starts,
    # exit times do not, so a file that starts earlier cannot duplicate the journal.
    def key(t):
        return (bar_time(t["bar"]).isoformat(timespec="seconds"), "long" if t["side"] > 0 else "short", t["kind"])

    def row(t, logged):
        return [logged, bar_time(t["bar"]).isoformat(timespec="seconds"), t["bar"], t["kind"],
                "long" if t["side"] > 0 else "short", t["fills"], t["tps_hit"],
                t["bars"], t["reason"], round(t["pnl"], 2), round(t["r"], 4), filled_bars(t),
                bar_time(t["entry_bar"]).isoformat(timespec="seconds"), round(t["entry_price"], 2),
                round(t["avg_entry"], 2), round(t["stop_price"], 2),
                json.dumps([round(x, 2) for x in t["tp_prices"]]), round(t["exit_price"], 2),
                round(t["risk_usd"], 2), t["binding_at_entry"], round(t["room_at_entry"], 2),
                round(t["fee_share_pct"], 2), t["tranches"]]

    seen, old_rows, header = {}, [], None
    if JOURNAL.exists():
        with JOURNAL.open() as fh:
            rd = csv.DictReader(fh); header = rd.fieldnames
            for r_ in rd:
                old_rows.append(r_); seen[(r_["exit_utc"], r_["side"], r_["kind"])] = r_["logged_utc"]
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    new = [t for t in closed if key(t) not in seen]
    if header is not None and header != JOURNAL_COLS:
        # Schema widening: rewrite every row from the same replay, keeping its logged_utc.
        # Refuse if a logged row is missing from the replay or any old column would change.
        by_key = {key(t): t for t in closed}
        for r_ in old_rows:
            k = (r_["exit_utc"], r_["side"], r_["kind"])
            if k not in by_key:
                sys.exit(f"journal migration: logged trade {k} not in the replay; refusing to rewrite")
            fresh = dict(zip(JOURNAL_COLS, map(str, row(by_key[k], r_["logged_utc"]))))
            drift = {c: (r_[c], fresh[c]) for c in header if r_[c] != fresh[c]}
            if drift:
                sys.exit(f"journal migration: {k} would change {drift}; refusing to rewrite")
        with JOURNAL.open("w", newline="") as fh:
            w = csv.writer(fh); w.writerow(JOURNAL_COLS)
            for t in closed:
                w.writerow(row(t, seen.get(key(t), now)))
        print(f"  journal: schema widened to {len(JOURNAL_COLS)} columns, {len(old_rows)} rows kept their logged_utc")
    else:
        write_header = header is None
        with JOURNAL.open("a", newline="") as fh:
            w = csv.writer(fh)
            if write_header:
                w.writerow(JOURNAL_COLS)
            for t in new:
                w.writerow(row(t, now))

    # ---- state (the heartbeat). Position: when it opened and how many tranches, nothing else.
    # No direction, no entry price, no stop: the page does not broadcast a signal. That is the line.
    last = len(bars) - 1
    floor_total = E.INITIAL * (1 - E.MAXLOSS_PCT)
    balance = r.realized_balance
    daily_room = E.INITIAL * E.DAILY_PCT + r.realized_today
    floor_room = balance - floor_total
    op = r.open_position
    position = ({"open_since_utc": bar_time(op["entry_bar"]).isoformat(), "tranches_filled": op["fills"],
                 "tranches": op["tranches"]} if op else None)
    state = {"strategy": CFG["name"], "as_of_bar_utc": bar_time(last).isoformat(),
             "last_close": round(bars[last][3], 2),
             "outcome": r.outcome, "balance": round(balance, 2),
             "trades_total": len(closed), "trades_new_this_run": len(new),
             "trading_days": len(r.trading_days),
             "distance_to_floor": round(floor_room, 2),
             "daily_room": round(daily_room, 2),
             "binding": "daily" if daily_room <= floor_room else "floor",
             "position": position,
             "max_drawdown": round(r.trough_dd, 2),
             "forward_filled_bars": len(flat),
             "trades_touching_filled_bars": sum(1 for t in closed if filled_bars(t))}
    STATE.write_text(json.dumps(state, indent=2))

    # ---- runs.csv: one row per shadow run (the workflow sets TROID_RUN=shadow; local runs do not)
    if os.environ.get("TROID_RUN") == "shadow":
        write_header = not RUNS.exists()
        with RUNS.open("a", newline="") as fh:
            w = csv.writer(fh)
            if write_header:
                w.writerow(["run_utc", "as_of_bar_utc", "last_close", "balance", "trades_new", "position"])
            w.writerow([dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), state["as_of_bar_utc"],
                        state["last_close"], state["balance"], len(new), "open" if position else "flat"])

    # ---- summary for the daily post
    st = E.trade_stats(closed) if closed else {}
    print(f"troid-shadow-1  ·  as of {state['as_of_bar_utc']}  ·  close {state['last_close']:,.2f}  ·  {state['outcome'].upper()}")
    print(f"  balance ${balance:,.2f}   floor ${floor_total:,.0f}   room ${floor_room:,.0f}   daily ${daily_room:,.0f}   binding {state['binding']}")
    print(f"  position: " + (f"open since {position['open_since_utc']} · {position['tranches_filled']} of {position['tranches']} tranches" if position else "flat"))
    if st:
        print(f"  {st['n']} trades   exp {st['exp_r']:+.3f}R   PF {st['profit_factor']:.2f}   "
              f"win {st['win_rate']:.0f}%   maxDD ${r.trough_dd:,.0f}")
    print(f"  {len(new)} new trade(s) journaled"
          + (f", {sum(1 for t in new if filled_bars(t))} through a forward-filled bar" if any(filled_bars(t) for t in new) else ""))
    for t in new[-3:]:
        print(f"    {bar_time(t['bar']):%Y-%m-%d %H:%M}  {t['kind']:<9} "
              f"{'long ' if t['side']>0 else 'short'}  {t['reason']:<18} {t['r']:+.2f}R")
    print(f"  journal: {JOURNAL.name} ({len(seen)+len(new)} rows)   state: {STATE.name}")
    print("\n  This is a shadow. It places nothing. Compare it against the trial account.")


if __name__ == "__main__":
    main()
