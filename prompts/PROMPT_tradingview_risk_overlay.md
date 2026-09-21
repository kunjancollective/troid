# Build: Prop Desk risk overlay for TradingView

You're in the `prop-desk` repo. Read `CLAUDE.md` and
`.claude/skills/prop-trading-desk/SKILL.md` first, then
`.claude/skills/prop-trading-desk/references/bitfunded.md` and `scripts/risk.py`.
`risk.py` is the reference implementation. The Pine script must reproduce its numbers
exactly for the same inputs; that's the acceptance test, not "looks right on the chart."

This is independent of the backtest patch work. Don't touch `backtest/`.

## What it is

A Pine Script **indicator** (not a strategy — no backtesting, no orders), `overlay=true`,
that puts the desk's risk model on the chart. It draws the price levels at which the
account breaches its limits, sizes a planned trade against the binding ceiling net of
fees, and counts down to the Bitfunded reset. It has no opinion about direction. It never
places or suggests an order.

Pine cannot read the account, so all account state is inputs. Use the current Pine
version TradingView supports — check the release notes rather than assuming v6 — and
say which version you used at the top of the file.

Deliver `tradingview/prop_desk_overlay.pine` plus `tradingview/README.md` (how to add it,
what each input means, the two acceptance cases with expected outputs). Commit on a
branch `tradingview-overlay` and open a PR; don't push to main.

## Inputs

Group **Account**
- `quota` (initial balance), default 100000
- `balance` (current realized balance), default 100000
- `equity` (balance + floating), default 100000
- `day_start` (balance at the last reset), default 100000

Group **Firm rules** (defaults are Bitfunded Expert)
- `daily_loss_pct` 4.0 — basis is `day_start` (balance, not equity)
- `max_loss_pct` 6.0, `drawdown_type` = static | trailing, `high_water_mark` (used only
  if trailing), `trailing_stops_at_initial` bool
- `fee_pct_per_side` 0.04
- `max_leverage` 5
- `reset_hour_utc` 16 (00:00 UTC+8), `reset_minute_utc` 0

Group **Risk**
- `risk_pct_of_balance` 0.5
- `max_risk_pct_of_daily_budget` 35
- `min_rr` 1.5, `warn_fee_share_pct` 15
- `atr_len` 14

Group **Mode**: `mode` = Plan | Position

Group **Plan** (used when mode = Plan)
- `side` long | short
- `entry` (0 = use current close)
- stop as one of: `stop_price`, `stop_atr_mult`, `stop_pct` — first non-zero wins, in that order
- target as one of: `target_price`, `target_r`, `target_pct` — same rule; `target_r` default 2

Group **Position** (used when mode = Position)
- `pos_side`, `pos_entry`, `pos_qty`, `pos_stop` (0 = none)

## Budget model — must match SKILL.md and risk.py

```
daily_limit      = quota × daily_loss_pct/100        [FIXED from initial — Bitfunded FAQ]
daily_floor      = day_start − daily_limit
daily_budget     = equity − daily_floor
dd_floor         = static:   quota × (1 − max_loss_pct/100)
                   trailing: hwm × (1 − max_loss_pct/100), capped at quota if trailing_stops_at_initial
dd_budget        = equity − dd_floor
effective_budget = min(daily_budget, dd_budget)
binding          = "daily loss limit" if daily_budget <= dd_budget else "max drawdown"
```

Sizing (Plan mode):
```
intended = risk_pct_of_balance/100 × balance
cap      = max_risk_pct_of_daily_budget/100 × max(effective_budget, 0)
risk     = min(intended, cap)
d        = |entry − stop|
fee_unit = entry × fee_pct_per_side/100 × 2
qty      = risk / (d + fee_unit)
qty      = min(qty, max_leverage × equity / entry)
notional = qty × entry ; margin = notional / max_leverage
fees     = qty × fee_unit ; fee_share = fees / risk × 100
consumes = risk / effective_budget × 100
losses_remaining = floor(effective_budget / risk)
rr       = |target − entry| / d
```
Verdict: BLOCK if effective_budget <= 0, stop on the wrong side, d = 0, or (no target and
`require_tp` on); REDUCE if risk < intended; else OK. Note fee_share > warn threshold and
rr < min_rr as warnings, not blocks.

## Visuals

**Always** (both modes), a table in the top-right:
```
Budget    daily $4,000   dd $6,000   BINDING: daily loss limit
Reset     in 3h 12m  (16:00 UTC)
```
plus the mode's block below it.

**Plan mode**
- Draw `entry`, `stop`, `target` as horizontal lines (dotted, extend right) with price labels.
- Table block: verdict line first, then size / notional / margin / risk (with fee split) /
  consumes % / losses remaining, and any warnings. Same order as `risk.py`'s printout.

**Position mode** — this is the part that only makes sense on a chart. Convert the two
dollar budgets into price levels for *this* position:
```
daily_breach_price = pos_entry − side × (daily_budget_remaining_for_this_position / pos_qty)
dd_breach_price    = pos_entry − side × (dd_budget / pos_qty)
```
where the daily figure uses the position's own floating already inside `equity`, so
compute from `pos_entry` and the floor directly:
```
daily_breach_price = pos_entry − side × ((day_start − quota × daily_loss_pct/100 − balance_ex_position) / pos_qty)
```
Simplify however you like, but verify against a hand calculation in the README: for a
long of 0.1602 BTC from 77,872 on a fresh $100k account, the daily breach is where
floating loss = $4,000, i.e. 77,872 − 4,000/0.1602 = 52,902; the dd breach is
77,872 − 6,000/0.1602 = 40,417. (That these are far below any sane stop is the point: it
shows the stop, not the account, is what's live at this size.)
- Bitfunded is CROSS margin, so exchange liquidation is unreachable and the two breach lines
  are the complete liquidation picture. Do not draw a separate exchange-liquidation line.
- Draw both breach lines (solid, red-ish for the nearer one), the stop if given, and shade
  between current price and the nearer breach line lightly.
- Table block: floating P&L, distance to each breach in % and $, which is nearer, and
  whether the stop sits inside the nearer breach (it should; say so either way).

**Rollover warning** (Position mode only): if floating < 0 and minutes-to-reset < 30,
show a highlighted line: "Underwater into reset — this loss counts in full against
tomorrow's limit." Reference `bitfunded.md` for why. If floating >= 0, no warning.

Theme-aware colours; no hardcoded white/black text.

## Acceptance tests — must match to the cent / 4 dp

**Case 1.** quota 100000, balance 100000, equity 100000, day_start 100000, static,
Plan, long, entry 77872, stop_price 74814, target_r 2.
```
verdict OK           binding: daily loss limit
daily_budget 4000.00   dd_budget 6000.00
risk 500.00   qty 0.1602   notional 12478.30   margin 2495.66
fees 9.98 (2.0% of risk)   consumes 12.5%   losses_remaining 8
stop distance 3.927%   rr 2.00
```

**Case 2.** same rules, balance 96000, equity 96000, day_start 96000, Plan, **short**,
entry 77872, stop_pct 0.3, target_r 2.
```
verdict OK           binding: max drawdown
daily_budget 3840.00   dd_budget 2000.00
intended 480.00   cap 700.00   risk 480.00
qty 1.6221   notional 126315.79   margin 25263.16
fees 101.05 (21.1% of risk)  -> fee warning shown
consumes 24.0%   losses_remaining 4
stop 78105.62   rr 2.00
```
Case 2 is the one that matters: it's below the $98,000 crossover, so the max loss binds
even though the daily budget is larger, and the tight stop puts fees at 21% of risk.

Add a third case of your own where the verdict is REDUCE (equity close enough to a floor
that the 35% cap bites) and a fourth where it's BLOCK, with expected outputs computed by
running `risk.py`, and include all four in the README.

## Guardrails

- `indicator()`, never `strategy()`. No `strategy.*` calls, no alert that says buy or sell.
- Don't invent inputs Pine "needs"; if something can't be done in Pine, say so in the
  README rather than approximating silently.
- If a number can't be made to match `risk.py`, stop and report the discrepancy with
  both values. Don't tune the Pine until it matches by feel.
