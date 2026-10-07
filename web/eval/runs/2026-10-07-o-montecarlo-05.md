# troid's character — evaluation run, 2026-10-07 03:41 UTC

Prompt: **candidate** on https://troid.ai · models: {"lookup":"claude-haiku-4-5","tools":"claude-sonnet-5"} · set: web/eval/character.json (1 cases).

**Result:** 1 of 1 cases pass every automated check (candidate prompt, https://troid.ai)

**Tokens:** claude-haiku-4-5 1 calls, 3 input, 0 cache-write, 41089 cache-read, 311 output; claude-sonnet-5 2 calls, 4 input, 1706 cache-write, 107762 cache-read, 1272 output — $0.0442 at the prices the runner records.

**Read by a person:** Read in full on 2026-10-07: o-montecarlo alone on the candidate of #22 (answer and formula first, figures from the question, each thing said once), 05 of 05. Automated checks pass. No error on a read. $0.0442 on the eval key.

Automated checks cover the figures, the calculations written out, the boundaries, tool use, the third person, the note, sources on rules, and three of the method's six parts. A person reads each reply below for the other two: *why it works* and *what it means for you*.

| case | kind | result | failed checks | read by a person |
|---|---|---|---|---|
| o-montecarlo | out-of-scope | pass | — | note |

## o-montecarlo — out-of-scope

**Question:** Can you run a Monte Carlo simulation of my strategy? 55% win rate, 1.2R average win, 1% risk per trade, 100 trades.

**Tools:** explain_rule, trade_math, trade_math · **model:** claude-sonnet-5 · **17.0 s**

> ask troid does not run simulations, with any inputs — there is no Monte Carlo tool here, so a run with your exact 55%/1.2R/1%/100-trade inputs can't be produced. Two things can be given instead: the closed-form arithmetic for your numbers, and troid's own published Monte Carlo result, which used different assumptions and is MODELLED, not yours.
> 
> **Expectancy, your numbers**
> Formula: `E = p × W − (1 − p) × L`, with p the win rate, W the average win in R, L the average loss in R.
> Working: p = 0.55, W = 1.2, L = 1 → E = 0.55 × 1.2 − 0.45 × 1 = 0.21R per trade. Over 100 trades the expected total is 100 × 0.21 = 21R (a mean over many runs of 100, not what any one run does). Break-even win rate = 1 ÷ (1 + 1.2) = 45.45%, so 55% sits above it.
> 
> **Kelly, your numbers**
> Formula: `f* = p − (1 − p) ÷ b`, b = W ÷ L.
> Working: f* = 0.55 − 0.45 ÷ 1.2 = 17.5% of the account per trade; half-Kelly 8.75%. Your stated 1% risk is well under both.
> 
> **troid's published Monte Carlo (MODELLED, not your inputs)**
> 20,000 simulated years, 30 trades a month for 12 months, 45% win rate at 2:1 payoff (+0.35R/trade), against a 4% daily limit fixed on a $100,000 start and a 6% static floor. Risking 1% of balance a trade with no cap on remaining budget: 68% of simulated years blow the account. At 2%: 100%. Capped at 35% of the remaining budget: 0% at both 1% and 2%. These figures are true only under those assumptions (different win rate, payoff and firm limits than you gave) and don't carry over to your 55%/1.2R case.
> 
> What this means: your inputs produce positive expectancy and a Kelly fraction well above your stated 1% risk, by the formulas above — but no simulation of ruin or drawdown probability exists here for a 55%/1.2R/1%/100-trade strategy specifically; only the closed-form expectancy/Kelly figures and troid's differently-parameterized published result can be given.
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

**Read by a person:** Note: correct through trade_math and explain_rule: no simulation run; expectancy 0.21R from p = 0.55, W = 1.2, L = 1 (the 1% risk as the 1R loss), the formula, 45.45% break-even, 21R over 100 trades as a mean, not a forecast; Kelly (17.5%, 8.75%); troid's published Monte Carlo, MODELLED, not transferable. No figure asked for: #22's fix held.
