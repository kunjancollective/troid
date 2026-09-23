#!/usr/bin/env python3
"""troid MCP server — prop-firm risk and compliance as tools.

Connect alongside a market-data server (TradingView) and your AI can size a setup
against the real rule set and check it for disqualification risk, in conversation.

  pip install "mcp[cli]"
  python server.py                    # stdio

Design constraints, deliberate:
  - No tool places, modifies or closes an order. Ever.
  - No tool generates an entry signal. troid evaluates ideas, it doesn't produce them.
    Bitfunded ToU 14(d)(v) prohibits using marketed strategies to pass an evaluation,
    so a signal tool would put users in breach of the agreement they signed.
  - No credential handling. Account state is passed in as numbers by the caller.
  - Arithmetic is shared with scripts/risk.py. Do not fork it; import it.
"""
from __future__ import annotations
import sys, math, json
from pathlib import Path

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    sys.exit("pip install 'mcp[cli]'")

mcp = FastMCP("troid")

# Rule sets. Percentages, so they hold for every account size the firm offers.
PROFILES = {
    "1step":    {"name": "Bitfunded 1-Step",       "daily": 4.0, "maxloss": 6.0,
                 "target": 10.0, "min_days": 5},
    "2step_s1": {"name": "Bitfunded 2-Step Stage 1","daily": 5.0, "maxloss": 10.0,
                 "target": 8.0,  "min_days": 5},
    "2step_s2": {"name": "Bitfunded 2-Step Stage 2","daily": 5.0, "maxloss": 8.0,
                 "target": 5.0,  "min_days": 5},
    # Trader Stage (funded) limits by path: help centre, Challenge & Trader Stage (read 2026-09-23 via the
    # owner's research session). 80% split and 1:5 leverage on each; any Trader Stage breach disqualifies.
    "trader_1step":   {"name": "Bitfunded Trader Stage after the 1-Step", "daily": 4.0, "maxloss": 6.0,
                       "target": 0.0, "min_days": 0},
    "trader_express": {"name": "Bitfunded Trader Stage after the Express", "daily": 3.0, "maxloss": 3.0,
                       "target": 0.0, "min_days": 0},
    "trader_2step":   {"name": "Bitfunded Trader Stage after the 2-Step", "daily": 5.0, "maxloss": 8.0,
                       "target": 0.0, "min_days": 0},
    "instant":  {"name": "Bitfunded Instant Funding", "daily": 3.0, "maxloss": 6.0,
                 "target": 0.0,  "min_days": 0,
                 "_note": "Confirmed from Bitfunded blog 2026-08-28: 3% daily, 6% static, no target, "
                          "60% split. RTP: 55% concentration ladder start, 3 closed trades min."},
    "express":  {"name": "Bitfunded 1-Step Express", "daily": 3.0, "maxloss": 3.0,
                 "target": 9.0,  "min_days": 5,
                 "_note": "Daily and max are the SAME size. Crossover is the starting balance: "
                          "both ceilings bind from the first dollar lost. Target 9% per the help "
                          "centre (Challenge & Trader Stage); the 28 Aug 2026 blog says 3%; the "
                          "Terms are silent on Express."},
}
FEE_PER_SIDE = 0.0004        # 0.04% on notional, each side
MAX_LEVERAGE = 5.0
MAX_OPEN_TRADES = 5          # Restricted Trading Practices s.3 (ToU 14(d)(xi) says 10; help centre is newer and stricter)
MAJORS = {"BTC","ETH","BNB","XRP","SOL","TRX","HYPE","ZEC","DOGE","ADA"}
HOLD_DAYS = {"major": 10, "minor": 7, "tradfi": 5}      # RTP s.1, tiered by asset class
PENALTY_LADDER = [(65,50),(75,60),(90,65),(96,70)]       # RTP s.2: margin% threshold -> payout penalty %
PENALTY_LADDER_IF = [(55,50),(65,55),(75,60),(90,65),(96,70)]   # Instant Funding
MIN_CLOSED_TRADES = {"default": 2, "instant": 3}         # RTP s.4, per stage, each open >= 10 min
MAX_MARGIN_PCT = 65.0        # first rung of the ladder
MMR = 0.005                  # maintenance margin rate; Bitfunded's exact figure unconfirmed
BUDGET_CAP_PCT = 35.0        # troid default: cap a trade at this share of remaining budget


def _budgets(quota, equity, day_start, prof):
    p = PROFILES[prof]
    daily_limit = quota * p["daily"] / 100            # FIXED from initial (Bitfunded FAQ)
    daily_floor = day_start - daily_limit
    dd_floor = quota * (1 - p["maxloss"] / 100)
    daily_budget = equity - daily_floor
    dd_budget = equity - dd_floor
    if daily_budget <= dd_budget:
        binding, eff = "daily loss limit", daily_budget
    else:
        binding, eff = "max drawdown", dd_budget
    # equity at which the two ceilings swap, on a fresh day
    crossover = dd_floor + daily_limit
    return dict(profile=p["name"], daily_floor=daily_floor, daily_budget=daily_budget,
                dd_floor=dd_floor, dd_budget=dd_budget, binding=binding,
                effective_budget=eff, crossover_equity=crossover)


@mcp.tool()
def check_budget(quota: float, equity: float, day_start_balance: float,
                 profile: str = "1step") -> dict:
    """How much room is left, and which of the two loss ceilings actually binds.

    A funded account has two ceilings that bind at different times. Traders blow
    challenges by sizing against the one that isn't currently binding. Below the
    crossover equity the static max loss governs and the advertised daily limit is
    irrelevant.

    profile: 1step | 2step_s1 | 2step_s2 | express | instant | trader_1step | trader_express | trader_2step
    """
    if profile not in PROFILES:
        return {"error": f"unknown profile. options: {', '.join(PROFILES)}"}
    b = _budgets(quota, equity, day_start_balance, profile)
    b["note"] = (f"Size against {b['binding']}: ${b['effective_budget']:,.2f}. "
                 f"Ceilings swap at ${b['crossover_equity']:,.2f} equity.")
    return b


@mcp.tool()
def _breakers(mode, side, entry, stop, equity, notional, leverage, daily_budget, dd_budget):
    stop_pct = abs(entry - stop) / entry * 100
    daily_pct = daily_budget / notional * 100
    floor_pct = dd_budget / notional * 100
    if mode == "isolated":
        liq = (1 - (1 - 1 / leverage) / (1 - MMR)) * 100
    else:
        liq = (1 - (1 - equity / notional) / (1 - MMR)) * 100 if notional > 0 else 1e9   # <= 0: already below maintenance
    order = sorted([("your stop", stop_pct), ("daily loss limit", daily_pct),
                    ("max loss floor", floor_pct), (f"exchange liquidation ({mode})", max(liq, 0))],
                   key=lambda e: e[1])
    warn = []
    if order[0][0] != "your stop":
        warn.append(f"DANGER: {order[0][0]} binds at {order[0][1]:.2f}% adverse, inside your "
                    f"{stop_pct:.2f}% stop. The stop cannot save you at this size.")
    if mode == "cross" and liq > floor_pct:
        warn.append("Cross margin: nothing cuts a runaway position before the firm's floor. "
                    "Your stop is the only circuit breaker in front of it.")
    if mode == "isolated" and liq < floor_pct:
        warn.append(f"Isolated margin: the exchange liquidates this position at {liq:.1f}% "
                    f"adverse for its own margin, before the firm's floor.")
    return {"margin_mode": mode, "first_to_bind": order[0][0],
            "order": [{"event": e, "adverse_move_pct": round(v, 2) if v < 1e8 else None} for e, v in order],
            "runaway_max_loss": round(notional / leverage if mode == "isolated" else min(notional, dd_budget), 2),
            "warnings": warn}


@mcp.tool()
def size_trade(quota: float, equity: float, day_start_balance: float,
               side: str, entry: float, stop: float,
               target: float = 0.0, target_r: float = 0.0,
               risk_pct_of_balance: float = 0.5, leverage: float = 5.0,
               profile: str = "1step", margin_mode: str = "cross") -> dict:
    """Size a trade the user is considering, net of fees, against the binding ceiling.

    This evaluates an idea the user brings. It does not generate one. Returns a
    verdict (OK / REDUCE / BLOCK), position size, margin, the fee share of risk, and
    how many further losses the account survives at this size.

    side: "long" or "short". Give target OR target_r, not both.
    margin_mode: "cross" (Bitfunded default) or "isolated". Changes only the order of
    circuit breakers, never the risk arithmetic.
    """
    if profile not in PROFILES:
        return {"error": f"unknown profile. options: {', '.join(PROFILES)}"}
    s = 1 if side.lower().startswith("l") else -1
    b = _budgets(quota, equity, day_start_balance, profile)
    d = abs(entry - stop)
    blocks, notes = [], []

    if s > 0 and stop >= entry:
        blocks.append("Stop is at or above entry on a long.")
    if s < 0 and stop <= entry:
        blocks.append("Stop is at or below entry on a short.")
    if d <= 0:
        blocks.append("Stop distance is zero.")
    if b["effective_budget"] <= 0:
        blocks.append(f"No budget left — {b['binding']} already breached.")
    if leverage > MAX_LEVERAGE:
        blocks.append(f"Leverage {leverage}x exceeds the {MAX_LEVERAGE}x firm cap.")
    if blocks:
        return {"verdict": "BLOCK", "reasons": blocks, **b}

    intended = risk_pct_of_balance / 100 * equity
    cap = BUDGET_CAP_PCT / 100 * max(b["effective_budget"], 0)
    risk = min(intended, cap)
    reduced = risk < intended - 1e-9

    fee_unit = entry * FEE_PER_SIDE * 2
    qty = risk / (d + fee_unit)
    notional = qty * entry
    margin = notional / leverage
    fees = qty * fee_unit
    fee_share = fees / risk * 100 if risk else 0.0
    tgt = target if target else (entry + s * target_r * d if target_r else 0.0)
    rr = abs(tgt - entry) / d if tgt else None
    consumes = risk / b["effective_budget"] * 100
    losses_left = math.floor(b["effective_budget"] / risk + 1e-9) if risk > 0 else 0

    margin_pct = margin / equity * 100
    if margin_pct > MAX_MARGIN_PCT:
        blocks.append(f"Margin is {margin_pct:.0f}% of capital — ToU 14(d)(xii) treats "
                      f"above ~{MAX_MARGIN_PCT:.0f}% as excessive risk.")
    if fee_share > 15:
        notes.append(f"Fees are {fee_share:.0f}% of risk (${fees:,.2f} on ${notional:,.0f} "
                     f"notional). Notional scales inversely with stop distance, so tight "
                     f"stops are punished hardest.")
    if reduced:
        notes.append(f"Cut from ${intended:,.2f} to ${risk:,.2f} — the {b['binding']} "
                     f"budget caps it at {BUDGET_CAP_PCT:.0f}% of what remains.")
    notes.append(f"{losses_left} more losses at this size before {b['binding']} trips.")
    notes.append(f"Leverage does not change this loss. At the stop you lose ${risk:,.2f} "
                 f"whether you use 2x or 25x; leverage sets margin and liquidation distance.")

    cb = _breakers(margin_mode, s, entry, stop, equity, notional, leverage,
                   b["daily_budget"], b["dd_budget"])
    notes.extend(cb["warnings"])
    verdict = "BLOCK" if blocks else ("REDUCE" if reduced else "OK")
    return {"verdict": verdict, "reasons": blocks, "notes": notes, "circuit_breakers": cb,
            "quantity": round(qty, 8), "notional": round(notional, 2),
            "margin": round(margin, 2), "margin_pct_of_equity": round(margin_pct, 2),
            "risk": round(risk, 2), "fees": round(fees, 2),
            "fee_share_of_risk_pct": round(fee_share, 2),
            "stop_distance_pct": round(d / entry * 100, 3),
            "target": round(tgt, 2) if tgt else None,
            "rr": round(rr, 2) if rr else None,
            "consumes_pct_of_budget": round(consumes, 1),
            "losses_remaining": losses_left, **b}


@mcp.tool()
def asset_class(symbol: str) -> str:
    """major | minor | tradfi, per Bitfunded's hold-duration tiers."""
    base = symbol.upper().split(":")[-1].replace("USDT","").replace("USD","")
    if base in MAJORS: return "major"
    if base in {"XAU","XAG","GOLD","SILVER","TSLA","NVDA","AAPL","NDX","DJI","SPX"} or len(base) <= 4 and not base.isalpha(): return "tradfi"
    return "minor"


@mcp.tool()
def check_compliance(hold_days: float = 0.0, open_trades: int = 1,
                     margin_pct_of_capital: float = 0.0, trading_days_so_far: int = 0,
                     uses_third_party_strategy: bool = False,
                     accounts_at_this_level: int = 1, profile: str = "1step",
                     symbol: str = "BTCUSDT", closed_trades_this_stage: int = 0) -> dict:
    """Check a trade plan against firm rules that cause disqualification.

    These are the rules people breach without knowing, because they live in the Terms
    rather than on the challenge page. Returns findings with severity and section refs.
    """
    p = PROFILES.get(profile, PROFILES["1step"])
    findings = []
    cls = asset_class(symbol); cap_days = HOLD_DAYS[cls]
    if hold_days > cap_days:
        findings.append({"severity": "breach", "rule": "RTP s.1 / ToU 14(d)(x)",
            "detail": f"Position held {hold_days:.1f} days exceeds the {cap_days}-day maximum "
                      f"for {cls} assets ({symbol}). Majors 10d, other crypto 7d, TradFi 5d."})
    if open_trades > MAX_OPEN_TRADES:
        findings.append({"severity": "breach", "rule": "RTP s.3",
            "detail": f"{open_trades} simultaneous trades exceeds the {MAX_OPEN_TRADES} cap "
                      f"(the ToU says 10; the help centre says 5 and is newer)."})
    ladder = PENALTY_LADDER_IF if profile == "instant" else PENALTY_LADDER
    pen = next((pct for thr, pct in reversed(ladder) if margin_pct_of_capital >= thr), None)
    if pen:
        findings.append({"severity": "penalty", "rule": "RTP s.2",
            "detail": f"Margin at {margin_pct_of_capital:.0f}% of capital sits on the concentration "
                      f"ladder: {pen}% payout penalty at review. Ladder starts at "
                      f"{ladder[0][0]}% for this profile."})
    need = MIN_CLOSED_TRADES["instant" if profile == "instant" else "default"]
    if 0 < closed_trades_this_stage < need:
        findings.append({"severity": "warning", "rule": "RTP s.4",
            "detail": f"{closed_trades_this_stage} closed trades this stage; {need} required "
                      f"(each open >= 10 min) before a payout request."})
    if uses_third_party_strategy:
        findings.append({"severity": "breach", "rule": "ToU 14(d)(v)",
            "detail": "Using a third-party or marketed strategy to pass an evaluation is "
                      "prohibited. Buying a bot, signal service or strategy pack and "
                      "running it on a challenge may void the account regardless of result."})
    if accounts_at_this_level > 1:
        findings.append({"severity": "breach", "rule": "ToU 6(b)",
            "detail": f"{accounts_at_this_level} accounts at one challenge level. Limit is "
                      f"one active account per level without written consent."})
    if p["min_days"] and 0 < trading_days_so_far < p["min_days"]:
        findings.append({"severity": "warning", "rule": "ToU 9(a)",
            "detail": f"{trading_days_so_far} trading days so far; {p['min_days']} required "
                      f"to clear the stage. Note the challenge page displays 0 — the "
                      f"contract governs."})
    clear = not findings
    findings = findings or [{"severity": "ok", "rule": "—",
                             "detail": "No breach detected against the rules modelled here."}]
    # Prohibited practices a trade plan cannot show: stated every time, as information.
    findings += [{"severity": "info", "rule": "ToU 14(d)(ix)",
                  "detail": "Switching strategies between the assessment account and the funded "
                            "account is prohibited. troid cannot check this from the inputs."},
                 {"severity": "info", "rule": "ToU 13(c)(v)",
                  "detail": "Opposite positions across connected accounts are prohibited, such as a "
                            "long on one account and a short on the same asset on another. troid "
                            "cannot check this from the inputs."}]
    return {"profile": p["name"], "clear": clear, "findings": findings,
            "caveat": "Checks only the rules modelled above; findings marked info are rules troid "
                      "cannot check from the inputs. Not a substitute for reading the firm's "
                      "Terms. Verify anything material with the firm directly."}


@mcp.tool()
def explain_rule(topic: str) -> dict:
    """Explain a prop-firm rule and why it matters, with the arithmetic.

    topics: crossover, reset, fees, leverage, drawdown, ladder, ruin, min_days,
            hold_limit, accounts, marketed_strategies, strategy_switching,
            opposite_positions, funded_stage
    """
    t = topic.lower().strip().replace(" ", "_")
    lib = {
      "crossover": "A funded account has two loss ceilings. Under Bitfunded the daily limit "
        "is a FIXED amount from the initial balance (FAQ); the max loss is a fixed floor from "
        "your starting quota. They swap where the day-start balance equals "
        "quota*(1 - maxloss + daily). On a $100k 1-Step that is $98,000 — only $2,000 below "
        "the start. A day that starts below $98,000 is bound by the max-loss floor, and the "
        "4% daily limit is not the constraint that day; above it, the daily limit binds. "
        "Intraday, which ceiling binds depends on that day's starting balance, not on equity "
        "alone. Size against the smaller of the two, always.",
      "reset": "Bitfunded's trading day resets at 00:00 UTC+8 = 16:00 UTC, which is noon in "
        "New York. Not midnight. Because of the platform's settlement process the reset can "
        "take effect any time between 00:00 and 00:10 UTC+8 (help centre, Criteria to be "
        "Success): 16:00-16:10 UTC. Those ten minutes are ambiguous; do not count on a fresh "
        "daily budget until 16:10 UTC. Morning and afternoon sessions draw on separate daily "
        "budgets. The trap: a floating loss that survives the reset counts in full against "
        "the new day, because the prior day's profit does not carry over. A position inside "
        "the limit at 11:59 can breach at 12:01 without price moving.",
      "fees": "0.04% per side on notional, 0.08% round trip. Notional scales inversely with "
        "stop distance, so tight stops are punished hardest. Fee share of risk = 2f/(s+2f). "
        "At a 3.9% stop that's 2% of risk; at a 0.3% scalp stop it's 21%.",
      "leverage": "Leverage does not determine your loss — the stop does. risk = "
        "|entry-stop| x quantity, and leverage appears nowhere in it. What leverage changes "
        "is margin posted and liquidation distance. Under ISOLATED margin that distance is "
        "roughly entry x (1 - 1/leverage): ~20% at 5x. Under CROSS margin the whole account "
        "backs the position, so at any size a 5x cap allows the firm's own 4%/6% floors are "
        "breached long before exchange liquidation. troid models cross margin by default; it "
        "has no recorded source for which margin modes Bitfunded offers. See 'cross'.",
      "cross": "Under cross margin, troid's default model (troid has no recorded source for "
        "Bitfunded's margin modes; the 5x leverage cap is from the help centre, Criteria to be "
        "Success), every position is backed by the entire account balance. Consequence one: exchange liquidation never binds — even at the 65% "
        "margin cap it sits at ~31% adverse move while the 6% floor binds at 1.85%. The firm's "
        "floors ARE your liquidation model. Consequence two: nothing cuts a runaway position "
        "before the firm fails you. Under isolated, the exchange would liquidate at ~20% for "
        "the position's own margin and the account survives; under cross the same runaway "
        "carries the whole account to the 6% floor. Your stop is the only circuit breaker in "
        "front of the firm's. Consequence three, the danger zone: at the 65% margin cap the "
        "daily limit binds at a 1.23% adverse move — TIGHTER than a normal 1.66% stop. At that "
        "size your stop sits behind the breach line and cannot save you.",
      "drawdown": "Bitfunded's max loss is STATIC — measured from the account quota, not a "
        "high-water mark. So profit permanently widens the buffer: up $3,000 and the floor "
        "is unchanged while your room grows. The opening stretch is the dangerous one, and "
        "the account gets structurally safer the further ahead it gets. Trailing drawdown "
        "at other firms works the opposite way.",
      "ladder": "Scaling in does not increase position size at fixed risk — it decreases it. "
        "With the stop anchored to the first entry's structure, later tranches sit further "
        "from the stop and earn less quantity. Five strength tranches hold about 34% LESS "
        "than a single entry at the same risk. The benefit is conditionality: you fill more "
        "on trades that work than on trades that don't.",
      "ruin": "Under a proportional cap (risk at most c of the REMAINING budget), budget "
        "after n losses is B(1-c)^n — it approaches zero without reaching it, so ruin by "
        "realized losses is unreachable and the real failure mode is a stalled account. "
        "Uncapped, a fixed fraction f of quota reaches the floor in floor(maxloss/f) losses: "
        "12 at 0.5%, 6 at 1%, 3 at 2%. At a professional +0.35R edge, 1% uncapped blows up "
        "68% of the time within a year; 2% is 98%. Under a cap, zero.",
      "min_days": "Five trading days minimum to clear a stage (ToU 9(a)). The challenge page "
        "displays 0. The contract governs. The bad failure mode is hitting your profit target "
        "in three days and being unable to clear the stage.",
      "hold_limit": "No position may stay open more than 10 consecutive calendar days "
        "(ToU 14(d)(x)). Profits from a breaching trade can be removed from payout eligibility.",
      "accounts": "One active account per challenge level without written consent (ToU 6(b)). "
        "Across all seven levels that caps simultaneous capital at $355,000 — not ten copies "
        "of the largest account, which is what most multi-account plans assume.",
      "marketed_strategies": "ToU 14(d)(v) prohibits using third-party or marketed strategies "
        "to pass an evaluation. Buying a bot, signal service or strategy pack and running it "
        "on a challenge may place you in breach regardless of how it performs. This is why "
        "troid evaluates trades rather than generating them.",
      "strategy_switching": "ToU 14(d)(ix) prohibits switching strategies between assessment "
        "and funded accounts. A trade plan cannot show it, so troid cannot check it; it is a "
        "rule about how the account is traded over time, not about one trade.",
      "opposite_positions": "ToU 13(c)(v) prohibits opposite positions across connected "
        "accounts: a long on one account and a short on the same asset on another. Hedged "
        "pairs cancel each other's market risk while each account keeps its own chance of "
        "passing, which is why firms prohibit them. troid cannot see connected accounts.",
      "funded_stage": "Trader Stage limits depend on the path (help centre, Challenge & Trader "
        "Stage): after the 1-Step 4% daily / 6% max, after the Express 3% / 3%, after the "
        "2-Step 5% / 8%, each with an 80% split; Instant 3% / 6% with a 60% split; leverage "
        "1:5 on each. Any Trader Stage breach disqualifies the account, and a new challenge "
        "is required.",
    }
    if t not in lib:
        return {"error": f"unknown topic. options: {', '.join(sorted(lib))}"}
    return {"topic": t, "explanation": lib[t],
            "tier": "DERIVED or SOURCED — run verify_claims.py in the repo to reproduce."}


@mcp.tool()
def asset_cost(price: float, atr: float, atr_multiple: float = 1.5,
               risk: float = 500.0, leverage: float = 5.0) -> dict:
    """What a given asset costs you to trade, from its price and ATR.

    Fee drag depends only on stop distance as a percentage of price — the instrument is
    irrelevant. But with ATR-based stops the asset's normalised volatility sets that
    percentage, so the asset decides your drag indirectly. Works on any instrument the
    firm lists, crypto or otherwise.
    """
    atr_pct = atr / price * 100
    stop_dist = atr_multiple * atr
    stop_frac = stop_dist / price
    fee_unit = price * FEE_PER_SIDE * 2
    qty = risk / (stop_dist + fee_unit)
    notional = qty * price
    drag = 2 * FEE_PER_SIDE / (stop_frac + 2 * FEE_PER_SIDE) * 100
    min_stop_5 = 2 * FEE_PER_SIDE * 95 / 5
    return {
        "atr_pct_of_price": round(atr_pct, 3),
        "stop_pct": round(stop_frac * 100, 3),
        "fee_drag_pct_of_risk": round(drag, 2),
        "quantity": round(qty, 8),
        "notional": round(notional, 2),
        "margin": round(notional / leverage, 2),
        "min_atr_multiple_for_5pct_drag": round(min_stop_5 / (atr / price), 2),
        "note": (f"A {stop_frac*100:.2f}% stop hands {drag:.1f}% of your risk to fees. "
                 f"Keep drag under 5% by stopping wider than {min_stop_5*100:.2f}% of "
                 f"price, which on this asset is {min_stop_5/(atr/price):.2f}x ATR."),
    }


@mcp.tool()
def list_profiles() -> dict:
    """List the challenge rule sets troid models, with the crossover for each."""
    out = {}
    for k, p in PROFILES.items():
        cross = (1 - p["maxloss"] / 100) + p["daily"] / 100
        out[k] = {"name": p["name"], "daily_loss_pct": p["daily"],
                  "max_loss_pct": p["maxloss"], "profit_target_pct": p["target"],
                  "min_trading_days": p["min_days"],
                  "crossover_pct_of_quota": round(cross * 100, 2),
                  "room_before_max_loss_binds_pct": round((1 - cross) * 100, 2)}
    out["_note"] = ("The 1-Step is the tightest structure — least room, highest target. "
                    "Sizing that clears it clears any of the others.")
    return out


if __name__ == "__main__":
    mcp.run()
