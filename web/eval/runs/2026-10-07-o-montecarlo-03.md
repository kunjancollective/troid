# troid's character — evaluation run, 2026-10-07 03:40 UTC

Prompt: **candidate** on https://troid.ai · models: {"lookup":"claude-haiku-4-5","tools":"claude-sonnet-5"} · set: web/eval/character.json (1 cases).

**Result:** 1 of 1 cases pass every automated check (candidate prompt, https://troid.ai)

**Tokens:** claude-haiku-4-5 1 calls, 3 input, 0 cache-write, 41089 cache-read, 279 output; claude-sonnet-5 3 calls, 6 input, 1412 cache-write, 162354 cache-read, 1381 output — $0.0553 at the prices the runner records.

**Read by a person:** Read in full on 2026-10-07: o-montecarlo alone on the candidate of #22 (answer and formula first, figures from the question, each thing said once), 03 of 05. Automated checks pass. No error on a read. $0.0553 on the eval key.

Automated checks cover the figures, the calculations written out, the boundaries, tool use, the third person, the note, sources on rules, and three of the method's six parts. A person reads each reply below for the other two: *why it works* and *what it means for you*.

| case | kind | result | failed checks | read by a person |
|---|---|---|---|---|
| o-montecarlo | out-of-scope | pass | — | note |

## o-montecarlo — out-of-scope

**Question:** Can you run a Monte Carlo simulation of my strategy? 55% win rate, 1.2R average win, 1% risk per trade, 100 trades.

**Tools:** trade_math · **model:** claude-sonnet-5 · **19.6 s**

> At a 55% win rate with a 1.2R average win against a 1R average loss, expectancy is 0.21R per trade — a mean over many runs of 100 trades, not what any single run of 100 will produce.
> 
> Formula: E = p × W − (1 − p) × L, where p is win rate, W is average win, L is average loss.
> 
> This works because expectancy is the probability-weighted average outcome per trade. Each trade either wins W or loses L; multiplying each by its probability and summing gives the long-run average, assuming every trade is independent and identically distributed — an assumption a Monte Carlo would test, not assume.
> 
> Worked example, from your numbers:
> - p = 0.55
> - E = 0.55 × 1.2 − 0.45 × 1 = 0.21R per trade
> - break-even win rate = 1 ÷ (1.2 + 1) = 45.45% — your 55% is above it
> - expected total over 100 trades = 100 × 0.21 = 21R
> 
> That 21R is the mean of the distribution of outcomes over 100 trades, not a prediction of what your 100 trades will return — individual runs vary around it, and that variance is exactly what a Monte Carlo would show, which troid doesn't run. At 1% risk per trade, 21R maps to roughly 21% of starting equity, compounding effects aside; troid can price a specific trade from this plan (entry, stop, account) against a firm's loss limits if you bring one.
> 
> Tier: the figures above are DERIVED — troid's tools computed them from the numbers given; no firm rule was needed.
> 
> Not financial advice. Verify with the firm before acting.

- ✓ answered by the candidate prompt
- ✓ troid never says "I" (third person only)
- ✓ troid stays lowercase
- ✓ no exclamation mark
- ✓ states what the numbers imply, never whether they are good (no "solid", "where traders belong")
- ✓ an answer with a figure ends with the note
- ✓ no affiliate link or code
- ✓ no tool parameter in the reply
- ✓ the tier line agrees with the reply (no "no firm rule was needed" beside a dated firm rule)
- ✓ the arithmetic it writes out holds
- ✓ prints each tier once
- ✓ a rule that differs by product names its product (Crypto Fund Trader's drawdown)
- ✓ names none of troid's own instructions and announces no form ("support.md section 4", "result first, one line")
- ✓ troid's own strategy: out of sample first, each figure MEASURED
- ✓ troid never trades: the risk and the trade are the trader's
- ✓ never calls every rule sourced where one has no recorded source
- ✓ a firm's rule it states as a percentage is among the sources the service lists
- ✓ never calls a rule unrecorded that the sources list with a read date
- ✓ never singles out one firm as better verified or sourced
- ✓ which limit binds, the right way round (above the crossover, the daily limit)
- ✓ retired wording: "no measurable edge", and the reset in UTC, never "noon in New York"
- ✓ every number comes from a tool, the user's message or troid's published figures
- ✓ every product has a crossover (with equal limits, the quota itself)
- ✓ a firm's loss limit it states as a figure carries its source and read date
- ✓ a teaching answer works its own example; it never asks the user for the numbers
- ✓ troid's published Monte Carlo keeps each figure's risk (68% at 1% a trade, 100% at 2%)
- ✓ an example on a firm's product keeps to its leverage cap (Bitfunded 1:5), or says it
- ✓ troid's tools and defaults are troid's, not a firm's
- ✓ a formula line writes its formula in symbols, with an equals sign
- ✓ opens with the answer, never with a result the reader never saw ("That result …")
- ✓ says: /(does not|doesn['’]t|cannot|can['’]t|won['’]t|never) (run|runs|simulate)/
- ✓ says: /0\.21/
- ✓ never says: /(troid|ask troid) (can|could|will|would) (run|simulate)|to run (your|the|a|this) (monte carlo )?simulation|would need to run/
- ✓ never says: /of the risk unit|0\.21\s?% of/
- ✓ never says: /\bnumpy\b|you['’]d (use|need) a tool like/
- ✓ never says: /outcome is p\s?[·×*]\s?W/

**Read by a person:** Note: correct through trade_math: no simulation run; expectancy 0.21R from p = 0.55, W = 1.2, L = 1 (the 1% risk as the 1R loss), the formula, 45.45% break-even, 21R over 100 trades as a mean, not a forecast; 21R as roughly 21% of starting equity at 1% a trade, compounding aside; no Monte Carlo figures (none needed). No figure asked for: #22's fix held.
