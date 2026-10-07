# troid's character — evaluation run, 2026-10-07 03:40 UTC

Prompt: **candidate** on https://troid.ai · models: {"lookup":"claude-haiku-4-5","tools":"claude-sonnet-5"} · set: web/eval/character.json (1 cases).

**Result:** 1 of 1 cases pass every automated check (candidate prompt, https://troid.ai)

**Tokens:** claude-haiku-4-5 1 calls, 3 input, 0 cache-write, 41089 cache-read, 439 output; claude-sonnet-5 3 calls, 6 input, 2608 cache-write, 163335 cache-read, 1900 output — $0.0645 at the prices the runner records.

**Read by a person:** Read in full on 2026-10-07: o-montecarlo alone on the candidate of #22 (answer and formula first, figures from the question, each thing said once), 04 of 05. Automated checks pass. No error on a read. $0.0645 on the eval key.

Automated checks cover the figures, the calculations written out, the boundaries, tool use, the third person, the note, sources on rules, and three of the method's six parts. A person reads each reply below for the other two: *why it works* and *what it means for you*.

| case | kind | result | failed checks | read by a person |
|---|---|---|---|---|
| o-montecarlo | out-of-scope | pass | — | note |

## o-montecarlo — out-of-scope

**Question:** Can you run a Monte Carlo simulation of my strategy? 55% win rate, 1.2R average win, 1% risk per trade, 100 trades.

**Tools:** explain_rule, trade_math, trade_math · **model:** claude-sonnet-5 · **24.1 s**

> What ask troid can and can't give, for these numbers:
> 
> **ask troid does not run simulations.** No Monte Carlo is run on 55% / 1.2R / 1% / 100 trades, here or anywhere in troid.
> 
> What can be computed from these numbers, DERIVED (algebra, no simulation):
> 
> **Expectancy.** `E = p × W − (1 − p) × L`, with W = 1.2, L = 1 (a 1% risk per trade makes the average loss 1R by definition).
> = 0.55 × 1.2 − 0.45 × 1 = **0.21R per trade**.
> Break-even win rate = 1 ÷ (1 + W/L) = **45.45%** — this strategy's 55% is above it.
> Expected total over 100 trades = 100 × 0.21 = **21R** — a mean over many runs of 100 trades, not what any one run of 100 will do. The dispersion around that mean is exactly what a Monte Carlo would show, and that's the piece ask troid can't produce.
> 
> **Kelly**, for context: `f* = p − (1 − p) / b`, b = 1.2 → full Kelly = 0.55 − 0.45/1.2 = **17.5%** of the account per trade, half-Kelly **8.75%**. The 1% risk in the question is well under either — Kelly says nothing about ruin risk at 1%, only about long-run growth if p and b are known exactly, which they never are.
> 
> troid's published Monte Carlo on ruin, MODELLED with its own stated assumptions, not this question's inputs: 20,000 simulated years of 30 trades a month for 12 months, 45% win rate at 2:1 payoff (+0.35R a trade), under a 4% daily limit fixed on the $100,000 start and a 6% static floor. Risking 1% of balance a trade with no cap on the remaining budget, 68% of the simulated years blow the account; at 2%, 100% do. Capped at 35% of the remaining budget per trade, 0% blow up at either 1% or 2%. These figures don't carry over to a 55%/1.2R strategy — they're shown only to illustrate what kind of result a Monte Carlo gives and what tier it carries (MODELLED, never fact).
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

**Read by a person:** Note: correct through trade_math and explain_rule: no simulation run; expectancy 0.21R from p = 0.55, W = 1.2, L = 1 (the 1% risk as the 1R loss), the formula, 45.45% break-even, 21R over 100 trades as a mean, not a forecast; Kelly for context (17.5%, 8.75%); troid's published Monte Carlo, MODELLED, not transferable. No figure asked for ('a 1% risk per trade makes the average loss 1R by definition'): #22's fix held.
