# troid-shadow-1 — the strategy, pinned

**Status: research log, not a product.** Bitfunded ToU 14(d)(v) prohibits using marketed
strategies to pass an evaluation. This document exists so the strategy is reproducible
and auditable, not so anyone trades it. Its measured expectancy is inside noise.

> **Hypothetical performance.** These results are based on simulated or hypothetical performance results that have certain inherent limitations. Unlike the results shown in an actual performance record, these results do not represent actual trading. Also, because these trades have not actually been executed, these results may have under-or over-compensated for the impact, if any, of certain market factors, such as lack of liquidity. Simulated or hypothetical trading programs in general are also subject to the fact that they are designed with the benefit of hindsight. No representation is being made that any account will or is likely to achieve profits or losses similar to these being shown.
>
> troid's own strategy shows no statistical edge. Out of sample, on 504 BTC trades from 2021–2025 the parameters never saw, it measures +0.008R per trade, standard error 0.016R — a MEASURED figure, inside noise, and not a fact about the future.

Configuration is `backtest/strategy_config.json`. Change it there, never in code.

## What it is

One entry logic, both directions, BTCUSDT 4h. Everything below is a parameter in the
config file.

**Regime switch.** Compute the 90-bar (15-day) high-low range in ATR units. Below 8 ATRs
is *compressed*. Compressed → pullback logic OFF, breakout logic ARMED. Otherwise →
pullback ON. (Robustness concern: Bollinger width agrees with this measure on only ~20%
of bars. Both must be tested in the walk-forward.)

**Pullback entry.** Trend = close vs 120-bar EMA with the EMA sloping the same way.
Pullback = price touched the 20-bar EMA within the last 3 bars. Trigger = close beyond
the prior bar's extreme and back on the trend side of the EMA20. Entry at next open.

**Breakout entry.** After ≥18 compressed bars, a close outside the range. Entry at next
open. (Fired once in eight months. Untested, not refuted.)

**Ladder, five tranches on strength.** T1 at market; T2–T5 sit 0.5 ATR steps *in the
direction of the trade* and fill only as it proves out. Stop anchored beyond T1's
structure, 0.5 ATR buffer, skipped if wider than 2.5 ATR. Each tranche carries 1/5 of
the risk budget at the shared stop. Unfilled tranches cancel after 6 bars or at TP1.

Measured effect: winners fill 4.48 tranches, losers 1.64 (with reverse-on-stop; 4.26 / 1.66 without). Same risk, ~34% less total
quantity than a single entry — the benefit is conditionality, not size.

**Three take-profits** at 1R, 2R, 3R measured from T1. TP1 closes a third of what's
held, TP2 half the remainder, TP3 the rest. Stop moves to average entry after TP1.

**Reverse on stop-out.** When a position is stopped, arm one reverse in the opposite
direction at the next open, stop beyond the failed move's extreme + 0.5 ATR. One flip
only, no reverse of a reverse. (Reverse-on-TP3 fired 4 times in 8 months — untestable.
Reverse-on-any was negative.)

**Holding: swing_safe.** Hold through the 16:00 UTC reset if floating ≥ 0. Flatten if
underwater. (Beat plain swing in every grid cell tested.)

**Sizing: the desk rule.** 0.5% of balance, capped at 35% of the remaining effective
budget, where effective = min(daily budget, distance to the static floor). Net of
0.04%/side fees.

**Compliance, enforced in the engine.** Forced exit at 60 bars (ToU 14(d)(x), 10 days).
Pass requires ≥5 trading days (ToU 9(a)). Leverage capped at 5×.

## What it measured

BTCUSDT 4h from api.binance.us, 8 Jan – 21 Sep 2026, 1,539 bars, one regime. One feed end
to end: the daily shadow extends this same file from this same feed (`stitch_bars.py`).
Two bars (31 Aug 04:00 and 08:00 UTC) are forward-filled feed gaps; the one trade that held
through them is flagged in the journal, not excluded.

```
n = 78   exp +0.033R   PF 1.29   win 32%   max DD $1,058 on $100k   10.1 trades/month
SE 0.046R   t = 0.73   95% CI [−0.056R, +0.123R]   contains zero
```

~30 configurations were searched on this sample. Under a true zero edge the best of 30
would be expected near +0.12R by chance. This result is below that threshold.

**72 rolling challenge starts: 0 pass, 0 fail, 0 zombie.** Median ending balance
$100,409. The cap holds the account flat; nothing in the entry logic moves it.

## What holds regardless

Four findings are structural and survived every configuration:

1. Ladder direction is the largest effect found — strength beats weakness by 0.31R at five tranches.
2. Intraday holding is self-defeating on 4h bars; half of trades get clock-flattened.
3. The regime filter is the only improvement with a mechanism behind it.
4. Under the cap, ruin is unreachable and the failure mode is a stalled account.

## The confluence gate (for shadow-2)

Five popular indicators on BTC 4h — RSI(14), MACD, EMA 9/21 cross, 10-bar momentum,
Stochastic(14) — correlate with each other at 0.73 mean absolute; MACD and the EMA cross
at 0.98. They are one price series restated. ATR percentile correlates with all five at
0.07. Confluence means independent MECHANISMS, not correlated indicators. An input enters
shadow-2 only if |corr| < 0.5 with everything already in. Candidates that pass on
mechanism: funding rate, open-interest change, cross-asset (BTC dominance, DXY), macro
calendar. Verify data availability before building on any of them.

## What would make it real

In order: survive 10 assets (5 crypto, 5 TradFi) in the cross-section; survive the
time-series holdout; survive three months of the public shadow forward test (there is no Bitfunded free trial; the shadow is the forward test). Any one failing
ends the claim. All three passing earns the right to say "+X R, out of sample."

The time-series holdout has been run (`WALKFORWARD.md`): this configuration was chosen on
2026, and on the 504 BTC trades from 2021–2025 it never saw it measures +0.008R, SE 0.016R,
95% CI [−0.023R, +0.040R]; ETH, 498 trades, +0.008R. No single year clears +0.04R.

**In-sample-to-holdout shrinkage: 75%.** +0.033R on the 78 trades the parameters were
chosen against became +0.008R on the 504 they never saw. That is the multiple-comparisons
effect, predicted above from the best-of-30 arithmetic and now measured on troid's own data
(`verify_claims.py` re-derives it). At 8.5 trades a month and $500 risk, +0.008R is about
$35 a month on a $100,000 account. The interval at n = 78 was wide enough to hope; at
n = 504 it is tight enough to know. That is the baseline calibration of "noise" on this
pipeline, and shadow-2 has to beat it out of sample.

Until then the number is +0.033R, and the number is noise.
