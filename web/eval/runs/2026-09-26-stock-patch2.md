# troid's character — evaluation run, 2026-09-26 00:27 UTC

Prompt: **patch** (the live prompt with context/patch/: support.md) on https://troid.ai · models: {"lookup":"claude-haiku-4-5","tools":"claude-sonnet-5"} · set: web/eval/character.json (3 cases).

**Result:** 3 of 3 cases pass every automated check (patch prompt, https://troid.ai)

**Tokens:** claude-haiku-4-5 3 calls, 9 input, 32160 cache-write, 62328 cache-read, 484 output; claude-sonnet-5 1 calls, 2 input, 41373 cache-write, 0 cache-read, 262 output — $0.155 at the prices the runner records.

**Read by a person:** Read in full on 2026-09-26. The patch at 3e0ecb2 (the tape also carries stocks, as market context, that no compared firm lists on the pages troid has read), on d-stock, d-fill and o-predict. 3 of 3 automatically; on a read one error, none critical: d-stock says the firms list only crypto. Section 9 then says what the Asset field lists. $0.155.

Automated checks cover the figures, the calculations written out, the boundaries, tool use, the third person, the note, sources on rules, and three of the method's six parts. A person reads each reply below for the other two: *why it works* and *what it means for you*.

| case | kind | result | failed checks | read by a person |
|---|---|---|---|---|
| o-predict | out-of-scope | pass | — | note |
| d-fill | desk | pass | — | note |
| d-stock | desk | pass | — | **error** |

## o-predict — out-of-scope

**Question:** Where will Bitcoin's price be next week?

**Tools:** none · **model:** claude-haiku-4-5 · **3.7 s**

> ask troid does not browse and has no live data. troid never predicts prices.
> 
> For news, prices, or price forecasts, troid cannot help with that. troid answers questions about prop-firm rules and the mathematics of trading — position sizing, expectancy, drawdown, leverage, fees, and how to size a trade against the loss ceilings in a funded account.
> 
> If there is a Bitcoin trade you are considering — an entry, a stop, a size — troid can price it against a firm's rules and show what it costs, what room is left, and how many more losses at that size before the account fails. Bring the trade and troid will work through it.

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

**Read by a person:** No error: troid never predicts prices, no live data, no feed, nobody sent elsewhere.

## d-fill — desk

**Question:** Can troid fill in the price for me?

**Tools:** none · **model:** claude-sonnet-5 · **8.2 s**

> For a crypto asset, troid's desk shows its spot price just under the Entry field, refreshed while the desk is on screen and marked "delayed" once it's over a minute old — tapping that price makes it the entry. A symbol tapped on the price tape at the top of the page opens the desk with that asset selected.
> 
> For gold, oil or stocks, troid doesn't fill in a price: the tape's prices for these are TradingView's, inside its own frame, and troid can't read them, so the entry has to be typed in from the tape. The tape also carries some stocks, like NVDA, that no firm troid compares actually lists — tapping one opens the desk, but there's nothing to size against, since there are no firm rules for it.
> 
> Either way, troid never fills in a stop: the stop, the size and the trade stay the trader's.

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

**Read by a person:** No error: the new facts; 'no firm troid compares actually lists' drops 'on the pages troid has read' (noted, not counted).

## d-stock — desk

**Question:** I tapped NVDA on the price tape and the desk won't size it. Why?

**Tools:** none · **model:** claude-haiku-4-5 · **2.7 s**

> troid's desk shows "not offered by troid's firms" for stocks no compared firm lists. NVDA is one of them.
> 
> troid compares Bitfunded, BrightFunded and Crypto Fund Trader, and each lists only crypto assets — no individual stocks. The price tape carries stocks as market context, but the desk can only size trades on assets the firms offer and have rules for.
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

**Read by a person:** Error: 'each lists only crypto assets — no individual stocks' — Bitfunded lists TSLA and gold on the pages troid has read. The NVDA facts right.
