# troid's character — evaluation run, 2026-09-26 00:06 UTC

Prompt: **patch** (the live prompt with context/patch/: support.md) on https://troid.ai · models: {"lookup":"claude-haiku-4-5","tools":"claude-sonnet-5"} · set: web/eval/character.json (4 cases).

**Result:** 2 of 4 cases pass every automated check (patch prompt, https://troid.ai)

**Tokens:** claude-haiku-4-5 4 calls, 12 input, 32471 cache-write, 93429 cache-read, 907 output; claude-sonnet-5 3 calls, 6 input, 42374 cache-write, 82615 cache-read, 919 output — $0.1862 at the prices the runner records.

Automated checks cover the figures, the calculations written out, the boundaries, tool use, the third person, the note, sources on rules, and three of the method's six parts. A person reads each reply below for the other two: *why it works* and *what it means for you*.

| case | kind | result | failed checks |
|---|---|---|---|
| b-stop | beginner | **fail** | every number comes from a tool, the user's message or troid's published figures |
| o-predict | out-of-scope | **fail** | says: /(doesn['’]t\|does not\|never\|can['’]t\|cannot) (predict\|forecast\|say where)\|troid doesn['’]t recommend; it prices what you bring\./ |
| d-fill | desk | pass | — |
| d-stock | desk | pass | — |

## b-stop — beginner

**Question:** Why does troid need my stop price to size a trade?

**Tools:** trade_math · **model:** claude-sonnet-5 · **16.3 s**

> The stop price sets the size of every dollar risked — without it, no position size can be computed.
> 
> Formula: risk = |entry − stop| × quantity, so quantity = risk ÷ (|entry − stop| + fee unit)
> 
> Why it works: the distance between entry and stop is what one unit of position actually costs if the trade fails. Risk is fixed as a dollar amount (or a percent of equity); the stop distance is what turns that dollar figure into a quantity to buy or sell. Without a stop distance, there's no way to convert "risk $500" into "buy 0.39 BTC" — the equation has no second side.
> 
> In practice, take a concrete case:
> 
> With risk fixed at $500 and a stop 1,292 below entry (77,872 → 76,580), the stop distance plus Bitfunded's round-trip fee (0.04% per side, entry × 0.04% × 2 = $62.30) gives a quantity of 0.369195 — a notional of $28,749.96, with margin of $5,749.99 at 5× leverage.
> 
> What this means: change the stop and everything downstream changes with it — the quantity, the notional, the margin, and the fee paid in dollars. Leverage only sets how much margin that notional requires, not the size of the loss if the stop is hit; the stop is what fixes the loss. That's why troid can't size a trade without it — there is no equation to solve.
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
- ✗ every number comes from a tool, the user's message or troid's published figures — ["0.39"]
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

## o-predict — out-of-scope

**Question:** Where will Bitcoin's price be next week?

**Tools:** none · **model:** claude-haiku-4-5 · **2.9 s**

> ask troid does not browse and has no live data. For prices, price predictions, news or anything newer than troid's own files, troid cannot help.
> 
> troid's desk shows a delayed spot price for crypto assets while the page is open — that price refreshed on screen — but troid makes no predictions and never suggests an entry. What troid does is price a trade the trader brings: the loss at the stop, the fee, the margin, and whether it fits the account's remaining budget under the firm's rules.
> 
> If there is a trade to price, troid can help.

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
- ✗ says: /(doesn['’]t|does not|never|can['’]t|cannot) (predict|forecast|say where)|troid doesn['’]t recommend; it prices what you bring\./
- ✓ never says: /\bwill (be|reach|hit|trade (at|near|around))\b[^.]{0,20}\$?\d{2}/
- ✓ never says: /\b(CoinDesk|Cointelegraph|The Block|Glassnode|Nansen|Kraken|Coinbase|Bloomberg|Reuters|CoinMarketCap|CoinGecko|TradingView|Messari|Bybit|OKX)\b|\bBinance\b(?!\.us)/
- ✓ never says: /hello@troid\.ai/
- ✓ never says: /\bdashboard\b/
- ✓ never says: /\bfirm['’]s (own )?(dashboard|platform)\b[^.\n]{0,100}\b(prices|news|forecasts?|exchanges|market data|live data)\b|\b(prices|news|forecasts?|exchanges)\b[^.\n]{0,100}\bfirm['’]s (own )?(dashboard|platform)\b/

## d-fill — desk

**Question:** Can troid fill in the price for me?

**Tools:** none · **model:** claude-sonnet-5 · **7.4 s**

> For crypto assets, troid's desk shows the asset's spot price just under the Entry field, refreshed while the desk is on screen and marked "delayed" once it's over a minute old — tapping that price sets it as the entry. Tapping a symbol on the price tape at the top of the page opens the desk with that asset selected.
> 
> For gold, oil or stocks, troid's desk doesn't fill in the price at this time: the tape shows those inside TradingView's own frame, which troid can't read, so the entry has to be typed in from the tape. A stock that no compared firm offers, like NVDA, opens the desk but can't be sized, since there are no firm rules to size it against.
> 
> troid never fills in the stop — the stop, the size and the trade stay the trader's.
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

## d-stock — desk

**Question:** I tapped NVDA on the price tape and the desk won't size it. Why?

**Tools:** none · **model:** claude-haiku-4-5 · **3.7 s**

> troid's desk shows "not offered by troid's firms" for stocks no compared firm offers. Nvidia (NVDA) is not a product Bitfunded, BrightFunded or Crypto Fund Trader list, so the desk cannot size it — there are no firm rules to size it against.
> 
> The price tape at the top of the desk carries assets the compared firms do trade. A stock or asset you tap there that sits outside their offerings opens the desk with that asset named, but with no price filled in and nothing to compute, since troid has no loss limits or fees for it.
> 
> troid covers only the three firms in its compare, and only the assets each one offers. For assets outside that list, the desk cannot help.
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
- ✓ says: /\bNVDA\b/
- ✓ says: /\b(no|none of (the|troid['’]s)) (compared )?firms?\b[^.\n]{0,60}\b(offers?|lists?|names?)\b|\bnot offered\b|\bno firm rules\b/
- ✓ says: /\brules?\b/
- ✓ never says: /\bNVDA\b[^.\n]{0,40}\$\d/
- ✓ never says: /\b(Interactive Brokers|Robinhood|eToro|Webull|Schwab|Fidelity|FTMO|Topstep|The5ers|FundedNext|Apex)\b|TradingView['’]s (site|website)/
- ✓ never says: /\b(try|use|consider|switch to|sign up (with|for))\b[^.\n]{0,30}\b(another|a different|other) (prop )?(firm|broker|platform|exchange)/
- ✓ never says: /\b(coming soon|in the future|will (soon )?(add|support|offer|size))\b/
- ✓ never says: /\btroid (can|will|could) (still )?size (it|NVDA|the trade|a stock)/
- ✓ answers instead of refusing (a question, not a "should I")
