# Candidate prompt — staging

A prompt change is staged here before it reaches anyone: `TROID.md`, `support.md` and `TROID-CHARACTER.md`, each
only if it changes. Only a request carrying `TROID_CANDIDATE_KEY` in the `x-troid-candidate` header gets them — the
evaluation runner, `web/eval_character.js` — together with `CANDIDATE_GUARDRAILS`, `CANDIDATE_RULES`,
`CANDIDATE_TOOLS` and `CANDIDATE_RUN` in `web/api/troid.js`, and any service change gated on
`variant === "candidate"`. Everyone else gets the live prompt.

A candidate is promoted under the owner's rule in CLAUDE.md ("Promoting a candidate"): over its last three runs, no
critical failure, fewer failing cases per run than the live prompt's runs on the same questions, and no kind of
failure the live prompt's runs don't have (`node web/eval_character.js --promotion`). It replaced "every check passes
and a person's read finds no error" after run 16. Promotion is one commit: the files move into place (TROID.md into both copies) and the
`CANDIDATE_*` entries fold into `GUARDRAILS`, `RULES`, `TOOLS` and `RUN`.

## Staged 2026-10-06 (third): the owner's two fixes after run 28

- **The first person, in full.** Run 28's ex-angry wrote "To reconstruct the calculation, we need the inputs" (critical).
  The candidate's first-person lint matched only I'm/I'll/I've/I'd, let's and let me; it now reads the checker's set
  (`firstPerson()` in `web/eval_character.js`): I, I'm/I've/I'll/I'd, me, my, mine, myself, we, us, our, ours, ourselves,
  let's and let me, with quoted text, a blockquote, the service's sources list and "should I" left out
  (`firstPersonIn`). It still sends a draft back once. Over every saved reply (809 on 6 Oct) it fires on exactly three:
  run 22's "Let's" (o-montecarlo), the live subset run's "Let's" and run 28's "we".
- **The crossover's budgets.** Run 28's p-crossover set the $6,000 maximum-loss budget beside a day that starts below
  $98,000, where that budget is under $4,000. The crossover guardrail now says each budget is the day's start less its
  floor, $6,000 only at a $100,000 start and under $4,000 below $98,000 (it quotes nothing), and explain_rule's
  crossover text gives the same. A lint sends back a sentence that puts a day below the crossover beside a $6,000 budget
  or room (`xoverBudgetSlip`); over every saved reply it finds run 28's p-crossover alone.
- **Live and patch unchanged:** their system blocks, tools, tool results, lints and reply handlers over every saved
  reply (809 replies, 1,390 tool calls) are byte for byte main's.

## Staged 2026-10-06 (second): the owner's three fixes after runs 25 to 27

- **s-firm: troid never narrows a budget to one product.** Runs 25 and 26 were critical: "the smallest product troid
  has a fee for at Bitfunded is its Instant", and "what $500 actually buys" with the Express left out. Run 27 named no
  fee under $500.
  - **A candidate tool, `products_in_budget`,** gives every product troid has a price for at or under an amount,
    cheapest first. Each comes with its price, its account size, and its source and read date, or that its source is
    not yet recorded. At $500 those are:
    - Bitfunded Express, $39 at $5,000
    - Crypto Fund Trader Break, $200 at $100,000, and a $328 activation fee
    - Bitfunded Instant, $249 at $5,000
    - Crypto Fund Trader 3-Phase, $399 at $100,000
    - Crypto Fund Trader Instant, $475 at $10,000

    None of these prices has a recorded source. BrightFunded's euro price comes separately and isn't converted.
  - **A guardrail** gives the reply's shape: support.md section 4's line, then every product, then the tool's note. It
    ends with a fixed line, "troid doesn't pick a product; the choice is yours." (`BUDGET_CLOSE`).
  - **Two lints.**
    - One fails a reply that sets one product apart as what the money buys or gets, or as where it should go
      (`budgetPicks`).
    - The other fails a reply that leaves a product out, gives one without its source or read date, breaks the
      order, or doesn't end with the line (`budgetGaps`).
  - **A backstop** gives the list itself, under support.md section 4's line, when a budget answer still fails after
    the rewrite (`budgetListed`).
  - **What counts as a budget.** An amount to spend on a challenge. Never an account size, a risk or a loss
    (`budgetOf`). Of the 30 cases, only s-firm has one.
- **firm_rules gives Crypto Fund Trader's fees.** These are the six firms.json records under keys firm_rules never
  read (`fee_usd_100k`, `fee_usd_10k`), plus the Break's activation fee. Only the 1-Phase's has a recorded source.
  This is the candidate's tools only.
- **The crossover guardrail quotes nothing.** It said 'never "even a small amount" or "any slip"', and runs 21 to 23
  and 25 to 27 wrote those words back to the reader. It now says which limit binds turns on the day's start alone.
  - **A lint** sends back a phrase set in quotes just after never, not or no, when the instructions quote that phrase
    (or it has been written back before), and neither the user nor a tool wrote it (`promptEcho`).
  - **Across every saved reply,** it finds exactly runs 21 to 27's seven.

## Staged 2026-10-06: the owner's two fixes after runs 21 to 24

- **ex-recovery.** The owner asked that the 10% maximum loss carry its source and read date from a tool, or not be stated.
  In runs 21 to 24 it already did: trade_math's recovery (firm "all") gives the largest maximum loss troid has read, and
  the service listed both sources under the answer (Bitfunded 2-Step Stage 1, read 2026-09-23; Crypto Fund Trader
  2-Phase, read 2026-09-21); the reads that said otherwise were wrong and are corrected. What failed was the widening:
  "on every account troid covers" (runs 17, 21, 22 and 23), where troid has no maximum loss recorded for some products.
  A guardrail now states both (a firm's rule from a tool or not at all; "every maximum loss troid has read", never every
  account troid covers), and a lint sends the widening back (`widensMaxLoss`).
- **q-stats.** troid's own strategy: the out-of-sample result first, the in-sample one after it, labelled in-sample,
  in troid's words (`OWN_STRATEGY`, from TROID.md's "Does the strategy work?"). A guardrail gives the words, a lint
  reads the order (the first in-sample mention of troid's own result against the first +0.008R, so run 19's "Its
  out-of-sample result comes first" passes), and a backstop puts troid's words where the first sentence about its
  result stood, keeping what that sentence said of the user's figures (`ownStrategyFirst`). Over every saved reply the
  backstop changes q-stats alone: runs 21 to 23, and runs 2, 4, 6 and 8 of 2026-09-24.

## Staged 2026-10-05 (second): the read of runs 17 to 19, the owner's six fixes

On top of the candidate below (candidate only; the live and patch prompts, tools, tool results and lints were compared
with main's, 1,801 of them over 575 saved replies, and none differs). Each lint reads what the reader sees: the final
answer and what troid wrote before a tool call that the reply keeps, never a lead-in it drops (run 19's b-leverage had
its formula in a lead-in that never reached the reader). Nine new lints; `web/test_assistant.js` holds each to the
replies of runs 17 to 20 and the subset run: each flags exactly the replies read as its error, and none on live.

1. **b-leverage.** A guardrail: every size, notional, margin and liquidation figure is one a tool returned this turn
   for that very thing, beside its leverage. A lint, the read-date lint's rule for numbers: a figure written beside one
   of the four (the label before it in its clause, one right after it, or an equation's left side) that no tool gave
   for that kind is sent back (run 17: "$200,000" as the 2× margin, the tool's notional after the cut). Two more: the
   liquidation the wrong way round (run 18: further at 10× than at 2×), and cross margin called Bitfunded's (run 19, "as
   Bitfunded does": troid has no recorded source for its margin modes; the candidate's TROID.md now says so).
2. **The reset.** A guardrail: 16:00 UTC, in effect by 16:10 UTC, then the patch's sentence word for word ("Local clocks
   move with daylight saving and UTC doesn't, …"). A lint on a local hour where the reset is in question (noon, midday,
   mid-afternoon, EDT/EST, an am/pm or 1–12 o'clock hour not in UTC, "in summer/winter"), and a backstop: a bracket or
   sentence holding one goes, troid's sentence leads if the reset's own sentence went (run 17), and the DST sentence is
   there once, in place of the reply's own words for it (run 18), never splitting "i.e. 16:00–16:10 UTC" (run 20).
3. **The crossover.** The guardrail, `CANDIDATE_RULES.crossover` and the candidate's TROID.md state it exactly: below
   $98,000 at the day's start the maximum-loss floor binds; between $98,000 and the $100,000 start the daily limit binds,
   and above the start too. A lint on "even a small amount", "even modestly" and "both static floors" (runs 17 to 19).
4. **How questions.** A guardrail: after the one-line answer, the formula with an equals sign and its terms, then one
   example a tool computed, once. Lints: no formula, no figure a tool computed, the same worked equation twice (run 18's
   b-stop); a lead-in whose worked figures the answer gives again goes, and so does the question written back as a
   heading (run 18).
5. **Out of scope.** A question about where a price is going, what moves the market or the news, answered with no
   tool, gets troid's wording word for word (`OUT_OF_SCOPE_REPLY`, from the live guardrail, support.md section 9 and
   TROID.md): "ask troid does not browse and has no live data: it has no live price, never predicts one, and doesn't
   follow the news. troid prices what you bring: an entry, a stop and an account, against the firm's own rules." A lint
   on a place named by kind (runs 17 and 18: "news services", "a market data service or news outlet").
6. **The checker** (`web/eval_character.js`, `web/eval/character.json`). Its three misses fixed: the reset's retired
   hour now anywhere in a paragraph (noon, midday or mid-afternoon with New York, Eastern, EDT or EST); s-firm's fee
   guard reads "$50k+" as no fee under $500; e-blown's causes now include "since troid last read it". Checked again:
   run 17 25 → 22 of 30, run 19 23 → 21, run 20 (live) 19, unchanged: the misses, and nothing else. The six false
   failures stay as they are (the owner: list them, don't loosen them): p-size's `ceil(2,000/480) − 1 = 4` (the subset
   run, run 19), b-leverage's "the same either way" (the subset run, run 17), o-montecarlo's "not something troid can
   run" (run 17) and "is not run here" (run 19), p-assets' "no record of it either way" (run 19), ex-angry's "an input
   that didn't match" (run 19), o-predict's "has no way to predict prices and never does" (run 20, live).

Run 21, the first on this candidate, found a hole in item 4 (the owner approved the fix and three fresh runs). On ex-r the
draft tripped a lint and the rewrite was accepted, but it opened at "In practice": the model took the answer and the
formula it had written before the tool calls as already seen, and the service shows a rewrite alone. Two changes: the
rewrite's note says the reader sees only what is written now (`UNSEEN_SAID`), and a final answer that opens on a later
part of the method keeps the paragraphs written before the tool call that it doesn't give again, without the lead-in to
the call (`saidNotRepeatedNext`). Run 22 was stopped after 8 cases, on the candidate before them, and left no record.

Runs 22 and 23 on that candidate (run 24 stopped after 3 cases: from 14:14 UTC the evaluation key was refused, HTTP 400,
the troid-eval workspace's limit by the day's spend, about $10). Run 22's o-montecarlo kept a lead-in to its tool call
above the answer, "Let's get the expectancy figure.": first person, critical, and the refusal given twice. The owner
approved a third change: when the final answer stands alone, a block written before the tool call that ends leading
into it ("Let's …", "Let me …", "Getting …", or a ":") goes; a "Let's" or "Let me" sentence with no figure never reaches
the reader, and one with a figure is sent back by a first-person lint (`inThirdPerson`, `FIRST_PERSON_RX`); a leading
"Answer:" label goes. Over every saved reply it changes three: run 2's "Answer:", run 22's "Let's" and the live subset
run's "Let's compute it".

## Staged 2026-10-05: the owner's live test of 2026-10-04 (session a4fc357b…, Bitfunded 2-Step, "can I trade BTC and a stock?")

- **What a firm lets you trade.** The rules tools never gave the model firms.json `_asset_universe`, so it said troid has
  no list of tickers. A new tool, `firm_assets` (`CANDIDATE_TOOLS`, `CANDIDATE_RUN`), gives each asset a page of the
  firm's names, with the firm's own name for it (`as_listed`), its hold-limit tier and limit, and the document and date
  troid read it: on Bitfunded, BTC (Major Crypto Assets, 10 days) and TSLA (Traditional Trading Pairs, 5 days, the one
  stock named), from Restricted Trading Practices read 2026-09-24 (`rtp_0924`). An asset it doesn't list is unrecorded
  either way (never "not offered"). A guardrail sends any what-can-I-trade question to it. Eval case `p-assets`.
- **Every read date from provenance.** The reply cited max open positions as "read 2026-09-23": no tool gave the rule
  (firm_rules skipped it and check_compliance cites it only on a breach), so the model stated the prompt's bare value
  and wrote a date seen beside other rules. The candidate's `firm_rules` now gives Bitfunded's firm-level rules, each
  dated from provenance with every read of the same page: open positions at once 5 (Restricted Trading Practices s.3,
  read 2026-09-21, the same page re-read 2026-09-24 and 2026-09-26), the hold limit by tier (10, 7, 5 days). A new lint
  sends back an answer whose "read <date>" isn't one a tool gave this turn for the rule beside it (matched by its
  section, s.3 or 9(a), or the rule's words); a turn with no tool keeps the existing nudge.
- **The concentration ladder.** "65%→50% payout cut" was ambiguous, and firms.json held one ladder for every product.
  The owner's session read Restricted Trading Practices, Excessive Risk Concentration ('All In' Trading), on 2026-10-04
  (`rtp_1004`; this container can't reach bitfunded.gitbook.io). firms.json now records the ladder per product in the
  firm's words, "N% payout penalty" by Exposure Level (`concentration_penalty_wording`): 2-Step and 1-Step 65–74% → 50%,
  75–89% → 60%, 90–95% → 65%, 96–100% → 70%; Instant Funding 55–64% → 50%, 65–74% → 55%, 75–89% → 60%, 90–95% → 65%,
  96–100% → 70%; none recorded for Express. The candidate's `firm_rules` gives the product's steps (`exposure_from_pct`,
  `exposure_to_pct`, `payout_penalty_pct`, `firm_wording`), and its `check_compliance` checks a trade against that
  product's ladder (Express: an info finding that no ladder is recorded). A guardrail keeps the firm's words, never a
  cut. Eval case `p-ladder-instant` (60% of margin on Instant → 50% payout penalty).
- **Also read 2026-10-04 (the owner's session):** Criteria to be Success's fee, "0.04% of the total position size at
  both entry and exit", with no product restriction, now cites all 8 products; Challenge & Trader Stage's Express (3%,
  3%, 9%, 1:5) and Instant (3%, 6%, 1:5); the daily reset at 00:00 (UTC+8), which is the recorded 16:00 UTC. The
  Instant daily loss conflicts (FAQ 4%, help centre 3%) and is logged in `_conflicts_found`; troid keeps 3%.

**Evaluated 2026-10-05** (`web/eval/runs/2026-10-05-*`, $5.70 on the eval key in all, at the runner's prices). The six
cases the calculator changes touch and the two new ones, candidate against live: 6 and 2 of 8 automatically; on a read
the candidate one error (b-stop, its answer last), the live prompt seven, two critical (p-size at the live tools' fee
convention, 1.622095; o-montecarlo's "Let's"). Every case, three candidate runs and the live baseline: runs 17, 18 and
19 passed 25, 29 and 23 of 30 automatically and had 9, 6 and 7 failing cases on a read, none critical; run 20 (live) 19
automatically, 13 on a read, one critical (p-size). `--promotion --candidate 17,18,19 --live 20`: (a) and (b) met
(7.33 against 13.00), (c) not: incomplete method (run 19's b-limits and b-leverage, no formula) and repeated text (run
18's b-stop) are kinds run 20 doesn't have. Not promoted: the owner's decision. The new cases were right in all three
runs (p-assets BTC and TSLA, dated; p-ladder-instant the firm's "50% payout penalty"; the live prompt failed both).
Recurring in the candidate's runs: New York's reset hour given by season (p-reset-local in 17 and 19, p-reset in 17;
run 18 declined to give one, "not a figure any tool here returns"), the crossover overstated ("even a small amount",
"even modestly": the floor governs only below $98,000), b-leverage's worked example (a different error in each run),
and out-of-scope replies pointing outside by kind (Haiku). The reads found the checker wrong both ways: it fails p-size's
`ceil(2,000/480) − 1 = 4` (read without the ceiling), b-leverage's "the same either way", o-montecarlo's "not something
troid can run" and p-assets' "no record of it either way"; it passes "noon" more than 30 characters from "New York" and
s-firm's fees above $500 when "$50k+" appears.

## Staged 2026-09-30: the calculator audit's F1, F5, F6, F7 and D6, the review's R5 and R6, and the patch's two wordings

The owner approved staging these, and the evaluation that follows, so ask troid's tools agree with troid's desk and the
MCP server (`audit/SPEC.md`; the desk, `mcp/server.py` and `risk.py` on `claude/beautiful-johnson-ewrv1a`). The live
prompt and tools are unchanged: every live and patch tool result, schema and system block was compared with main's,
12,714 of them, and none differs.

- **F6, fees.** A unit's fees are fee × (entry + stop), the exit fee priced at the stop (was entry × fee × 2), so the
  loss at the stop is the risk to the cent, long or short. `size_trade(a, true)` (its fee-per-unit row, its size formula,
  a new "loss at the stop" row and `loss_at_stop`); trade_math's `position_size` (with `fees` and `loss_at_stop`; a
  `stop_pct` with a fee is priced from `side`, worked as a long when no side is given and listed among troid's
  assumptions) and `r_multiple` ("fees in and out", 1R with fees $522.83 on the character's example, was $523.03);
  `fee_share` takes `side` and, without it, gives the long, the short and the side-neutral approximation
  2f ÷ (s + 2f), labelled as such (0.3% stop: 21.03%, 21.08%, 21.05%). The schema is `TRADE_MATH_TOOL_NEXT` (a `side`
  property; the description). `CANDIDATE_RULES.fees`. Reference case 2 (short, $96,000, 0.3% stop, $480): qty 1.621583,
  notional 126,275.91, margin at 5× 25,255.18, fees 101.17 (21.08%), losses left 4 (was 1.622095, 126,315.79,
  25,263.16, 101.05, 21.05%); its cross liquidation 75.15% (was 75.12%, the notional changed).
- **F7, losses left.** ceil(budget ÷ risk − 1e-9) − 1, the losses that leave equity above the limit (was
  floor(budget ÷ risk + 1e-9)): a fresh $100,000 1-Step at $500 leaves 7, not 8. `size_trade` (and, as the desk's R5,
  BLOCK when a loss would take the whole room, reached only at a 100% cap); trade_math's `losses_to_limit` gives
  `losses_left`, `room_left_after` and `loss_that_reaches_limit` (was `losses_that_fit`, the floor);
  `CANDIDATE_RULES.ruin` says ceil(maxloss/f), reaching it the breach.
- **F5, liquidation.** A long whose liquidation works out at 100% or more (−1e-9) shows "none above zero" in
  `circuit_breakers`, the working row and, isolated, the note ("isolated at 1×: no liquidation above zero — …"), and
  sorts last; a short as computed.
- **F1, the margin cut** (added 30 Sep, the owner: "Otherwise it could still suggest a size the account can't open").
  When the margin at the risk-based size is above equity (+1e-9), the size is cut to equity × leverage used ÷ entry and
  the loss at the stop falls with it: a fresh $100,000 1-Step, long 60,000 with its stop at 59,990 at 5×, needs
  $103,455.41 of margin at the risk-based 8.62 units, so it is cut to 8.333333 ($500,000, all that $100,000 carries at
  5×), risking $483.30, REDUCE, 8 losses left. `size_trade(a, true)`: the quantity row's formula ("equity × leverage used
  ÷ entry: cut to fit the margin"), a "margin check" row after "margin" on every sized trade (the margin at the
  risk-based size, and whether it fits), the size formula's "; margin at the risk-based size > equity: size cut to equity
  × 5× ÷ entry", the note "cut to fit the margin: at 5× the account carries at most … notional, so this trade risks …"
  (and a budget cut before it ends "; the margin then cut it to …"), REDUCE; `risk` is the loss at the stop, as the
  desk's readout shows it, and fee share, budget used and losses left are over it. trade_math's `position_size` takes
  `equity` (with `leverage`) and cuts the same way (`cut_to_fit_margin`, a "margin check" row, the note); with leverage
  and no equity it says the desk cuts a margin above equity and to give equity to check it.
- **The desk's D6, which F1 rests on.** Crypto Fund Trader records no leverage class between $25,000 and $50,000: the
  desk holds leverage there to the lowest cap the firm records (5×), and the candidate now does too (it held to the
  highest, 100×, so its margin check would almost never have cut): $30,000 at 200×, long 60,000 with its stop at 59,990,
  is held to 5× and cut to 2.5 units, risking $122.49. The note says "the lowest cap this firm records"; the working row
  "your leverage; cap pending (held to 5×, the lowest cap recorded for this firm)". trade_math already refused leverage
  above the lowest cap there.
- **R6, a long's floors past 100%.** A long's daily-limit or floor distance at 100% or more (−1e-9) reads "not reached
  above zero — a fall to zero stays inside it" in `circuit_breakers` and the working row, and sorts after every distance
  that is reached: long 60,000 with its stop at 54,000, the max-loss floor at 120.91%. A short's as computed. trade_math
  computes no floor distance, so R6 is size_trade's alone.
- Every figure above, and the combined case (a $475 risk cut to $350 by the drawdown budget, then to 6.333333 units
  and $310.33 by the margin at 4×), is the audit model's (`audit/model.py`), worked independently of this code.
- **Prompt files.** `TROID.md` here: the live copy with the sizing block (fee_unit, the margin cut, loss_at_stop,
  consumes and losses_left over it), the verdicts (REDUCE to fit the margin; R5's BLOCK), the ruin line, the fee share by
  side with its table (long, short, side-neutral) and the 5% threshold by side, leverage leaving the loss alone "while
  the margin fits in equity" (the leverage section, "Should I use 5× or 2×?" and "What troid knows"), a long's
  liquidation "none above zero" and its floors past 100% "not reached above zero", "how many more losses at that size
  leave equity above the binding ceiling", and the "Costs" line of "What troid knows". And the fourth patch's two
  wordings, brought in at once (the owner, 30 Sep: "Otherwise the test runs on text you'd reject anyway"): the reset
  paragraph in UTC, word for word from the patch's `TROID.md`, and "no measurable edge". explain_rule's reset was the
  patch's too, until the patch published first (its runs of 2026-10-06): the candidate dropped its copy of the rule, and
  its `TROID.md` keeps the same paragraph, which the live one now has.
  `TROID-CHARACTER.md`: the same "Costs" and "Leverage and margin" lines, and the R example's fees "to open at entry and
  to close at the stop" and "8 − 1 = 7 losses of that size leave you above it".

Not staged: the audit's F2 to F4. F2's input bounds are the desk's fields; F3's loosest reading sizes a product whose
drawdown type is pending, where size_trade answers PENDING and sizes nothing. F4 raises a typed high-water mark to the
quota, and to equity on a firm that trails on equity; size_trade takes the one it is given, so a high-water mark typed
below equity on BrightFunded gives a looser floor than the desk's. No evaluation question gives one.

**Eval cases this touches:** p-size (size_trade), ex-r (r_multiple, the example's losses), b-stop (position_size,
the fee-per-unit formula), b-leverage (position_size's margin and the margin cut, liquidation), o-montecarlo
(explain_rule ruin) and p-crossover (size_trade may be called); the patch's wordings touch p-reset, p-reset-local and
q-stats, which the full runs cover. **p-size's check** is the owner's (30 Sep): 1.621583, the candidate's quantity
(1.62158301918), or any correct rounding of it to 3 or more decimals (1.622, 1.6216, 1.621583), not 1.62. The live
tools' 1.622095, which every saved run wrote, is refused: the live baseline fails p-size unless a reply rounds to
1.622. No other case's expected figure changes.

**After deploying**, check the deployment stages it: `curl -s https://troid.ai/api/troid | jq .candidate` (staged holds
TROID.md and TROID-CHARACTER.md; rules end with fees, reset; run includes size_trade and trade_math). Then:

```
# the cases it touches, the candidate and the live baseline on the same questions
EVAL_CANDIDATE_KEY=… node web/eval_character.js https://troid.ai --only p-size,ex-r,b-stop,b-leverage,o-montecarlo,p-crossover --out web/eval/runs/<date>-f5f7-candidate
EVAL_CANDIDATE_KEY=… EVAL_LIVE=1 node web/eval_character.js https://troid.ai --only p-size,ex-r,b-stop,b-leverage,o-montecarlo,p-crossover --out web/eval/runs/<date>-f5f7-live

# to decide a promotion: every case (28), three candidate runs and the live baseline, each read into <run>.read.json (_errors)
EVAL_CANDIDATE_KEY=… node web/eval_character.js https://troid.ai --out web/eval/runs/<date>-run17
EVAL_CANDIDATE_KEY=… node web/eval_character.js https://troid.ai --out web/eval/runs/<date>-run18
EVAL_CANDIDATE_KEY=… node web/eval_character.js https://troid.ai --out web/eval/runs/<date>-run19
EVAL_CANDIDATE_KEY=… EVAL_LIVE=1 node web/eval_character.js https://troid.ai --out web/eval/runs/<date>-run20
node web/eval_character.js --promotion --candidate 17,18,19 --live 20
```

The full runs evaluate everything staged here together, runs 10 to 16's fixes with F5 to F7. Promotion folds
`size_trade`'s `next` branch in (dropping the flag), `MATH_NEXT` and `MATH_FORMULAS_NEXT` into `MATH` and
`MATH_FORMULAS`, `TRADE_MATH_TOOL_NEXT` into `TRADE_MATH_TOOL`, `CANDIDATE_RULES` into `RULES`, and moves `TROID.md`
into `web/public/TROID.md` and the root copy, `TROID-CHARACTER.md` into `web/context/` and the root copy; the live
checks in `web/test_assistant.js` (reference case 2, "the live smoke figures", losses left 8) then move to these figures,
and METHODOLOGY's three audit rows (on the audit branch) drop "ask troid's size_trade has not followed yet".

troid's character was promoted after evaluation run 9. Staged now, from the reads of run 10 (the live prompt), run 11
(this candidate, 21 of 24, six errors), run 12 (22 of 24, four), run 13 (22 of 24, three), run 14 (22 of 24, five) and run 15 (23 of 24, seven): four guardrails, explain_rule's ruin, crossover and drawdown texts with the
rules they state (`CANDIDATE_TOPIC_CITES`), the tools in `CANDIDATE_RUN` (the floating-loss rule with its source, the
leverage cap in trade_math, a staged challenge's targets added up, BrightFunded's EUR price), `CANDIDATE_LINTS`, and
support.md section 4's reply word for word on a should-I question, one DERIVED tier line where trade_math ran with and
without a firm's rule, no word about a draft the user never saw, a stop as a percent in trade_math, no method
section written twice around a tool call, and support.md section 2's three usual causes when a user says troid's
numbers were involved and the reply leaves them out (unless it names them in its own words), half Kelly ÷ the daily limit
in trade_math, and no lead-in to a tool call left above the final answer. After the owner's review of run 16: every
number in an answer from a tool, the user or troid's published figures (`web/api/_numbers.js`, a backstop that asks
once for a rewrite), a teaching answer's formula written out, and `TROID-CHARACTER.md` staged here with its examples'
read dates replaced by "(read date from the tool)", so the prompt teaches no date from memory, and every number in
its examples from the question, a tool or a step shown on the page (the owner's wording for the R and recovery
examples: "2,584 × 0.3862 = $998, which is 2 × 1R = +2R"; "0.20 ÷ (1 − 0.20) = 0.25, so 25%"). After the subset run of
2026-09-24 (the eight cases those changes touch; 7 of 8 automatically, four errors on a read, none critical): a lint
rewrite stands only when it trips fewer notes than its draft and fixes at least one (o-montecarlo's rewrite had lost
its answer); a formula line carries an equals sign (b-stop's formula in words read as risk ÷ distance + fee); a reply
never opens on a result the reader never saw ("That result …"); the tier line says MODELLED when a reply quotes
troid's Monte Carlo (`ask.tier.modelled`); and troid's assumptions are listed once, by the service (p-size listed them
twice). The second subset run (those three cases) read with no critical or major error: o-montecarlo and
p-size fixed; b-stop's formula right, still in words.

Run 14's read also found that run 9's ex-r, the reply the promotion rested on, stated the 1-Step's 4% daily limit with
no tool behind it and no read date; the read of run 9 missed it, and the check added after run 14 finds it (run 9 is
23 of 24 under the checks now; re-read after run 16 to the candidate's standard, three of its replies fail). The live
prompt has the fault, and so did the candidate in run 16, in dollars ("$4,000 ÷ $500 ≈ 8") where the firm-percentage
lint only reads percentages: the undated examples and the number backstop are staged against it. Run 15's read found
the same of run 11's ex-kelly (half Kelly given full Kelly's 4.38× the daily limit).
