# troid's character — evaluation run, 2026-10-07 03:43 UTC

Prompt: **candidate** on https://troid.ai · models: {"lookup":"claude-haiku-4-5","tools":"claude-sonnet-5"} · set: web/eval/character.json (1 cases).

**Result:** 1 of 1 cases pass every automated check (candidate prompt, https://troid.ai)

**Tokens:** claude-haiku-4-5 1 calls, 3 input, 346 cache-write, 40733 cache-read, 55 output; claude-sonnet-5 2 calls, 4 input, 1538 cache-write, 107621 cache-read, 612 output — $0.0363 at the prices the runner records.

**Read by a person:** Read in full on 2026-10-07: p-crossover alone on the candidate of #22 (answer and formula first, figures from the question, each thing said once), 01 of 03. Automated checks pass. No error on a read. $0.0363 on the eval key.

Automated checks cover the figures, the calculations written out, the boundaries, tool use, the third person, the note, sources on rules, and three of the method's six parts. A person reads each reply below for the other two: *why it works* and *what it means for you*.

| case | kind | result | failed checks | read by a person |
|---|---|---|---|---|
| p-crossover | prop-rule | pass | — | note |

## p-crossover — prop-rule

**Question:** What is the crossover on a $100,000 Bitfunded 1-Step, and why does it matter?

**Tools:** explain_rule · **model:** claude-sonnet-5 · **8.8 s**

> The crossover on a $100,000 Bitfunded 1-Step is **$98,000**.
> 
> **Formula:** crossover = quota × (1 − max% + daily%) = 100,000 × (1 − 0.06 + 0.04) = 100,000 × 0.98 = $98,000.
> 
> **Why it works:** Bitfunded runs two loss ceilings at once — a daily limit (a fixed dollar amount, 4% of the initial balance) and a maximum-loss floor (a static floor, 6% below the starting quota, at $94,000). Which one actually constrains a given day depends on where the day starts, not on equity alone. Above $98,000 at the day's start, the $94,000 floor is far enough away that the daily limit (day-start minus 4% of $100,000) is reached first. Below $98,000, the floor is the closer boundary and binds instead — the advertised 4% daily figure stops being the real constraint. A day starting less than $2,000 below the $100,000 start is still bound by the daily limit, however much ground was lost or recovered earlier.
> 
> **What it means:** on a day that starts exactly at $100,000, the maximum-loss budget is $6,000 (100,000 − 94,000) and the daily budget is $4,000 — the daily limit binds, since it's smaller. On a day that starts below $98,000, the max-loss budget shrinks under $4,000 and becomes the smaller, binding one instead. Both ceilings count floating losses on open positions — an account can fail mid-trade, with no close required, if either ceiling is reached.
> 
> Sources, each with the date troid read it:
> - daily 4% (1-Step) — Bitfunded help centre — Challenge & Trader Stage, One Step Evaluation table (Stage 1); Terms of Use 9(a), 1 Step Challenges, Objectives, read 2026-09-23
> - max 6% (1-Step) — Bitfunded help centre — Challenge & Trader Stage, One Step Evaluation table (Stage 1); Terms of Use 9(a), 1 Step Challenges, Objectives, read 2026-09-23
> - daily basis (initial balance) — Bitfunded FAQ, read 2026-09-21
> - Crypto Fund Trader daily basis (day-start balance) — Crypto Fund Trader T&C 8.i–8.ii, read 2026-09-21
> - BrightFunded daily basis (high at rollover) — BrightFunded help centre — 'How does my daily permitted loss work' and 'BrightFunded 1-Step', read 2026-09-22
> - floating losses count toward the daily and maximum loss (Bitfunded) — Bitfunded help centre — Criteria to be Success, 1. Maximum Daily Loss and 2. Maximum Loss (floating losses are in both calculations; an open position that reaches either limit fails the account), read 2026-09-24
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

**Read by a person:** Note: correct through explain_rule: $98,000 first; quota × (1 − max% + daily%) worked; the daily limit a fixed $4,000 from the initial balance, the static $94,000 floor; below $98,000 the floor binds with under $4,000 of room, between $98,000 and $100,000 and above it the daily limit; $6,000 only at a $100,000 start; floating losses. No sources paragraph: #22's fix held; run 28's held too.
