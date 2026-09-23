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
| 2026-09-22 | The journal recorded each closed trade's outcome but not its geometry: no entry, stop, take-profit or exit price, no risk in dollars, no binding ceiling. A trade could not be drawn or its sizing checked from the public file alone. | Schema widened by eleven columns (entry and average price, initial stop, take-profits, exit price, risk, binding ceiling and room at entry, fee share, tranche count). Every row re-derived from the same deterministic replay; the twelve original columns are byte-identical and every row keeps its original `logged_utc`. A widening, not a data change. The migration refuses to run if any original value would move. |
| 2026-09-22 | Shadow commits reached the repo but not the site. Vercel's Hobby plan rejected the workflow's commit identity (`shadow@troid.ai`, not a member of the Vercel team): all five shadow commits between 03:58 and 23:00 UTC were blocked. Two were carried to the site minutes later by commits made in the owner's name; the ledger on the site lagged the repo from 09:21 UTC on 22 Sep to 00:40 UTC on 23 Sep, about 15 hours. | Fixed by the repo going public: Vercel deploys a public repo's commits from any author. The first shadow commit after the change (23 Sep, 00:40 UTC) deployed, and the live ledger was byte-identical to the repo with its last bar matching the run. |
| 2026-09-23 | troid's desk capped Crypto Fund Trader's Instant accounts at 100× leverage, the Advanced-account cap. Instant accounts are $2.5k–$10k, inside the Student band, and the firm's recorded terms give Student accounts 1:5. Found while tracing every rule to its source. | Instant capped at 5×; the test that asserted 100× now asserts 5× for Instant and 100× for 1-Phase. Every computed number now shows the firm document, section and read date it came from, and says "source not yet recorded" where the repo has none. |

## Version

**v1.0 — 2026-09-21.** First public version. Material changes to method are logged here with a date.
