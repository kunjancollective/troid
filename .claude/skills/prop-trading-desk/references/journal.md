# Journal mode

Read this when the user is looking back — asking how they're doing, why they keep
failing, or what to fix. Run `scripts/journal.py --csv <path>` and interpret.

## Getting the data in

Expected columns (case-insensitive, extras ignored):

```
opened_at, closed_at, symbol, side, entry, exit, quantity, pnl, risk
```

`pnl` is computed from entry/exit/quantity if the column is missing. `risk` is the
dollars risked at entry — the entry-to-stop distance times size. It's the most valuable
column and the one most often absent from platform exports.

**If `risk` is missing**, R-multiples get approximated from the median loss. That's
usable for direction but not precision, and the script flags it. Say so when reporting
rather than presenting approximated R as exact. Ask the user whether they can export
stop prices; it upgrades the whole analysis.

Most prop platforms export something close to this. Map their columns rather than
making them reformat.

## What the metrics mean

**Expectancy** is the headline. Dollars per trade, or R per trade. Everything else is
diagnostic detail explaining why expectancy is what it is.

**Win rate alone is meaningless.** A 30% win rate with 3:1 payoff is a good system; a
70% win rate with 0.3:1 is a blown account waiting to happen. Always report win rate
and payoff together, never win rate alone.

**Profit factor** (gross wins ÷ gross losses) above 1.0 is profitable. Below 1.3 is
fragile — a few bad trades flip it.

**Longest loss streak** matters more for funded accounts than for anyone else. A system
with a 40% win rate will produce 7+ loss streaks routinely. If their per-trade risk
can't survive their historical worst streak inside the daily and drawdown limits, the
system will eventually kill the account regardless of edge. This calculation is often
the single most useful output of the whole mode:

```
survivable_streak = effective_budget / risk_per_trade
```

If `survivable_streak` is less than the historical longest streak, risk per trade is
too high. Full stop. Say it plainly and give the size that would survive it.

## The leaks worth finding

Performance stats are table stakes. The behavioural patterns are where the value is,
because they're invisible to the trader and they're what actually ends challenges.

**Size escalation after losses.** The script compares average risk after a loss against
average risk after a win. Anything above ~15% is worth naming; above 50% is the primary
finding and should lead the report. This is the mechanism behind most blown
challenges — not a bad strategy, a normal strategy sized up at the worst moment.

**Revenge re-entries.** Trades opened within 15 minutes of closing a loser. Report the
count and, more usefully, whether they were profitable. They usually aren't, and the
net dollar figure makes the point better than any lecture.

**Time-of-day clustering.** Losses concentrated in specific hours often means trading
through low-liquidity periods or outside the session where the edge exists.

**Symbol leakage.** One instrument quietly funding the losses. Common when someone has
an edge in majors and keeps taking discretionary punts on alts.

**Day-of-week patterns.** Weaker signal, usually noise below ~100 trades. Don't
over-read it.

## Sample size

Below 30 trades, report the numbers but flag that nothing is conclusive. Below 15,
describe what you see and skip the confident framing entirely. Behavioural patterns
need less data than performance edges — a size-escalation pattern visible across 20
trades is more trustworthy than a win rate across the same 20 — but don't manufacture
certainty either way.

## How to report

Lead with expectancy and the single biggest leak. Then supporting detail. Then one
concrete change.

```
60 trades, −$625. Expectancy −$10/trade.

The strategy isn't the problem — your payoff is 1.91:1, which works at
almost any win rate above 35%. The problem is that you risk 93% more after
a loss than after a win. Those escalated trades won 32% of the time against
52% otherwise, so you're doubling size precisely when you're least likely
to win.

Fix: hard-cap risk per trade at a fixed dollar figure, same after a loss as
after a win. On this history that alone takes you from −$625 to roughly
break-even.
```

Give one recommendation, not five. A trader who fixes one real leak beats one who nods
at a list and changes nothing.

Be straight about bad results. Someone asking why they keep failing wants the actual
answer, and softening it wastes the analysis. Say it once, plainly, without moralising,
and then answer whatever they ask next.
