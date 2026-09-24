# Candidate prompt — staging

A prompt change is staged here before it reaches anyone: `TROID.md`, `support.md` and `TROID-CHARACTER.md`, each
only if it changes. Only a request carrying `TROID_CANDIDATE_KEY` in the `x-troid-candidate` header gets them — the
evaluation runner, `web/eval_character.js` — together with `CANDIDATE_GUARDRAILS`, `CANDIDATE_RULES`,
`CANDIDATE_TOOLS` and `CANDIDATE_RUN` in `web/api/troid.js`, and any service change gated on
`variant === "candidate"`. Everyone else gets the live prompt.

A candidate is promoted only when an evaluation run passes every check and a person's read of every reply finds no
error (`web/eval/runs/`). Promotion is one commit: the files move into place (TROID.md into both copies) and the
`CANDIDATE_*` entries fold into `GUARDRAILS`, `RULES`, `TOOLS` and `RUN`.

Nothing is staged now: troid's character was promoted after evaluation run 9.
