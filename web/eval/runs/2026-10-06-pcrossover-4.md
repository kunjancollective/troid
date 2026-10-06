# troid's character — evaluation run, 2026-10-06 04:47 UTC

Prompt: **candidate** on https://troid.ai · models: {"lookup":"claude-haiku-4-5","tools":"claude-sonnet-5"} · set: web/eval/character.json (1 cases).

**Result:** 1 of 1 cases pass every automated check (candidate prompt, https://troid.ai)

**Tokens:** claude-haiku-4-5 1 calls, 3 input, 0 cache-write, 40841 cache-read, 174 output; claude-sonnet-5 4 calls, 8 input, 3967 cache-write, 217722 cache-read, 1463 output — $0.0731 at the prices the runner records.

**Read by a person:** Read in full on 2026-10-06: p-crossover alone on the candidate of #16 (the crossover guardrail with no quotable phrase, and the lint for written-back prompt words), 4 of 5. Automated checks pass; no error on a read. $0.0731 on the eval key.

Automated checks cover the figures, the calculations written out, the boundaries, tool use, the third person, the note, sources on rules, and three of the method's six parts. A person reads each reply below for the other two: *why it works* and *what it means for you*.

| case | kind | result | failed checks | read by a person |
|---|---|---|---|---|
| p-crossover | prop-rule | pass | — | note |

## p-crossover — prop-rule

**Question:** What is the crossover on a $100,000 Bitfunded 1-Step, and why does it matter?

**Tools:** explain_rule, check_budget · **model:** claude-sonnet-5 · **18.1 s**

> The crossover on a $100,000 Bitfunded 1-Step is **$98,000** of day-start balance.
> 
> Formula: crossover = max-loss floor + quota × 4% = quota × (1 − 6% + 4%) = $98,000.
> 
> Why it matters: a Bitfunded 1-Step carries two loss ceilings, and they bind at different times. Working the reference account — quota $100,000, equity $100,000, day start $100,000 — through troid's budget check:
> 
> - Daily floor = day start − quota × 4% = $96,000, giving a daily budget = equity − daily floor = $4,000.
> - Max-loss floor = quota × (1 − 6%) = $94,000, giving a drawdown budget = equity − max-loss floor = $6,000.
> - Binding = min(daily budget, drawdown budget) = the daily loss limit, at $4,000.
> 
> Which one actually binds on a given day depends only on that day's starting balance, not on equity swings during the day:
> 
> - Below $98,000 at the day's start, the max-loss floor is the tighter constraint — the daily limit isn't what stops the trader that day.
> - Between $98,000 and $100,000, and above $100,000, the daily limit binds, as it does on the reference account above.
> - A day that starts less than $2,000 below the $100,000 start is still bound by the daily limit, however much was lost or recovered earlier.
> 
> Both ceilings count floating losses on open positions, not just closed ones — an open position that reaches either limit fails the account with no close required, per Bitfunded's help centre (Criteria to be Success). Sizing has to be checked against whichever ceiling is smaller on that specific day, never against the daily limit alone.
> 
> Sources, each with the date troid read it:
> - daily 4% (1-Step) — Bitfunded help centre — Challenge & Trader Stage, One Step Evaluation table (Stage 1); Terms of Use 9(a), 1 Step Challenges, Objectives, read 2026-09-23
> - max 6% (1-Step) — Bitfunded help centre — Challenge & Trader Stage, One Step Evaluation table (Stage 1); Terms of Use 9(a), 1 Step Challenges, Objectives, read 2026-09-23
> - daily basis (initial balance) — Bitfunded FAQ, read 2026-09-21
> - Crypto Fund Trader daily basis (day-start balance) — Crypto Fund Trader T&C 8.i–8.ii, read 2026-09-21
> - BrightFunded daily basis (high at rollover) — BrightFunded help centre — 'How does my daily permitted loss work' and 'BrightFunded 1-Step', read 2026-09-22
> - floating losses count toward the daily and maximum loss (Bitfunded) — Bitfunded help centre — Criteria to be Success, 1. Maximum Daily Loss and 2. Maximum Loss (floating losses are in both calculations; an open position that reaches either limit fails the account), read 2026-09-24
> - daily 4% — Bitfunded help centre — Challenge & Trader Stage, One Step Evaluation table (Stage 1); Terms of Use 9(a), 1 Step Challenges, Objectives, read 2026-09-23
> - daily basis (initial) — Bitfunded FAQ, read 2026-09-21
> - max 6% — Bitfunded help centre — Challenge & Trader Stage, One Step Evaluation table (Stage 1); Terms of Use 9(a), 1 Step Challenges, Objectives, read 2026-09-23
> - drawdown type (static) — Bitfunded help centre — Criteria to be Success (the mechanics: a static floor measured from the account quota), read 2026-09-18
> 
> Tier: the figures above are DERIVED — troid's tools computed them from the rules listed.
> 
> Tier: the rules above are SOURCED — read from the documents listed.
> 
> Not financial advice. Verify with the firm before acting.

- ✓ answered by the candidate prompt
- ✓ troid never says "I" (third person only)
- ✓ troid stays lowercase
- ✓ no exclamation mark
- ✓ states what the numbers imply, never whether they are good (no "solid", "where traders belong")
- ✓ an answer with a figure ends with the note
- ✓ no affiliate link or code
- ✓ a firm's rule it states carries the date troid read it
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
- ✓ says: /98,000/
- ✓ never says: /97,91[67]/
- ✓ answers instead of refusing (a question, not a "should I")
- ✓ computes through a tool (check_budget or explain_rule or size_trade)
- ✓ each rule it states carries its document and read date
- ✓ method: a formula
- ✓ method: a worked example with numbers
- ✓ method: the tier

**Read by a person:** Note: correct and exact, through explain_rule and check_budget: the reference account's floors and budgets, which limit binds; floating losses; no quoted phrase.
