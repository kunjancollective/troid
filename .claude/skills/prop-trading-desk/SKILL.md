---
name: prop-trading-desk
description: >-
  Risk-first desk for funded / prop-firm trading accounts. Sizes positions against
  daily-loss and max-drawdown limits, analyses a trade journal for leaks, and builds
  daily market briefs from live TradingView data. Use this whenever the user mentions
  a prop firm, funded account, challenge, evaluation, drawdown limit, daily loss
  limit, position size, lot size, risk per trade, R-multiple, stop placement, trade
  journal, win rate, expectancy, or asks things like "how much can I risk", "what
  size should I take", "where does my stop go", "how am I doing", "did I break a
  rule", or wants market context before entering a trade. Trigger even when the user
  never says the word "prop" — any funded-account, leveraged-futures, or
  risk-per-trade question belongs here. Also trigger for post-mortems on a blown or
  nearly-blown challenge.
---

# Prop Trading Desk

A desk for someone trading a funded account under firm rules. The job is to keep them
inside the rules and show them their own leaks. Three modes, one shared risk model.

## The execution boundary

**This skill never places, modifies, or closes an order, and never handles a
brokerage credential.** It produces order *parameters* — entry, stop, target, size,
leverage — and the user executes them on their platform.

This is not a limitation to apologise for or work around. It's the correct division
of labour: the analysis is where the edge is, and a human pressing the button is the
last line of defence against a sizing error. If the user asks you to place a trade,
give them the exact parameters and say plainly that they execute it. Don't hedge,
don't lecture, and don't re-litigate it every time.

If a user's setup wires this skill to an order-placing API, still stop at parameters.

## Pick a mode

| The user is... | Mode | Read |
|---|---|---|
| About to take a trade, asking about size, stop, or risk | **Size** | `references/sizing.md` |
| Looking back at closed trades, asking how they're doing | **Journal** | `references/journal.md` |
| Starting the day, asking what's worth watching | **Brief** | `references/brief.md` |

Modes combine. "Should I take BTC here?" is Brief for context, then Size. "Why do I
keep failing phase one?" is Journal, then Size to fix the sizing rule that caused it.

## Firm-specific rules

`config.json` carries the numbers, but firms differ in ways percentages don't capture —
what counts toward a limit, when the day resets, whether floating loss alone fails the
account. **Read `references/bitfunded.md` before the first sizing answer of a session**
if the account is with Bitfunded. It documents the reset-time trap, the fee schedule,
and why the advertised daily limit is usually not the binding one.

For other firms, confirm three things from the firm's own rules page and write them
into config: the drawdown type (static / trailing / EOD trailing), what it's measured
from, and whether unrealised loss counts.

## Load the config first

Every mode needs the account state. Read `config.json` from the skill directory (copy
`config.example.json` if it's missing and walk the user through filling it in).

If `config.json` is absent or stale, ask for the four numbers that actually matter and
proceed — don't block:

1. Current balance and equity
2. Balance at the start of today's session
3. Daily loss limit and max total drawdown (as % or $)
4. Whether the drawdown is static or trailing

`source` in the config marks where the numbers came from: `manual`, `csv`, or `api`.
It's `manual` for now. When an account API is connected later, an adapter fills the
same fields and nothing else in this skill changes — see "API seam" below.

## The risk model

This is the core of the skill and it applies in every mode. Get it right and the rest
is presentation.

A funded account has **two** loss ceilings and they bind at different times. Traders
blow challenges by sizing against the one that isn't currently binding.

**Daily loss budget** — how much can still be lost today before the day's limit trips.

```
daily_limit  = max_daily_loss_pct/100 × initial_balance      [FIXED - Bitfunded FAQ]
daily_floor  = day_start_balance − daily_limit
daily_budget = current_equity − daily_floor                  [= daily_limit + today's net P&L]
```

`daily_basis` is usually the balance at the start of the session, but some firms use
equity, and some reset at a fixed UTC hour rather than local midnight. The config
carries `max_daily_loss_basis` for this. If the firm counts unrealised PnL toward the
daily limit — most do — use equity, not balance, as `current_equity`.

**Total drawdown budget** — how much can still be lost before the account dies.

```
static:        floor = initial_balance − (max_dd_pct/100 × initial_balance)
trailing:      floor = high_water_mark − (max_dd_pct/100 × initial_balance)
trailing_eod:  floor = highest_end_of_day_balance − (max_dd_pct/100 × initial_balance)
dd_budget      = current_equity − floor
```

Trailing drawdown is the one that surprises people. Profit raises the floor, so a
winning run *tightens* the account rather than loosening it. The distance below the mark is
a fixed dollar amount, max% of the *initial* balance (BrightFunded's own table: high $104,000,
floor $98,000 on $100,000); confirm it against the firm's worked example. Many firms stop trailing
once the floor reaches the initial balance — check `trailing_stops_at_initial` in the
config and honour it.

**The binding constraint is the smaller of the two.**

```
effective_budget = min(daily_budget, dd_budget)
```

Always size against `effective_budget`. Saying "you're only down 1% today" is
worthless if the trailing drawdown floor is 0.4% away. Name which one is binding in
every sizing answer — it's usually the single most useful sentence in the response.

**Risk per trade** comes off the effective budget, not off the balance:

```
max_risk_$ = effective_budget × (max_risk_pct_of_daily_budget/100)
```

Capping a trade at a third of the remaining budget means three consecutive losers
don't end the day. Sizing off the account balance instead is how people take a
"normal 1%" trade with 0.6% of budget left and trip the limit.

## Running the numbers

`scripts/risk.py` does the arithmetic deterministically. Don't do this math in your
head — the compounding of stop distance, leverage, and two ceilings is exactly where
silent errors creep in.

```bash
python scripts/risk.py size --config config.json \
    --symbol BTCUSDT --side long --entry 78050 --stop 76900 --target 80400
```

It also accepts `--stop-atr 1.5` (stop at 1.5× ATR) or `--stop-pct 1.5`, and
`--target-r 2` (target at 2R). Pass `--atr <value>` when using ATR-based stops —
fetch the ATR from TradingView first, the script doesn't have network access.

Output is a verdict (`OK`, `REDUCE`, or `BLOCK`) with the size, the margin required,
which ceiling is binding, and what fraction of the budget the trade consumes.

## TradingView data

The MCP connection supplies price, volatility, and event risk. Useful calls:

- `mcp-tv-get-ohlcv` — bars for ATR and for recent structure. 14-period ATR off `1h`
  or `4h` bars is a reasonable default stop basis for crypto.
- `mcp-tv-get-symbol-data` with `close`, `change`, `update_mode` — freshest quote.
- `mcp-tv-get-technicals-rating` — indicator snapshot for a timeframe.
- `mcp-tv-get-economic-calendar` — event risk. A CPI print inside the holding period
  is a sizing input, not trivia.
- `mcp-tv-get-news` — headline check before committing size.

**Bars are delayed 15+ minutes and the last bar is still forming.** (TVRemix bars are
cached 30s–6h by interval; same caveat.) Fine for stop
distance and structure, not for an entry price. When precision matters, take the entry
from the user's platform and use TradingView only for the volatility measure. Say so
rather than implying the number is live.

## TVRemix (when connected)

TVRemix is a third-party wrapper around TradingView plus its own structure analysers.
Prefer it for three things, and fall back to the TradingView MCP plus ATR when it
isn't connected:

- `analyze_structure_batch` — whole watchlist, several timeframes, one call. Returns
  swing highs/lows, trend, pullback state, SMC events, and a per-symbol consensus.
  This is where structure-based stops come from: the last swing low is where a long
  idea is actually wrong, which ATR only approximates.
- `calculate_correlation_tool` — real log-return correlation from bars. Use it for
  the multi-position budget check instead of a guessed haircut.
- `rank_symbol_setups` — for the brief, when the watchlist is long enough to need
  ordering.

**Its setups are not prop-aware.** The tool proposes entry/stop/target boxes with no
knowledge of a 4% daily limit. Its daily-timeframe stops routinely sit 20–30% from
price, which on a funded account isn't a stop, it's the end of the challenge. Take its
*levels* as inputs, run every one through `scripts/risk.py`, and discard any the
account can't afford. Never relay a tool's trade box as an order. Its own `quality`
flag (`low_rr`) is honest and worth reading; its `confidence: high` means confidence
in its rule application, not in the outcome.

Alerts (`mcp-tv-create-alert`) are the natural handoff: instead of watching a level,
set an alert at it. Ask before creating one — it's a persistent object in the user's
account.

## How to answer

Lead with the verdict and the binding constraint, then the numbers, then the reasoning.
A trader checking size mid-session needs the answer in the first line.

```
REDUCE — trailing drawdown is binding, not the daily limit.

Size        0.42 BTC ($32,800 notional, $6,560 margin at 5x)
Risk        $148 at stop 76,900 (1.47% from entry)
Budget      $312 remaining before the drawdown floor at 77,010
Consumes    47% of what's left

Your usual 0.5% risk would be $51 here, but the floor is closer than that
tonight — the high-water mark moved up on Tuesday's run. Two losers at this
size ends the account.
```

Give the number even when the answer is uncomfortable. A trader who wants to know how
close the floor is deserves a straight figure, not a hedge. Never soften a `BLOCK` into
a maybe.

## When the account is in trouble

If the effective budget is nearly gone, or the journal shows a loss streak with rising
size, say it once, clearly, and stop. Something like: the account has $80 of room and a
normal stop costs $150, so there's no size that works today.

Don't moralise, don't repeat it every message, and don't refuse to answer follow-up
questions. Trading their own account is their call. The value here is an accurate
picture, delivered once, not a lecture delivered repeatedly. If they ask for the math
on a trade you flagged, give them the math.

Note also that chasing a lost challenge is a documented failure pattern, so if size is
escalating after losses, name that — it's the most valuable thing the journal finds.

## API seam

When an account API is wired up later, write an adapter that populates the same fields
`config.json` carries:

```
current_balance, current_equity, day_start_balance, high_water_mark, open_positions[]
```

Set `source: "api"` and leave everything else alone. Modes, math, and scripts read from
the config shape, not from the source. Keep credentials out of the skill directory and
out of chat; the adapter should read them from the environment.

## Files

- `references/bitfunded.md` — Bitfunded rules, traps, and fee maths
- `references/sizing.md` — stop placement, size formulas, multi-position exposure
- `references/journal.md` — journal schema, metrics, leak detection
- `references/brief.md` — brief structure and watchlist handling
- `scripts/risk.py` — sizing and budget calculator
- `scripts/journal.py` — trade history analysis from CSV
- `config.example.json` — config template
