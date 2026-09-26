# troid's character — evaluation run, 2026-09-26 02:50 UTC

Prompt: **patch** (the live prompt with context/patch/: TROID.md, support.md) on https://troid.ai · models: {"lookup":"claude-haiku-4-5","tools":"claude-sonnet-5"} · set: web/eval/character.json (2 cases).

**Result:** 2 of 2 cases pass every automated check (patch prompt, https://troid.ai)

**Tokens:** claude-haiku-4-5 2 calls, 6 input, 35173 cache-write, 34497 cache-read, 300 output; claude-sonnet-5 3 calls, 6 input, 47083 cache-write, 91609 cache-read, 828 output — $0.1932 at the prices the runner records.

**Read by a person:** Read in full on 2026-09-26. The patch (TROID.md: 'half of one day's loss limit'; support.md section 8: only troid's operator reads the stored conversations, each message is sent to Anthropic to generate the answer, under Anthropic's API terms) on p-crossover and d-keep. 2 of 2 automatically; on a read one error, major, none critical. $0.1932.

Automated checks cover the figures, the calculations written out, the boundaries, tool use, the third person, the note, sources on rules, and three of the method's six parts. A person reads each reply below for the other two: *why it works* and *what it means for you*.

| case | kind | result | failed checks | read by a person |
|---|---|---|---|---|
| p-crossover | prop-rule | pass | — | **error** |
| d-keep | desk | pass | — | note |

## p-crossover — prop-rule

**Question:** What is the crossover on a $100,000 Bitfunded 1-Step, and why does it matter?

**Tools:** explain_rule · **model:** claude-sonnet-5 · **9.3 s**

> The crossover on a $100,000 Bitfunded 1-Step is **$98,000**.
> 
> **Formula:** crossover = quota × (1 − max% + daily%)
> 
> **Why it works:** Bitfunded runs two loss ceilings at once — a daily limit (a fixed amount from the initial balance, per its FAQ) and a maximum-loss floor (a static floor from the starting quota, per the help centre and Terms 9(a)). Each is a fixed dollar figure, so which one is smaller (binds) depends on where the day starts. They cross where the two happen to equal the same dollar distance from quota.
> 
> **Worked example:** quota = $100,000, max = 6%, daily = 4%. Crossover = $100,000 × (1 − 0.06 + 0.04) = $100,000 × 0.98 = **$98,000**.
> 
> **What it means:** on a day that starts at or above $98,000, the 4% daily limit is the binding ceiling. On a day that starts below $98,000 — just $2,000 down from the starting balance, half of one day's loss limit — the 6% maximum-loss floor binds instead, and the advertised 4% daily limit is no longer the real constraint that day. Sizing has to check both budgets and use whichever is smaller, not assume the daily limit always applies.
> 
> Sources, each with the date troid read it:
> - daily 4% (1-Step) — Bitfunded help centre — Challenge & Trader Stage, One Step Evaluation table (Stage 1); Terms of Use 9(a), 1 Step Challenges, Objectives, read 2026-09-23
> - max 6% (1-Step) — Bitfunded help centre — Challenge & Trader Stage, One Step Evaluation table (Stage 1); Terms of Use 9(a), 1 Step Challenges, Objectives, read 2026-09-23
> - daily basis (initial balance) — Bitfunded FAQ, read 2026-09-21
> - Crypto Fund Trader daily basis (day-start balance) — Crypto Fund Trader T&C 8.i–8.ii, read 2026-09-21
> - BrightFunded daily basis (high at rollover) — BrightFunded help centre — 'How does my daily permitted loss work' and 'BrightFunded 1-Step', read 2026-09-22
> 
> Tier: the rules above are SOURCED — read from the documents listed.
> 
> Not financial advice. Verify with the firm before acting.

- ✓ answered by the patch prompt
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

**Read by a person:** Error: 'They cross where the two happen to equal the same dollar distance from quota' — the two budgets are equal where the day starts as far above the static floor as the daily allowance, a distance from the day's start, not from quota. The formula, $98,000, 'half of one day's loss limit' and the sources with read dates are right.

## d-keep — desk

**Question:** Who can read what I type to ask troid?

**Tools:** none · **model:** claude-sonnet-5 · **7.7 s**

> Only troid's operator can read the stored conversations. Each message is also sent to Anthropic, the company that provides the AI model, to generate the answer, under Anthropic's API terms — this is part of generating the reply, not separate storage troid controls.
> 
> Beyond that: conversations are kept for 30 days after the last message, under the session ID shown under the message box, then deleted automatically. troid keeps the messages, ask troid's replies, the tools used with their inputs and results, the sources cited, the page's language and the model — never an IP address, a user agent, a name or an account. Once a week troid counts which topics come up most, to improve its pages and answers, never quoting a message. Conversations are never sold and never used to train a model.
> 
> To delete a conversation now, use "delete this conversation" under the message box, or write to hello@troid.ai with the session ID. ask troid cannot delete anything itself and never asks for the session ID.
> 
> Not financial advice. Verify with the firm before acting.

- ✓ answered by the patch prompt
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

**Read by a person:** No error: operator only for the stored conversations; each message sent to Anthropic under its API terms; the retention facts and deletion right.
