# BrightFunded's 16 Nov 2026 plans: which 1-Step should troid's column show?

For the owner. Nothing below has been applied. `firms.json` gained the 2026-11-16 reads (`brightfunded.provenance.sources`
`*_1116`, each with its sha256 prefix) and three `rule_changes` entries. `compare_product`, `products`, `calc` and every
field's source list are unchanged, so /compare, /firms/brightfunded's rules, the desk and the calculator audit show what
they showed on 2026-11-04. Only these dates moved: /compare's "reviewed" date and the firm page's "last read" date.

## What changed

- **1-Step is now an OLD plan.** It covers accounts bought before 16 Nov 2026 only, and its rules don't change
  (`help_1step_old_1116`). `/1-step` now redirects to `/cfds/1-step-daily` (`product_1step_daily_1116`). Neither the
  product page nor the comparison table (`comparison_1116`) lists the old 1-Step.
- **1-Step Daily is sold from 16 Nov 2026.** Its sizing rules match the old plan's. The rest differs: no minimum days,
  payouts any day with a 1% buffer, a new account after each payout, and inactivity counts as a hard breach (see the
  Option B table).
- **The 2-Step and Instant changed too** (see the end of this note).
- **More articles troid cites are now OLD:** `9241611` (per-plan table), `9268736` (reward split) and `12577176`
  (consistency). Each now redirects to an `-old` URL that points to a new article.
- **The help centre was still being edited.** Three of the articles showed "Updated in the last 15 minutes" and two
  "in the last hour" when fetched (about 16:58 UTC). Re-read them before switching anything.

## Option A: keep the OLD 1-Step, labelled "accounts bought before 16 Nov 2026"

| Field | Change | Source |
|---|---|---|
| `compare_product.label`, `calc.products.1step.label` | "1-Step" → e.g. "1-Step (OLD): accounts bought before 16 Nov 2026" | `help_1step_old_1116` |
| `daily_pct` 3, `max_pct` 6, `target_pct` 10, `min_days` 5 | value unchanged; add the 11-16 read | `help_1step_old_1116`, `help_rules_old_1116` |
| `daily_basis`, `drawdown_type`, `reset_utc`, `calc.*` | unchanged; add the 11-16 read | `help_1step_old_1116`, `help_daily_loss_1116` (its table lists "1-Step (before November 16th, 2026) 3%") |
| `split`, `consistency_rule` | unchanged | `help_split_old_1116`, `help_consistency_old_1116` |
| `refund`, `us_available` | unchanged | `tc_1116` (7.7b; s.2) |
| `price` €497 | **no longer published for this plan**: `/1-step` now shows 1-Step Daily. Either keep "as published on 2026-11-04" (`product_1step_1104`, its last read) or return the field to pending | — |

Against it: the column would describe a plan nobody can buy, and the affiliate link beside it opens a site that sells
1-Step Daily, 2-Step Bright and Instant, not this plan.

## Option B: switch the column to 1-Step Daily

Keeping the key `1step` and changing only the label avoids churn. BrightFunded's `1step` appears in 9 named cases in
`audit/cases.py` and in 4 `web/test_desk.py` cases. The audit's grid and seeded cases read the products from the page,
so they would follow a rename; the named cases would not.

| Field | Change | Source |
|---|---|---|
| `compare_product.label`, `calc.products.1step.label` | "1-Step" → "1-Step Daily" | `product_1step_daily_1116`, `help_1step_daily_1116` |
| `min_days` (compare and `products.1step`) | 5 → 0 ("No Minimum" / "None") | `product_1step_daily_1116`, `comparison_1116`, `help_1step_daily_rules_1116`, `help_rules_1116` |
| `trader_stage_rule` | rewritten: payouts any day from the first funded trading day; a 1% buffer on the closed balance; no minimum or maximum; a new account after each payout, with the trailing max loss restarting; no new trade in 30 calendar days is a hard breach (reactivation until 30 Nov 2026 only); news rule unchanged | `help_1step_daily_payouts_1116`, `help_1step_daily_rules_1116`, `help_news_1116` |
| `daily_pct` 3, `max_pct` 6, `target_pct` 10, `price` €497 | values unchanged; sources replaced | `product_1step_daily_1116`, `comparison_1116`, `help_1step_daily_1116`, `help_1step_daily_rules_1116`, `help_rules_1116` |
| `daily_basis`, `reset_utc`, `calc.daily_basis` | text unchanged; sources replaced | `help_daily_loss_1116`, `help_1step_daily_rules_1116` |
| `drawdown_type`, `calc.drawdown` / `locks_at_initial_after_pct` / `hwm_basis` | unchanged (trailing on equity, real time, locking at 6%); sources replaced | `help_1step_daily_1116`, `help_1step_daily_rules_1116`, `help_rules_1116` |
| `split` | text unchanged ("80% … 90% with a paid add-on … up to 100% through the scaling plan") | `help_split_1116`, `help_1step_daily_addons_1116`. **Log a conflict** (`_conflicts_found`): the comparison table's row says "Up to 90%" while its heading says "Up To 100% Payout Ratio"; the product page says "Up to 90%" |
| `refund`, `consistency_rule`, `news_rule`, `hold_cap`, `profit_cap`, `us_available` | unchanged | `tc_1116`, `help_1step_daily_addons_1116`, `help_consistency_1116`, `help_news_1116`, `help_1step_daily_rules_1116`, `help_1step_daily_payouts_1116` |
| `hold_cap` provenance section text | "Terms and Conditions and 1-Step pages" → "… 1-Step Daily pages". `web/test_desk.py:353` expects the old words, so update it with the field | — |
| `products.1step.fee_eur_100k_promo`, `offers_seen` | both describe the OLD plan's discount; mark them ended. troid's pages carry no promotions | — |
| `_trailing_trap`, `verified_from`, `_daily_rollover_note` | re-cite to 18450319 and the 1-Step Daily URLs | the same keys |

The desk's sizing inputs keep their values, so the desk's figures and the audit's derivations are unchanged. Its labels
and read dates move, so `audit.yml`, `test_desk.py` and `test_firm_pages.py` need a run.

## Option C: show both

The compare column (one `compare_product`) becomes 1-Step Daily as in B, and the OLD 1-Step stays as a second product,
for example `calc.products.1step_old` labelled as in A, with its own `provenance.products` entries
(`help_1step_old_1116`, `help_rules_old_1116`, `help_daily_loss_1116`).

This takes every field change in B, plus one new desk product. That product adds states to `test_desk.py` (its 84
states are held to the audited desk), cases in `audit/`, and a row on the firm page. It also faces A's problem: there
is no current price for the OLD plan.

What it buys is small. The two plans size identically: the same 3% daily on max(balance, equity) at rollover, the same 6%
trailing on equity locking at +6%, the same reset. Only the minimum-days and payout rows differ.

## Still unverified, whichever option

- **Drawdown type.** For 1-Step Daily the help centre says trailing, in real time, on equity, locking at the starting
  balance once equity is 6% above it (`help_1step_daily_1116`, `help_1step_daily_rules_1116`, `help_rules_1116`). The
  product page and the comparison table don't say, and T&C 6.6(c) leaves it to the product. It is first-party, but in
  the help centre only.
- **Daily basis.** A fixed 3% of the original size below max(balance, equity) at rollover. The rollover tables in
  `help_1step_daily_rules_1116` and `help_daily_loss_1116` both confirm it. Sourced.
- **Reset time.** The 11:30–11:59 PM CET rollover, per the help centre only. UTC is troid's conversion: 22:30 UTC in
  winter, 21:30 UTC in summer.
- **Crypto leverage.** 1:5 per article 9268380 (`help_leverage_1116`), unchanged since 2026-03-17. It names no plan, so
  whether it covers the new plans isn't stated. `max_leverage` stays null: the per-asset cap still needs your call
  (`_lev_note`).
- **Fees.** No commission is published on `/trading-instruments` (fetched 2026-11-16, sha256 `d8bae503205cb6f6`; it
  shows only swap fees), on the product page or on the comparison table. `fee_per_side_pct` stays null. Swap-Free is a
  +10% add-on.
- **Max open positions.** Not on any page read.

## Separate decisions the same change raises

- **2-Step.** 2-Step Classic is OLD only (`help_2step_classic_old_1116`): the product page and comparison table don't
  list it. New 2-Step Bright keeps 8%/5%, 4% and 8% static, but replaces "5 trading days" with "3 profitable days per
  phase, each ≥0.5% net" (`help_2step_bright_rules_1116`), which is a different rule. The firm page's 2-Step rows still
  show the OLD plans' 5 days, cited to the per-plan article now marked OLD.
- **Instant** is new and not shown. Showing it would need a 1% max floating loss and a Friday close, neither of which
  the desk models (`help_instant_rules_1116`).

## If a recommendation helps

B, keeping the key `1step`: the compare exists to compare what a reader can buy, and the OLD plan has no published price
or link. The desk's numbers don't change, and `rule_changes` keeps the OLD plan's differences on the firm page. Re-read
the edited articles on a later day before switching.
