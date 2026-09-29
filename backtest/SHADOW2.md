# troid-shadow-2 — the design, fixed before any run

**Status: research log, not a product.** Bitfunded ToU 14(d)(v) prohibits using marketed strategies to pass an
evaluation. This document exists so the test is reproducible and auditable, not so anyone trades it.

> **Hypothetical performance.** These results are based on simulated or hypothetical performance results that have certain inherent limitations. Unlike the results shown in an actual performance record, these results do not represent actual trading. Also, because these trades have not actually been executed, these results may have under-or over-compensated for the impact, if any, of certain market factors, such as lack of liquidity. Simulated or hypothetical trading programs in general are also subject to the fact that they are designed with the benefit of hindsight. No representation is being made that any account will or is likely to achieve profits or losses similar to these being shown.
>
> troid's own strategy shows no measurable edge.

Configuration: `backtest/shadow2_config.json`. Signals: `backtest/engine_s2.py`. The measurement: `WALKFORWARD2.md`,
written by `walkforward2.py`, never by hand.

## Why a second strategy

troid-shadow-1 measured +0.008R a trade on 504 BTC trades it never saw (95% CI [−0.023R, +0.040R]) and the same on
ETH (`WALKFORWARD.md`): noise. HANDOFF.md's sequencing asks for a second, separate strategy built from mechanisms
rather than restated price indicators: time-series momentum over 3 to 12 months, long and short, one parameter
family; volatility targeting; the regime question put as a volatility-of-volatility state and tested against
Bollinger width; the desk's sizing and every compliance rule unchanged; and no input whose correlation with one
already in reaches 0.5. shadow-1 is not edited: it keeps its config, its journal and its record.

## Fixed before any run (2026-09-29)

Everything below was written, with the config, before shadow-2 was run on any bar. Nothing in it is chosen from a
result. A change after a result is a new strategy with a new name.

**Signal: time-series momentum, one family.** At each decision, each lookback of 3, 6, 9 and 12 months (30.44 days
a month, six 4h bars a day) votes the sign of the asset's return over that lookback. The trade takes the sign of the
sum of the four votes: long when more point up, short when more point down, nothing on a two-two tie. The four
lookbacks are one family; the ensemble is the strategy, fixed now, so no lookback is picked after the fact. Each
lookback alone is still reported beside it: that is the neighbourhood.

**One decision a day.** The vote is read on the close of the 20:00–24:00 UTC bar and a trade opens at the 00:00 UTC
open, eight hours after Bitfunded's 16:00 UTC reset, never inside its 16:00–16:10 settling window. An open position
skips the day's decision; a closed one can reopen at the next day's.

**Volatility targeting.** Volatility is the standard deviation of the last 30 days of 4h log returns, scaled to a
day. The stop sits two of those daily deviations from the entry. The desk's rule sizes every trade at that stop:
0.5% of the balance, capped at 35% of the remaining effective budget, net of fees. Wider volatility, wider stop,
smaller position, the same dollars at risk.

**Exits.** The stop; a take-profit at 3R, so no trade runs without both (Restricted Trading Practices s.4 can class
trading without them as excessive risk); and the hold limit for the asset's class, Bitfunded help centre, Restricted
Trading Practices s.1: 10 days (60 bars) for its major crypto assets, 7 days (42) for other crypto, 5 days (30) for
TradFi. A vote that flips does not close a trade: the lookbacks are months long, a flip is rare, and each trade ends
within days anyway.

**Holding through the reset.** shadow-2 holds through the 16:00 UTC reset whatever the floating result ("swing").
shadow-1's swing_safe closes anything underwater at every reset; on a trade meant to run for days that would turn a
losing trade's horizon into hours, and swing_safe was chosen on shadow-1's own data. The rollover rule still
applies in full: floating loss carried into a new day counts against the new day's limit, and a breach ends the
account.

**Unchanged from shadow-1.** The accounting is engine_v2's, the same function shadow-1 runs: the daily limit fixed
at 4% of the initial balance, the static floor at 6%, the 16:00 UTC reset with floating loss carried in full, fees of
0.04% a side, 0.03% slippage on stops, leverage capped at 5×, at least 5 trading days to pass. Each trade is one
entry: no ladder, no reverse.

**The regime, recorded, not used.** At every entry shadow-2 records two states, each against its own trailing
365-day median, so neither looks ahead:
- vol-of-vol: the coefficient of variation of the 30-day volatility over the last 90 days; at or below its median is
  *calm*, above is *unsettled*;
- Bollinger width: 20 bars, two standard deviations, divided by the mean; at or below its median is *compressed*,
  above is *expanded*.

Neither filters a trade. Filtering on a guessed state halves the trades on a guess; recording it on every trade
answers whether the state carries information. If it does, a filter is a new config, tested forward, never fitted
back onto these years.

**The confluence gate.** At the decision bars, troid computes the correlation between the inputs: the vote, the
volatility (it sets the stop), the vol-of-vol, and, for the comparisons, Bollinger width and shadow-1's two inputs
(its 120-bar EMA trend and its range width in ATRs). An input is admitted only if |corr| < 0.5 with every input
already admitted, in this order: the vote, the volatility, the vol-of-vol. The matrix is reported whatever it shows.

**Periods.** The holdout is 1 January 2025 to 21 September 2026, the frozen end of the sample (HANDOFF.md step 3);
later bars are a live tail. Nothing is fitted on any year, so the rows before 2025 are reported as what they are:
before the holdout. The 12-month lookback, the 365-day medians and the 90-day window need about fifteen months of
bars before the first decision.

**The cross-section.** Bitfunded's ten named major crypto assets (Restricted Trading Practices s.1): BTC, ETH, BNB,
XRP, SOL, TRX, HYPE, ZEC, DOGE, ADA, each where binance.us has 4h history from before 1 January 2023, USDT pair
first, then USD. Then these, in this order, until at least ten assets qualify: LTC, LINK, BCH, DOT, AVAX, XLM,
ATOM, UNI, ETC, ALGO (Bitfunded's other crypto, a 7-day hold). Every asset that qualifies is reported, not the first
ten. TradFi (XAU, XAG, TSLA) has no binance.us history, and troid mixes no feeds: it stays open. PAXG, tokenised gold
on binance.us if it is listed there, is reported apart as a gold proxy, with TradFi's 5-day hold, and not counted as
TradFi. shadow-1 runs on the same assets, its config unchanged but for the hold limit of each asset's class.

## What counts as surviving

Fixed now, with the design:

- **Shadow-2's expectancy (H1).** On the cross-section's holdout, pooled across assets, the mean R per trade is above
  zero and its 95% interval excludes zero, the standard error clustered by entry day (crypto assets move together:
  trades opened the same day are not independent); and the holdout mean is positive on at least two thirds of the
  assets with 30 trades or more. Both, or it did not survive.
- **The vol-of-vol state (H2).** On the pooled holdout, calm-state trades beat unsettled-state trades: the difference
  in mean R is above zero with a clustered 95% interval that excludes zero, and it has the same sign on at least two
  thirds of the assets with 30 trades or more in each state. Bollinger width's split is reported beside it, with how
  often the two states agree.
- A bucket under 30 trades is insufficient, not a number. Every result is MEASURED and never stated as fact.
- If neither survives, that is the finding. If H1 survives, a forward journal (`journal_shadow2.csv`, run daily beside
  shadow-1's) is the next test, and the owner's decision.

## What troid states and does not check

Bitfunded's ToU 14(d)(ix) (no switching strategies between the assessment and the funded account) and 13(c)(v) (no
opposite positions across connected accounts) can't be seen in a backtest. Each trade here closes within its hold
limit, and a new one opens only at a later day's decision: whether a firm counts a close and reopen as one position is
its call. The cross-section runs each asset alone; one account trading ten assets at once would meet the five-position
limit (Restricted Trading Practices s.3), which these runs do not model.
