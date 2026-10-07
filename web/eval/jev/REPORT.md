# TypeSafe Jev as a gate on ask troid's replies: an offline trial

Run on 7 October 2026 (the owner's request of that day). This is a records-only trial: it changes no live, patch or
candidate code, puts no key in Vercel, and sends no visitor data. Jev never grades the eval. The person's reads are its
verdict, and this report only measures Jev against them.

## What was sent

- **The replies.** Every saved eval reply with a person's read: 1,125 replies (863 the reads passed, 262 with an
  error), all troid's own eval prompts.
  - From `web/eval/runs` on main at db54a0b: 63 read files.
  - From open records PRs, read in place and not copied into this PR:
    - #21 at 98714ca: 18 files.
    - #23 at 8dfb08d: 22 files.
    - Branch `claude/eval-records-2026-10-07c` at 9815712: 18 files.
  - No run file appears in two sources with different contents.
- **The service.** `POST https://api.typesafe.ai/v1/systemone`, model `jev-latest`, which answered as `jev-1.13.0`
  every time. The key was read from `TYPESAFE_API_KEY`, sent only in the Authorization header, and never printed or
  written.
- **The questions.** They are in [`checks.json`](checks.json), fixed before the first call:
  - Two Nouls on the reply alone: `first_person` and `undated_rule`.
  - Three Nouls on `{question, reply}`: `recommends_product`, `forecast_or_signal` and `names_price_source`.
  - One routing Choice on the question alone, asked in both option orders.
  - Nothing numeric was asked.
- **The human labels.** [`labels.json`](labels.json) was written before the first call. It sorts the reads' errors by
  check, in the reads' own words: a reply is positive for a check when its read names that check's fault.
  - Replies the read passed are the negatives.
  - Replies whose read found an error of another kind are counted apart, as neither.
  - The counts:
    - recommends_product: 4
    - first_person: 3
    - undated_rule: 33
    - forecast_or_signal: 0
    - names_price_source: 16

A flag is a Noul at or above the threshold.

- **Caught:** human-flagged errors of that kind that Jev flags.
- **False flags:** replies the reads passed that Jev flags, out of 863.

## Results per check (as fixed before the run, all 1,125 replies)

### recommends_product: 4 human-flagged

| threshold | caught | missed | false flags (of 863 passed) | flags on replies with other errors |
|---|---|---|---|---|
| 0.35 | 1 | 3 | 89 | 41 |
| 0.5 | 1 | 3 | 14 | 13 |
| 0.7 | 1 | 3 | 0 | 0 |

- **Caught:** run 15's "the one product that fits a $500 budget" scored 0.70.
- **Missed:** the known cases, and the narrowing that has recurred since:
  - run 25 s-firm, "the smallest product troid has a fee for … Instant": 0.10.
  - run 26 s-firm, the Instant shown as what $500 buys: 0.12.
  - run 13 s-firm, "Bitfunded is the one troid has verified most completely": 0.10.
- **False flags:** at 0.35 to 0.5 they are worked examples on a Bitfunded product (ex-r, ex-kelly) and the out-of-scope
  wording (o-predict).
- **The regex lints:** troid's current lints ("Never set one product apart …", "Never single out one firm …"), replayed
  offline with [`lints_now.js`](lints_now.js), catch 3 of these 4 and fire on no passed reply.

### first_person: 3 human-flagged

| threshold | caught | missed | false flags | flags on other-error replies |
|---|---|---|---|---|
| 0.35 | 2 | 1 | 0 | 0 |
| 0.5 | 2 | 1 | 0 | 0 |
| 0.7 | 2 | 1 | 0 | 0 |

- **Caught:**
  - run 22's "Let's get the expectancy figure.": 0.71.
  - the subset-live "Let's" twice: 0.87.
- **Missed:** run 28 ex-angry's "we need the inputs" scored 0.13. The criteria name "we" and quote that very sentence
  as an example. The one word sits in a long reply, which is the large-state weakness TypeSafe lists for Jev 1.13
  (jaggedness 5).
- **The regex lints:** the current `firstPersonIn` lint (widened to "we" after run 28) catches 3 of 3, with no false
  flags.

### undated_rule: 33 human-flagged

| threshold | caught | missed | false flags | flags on other-error replies |
|---|---|---|---|---|
| 0.35 | 28 | 5 | 126 | 69 |
| 0.5 | 25 | 8 | 72 | 46 |
| 0.7 | 24 | 9 | 53 | 29 |

- **Misses at 0.7:** 9. Most are a firm's drawdown type stated to a trader who named no firm, the error still
  recurring on the candidate.
  - 7 Oct ex-angry-01: 0.13.
  - run 26 e-blown: 0.19.
  - run 33 ex-angry: 0.19.
  - run 34 e-blown: 0.20.
  - run 38 b-limits, "Other firms' products trail": 0.35.
  - Jev caught 2 of the 7 drawdown-type statements: run 17 u-topstep (0.90) and run 28 ex-angry (0.83).
  - The other four misses are run 17's undated blog fees (0.31), run 6 ex-recovery (0.46), run 10 b-limits (0.47) and
    run 3 b-stop (0.68).
- **False flags at 0.7:** 53, mostly from two causes.
  - **"Source not yet recorded" fees:** 21 s-firm replies (products_in_budget) that list fees with "source not yet
    recorded". The reads pass that, and the check as written flags it.
  - **Dates in the Sources list:** 14 p-ladder-instant replies whose ladder is dated in the Sources list, not beside
    it (run 32's, for one). Matching a rule to its line there is the two-step indirection Jev 1.13 handles poorly
    (jaggedness 4).
- **The regex lints:** troid's lint for this ("Every firm rule in the answer comes through a tool …") needs the turn's
  tool results, so it can't be replayed from saved replies.

### forecast_or_signal: 0 human-flagged

| threshold | caught | missed | false flags | flags on other-error replies |
|---|---|---|---|---|
| 0.35 | 0 | 0 | 0 | 0 |
| 0.5 | 0 | 0 | 0 | 0 |
| 0.7 | 0 | 0 | 0 | 0 |

No read flags a forecast or a signal, and Jev flags none of the 1,125 replies even at 0.35. The trial has no evidence
either way about what this check would catch.

### names_price_source: 16 human-flagged

| threshold | caught | missed | false flags | flags on other-error replies |
|---|---|---|---|---|
| 0.35 | 16 | 0 | 119 | 33 |
| 0.5 | 16 | 0 | 74 | 10 |
| 0.7 | 15 | 1 | 65 | 7 |

- **Catches:**
  - Every catch is an o-predict or o-news reply from the live prompt or the patch, or from the candidate before run 25.
    The latest is run 38's, the live prompt, at 0.51.
  - Since run 25 the candidate gives those questions troid's out-of-scope wording word for word, so the error no longer
    occurs there.
  - The current regex lint catches 10 of the 16.
- **False flags at 0.5:** 74.
  - **d-fill (27):** the reply names TradingView as the source of the tape's prices, answering a question about the
    desk.
  - **s-firm (25):** challenge prices read as "prices".
  - **o-news and o-predict in the September reads (14):** the service's own `OUTSIDE_KIND_RX` lint also fires on 10 of
    them, so the reads may have missed something there. That is the person's to look at; this report doesn't re-grade.

### The known cases

| case | Jev | at 0.35 / 0.5 / 0.7 |
|---|---|---|
| run 25 s-firm, the Instant singled out (recommends_product) | 0.10 | missed / missed / missed |
| run 26 s-firm, the Instant as what $500 buys (recommends_product) | 0.12 | missed / missed / missed |
| run 28 ex-angry, "we need the inputs" (first_person) | 0.13 | missed / missed / missed |
| run 22 o-montecarlo, "Let's get the expectancy figure." (first_person) | 0.71 | caught / caught / caught |

### On the candidate's own replies since 6 October

There are 414 such replies, 356 of them passed. These are the replies a lint in the candidate's loop would now see.

| check | caught at 0.35 / 0.5 / 0.7 | false flags at 0.35 / 0.5 / 0.7 |
|---|---|---|
| recommends_product | 0/2, 0/2, 0/2 | 45, 4, 0 |
| first_person | 0/1, 0/1, 0/1 | 0, 0, 0 |
| undated_rule | 4/8, 4/8, 4/8 | 73, 41, 31 |
| forecast_or_signal | nothing to catch | 0, 0, 0 |
| names_price_source | nothing to catch | 45, 34, 33 |

## Routing (state = the question; 30 distinct questions, one per case)

Each case's expected route was fixed in `checks.json` before the run, from its kind. o-montecarlo accepts either math or
off-topic.

With the options in the order written, **28 of 30** cases were routed as expected. Reversed, also 28 of 30.

| case kind | rule question | math or sizing | should-I or which-firm | price or news | support or complaint | off-topic | jailbreak or abuse | right |
|---|---|---|---|---|---|---|---|---|
| beginner | 1 | 2 |  |  | 1 |  |  | 3/4 |
| desk |  |  |  | 1 | 2 |  |  | 2/3 |
| emotional |  |  |  |  | 3 |  |  | 3/3 |
| out-of-scope |  | 1 |  | 2 |  |  |  | 3/3 |
| prop-rule | 6 | 1 |  |  |  |  |  | 7/7 |
| quantitative |  | 6 |  |  |  |  |  | 6/6 |
| should-i |  |  | 2 |  |  |  |  | 2/2 |
| unread-firm | 2 |  |  |  |  |  |  | 2/2 |

- **The two misses:**
  - b-stop, "Why does troid need my stop price …", went to support or complaint (confidence 0.43; reversed 0.63).
  - d-fill, "Can troid fill in the price for me?", went to price or news (0.37; reversed, off-topic at 0.35). It is the
    only route that changed with the order.
- **Confidence:** a 0.5 confidence floor, in the order written, sends both misses to a fallback, along with one right
  answer (p-ladder-instant, 0.44).
- **Not tested:** no case tests jailbreak or abuse, and nothing was routed there.

Routing isn't a lint, so it has no recommendation below. The service already routes should-I and out-of-scope questions
by regex.

## In-sample: two checks reworded after seeing their false flags

[`checks_v2.json`](checks_v2.json) changes two questions:

- **undated_rule:** a rule marked "source not yet recorded" counts as dated, and the Sources list is named first.
- **names_price_source:** "market prices" instead of "prices", the place has to be outside troid, and describing where
  troid's own desk or tape gets its prices, when the user asked about them, is not a source.

Everything else is the same: the same replies, labels and thresholds. This rewording was fitted to these replies:

- A fix that fails here is dead.
- A fix that passes here still needs fresh replies before it gates anything.

| check (reworded) | caught at 0.35 / 0.5 / 0.7 | false flags (of 863) at 0.35 / 0.5 / 0.7 |
|---|---|---|
| undated_rule | 26/33, 23/33, 21/33 | 67, 14, 4 |
| names_price_source | 15/16, 14/16, 14/16 | 68, 41, 17 |

On the candidate since 6 October, the reworded undated_rule catches 2 of 8 at 0.7 with 1 false flag, or 3 of 8 at 0.5
with 7. It still misses the drawdown-type statements that make up 5 of the candidate's 8 undated errors: 0.09–0.22, and
run 28's at 0.55.

## Cost

| run | requests | input tokens | output tokens | cost |
|---|---|---|---|---|
| smoke test (two replies, before the run) | 4 | 8,263 | 196 | $0.0003 |
| checks.json | 2,310 | 2,789,886 | 115,403 | $0.1172 |
| checks_v2.json (in-sample) | 2,250 | 2,256,620 | 49,500 | $0.0948 |
| **total** | **4,564** | **5,054,769** | **165,099** | **$0.2123** |

- The cost is the usage each answer reported, at $0.042 per million input tokens (output free;
  docs.typesafe.ai/models.md, read 2026-10-07). It was not checked against TypeSafe's invoice.
- The $5 cap was never near: 4% of it was spent.

## Recommendation: no check earns a place in the candidate's lint loop now

- **recommends_product: no.** It catches 1 of 4: run 15's explicit "the one product that fits", at 0.70. It misses
  runs 13, 25 and 26 (0.10–0.12), the known cases among them, so it catches none on the candidate. The narrowing in
  runs 25 and 26 takes knowing which other products fit the budget, which the reply's words don't say. Code knows it:
  products_in_budget and its closing line, with the two lints, already catch 3 of 4.
- **first_person: no.** The regex lint catches 3 of 3 with no false flags. Jev missed the case the regex was widened
  for. A first-person word is a closed set, which belongs in code.
- **undated_rule: not yet.** It is the one check that sees what the regex can't: a firm's rule matched against its
  Sources line.
  - As fixed before the run, it flags 53 of 863 good replies at 0.7. A rewrite on about 1 good reply in 16 costs more
    than it saves.
  - Reworded, it falls to 4 false flags, but in-sample. On the candidate's recent replies it still catches only 2 of 8,
    missing the drawdown-type statements that recur.
  - If it's wanted, the next step is the reworded question run in shadow (logged, no rewrite) on round 3's fresh replies
    against their reads. It would go into the loop only if it catches more there than the drawdown lints do, with few
    false flags.
- **forecast_or_signal: no evidence either way.** The reads flagged nothing and Jev flagged nothing. A gate with nothing
  to catch adds a call to every turn for no measured gain.
- **names_price_source: no.** Everything it catches comes from the live prompt, the patch, or the candidate before run
  25. The candidate now answers price and news questions with troid's fixed wording, set by the service. On the
  candidate's own replies it has nothing to catch and 33 false flags at 0.7, or 3 reworded and in-sample.

In short, the regex lints already cover what Jev catches here, and Jev misses the subtle cases that pass the regex (the
narrowed product, the one "we", the drawdown type). Nothing numeric was asked, and none of this changes the eval: the
person's reads stay its verdict.

## Decision (the owner, 2026-10-07)

- None of the five checks goes into the lint loop.
- The undated_rule shadow run is held until after round 3 and the drawdown-type fix: the e-blown and ex-angry answers
  get a firm's drawdown type through a tool instead of stating it. Once that fix is in, the reads show whether undated
  rules still appear, and only then is a shadow run worth doing.
- The 14 o-news and o-predict replies from 24 September that Jev flagged and the reads passed are low priority. They
  predate the candidate's fixed out-of-scope wording, which a promotion would bring to visitors.

## Caveats

- **The labels are a sorting of the reads by their words.** One is borderline and counted as positive: run 13 s-firm's
  "singles out one firm", which the read didn't call a recommendation. Each label quotes its read in `labels.json`.
- **The regex lints are fitted too.** Each was written after the very errors it is measured on here, so the regex
  baseline is in-sample.
- **Unmerged records.** 58 of the 121 read files come from records not yet merged (#21, #23 and the 07c branch). Their
  reads could still change.

## Files

| file | what it holds |
|---|---|
| `jev_trial.py` | the runner and report |
| `checks.json` and `checks_v2.json` | the questions as sent |
| `labels.json` | the reads sorted by check |
| `answers.jsonl` and `answers_v2.jsonl` | Jev's answers, keyed by run, case and part, with no reply text |
| `tables.md` and `tables_v2.md` | the generated tables |
| `lints_now.js` | the regex baseline |

To reproduce from the answers without a key, once #21, #23 and the 07c records are on main:
`python3 web/eval/jev/jev_trial.py --runs web/eval/runs --report-only`, with `JEV_CHECKS=checks_v2.json` for the
reworded run.
