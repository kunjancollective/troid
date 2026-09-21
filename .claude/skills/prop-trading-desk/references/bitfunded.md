# Bitfunded rules

Sourced from Bitfunded's own docs (help center "Criteria to be Success" and the FAQ).
Expert $100,000 / Stage 1 (1 Step) figures. Verify against the user's actual tier — the
percentages change but the mechanics don't.

```
Profit target      10%  ($10,000)  realized only, floating profit doesn't count
Max daily loss      4%  ($4,000)   realized + floating
Max loss            6%  ($6,000)   realized + floating, STATIC
Max leverage        5x
Fees              0.04% per side on notional (0.08% round trip)
Daily reset       00:00 UTC+8
```

## The 4:6 ratio is the whole story

Most firms run a 2:1 ratio between max loss and daily loss (5/10, 4/8). Bitfunded
runs 1.5:1. That single number drives everything.

**You get one and a half maximum-loss days in the entire life of the account.**

The crossover where the ceilings swap is worth memorising:

```
daily_budget = 0.04 × equity        (on a fresh day)
dd_budget    = equity − 94,000
equal when      4,000 = E − 94,000   →  E = 98,000   [daily limit is FIXED at 4% of quota]
```

Above $98,000 the daily limit binds. Below it, the 6% max loss governs and the daily
allowance is fiction. On a $100,000 account that crossover is only $2,000 away — about
half of one bad day. So for most of a struggling account's life, the max loss is the
real constraint and the "4% daily" number on the marketing page is irrelevant.

Say this explicitly the first time the account drops below the crossover. A trader who
thinks they have $5,760 of daily room when they actually have $3,000 total will size
nearly double what the account can survive.

## Static cuts the other way too

Because the max loss is fixed to the account quota rather than a high-water mark,
profit permanently widens the buffer. Up $3,000 and the floor is still $94,000, so
total room is $9,000 while daily stays $4,000 — the daily binds again and keeps
binding. The account gets structurally safer the further ahead it gets.

This makes the opening days the dangerous ones. Frame early sizing accordingly: the
goal in the first stretch isn't to hit the target, it's to get far enough above
$98,000 that a normal losing streak can't reach the floor.

## Traps in the fine print

**Floating losses across the reset.** From Bitfunded's own example (their 100k/5% case):
a 6,000 floating loss that survives the reset counts fully against the new day, because
the previous day's profit does not carry over. A position comfortably inside the limit at
11:59 can breach at 12:01 without price moving.

*Measured scope, so don't overstate it.* The trap needs **two** things at once: risk per
position at or above 4% of the account (a stop-loss at that size is the whole daily
limit), **and** a policy that carries losers through the reset. Under the desk's own
rules it is dead twice over — the budget cap holds a single position's floating loss to
at most 35% of the daily limit, and swing_safe flattens every underwater position before
the reset. Across 9,014 reset evaluations in backtest, 2,225 positions survived to a
reset and not one was underwater. At 4% uncapped risk holding losers through, the largest
floating loss actually carried in was $3,422 against a $4,000 line — 86% of the way,
never firing.

So: mention it when the user is sizing above ~4% per position or explicitly holding a
loser into the reset. Don't lead with it otherwise; it isn't live under the desk's own
recommendations, and treating a dead hazard as urgent costs credibility on the live ones.

**The reset lands midday.** 00:00 UTC+8 is 16:00 UTC, which is **noon in New York**
(11:00 EST in winter). Not overnight. A morning session and an afternoon session are
on different trading days, and a loss at 11:45 plus a loss at 12:15 draw on separate
budgets. Bitfunded notes the reset may take until 00:10 UTC+8 to apply, so treat the
ten minutes either side as undefined and don't hold a marginal position through it.

**Floating loss alone fails the account.** Both limits auto-fail on unrealised loss —
no close required, no margin call, no chance to recover. An open position that dips to
the limit intraday ends the challenge even if it would have come back. This is why the
liquidation-versus-stop check matters more here than on a normal account.

**Profit target is realized-only** and all positions must be closed to clear the
stage. Floating profit doesn't count toward it.

## Fees are a sizing input, not a footnote

0.04% per side on **notional**, and notional scales inversely with stop distance. So
the tighter the stop, the more of the risk budget goes to fees:

```
3.9% stop (1.5× daily ATR)  ->  ~2% of risk
1.5% stop                   ->  ~5% of risk
0.3% stop (scalp)           ->  ~21% of risk
```

At a 0.3% stop on a $500 risk budget, $105 goes to Bitfunded before price moves. A
scalping approach here needs either a materially better hit rate or a wider stop to
break even against a swing approach. `scripts/risk.py` sizes net of fees and warns
above 15%.

## Unresolved

**Minimum trading days conflict.** The challenge page shows 0; the FAQ says at least
5. These can't both be right. Tell the user to confirm with support before planning
around either, because a 0 assumption plus a real 5-day requirement means passing the
target and then being unable to clear the stage.

The FAQ also describes a two-stage evaluation, while the current challenge page shows a
single "1 Step" Stage 1 into Trader Stage. The FAQ appears to lag the product. Prefer the challenge page and the help
center, and treat the FAQ as stale where they disagree.
