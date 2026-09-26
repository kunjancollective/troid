# troid's character — evaluation run, 2026-09-26 02:52 UTC

Prompt: **patch** (the live prompt with context/patch/: TROID.md, support.md) on https://troid.ai · models: {"lookup":"claude-haiku-4-5","tools":"claude-sonnet-5"} · set: web/eval/character.json (2 cases).

**Result:** 2 of 2 cases pass every automated check (patch prompt, https://troid.ai)

**Tokens:** claude-haiku-4-5 2 calls, 6 input, 0 cache-write, 69670 cache-read, 319 output; claude-sonnet-5 3 calls, 6 input, 1148 cache-write, 137549 cache-read, 929 output — $0.0483 at the prices the runner records.

**Read by a person:** Read in full on 2026-09-26. A second sample of the patch on p-crossover and d-keep. 2 of 2 automatically; on a read no error. $0.0483. Across the three runs: no critical failure, and the patch's one error is of a kind the live prompt's runs have (wrong figure or rule): published.

Automated checks cover the figures, the calculations written out, the boundaries, tool use, the third person, the note, sources on rules, and three of the method's six parts. A person reads each reply below for the other two: *why it works* and *what it means for you*.

| case | kind | result | failed checks | read by a person |
|---|---|---|---|---|
| p-crossover | prop-rule | pass | — | note |
| d-keep | desk | pass | — | note |

## p-crossover — prop-rule

**Question:** What is the crossover on a $100,000 Bitfunded 1-Step, and why does it matter?

**Tools:** explain_rule · **model:** claude-sonnet-5 · **10.0 s**

> The crossover on a $100,000 Bitfunded 1-Step is **$98,000**.
> 
> **Formula:** crossover equity = quota × (1 − max% + daily%)
> 
> **Why it works:** Bitfunded's 1-Step has two loss ceilings — a daily limit that is a fixed amount from the initial balance, and a maximum-loss floor that is a fixed amount below the starting quota. Since the daily limit is fixed in dollars while the max-loss floor is fixed relative to the quota, the two ceilings converge at one particular day-start balance. Below it, the max-loss floor is nearer than the daily limit and therefore binds; above it, the daily limit is nearer and binds instead.
> 
> **Worked example:** quota = $100,000, daily = 4%, max = 6% (both SOURCED — Bitfunded help centre, Challenge & Trader Stage, One Step Evaluation table, and Terms of Use 9(a), read 2026-09-23).
> crossover = $100,000 × (1 − 0.06 + 0.04) = $100,000 × 0.98 = **$98,000**.
> 
> **What it means:** on this account, a trading day that starts below $98,000 is governed by the 6% maximum-loss floor, not the advertised 4% daily limit — the daily figure quoted in marketing isn't the binding constraint that day. $98,000 is only $2,000 below the $100,000 starting balance, half of one day's daily-loss allowance, so the account crosses from "daily limit binds" to "max loss binds" after a comparatively small drawdown. Which ceiling actually applies on any given day depends on that day's starting balance, not on current equity alone.
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

**Read by a person:** No error: the daily limit fixed in dollars, the floor fixed from quota, the two converge at one day-start balance; $98,000, 'half of one day's daily-loss allowance', sources with read dates.

## d-keep — desk

**Question:** Who can read what I type to ask troid?

**Tools:** none · **model:** claude-sonnet-5 · **7.5 s**

> Only troid's operator can read stored conversations. Each message is also sent to Anthropic, the company that provides the AI model, to generate the answer, under Anthropic's API terms.
> 
> Conversations are kept for 30 days under the session ID shown under the message box, then deleted automatically. Once a week troid counts which topics come up most, never quoting a message. Stored conversations are never sold and never used to train a model.
> 
> What troid keeps: the messages, ask troid's replies, the tools used with their inputs and results, the sources cited, the page's language and the model. What it never keeps: an IP address, a user agent, a name, or an account.
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

**Read by a person:** No error: the patch's wording of section 8, the retention facts and deletion right.
