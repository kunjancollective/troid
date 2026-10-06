# troid's character — evaluation run, 2026-10-06 04:45 UTC

Prompt: **candidate** on https://troid.ai · models: {"lookup":"claude-haiku-4-5","tools":"claude-sonnet-5"} · set: web/eval/character.json (1 cases).

**Result:** 1 of 1 cases pass every automated check (candidate prompt, https://troid.ai)

**Tokens:** claude-haiku-4-5 1 calls, 3 input, 0 cache-write, 40841 cache-read, 55 output; claude-sonnet-5 2 calls, 4 input, 0 cache-write, 108523 cache-read, 616 output — $0.0323 at the prices the runner records.

Automated checks cover the figures, the calculations written out, the boundaries, tool use, the third person, the note, sources on rules, and three of the method's six parts. A person reads each reply below for the other two: *why it works* and *what it means for you*.

| case | kind | result | failed checks |
|---|---|---|---|
| p-crossover | prop-rule | pass | — |

## p-crossover — prop-rule

**Question:** What is the crossover on a $100,000 Bitfunded 1-Step, and why does it matter?

**Tools:** explain_rule · **model:** claude-sonnet-5 · **12.9 s**

> The crossover on a $100,000 Bitfunded 1-Step is **$98,000**.
> 
> **Formula:** crossover equity = quota × (1 − max% + daily%)
> 
> With quota = $100,000, max loss = 6%, daily loss = 4%: 100,000 × (1 − 0.06 + 0.04) = 100,000 × 0.98 = $98,000 — only $2,000 below the $100,000 starting balance.
> 
> **Why it works:** Bitfunded runs two separate ceilings at once — a daily limit (a fixed dollar amount, 4% of the *initial* balance, per the FAQ) and a maximum-loss floor (a static floor at 6% below the starting quota). Each day, whichever ceiling is numerically closer to the day's starting equity is the one that actually binds. Below $98,000 at the day's start, the 6% maximum-loss floor is already closer than another 4% daily drop would reach, so the floor binds and the advertised daily limit isn't the real constraint that day. Between $98,000 and $100,000, and above $100,000, the daily limit binds instead.
> 
> **What it means:** which ceiling binds turns on the day's *starting* balance alone, not on equity alone intraday, and not on how much was lost or given back before that day started. A day that starts less than $2,000 below the $100,000 start is still governed by the daily limit; only a day that starts below $98,000 is governed by the maximum-loss floor. Both ceilings count floating losses on open positions — Bitfunded auto-fails an account that reaches either one, with no close required.
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
- ✓ a firm's floating-loss rule carries its source, or says it is not yet recorded
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
