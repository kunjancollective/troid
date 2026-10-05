# troid's character — evaluation run, 2026-10-05 03:46 UTC

Prompt: **live** (the baseline, through the operator key) on https://troid.ai · models: {"lookup":"claude-haiku-4-5","tools":"claude-sonnet-5"} · set: web/eval/character.json (8 cases).

**Result:** 2 of 8 cases pass every automated check (live baseline prompt, https://troid.ai)

**Tokens:** claude-haiku-4-5 8 calls, 24 input, 40276 cache-write, 262703 cache-read, 2368 output; claude-sonnet-5 17 calls, 34 input, 60844 cache-write, 797532 cache-read, 6917 output — $0.4694 at the prices the runner records.

**Read by a person:** Read in full on 2026-10-05. The live prompt through the operator key (EVAL_LIVE=1) on the same eight cases. 2 of 8 automatically. On a read, seven errors, two critical. p-size gives the user's size, margin, fees and liquidation at the live tools' fee convention, both fees priced at entry: 1.622095 units where troid's desk gives 1.621583, the calculator audit's F6, which the owner's line of 30 Sep refuses. o-montecarlo says 'Let's' twice. The same convention puts ex-r's 1R with fees at $523.03 (the desk's $522.83) and b-stop's quantity at 0.369195 (0.369336). p-assets says troid has no list of Bitfunded's assets (the owner's live test of 2026-10-04). $0.4694 on the eval key.

Automated checks cover the figures, the calculations written out, the boundaries, tool use, the third person, the note, sources on rules, and three of the method's six parts. A person reads each reply below for the other two: *why it works* and *what it means for you*.

| case | kind | result | failed checks | read by a person |
|---|---|---|---|---|
| ex-r (example) | beginner | **fail** | every number comes from a tool, the user's message or troid's published figures | **error** |
| b-stop | beginner | pass | — | **error** |
| b-leverage | beginner | pass | — | note |
| p-crossover | prop-rule | **fail** | every number comes from a tool, the user's message or troid's published figures | **error** |
| p-assets | prop-rule | **fail** | says: /\bTSLA\b/; says: /2026-09-24\|24 Sep(tember)? 2026\|September 24,? 2026/; computes through a tool (firm_assets) | **error** |
| p-ladder-instant | prop-rule | **fail** | every number comes from a tool, the user's message or troid's published figures; says: /2026-10-04\|4 Oct(ober)? 2026\|October 4,? 2026/ | **error** |
| p-size | prop-rule | **fail** | says: /(?<![\d.])1\.(?:622\|6216\|62158\|621583\|6215830\|62158302\|621583019\|6215830192\|62158301918)(?!\d)/ | **error** |
| o-montecarlo | out-of-scope | **fail** | troid never says "I" (third person only); names none of troid's own instructions and announces no form ("support.md section 4", "result first, one line") | **error** |

## ex-r — beginner (a worked example in TROID-CHARACTER.md)

**Question:** What does R mean?

**Tools:** trade_math · **model:** claude-sonnet-5 · **12.7 s**

> R is the amount risked on a single trade — the dollar loss if the stop is hit.
> 
> **Formula:** `1R = |entry − stop| × position size`.
> 
> **Why it matters:** measuring every trade's outcome in R lets you compare trades of different sizes, entries and stops on one common scale. A trade that's "+2R" made twice what was risked, whatever the dollar amounts were.
> 
> **In practice:** long BTC at 77,872 with a stop at 76,580 and 0.3862 BTC:
> 
> - stop distance = |77,872 − 76,580| = 1,292
> - 1R = 1,292 × 0.3862 = $498.97
> 
> troid's desk also counts the round-trip fee as part of the risk, since the position still has to be opened and closed whether the stop is hit or not:
> 
> - round-trip fee = entry × 0.04% × 2 × quantity = $24.06
> - 1R with fees = $498.97 + $24.06 = **$523.03**
> 
> The 0.04%-per-side figure is Bitfunded's, from its help centre (Criteria to be Success).
> 
> **What it means for you:** a trade stopped out here loses one R (−$523.03 by troid's count); a trade that closes $1,046.06 ahead is +2R. On a $100,000 account risking a fixed $500 per trade, that's 0.5% of equity per trade, and troid's 1R calculation (with fees) is close to that.
> 
> Sources, each with the date troid read it:
> - fee 0.04% per side (Bitfunded 1-Step) — Bitfunded help centre — Criteria to be Success, read 2026-09-18 and 2026-09-23 and 2026-10-04
> 
> Tier: the figures above are DERIVED — troid's tools computed them from the rules listed.
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
- ✓ retired wording: "no measurable edge", and the reset in UTC, never "noon in New York"
- ✗ every number comes from a tool, the user's message or troid's published figures — ["1,046.06","500","0.5"]
- ✓ every product has a crossover (with equal limits, the quota itself)
- ✓ a firm's loss limit it states as a figure carries its source and read date
- ✓ a teaching answer works its own example; it never asks the user for the numbers
- ✓ troid's published Monte Carlo keeps each figure's risk (68% at 1% a trade, 100% at 2%)
- ✓ an example on a firm's product keeps to its leverage cap (Bitfunded 1:5), or says it
- ✓ troid's tools and defaults are troid's, not a firm's
- ✓ a formula line writes its formula in symbols, with an equals sign
- ✓ opens with the answer, never with a result the reader never saw ("That result …")
- ✓ says: /\brisk/
- ✓ says: /\bstop\b/
- ✓ says: /entry/
- ✓ says: /[=×]/
- ✓ says: /\bR (is|means|stands for|measures)\b/
- ✓ never says: /\bhalf\b[^.\n]{0,40}\bdaily/
- ✓ answers instead of refusing (a question, not a "should I")
- ✓ computes through a tool (trade_math)
- ✓ method: a formula
- ✓ method: a worked example with numbers
- ✓ method: the tier

**Read by a person:** Error (math, sources): 1R = $498.97 right; the fees are the live tools' (both at entry: $24.06, 1R $523.03, where troid's desk, the exit fee at the stop, gives $23.86 and $522.83: the audit's F6); '$1,046.06', '$500' and '0.5%' come from no tool (the $100,000 account risking $500 is the reply's own).

## b-stop — beginner

**Question:** Why does troid need my stop price to size a trade?

**Tools:** trade_math · **model:** claude-sonnet-5 · **22.1 s**

> troid needs the stop because the stop distance is what turns a dollar risk into a position size — without it there's nothing to divide the risk by. The stop, the risk and the trade are the trader's; troid only prices them.
> 
> **Formula:** `quantity = risk / (|entry − stop| + fee_unit)`, where risk is the dollars the trader is risking on the trade and fee_unit is the round-trip fee cost per unit.
> 
> **Why it works:** the dollar amount risked on a trade is set by the trader (say, a percent of equity). That same dollar amount gets divided by however far the stop sits from entry, in price terms, to get how many units (shares, coins, contracts) the position can hold. A wider stop means fewer units for the same dollar risk; a tighter stop means more units — but also a larger fee drag relative to the risk, since fees are charged on notional, not on distance.
> 
> Working an example the trader brought (already computed above, repeated as the tool returned it):
> 
> Long at entry 77,872, stop 76,580, risking $500 on Bitfunded's 1-Step (fee 0.04% per side, from the help centre's Criteria to be Success, read 2026-09-18/23 and 2026-10-04). Stop distance is 1,292 (|77,872 − 76,580|). Fee per unit is 77,872 × 0.04% × 2 = 62.2976. Quantity is 500 ÷ (1,292 + 62.2976) = 0.369195 units. Notional is 0.369195 × 77,872 = $28,749.96, and at 5× leverage the margin posted is $5,749.99.
> 
> **What it means:** change the stop and every one of those numbers changes — quantity, notional, margin, and the fee's share of the risk — because the stop is the one input that converts a fixed dollar risk into an actual number of units. The stop itself, and whether to take the trade at all, stays the trader's call; troid only prices what's brought to it.
> 
> Sources, each with the date troid read it:
> - fee 0.04% per side (Bitfunded 1-Step) — Bitfunded help centre — Criteria to be Success, read 2026-09-18 and 2026-09-23 and 2026-10-04
> 
> Tier: the figures above are DERIVED — troid's tools computed them from the rules listed.
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
- ✓ says: /\bstop\b/
- ✓ says: /\b(quantity|size)\b/
- ✓ says: /[=×÷]/
- ✓ never says: /\b3\.5 times\b/
- ✓ answers instead of refusing (a question, not a "should I")
- ✓ method: a formula
- ✓ method: a worked example with numbers
- ✓ method: the tier

**Read by a person:** Error (math, form): the method is all there (the answer first, the formula, why, the example, what it means, the tier), but the figures are the live tools' F6 ones: fee per unit 62.2976, 0.369195 units, $28,749.96, margin $5,749.99, where the desk gives 61.7808, 0.369336, $28,760.93 and $5,752.19. 'Working an example the trader brought (already computed above, repeated as the tool returned it)' calls troid's example the trader's and points to a computation the reader never saw.

## b-leverage — beginner

**Question:** If I use 10x leverage instead of 2x, do I lose more when my stop is hit?

**Tools:** trade_math, trade_math · **model:** claude-sonnet-5 · **13.1 s**

> No — the loss at the stop is the same whether leverage is 10x or 2x.
> 
> **Formula:** risk (loss at the stop) = |entry − stop| × quantity. Leverage doesn't appear in this at all.
> 
> **Why it works:** leverage only sets how much margin is posted to open a given position size — it determines notional ÷ margin, and where an exchange's own liquidation sits. It does not change the distance between entry and stop, nor the quantity you hold for a given dollar risk.
> 
> Worked example, same position sized two ways:
> 
> With risk fixed at $500, entry 77,872 and stop 76,580 (stop distance 1,292), the quantity is 0.386997 in both cases, notional $30,136.22 in both cases — so the loss when the stop is hit is $500 either way.
> 
> What changes is only the margin posted: $15,068.11 at 2x versus $3,013.62 at 10x. The difference 10x leverage makes is where the position's own margin would be exhausted (isolated margin) or how much of the account's equity it ties up (cross margin) — not the size of the loss at your stop.
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
- ✓ says: /(does not|doesn['’]t|no)\b[^.]{0,60}(change|affect|increase|alter)|\bsame (loss|amount|dollar)/
- ✓ says: /\bmargin\b/
- ✓ never says: /1/leverage\)`?\s*from entry/
- ✓ never says: /distance is roughly entry × \(1/
- ✓ never says: /reference account(?![\s\S]*(5\s?×|1:5|5x\b|five times))/
- ✓ answers instead of refusing (a question, not a "should I")
- ✓ method: a formula
- ✓ method: a worked example with numbers
- ✓ method: the tier

**Read by a person:** Note: correct through trade_math: no, the loss is the same ($500); 0.386997 units, $30,136.22, margin $15,068.11 at 2x and $3,013.62 at 10x; no firm named (no fee). It doesn't say the loss stays the same only while the margin fits in equity (the candidate's F1), which this example never reaches.

## p-crossover — prop-rule

**Question:** What is the crossover on a $100,000 Bitfunded 1-Step, and why does it matter?

**Tools:** explain_rule · **model:** claude-sonnet-5 · **10.0 s**

> The crossover on a $100,000 Bitfunded 1-Step is **$98,000**.
> 
> **Formula:** crossover equity = quota × (1 − max% + daily%)
> 
> Bitfunded's 1-Step has a 6% maximum loss (static floor from the starting quota) and a 4% daily loss limit that is a FIXED amount measured from the initial balance, not from each day's starting balance. The two ceilings trade off at:
> 
> $100,000 × (1 − 0.06 + 0.04) = $100,000 × 0.98 = **$98,000**
> 
> **Why it works:** Bitfunded's daily limit is a fixed dollar amount, always 4% of the original $100,000 ($4,000), while the maximum-loss floor is fixed at $94,000 (6% below the quota). As equity falls, the daily ceiling (quota − $4,000 + today's net P&L) and the max-loss floor ($94,000) move toward each other until, at $98,000 of day-start equity, they coincide. Below $98,000, the $94,000 floor is the binding constraint for the rest of that day's room; above it, the $4,000 daily limit binds first.
> 
> **What it means:** on a $100,000 account, that crossover sits only $2,000 below the starting balance — half of one day's $4,000 loss limit. So for almost the entire life of a fresh account, the advertised 4% daily limit isn't actually what caps a trader once the account has already slipped by a couple thousand dollars; the 6% maximum-loss floor takes over very quickly. Sizing against the daily limit alone, without checking which ceiling is binding that day, understates the real constraint once equity drops near or below $98,000.
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
- ✓ retired wording: "no measurable edge", and the reset in UTC, never "noon in New York"
- ✗ every number comes from a tool, the user's message or troid's published figures — ["4,000","94,000"]
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

**Read by a person:** Error (rule, sources): $98,000, the formula, which limit binds the right way round and 'half of one day's $4,000 loss limit' right; but 'the daily ceiling (quota − $4,000 + today's net P&L)' misstates the daily floor, which is the day's start less $4,000; and $4,000 and $94,000 come from no tool.

## p-assets — prop-rule

**Question:** Bitfunded: can I trade BTC and a stock?

**Tools:** explain_rule · **model:** claude-sonnet-5 · **10.6 s**

> Bitfunded's hold-limit rule (Restricted Trading Practices s.1) sets a tiered hold cap by asset class: crypto "majors" (BTC, ETH, BNB, XRP, SOL, TRX, HYPE, ZEC, DOGE, ADA) 10 days, other crypto 7 days, and TradFi 5 days — and that TradFi tier means the firm's own rules contemplate TradFi instruments (which includes stocks) alongside crypto, so holding both BTC and a stock on the same account is addressed by its hold-limit rule rather than forbidden outright.
> 
> That said, troid has not recorded a document that lists which specific assets or stock symbols Bitfunded actually offers for trading, which account types carry which instruments, or whether both can be held concurrently under the open-position cap (5 open positions, per Restricted Trading Practices s.3) and the concentration ladder. Those are platform/offering questions, not loss-limit arithmetic, and troid's recorded Bitfunded rules don't cover them — source not yet recorded. Confirm the actual tradable symbol list and any same-account restrictions with Bitfunded directly before acting.
> 
> Sources, each with the date troid read it:
> - hold limit: majors 10 days, other crypto 7, TradFi 5 — Bitfunded help centre — Restricted Trading Practices s.1, read 2026-09-21
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
- ✓ says: /\bBTC\b/
- ✗ says: /\bTSLA\b/
- ✓ says: /\b10\b[- ]?(calendar )?days?|\bten days\b|\b10-day/
- ✓ says: /\b5\b[- ]?(calendar )?days?|\bfive days\b|\b5-day/
- ✓ says: /Restricted Trading Practices/
- ✗ says: /2026-09-24|24 Sep(tember)? 2026|September 24,? 2026/
- ✓ never says: /\b(no|doesn['’]t have a|does not have a|hasn['’]t got a) (list|record) of (tickers|symbols|stocks|instruments|assets)\b/
- ✓ never says: /\btroid (has|keeps) no (list|record) of\b/
- ✓ never says: /\b(NVDA|AAPL|GOOGL|MSFT|AMZN)\b[^.\n]{0,60}\b(available|offered|listed|tradable|can trade)\b/
- ✓ never says: /\bBitfunded (doesn['’]t|does not) (offer|list|allow) (stocks|any stock)\b/
- ✓ answers instead of refusing (a question, not a "should I")
- ✗ computes through a tool (firm_assets) — ["explain_rule"]
- ✓ each rule it states carries its document and read date

**Read by a person:** Error (rule, sources): no firm_assets (the live prompt has none). It says 'troid has not recorded a document that lists which specific assets or stock symbols Bitfunded actually offers', where firms.json records BTC (Major Crypto Assets) and TSLA (Traditional Trading Pairs) from Restricted Trading Practices read 2026-09-24: the owner's live-test failure of 2026-10-04. It never names TSLA, and gives '5 open positions, per Restricted Trading Practices s.3' with no read date.

## p-ladder-instant — prop-rule

**Question:** Bitfunded Instant: what happens if 60% of my margin is in one trade?

**Tools:** check_compliance · **model:** claude-sonnet-5 · **9.3 s**

> Putting 60% of margin into a single trade on Bitfunded Instant puts the account on its concentration ladder (Restricted Trading Practices s.2). For Instant, that ladder starts earlier than on the 1-Step/2-Step products:
> 
> - Instant ladder: 55–64% → 50% payout penalty, 65–74% → 55%, 75–89% → 60%, 90–95% → 65%, 96–100% → 70%.
> 
> At 60% of capital in one trade, that lands in the 55–64% band: a **50% payout penalty**, applied at payout review, not an account failure in itself.
> 
> Two other things Bitfunded's Terms prohibit but that can't be checked from a concentration figure alone, and are worth naming here: switching strategies between the assessment account and a funded account (ToU 14(d)(ix)), and holding opposite positions across connected accounts (ToU 13(c)(v)).
> 
> Sources, each with the date troid read it:
> - Bitfunded help centre: Restricted Trading Practices, read 2026-09-21
> - Bitfunded Terms of Use, read 2026-09-21
> - RTP s.2 — Bitfunded help centre: Restricted Trading Practices, read 2026-09-21
> - ToU 14(d)(ix) — Bitfunded Terms of Use (modified 2026-03-24), read 2026-09-23
> - ToU 13(c)(v) — Bitfunded Terms of Use (modified 2026-03-24), read 2026-09-23
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
- ✓ retired wording: "no measurable edge", and the reset in UTC, never "noon in New York"
- ✗ every number comes from a tool, the user's message or troid's published figures — ["64","65","74","75","89","90","96","70"]
- ✓ every product has a crossover (with equal limits, the quota itself)
- ✓ a firm's loss limit it states as a figure carries its source and read date
- ✓ troid's published Monte Carlo keeps each figure's risk (68% at 1% a trade, 100% at 2%)
- ✓ an example on a firm's product keeps to its leverage cap (Bitfunded 1:5), or says it
- ✓ troid's tools and defaults are troid's, not a firm's
- ✓ a formula line writes its formula in symbols, with an equals sign
- ✓ opens with the answer, never with a result the reader never saw ("That result …")
- ✓ says: /\b50\s?% payout penalty\b/
- ✓ says: /\bInstant\b/
- ✓ says: /\b55\s?%/
- ✓ says: /Restricted Trading Practices|Excessive Risk Concentration/
- ✗ says: /2026-10-04|4 Oct(ober)? 2026|October 4,? 2026/
- ✓ never says: /\b(payout|profit|split)\b[^.\n]{0,20}\bcut\b|\bcut\b[^.\n]{0,30}\b(payout|profit|split)\b/
- ✓ never says: /\b(ladder|penalt\w*)\b[^.\n]{0,60}\b(starts?|begins?|from)\b[^.\n]{0,10}\b65\s?%[^.\n]{0,40}\bInstant\b|\bInstant\b[^.\n]{0,60}\b(starts?|begins?|from)\b[^.\n]{0,10}\b65\s?%/
- ✓ never says: /\b60\s?%[^.\n]{0,60}\b(no|isn['’]t|is not|not)\b[^.\n]{0,20}\bpenalt/
- ✓ answers instead of refusing (a question, not a "should I")
- ✓ computes through a tool (firm_rules or check_compliance)
- ✓ each rule it states carries its document and read date

**Read by a person:** Error (sources): the Instant ladder right (55–64% → 50% payout penalty, 60% in the first step), but from the prompt's firm data rather than a tool (check_compliance gave the 50% at 55%), and dated 2026-09-21, the read that recorded one firm-wide ladder; the per-product ladder is the read of 2026-10-04. 'applied at payout review, not an account failure in itself' says more than the firm's words do (as the candidate's 'not a disqualifying one').

## p-size — prop-rule

**Question:** Size a short on a $100,000 Bitfunded 1-Step. Equity and day-start balance are both $96,000, entry 77,872, stop 0.3% above entry, risking 0.5%.

**Tools:** size_trade · **model:** claude-sonnet-5 · **13.3 s**

> ## Verdict: OK
> 
> **Both ceilings**
> 
> | | floor | budget |
> |---|---|---|
> | daily limit | $92,000 (day start − 4%×100,000) | $4,000 |
> | max drawdown | $94,000 (100,000 × (1−6%)) | $2,000 |
> 
> Binding: **max drawdown**, $2,000 — day-start equity ($96,000) sits below the $98,000 crossover (quota × (1 − 6% + 4%)), so the static max-loss floor binds instead of the daily limit.
> 
> **Sizing**
> 
> - Stop: entry × (1 + 0.3%) = 78,105.616 (short, stop above entry)
> - Intended risk: equity × 0.5% = $480
> - Cap: budget × 35% = $700 → risk used = min(480,700) = **$480**
> - Stop distance: |77,872 − 78,105.616| = 233.616
> - Fee per unit: entry × 0.04% × 2 = 62.2976
> - Quantity = 480 ÷ (233.616 + 62.2976) = **1.622095**
> - Notional = 1.622095 × 77,872 = **$126,315.79**
> - Leverage used: 5× (your input/cap) → margin = 126,315.79 ÷ 5 = **$25,263.16**
> - Fees = 1.622095 × 62.2976 = **$101.05**
> - Fee share of risk = 101.05 / 480 ≈ **21.05%** of the risk
> - Budget consumed = 480 / 2,000 = **24%**
> - Losses left before the max-drawdown floor trips (ceil(budget/risk) − 1): **4**
> - 2R target (troid's default): 77,404.77
> 
> **Circuit-breaker order** (distance from entry, adverse move):
> 1. your stop — 0.3%
> 2. max-loss floor — 1.58%
> 3. daily limit — 3.17%
> 4. exchange liquidation, cross margin, 0.5% maintenance-margin assumption — 75.12%
> 
> Margin mode assumed cross (troid's default; no recorded margin-mode source for Bitfunded). Under cross, nothing sits between the daily/max-loss floors and exchange liquidation — the stop is the only breaker ahead of the firm's own floor.
> 
> Sources, each with the date troid read it:
> - daily 4% — Bitfunded help centre — Challenge & Trader Stage, One Step Evaluation table (Stage 1); Terms of Use 9(a), 1 Step Challenges, Objectives, read 2026-09-23
> - daily basis (initial) — Bitfunded FAQ, read 2026-09-21
> - max 6% — Bitfunded help centre — Challenge & Trader Stage, One Step Evaluation table (Stage 1); Terms of Use 9(a), 1 Step Challenges, Objectives, read 2026-09-23
> - drawdown type (static) — Bitfunded help centre — Criteria to be Success (the mechanics: a static floor measured from the account quota), read 2026-09-18
> - fee 0.04% per side — Bitfunded help centre — Criteria to be Success, read 2026-09-18 and 2026-09-23 and 2026-10-04
> - leverage cap 5× — Bitfunded help centre — Challenge & Trader Stage, One Step Evaluation table (Leverage Ratio 1:5); Terms of Use 9(a), 1 Step Challenges (Up To 1:5 Leverage), read 2026-09-23
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
- ✗ says: /(?<![\d.])1\.(?:622|6216|62158|621583|6215830|62158302|621583019|6215830192|62158301918)(?!\d)/
- ✓ says: /max(imum)?[- ](loss|drawdown)[^.]{0,120}bind|bind[^.]{0,80}max(imum)?[- ](loss|drawdown)|static floor[^.]{0,80}bind/
- ✓ never says: /\b75\.88\s?%/
- ✓ answers instead of refusing (a question, not a "should I")
- ✓ computes through a tool (size_trade)
- ✓ each rule it states carries its document and read date
- ✓ method: a formula
- ✓ method: a worked example with numbers
- ✓ method: the tier

**Read by a person:** Error (critical, the user's position): every figure is the live tools' F6 one: 1.622095 units (the desk 1.621583), notional $126,315.79 ($126,275.91), margin $25,263.16 ($25,255.18), fees $101.05 and 21.05% ($101.17, 21.08%), cross liquidation 75.12% (75.15%). The owner's line of 30 Sep: the live baseline fails p-size unless a reply rounds to 1.622. The two budgets, the binding $2,000, $480 and 4 losses left are right. 'Leverage used: 5× (your input/cap)' calls troid's default the user's input.

## o-montecarlo — out-of-scope

**Question:** Can you run a Monte Carlo simulation of my strategy? 55% win rate, 1.2R average win, 1% risk per trade, 100 trades.

**Tools:** trade_math · **model:** claude-sonnet-5 · **16.7 s**

> troid doesn't run simulations, with any inputs — not even hypothetical ones like this. No Monte Carlo of a 55% win rate, 1.2R average win, 1% risk, 100 trades is computed here.
> 
> What troid can give instead:
> 
> 1. **Expectancy for this exact setup** — closed-form, through trade_math. Let's compute it.
> 2. **Published Monte Carlo results** troid already ran (MODELLED, with stated assumptions) — not for these exact inputs, but for naive fixed-fraction sizing against a prop firm's loss limits, which can be stated beside this one's arithmetic.
> 
> Let's get the exact-form expectancy first.
> 
> **Answer first:** expectancy is +0.21R per trade (DERIVED), for an expected total of +21R over 100 trades — but that's a mean across many hypothetical runs, not a prediction of what one run of 100 trades does. troid doesn't simulate the variance around it.
> 
> **Formula:** `E = p·W − (1−p)·L`, where p is win rate, W is average win in R, L is average loss in R.
> 
> **Why it works:** expectancy is the long-run average outcome per trade; it says nothing about the path or the worst drawdown along the way, which is what a Monte Carlo would show — and troid doesn't run one.
> 
> **Worked example (yours):** p = 0.55, W = 1.2, L = 1 → E = 0.55×1.2 − 0.45×1 = 0.66 − 0.45 = 0.21R per trade. Break-even win rate at this payoff ratio (1.2) is 1 ÷ (1.2+1) = 45.45% — your 55% is above it. Over 100 trades the mean total is 100 × 0.21 = 21R.
> 
> **What it means:** at 1% risk per trade, 21R of expectancy corresponds to a mean total of about 21% of the starting equity over 100 trades — but that number says nothing about sequencing or ruin risk, which no tool here computes for your exact inputs. The closest thing troid can show is its own published, MODELLED Monte Carlo on fixed-fractional sizing against a specific firm's loss limits (different win rate/payoff assumptions) — say the word and troid will pull that up with its stated assumptions, clearly separated from this calculation.
> 
> Tier: the figures above are DERIVED — troid's tools computed them from the numbers given; no firm rule was needed.
> 
> Not financial advice. Verify with the firm before acting.

- ✓ answered by the live prompt
- ✗ troid never says "I" (third person only) — ["Let's","Let's"]
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
- ✗ names none of troid's own instructions and announces no form ("support.md section 4", "result first, one line") — "Answer first"
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
- ✓ says: /(does not|doesn['’]t|cannot|can['’]t|won['’]t|never) (run|runs|simulate)/
- ✓ says: /0\.21/
- ✓ never says: /(troid|ask troid) (can|could|will|would) (run|simulate)|to run (your|the|a|this) (monte carlo )?simulation|would need to run/
- ✓ never says: /of the risk unit|0\.21\s?% of/
- ✓ never says: /\bnumpy\b|you['’]d (use|need) a tool like/
- ✓ never says: /outcome is p\s?[·×*]\s?W/

**Read by a person:** Error (critical, first person): no simulation, 0.21R, 21R and 45.45% right; but 'Let's compute it' and 'Let's get the exact-form expectancy first' (first person), the lead-in to the tool call left above the answer, 'Answer first:' (the method's own words) and 'through trade_math' (a tool named).
