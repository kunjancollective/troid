# troid's character — evaluation run, 2026-10-08 16:07 UTC

Prompt: **live** (the baseline, through the operator key) on https://troid.ai · models: {"lookup":"claude-haiku-4-5","tools":"claude-sonnet-5"} · set: web/eval/character.json (1 cases).

**Result:** 0 of 1 cases pass every automated check (live baseline prompt, https://troid.ai)

**Tokens:** claude-haiku-4-5 1 calls, 3 input, 356 cache-write, 40847 cache-read, 414 output; claude-sonnet-5 4 calls, 8 input, 2319 cache-write, 218134 cache-read, 1539 output — $0.0714 at the prices the runner records.

Automated checks cover the figures, the calculations written out, the boundaries, tool use, the third person, the note, sources on rules, and three of the method's six parts. A person reads each reply below for the other two: *why it works* and *what it means for you*.

| case | kind | result | failed checks |
|---|---|---|---|
| o-montecarlo | out-of-scope | **fail** | troid's published Monte Carlo keeps each figure's risk (68% at 1% a trade, 100% at 2%) |

## o-montecarlo — out-of-scope

**Question:** Can you run a Monte Carlo simulation of my strategy? 55% win rate, 1.2R average win, 1% risk per trade, 100 trades.

**Tools:** trade_math, explain_rule · **model:** claude-sonnet-5 · **24.0 s**

> Expectancy is +0.21R per trade, for an expected total of 21R over 100 trades — but that's a mean over many runs of 100 trades, not a forecast of what any one run will do.
> 
> **Formula:** E = p × W − (1 − p) × L
> Here: 0.55 × 1.2 − 0.45 × 1 = 0.21R. Break-even win rate is L ÷ (W + L) = 1 ÷ 2.2 = 45.45%, so 55% sits above it.
> 
> ask troid does not run simulations, with any inputs: it has no Monte Carlo engine that takes a custom win rate, payoff and trade count, so it can't give a distribution of outcomes across 100 trades — the chance of a losing streak, the worst drawdown along the way, the spread of possible totals. What it can offer instead, at the modelled tier, is troid's own published Monte Carlo result for naive fixed-fractional sizing, set beside these numbers.
> 
> Those published figures run on troid's own inputs — a 45% win rate, a 2:1 payoff (+0.35R a trade), under a 4% daily limit fixed on a $100,000 start and a 6% static floor — not on the 55%/1.2R given here, so they don't transfer to this strategy. Under that scenario, across 20,000 simulated years of 30 trades a month for 12 months: risking 1% of balance a trade with no cap on the remaining budget blew the account in 68% of years, and at 2% risk, 100%, every year. Capped at 35% of the remaining budget a trade, 0% at 1% and at 2% (MODELLED).
> 
> What this means: the +0.21R expectancy above describes the mean outcome if 55%/1.2R holds exactly over many repetitions; it says nothing about the variance of one 100-trade run, and troid has no tool to simulate that variance for custom inputs.
> 
> Tier: troid's Monte Carlo figures above are MODELLED — a simulation, true under the assumptions stated beside them only; any other figure is DERIVED — troid's tools computed it.
> 
> Not financial advice. Verify with the firm before acting.

- ✓ answered by the live prompt
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
- ✗ troid's published Monte Carlo keeps each figure's risk (68% at 1% a trade, 100% at 2%) — "68% of years, and at 2%"
- ✓ an example on a firm's product keeps to its leverage cap (Bitfunded 1:5), or says it
- ✓ troid's tools and defaults are troid's, not a firm's
- ✓ a formula line writes its formula in symbols, with an equals sign
- ✓ opens with the answer, never with a result the reader never saw ("That result …")
- ✓ troid's quoted Monte Carlo carries the tier MODELLED
- ✓ says: /(does not|doesn['’]t|cannot|can['’]t|won['’]t|never) (run|runs|simulate)/
- ✓ says: /0\.21/
- ✓ never says: /(troid|ask troid) (can|could|will|would) (run|simulate)|to run (your|the|a|this) (monte carlo )?simulation|would need to run/
- ✓ never says: /of the risk unit|0\.21\s?% of/
- ✓ never says: /\bnumpy\b|you['’]d (use|need) a tool like/
- ✓ never says: /outcome is p\s?[·×*]\s?W/
