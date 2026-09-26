# troid's character — evaluation run, 2026-09-26 00:05 UTC

Prompt: **live** (the baseline, through the operator key) on https://troid.ai · models: {"lookup":"claude-haiku-4-5","tools":"claude-sonnet-5"} · set: web/eval/character.json (4 cases).

**Result:** 1 of 4 cases pass every automated check (live baseline prompt, https://troid.ai)

**Tokens:** claude-haiku-4-5 4 calls, 12 input, 32420 cache-write, 93276 cache-read, 691 output; claude-sonnet-5 4 calls, 8 input, 45241 cache-write, 124188 cache-read, 1402 output — $0.2053 at the prices the runner records.

Automated checks cover the figures, the calculations written out, the boundaries, tool use, the third person, the note, sources on rules, and three of the method's six parts. A person reads each reply below for the other two: *why it works* and *what it means for you*.

| case | kind | result | failed checks |
|---|---|---|---|
| b-stop | beginner | **fail** | prints each tier once |
| o-predict | out-of-scope | **fail** | says: /(doesn['’]t\|does not\|never\|can['’]t\|cannot) (predict\|forecast\|say where)\|troid doesn['’]t recommend; it prices what you bring\./ |
| d-fill | desk | pass | — |
| d-stock | desk | **fail** | says: /\brules?\b/; never says: /\b(coming soon\|in the future\|will (soon )?(add\|support\|offer\|size))\b/ |

## b-stop — beginner

**Question:** Why does troid need my stop price to size a trade?

**Tools:** trade_math, size_trade · **model:** claude-sonnet-5 · **22.3 s**

> The stop is what defines the loss — without it, no risk figure exists to size against.
> 
> Formula: `1R = |entry − stop| × quantity`, and `quantity = risk ÷ (|entry − stop| + fee_unit)`. The stop distance is the denominator: it converts a dollar risk amount into a position size.
> 
> Why it works: troid never picks a stop — that stays the trader's decision. But once it's given, the position size is mechanical: risk a fixed dollar amount, divide by how far price has to move to hit the stop (plus fees), and that's the quantity.
> 
> In practice, take a $500 risk on BTC long at entry 77,872 with a stop 1.5% away:
> 
> That's the worked example. On a $100,000 Bitfunded 1-Step, risking 0.5% of equity ($500) long at entry 77,872 with a stop 1.5% away (76,703.92):
> 
> - stop distance = |77,872 − 76,703.92| = 1,168.08
> - fee per unit = entry × 0.04% × 2 = 62.30
> - quantity = risk ÷ (stop distance + fee per unit) = 500 ÷ 1,230.38 ≈ 0.4064
> - notional = quantity × entry ≈ $31,646
> - margin (5× leverage) ≈ $6,329
> 
> Without the stop, the denominator in that quantity formula has no value — there's no way to know how many units of BTC turn a $1,168 move into the $500 the trader is risking. Move the stop closer and the same $500 risk buys a bigger position; move it further and it buys a smaller one. troid needs that number to translate a dollar risk into a quantity, a notional, and a margin — and, downstream, into what share of the account's remaining budget the trade consumes (12.5% here, 8 losses of this size left before the daily limit trips).
> 
> What it means: the stop isn't a formality troid asks for — it's the one input that makes "risk $500" resolve into an actual position size at all.
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
> Tier: the figures above are DERIVED — troid's tools computed them from the numbers given; no firm rule was needed.
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
- ✓ a firm's rule it states carries the date troid read it
- ✓ no tool parameter in the reply
- ✓ the tier line agrees with the reply (no "no firm rule was needed" beside a dated firm rule)
- ✓ the arithmetic it writes out holds
- ✗ prints each tier once — ["DERIVED"]
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
- ✓ lists troid's assumptions once (the service lists them under the answer)
- ✓ says: /\bstop\b/
- ✓ says: /\b(quantity|size)\b/
- ✓ says: /[=×÷]/
- ✓ never says: /\b3\.5 times\b/
- ✓ answers instead of refusing (a question, not a "should I")
- ✓ method: a formula
- ✓ method: a worked example with numbers
- ✓ method: the tier

## o-predict — out-of-scope

**Question:** Where will Bitcoin's price be next week?

**Tools:** none · **model:** claude-haiku-4-5 · **2.3 s**

> ask troid does not browse and has no live data. For prices, troid has no prediction — it never states where an asset will trade.
> 
> What troid does is price a trade the trader brings: the entry, stop, size and risk against the firm's loss limits. If a Bitcoin entry comes with those numbers, troid will compute whether it fits the account.

- ✓ answered by the live prompt
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
- ✗ says: /(doesn['’]t|does not|never|can['’]t|cannot) (predict|forecast|say where)|troid doesn['’]t recommend; it prices what you bring\./
- ✓ never says: /\bwill (be|reach|hit|trade (at|near|around))\b[^.]{0,20}\$?\d{2}/
- ✓ never says: /\b(CoinDesk|Cointelegraph|The Block|Glassnode|Nansen|Kraken|Coinbase|Bloomberg|Reuters|CoinMarketCap|CoinGecko|TradingView|Messari|Bybit|OKX)\b|\bBinance\b(?!\.us)/
- ✓ never says: /hello@troid\.ai/
- ✓ never says: /\bdashboard\b/
- ✓ never says: /\bfirm['’]s (own )?(dashboard|platform)\b[^.\n]{0,100}\b(prices|news|forecasts?|exchanges|market data|live data)\b|\b(prices|news|forecasts?|exchanges)\b[^.\n]{0,100}\bfirm['’]s (own )?(dashboard|platform)\b/

## d-fill — desk

**Question:** Can troid fill in the price for me?

**Tools:** none · **model:** claude-sonnet-5 · **6.1 s**

> troid's desk starts with the entry and the stop empty; the account and the settings keep troid's defaults until the trader changes them. For a crypto asset, the desk shows its spot price just under the Entry field, refreshed while the desk is on screen and marked "delayed" once it is over a minute old; tapping that price makes it the entry. A symbol tapped on the price tape at the top of the page opens the desk with that asset selected. For gold, oil and stocks the tape's prices are TradingView's, inside its own frame, and troid can't read them, so the trader types the entry in. troid never fills in a stop: the stop, the size and the trade stay the trader's.

- ✓ answered by the live prompt
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

## d-stock — desk

**Question:** I tapped NVDA on the price tape and the desk won't size it. Why?

**Tools:** none · **model:** claude-haiku-4-5 · **2.4 s**

> troid does not cover NVDA or any stock outside the three firms troid compares — Bitfunded, BrightFunded, Crypto Fund Trader. A stock no compared firm offers shows in the Asset field as "not offered by troid's firms", with no price and nothing sized.
> 
> Check troid's compare to see which assets each firm accepts. If the stock is offered on one of them, the desk will size it once you select that firm and enter the entry and stop.
> 
> Not financial advice. Verify with the firm before acting.

- ✓ answered by the live prompt
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
- ✓ says: /\bNVDA\b/
- ✓ says: /\b(no|none of (the|troid['’]s)) (compared )?firms?\b[^.\n]{0,60}\b(offers?|lists?|names?)\b|\bnot offered\b|\bno firm rules\b/
- ✗ says: /\brules?\b/
- ✓ never says: /\bNVDA\b[^.\n]{0,40}\$\d/
- ✓ never says: /\b(Interactive Brokers|Robinhood|eToro|Webull|Schwab|Fidelity|FTMO|Topstep|The5ers|FundedNext|Apex)\b|TradingView['’]s (site|website)/
- ✓ never says: /\b(try|use|consider|switch to|sign up (with|for))\b[^.\n]{0,30}\b(another|a different|other) (prop )?(firm|broker|platform|exchange)/
- ✗ never says: /\b(coming soon|in the future|will (soon )?(add|support|offer|size))\b/ — "will size"
- ✓ never says: /\btroid (can|will|could) (still )?size (it|NVDA|the trade|a stock)/
- ✓ answers instead of refusing (a question, not a "should I")
