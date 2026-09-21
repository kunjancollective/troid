#!/usr/bin/env python3
"""Trade journal analysis for funded accounts.

Stdlib only. Reads a CSV of closed trades and reports performance plus the
behavioural patterns that actually end challenges.

Expected columns (case-insensitive, extras ignored, missing ones degrade
gracefully):

  opened_at, closed_at, symbol, side, entry, exit, quantity, pnl, risk

`risk` is the dollar amount risked at entry (entry-to-stop). If absent, R-multiples
are approximated from the median loss, which is rough but still directionally useful
— say so when reporting.

  python journal.py --csv trades.csv
  python journal.py --csv trades.csv --json
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from datetime import datetime
from pathlib import Path

TIME_FORMATS = (
    "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%d %H:%M", "%Y-%m-%d", "%d/%m/%Y %H:%M", "%m/%d/%Y %H:%M",
)


def parse_time(raw: str):
    raw = (raw or "").strip().replace("+00:00", "")
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


def num(raw, default=None):
    try:
        return float(str(raw).replace(",", "").replace("$", "").strip())
    except (TypeError, ValueError):
        return default


def load_trades(path: str) -> list[dict]:
    p = Path(path)
    if not p.is_file():
        sys.exit(f"No CSV at {path}")
    rows = []
    with p.open(newline="", encoding="utf-8-sig") as fh:
        for raw in csv.DictReader(fh):
            row = {(k or "").strip().lower(): v for k, v in raw.items()}
            pnl = num(row.get("pnl"))
            if pnl is None:
                entry, exit_, qty = (num(row.get("entry")), num(row.get("exit")),
                                     num(row.get("quantity")))
                if None not in (entry, exit_, qty):
                    sign = -1 if (row.get("side", "").lower().startswith("s")) else 1
                    pnl = sign * (exit_ - entry) * qty
            if pnl is None:
                continue
            rows.append({
                "opened_at": parse_time(row.get("opened_at", "")),
                "closed_at": parse_time(row.get("closed_at", "")),
                "symbol": (row.get("symbol") or "?").upper(),
                "side": (row.get("side") or "?").lower(),
                "pnl": pnl,
                "risk": num(row.get("risk")),
            })
    rows.sort(key=lambda r: r["closed_at"] or r["opened_at"] or datetime.min)
    return rows


def r_multiples(trades: list[dict]) -> tuple[list[float], bool]:
    """Return (R values, whether they were approximated)."""
    if all(t["risk"] for t in trades):
        return [t["pnl"] / t["risk"] for t in trades], False
    losses = [abs(t["pnl"]) for t in trades if t["pnl"] < 0]
    unit = statistics.median(losses) if losses else None
    if not unit:
        return [], True
    return [t["pnl"] / unit for t in trades], True


def max_drawdown(trades: list[dict]) -> tuple[float, int]:
    peak = equity = 0.0
    worst = 0.0
    longest = run = 0
    for t in trades:
        equity += t["pnl"]
        peak = max(peak, equity)
        worst = min(worst, equity - peak)
        run = run + 1 if t["pnl"] < 0 else 0
        longest = max(longest, run)
    return worst, longest


def size_escalation(trades: list[dict]) -> dict | None:
    """Do trades get bigger right after a loss? This is the classic tell."""
    sized = [t for t in trades if t["risk"]]
    if len(sized) < 8:
        return None
    after_loss, after_win = [], []
    for prev, cur in zip(sized, sized[1:]):
        (after_loss if prev["pnl"] < 0 else after_win).append(cur["risk"])
    if not after_loss or not after_win:
        return None
    al, aw = statistics.mean(after_loss), statistics.mean(after_win)
    return {
        "avg_risk_after_loss": al,
        "avg_risk_after_win": aw,
        "escalation_pct": (al / aw - 1) * 100 if aw else 0,
        "n_after_loss": len(after_loss),
    }


def revenge_trades(trades: list[dict], minutes: int = 15) -> list[dict]:
    """Re-entries within N minutes of closing a loser."""
    out = []
    for prev, cur in zip(trades, trades[1:]):
        if prev["pnl"] >= 0 or not prev["closed_at"] or not cur["opened_at"]:
            continue
        gap = (cur["opened_at"] - prev["closed_at"]).total_seconds() / 60
        if 0 <= gap <= minutes:
            out.append({"after": prev["symbol"], "gap_min": round(gap, 1),
                        "result": cur["pnl"]})
    return out


def group_stats(trades: list[dict], key) -> list[dict]:
    buckets: dict = {}
    for t in trades:
        k = key(t)
        if k is None:
            continue
        buckets.setdefault(k, []).append(t["pnl"])
    rows = []
    for k, pnls in buckets.items():
        wins = [p for p in pnls if p > 0]
        rows.append({
            "key": k, "n": len(pnls), "pnl": sum(pnls),
            "win_rate": len(wins) / len(pnls) * 100,
        })
    return sorted(rows, key=lambda r: r["pnl"])


def analyse(trades: list[dict]) -> dict:
    if not trades:
        sys.exit("No usable trades found in the CSV.")
    pnls = [t["pnl"] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    rs, approx = r_multiples(trades)
    worst_dd, longest_streak = max_drawdown(trades)

    win_rate = len(wins) / len(trades) * 100
    avg_win = statistics.mean(wins) if wins else 0
    avg_loss = statistics.mean(losses) if losses else 0
    gross_win, gross_loss = sum(wins), abs(sum(losses))

    return {
        "n_trades": len(trades),
        "net_pnl": sum(pnls),
        "win_rate": win_rate,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "payoff_ratio": (avg_win / abs(avg_loss)) if avg_loss else None,
        "profit_factor": (gross_win / gross_loss) if gross_loss else None,
        "expectancy": statistics.mean(pnls),
        "expectancy_r": statistics.mean(rs) if rs else None,
        "r_approximated": approx,
        "best": max(pnls),
        "worst": min(pnls),
        "max_drawdown": worst_dd,
        "longest_loss_streak": longest_streak,
        "by_symbol": group_stats(trades, lambda t: t["symbol"]),
        "by_hour": group_stats(
            trades, lambda t: t["opened_at"].hour if t["opened_at"] else None),
        "by_weekday": group_stats(
            trades, lambda t: t["opened_at"].strftime("%a") if t["opened_at"] else None),
        "size_escalation": size_escalation(trades),
        "revenge_trades": revenge_trades(trades),
    }


def report(a: dict) -> None:
    print(f"{a['n_trades']} trades, net ${a['net_pnl']:,.2f}")
    print()
    print(f"Win rate       {a['win_rate']:.1f}%")
    print(f"Avg win        ${a['avg_win']:,.2f}")
    print(f"Avg loss       ${a['avg_loss']:,.2f}")
    if a["payoff_ratio"]:
        print(f"Payoff         {a['payoff_ratio']:.2f}:1")
    if a["profit_factor"]:
        print(f"Profit factor  {a['profit_factor']:.2f}")
    print(f"Expectancy     ${a['expectancy']:,.2f}/trade", end="")
    if a["expectancy_r"] is not None:
        approx = " (R approximated from median loss)" if a["r_approximated"] else ""
        print(f"  =  {a['expectancy_r']:.2f}R{approx}")
    else:
        print()
    print(f"Max drawdown   ${a['max_drawdown']:,.2f}")
    print(f"Worst streak   {a['longest_loss_streak']} losses in a row")

    print("\nBy symbol (worst first)")
    for row in a["by_symbol"][:8]:
        print(f"  {row['key']:<12} {row['n']:>3} trades  "
              f"${row['pnl']:>10,.2f}  {row['win_rate']:.0f}% win")

    worst_hours = [r for r in a["by_hour"] if r["pnl"] < 0][:3]
    if worst_hours:
        print("\nWorst hours to trade (by open time)")
        for row in worst_hours:
            print(f"  {row['key']:02d}:00        {row['n']:>3} trades  "
                  f"${row['pnl']:>10,.2f}")

    esc = a["size_escalation"]
    if esc and esc["escalation_pct"] > 15:
        print(f"\n⚠ Size escalation: you risk "
              f"{esc['escalation_pct']:.0f}% more after a loss "
              f"(${esc['avg_risk_after_loss']:,.0f} vs "
              f"${esc['avg_risk_after_win']:,.0f} after a win, "
              f"n={esc['n_after_loss']}).")

    rev = a["revenge_trades"]
    if rev:
        wins = sum(1 for r in rev if r["result"] > 0)
        total = sum(r["result"] for r in rev)
        print(f"\n⚠ {len(rev)} re-entries within 15 min of a loss — "
              f"{wins}/{len(rev)} profitable, net ${total:,.2f}.")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="journal.py")
    ap.add_argument("--csv", default="trades.csv")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    a = analyse(load_trades(args.csv))
    if args.json:
        print(json.dumps(a, indent=2, default=str))
    else:
        report(a)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
