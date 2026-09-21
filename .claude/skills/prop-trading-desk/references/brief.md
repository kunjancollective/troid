# Brief mode

Read this when the user is starting a session — "what's worth watching", "anything
happening today", or asking for context before deciding whether to trade at all.

## What a brief is for

It answers one question: **is today a day to trade, and if so, where?**

It is not a market newsletter. Resist the pull toward comprehensive coverage. A trader
reading this at 8am needs four or five lines that change what they do, and nothing
they'd skim past.

## Always open with the budget

Before any market content, state the account's room:

```
$302 daily budget, $622 to the drawdown floor. Daily limit binds.
```

This frames everything after it. A great setup is irrelevant on a day with $30 of room,
and a trader who sees the budget first is less likely to talk themselves into
something. Run `scripts/risk.py budget` for it.

## Pulling the data

**With TVRemix connected, start with one call:** `analyze_structure_batch` on the whole
watchlist at `["240", "1D"]`. It returns trend, pullback state, nearest support and
resistance, SMC events, and a consensus verdict per symbol. That's most of the brief
in one round trip. Add `calculate_correlation_tool` when more than one position is
open or being considered. Then use the TradingView MCP for the pieces below that
TVRemix's batch call doesn't cover (fresh quote, calendar, news).

**Without it,** for each symbol in `config.watchlist`:

- `mcp-tv-get-symbol-data-batch` with `close`, `change`, `update_mode` — one call for
  the whole watchlist, quotes in a single round trip.
- `mcp-tv-get-ohlcv` on 4h or 1D — recent range, and ATR for today's expected move.
- `mcp-tv-get-technicals-rating` — only when it would change a decision. It's an
  indicator aggregate, not an edge; treat it as one input among several and don't lead
  with it.

For the session as a whole:

- `mcp-tv-get-economic-calendar` — the important one. A CPI or FOMC print inside the
  holding window is a sizing decision, not background colour. Crypto still reacts to
  US macro, so filter to US/EU high-impact rather than everything.
- `mcp-tv-get-news` — a headline check on the watchlist. Skip the noise; flag anything
  that moves a specific name.

**Bars are delayed 15+ minutes and the last one is still forming.** Say so if a number
looks like an entry price. Good for range, ATR, and structure; never quote it as a
live fill.

## Structure

```
Budget      $302 daily, $622 to floor — daily binds
Session     CPI at 13:30 UTC. Expect a spike; size accordingly or wait it out.

BTCUSDT     78,001  (−0.4%)  daily ATR 2,039  4h/1D mixed
            4h just printed a bearish CHoCH at 77,620 — last higher low is
            gone. Structure stop for a long is now 75,690 (3.0%); ~0.21 BTC
            at $500 risk. Not a long until it reclaims 78,420.
ETHUSDT     3,200   (−0.4%)  4h ATR 62
            Mid-range, nothing actionable.
SOLUSDT     —       your worst symbol in the journal, 8% win rate. Skipping
            unless the setup is exceptional.
```

Note the last line. When the journal has flagged a symbol as a leak, carry that into
the brief. Connecting the two modes is the most useful thing this skill does — the
brief is where a known leak can actually be prevented rather than diagnosed afterward.

## What to leave out

- Price predictions. Give levels and what would confirm or invalidate them.
- Indicator soup. Three confirming oscillators is one signal, not three.
- Symbols with nothing happening. "Mid-range, nothing actionable" is a complete entry,
  and a short brief is a sign of judgment rather than laziness.
- Any suggestion that a setup is high-probability. Report structure and let the trader
  decide; the skill's edge is risk, not direction.

## Alerts as the handoff

The natural end of a brief is an alert, not a trade. If a level matters but isn't in
play yet, offer to set one with `mcp-tv-create-alert` so they don't sit watching a
chart.

Ask first — an alert is a persistent object in their TradingView account. Confirm the
symbol, the price, and the direction before creating it, and don't create several at
once off a single yes.
