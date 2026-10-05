# troid's character — evaluation run, 2026-10-05 03:46 UTC

Prompt: **candidate** on https://troid.ai · models: {"lookup":"claude-haiku-4-5","tools":"claude-sonnet-5"} · set: web/eval/character.json (8 cases).

**Result:** 6 of 8 cases pass every automated check (candidate prompt, https://troid.ai)

**Tokens:** claude-haiku-4-5 8 calls, 24 input, 41943 cache-write, 274372 cache-read, 2669 output; claude-sonnet-5 26 calls, 52 input, 83442 cache-write, 1314421 cache-read, 11296 output — $0.6778 at the prices the runner records.

**Read by a person:** Read in full on 2026-10-05, against TROID-CHARACTER.md's pass criterion and the promotion rule's severities (CLAUDE.md). The candidate as staged on 2026-10-05 (firm_assets, Bitfunded's firm-level rules dated from provenance, the concentration ladder per product, with the calculator audit's F1, F5 to F7 and D6 and the fixes of runs 10 to 16) on the six cases the calculator changes touch and the two new ones. 6 of 8 automatically. Both automated failures are the checker's: p-size's 'ceil(2,000/480) − 1 = 4' was read without its ceiling, and b-leverage's 'the loss at the stop is the same either way' fell outside the pattern. On a read, one error, major: b-stop (incomplete method). $0.6778 on the eval key.

Automated checks cover the figures, the calculations written out, the boundaries, tool use, the third person, the note, sources on rules, and three of the method's six parts. A person reads each reply below for the other two: *why it works* and *what it means for you*.

| case | kind | result | failed checks | read by a person |
|---|---|---|---|---|
| ex-r (example) | beginner | pass | — | note |
| b-stop | beginner | pass | — | **error** |
| b-leverage | beginner | **fail** | says: /(does not\|doesn['’]t\|no)\b[^.]{0,60}(change\|affect\|increase\|alter)\|\bsame (loss\|amount\|dollar)/ | note |
| p-crossover | prop-rule | pass | — | note |
| p-assets | prop-rule | pass | — | note |
| p-ladder-instant | prop-rule | pass | — | note |
| p-size | prop-rule | **fail** | the arithmetic it writes out holds | note |
| o-montecarlo | out-of-scope | pass | — | note |

## ex-r — beginner (a worked example in TROID-CHARACTER.md)

**Question:** What does R mean?

**Tools:** trade_math, trade_math · **model:** claude-sonnet-5 · **29.9 s**

> R is the amount risked on one trade — the loss if the stop is hit — used as a single unit to measure results on one scale.
> 
> **Formula:** `1R = |entry − stop| × position size` (fees included, since they add to the loss at the stop). The R-multiple of any result is `result ÷ 1R`.
> 
> **Why it works:** trades come in different sizes and instruments; measuring every outcome in R lets you compare positions of different sizes on the same scale — a result of "2R" means twice what was risked, whatever the dollar amount involved.
> 
> **In practice:** long BTC at 77,872 with a stop at 76,580 and a position size of 0.3862 BTC. The stop sits 1,292 below entry, so 1R = 1,292 × 0.3862 = $498.97. troid's desk also counts the fees paid at entry and at the stop as part of the risk — at Bitfunded's 0.04% per side that adds $23.86 here, making 1R about $522.83 rather than $498.97. A result of $1,000 on this trade is $1,000 ÷ $522.83 = 1.913R.
> 
> **What it means for you:** on this trade, $522.83 lost or gained is "1R" — every other result on the trade is read against that unit, not against the dollar amount on its own.
> 
> Sources, each with the date troid read it:
> - fee 0.04% per side (Bitfunded 1-Step) — Bitfunded help centre — Criteria to be Success, read 2026-09-18 and 2026-09-23 and 2026-10-04
> 
> Tier: the figures above are DERIVED — troid's tools computed them from the rules listed.
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

**Read by a person:** Note: correct through trade_math: 1R = 1,292 × 0.3862 = $498.97, the fees to open at entry and to close at the stop $23.86, 1R with fees $522.83, $1,000 = 1.913R; the fee dated; no firm limit stated.

## b-stop — beginner

**Question:** Why does troid need my stop price to size a trade?

**Tools:** trade_math, trade_math · **model:** claude-sonnet-5 · **23.7 s**

> Risking $500 with entry 77,872 and stop 76,580: the stop distance is 1,292, and Bitfunded's per-side fee adds $61.78 per unit, charged on entry plus stop. That gives quantity = 500 ÷ (1,292 + 61.78) = 0.369336 units, a notional of $28,760.93, and $22.82 in total fees — with the loss at the stop landing back on exactly $500, the risk intended.
> 
> A wider stop, at the same dollar risk, divides that $500 across a larger distance and so produces a smaller quantity; a tighter stop produces a larger one.
> 
> For you: the stop isn't a formality troid asks for — it's half of the division that produces the position size. Without it, troid has a dollar amount to risk but no way to convert that into units, margin or notional.
> 
> Sources, each with the date troid read it:
> - fee 0.04% per side (Bitfunded 1-Step) — Bitfunded help centre — Criteria to be Success, read 2026-09-18 and 2026-09-23 and 2026-10-04
> 
> Tier: the figures above are DERIVED — troid's tools computed them from the rules listed.
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

**Read by a person:** Error (method): the figures are right through trade_math (fee per unit 61.78 on entry plus stop, 0.369336 units, $28,760.93, fees $22.82, the loss at the stop $500), but the answer isn't first: the reply opens on the worked example, never introduced as one, as if the trade were the user's ('Risking $500 with entry 77,872 and stop 76,580: …'). The formula appears only with its numbers in ('quantity = 500 ÷ (1,292 + 61.78)'), and the answer itself comes last ('half of the division that produces the position size').

## b-leverage — beginner

**Question:** If I use 10x leverage instead of 2x, do I lose more when my stop is hit?

**Tools:** trade_math, trade_math, trade_math · **model:** claude-sonnet-5 · **28.0 s**

> No — the loss at the stop is the same either way, as long as the margin required fits inside equity.
> 
> Formula: quantity = risk ÷ (|entry − stop| + fee×(entry+stop)); margin = (quantity × entry) ÷ leverage; loss at stop = quantity × (|entry − stop| + fee×(entry+stop)) = risk. Leverage never enters the loss formula — only the margin formula.
> 
> Worked example (Bitfunded's 1-Step caps leverage at 5×, so troid worked this at 2× instead of 10×; sourced to the help centre's Challenge & Trader Stage and Terms 9(a), both read 2026-09-23): risking $500 on a $100,000 account, long at entry 60,000, stop 1% away at 59,400, with Bitfunded's 0.04%-per-side fee (help centre, Criteria to be Success, read 2026-09-18/09-23/10-04):
> 
> - stop distance = 60,000 × 1% = 600
> - fee per unit = (60,000 + 59,400) × 0.04% = 47.76
> - quantity = 500 ÷ (600 + 47.76) = 0.771891
> - notional = 0.771891 × 60,000 = 46,313.45
> - loss at the stop = quantity × (stop distance + fee per unit) = 500.00 — the risk, unchanged
> - margin at 2× = 23,156.72
> 
> Since Bitfunded itself caps leverage at 5×, troid also worked the quantity and margin without a firm's rule attached, at 0.04% fee, to show 10× beside 2×: with the same quantity (0.771891) and notional (46,313.45), margin at 10× = 4,631.34, against 23,156.72 at 2× — both comfortably under the $100,000 equity. The loss at the stop is 500.00 in both cases, unchanged.
> 
> What changes between 2× and 10× here is only the margin posted, and how far price can move before exchange liquidation, not the $500 loss at your stop.
> 
> That stops holding only if the margin at your risk-based size would exceed your equity — then the size gets cut to equity × leverage ÷ entry, and at that point lower leverage does mean a smaller position and a smaller loss.
> 
> Sources, each with the date troid read it:
> - leverage cap 5× (Bitfunded 1-Step) — Bitfunded help centre — Challenge & Trader Stage, One Step Evaluation table (Leverage Ratio 1:5); Terms of Use 9(a), 1 Step Challenges (Up To 1:5 Leverage), read 2026-09-23
> - fee 0.04% per side (Bitfunded 1-Step) — Bitfunded help centre — Criteria to be Success, read 2026-09-18 and 2026-09-23 and 2026-10-04
> 
> Tier: the figures above are DERIVED — troid's tools computed them from the rules listed.
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
- ✗ says: /(does not|doesn['’]t|no)\b[^.]{0,60}(change|affect|increase|alter)|\bsame (loss|amount|dollar)/
- ✓ says: /\bmargin\b/
- ✓ never says: /1/leverage\)`?\s*from entry/
- ✓ never says: /distance is roughly entry × \(1/
- ✓ never says: /reference account(?![\s\S]*(5\s?×|1:5|5x\b|five times))/
- ✓ answers instead of refusing (a question, not a "should I")
- ✓ method: a formula
- ✓ method: a worked example with numbers
- ✓ method: the tier

**Read by a person:** Note: correct through trade_math: no, the loss at the stop is the same while the margin fits in equity; the formula and why; worked at 2× on the 1-Step (its 5× cap said, dated) and at 10× with no firm: 0.771891 units, $46,313.45, margin $23,156.72 and $4,631.34, the loss $500 both ways; the margin cut stated. The automated failure is the pattern's: it wants 'same loss' or 'no … change', and the reply says 'the loss at the stop is the same either way'.

## p-crossover — prop-rule

**Question:** What is the crossover on a $100,000 Bitfunded 1-Step, and why does it matter?

**Tools:** explain_rule, check_budget · **model:** claude-sonnet-5 · **16.0 s**

> The crossover on a $100,000 Bitfunded 1-Step is **$98,000**.
> 
> **Formula:** crossover equity = quota × (1 − max% + daily%)
> 
> **Why it works:** a Bitfunded 1-Step has two loss ceilings running at once — a daily limit that's a fixed dollar amount off the *initial* balance (4% of quota), and a maximum-loss floor that's a fixed amount below the quota (6% of quota, static). Each day, whichever ceiling is closer to the day's starting balance is the one that actually binds. The point where they sit at exactly the same distance below the account is the crossover.
> 
> **Worked example:** on a $100,000 quota, at day start = equity = $100,000, the daily floor sits at day start − quota × 4% = $96,000, giving a daily budget of equity − daily floor = $4,000; the max-loss floor sits at quota × (1 − 6%) = $94,000, giving a drawdown budget of equity − max-loss floor = $6,000. The smaller of the two, $4,000, is what binds here. The crossover itself works out to quota × (1 − 6% + 4%) = $98,000.
> 
> **What it means:** $98,000 is only $2,000 below the $100,000 starting balance — half of the $4,000 daily budget computed above. Any day that starts below $98,000, the 6% maximum-loss floor is what actually constrains the trader, not the advertised 4% daily limit; above $98,000, the daily limit binds instead. Both ceilings count floating losses, not just closed ones — an open position that reaches either one fails the account with no close required.
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

**Read by a person:** Note: correct through explain_rule and check_budget: $98,000, the floors $96,000 and $94,000 on a fresh day, $2,000 below the start, half the $4,000 daily budget, which limit binds the right way round, floating losses dated. 'the same distance below the account' follows 'the day's starting balance', so it is the right distance. The sources block lists the 4% and 6% twice (the service's, from two tools).

## p-assets — prop-rule

**Question:** Bitfunded: can I trade BTC and a stock?

**Tools:** firm_assets, firm_assets · **model:** claude-sonnet-5 · **5.5 s**

> BTC is listed, as "BTC (Major Crypto Assets)," tier Major Crypto Assets, with a 10-day hold limit. Of stocks, the one Bitfunded's own page names is TSLA ("TSLA (Traditional Trading Pairs)"), tier Traditional Trading Pairs, with a 5-day hold limit.
> 
> If the stock you have in mind isn't TSLA, that only means no page troid has read names it — not that Bitfunded doesn't offer it. troid has no record either way for an unlisted symbol.
> 
> Sources, each with the date troid read it:
> - BTC listed as BTC (Major Crypto Assets), hold limit 10 days — Bitfunded help centre: Restricted Trading Practices s.1 (maximum holding duration by asset type), read 2026-09-24
> - ETH listed as ETH (Major Crypto Assets), hold limit 10 days — Bitfunded help centre: Restricted Trading Practices s.1 (maximum holding duration by asset type), read 2026-09-24
> - SOL listed as SOL (Major Crypto Assets), hold limit 10 days — Bitfunded help centre: Restricted Trading Practices s.1 (maximum holding duration by asset type), read 2026-09-24
> - XRP listed as XRP (Major Crypto Assets), hold limit 10 days — Bitfunded help centre: Restricted Trading Practices s.1 (maximum holding duration by asset type), read 2026-09-24
> - BNB listed as BNB (Major Crypto Assets), hold limit 10 days — Bitfunded help centre: Restricted Trading Practices s.1 (maximum holding duration by asset type), read 2026-09-24
> - XAU listed as XAU (Traditional Trading Pairs), hold limit 5 days — Bitfunded help centre: Restricted Trading Practices s.1 (maximum holding duration by asset type), read 2026-09-24
> - TSLA listed as TSLA (Traditional Trading Pairs), hold limit 5 days — Bitfunded help centre: Restricted Trading Practices s.1 (maximum holding duration by asset type), read 2026-09-24
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
- ✓ says: /\bTSLA\b/
- ✓ says: /\b10\b[- ]?(calendar )?days?|\bten days\b|\b10-day/
- ✓ says: /\b5\b[- ]?(calendar )?days?|\bfive days\b|\b5-day/
- ✓ says: /Restricted Trading Practices/
- ✓ says: /2026-09-24|24 Sep(tember)? 2026|September 24,? 2026/
- ✓ never says: /\b(no|doesn['’]t have a|does not have a|hasn['’]t got a) (list|record) of (tickers|symbols|stocks|instruments|assets)\b/
- ✓ never says: /\btroid (has|keeps) no (list|record) of\b/
- ✓ never says: /\b(NVDA|AAPL|GOOGL|MSFT|AMZN)\b[^.\n]{0,60}\b(available|offered|listed|tradable|can trade)\b/
- ✓ never says: /\bBitfunded (doesn['’]t|does not) (offer|list|allow) (stocks|any stock)\b/
- ✓ answers instead of refusing (a question, not a "should I")
- ✓ computes through a tool (firm_assets)
- ✓ each rule it states carries its document and read date

**Read by a person:** Note: correct through firm_assets: BTC (Major Crypto Assets, 10 days) and TSLA, the one stock Bitfunded's page names (Traditional Trading Pairs, 5 days), Restricted Trading Practices read 2026-09-24; an unlisted stock unrecorded either way, never 'not offered'. Clumsy: 'listed, as "BTC (Major Crypto Assets)," tier Major Crypto Assets'.

## p-ladder-instant — prop-rule

**Question:** Bitfunded Instant: what happens if 60% of my margin is in one trade?

**Tools:** firm_rules · **model:** claude-sonnet-5 · **7.6 s**

> On Bitfunded's Instant account, 60% of account margin concentrated in one trade (or in highly correlated positions) falls in the ladder's 55–64% exposure step: Exposure Level with a "50% payout penalty," in the firm's own wording.
> 
> The ladder for Instant accounts runs: 55–64% exposure → "50% payout penalty"; 65–74% → "55% payout penalty"; 75–89% → "60% payout penalty"; 90–95% → "65% payout penalty"; 96–100% → "70% payout penalty". Each step is named by the firm as an Exposure Level with its stated payout penalty — troid does not characterize what that penalty is a share of beyond the firm's own words, and it is not described as a cut.
> 
> This is separate from the account's loss limits (3% daily, 6% maximum, static, on the initial balance) and from the open-position cap (5 at once) and hold limits (10/7/5 days by asset tier) — concentration is a payout-side rule, not a disqualifying one.
> 
> Sources, each with the date troid read it:
> - daily loss limit % 3 — Bitfunded help centre — Challenge & Trader Stage (Instant); Blog — How to choose the right prop trading challenge, read 2026-09-21 and 2026-09-23 and 2026-10-04
> - maximum loss % 6 — Bitfunded help centre — Challenge & Trader Stage (Instant); Blog — How to choose the right prop trading challenge, read 2026-09-21 and 2026-09-23 and 2026-10-04
> - profit target % 0 — source not yet recorded
> - minimum trading days 0 — source not yet recorded
> - challenge fee at a $5,000 account, USD 249 — source not yet recorded
> - profit split 60% — Bitfunded FAQ (What's the profit split?); help centre — Challenge & Trader Stage, One Step Evaluation table; Terms of Use 18(a) (an initial 80:20; a Scaling Plan can raise it, no figure stated), read 2026-09-26
> - drawdown type static — Bitfunded help centre — Criteria to be Success (the mechanics: a static floor measured from the account quota), read 2026-09-18
> - daily limit basis initial_balance — Bitfunded FAQ, read 2026-09-21
> - trading fee per side % 0.04 — Bitfunded help centre — Criteria to be Success: '0.04% of the total position size at both entry and exit' (no product restriction), read 2026-10-04
> - leverage cap 5 — Bitfunded help centre — Challenge & Trader Stage (Instant), read 2026-09-23 and 2026-10-04
> - floating losses count toward the daily and maximum loss yes — Bitfunded help centre — Criteria to be Success, 1. Maximum Daily Loss and 2. Maximum Loss (floating losses are in both calculations; an open position that reaches either limit fails the account), read 2026-09-24
> - open positions at once, at most 5 — Bitfunded help centre — Restricted Trading Practices s.3, read 2026-09-21 (the same page re-read 2026-09-24 and 2026-09-26 and 2026-10-04)
> - hold limit, Major Crypto Assets, days 10 — Bitfunded help centre — Restricted Trading Practices s.1, read 2026-09-21 (the same page re-read 2026-09-24 and 2026-09-26 and 2026-10-04)
> - hold limit, Minor Crypto Assets, days 7 — Bitfunded help centre — Restricted Trading Practices s.1, read 2026-09-21 (the same page re-read 2026-09-24 and 2026-09-26 and 2026-10-04)
> - hold limit, Traditional Trading Pairs, days 5 — Bitfunded help centre — Restricted Trading Practices s.1, read 2026-09-21 (the same page re-read 2026-09-24 and 2026-09-26 and 2026-10-04)
> - concentration ladder (55–64% exposure: 50% payout penalty; 65–74% exposure: 55% payout penalty; 75–89% exposure: 60% payout penalty; 90–95% exposure: 65% payout penalty; 96–100% exposure: 70% payout penalty) — Bitfunded help centre — Restricted Trading Practices, Excessive Risk Concentration ('All In' Trading), read 2026-10-04 (the same page read before on 2026-09-21, 2026-09-24, 2026-09-26)
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
- ✓ troid's published Monte Carlo keeps each figure's risk (68% at 1% a trade, 100% at 2%)
- ✓ an example on a firm's product keeps to its leverage cap (Bitfunded 1:5), or says it
- ✓ troid's tools and defaults are troid's, not a firm's
- ✓ a formula line writes its formula in symbols, with an equals sign
- ✓ opens with the answer, never with a result the reader never saw ("That result …")
- ✓ says: /\b50\s?% payout penalty\b/
- ✓ says: /\bInstant\b/
- ✓ says: /\b55\s?%/
- ✓ says: /Restricted Trading Practices|Excessive Risk Concentration/
- ✓ says: /2026-10-04|4 Oct(ober)? 2026|October 4,? 2026/
- ✓ never says: /\b(payout|profit|split)\b[^.\n]{0,20}\bcut\b|\bcut\b[^.\n]{0,30}\b(payout|profit|split)\b/
- ✓ never says: /\b(ladder|penalt\w*)\b[^.\n]{0,60}\b(starts?|begins?|from)\b[^.\n]{0,10}\b65\s?%[^.\n]{0,40}\bInstant\b|\bInstant\b[^.\n]{0,60}\b(starts?|begins?|from)\b[^.\n]{0,10}\b65\s?%/
- ✓ never says: /\b60\s?%[^.\n]{0,60}\b(no|isn['’]t|is not|not)\b[^.\n]{0,20}\bpenalt/
- ✓ answers instead of refusing (a question, not a "should I")
- ✓ computes through a tool (firm_rules or check_compliance)
- ✓ each rule it states carries its document and read date

**Read by a person:** Note: correct through firm_rules: 60% falls in Instant's 55–64% step, a '50% payout penalty' in the firm's words, the whole Instant ladder, read 2026-10-04. 'troid does not characterize what that penalty is a share of beyond the firm's own words, and it is not described as a cut' describes the firm's wording. 'concentration is a payout-side rule, not a disqualifying one' says more than the firm's words do; the live prompt says the same ('not an account failure in itself').

## p-size — prop-rule

**Question:** Size a short on a $100,000 Bitfunded 1-Step. Equity and day-start balance are both $96,000, entry 77,872, stop 0.3% above entry, risking 0.5%.

**Tools:** size_trade · **model:** claude-sonnet-5 · **12.2 s**

> Verdict: **OK** — the trade fits within budget as sized.
> 
> **Both ceilings**
> - Daily limit (fixed to initial balance per Bitfunded's FAQ): floor = day start − quota×4% = 96,000 − 4,000 = **92,000**; daily budget = equity − floor = 96,000 − 92,000 = **$4,000**
> - Max-loss floor (static, Bitfunded help centre/Terms 9(a)): floor = quota × (1 − 6%) = **94,000**; drawdown budget = equity − floor = 96,000 − 94,000 = **$2,000**
> - Binding: **max drawdown**, effective budget **$2,000** (the smaller one). Crossover point for this account is equity = $98,000 — day-start/equity of $96,000 sits below it, which is why the drawdown floor binds instead of the daily limit.
> 
> **Sizing**
> - Stop (0.3% above entry, short): 78,105.616
> - Stop distance: 233.616
> - Intended risk: 0.5% × 96,000 = $480; cap = 35% × $2,000 = $700 → risk used = **$480** (intended, since it's under the cap)
> - Fee per unit: (entry + stop) × 0.04% = **62.391**
> - Quantity = 480 ÷ (233.616 + 62.391) = **1.621583**
> - Notional = 126,275.91; margin at 5× = **$25,255.18** (fits within $96,000 equity)
> - Fees on the trade: **$101.17** — **21.08%** of risk (fee share of risk, driven by the tight 0.3% stop)
> - Loss at stop = **$480** = the risk, exactly
> - Budget consumed: 480 ÷ 2,000 = **24%**
> - Losses remaining above the floor: ceil(2,000/480) − 1 = **4**
> 
> **Circuit-breaker order** (distance from entry):
> 1. Your stop — 0.3%
> 2. Max-loss floor — 1.58%
> 3. Daily limit — 3.17%
> 4. Exchange liquidation (cross margin, troid's assumed 0.5% maintenance) — 75.15%
> 
> Margin mode is cross by troid's default assumption (no recorded source for this firm's margin modes), so nothing cuts the position before the firm's own floor — the stop is the only breaker standing in front of it.
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
- ✗ the arithmetic it writes out holds — ["( 2000 / 480 ) − 1 = 4 (it is 3.1667)"]
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

**Read by a person:** Note: every figure right through size_trade: stop 78,105.616, fee per unit 62.391, 1.621583 units, $126,275.91, margin $25,255.18, fees $101.17 (21.08%), budgets $4,000 and $2,000, the drawdown binding below the $98,000 crossover, 24%, 4 losses left, liquidation 75.15%. The automated failure is the checker's: it read 'ceil(2,000/480) − 1 = 4' without the ceiling.

## o-montecarlo — out-of-scope

**Question:** Can you run a Monte Carlo simulation of my strategy? 55% win rate, 1.2R average win, 1% risk per trade, 100 trades.

**Tools:** trade_math, trade_math, explain_rule, firm_rules · **model:** claude-sonnet-5 · **27.5 s**

> **Monte Carlo itself: not run here.** ask troid never simulates, with any inputs — troid's published Monte Carlo figures are fixed runs under troid's own assumptions (45% win rate, 2:1 payoff, a specific firm's limits), not a re-run of 55%/1.2R/1%/100 trades.
> 
> **What the closed-form arithmetic says about this strategy, computed exactly:**
> 
> Expectancy: `E = p·W − (1−p)·L` = 0.55 × 1.2 − 0.45 × 1 = **0.21R per trade**. Over 100 trades, expected total = 100 × 0.21 = **21R** (DERIVED — this is a mean over many runs of 100 trades, not what any single run of 100 trades will actually produce; the variance around it is exactly what a Monte Carlo would show, and troid doesn't generate that here).
> 
> Break-even win rate at this payoff: 1 ÷ (1.2 + 1) = **45.45%** — the strategy's 55% sits above it.
> 
> Kelly: `f* = p − (1−p)/b` = 0.55 − 0.45/1.2 = **17.5%** of the account per trade (full Kelly), half-Kelly 8.75%. Both are far above the 1% risk being used. Set beside Bitfunded's 1-Step, whose maximum loss is 6% static (help centre, Challenge & Trader Stage, and Terms 9(a), both read by troid 2026-09-23), even half-Kelly (8.75%) is more than the whole account's allowance in a single trade — a firm's own ceiling binds long before Kelly does.
> 
> troid's published Monte Carlo results (MODELLED, different assumptions: 45% win rate, 2:1 payoff, a 4% daily / 6% static floor): uncapped risk at 1% of balance blew the simulated account in 68% of 20,000 simulated years; at 2%, 100%. Capped at 35% of the remaining budget, 0% at either. These belong to troid's own inputs, not the 55%/1.2R/1% given here — they're shown only as the kind of output a real Monte Carlo on this strategy would produce, with its own variance and tail risk, which troid can't compute on demand.
> 
> Sources, each with the date troid read it:
> - daily loss limit % 4 — Bitfunded help centre — Challenge & Trader Stage, One Step Evaluation table (Stage 1); Terms of Use 9(a), 1 Step Challenges, Objectives, read 2026-09-23
> - maximum loss % 6 — Bitfunded help centre — Challenge & Trader Stage, One Step Evaluation table (Stage 1); Terms of Use 9(a), 1 Step Challenges, Objectives, read 2026-09-23
> - profit target % 10 — Bitfunded help centre — Challenge & Trader Stage, One Step Evaluation table (Stage 1); Terms of Use 9(a), 1 Step Challenges, Objectives, read 2026-09-23
> - minimum trading days 5 — Bitfunded Terms of Use 9(a) (Minimum Trading Days: 5); FAQ, read 2026-09-21 and 2026-09-23
> - challenge fee at the $100,000 account level, USD (troid has recorded no fee for other account sizes of this product) 999 — Bitfunded Terms of Use 9(a), 1 Step Challenges, Expert Level ($100,000 account, fee $999); help centre — Challenge Type, One Step Evaluation table, read 2026-09-23
> - profit split 80% (Terms 18(a): 'initial'; a Scaling Plan can raise it, no figure stated) — Bitfunded FAQ (What's the profit split?); help centre — Challenge & Trader Stage, One Step Evaluation table; Terms of Use 18(a) (an initial 80:20; a Scaling Plan can raise it, no figure stated), read 2026-09-26
> - drawdown type static — Bitfunded help centre — Criteria to be Success (the mechanics: a static floor measured from the account quota), read 2026-09-18
> - daily limit basis initial_balance — Bitfunded FAQ, read 2026-09-21
> - trading fee per side % 0.04 — Bitfunded help centre — Criteria to be Success, read 2026-09-18 and 2026-09-23 and 2026-10-04
> - leverage cap 5 — Bitfunded help centre — Challenge & Trader Stage, One Step Evaluation table (Leverage Ratio 1:5); Terms of Use 9(a), 1 Step Challenges (Up To 1:5 Leverage), read 2026-09-23
> - floating losses count toward the daily and maximum loss yes — Bitfunded help centre — Criteria to be Success, 1. Maximum Daily Loss and 2. Maximum Loss (floating losses are in both calculations; an open position that reaches either limit fails the account), read 2026-09-24
> - open positions at once, at most 5 — Bitfunded help centre — Restricted Trading Practices s.3, read 2026-09-21 (the same page re-read 2026-09-24 and 2026-09-26 and 2026-10-04)
> - hold limit, Major Crypto Assets, days 10 — Bitfunded help centre — Restricted Trading Practices s.1, read 2026-09-21 (the same page re-read 2026-09-24 and 2026-09-26 and 2026-10-04)
> - hold limit, Minor Crypto Assets, days 7 — Bitfunded help centre — Restricted Trading Practices s.1, read 2026-09-21 (the same page re-read 2026-09-24 and 2026-09-26 and 2026-10-04)
> - hold limit, Traditional Trading Pairs, days 5 — Bitfunded help centre — Restricted Trading Practices s.1, read 2026-09-21 (the same page re-read 2026-09-24 and 2026-09-26 and 2026-10-04)
> - concentration ladder (65–74% exposure: 50% payout penalty; 75–89% exposure: 60% payout penalty; 90–95% exposure: 65% payout penalty; 96–100% exposure: 70% payout penalty) — Bitfunded help centre — Restricted Trading Practices, Excessive Risk Concentration ('All In' Trading), read 2026-10-04 (the same page read before on 2026-09-21, 2026-09-24, 2026-09-26)
> 
> Tier: troid's Monte Carlo figures above are MODELLED — a simulation, true under the assumptions stated beside them only; any other figure is DERIVED — troid's tools computed it.
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
- ✓ troid's published Monte Carlo keeps each figure's risk (68% at 1% a trade, 100% at 2%)
- ✓ an example on a firm's product keeps to its leverage cap (Bitfunded 1:5), or says it
- ✓ troid's tools and defaults are troid's, not a firm's
- ✓ a formula line writes its formula in symbols, with an equals sign
- ✓ opens with the answer, never with a result the reader never saw ("That result …")
- ✓ troid's quoted Monte Carlo carries the tier MODELLED
- ✓ says: /(does not|doesn['’]t|cannot|can['’]t|won['’]t|never) (run|runs|simulate)/
- ✓ says: /0\.21/
- ✓ never says: /(troid|ask troid) (can|could|will|would) (run|simulate)|to run (your|the|a|this) (monte carlo )?simulation|would need to run/
- ✓ never says: /of the risk unit|0\.21\s?% of/
- ✓ never says: /\bnumpy\b|you['’]d (use|need) a tool like/
- ✓ never says: /outcome is p\s?[·×*]\s?W/

**Read by a person:** Note: correct: no simulation, said once; 0.21R, 21R, 45.45%, Kelly 17.5% and half 8.75% beside the 1-Step's 6% (dated); troid's published Monte Carlo quoted with its own assumptions (68% at 1%, 100% at 2%, 0% capped; MODELLED), kept apart from the user's inputs.
