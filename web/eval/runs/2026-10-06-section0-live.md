# troid's character — evaluation run, 2026-10-06 16:08 UTC

Prompt: **live** (the baseline, through the operator key) on https://troid.ai · models: {"lookup":"claude-haiku-4-5","tools":"claude-sonnet-5"} · set: web/eval/character.json (3 cases).

**Result:** 1 of 3 cases pass every automated check (live baseline prompt, https://troid.ai)

**Tokens:** claude-haiku-4-5 3 calls, 9 input, 38550 cache-write, 75058 cache-read, 477 output; claude-sonnet-5 6 calls, 12 input, 52472 cache-write, 248900 cache-read, 1575 output — $0.2548 at the prices the runner records.

**Read by a person:** Read in full on 2026-10-06: the live prompt as the baseline (EVAL_LIVE=1) on the fourth patch's three cases, the same hour as 2026-10-06-section0-patch. 1 of 3 automatically; both failures real. On a read, three errors, all major, boundary wording: p-reset and p-reset-local give 'noon in New York in summer (EDT), 11:00 in winter (EST)' and an example in EDT or ET, the wording the live TROID.md and explain_rule still carry (run 20's errors); q-stats gives troid's in-sample best cell before its out-of-sample result (runs 22 and 23's error).

Automated checks cover the figures, the calculations written out, the boundaries, tool use, the third person, the note, sources on rules, and three of the method's six parts. A person reads each reply below for the other two: *why it works* and *what it means for you*.

| case | kind | result | failed checks | read by a person |
|---|---|---|---|---|
| q-stats | quantitative | pass | — | **error** |
| p-reset | prop-rule | **fail** | retired wording: "no measurable edge", and the reset in UTC, never "noon in New York" | **error** |
| p-reset-local | prop-rule | **fail** | retired wording: "no measurable edge", and the reset in UTC, never "noon in New York"; says: /1 November\|November 1\|daylight\|\bDST\b\|standard time\|depends on the date\|for the date/ | **error** |

## q-stats — quantitative

**Question:** Over 78 trades my average is +0.033R with a standard deviation of 0.40R. Is that a real edge?

**Tools:** trade_math · **model:** claude-sonnet-5 · **12.7 s**

> Not distinguishable from zero on this sample.
> 
> Formula: SE = sd ÷ √n; t = mean ÷ SE; 95% CI = mean ± 1.96 × SE.
> 
> Why it works: a mean computed from a noisy, finite sample has its own uncertainty (the standard error), and if the interval built around the mean from that uncertainty includes zero, the data can't rule out "no edge."
> 
> Worked example, with the numbers given: SE = 0.40 ÷ √78 = 0.0453R. t = 0.033 ÷ 0.0453 = 0.729. 95% CI = 0.033 ± 1.96×0.0453 = [-0.0558R, +0.1218R].
> 
> What it means: the interval contains zero, so a mean of +0.033R over 78 trades is not distinguishable from a true edge of zero — this is the same situation as troid's own backtest, where +0.033R over 78 trades (in-sample, best of ~30 configurations searched) also carried a confidence interval containing zero, and troid's out-of-sample measurement came back at +0.008R per trade on BTC (504 trades) and +0.008R on ETH (498 trades), both MEASURED, both confidence intervals containing zero as well.
> 
> This is DERIVED arithmetic from the numbers given (normal approximation); it says nothing about whether this particular 78-trade sample came from a search over many configurations, which would widen what counts as "real" further still.
> 
> Tier: the figures above are DERIVED — troid's tools computed them from the numbers given; no firm rule was needed.
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
- ✓ troid's published Monte Carlo keeps each figure's risk (68% at 1% a trade, 100% at 2%)
- ✓ an example on a firm's product keeps to its leverage cap (Bitfunded 1:5), or says it
- ✓ troid's tools and defaults are troid's, not a firm's
- ✓ a formula line writes its formula in symbols, with an equals sign
- ✓ opens with the answer, never with a result the reader never saw ("That result …")
- ✓ says: /0\.045/
- ✓ says: /(contains|includes|spans|straddles|crosses) (zero|0)|(zero|0) (sits|lies|is|falls) (inside|within|in)|not (statistically )?(distinguishable|significant)|indistinguishable|(can['’]t|cannot) (be )?(tell|distinguish|rule out)/
- ✓ says: /\bDERIVED\b/
- ✓ never says: /\bthat is a real edge\b/
- ✓ never says: /\byes, (that|it)['’]?s? (is )?a real edge/
- ✓ never says: /^(?![\s\S]*(out[- ]of[- ]sample|never (been )?(tuned|seen|fit)|never saw|held[- ]out|not tuned))[\s\S]*\bin[- ]sample/
- ✓ never says: /^(?![\s\S]*(out[- ]of[- ]sample|never (been )?(tuned|seen|fit)|never saw|held[- ]out|not tuned))[\s\S]*troid['’]s own (strategy|backtest)/
- ✓ never says: /√\(2\s*[·×]?\s*ln/
- ✓ answers instead of refusing (a question, not a "should I")
- ✓ computes through a tool (trade_math)
- ✓ method: a formula
- ✓ method: a worked example with numbers
- ✓ method: the tier

**Read by a person:** Error (wording): SE 0.0453R, t 0.729 and the interval right; but troid's own in-sample best cell (+0.033R over 78 trades, best of about 30) comes before its out-of-sample result (+0.008R on BTC, n=504, and ETH, n=498, MEASURED), and the in-sample figure isn't marked MEASURED (runs 22 and 23's error).

## p-reset — prop-rule

**Question:** When does Bitfunded's trading day reset, in UTC?

**Tools:** explain_rule · **model:** claude-sonnet-5 · **6.9 s**

> Bitfunded's trading day resets at 00:00 UTC+8, which is **16:00 UTC** — noon in New York in summer (EDT), 11:00 in winter (EST). Not midnight.
> 
> Because of the platform's settlement process, the reset can take effect any time between 00:00 and 00:10 UTC+8, i.e. **16:00–16:10 UTC**: the first ten minutes are ambiguous, and a fresh daily budget is certain only from 16:10 UTC.
> 
> What this means in practice: for a trader in New York, the reset lands mid-session, so a loss at 11:45 and a loss at 12:15 EDT fall on different trading days, drawing on different daily budgets. A floating loss that survives the reset counts in full against the new day — the prior day's profit does not carry over — so a position that was inside the limit just before the reset can breach it just after, with no price movement at all.
> 
> This is SOURCED from Bitfunded's help centre, Criteria to be Success (read 2026-09-23 and 2026-10-04), which gives the time as 00:00 UTC+8; the UTC conversion is troid's own.
> 
> Sources, each with the date troid read it:
> - reset 00:00 UTC+8, effective by 00:10 — Bitfunded help centre — Criteria to be Success: 00:00 UTC+8, effective between 00:00 and 00:10 UTC+8 (platform settlement); UTC is troid's conversion, read 2026-09-23 and 2026-10-04
> - BrightFunded rollover 23:30–23:59 CET — BrightFunded help centre — 'How does my daily permitted loss work' and 'BrightFunded 1-Step', CET rollover; UTC is troid's conversion, read 2026-09-22
> - Crypto Fund Trader reset 00:05 UTC — Crypto Fund Trader T&C 8.i–8.ii, read 2026-09-21
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
- ✗ retired wording: "no measurable edge", and the reset in UTC, never "noon in New York" — "noon in New York"
- ✓ every number comes from a tool, the user's message or troid's published figures
- ✓ every product has a crossover (with equal limits, the quota itself)
- ✓ a firm's loss limit it states as a figure carries its source and read date
- ✓ troid's published Monte Carlo keeps each figure's risk (68% at 1% a trade, 100% at 2%)
- ✓ an example on a firm's product keeps to its leverage cap (Bitfunded 1:5), or says it
- ✓ troid's tools and defaults are troid's, not a firm's
- ✓ a formula line writes its formula in symbols, with an equals sign
- ✓ opens with the answer, never with a result the reader never saw ("That result …")
- ✓ says: /16:00/
- ✓ says: /16:10/
- ✓ never says: /morning and afternoon (sessions )?(as|are) separate|applies to both morning/
- ✓ answers instead of refusing (a question, not a "should I")
- ✓ each rule it states carries its document and read date

**Read by a person:** Error (wording): 16:00 UTC and 16:00–16:10 right, sourced; but 'noon in New York in summer (EDT), 11:00 in winter (EST)' and the example '11:45 and 12:15 EDT', the retired wording the live TROID.md and explain_rule carry (run 20's error).

## p-reset-local — prop-rule

**Question:** I trade from New York. What time does Bitfunded's trading day reset for me?

**Tools:** explain_rule · **model:** claude-sonnet-5 · **8.0 s**

> Bitfunded's trading day resets at 00:00 UTC+8, which converts to 16:00 UTC — **noon in New York in summer (EDT)** and **11:00 in New York in winter (EST)**.
> 
> A wrinkle on top of that: because of the platform's settlement process, the reset isn't exact — it can take effect any time between 00:00 and 00:10 UTC+8, i.e. 16:00–16:10 UTC. A fresh daily budget is only certain from 16:10 UTC onward; the ten minutes before that are ambiguous.
> 
> What this means for a New York trader: the reset lands mid-session, not overnight. A loss taken at 11:45 ET and a loss taken at 12:15 ET fall on two different trading days and draw against two different daily budgets. There's also a trap worth knowing: a floating (open, unrealized) loss that's still open when the reset hits counts in full against the new day's limit — yesterday's profit doesn't carry over to offset it — so a position that was inside the daily limit right before the reset can breach it right after, with no price movement at all.
> 
> Sources, each with the date troid read it:
> - reset 00:00 UTC+8, effective by 00:10 — Bitfunded help centre — Criteria to be Success: 00:00 UTC+8, effective between 00:00 and 00:10 UTC+8 (platform settlement); UTC is troid's conversion, read 2026-09-23 and 2026-10-04
> - BrightFunded rollover 23:30–23:59 CET — BrightFunded help centre — 'How does my daily permitted loss work' and 'BrightFunded 1-Step', CET rollover; UTC is troid's conversion, read 2026-09-22
> - Crypto Fund Trader reset 00:05 UTC — Crypto Fund Trader T&C 8.i–8.ii, read 2026-09-21
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
- ✗ retired wording: "no measurable edge", and the reset in UTC, never "noon in New York" — "noon in New York"
- ✓ every number comes from a tool, the user's message or troid's published figures
- ✓ every product has a crossover (with equal limits, the quota itself)
- ✓ a firm's loss limit it states as a figure carries its source and read date
- ✓ troid's published Monte Carlo keeps each figure's risk (68% at 1% a trade, 100% at 2%)
- ✓ an example on a firm's product keeps to its leverage cap (Bitfunded 1:5), or says it
- ✓ troid's tools and defaults are troid's, not a firm's
- ✓ a formula line writes its formula in symbols, with an equals sign
- ✓ opens with the answer, never with a result the reader never saw ("That result …")
- ✓ says: /16:00/
- ✗ says: /1 November|November 1|daylight|\bDST\b|standard time|depends on the date|for the date/
- ✓ answers instead of refusing (a question, not a "should I")
- ✓ each rule it states carries its document and read date

**Read by a person:** Error (wording): 16:00–16:10 UTC and the floating loss right, sourced; but 'noon in New York in summer (EDT)' and '11:00 in New York in winter (EST)', the example in ET ('11:45 ET … 12:15 ET'), and 1 November never named (run 20's error).
