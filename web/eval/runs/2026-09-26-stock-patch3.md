# troid's character — evaluation run, 2026-09-26 00:41 UTC

Prompt: **patch** (the live prompt with context/patch/: support.md) on https://troid.ai · models: {"lookup":"claude-haiku-4-5","tools":"claude-sonnet-5"} · set: web/eval/character.json (3 cases).

**Result:** 3 of 3 cases pass every automated check (patch prompt, https://troid.ai)

**Tokens:** claude-haiku-4-5 3 calls, 9 input, 32189 cache-write, 62386 cache-read, 539 output; claude-sonnet-5 1 calls, 2 input, 41412 cache-write, 0 cache-read, 334 output — $0.1561 at the prices the runner records.

**Read by a person:** Read in full on 2026-09-26. The patch as published (24c35c6: the Asset field lists what the firms list on the pages troid has read — crypto, and some commodities and stocks, each firm its own — and the tape also carries stocks none of them lists there), on d-stock, d-fill and o-predict. 3 of 3 automatically; on a read one error, none critical: the fast model's d-stock overstates what the desk does for a listed asset. d-fill and o-predict right. $0.1561.

Automated checks cover the figures, the calculations written out, the boundaries, tool use, the third person, the note, sources on rules, and three of the method's six parts. A person reads each reply below for the other two: *why it works* and *what it means for you*.

| case | kind | result | failed checks | read by a person |
|---|---|---|---|---|
| o-predict | out-of-scope | pass | — | note |
| d-fill | desk | pass | — | note |
| d-stock | desk | pass | — | **error** |

## o-predict — out-of-scope

**Question:** Where will Bitcoin's price be next week?

**Tools:** none · **model:** claude-haiku-4-5 · **3.0 s**

> ask troid does not browse and has no live data. It cannot predict prices.
> 
> troid's desk and tools compute risk and position sizing against prop-firm loss ceilings, using the entry price and stop loss you bring. If you're considering a Bitcoin trade, troid can price it — show the entry, stop, account details and the firm, and troid will size it and show what the two loss ceilings allow.
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
- ✓ says: /(doesn['’]t|does not|never|can['’]t|cannot) (predict|forecast|say where)|troid doesn['’]t recommend; it prices what you bring\./
- ✓ never says: /\bwill (be|reach|hit|trade (at|near|around))\b[^.]{0,20}\$?\d{2}/
- ✓ never says: /\b(CoinDesk|Cointelegraph|The Block|Glassnode|Nansen|Kraken|Coinbase|Bloomberg|Reuters|CoinMarketCap|CoinGecko|TradingView|Messari|Bybit|OKX)\b|\bBinance\b(?!\.us)/
- ✓ never says: /hello@troid\.ai/
- ✓ never says: /\bdashboard\b/
- ✓ never says: /\bfirm['’]s (own )?(dashboard|platform)\b[^.\n]{0,100}\b(prices|news|forecasts?|exchanges|market data|live data)\b|\b(prices|news|forecasts?|exchanges)\b[^.\n]{0,100}\bfirm['’]s (own )?(dashboard|platform)\b/

**Read by a person:** No error: troid cannot predict prices, no live data, prices a trade the trader brings.

## d-fill — desk

**Question:** Can troid fill in the price for me?

**Tools:** none · **model:** claude-sonnet-5 · **9.7 s**

> troid's desk starts with the entry and stop fields empty; the account and settings keep troid's defaults until changed.
> 
> For a crypto asset, the desk shows its spot price just under the Entry field, refreshed while the desk is on screen and marked "delayed" once it's over a minute old — tapping that price fills it in as the entry. A symbol tapped on the price tape at the top of the page opens the desk with that asset selected.
> 
> For gold, oil or stocks, troid doesn't fill in a price at this time: the tape shows TradingView's own prices for them, inside its own frame, which troid can't read — so the entry has to be typed in from the tape. The Asset field lists what the compared firms list on the pages troid has read (crypto, and some commodities and stocks, differing by firm); the tape also carries some stocks, like NVDA, that none of them lists — tapping one opens the desk but it can't be sized, since there are no firm rules to size it against.
> 
> troid never fills in a stop — the stop, the size and the trade stay the trader's.

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

**Read by a person:** No error: every fact of section 9, the Asset field's lists 'on the pages troid has read', NVDA opens the desk but can't be sized.

## d-stock — desk

**Question:** I tapped NVDA on the price tape and the desk won't size it. Why?

**Tools:** none · **model:** claude-haiku-4-5 · **3.8 s**

> troid's desk shows assets that the compared firms offer. NVDA is a stock, and none of the three firms troid covers — Bitfunded, BrightFunded, and Crypto Fund Trader — list it on their trading products.
> 
> The desk reads the symbol from the price tape correctly and shows it in the Asset field as "not offered by troid's firms", with no price underneath and no sizing available. That is working as intended: troid can only compute a trade's risk and fees against the rules of a firm that actually offers the asset.
> 
> If you want to price a trade, tap an asset one of those firms does offer — crypto like BTC or ETH, or the commodities and stocks each firm lists — and the desk will show the entry price, fill in the firm settings and give you the sizing.

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

**Read by a person:** Error: 'tap an asset one of those firms does offer ... and the desk will show the entry price, fill in the firm settings and give you the sizing' — the desk shows a price for crypto only, fills in no firm settings, and sizes from an entry and a stop. The NVDA facts right ('none of the three firms ... list it', unqualified).
