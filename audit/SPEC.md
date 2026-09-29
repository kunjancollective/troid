# Calculator audit, 29 Sep 2026 — the shared contract

This file pins down the handoff (HANDOFF-calculator-audit.md, 29 Sep 2026) precisely enough that the desk
(web/templates/index.html `render()`) and the independent audit (audit/model.py) could be written by different hands
from the same text and then compared: they were, in parallel, and on the first run they agreed on 2,290 of 2,292 checks.
The two that differed were this file's own ambiguity (F4's note, clarified below). A change here is a change to what
the audit holds the desk to: it needs the owner's review, like a change to the model.

Repo: kunjancollective/troid. Base commit 9c8d447 (main). Today is 2026-09-29 (ISO week 2026-W40).

## Inputs (desk field ids)

quota `q`, equity `eq`, daystart `ds`, hwm `H` (blank → none), hirollover `R` (blank → none), side `s` ∈ {+1, −1},
entry `E`, stop `S`, targetR `tR`, riskPct `rp`, capPct `cp`, lev `L`, mode ∈ {cross, isolated}.
A blank or unparseable number reads as 0 (the desk's `n()`), and for H and R, 0 means "none" (use the default).

Firm rules per product (firms.json → the desk's FIRMS): daily % `d`, max % `m`, daily basis, drawdown type
(`static` | `trailing` | null = pending), `locks` (lock at initial after +locks%), `hwm` basis (`equity` | `balance`),
fee per side % (null = pending → 0 in the arithmetic, "pending" shown), leverage cap `lev` or bands `levb`
[{max_quota?, min_quota?, lev}]. MMR = 0.005 (troid's assumption).

## F2. Input bounds (checked first)

BLOCK, naming each field out of range, when any of:
- q ≤ 0                      → "Quota must be more than 0"            (key index.js.b_gt0 = "{field} must be more than 0")
- rp ≤ 0 or rp > 100         → "Risk % must be more than 0 and at most 100"   (index.js.b_pct = "{field} must be more than 0 and at most 100")
- cp ≤ 0 or cp > 100         → "Budget cap % must be more than 0 and at most 100"
- L < 1                      → "Leverage must be at least 1"           (index.js.b_lev = "{field} must be at least 1")
- E ≤ 0 (only when the entry field is not empty) → "Entry must be more than 0"
- S ≤ 0 (only when the stop field is not empty)  → "Stop must be more than 0"
`{field}` is the field's own label (index.calc.quota "Quota", .risk_pct "Risk %", .cap_pct "Budget cap %",
.leverage "Leverage", .entry "Entry", .stop "Stop"). A range error makes the verdict BLOCK in every state (also with
no entry yet); the verdict sentence lists the reasons (index.js.vs_block "Can't be sized: {reasons}."), joined by "; ".
When entry and stop are both present, the existing reasons (stop on the wrong side, zero distance, breached) are added.
HTML: riskPct and capPct get min="0" max="100"; lev min="1"; quota, entry, stop min="0" (HTML min is inclusive;
render() excludes 0). desklink.js: a link value out of these bounds counts as unreadable (`bad`) and the input keeps
its default — keys q, en, st > 0; rp, cp in (0, 100]; lv ≥ 1.

## F4. High-water mark and high at rollover

hwm = H if H > 0 else max(eq, q); then hwm = max(hwm, q); and when the product's hwm basis is "equity",
hwm = max(hwm, eq). When the typed H was raised, a note says so:
- index.js.n_hwm_raised = "high-water mark raised from {typed} to {hwm}: it can't be below the quota"
- index.js.n_hwm_raised_equity = "high-water mark raised from {typed} to {hwm}: this firm trails on equity, so it can't be below your equity"
(the note names the bound that set the value: the equity one only when the mark was raised to the equity — below both
the quota and an equity under it, the mark is the quota and so is its note; typed and hwm formatted as dollars).
Clarified 2026-09-29, before any audit was published: the first text said "when both apply, the equity one", which the
desk read as the bound that set the value and the model read as the typed value being below both.
hi = R if R > 0 else ds; then hi = max(hi, ds) (the high at rollover is the higher of balance and equity at the
rollover, and the day-start balance is that balance, so it can't be below it). Note when raised:
- index.js.n_hi_raised = "high at rollover raised from {typed} to {hi}: it can't be below the day start"

## Floors and budgets (unchanged except F3)

daily floor dF: basis `initial` → ds − d·q; `day_start` → ds·(1 − d); `max_balance_equity` → hi − d·q; else pending.
max-loss floor ddF: `static` → q·(1 − m); `trailing` → locked = locks ≠ null and hwm ≥ q·(1 + locks/100);
ddF = q if locked else hwm − m·q.
**F3**: drawdown type null (pending) with m known → ddF = q·(1 − m), the loosest reading (a trailing floor is never
lower than the static one). Working-table formula index.js.f_dd_loosest = "quota × (1 − {m}%): the loosest reading,
drawdown type pending"; note index.js.n_dd_loosest = "drawdown type pending — sized against the loosest reading of
the {m}% max loss; a trailing floor would be tighter". The rule "max {m}%" counts as used (provenance), the drawdown
type does not (it is pending, not unsourced). The label is the plain max-loss floor (index.js.dd_floor).
dB = eq − dF, ddB = eq − ddF; eff = min of those known; binding = daily when dB ≤ ddB, else max drawdown.

## Existing blocks (unchanged)

long and S ≥ E; short and S ≤ E; dist = |E − S| ≤ 0; eff ≤ 0 (breached).

## Sizing

intended = rp/100 · eq; cap = cp/100 · max(eff, 0); riskB = min(intended, cap)   ← working row "risk" (index.js.risk)
f = fee/100 (0 when pending)
**F6** fee per unit fu = f · (E + S)   (the exit fee priced at the stop, the way an exchange charges it)
      index.js.f_fpu = "(entry + stop) × {fee}%"
      index.js.f_size = "size = min(equity × {risk}%, room × {cap}%) ÷ (stop distance + (entry + stop) × {fee}%)"
qty0 = riskB / (dist + fu)
leverage used: cap = the product's `lev`, or the band covering q; levUsed = min(L, cap).
**D6** bands exist but none covers q (CFT between $25k and $50k): levUsed = min(L, the LOWEST band lev) (5×), and say so:
      index.js.n_lev_held = "leverage held to {lev}×, the lowest cap this firm records"
      index.js.f_lev_pending_held = "your leverage; cap pending (held to {lev}×, the lowest cap recorded for this firm)"
no cap and no bands (pending): levUsed = L.
margin0 = qty0 · E / levUsed
**F1** if margin0 > eq + 1e-9: qty = eq · levUsed / E (the size is cut to fit the margin), else qty = qty0.
notional = qty · E; margin = notional / levUsed; fees = qty · fu
loss at the stop, `loss` = qty · (dist + fu)  (= riskB exactly unless F1 cut it)
fee share = fees / loss · 100
budget used = loss / eff · 100
**F7** losses left = ceil(eff / loss − 1e-9) − 1   (losses that leave equity above the floor; firms word a breach as
      reaching the limit). index.js.f_left = "ceil(budget ÷ risk) − 1"; glossary.left.formula = "ceil(room ÷ risk) − 1".
target = E + s · tR · dist
verdict: REDUCE when riskB < intended − 1e-9 or F1 cut the size; else OK.
F1 verdict sentence (when F1 cut, whatever else): index.js.vs_margin = "Cut to fit the margin: at {lev}× the account
carries at most {max} notional, so this trade risks {risk}." ({max} = eq · levUsed, {risk} = loss, dollars).

## Working table ("show the working", `#result details.work tr`, three cells: label, formula, value)

Existing labels keep their keys and English text. Rows the audit reads, by i18n key (English label):
- index.js.daily_floor "daily floor" → dF · index.js.dd_floor "max-loss floor" → ddF
- index.js.st_daily_budget "daily budget" → dB · index.js.st_dd_budget "drawdown budget" → ddB
- index.js.st_intended "intended risk" → intended · index.js.st_cap "cap" → cap · index.js.risk "risk" → riskB
- index.js.st_dist "stop distance" → "dist (pct%)"
- index.js.st_fpu "fee per unit" → fu · index.js.st_qty "quantity" → qty (final) · index.js.st_notional "notional"
- index.js.st_lev_used "leverage used" → "levUsed×" · index.js.margin "margin" → margin (final)
- NEW index.js.st_margin_check "margin check" → value $(margin0); formula index.js.f_margin_fits = "margin at the
  risk-based size ≤ equity" or index.js.f_margin_cut = "margin at the risk-based size > equity: size cut to equity ×
  {lev}× ÷ entry". Row present on every sized trade, placed right after "margin".
- index.js.fees "fees" → "$fees ($share of risk)" (value before the parenthesis)
- NEW index.js.st_loss "loss at the stop" → $(loss); formula index.js.f_loss = "quantity × (stop distance + fee per
  unit)". Row present on every sized trade, placed right after "fees" (or where fees would be when fee pending).
- index.js.budget_used "budget used" → "x.x%" · index.js.st_left "losses left" → left
- index.js.st_target "target" · index.js.st_daily_dist "daily-limit distance" → dB/notional·100 %
- index.js.st_dd_dist "max-loss floor distance" / index.js.st_trailing_dist "trailing floor distance" → ddB/notional·100 %
- "exchange liq (cross|isolated)" (index.js.br_liq) → see F5
- When quantity was cut (F1), the quantity row's formula is index.js.f_qty_margin = "equity × leverage used ÷ entry:
  cut to fit the margin".

## F5. Liquidation

mB = 1/levUsed (isolated) or eq/notional (cross); liq = (mB − MMR) / (1 − s·MMR) · 100.
Display: liq ≤ 0 → the existing "0.00% — below maintenance at entry" (index.js.v_liq_below).
A LONG (s = +1) with liq ≥ 100 − 1e-9 → index.js.v_liq_none = "none above zero" — in the working-table value, in the
breakers line (in place of the percentage), in the ladder (desk2.js), and the readout note: for isolated,
index.js.n_isolated_none = "isolated at {lev}×: no liquidation above zero — the position's own margin covers a fall to
zero" in place of n_isolated; for cross the cross note is unchanged. The glossary live line for liq is hidden in that
case. Shorts are shown as computed (they can exceed 100%).

## Readout cells

The "risk" cell shows `loss`; size shows qty; margin shows margin; fee share as today. The gauge gets risk = loss,
intended = intended, reduced = (verdict REDUCE).

## Things that do NOT change

Daily floors, the binding tie-break (dB ≤ ddB → daily), the circuit-breaker ordering, isolated/cross formulas,
MMR 0.5%, the compare's "losses before max loss binds", ask troid's tools (they follow via the candidate process).

## The audit's output (audit/run.py)

web/public/audit.json:
{"date": "YYYY-MM-DD" (UTC run date), "week": "YYYY-Www", "commit": "<40-hex of the audited tree>",
 "checks": N, "passed": P, "failed": F, "report": "audit/reports/YYYY-Www.md",
 "pages": ["/", "/ar"], "cases": C, "seed": "YYYY-Www", "rules_read": {"from": "YYYY-MM-DD", "to": "YYYY-MM-DD"},
 "stale_rules": [...], "unsourced_rules": [...]}
checks = passed + failed. A "check" is one case on one page (all of its figures and its verdict), plus each data check
(FIRMS vs firms.json per product, provenance coverage per product).

The desk shows, under the result (a sibling after #result in web/templates/partials/_desk2.html, filled at run time
by a small web/public/audit.js from /audit.json, hidden when it can't load or site.json "calc_audit" is false):
- passed: desk2.audit.pass = "Calculators audited {date} · {n} checks passed · <a href=\"{href}\">report</a>"
- failed: desk2.audit.fail = "Calculators audited {date} · found {n} mismatches · <a href=\"{href}\">report</a>"
  ({date} like "4 Oct 2026", Intl en-GB in English, the page's intl locale elsewhere; {href} =
  https://github.com/kunjancollective/troid/blob/main/<report>)
- and, on its own line, desk2.audit.rules = "Rules read {range}" (e.g. "18–23 Sep 2026"), from firms.json's read
  dates of the rules the desk uses, written at build time as ISO dates and formatted by audit.js.
Past 8 days old the line shows its date as is (no special wording).
