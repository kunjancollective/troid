# troid's character — evaluation run, 2026-10-08 16:06 UTC

Prompt: **live** (the baseline, through the operator key) on https://troid.ai · models: {"lookup":"claude-haiku-4-5","tools":"claude-sonnet-5"} · set: web/eval/character.json (1 cases).

**Result:** 1 of 1 cases pass every automated check (live baseline prompt, https://troid.ai)

**Tokens:** claude-haiku-4-5 1 calls, 3 input, 41221 cache-write, 0 cache-read, 209 output; claude-sonnet-5 3 calls, 6 input, 58845 cache-write, 111949 cache-read, 1750 output — $0.2396 at the prices the runner records.

Automated checks cover the figures, the calculations written out, the boundaries, tool use, the third person, the note, sources on rules, and three of the method's six parts. A person reads each reply below for the other two: *why it works* and *what it means for you*.

| case | kind | result | failed checks |
|---|---|---|---|
| p-size | prop-rule | pass | — |

## p-size — prop-rule

**Question:** Size a short on a $100,000 Bitfunded 1-Step. Equity and day-start balance are both $96,000, entry 77,872, stop 0.3% above entry, risking 0.5%.

**Tools:** size_trade · **model:** claude-sonnet-5 · **17.9 s**

> **Verdict: OK.**
> 
> **Which ceiling binds:** equity $96,000 is below the $98,000 crossover (quota × (1 − 6% + 4%) = $98,000), so the max-loss floor binds, not the daily limit.
> 
> - Daily floor = day start − quota × 4% = 96,000 − 4,000 = $92,000 → daily budget = equity − daily floor = $4,000
> - Max-loss floor = quota × (1 − 6%) = $94,000 → drawdown budget = equity − floor = $2,000
> - Binding = min(4,000, 2,000) = **$2,000 (max drawdown)**
> 
> **Sizing:**
> - Stop = entry × (1 + 0.3%) = $78,105.616
> - Intended risk = equity × 0.5% = $480; cap = budget × 35% = $700; risk used = min = **$480**
> - Stop distance = $233.616; fee per unit = (entry+stop) × 0.04% = $62.391
> - Quantity = 480 ÷ (233.616 + 62.391) = **1.621583**
> - Notional = $126,275.91; margin = notional ÷ 5 = **$25,255.18** (fits under $96,000 equity)
> - Fees = $101.17 → **21.08% of risk** (a tight 0.3% stop, so fees dominate)
> - Loss at stop = $480 = risk, as intended
> - Budget used = 480 ÷ 2,000 = **24%**
> - Losses left = ceil(2,000 ÷ 480) − 1 = **4** (this one included); the **5th** loss reaches the floor
> - Target (2R, troid's default) = $77,404.77
> 
> **Circuit-breaker order:** stop (0.3%) → max-loss floor (1.58%) → daily limit (3.17%) → exchange liquidation under cross margin (75.15%, troid's assumed 0.5% maintenance margin, troid's default margin mode). Nothing but the stop sits in front of the firm's own floor.
> 
> Sources, each with the date troid read it:
> - daily 4% — Bitfunded help centre — Challenge & Trader Stage, One Step Evaluation table (Stage 1); Terms of Use 9(a), 1 Step Challenges, Objectives, read 2026-09-23
> - daily basis (initial) — Bitfunded FAQ, read 2026-09-21
> - max 6% — Bitfunded help centre — Challenge & Trader Stage, One Step Evaluation table (Stage 1); Terms of Use 9(a), 1 Step Challenges, Objectives, read 2026-09-23
> - drawdown type (static) — Bitfunded help centre — Criteria to be Success (the mechanics: a static floor measured from the account quota), read 2026-09-18
> - fee 0.04% per side — Bitfunded help centre — Criteria to be Success, read 2026-09-18 and 2026-09-23 and 2026-10-04
> - leverage cap 5× — Bitfunded help centre — Challenge & Trader Stage, One Step Evaluation table (Leverage Ratio 1:5); Terms of Use 9(a), 1 Step Challenges (Up To 1:5 Leverage), read 2026-09-23
> - floating losses count toward the daily and maximum loss (Bitfunded) — Bitfunded help centre — Criteria to be Success, 1. Maximum Daily Loss and 2. Maximum Loss (floating losses are in both calculations; an open position that reaches either limit fails the account), read 2026-09-24
> 
> Tier: the figures above are DERIVED — troid's tools computed them from the rules listed.
> 
> troid's assumptions, not the firm's rules: exchange liquidation uses a 0.5% maintenance margin — troid's assumption, no firm source; margin mode cross — troid's default, not an input you gave; troid has no recorded source for this firm's margin modes; leverage 5× — troid's default, not an input you gave; budget cap 35% of the binding budget — troid's default, not an input you gave; target 2R — troid's default, not an input you gave.
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
- ✓ troid's published Monte Carlo keeps each figure's risk (68% at 1% a trade, 100% at 2%)
- ✓ an example on a firm's product keeps to its leverage cap (Bitfunded 1:5), or says it
- ✓ troid's tools and defaults are troid's, not a firm's
- ✓ a formula line writes its formula in symbols, with an equals sign
- ✓ opens with the answer, never with a result the reader never saw ("That result …")
- ✓ lists troid's assumptions once (the service lists them under the answer)
- ✓ says: /\b480\b/
- ✓ says: /(?<![\d.])1\.(?:622|6216|62158|621583|6215830|62158302|621583019|6215830192|62158301918)(?!\d)/
- ✓ says: /max(imum)?[- ](loss|drawdown)[^.]{0,120}bind|bind[^.]{0,80}max(imum)?[- ](loss|drawdown)|static floor[^.]{0,80}bind/
- ✓ never says: /\b75\.88\s?%/
- ✓ answers instead of refusing (a question, not a "should I")
- ✓ computes through a tool (size_trade)
- ✓ each rule it states carries its document and read date
- ✓ method: a formula
- ✓ method: a worked example with numbers
- ✓ method: the tier
