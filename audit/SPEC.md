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

## Changes after the review, 2026-09-30

The desk was reviewed after the audit's first run; these rules change what the desk shows, so the model follows them
from here, not from the desk's code. The owner reviewed and approved R1–R8 and the F4 clarification on 30 Sep 2026,
R5 included (a 100% cap whose loss lands on the floor is a BLOCK). Each rule names its
i18n keys (English text in quotes). Where a rule below and an earlier section differ, the rule below holds.

**R1. Equity and day start are bounded (extends F2).** Two more reasons, in this order among F2's: quota, equity, day
start, risk %, budget cap %, leverage, entry, stop.
- eq ≤ 0 → "Equity must be more than 0" (index.js.b_gt0, field index.calc.equity "Equity")
- ds ≤ 0 → "Day start must be more than 0" (index.js.b_gt0, field index.calc.daystart "Day start")
A blank field reads as 0 and is refused (a blank day start used to drop the daily limit silently: dF = −d·q). The
account card st-account is flagged. HTML: equity and daystart get min="0". desklink.js: keys e and ds must be > 0.
hwm and hirollover are unchanged (0 there means "none").

**R2. An account out of range computes nothing from it (F2).** When q ≤ 0, eq ≤ 0 or ds ≤ 0: no floor, budget, binding
or size is computed. Verdict BLOCK, sentence index.js.vs_block with every range reason (R1's order, joined by "; "),
and no other reason (no stop-side reason, never index.js.b_breached); the notes are the reasons; the working table is
the three index.js.st_inputs rows only; no provenance block; no link row (R4). The gauge draws no floor: its line is
desk2.js.g_line_block and its aria-label is that line alone. With a tapped stock no firm lists, the readout is R3's.
Elsewhere (the account in range) index.js.b_breached can no longer come from a refused quota.

**R3. A tapped stock no firm lists, with a field out of range (F2).** The readout stays desk2.js.tape_none (nothing is
sized for the stock, whatever is typed) and the range reasons follow it as notes, before the account's own notes. No
verdict. The gauge is BLOCK (desk2.js.g_line_block, the reasons) when there is a range reason, EMPTY otherwise; when
the product records neither floor, the gauge stays PENDING and the reasons still follow the readout.

**R4. Links and range errors.** The copy-link row (index.js.share_copy) is left out of every result that has a range
reason (F2 and R1), since a link can't carry the refused value and would open as another result. Every other BLOCK
(stop on the wrong side, zero distance, breached, R5) keeps it, as do SET, OK, REDUCE and the pending BLOCK without a
range reason. desklink.js decode(): a number outside the bounds keeps the input's default and is counted in `out`
(the input ids, in the link's order), not in `bad`; `bad` counts only malformed values. The notice adds
index.js.shared_range = "Values in the link outside the desk's bounds ({fields}) were left at the desk's defaults."
with {fields} the fields' labels (index.calc.*) joined by index.js.list_comma, before index.js.shared_bad.

**R5. A loss that takes the whole room is refused (F7).** After loss and left are computed: when left < 1 (that is,
ceil(eff / loss − 1e-9) − 1 ≤ 0, reached only at a 100% cap with intended ≥ eff), BLOCK with the reason
index.js.b_reaches = "a loss at this stop would take the whole room and reach the {bind}, which fails the account —
set the budget cap below 100%" ({bind} = the binding label, index.js.bind_daily or bind_dd). The sentence is
index.js.vs_block; the notes are the reason; the working table is the inputs, floors, budgets and binding rows (as every
BLOCK); the provenance block without the size formula; the link row kept; the risk card st-risk flagged. The F2 bound
cp ≤ 100 is unchanged. The handoff's F3 case (CFT Instant, 2% at a 100% cap, room $100) is now this BLOCK.

**R6. A long's floor distances at or past 100% (extends F5).** For s = +1: dP = dB / notional · 100 and
ddP = ddB / notional · 100. When one is ≥ 100 − 1e-9 its value is index.js.v_floor_none = "not reached above zero — a
fall to zero stays inside it", in place of the percentage: in the working table (index.js.st_daily_dist, st_dd_dist or
st_trailing_dist), in the breakers line, and as the ladder's 4th item; it sorts after every finite distance. That
term's glossary live line (daily or floor) is hidden. Shorts are shown as computed, as before.

**R7. The loosest reading, everywhere the floor's formula is shown (extends F3).** In F3's case the max-loss floor's
formula is index.js.f_dd_loosest in the working table (as before), in the explainer's floors step and in the floor's
glossary live line {formula}. The room's provenance formula (index.js.f_room_both / f_room_dd) keeps f_dd_static. The
explainer's crossover step for any product whose drawdown type is null is desk2.js.x3_pending = "On {product} troid has
not recorded the drawdown type, so no crossover is shown." in place of x3_none.

**R8. A margin cut, everywhere the risk is described (extends F1).** When F1 cut the size:
- The budget-cap note, when riskB < intended too: index.js.n_cut_margin = "cut from {from} to {to} — {bind} budget caps
  it; the margin then cut it to {loss}" ({from} = intended, {to} = riskB, {loss} = loss) in place of index.js.n_cut.
- The risk term's live line: index.js.gx_risk_cut = "the smaller of {intended} and {cap}: {rb}; the margin then cut the
  size to fit at {lev}×, so the trade risks {risk}." ({rb} = riskB, {lev} = levUsed, {risk} = loss) in place of
  glossary.risk.live.
- The provenance formula ends "; " + index.js.f_margin_cut with {lev} = levUsed, after the size formula.
- The explainer: the size step shows `size = riskB ÷ (dist + fu) = qty0`, then desk2.js.x5_cut = "margin = {q0} ×
  {entry} ÷ {lev}× = {m0}, more than equity {eq}: size = {eq} × {lev}× ÷ {entry} = {qty}", then the fee share over the
  loss; the leverage step is desk2.js.x6_h_cut "Why leverage changes the loss here", x6_p_cut, and x6_code_cut = "at
  {lev}× the account carries at most {max} notional; the loss at the stop is {qty} × ({dist} + {fu}) = {risk}"
  ({max} = eq · levUsed, {risk} = loss) in place of x6_h, x6_p and x6_code ("… either way"), which stay for a trade
  the margin didn't cut.
- glossary.leverage.what = "How much position each dollar of margin controls. It changes margin and liquidation
  distance — not the loss at your stop, while the margin fits in your equity. When it doesn't, the size is cut to fit,
  and lower leverage means a smaller loss."

Not changed by the review, and left for the owner: the floor distances are budget ÷ notional, net of no fee (a fee-net
distance would put a 100% cap's daily limit on the stop exactly); R5 refuses that case instead.

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
