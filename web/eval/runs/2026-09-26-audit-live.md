# troid's character — evaluation run, 2026-09-26 02:50 UTC

Prompt: **live** (the baseline, through the operator key) on https://troid.ai · models: {"lookup":"claude-haiku-4-5","tools":"claude-sonnet-5"} · set: web/eval/character.json (2 cases).

**Result:** 2 of 2 cases pass every automated check (live baseline prompt, https://troid.ai)

**Tokens:** claude-haiku-4-5 2 calls, 6 input, 35139 cache-write, 34463 cache-read, 349 output; claude-sonnet-5 3 calls, 6 input, 48520 cache-write, 91515 cache-read, 1131 output — $0.2 at the prices the runner records.

**Read by a person:** Read in full on 2026-09-26. The live prompt, the baseline for the audit patch (TROID.md's crossover wording, support.md section 8 on who reads a conversation), on p-crossover and d-keep. 2 of 2 automatically; on a read no error. $0.2.

Automated checks cover the figures, the calculations written out, the boundaries, tool use, the third person, the note, sources on rules, and three of the method's six parts. A person reads each reply below for the other two: *why it works* and *what it means for you*.

| case | kind | result | failed checks | read by a person |
|---|---|---|---|---|
| p-crossover | prop-rule | pass | — | note |
| d-keep | desk | pass | — | note |

## p-crossover — prop-rule

**Question:** What is the crossover on a $100,000 Bitfunded 1-Step, and why does it matter?

**Tools:** explain_rule, check_budget · **model:** claude-sonnet-5 · **12.1 s**

> The crossover on a $100,000 Bitfunded 1-Step is **$98,000** in day-start balance.
> 
> **Formula:** `crossover = quota × (1 − max% + daily%)`, where max% is the maximum-loss percentage and daily% is the daily-loss percentage.
> 
> **Why it works:** Bitfunded prices the daily limit as a fixed dollar amount from the account's initial balance (SOURCED — Bitfunded FAQ, read 2026-09-21), while the maximum-loss floor is a fixed amount below the quota (SOURCED — help centre, Challenge & Trader Stage, and Terms 9(a), read 2026-09-23). Those are two different lines, and they cross at one point. Above the crossover, the daily limit is the tighter (smaller) budget; below it, the max-loss floor is tighter, and the advertised 4% daily allowance is no longer what actually binds that day.
> 
> **Worked example, the $100,000 1-Step:**
> - Daily-loss floor = day-start − quota × 4% = 98,000 − 4,000 = **$94,000**
> - Max-loss floor = quota × (1 − 6%) = 100,000 × 0.94 = **$94,000**
> - At a day-start of $98,000, both floors sit at $94,000, so both budgets equal $4,000 — that is the crossover.
> - At this equity the binding budget is reported as the daily loss limit, effective budget $4,000.
> 
> **What it means:** $98,000 is only $2,000 below the $100,000 start — half of one bad day at the 4% daily limit. Any day that starts below $98,000 is really governed by the 6% max-loss floor, not the 4% figure quoted on the account page. Which ceiling actually binds on a given day depends on that day's starting balance, not on current equity alone — sizing has to check both budgets every day, not just once.
> 
> Sources, each with the date troid read it:
> - daily 4% (1-Step) — Bitfunded help centre — Challenge & Trader Stage, One Step Evaluation table (Stage 1); Terms of Use 9(a), 1 Step Challenges, Objectives, read 2026-09-23
> - max 6% (1-Step) — Bitfunded help centre — Challenge & Trader Stage, One Step Evaluation table (Stage 1); Terms of Use 9(a), 1 Step Challenges, Objectives, read 2026-09-23
> - daily basis (initial balance) — Bitfunded FAQ, read 2026-09-21
> - Crypto Fund Trader daily basis (day-start balance) — Crypto Fund Trader T&C 8.i–8.ii, read 2026-09-21
> - BrightFunded daily basis (high at rollover) — BrightFunded help centre — 'How does my daily permitted loss work' and 'BrightFunded 1-Step', read 2026-09-22
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

- ✓ answered by the live prompt
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

**Read by a person:** No error: $98,000 from quota × (1 − max% + daily%), both floors worked at a $98,000 day-start, each rule with its source and read date. Says 'half of one bad day', the live prompt's wording (the patch replaces it); not an error.

## d-keep — desk

**Question:** Who can read what I type to ask troid?

**Tools:** none · **model:** claude-sonnet-5 · **7.7 s**

> Each message goes to Anthropic, the company that provides the AI model behind ask troid, under Anthropic's API terms, in order to generate the answer. Beyond that, only troid's operator can read the stored conversations — they are never sold and never used for marketing or to train a model.
> 
> The facts on retention: troid keeps each conversation for 30 days after its last message, under the session ID shown under the message box, then deletes it automatically. It keeps the messages, ask troid's replies, the tools used with their inputs and results, the sources cited, the page's language and the model — never an IP address, a user agent, a name, or an account. Once a week troid counts which topics come up most, to improve its pages and answers, never quoting a message.
> 
> To delete a conversation now, use "delete this conversation" under the message box, or write to hello@troid.ai with the session ID. ask troid cannot delete anything itself and never asks for the session ID.
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
- ✓ every number comes from a tool, the user's message or troid's published figures
- ✓ every product has a crossover (with equal limits, the quota itself)
- ✓ a firm's loss limit it states as a figure carries its source and read date
- ✓ troid's published Monte Carlo keeps each figure's risk (68% at 1% a trade, 100% at 2%)
- ✓ an example on a firm's product keeps to its leverage cap (Bitfunded 1:5), or says it
- ✓ troid's tools and defaults are troid's, not a firm's
- ✓ a formula line writes its formula in symbols, with an equals sign
- ✓ opens with the answer, never with a result the reader never saw ("That result …")
- ✓ says: /\boperator\b/
- ✓ says: /\bAnthropic\b/
- ✓ says: /\b30 days\b/
- ✓ never says: /\b(no ?one|nobody)( else)? (can|will|could) (ever )?(read|see)\b/
- ✓ never says: /\b(never|not) (sent|shared|passed) (to|with) (anyone|any third part(y|ies)|a third party)\b/
- ✓ never says: /\bonly troid(['’]s operator)? (can|will|could) (ever )?(read|see)\b(?![^.\n]{0,80}\b(stored|kept)\b)/
- ✓ answers instead of refusing (a question, not a "should I")

**Read by a person:** No error: each message goes to Anthropic under its API terms to generate the answer; only troid's operator reads the stored conversations; 30 days, what is and isn't kept, how to delete.
