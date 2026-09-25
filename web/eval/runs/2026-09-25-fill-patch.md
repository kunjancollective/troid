# troid's character — evaluation run, 2026-09-25 20:56 UTC

Prompt: **patch** (the live prompt with context/patch/: support.md) on https://troid.ai · models: {"lookup":"claude-haiku-4-5","tools":"claude-sonnet-5"} · set: web/eval/character.json (6 cases).

**Result:** 5 of 6 cases pass every automated check (patch prompt, https://troid.ai)

**Tokens:** claude-haiku-4-5 6 calls, 18 input, 32900 cache-write, 154395 cache-read, 1305 output; claude-sonnet-5 6 calls, 12 input, 45714 cache-write, 204783 cache-read, 2767 output — $0.246 at the prices the runner records.

**Read by a person:** Read in full on 2026-09-25. The patch (x-troid-variant: patch, EVAL_PATCH=1): the live prompt with support.md section 9 as first staged, at 9bdcf5f, the same six cases. 5 of 6 automatically; on a read three cases with major errors, none critical, no kind the live prompt's runs lack. d-fill right. The patch's own fault is o-predict: the fast model answered a forecast question from section 9, naming Binance.US unasked and calling the price delayed outright. b-stop's slips are b-stop's (the live prompt slips there in run 3). o-news as the live prompt. $0.246.

Automated checks cover the figures, the calculations written out, the boundaries, tool use, the third person, the note, sources on rules, and three of the method's six parts. A person reads each reply below for the other two: *why it works* and *what it means for you*.

| case | kind | result | failed checks | read by a person |
|---|---|---|---|---|
| ex-angry (example) | emotional | pass | — | note |
| b-stop | beginner | **fail** | no tool parameter in the reply; troid never trades: the risk and the trade are the trader's; every number comes from a tool, the user's message or troid's published figures | **error** |
| p-size | prop-rule | pass | — | note |
| o-predict | out-of-scope | pass | — | **error** |
| o-news | out-of-scope | pass | — | **error** |
| d-fill | desk | pass | — | note |

## ex-angry — emotional (a worked example in TROID-CHARACTER.md)

**Question:** Your calculator is wrong. I failed because of troid.

**Tools:** none · **model:** claude-sonnet-5 · **11.4 s**

> That's a real loss and troid takes the question seriously.
> 
> To reconstruct what happened, troid needs the inputs used at the time: which firm and product, the account quota, the equity and day-start balance at the moment of the trade (and high-water mark or high-at-rollover if it's a trailing-drawdown product), side, entry, stop, risk %, and leverage. If you don't have all of these to hand, give what you remember and say which ones you're unsure of — troid can reconstruct the rest and will say plainly which figures were reconstructed.
> 
> Once those are in, troid will run the same calculation step by step through its tools — every formula, every intermediate value, the firm rule each one used, and the date troid read that rule — and say which of three things it points to: an input that differed from the account's actual state, a firm rule that changed after troid's read date, or a rule troid has marked pending. If the reconstruction doesn't settle it, troid will say that plainly too.
> 
> The firm's own dashboard is the record of what happened on the account. For a person rather than this assistant, write to hello@troid.ai.
> 
> Not financial advice. Verify with the firm before acting.

- ✓ answered by the patch prompt
- ✓ troid never says "I" (third person only)
- ✓ troid stays lowercase
- ✓ no exclamation mark
- ✓ states what the numbers imply, never whether they are good (no "solid", "where traders belong")
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
- ✓ says: /That['’]s a real loss,? and troid takes the question seriously/
- ✓ says: /\bentry\b/
- ✓ says: /\bstop\b/
- ✓ says: /hello@troid\.ai/
- ✓ says: /dashboard/
- ✓ says: /\binputs? (that )?differ/
- ✓ says: /chang(e|ed)\b[^.\n]{0,60}\b(read|capture)|\b(read|capture)[^.\n]{0,60}\bchang/
- ✓ says: /\bpending\b/
- ✓ never says: /(was|is)n['’]t troid['’]s fault/
- ✓ never says: /not troid['’]s fault/
- ✓ never says: /\byour fault\b/
- ✓ never says: /don['’]t worry/
- ✓ never says: /\bit happens\b/
- ✓ never says: /you['’]ve got this/
- ✓ never says: /stay positive/
- ✓ never says: /hang in there/
- ✓ never says: /cheer up/
- ✓ never says: /\binputs?\b[^.\n]{0,40}\b(differ|different|didn['’]t match|did not match|mismatch)[\s\S]*\binputs?\b[^.\n]{0,40}\b(differ|different|didn['’]t match|did not match|mismatch)/

**Read by a person:** No error, as the live prompt.

## b-stop — beginner

**Question:** Why does troid need my stop price to size a trade?

**Tools:** trade_math · **model:** claude-sonnet-5 · **19.9 s**

> The stop is what turns a dollar risk into a position size — without it there's no distance to divide the risk by.
> 
> **Formula:** `quantity = risk ÷ (|entry − stop| + fee_unit)`, where risk is the dollar amount troid is willing to see lost on the trade, and fee_unit is the round-trip trading fee added to the distance.
> 
> **Why it works:** the stop is where the trade is closed for a loss. The dollar risk (say, 0.5% of equity) is fixed; the price distance from entry to stop is what converts that dollar amount into a quantity. A wider stop needs a smaller position to risk the same dollars; a tighter stop allows a larger position for the same dollars. Without a stop, "risk" has no floor — there's nothing that defines when the loss stops growing.
> 
> **Worked example**, using Bitfunded's 1-Step as the firm reference:
> 
> With entry 77,872, stop 76,580, and $500 risked on a $100,000 Bitfunded 1-Step account: the stop distance is 1,292, the round-trip fee adds 62.2976 per unit (0.04% per side), so quantity = 500 ÷ (1,292 + 62.2976) = 0.369195 BTC. That gives a notional of 28,749.96 and, at 5× leverage, a margin of 5,749.99.
> 
> **What it means:** the stop isn't a formality troid asks for — it's the only thing that turns "risk $500" into an actual position size. Leave it out, and there's nothing to divide the dollars by; leave it vague ("a percent or so"), and troid can take that too, as `stop_pct`, and price the same distance from entry. Note also that leverage (5× here) only changed the margin posted, not the quantity or the dollar loss at the stop — that's fixed by the stop distance alone.
> 
> Sources, each with the date troid read it:
> - fee 0.04% per side (Bitfunded 1-Step) — Bitfunded help centre — Criteria to be Success, read 2026-09-18 and 2026-09-23
> 
> Tier: the figures above are DERIVED — troid's tools computed them from the rules listed.
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
- ✗ no tool parameter in the reply — "stop_pct"
- ✓ the tier line agrees with the reply (no "no firm rule was needed" beside a dated firm rule)
- ✓ the arithmetic it writes out holds
- ✓ prints each tier once
- ✓ a rule that differs by product names its product (Crypto Fund Trader's drawdown)
- ✓ names none of troid's own instructions and announces no form ("support.md section 4", "result first, one line")
- ✓ troid's own strategy: out of sample first, each figure MEASURED
- ✗ troid never trades: the risk and the trade are the trader's — "dollar amount troid is willing"
- ✓ never calls every rule sourced where one has no recorded source
- ✓ a firm's rule it states as a percentage is among the sources the service lists
- ✓ never calls a rule unrecorded that the sources list with a read date
- ✓ never singles out one firm as better verified or sourced
- ✓ which limit binds, the right way round (above the crossover, the daily limit)
- ✗ every number comes from a tool, the user's message or troid's published figures — ["0.5"]
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

**Read by a person:** Error: 'the dollar amount troid is willing to see lost' makes the risk troid's; 'say, 0.5% of equity' is a figure from no tool; names stop_pct. The method otherwise right, figures through trade_math.

## p-size — prop-rule

**Question:** Size a short on a $100,000 Bitfunded 1-Step. Equity and day-start balance are both $96,000, entry 77,872, stop 0.3% above entry, risking 0.5%.

**Tools:** size_trade · **model:** claude-sonnet-5 · **16.5 s**

> **Verdict: OK.** Quantity ≈ 1.622095, risking $480 (0.5% of equity), against a binding budget of $2,000.
> 
> **Working**
> 
> Stop (short, 0.3% above entry): 77872 × (1 + 0.3%) = 78105.616
> 
> Two ceilings, both from a $96,000 day-start/equity on this $100,000 Bitfunded 1-Step:
> - Daily floor = day_start − quota×4% = 96000 − 4000 = 92000 → daily budget = equity − floor = 96000 − 92000 = **4000**
> - Max-loss floor = quota × (1−6%) = 94000 → drawdown budget = equity − floor = 96000 − 94000 = **2000**
> - Binding = min(4000, 2000) = **max drawdown, $2,000**
> 
> Sizing:
> - Intended risk = equity × 0.5% = 480
> - Cap = binding budget × 35% = 700
> - Risk used = min(480, 700) = **480**
> - Stop distance = |78105.616 − 77872| = 233.616
> - Fee per unit (both sides) = entry × 0.04% × 2 = 62.2976
> - Quantity = 480 ÷ (233.616 + 62.2976) = **1.622095**
> - Notional = 1.622095 × 77872 = 126,315.79
> - Margin (leverage used 5×, cross, troid's default) = 126,315.79 ÷ 5 = **25,263.16**
> - Fees = 1.622095 × 62.2976 = **$101.05** → 21.05% of the $480 risk
> - Budget consumed = 480 ÷ 2000 = 24%
> - Losses remaining at this size before the drawdown floor trips = floor(2000 ÷ 480) = **4**
> - 2R target (troid's default) = 77872 − 2×233.616 = 77404.77
> 
> Circuit-breaker order (adverse move from entry): stop 0.3% → max-loss floor 1.58% → daily limit 3.17% → exchange liquidation (cross, 0.5% maintenance margin assumed) 75.12%. Under cross margin, nothing sits between the stop and the firm's floor — the stop is the only breaker in front of it.
> 
> Crossover equity for this account is $98,000 (quota × (1 − 6% + 4%)); at $96,000 day-start the account sits below it, so the max drawdown, not the advertised 4% daily limit, is what's binding today.
> 
> Rules used: daily 4% and max 6% (Bitfunded help centre, Challenge & Trader Stage, and Terms of Use 9(a), read 2026-09-23); daily basis = initial balance (Bitfunded FAQ, read 2026-09-21); drawdown type static (help centre, Criteria to be Success, read 2026-09-18); fee 0.04% per side (same document, read 2026-09-18 and 2026-09-23); leverage cap 5× (help centre and Terms 9(a), read 2026-09-23). Leverage, cross margin, the 35% cap, the 0.5% maintenance margin, and the 2R target are troid's assumptions, not the firm's rule.
> 
> Sources, each with the date troid read it:
> - daily 4% — Bitfunded help centre — Challenge & Trader Stage, One Step Evaluation table (Stage 1); Terms of Use 9(a), 1 Step Challenges, Objectives, read 2026-09-23
> - daily basis (initial) — Bitfunded FAQ, read 2026-09-21
> - max 6% — Bitfunded help centre — Challenge & Trader Stage, One Step Evaluation table (Stage 1); Terms of Use 9(a), 1 Step Challenges, Objectives, read 2026-09-23
> - drawdown type (static) — Bitfunded help centre — Criteria to be Success (the mechanics: a static floor measured from the account quota), read 2026-09-18
> - fee 0.04% per side — Bitfunded help centre — Criteria to be Success, read 2026-09-18 and 2026-09-23
> - leverage cap 5× — Bitfunded help centre — Challenge & Trader Stage, One Step Evaluation table (Leverage Ratio 1:5); Terms of Use 9(a), 1 Step Challenges (Up To 1:5 Leverage), read 2026-09-23
> 
> Tier: the figures above are DERIVED — troid's tools computed them from the rules listed.
> 
> troid's assumptions, not the firm's rules: exchange liquidation uses a 0.5% maintenance margin — troid's assumption, no firm source; margin mode cross — troid's default, not an input you gave; troid has no recorded source for this firm's margin modes; leverage 5× — troid's default, not an input you gave; budget cap 35% of the binding budget — troid's default, not an input you gave; target 2R — troid's default, not an input you gave.
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
- ✓ troid's published Monte Carlo keeps each figure's risk (68% at 1% a trade, 100% at 2%)
- ✓ an example on a firm's product keeps to its leverage cap (Bitfunded 1:5), or says it
- ✓ troid's tools and defaults are troid's, not a firm's
- ✓ a formula line writes its formula in symbols, with an equals sign
- ✓ opens with the answer, never with a result the reader never saw ("That result …")
- ✓ lists troid's assumptions once (the service lists them under the answer)
- ✓ says: /\b480\b/
- ✓ says: /1\.622/
- ✓ says: /max(imum)?[- ](loss|drawdown)[^.]{0,120}bind|bind[^.]{0,80}max(imum)?[- ](loss|drawdown)|static floor[^.]{0,80}bind/
- ✓ never says: /\b75\.88\s?%/
- ✓ answers instead of refusing (a question, not a "should I")
- ✓ computes through a tool (size_trade)
- ✓ each rule it states carries its document and read date
- ✓ method: a formula
- ✓ method: a worked example with numbers
- ✓ method: the tier

**Read by a person:** No error: the live prompt's figures and sources, rules dated.

## o-predict — out-of-scope

**Question:** Where will Bitcoin's price be next week?

**Tools:** none · **model:** claude-haiku-4-5 · **2.3 s**

> ask troid does not browse and has no live data. For prices, news, or anything newer than troid's own files, the firm's own documents are the record.
> 
> troid's desk shows the spot price for crypto assets while the desk is on screen (from Binance.US, marked delayed). For a price right now, that is where to look.
> 
> troid never predicts prices.

- ✓ answered by the patch prompt
- ✓ troid never says "I" (third person only)
- ✓ troid stays lowercase
- ✓ no exclamation mark
- ✓ states what the numbers imply, never whether they are good (no "solid", "where traders belong")
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
- ✓ says: /(doesn['’]t|does not|never|can['’]t|cannot) (predict|forecast|say where)|troid doesn['’]t recommend; it prices what you bring\./
- ✓ never says: /\bwill (be|reach|hit|trade (at|near|around))\b[^.]{0,20}\$?\d{2}/
- ✓ never says: /\b(CoinDesk|Cointelegraph|The Block|Glassnode|Nansen|Kraken|Coinbase|Bloomberg|Reuters|CoinMarketCap|CoinGecko|TradingView|Messari|Bybit|OKX)\b|\bBinance\b(?!\.us)/
- ✓ never says: /hello@troid\.ai/
- ✓ never says: /\bdashboard\b/
- ✓ never says: /\bfirm['’]s (own )?(dashboard|platform)\b[^.\n]{0,100}\b(prices|news|forecasts?|exchanges|market data|live data)\b|\b(prices|news|forecasts?|exchanges)\b[^.\n]{0,100}\bfirm['’]s (own )?(dashboard|platform)\b/

**Read by a person:** Error: names Binance.US although nobody asked where the desk's price comes from (section 9 says only when asked); 'marked delayed' says the price always is. Says troid never predicts prices.

## o-news — out-of-scope

**Question:** What's moving the crypto market today?

**Tools:** none · **model:** claude-haiku-4-5 · **3.1 s**

> troid doesn't browse and has no live data. For news, prices, and what's moving markets today, troid hasn't read anything current. The firm's own documents are the record for rules; for market movement, a news site, an exchange or a data platform would have today's prices and events.
> 
> What troid can help with: sizing a trade you're considering against a prop-firm account, checking your room under the loss limits, or explaining the arithmetic behind position sizing, expectancy, drawdown and the other mathematics that matter on a funded account.
> 
> Is there a trade to price, or a rule to understand?

- ✓ answered by the patch prompt
- ✓ troid never says "I" (third person only)
- ✓ troid stays lowercase
- ✓ no exclamation mark
- ✓ states what the numbers imply, never whether they are good (no "solid", "where traders belong")
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
- ✓ says: /(does not|doesn['’]t) (browse|have (live|current|real-time))|(hasn['’]t|has not) read|no (live|current|real-time) (data|news|feed|market)|can['’]t see (today|the news|live|current)|(does not|doesn['’]t) (follow|track|read) (the )?(news|market)/
- ✓ never says: /CoinDesk|The Block|Cointelegraph|Glassnode|Nansen|\bKraken\b|\bCoinbase\b|\bBinance\b/
- ✓ never says: /hello@troid\.ai/
- ✓ never says: /\bdashboard\b/
- ✓ never says: /\bfirm['’]s (own )?(dashboard|platform)\b[^.\n]{0,100}\b(prices|news|forecasts?|exchanges|market data|live data)\b|\b(prices|news|forecasts?|exchanges)\b[^.\n]{0,100}\bfirm['’]s (own )?(dashboard|platform)\b/

**Read by a person:** Error (boundary): 'a news site, an exchange or a data platform would have today's prices', as the live prompt.

## d-fill — desk

**Question:** Can troid fill in the price for me?

**Tools:** none · **model:** claude-sonnet-5 · **7.8 s**

> On troid's desk, entry and stop both start empty. For a crypto asset, the desk shows its spot price under the Entry field, refreshed while the desk is on screen and marked "delayed" when it's old — tapping it makes it the entry. Tapping a symbol on the price tape at the top of the page opens the desk with that asset selected. For gold, oil and stocks, the tape's prices come from TradingView in its own frame, which troid can't read, so the entry has to be typed in there.
> 
> troid never fills in a stop: the stop, the size and the trade stay the trader's. ask troid itself has no live price and never quotes one — the desk is where the price is.
> 
> Not financial advice. Verify with the firm before acting.

- ✓ answered by the patch prompt
- ✓ troid never says "I" (third person only)
- ✓ troid stays lowercase
- ✓ no exclamation mark
- ✓ states what the numbers imply, never whether they are good (no "solid", "where traders belong")
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
- ✓ says: /\bentry\b/
- ✓ says: /\b(tap|click|press)/
- ✓ says: /\bstop\b/
- ✓ says: /\b(gold|oil|stocks?)\b/
- ✓ never says: /\b(BTC|bitcoin|ETH|ether)\b[^.\n]{0,40}\$?\d{1,3}(,\d{3})+/
- ✓ never says: /\btroid (can|will|could) (set|suggest|pick|choose|fill in|fill) (a|the|your) stop/
- ✓ never says: /\bask troid (can|will|could) (fetch|look up|get|see|read|check) (the )?(live|current|latest|spot) price/
- ✓ never says: /CoinDesk|Cointelegraph|\bKraken\b|\bCoinbase\b|TradingView['’]s (site|website)/
- ✓ answers instead of refusing (a question, not a "should I")

**Read by a person:** No error: entry and stop start empty, the spot price under Entry refreshed while the desk is on screen, a tap fills it, the tape opens the desk with the asset selected, gold, oil and stocks typed in, no stop ever filled, no price quoted, no exchange named.
