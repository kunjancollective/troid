#!/usr/bin/env python3
"""troid asset atlas — per-asset risk characteristics for every instrument a firm lists.

The scaling problem is NOT "make the strategy work on 120 assets". It's "tell the trader
what each asset costs them". That answer is pure arithmetic and it generalises to any
instrument the firm ever adds, including non-crypto.

Two facts drive everything here:

  fee_share = 2f / (s + 2f)        f = fee per side, s = stop as a fraction of price

    Fee drag depends ONLY on stop distance as a percentage — not on the asset. But if
    your stops are ATR-based, then the asset's normalised volatility sets s, and so the
    asset does decide your fee drag after all.

  qty = risk / (stop_distance + entry * 2f)

    A wider stop means less quantity for the same dollar risk, so high-volatility assets
    consume LESS margin per unit of risk. That matters against the 65% concentration rule.

Feed it a symbol list plus price and ATR (from any market-data source) and it produces
the atlas. Adding assets is a data change, never a code change.
"""
from __future__ import annotations
import json, sys, math

FEE_PER_SIDE = 0.0004
LEVERAGE = 5.0
RISK = 500.0            # reference risk unit for capital-efficiency comparison


def fee_share(stop_frac: float, f: float = FEE_PER_SIDE) -> float:
    """Share of the risk budget consumed by round-trip fees."""
    return 2 * f / (stop_frac + 2 * f) * 100


def min_stop_for(budget_pct: float, f: float = FEE_PER_SIDE) -> float:
    """Smallest stop (as a fraction of price) keeping fee drag under budget_pct."""
    return 2 * f * (100 - budget_pct) / budget_pct


def profile_asset(symbol: str, price: float, atr: float, atr_mult: float = 1.5,
                  fee: float = FEE_PER_SIDE, leverage: float = LEVERAGE,
                  risk: float = RISK) -> dict:
    atr_pct = atr / price * 100
    stop_dist = atr_mult * atr
    stop_frac = stop_dist / price
    fee_unit = price * fee * 2
    qty = risk / (stop_dist + fee_unit)
    notional = qty * price
    margin = notional / leverage
    return {
        "symbol": symbol, "price": price, "atr": atr,
        "atr_pct": atr_pct,
        "stop_pct": stop_frac * 100,
        "fee_share_pct": fee_share(stop_frac, fee),
        "qty": qty, "notional": notional,
        "margin": margin,
        "margin_pct_of_100k": margin / 100_000 * 100,
        # smallest ATR multiple that keeps fee drag under 5% on this asset
        "min_atr_mult_5pct": min_stop_for(5.0, fee) / (atr / price),
    }


def atlas(assets: list[dict], atr_mult: float = 1.5) -> list[dict]:
    rows = [profile_asset(a["symbol"], a["price"], a["atr"], atr_mult) for a in assets]
    return sorted(rows, key=lambda r: r["atr_pct"])


def render(rows: list[dict], atr_mult: float) -> None:
    print(f"\ntroid asset atlas — {atr_mult}x DAILY ATR stop, ${RISK:.0f} risk, "
          f"{LEVERAGE:.0f}x leverage, {FEE_PER_SIDE*100:.2f}%/side")
    print("  ATR here is 14-period DAILY. A 4h strategy uses 4h ATR, roughly daily/2.5:\n"
          "  stops ~2.5x tighter, fee drag ~2.6x higher, positions ~2.6x larger. Label the\n"
          "  timeframe on any number you publish from this table.\n")
    print(f"{'asset':<12}{'price':>12}{'ATR %':>8}{'stop %':>8}{'fee drag':>10}"
          f"{'notional':>12}{'margin':>10}{'min ATRx':>10}")
    print("-" * 82)
    for r in rows:
        sym = r["symbol"].split(":")[-1]
        print(f"{sym:<12}{r['price']:>12,.4f}{r['atr_pct']:>7.2f}%{r['stop_pct']:>7.2f}%"
              f"{r['fee_share_pct']:>9.2f}%{r['notional']:>12,.0f}{r['margin']:>10,.0f}"
              f"{r['min_atr_mult_5pct']:>10.2f}")
    lo, hi = rows[0], rows[-1]
    print(f"\n  volatility spread: {lo['symbol'].split(':')[-1]} {lo['atr_pct']:.2f}% "
          f"to {hi['symbol'].split(':')[-1]} {hi['atr_pct']:.2f}%  "
          f"({hi['atr_pct']/lo['atr_pct']:.1f}x)")
    print(f"  margin for the SAME $500 risk: ${hi['margin']:,.0f} to ${lo['margin']:,.0f} "
          f"({lo['margin']/hi['margin']:.1f}x)")
    print(f"  -> higher-volatility assets need wider stops, so they hold less size and\n"
          f"     use less margin for identical dollar risk. They are also more fee-efficient\n"
          f"     per ATR unit, because fee drag falls as the stop widens.")

    print(f"\n  fee drag by stop distance — identical on every asset, it depends only on stop %:")
    for s in (0.003, 0.005, 0.01, 0.015, 0.02, 0.04):
        print(f"     {s*100:>5.2f}% stop -> {fee_share(s):>5.2f}% of risk")
    for b in (5, 10, 20):
        print(f"  keep fee drag under {b:>2}% -> stop must exceed {min_stop_for(b)*100:.2f}% of price")


if __name__ == "__main__":
    # Live snapshot, 17 Sep 2026. ATR values are TradingView's DAILY 14-period column.
    # TRADFI CAVEAT: Bitfunded quotes synthetic USDT perps (XAUUSDT etc.) from an unnamed
    # partner exchange, not spot. These rows use spot references. Replace with the actual
    # instrument once the feed exchange is confirmed; basis and funding shift the ATR. Replace via any market-data source; the schema is
    # the contract, not the source.
    ASSETS = [
        {"symbol": "BINANCE:BTCUSDT",  "price": 76376.3,   "atr": 2074.5214},
        {"symbol": "BINANCE:BNBUSDT",  "price": 725.18,    "atr": 21.7778},
        {"symbol": "BINANCE:ETHUSDT",  "price": 2436.61,   "atr": 92.7159},
        {"symbol": "BINANCE:LTCUSDT",  "price": 52.013,    "atr": 1.9992},
        {"symbol": "BINANCE:SOLUSDT",  "price": 99.492,    "atr": 4.3554},
        {"symbol": "BINANCE:DOGEUSDT", "price": 0.080792,  "atr": 0.0041277},
        {"symbol": "BINANCE:ANKRUSDT", "price": 0.0044136, "atr": 0.00025735},
        {"symbol": "BINANCE:XRPUSDT",  "price": 1.295,     "atr": 0.0776790},
    ]
    mult = float(sys.argv[1]) if len(sys.argv) > 1 else 1.5
    rows = atlas(ASSETS, mult)
    render(rows, mult)
    json.dump(rows, open("atlas.json", "w"), indent=1)
