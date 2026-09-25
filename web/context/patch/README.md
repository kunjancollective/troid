# Patch — one change shipped on its own

A change the owner asks to ship alone, apart from the candidate in `../candidate/`, is staged here: `TROID.md`,
`support.md` or `TROID-CHARACTER.md`, each only if it changes. Only a request carrying `TROID_CANDIDATE_KEY` with
`x-troid-variant: patch` gets it — the live prompt with these files in place, and nothing of the candidate's
(`EVAL_PATCH=1` in `web/eval_character.js`). It is evaluated on the cases it touches against the live baseline
(`EVAL_LIVE=1`), and published when it adds no critical failure and no new kind of failure: the file moves into place and
this directory empties.

Staged now (2026-09-25): `support.md` section 9, "Can troid fill in the price?" — the redesigned desk's price fill, in
the FAQ's facts without its figures. Evaluated on d-fill (new) and b-stop, p-size, o-predict, o-news and ex-angry.
