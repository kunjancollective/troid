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

## Staged 2026-09-30: the calculator audit's F5, F6 and F7

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
- **Prompt files.** `TROID.md` here: the live copy with the sizing block (fee_unit, loss_at_stop, losses_left), the
  ruin line, the fee share by side with its table (long, short, side-neutral) and the 5% threshold by side, a long's
  liquidation "none above zero", "how many more losses at that size leave equity above the binding ceiling", and the
  "Costs" line of "What troid knows". It is the live `web/public/TROID.md`, not the patch's: as with explain_rule's reset,
  the candidate keeps the live reset text until the patch publishes; when it does, bring the patch's two changes (the
  reset paragraph in UTC, "no measurable edge") into this copy. `TROID-CHARACTER.md`: the same "Costs" line, and the R
  example's fees "to open at entry and to close at the stop" and "8 − 1 = 7 losses of that size leave you above it".

Not staged: F1 (a margin above equity cut to fit), R6 (a long's floor distance past 100%, "not reached above zero") and
the audit's other fixes; ask troid's size_trade still shows a long's floor distance past 100% as computed.

**Eval cases this touches:** p-size (size_trade), ex-r (r_multiple, the example's losses), b-stop (position_size,
the fee-per-unit formula), b-leverage (position_size's margin, liquidation), o-montecarlo (explain_rule ruin) and
p-crossover (size_trade may be called). **p-size's check `1\.622` will fail under the candidate:** every saved run wrote
the tool's six decimals (1.622095), and the candidate's quantity is 1.621583, which matches only if a reply rounds it
to 1.622. Left as it is (the task was not to loosen a check); the owner decides whether to change it to the new figure,
knowing the live baseline then fails it. No other case's expected figure changes.

**After deploying**, check the deployment stages it: `curl -s https://troid.ai/api/troid | jq .candidate` (staged holds
TROID.md and TROID-CHARACTER.md; rules end with fees; run includes size_trade and trade_math). Then:

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
