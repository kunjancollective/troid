# troid — methodology, versioned

troid publishes arithmetic, and arithmetic can be wrong. This file says how numbers get
onto a page, what tier each one carries, and every correction made since launch. It is
versioned because the method changes, and a method that changes silently is a method
nobody can check.

## Tiers

Every published figure carries one of four tiers, and a reader can find which:

- **DERIVED** — algebra from a firm's published rules. Reproduces in `backtest/verify_claims.py`.
- **SOURCED** — read from a firm's own primary document, with the section cited.
- **MODELLED** — a simulation with stated assumptions. Sensitive to those assumptions.
- **MEASURED** — a backtest or forward test on one sample. Never stated as fact.

## How a rule gets onto a page

1. Read from the firm's own documents — Terms *and* help centre or product page, both.
2. Where the two disagree, the stricter figure governs until the firm confirms in writing.
3. Record the source URL beside the field. A config file is not a source.
4. Third-party directories and reviews may point at where to look. They never fill a cell.
5. A cell without a source shows *pending*. The same rule applies to every firm.

## How a strategy number gets onto a page

It doesn't, as fact. The strategy's result is MEASURED. It is published with its sample
size, standard error, and confidence interval, and with the number chance alone would
produce across the configurations searched. When the walk-forward came back as noise, the
page said so the same day.

## Firm selection

One reference firm, chosen for verification depth, not rank. Two rotating slots by an
external, public, checkable ranking, reviewed quarterly. Alphabetical on the page. No
score, no badge, no recommendation. The link for each appears when its affiliate
agreement exists and its daily, max, target and price are verified from its own documents.

## Corrections

| date | what was wrong | what changed |
|---|---|---|
| 2026-09-21 | Daily limit modelled from day-start balance. Bitfunded's FAQ says initial balance. An unverified assumption in the first config propagated through a code review that checked the engine against the config rather than the firm. | Basis corrected. Crossover $97,917 → $98,000. Rule added: no parameter enters a config without a `verified_from` URL. |
| 2026-09-21 | Open-position cap modelled as 10 (ToU). Help centre says 5. Hold cap modelled as a flat 10 days; help centre tiers it 10/7/5 by asset. | Both corrected to the stricter figure. Rule added: read Terms and help centre both. |
| 2026-09-21 | First live shadow run replayed history on a different exchange feed (binance.us) than the frozen sample (Binance.com via TradingView). 15 alternate-history trades were labelled "logged live." | Reverted within minutes. History re-backfilled on one feed end to end. Stitch step added. |
| 2026-09-21 | Journal stored R to three decimals; the mean sat on a rounding boundary and two artifacts disagreed at the second decimal. | Four decimals stored. Accuracy ledger now re-derives n, mean, SE and shrinkage from the journal and fails on drift. |
| 2026-09-21 | A summary described a standard error as a confidence interval. | Corrected. ±0.016R is the SE; the 95% interval is ±0.031R. |
| 2026-09-21 | The public FAQ still described the daily limit as measured against the day-start balance, said results were published monthly, and its disclaimer said the backtest had not been validated out of sample after it had. | All three sentences corrected the day the walk-forward was published. |

## Version

**v1.0 — 2026-09-21.** First public version. Material changes to method are logged here with a date.
