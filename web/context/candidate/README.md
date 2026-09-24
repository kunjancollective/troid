# Candidate prompt — staging

A prompt change is staged here before it reaches anyone: `TROID.md`, `support.md` and `TROID-CHARACTER.md`, each
only if it changes. Only a request carrying `TROID_CANDIDATE_KEY` in the `x-troid-candidate` header gets them — the
evaluation runner, `web/eval_character.js` — together with `CANDIDATE_GUARDRAILS`, `CANDIDATE_RULES`,
`CANDIDATE_TOOLS` and `CANDIDATE_RUN` in `web/api/troid.js`, and any service change gated on
`variant === "candidate"`. Everyone else gets the live prompt.

A candidate is promoted only when an evaluation run passes every check and a person's read of every reply finds no
error (`web/eval/runs/`). Promotion is one commit: the files move into place (TROID.md into both copies) and the
`CANDIDATE_*` entries fold into `GUARDRAILS`, `RULES`, `TOOLS` and `RUN`.

troid's character was promoted after evaluation run 9. Staged now, from the reads of run 10 (the live prompt) and run 11
(this candidate, 21 of 24, six errors): three guardrails, explain_rule's ruin, crossover and drawdown texts with the
rules they state (`CANDIDATE_TOPIC_CITES`), the tools in `CANDIDATE_RUN` (the floating-loss rule with its source, the
leverage cap in trade_math, a staged challenge's targets added up, BrightFunded's EUR price), `CANDIDATE_LINTS`, and
support.md section 4's reply word for word on a should-I question. No file is staged.
