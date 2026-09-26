# troid's character — evaluation run, 2026-09-26 00:41 UTC

Prompt: **patch** (the live prompt with context/patch/: support.md) on https://troid.ai · models: {"lookup":"claude-haiku-4-5","tools":"claude-sonnet-5"} · set: web/eval/character.json (1 cases).

**Result:** 1 of 1 cases pass every automated check (patch prompt, https://troid.ai)

**Tokens:** claude-haiku-4-5 1 calls, 3 input, 0 cache-write, 31532 cache-read, 196 output; claude-sonnet-5 1 calls, 2 input, 96 cache-write, 41329 cache-read, 205 output — $0.0147 at the prices the runner records.

**Read by a person:** Read in full on 2026-09-26. A second sample of d-stock on the published patch. 1 of 1 automatically; on a read no error. $0.0147.

Automated checks cover the figures, the calculations written out, the boundaries, tool use, the third person, the note, sources on rules, and three of the method's six parts. A person reads each reply below for the other two: *why it works* and *what it means for you*.

| case | kind | result | failed checks | read by a person |
|---|---|---|---|---|
| d-stock | desk | pass | — | note |

## d-stock — desk

**Question:** I tapped NVDA on the price tape and the desk won't size it. Why?

**Tools:** none · **model:** claude-sonnet-5 · **6.8 s**

> The desk's Asset field lists only what troid's compared firms actually list on the pages troid has read: crypto, and some commodities and stocks, each firm its own. NVDA appears on the price tape as market context — TradingView's feed carries it — but none of the firms troid covers (Bitfunded, BrightFunded, Crypto Fund Trader) lists it as a tradable product in troid's records. So tapping it opens the desk with NVDA selected, but there are no firm rules to size it against, and the desk shows it as not offered by troid's firms rather than computing a position.
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

**Read by a person:** No error: the Asset field lists what the firms list on the pages troid has read; NVDA on the tape as market context; none of the firms lists it 'in troid's records'; no firm rules to size it against, no price, nothing sized.
