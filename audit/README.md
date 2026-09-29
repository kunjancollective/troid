# The calculator audit

troid's desk sizes a trade in the reader's browser. Once a week, and on every pull request that touches the desk,
an independent model re-derives every figure the desk shows and compares them, case by case, on the page as built.
The audit is not written by the thing it audits: the model reads `firms.json` and first principles, never the desk's
code (`render()` in `web/templates/index.html`, `web/public/desk2.js`, `backtest/regions.py`), and imports nothing of
the desk's or the generators'. (HANDOFF-calculator-audit, 29 Sep 2026.)

| file | what |
|---|---|
| `model.py` | The model: `rules(firm, product)` from `firms.json`, `model(firm, product, inputs)` for every figure. Seeded from the owner-reviewed `calc_audit_seed.py`; the changes the handoff's F1–F7 and D6 require are listed in its docstring. |
| `provenance.py` | Which rules the desk sizes with, the source `firms.json` records for each and the date troid read it: the report's unsourced, pending and stale lists, and the range the desk's "Rules read" line must show. |
| `cases.py` | The seed's 23 edge cases and a named regression for each fix, each pinned to figures worked by hand; the desk's grid (six rows) on every product it offers; 1,000 random cases seeded by the ISO week. |
| `run.py` | Serves the built site, drives the English desk and the right-to-left `/ar` (a draft preview built for the run) in Chromium, compares, runs the data checks, and writes `web/public/audit.json` and `reports/<week>.md`. |
| `reports/` | One report a week, committed with `audit.json` through a pull request the Sunday run opens (`.github/workflows/audit.yml`). |

## Running it

```bash
python3 audit/cases.py                         # the model against its pinned figures; no browser
python3 audit/run.py --no-write                # this ISO week's audit, printed; nothing written
python3 audit/run.py --week 2026-W40           # a week again, exactly; writes audit.json and reports/2026-W40.md
python3 audit/run.py --no-write --revert all   # diagnosis: the model with the seed's derivations
```

It needs Playwright's Chromium (`/opt/pw-browsers/chromium` where it exists, Playwright's own otherwise) and jinja2 for
the `/ar` preview. It exits 0 when every check passed, 1 on any mismatch, 2 when it couldn't run (the model misses a
pinned figure, or a page has no desk).

A check is one case on one page (its verdict and every figure it shows), plus each data check: the page's inline
`FIRMS` equals `firms.json` for every calc field of every product, and every rule the desk sizes with is cited with its
source in the provenance block, or named in "Source not yet recorded for …", as `firms.json` records it. The report
also lists the rules with no recorded source, the pending rules, and read dates older than 45 days.

Each mismatch is labelled with the handoff items that account for it: the smallest set of items whose earlier
(the seed's) derivation makes the page match. The label helps read a report; it never decides a check. `--revert`
runs the whole audit on those earlier derivations, to show the harness is otherwise clean; it writes nothing.

## Changing the model

A change to the model's derivations needs the owner's review, and a mismatch is never a reason for one. When the desk
and the model disagree, which is wrong is settled against the firm's documents and the handoff, not by editing
whichever is easier. When the desk changes on purpose, the handoff says how first, then the desk and the model follow
it separately, and the change is listed in the model's docstring with the item that requires it. A figure worked by
hand goes in `cases.py` as a pin, and `run.py` refuses to drive a page until the model meets every pin.

## On the desk

`web/public/audit.js` fills the line under the desk from `/audit.json`: "Calculators audited 4 Oct 2026 · 1,023 checks
passed · report", or "… found 2 mismatches · report", linked to the week's report on GitHub. The line is hidden when
the file is missing or doesn't hold together; an old audit shows its date as it is. "Rules read …" is a separate
claim, on its own line, written at build time from `firms.json`. `web/i18n/site.json` `calc_audit` takes both off the
page. Tests: `python web/test_audit_line.py`; `backtest/verify_claims.py` holds `audit.json` to its report and the
rules line to `firms.json`.
