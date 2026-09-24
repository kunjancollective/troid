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
