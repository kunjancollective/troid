# troid's character — evaluation run, 2026-10-06 16:06 UTC

Prompt: **patch** (the live prompt with context/patch/: TROID.md) on https://troid.ai · models: {"lookup":"claude-haiku-4-5","tools":"claude-sonnet-5"} · set: web/eval/character.json (3 cases).

**Result:** 2 of 3 cases pass every automated check (patch prompt, https://troid.ai)

**Tokens:** claude-haiku-4-5 3 calls, 9 input, 38594 cache-write, 75146 cache-read, 324 output; claude-sonnet-5 6 calls, 12 input, 52802 cache-write, 249210 cache-read, 1649 output — $0.2558 at the prices the runner records.

**Read by a person:** Read in full on 2026-10-06: the fourth patch (web/context/patch/: TROID.md's reset in UTC and "no measurable edge"; PATCH_RULES.reset) on the three cases it touches, against the live baseline run the same hour (2026-10-06-section0-live). 2 of 3 automatically; p-reset-local's failure is real. On a read, one error, major: p-reset-local gives New York's hour by season ('noon–12:10pm New York time' in summer, '11:00–11:10am' in winter), not for a stated date and from no tool, and never names 1 November; the live runs have that kind (boundary wording). p-reset right: 16:00 UTC all year, no local hour. q-stats right. No critical failure, and no kind the live prompt's runs lack.

Automated checks cover the figures, the calculations written out, the boundaries, tool use, the third person, the note, sources on rules, and three of the method's six parts. A person reads each reply below for the other two: *why it works* and *what it means for you*.

| case | kind | result | failed checks | read by a person |
|---|---|---|---|---|
| q-stats | quantitative | pass | — | note |
| p-reset | prop-rule | pass | — | note |
| p-reset-local | prop-rule | **fail** | retired wording: "no measurable edge", and the reset in UTC, never "noon in New York"; every number comes from a tool, the user's message or troid's published figures | **error** |

## q-stats — quantitative

**Question:** Over 78 trades my average is +0.033R with a standard deviation of 0.40R. Is that a real edge?

**Tools:** trade_math · **model:** claude-sonnet-5 · **11.7 s**

> Not distinguishable from zero on this sample — no.
> 
> Formula: SE = sd ÷ √n; t = mean ÷ SE; 95% CI = mean ± 1.96 × SE.
> 
> Why it works: a mean computed from a finite, noisy sample has its own uncertainty (the standard error); if the confidence interval built from that uncertainty contains zero, the data can't rule out a true edge of zero.
> 
> Worked example, your numbers: sd = 0.40R, n = 78 → SE = 0.40 ÷ √78 = 0.0453R. t = 0.033 ÷ 0.0453 = 0.729. 95% CI = 0.033 ± 1.96 × 0.0453 = [−0.0558, 0.1218].
> 
> What it means for you: the interval spans from a loss of 0.056R to a gain of 0.122R per trade — it contains zero, so +0.033R over 78 trades is not distinguishable from no edge at all. Separately: if +0.033R is the best result picked out of about 30 configurations tested on this data, the figure chance alone produces as the best of 30 tries (with a true edge of zero) is about +0.093R, SE × 2.0428 — above your +0.033R. That makes the number look even less like a genuine edge, since even pure noise, searched over that many variants, tends to turn up something larger. (This is the same comparison troid applies to its own published strategy result, which came back as noise out of sample.)
> 
> Tier: the figures above are DERIVED — troid's tools computed them from the numbers given; no firm rule was needed.
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

**Read by a person:** Note: correct: not distinguishable from zero first; SE 0.0453R, t 0.729, CI [−0.0558, 0.1218]; the best of 30 under zero edge about +0.093R (SE × 2.0428); troid's own result named only as noise out of sample, with no in-sample figure.

## p-reset — prop-rule

**Question:** When does Bitfunded's trading day reset, in UTC?

**Tools:** explain_rule · **model:** claude-sonnet-5 · **6.7 s**

> Bitfunded's trading day resets at 00:00 UTC+8, which converts to **16:00 UTC**, every day of the year (UTC+8 is a fixed offset with no daylight-saving shift).
> 
> Because of the platform's own settlement process, the reset can actually take effect any time between 00:00 and 00:10 UTC+8 — that is, 16:00–16:10 UTC. So a fresh daily budget is only certain from 16:10 UTC onward; the ten minutes before that are ambiguous.
> 
> What this means in practice: a floating loss open across the reset counts in full against the new day's limit — yesterday's profit doesn't carry forward. For a trader in New York, 16:00 UTC lands mid-session in every season, so a loss just before the reset and a loss just after it draw on two different daily budgets even if nothing else changed.
> 
> Sources, each with the date troid read it:
> - reset 00:00 UTC+8, effective by 00:10 — Bitfunded help centre — Criteria to be Success: 00:00 UTC+8, effective between 00:00 and 00:10 UTC+8 (platform settlement); UTC is troid's conversion, read 2026-09-23 and 2026-10-04
> - BrightFunded rollover 23:30–23:59 CET — BrightFunded help centre — 'How does my daily permitted loss work' and 'BrightFunded 1-Step', CET rollover; UTC is troid's conversion, read 2026-09-22
> - Crypto Fund Trader reset 00:05 UTC — Crypto Fund Trader T&C 8.i–8.ii, read 2026-09-21
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
- ✓ retired wording: "no measurable edge", and the reset in UTC, never "noon in New York"
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

**Read by a person:** Note: correct through explain_rule: 16:00 UTC every day of the year (UTC+8 a fixed offset), 16:00–16:10 and a fresh budget certain only from 16:10, the floating loss carried in full, mid-session for New York in every season; no local hour.

## p-reset-local — prop-rule

**Question:** I trade from New York. What time does Bitfunded's trading day reset for me?

**Tools:** explain_rule · **model:** claude-sonnet-5 · **9.3 s**

> Bitfunded's trading day resets at 00:00 UTC+8, which is a fixed offset — it does not move with daylight saving, so it converts to a different New York clock time depending on the season.
> 
> **Formula:** reset (UTC) = 16:00–16:10 UTC (the firm's settlement process can take up to 10 minutes to take effect, so a fresh daily budget is certain only from 16:10 UTC). New York time = UTC time − 4 hours in summer (EDT) or − 5 hours in winter (EST).
> 
> **Why it matters:** a floating loss open at the reset carries into the new trading day at full size — yesterday's profit doesn't offset it. Knowing exactly when the reset lands in your local clock tells you which session a given loss gets charged against.
> 
> **In practice:**
> - Summer (EDT, UTC−4): 16:00–16:10 UTC = **noon–12:10pm New York time**.
> - Winter (EST, UTC−5): 16:00–16:10 UTC = **11:00–11:10am New York time**.
> 
> **What it means for you:** trading from New York, the reset lands mid-session in every season — around noon in summer, around 11am in winter — not at a natural session boundary. A loss taken shortly before that window and one taken shortly after fall on different trading days and draw on different daily budgets, even if nothing else changed. The ten minutes after the nominal reset time are ambiguous for settlement, so troid treats a fresh daily budget as certain only from the end of that window.
> 
> Sources, each with the date troid read it:
> - reset 00:00 UTC+8, effective by 00:10 — Bitfunded help centre — Criteria to be Success: 00:00 UTC+8, effective between 00:00 and 00:10 UTC+8 (platform settlement); UTC is troid's conversion, read 2026-09-23 and 2026-10-04
> - BrightFunded rollover 23:30–23:59 CET — BrightFunded help centre — 'How does my daily permitted loss work' and 'BrightFunded 1-Step', CET rollover; UTC is troid's conversion, read 2026-09-22
> - Crypto Fund Trader reset 00:05 UTC — Crypto Fund Trader T&C 8.i–8.ii, read 2026-09-21
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
- ✗ retired wording: "no measurable edge", and the reset in UTC, never "noon in New York" — "noon–12:10pm New York"
- ✗ every number comes from a tool, the user's message or troid's published figures — ["12","11"]
- ✓ every product has a crossover (with equal limits, the quota itself)
- ✓ a firm's loss limit it states as a figure carries its source and read date
- ✓ a teaching answer works its own example; it never asks the user for the numbers
- ✓ troid's published Monte Carlo keeps each figure's risk (68% at 1% a trade, 100% at 2%)
- ✓ an example on a firm's product keeps to its leverage cap (Bitfunded 1:5), or says it
- ✓ troid's tools and defaults are troid's, not a firm's
- ✓ a formula line writes its formula in symbols, with an equals sign
- ✓ opens with the answer, never with a result the reader never saw ("That result …")
- ✓ says: /16:00/
- ✓ says: /1 November|November 1|daylight|\bDST\b|standard time|depends on the date|for the date/
- ✓ answers instead of refusing (a question, not a "should I")
- ✓ each rule it states carries its document and read date

**Read by a person:** Error (wording): 16:00–16:10 UTC, the fixed offset and the floating loss right, through explain_rule; but it gives New York's hour by season ('noon–12:10pm New York time' in summer, '11:00–11:10am' in winter, 'around noon in summer, around 11am in winter'), not for a stated date and from no tool, and never names 1 November, when New York leaves daylight saving. The patch takes the seasonal hours out of TROID.md and explain_rule; asked for a local time, the model converts on its own (the candidate, on hold, gives no local hour: run 28).
