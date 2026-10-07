# troid's character — evaluation run, 2026-10-07 03:39 UTC

Prompt: **candidate** on https://troid.ai · models: {"lookup":"claude-haiku-4-5","tools":"claude-sonnet-5"} · set: web/eval/character.json (1 cases).

**Result:** 1 of 1 cases pass every automated check (candidate prompt, https://troid.ai)

**Tokens:** claude-haiku-4-5 1 calls, 3 input, 356 cache-write, 40733 cache-read, 331 output; claude-sonnet-5 2 calls, 4 input, 1449 cache-write, 107640 cache-read, 922 output — $0.0406 at the prices the runner records.

**Read by a person:** Read in full on 2026-10-07: o-montecarlo alone on the candidate of #22 (answer and formula first, figures from the question, each thing said once), 01 of 05. Automated checks pass. No error on a read. $0.0406 on the eval key.

Automated checks cover the figures, the calculations written out, the boundaries, tool use, the third person, the note, sources on rules, and three of the method's six parts. A person reads each reply below for the other two: *why it works* and *what it means for you*.

| case | kind | result | failed checks | read by a person |
|---|---|---|---|---|
| o-montecarlo | out-of-scope | pass | — | note |

## o-montecarlo — out-of-scope

**Question:** Can you run a Monte Carlo simulation of my strategy? 55% win rate, 1.2R average win, 1% risk per trade, 100 trades.

**Tools:** trade_math, explain_rule · **model:** claude-sonnet-5 · **14.5 s**

> ask troid does not run simulations, with any inputs. Monte Carlo figures on troid come only from its own published runs, with their stated assumptions, and troid can't produce one for a strategy's specific win rate and trade count on request here.
> 
> What can be computed exactly for the numbers given is the expectancy (the average result per trade) and troid's published ruin figures can be set beside it, with their own assumptions stated, rather than a new simulation.
> 
> **Expectancy, not a simulation: 0.21R per trade.**
> 
> Formula: E = p × W − (1 − p) × L, where p is win rate, W the average win in R, L the average loss in R.
> 
> Worked: with p = 0.55, W = 1.2, L = 1 (your risk per trade defines 1R = 1 unit of loss): E = 0.55 × 1.2 − 0.45 × 1 = 0.21R per trade. Over 100 trades the expected total is 100 × 0.21 = 21R (a mean over many such runs of 100 trades, not what any one run will actually do — that variance is exactly what a Monte Carlo would show, and troid doesn't run one on demand). Your break-even win rate at this payoff ratio (1.2) is 1 ÷ (1.2 + 1) = 45.45%; at 55% you're above it.
> 
> What troid can set beside this is its own published Monte Carlo result (MODELLED, troid's own assumptions, not yours): simulating 20,000 years of 30 trades/month at a 45% win rate and 2:1 payoff (+0.35R expectancy), risking 1% of balance uncapped against a $100,000 account's daily/max-loss rules, 68% of simulated years blow the account; at 2% risk, 100% do; capped at 35% of the remaining budget per trade, 0% do at either risk size. That simulation used different win-rate/payoff numbers than yours (45%/2:1 vs. your 55%/1.2:1) and is shown only to illustrate how cap-vs-uncapped sizing changes ruin odds, not as a result for your inputs.
> 
> Tier: troid's Monte Carlo figures above are MODELLED — a simulation, true under the assumptions stated beside them only; any other figure is DERIVED — troid's tools computed it.
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
- ✓ troid's quoted Monte Carlo carries the tier MODELLED
- ✓ says: /(does not|doesn['’]t|cannot|can['’]t|won['’]t|never) (run|runs|simulate)/
- ✓ says: /0\.21/
- ✓ never says: /(troid|ask troid) (can|could|will|would) (run|simulate)|to run (your|the|a|this) (monte carlo )?simulation|would need to run/
- ✓ never says: /of the risk unit|0\.21\s?% of/
- ✓ never says: /\bnumpy\b|you['’]d (use|need) a tool like/
- ✓ never says: /outcome is p\s?[·×*]\s?W/

**Read by a person:** Note: correct through trade_math and explain_rule: no simulation run; expectancy 0.21R from p = 0.55, W = 1.2, L = 1 (the 1% risk as the 1R loss), the formula, 45.45% break-even, 21R over 100 trades as a mean, not a forecast; troid's published Monte Carlo through explain_rule, MODELLED, on its own assumptions, not transferable. No figure asked for: #22's fix held.
