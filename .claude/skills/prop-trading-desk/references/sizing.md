# Sizing mode

Read this when the user is about to take a trade, or asks about size, stop, leverage,
or risk. The shared budget model lives in SKILL.md — this covers turning that budget
into an actual order.

## Leverage is not risk

The most common confusion on crypto perps. On a perp, **leverage does not determine how
much you lose.** The stop does.

```
risk   = |entry − stop| × quantity        <- leverage appears nowhere
margin = (quantity × entry) / leverage    <- this is all leverage changes
```

Two traders both risking $50 with the same stop distance hold the same position and
lose the same $50. The one at 10x has posted less margin and sits closer to
liquidation; the one at 2x has more margin locked up and more room. Same risk,
different capital efficiency.

So when someone asks "should I use 5x or 3x?", the honest answer is that it doesn't
change their loss on the trade. What it changes is how much margin is tied up, and
whether price can wick through liquidation before reaching the stop — which is the
failure mode that actually matters.

**Bitfunded is cross margin at 5x, and that changes what "liquidation" means.** Under
isolated margin a position is liquidated when its own margin is exhausted, ~20% adverse
at 5x. Under cross the whole account backs every position, so exchange liquidation is
unreachable at any size the firm permits — at the 65% margin cap it's ~31% away while
the 6% floor binds at 1.85%. The firm's floors are the liquidation model. Two
consequences: nothing cuts a runaway position before the firm fails you (isolated would
have capped the damage at the position's margin), and at high concentration the daily
limit can sit *inside* a normal stop — at 65% margin it binds at 1.23% adverse. Check
the breach lines against the stop, always; under cross they are what's live.

## Where the stop goes

Place it where the idea is wrong, then size to it. Never pick a size first and put the
stop where that size allows. That's how people end up with stops inside the noise band,
getting wicked out of trades that were ultimately right.

Three defensible methods:

**Volatility (ATR).** Default 1.5× the 14-period ATR on 4h bars for swing entries,
1.0–1.5× on 1h for intraday. Fetch bars with `mcp-tv-get-ohlcv` and compute:

```
TR  = max(high−low, |high−prev_close|, |low−prev_close|)
ATR = mean(TR) over 14 periods
```

**Structure.** Below the swing low that would invalidate the idea (long), above the
swing high (short), plus a buffer so the exact wick doesn't clip you. With TVRemix
connected, `analyze_structure_batch` or `analyze_swing_tool` returns the actual pivot
levels on the timeframe you name — read `support[]` for the nearest swing lows and the
setup's `stop_loss` for the last one. Check the SMC `recent_events` too: a fresh
`bearish_choch` at a level means that low has already broken and is no longer a valid
stop for a long.

**Invalidation level.** A specific price where the thesis is dead — a broken range low,
a failed VWAP reclaim. Cleanest when the user actually has a thesis.

Ask which they're using if it isn't obvious. A stop with no reasoning behind it is
worth pushing back on, gently and once.

## Fees and slippage

Real loss exceeds the modelled stop distance. Taker fees both sides plus slippage on a
stop-market fill typically add 0.05–0.15% of notional on liquid crypto pairs. On a 1.5%
stop that's up to a tenth of the risk. When the budget is tight, buffer it:

```
effective_risk = modelled_risk × 1.10
```

Mention this when the trade consumes most of the remaining budget. Skip it when there's
plenty of room — precision theatre is noise.

## A ladder is not a bigger position

Scaling in does not increase size at fixed risk — it decreases it. With the stop anchored
to T1's structure, each later tranche sits further from the stop and so earns less
quantity. Measured: five strength tranches at $500 risk on a 1.5-ATR stop hold 0.109 BTC
against 0.167 BTC for a single entry, **34% less**.

What a strength ladder buys is *conditionality*. Backtested fills: 4.17 tranches on
winners, 1.56 on losers. Small when wrong, large when right. That halved drawdown in
every test. But if someone asks for a ladder because they want a larger position, correct
the premise — larger positions come only from more risk per trade, and the ruin maths
says no.

## Multiple positions

Budget is shared across everything open, not per trade. Two open longs on BTC and ETH
are not two independent risks: crypto majors correlate hard in a drawdown and converge
toward 1 in a real flush.

The simplest safe approach is to sum the risks with no correlation discount and size
the second entry against whatever budget remains after the first. With TVRemix
connected, `calculate_correlation_tool` on the open symbols gives the real figure —
BTC/ETH ran 0.87 over the 60 days to mid-September 2026 — and a haircut of
`1 − (1 − ρ)/2` is a reasonable compromise: at ρ=0.87 that's 0.94, so two positions
count as 1.94, which is to say: don't bother discounting, just sum.

Check `max_concurrent_positions` in config. If the user is already at the cap, say so
before doing any math.

## The output

Always give these, in this order:

1. **Verdict** — OK / REDUCE / BLOCK, and which ceiling is binding
2. **Size** — quantity, notional, margin at the stated leverage
3. **Levels** — entry, stop (with % distance), target (with R multiple)
4. **Budget impact** — dollars risked, % of remaining budget consumed, how many more
   losses at this size before the account trips

Then one or two sentences of reasoning. Not more. Someone mid-session is reading the
first line and the numbers.

Run `scripts/risk.py` for the arithmetic rather than doing it inline. It handles the
two-ceiling comparison, the budget cap, and the validation checks, and it won't make a
sign error on a short.
