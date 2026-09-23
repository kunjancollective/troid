#!/usr/bin/env python3
"""Position sizing and drawdown-budget calculator for funded / prop accounts.

Stdlib only. No network: pass in price and ATR (fetch them from TradingView first).

This script never places an order. It returns parameters for a human to execute.

  python risk.py budget --config config.json
  python risk.py size --config config.json --symbol BTCUSDT --side long \
      --entry 78050 --stop 76900 --target 80400
  python risk.py size --config config.json --symbol BTCUSDT --side long \
      --entry 78050 --stop-atr 1.5 --atr 940 --target-r 2
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# ---------------------------------------------------------------- budget model


def daily_floor(cfg: dict) -> tuple[float, float]:
    """Return (floor, limit_amount) for today's loss limit.

    Bitfunded FAQ: the daily limit is a FIXED amount = daily% x INITIAL balance, resetting
    each day. Today's net P&L (equity - day_start) offsets it, so profit made today widens
    the room and loss made today narrows it. The limit itself never moves.
    """
    acct, rules = cfg["account"], cfg["rules"]
    pct = rules.get("max_daily_loss_pct", 0)
    limit = (pct / 100.0) * acct["initial_balance"]
    day_start = acct.get("day_start_balance", acct["current_balance"])
    return day_start - limit, limit


def drawdown_floor(cfg: dict) -> float:
    """Return the equity level at which the account is dead."""
    acct, rules = cfg["account"], cfg["rules"]
    pct = rules.get("max_total_drawdown_pct", 0)
    dd_type = rules.get("drawdown_type", "static")
    initial = acct["initial_balance"]

    if dd_type == "static":
        return initial - (pct / 100.0) * initial

    # trailing / trailing_eod both track a high-water mark; the config supplies
    # the EOD-only mark when the firm measures it that way.
    hwm = acct.get("high_water_mark", initial)
    floor = hwm - (pct / 100.0) * hwm
    if rules.get("trailing_stops_at_initial", False):
        # Once the floor reaches the starting balance it stops climbing.
        floor = min(floor, initial)
    return floor


def budgets(cfg: dict) -> dict:
    acct = cfg["account"]
    rules = cfg["rules"]

    # Most firms count unrealised PnL toward the daily limit, so equity is the
    # right measure. Fall back to balance when equity isn't supplied.
    equity = acct.get("current_equity", acct["current_balance"])
    measure = equity if rules.get("daily_loss_includes_unrealized", True) \
        else acct["current_balance"]

    d_floor, d_basis = daily_floor(cfg)
    dd_flr = drawdown_floor(cfg)

    d_budget = measure - d_floor
    dd_budget = equity - dd_flr

    if d_budget <= dd_budget:
        binding, effective = "daily loss limit", d_budget
    else:
        binding, effective = "max drawdown", dd_budget

    return {
        "equity": equity,
        "daily_floor": d_floor,
        "daily_basis": d_basis,
        "daily_budget": d_budget,
        "drawdown_floor": dd_flr,
        "drawdown_type": rules.get("drawdown_type", "static"),
        "drawdown_budget": dd_budget,
        "effective_budget": effective,
        "binding": binding,
    }


# ------------------------------------------------------------ circuit breakers

def circuit_breakers(cfg: dict, side: int, entry: float, stop: float, qty: float,
                     equity: float, notional: float, leverage: float) -> dict:
    """The adverse price move (as % of entry) at which each thing stops you, sorted.

    Exchange liquidation differs by margin mode; everything else does not.
      isolated: the position's own margin is exhausted.
                P = entry * (1 - 1/lev) / (1 - mmr)             (long; mirrored for short)
      cross:    the whole account backs it; liquidates when equity + pnl = maintenance.
                P = (entry - equity/qty) / (1 - mmr)             (long; mirrored for short)
    mmr = maintenance margin rate. Bitfunded's exact figure is not in their public docs;
    the default is a typical major-perp rate and is a config parameter.
    """
    rules = cfg["rules"]
    mode = rules.get("margin_mode", "cross")
    mmr = rules.get("maintenance_margin_rate", 0.005)
    b = budgets(cfg)
    stop_pct = abs(entry - stop) / entry * 100
    daily_pct = b["daily_budget"] / notional * 100 if notional else float("inf")
    floor_pct = b["drawdown_budget"] / notional * 100 if notional else float("inf")
    if mode == "isolated":
        liq_pct = (1 - (1 - 1 / leverage) / (1 - mmr)) * 100
    else:
        liq_pct = (1 - (1 - equity / notional) / (1 - mmr)) * 100 if notional > 0 else float("inf")   # <= 0: already below maintenance
    liq_pct = max(liq_pct, 0.0)
    events = sorted([("your stop", stop_pct), ("daily loss limit", daily_pct),
                     ("max loss floor", floor_pct),
                     (f"exchange liquidation ({mode})", liq_pct)], key=lambda e: e[1])
    first = events[0][0]
    warnings = []
    if first != "your stop":
        warnings.append(f"DANGER: {first} binds at {events[0][1]:.2f}% adverse, INSIDE your "
                        f"{stop_pct:.2f}% stop. The stop cannot save you at this size.")
    if mode == "cross" and liq_pct > floor_pct:
        warnings.append("Cross margin: exchange liquidation is beyond the firm's floor. Nothing "
                        "cuts a runaway position before the firm fails you; your stop is the "
                        "only circuit breaker in front of the floor.")
    if mode == "isolated" and liq_pct < floor_pct:
        warnings.append(f"Isolated margin: the exchange would liquidate this position at "
                        f"{liq_pct:.1f}% adverse for its own ${notional/leverage:,.0f} margin, "
                        f"before the firm's floor. A runaway costs the margin, not the account.")
    return {"margin_mode": mode, "order": events, "first_to_bind": first,
            "runaway_max_loss": (notional / leverage) if mode == "isolated" else min(notional, b["drawdown_budget"]),
            "warnings": warnings}


# ----------------------------------------------------------------- sizing math


def resolve_stop(args, entry: float) -> float:
    sign = -1 if args.side == "long" else 1
    if args.stop is not None:
        return args.stop
    if args.stop_atr is not None:
        if args.atr is None:
            sys.exit("--stop-atr needs --atr <value> (fetch ATR from TradingView first)")
        return entry + sign * args.stop_atr * args.atr
    if args.stop_pct is not None:
        return entry + sign * (args.stop_pct / 100.0) * entry
    sys.exit("Give a stop: --stop, --stop-atr (with --atr), or --stop-pct")


def resolve_target(args, entry: float, stop: float) -> float | None:
    sign = 1 if args.side == "long" else -1
    if args.target is not None:
        return args.target
    if args.target_r is not None:
        return entry + sign * args.target_r * abs(entry - stop)
    if args.target_pct is not None:
        return entry + sign * (args.target_pct / 100.0) * entry
    return None


def size_trade(cfg: dict, args) -> dict:
    b = budgets(cfg)
    rules, risk_cfg = cfg["rules"], cfg.get("risk", {})

    entry = args.entry
    stop = resolve_stop(args, entry)
    target = resolve_target(args, entry, stop)

    stop_dist = abs(entry - stop)
    notes: list[str] = []
    blocks: list[str] = []

    # Direction sanity — a stop on the wrong side silently inverts the trade.
    if args.side == "long" and stop >= entry:
        blocks.append(f"Stop {stop:,.2f} is at or above entry {entry:,.2f} on a long.")
    if args.side == "short" and stop <= entry:
        blocks.append(f"Stop {stop:,.2f} is at or below entry {entry:,.2f} on a short.")
    if stop_dist <= 0:
        blocks.append("Stop distance is zero.")

    # How much may this trade risk?
    balance_risk = (risk_cfg.get("default_risk_pct_of_balance", 0.5) / 100.0) \
        * cfg["account"]["current_balance"]
    budget_cap = (risk_cfg.get("max_risk_pct_of_daily_budget", 35) / 100.0) \
        * max(b["effective_budget"], 0)

    if args.risk_usd is not None:
        intended = args.risk_usd
        risk_source = "user-specified"
    elif args.risk_pct is not None:
        intended = (args.risk_pct / 100.0) * cfg["account"]["current_balance"]
        risk_source = "user-specified %"
    else:
        intended = balance_risk
        risk_source = "config default"

    risk_amount = min(intended, budget_cap)
    reduced = risk_amount < intended - 1e-9

    if b["effective_budget"] <= 0:
        blocks.append(
            f"No budget left — {b['binding']} is already breached or at the line."
        )
    elif risk_amount <= 0:
        blocks.append("Budget cap leaves nothing to risk on this trade.")

    result = {
        "symbol": args.symbol,
        "side": args.side,
        "entry": entry,
        "stop": stop,
        "target": target,
        "stop_distance": stop_dist,
        "stop_distance_pct": (stop_dist / entry * 100) if entry else 0,
        "intended_risk": intended,
        "risk_source": risk_source,
        "budget_cap": budget_cap,
        "risk_amount": risk_amount,
        "reduced_by_budget": reduced,
        **{f"budget_{k}": v for k, v in b.items()},
    }

    if blocks:
        result.update({"verdict": "BLOCK", "reasons": blocks, "notes": notes})
        return result

    # Size from risk and stop distance, net of round-trip fees.
    # Fees scale with NOTIONAL, and notional scales inversely with stop distance,
    # so tight stops are disproportionately expensive. Solve for quantity where
    # stop loss + both fee legs together consume the risk budget.
    fee_rate = rules.get("fee_pct_per_side", 0.0) / 100.0
    fee_per_unit = entry * fee_rate * 2
    qty = risk_amount / (stop_dist + fee_per_unit)
    notional = qty * entry
    fees = qty * fee_per_unit
    loss_at_stop = qty * stop_dist

    fee_share = (fees / risk_amount * 100) if risk_amount else 0
    warn_at = risk_cfg.get("warn_fee_share_of_risk_pct", 15)
    if fee_share > warn_at:
        notes.append(
            f"Fees are {fee_share:.0f}% of your risk (${fees:,.2f} on "
            f"${notional:,.0f} notional). The stop is tight enough that costs "
            f"dominate — widen it or accept the drag."
        )

    max_lev = rules.get("max_leverage", 5)
    leverage = args.leverage if args.leverage is not None else max_lev
    if leverage > max_lev:
        blocks.append(f"Leverage {leverage}x exceeds the {max_lev}x cap.")
    margin = notional / leverage if leverage else float("inf")

    free = b["equity"]
    if margin > free:
        blocks.append(
            f"Margin ${margin:,.2f} exceeds equity ${free:,.2f} — "
            f"needs {notional / free:,.1f}x to hold this size."
        )

    rr = None
    if target is not None:
        reward = abs(target - entry)
        rr = reward / stop_dist if stop_dist else None
        min_rr = risk_cfg.get("min_rr")
        if min_rr and rr is not None and rr < min_rr:
            notes.append(f"R:R {rr:.2f} is below the {min_rr} minimum in config.")
    elif rules.get("require_tp_and_sl", True):
        blocks.append("No take profit set, and the firm requires one on every order.")

    consumes = (risk_amount / b["effective_budget"] * 100) \
        if b["effective_budget"] > 0 else 100.0

    if reduced:
        notes.append(
            f"Cut from ${intended:,.2f} to ${risk_amount:,.2f} — "
            f"the {b['binding']} budget caps it."
        )
    # epsilon guards the exact-integer boundary where float // returns n-1
    losers_left = int(b["effective_budget"] / risk_amount + 1e-9) if risk_amount > 0 else 0
    notes.append(f"{losers_left} more losses at this size before {b['binding']} trips.")

    cb = circuit_breakers(cfg, 1 if args.side == "long" else -1, entry, stop, qty,
                          b["equity"], notional, leverage)
    notes.extend(cb["warnings"])
    verdict = "BLOCK" if blocks else ("REDUCE" if reduced else "OK")
    result.update({
        "circuit_breakers": cb,
        "quantity": qty,
        "notional": notional,
        "fees": fees,
        "fee_share_of_risk": fee_share,
        "loss_at_stop": loss_at_stop,
        "leverage": leverage,
        "margin": margin,
        "rr": rr,
        "consumes_pct_of_budget": consumes,
        "losses_remaining": losers_left,
        "verdict": verdict,
        "reasons": blocks,
        "notes": notes,
    })
    return result


# -------------------------------------------------------------------- printing


def money(x) -> str:
    return f"${x:,.2f}" if isinstance(x, (int, float)) else str(x)


def print_budget(b: dict, name: str = "") -> None:
    if name:
        print(f"Profile           {name}")
    print(f"Equity            {money(b['equity'])}")
    print(f"Daily floor       {money(b['daily_floor'])}   "
          f"(basis {money(b['daily_basis'])})")
    print(f"Daily budget      {money(b['daily_budget'])}")
    print(f"Drawdown floor    {money(b['drawdown_floor'])}   "
          f"({b['drawdown_type']})")
    print(f"Drawdown budget   {money(b['drawdown_budget'])}")
    print()
    print(f"BINDING: {b['binding']} — {money(b['effective_budget'])} of room")


def print_size(r: dict) -> None:
    print(f"{r['verdict']} — binding constraint is {r['budget_binding']}")
    print()
    if r["verdict"] != "BLOCK":
        print(f"Size        {r['quantity']:.6g} {r['symbol']}  "
              f"({money(r['notional'])} notional, "
              f"{money(r['margin'])} margin at {r['leverage']:g}x)")
        print(f"Entry       {r['entry']:,.2f}")
        print(f"Stop        {r['stop']:,.2f}  "
              f"({r['stop_distance_pct']:.2f}% away)")
        if r.get("target") is not None:
            rr = f"{r['rr']:.2f}R" if r.get("rr") else "—"
            print(f"Target      {r['target']:,.2f}  ({rr})")
        print(f"Risk        {money(r['risk_amount'])}  "
              f"({money(r['loss_at_stop'])} at stop + "
              f"{money(r['fees'])} fees, {r['fee_share_of_risk']:.0f}% fees)")
        print(f"Budget      {money(r['budget_effective_budget'])} remaining "
              f"(floor {money(r['budget_drawdown_floor'])})")
        print(f"Consumes    {r['consumes_pct_of_budget']:.0f}% of what's left")
        cb = r["circuit_breakers"]
        print(f"Breakers    [{cb['margin_mode']}]  " + "  →  ".join(
            f"{n} {v:.2f}%" if v != float("inf") else f"{n} —" for n, v in cb["order"]))
        print()
    for reason in r.get("reasons", []):
        print(f"  BLOCK: {reason}")
    if r["verdict"] != "BLOCK":
        for note in r.get("notes", []):
            print(f"  note: {note}")


# ------------------------------------------------------------------------ main


def load_config(path: str, profile: str | None = None) -> dict:
    """Load config and overlay the active challenge profile onto rules.

    Profiles let one config serve 1-Step, both 2-Step stages and the funded
    Trader stage. The entry strategy is rule-agnostic; only sizing changes.
    """
    p = Path(path)
    if not p.is_file():
        sys.exit(f"No config at {path}. Copy config.example.json to config.json.")
    cfg = json.loads(p.read_text())
    name = profile or cfg.get("active_profile")
    profiles = cfg.get("profiles", {})
    if name:
        if name not in profiles:
            sys.exit(f"Unknown profile {name!r}. Available: {', '.join(profiles)}")
        cfg["rules"].update({k: v for k, v in profiles[name].items()
                             if not k.startswith("_")})
        cfg["_active"] = profiles[name].get("_name", name)
    return cfg


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="risk.py")
    ap.add_argument("--config", default="config.json")
    ap.add_argument("--profile", help="1step | 2step_s1 | 2step_s2 | trader")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    # also accepted after the subcommand; SUPPRESS keeps the subparser from
    # overwriting a flag given before it
    jsonflag = dict(action="store_true", default=argparse.SUPPRESS,
                    help="machine-readable output")
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("budget"); b.add_argument("--json", **jsonflag)

    s = sub.add_parser("size"); s.add_argument("--json", **jsonflag)
    s.add_argument("--symbol", required=True)
    s.add_argument("--side", required=True, choices=["long", "short"])
    s.add_argument("--entry", type=float, required=True)
    s.add_argument("--stop", type=float)
    s.add_argument("--stop-pct", dest="stop_pct", type=float)
    s.add_argument("--stop-atr", dest="stop_atr", type=float)
    s.add_argument("--atr", type=float, help="ATR value from TradingView")
    s.add_argument("--target", type=float)
    s.add_argument("--target-r", dest="target_r", type=float)
    s.add_argument("--target-pct", dest="target_pct", type=float)
    s.add_argument("--leverage", type=float)
    s.add_argument("--risk-usd", dest="risk_usd", type=float)
    s.add_argument("--risk-pct", dest="risk_pct", type=float)

    args = ap.parse_args(argv)
    args.json = getattr(args, "json", False)
    cfg = load_config(args.config, args.profile)

    if args.cmd == "budget":
        b = budgets(cfg)
        if args.json:
            print(json.dumps(b, indent=2))
        else:
            print_budget(b, cfg.get("_active", ""))
        return 0

    r = size_trade(cfg, args)
    if args.json:
        print(json.dumps(r, indent=2, default=str))
    else:
        print_size(r)
    return 1 if r["verdict"] == "BLOCK" else 0


if __name__ == "__main__":
    raise SystemExit(main())
