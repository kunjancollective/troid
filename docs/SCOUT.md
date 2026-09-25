# troid — scout register

Every outside repository troid uses, trials, watches or turned down, with the date it was read and the reason.
troid's value is being right and traceable; a tool earns a place only if it computes, draws, checks or protects,
and never if it decides trades, generates signals or places orders.

A verdict here is an evaluation, not an installation. Nothing marked **trial** is added to troid, or run against
production, until the owner approves it (list at the end).

## How a repo is scored

| # | question | pass |
|---|---|---|
| 1 | Computes, draws, checks or protects? | Yes. Anything that decides trades, generates signals or places orders is rejected outright. |
| 2 | Alive? | A commit in the last 3 months and maintainers answering issues. |
| 3 | Used? | Dependents and regular releases. Stars count least. |
| 4 | Licence | MIT, Apache-2.0, BSD: fine. GPL/AGPL/LGPL: rejected for code (ideas may be referenced). No licence: rejected. Commons Clause, Elastic, proprietary: flagged. |
| 5 | What it touches | API keys, data sent to a third party, cost — each stated. |
| 6 | Overlap | What troid already does, and what the repo would replace. |
| 7 | Scope | One piece usable without adopting a whole framework? |

Verdicts: **adopt**, **trial**, **watch**, **reject**.

## How the 2026-09-25 read was done

Stars, push date and licence field from GitHub's repository search. Every licence below was read from the repo's
own LICENSE file, not the licence label GitHub shows (they disagree for arch, openai/evals and vectorbt). Last commit
and tag dates from a shallow clone of the default branch; release pages were cross-checked against tag commits and
PyPI because a fetched releases page twice showed the wrong year. "Used by" is GitHub's dependents page where it
loaded; "not read" where it did not. Whether maintainers *reply* to issues was judged from issue open/close state and
commit authorship, not from reading threads, and is marked where that matters.

---

## N1 — know when a firm changes a rule on its own pages

troid's largest ongoing risk: a firm edits its Terms or help centre after troid read them. Layer one says *which*
pages changed; layer two (jev-mcp, below) checks troid's recorded claims against the changed text.

| repo | what it does | last commit | releases | used-by / stars | licence (as read) | keys / data / cost | overlap | verdict |
|---|---|---|---|---|---|---|---|---|
| dgtlmoon/changedetection.io | Self-hosted page watcher: snapshot history, word/line diffs, notifications, REST API | 2026-09-25 | 0.60.7, 2026-09-17; five releases 4–17 Sep | not verified · 34.5k★ | Apache-2.0, standard text | No key for core use. Optional LLM features send diffs to an AI provider of the user's choosing — keep off. Free self-hosted; hosted SaaS is paid, and the visual selector and hosted AI features are SaaS-side | Brings its own browser container, duplicating troid's Playwright | **trial** — best feature fit and very active; the catch is a server that runs all the time, which troid (Vercel + Actions) doesn't have |
| thp/urlwatch | CLI: jobs in a config file, diffed against a local cache, reports | 2026-07-10 | 2.29 (PyPI 2024-12-10); master's Playwright fixes unreleased | not read · 3.1k★ | BSD-3-Clause | None | Browser jobs use Playwright, the stack troid already has | **trial (runner-up)** — runs in GitHub Actions like the rest of troid; no release since 2024 |
| simonw/git-scraper-template | Actions cron fetches a URL and commits it; git history is the diff log | 2025-02-26 | none | not read · 133★ | **none** (no LICENSE file) | None | troid's `shadow.yml` already works this way | **reject for code** (no licence, inactive); **idea referenced** — the pattern is the lightest route |
| EdJoPaTo/website-stalker | Rust CLI: fetch, filter, git commit, in Actions | 2026-07-01 (last human commit 2026-06-12) | v0.27.1, 2026-06-13 | not read · 75★ | LGPL-2.1 | None | No JS rendering found | **reject** — LGPL, no rendered pages, one maintainer |
| huginn/huginn | Rails "agents" platform: monitor, then act | 2026-09-24 | v2026.09.22, weekly | not verified · 50.0k★ | MIT | Self-hosted, needs MySQL/Postgres | Low | **reject (scope)** — alive and MIT, but a whole platform to diff a handful of pages |

**Top pick: none adopted yet. The route to trial is the one with no new service:** extend the existing Actions
pattern — Playwright reads each recorded source page, the N2 pick turns it into clean text, the snapshot is
committed, and a change is a dated, reviewable git diff beside `firms_evidence.json`'s read dates. changedetection.io
is the stronger tool if the owner is willing to host it; urlwatch is the packaged fallback inside Actions.

## N2 — read firm pages that only render in a browser

| repo | what it does | last commit | releases | used-by / stars | licence (as read) | keys / data / cost | overlap | verdict |
|---|---|---|---|---|---|---|---|---|
| adbar/trafilatura | Main text and metadata from HTML, to TXT/Markdown/JSON | 2026-09-25 | 2.2.0, 2026-07-31; 2.1.0, 2026-06-07 | 9,529 repos / 809 packages · 6.9k★ | Apache-2.0 | None; does not fetch | Complements Playwright: takes `page.content()` troid already has | **trial → adopt** — one function, no network, no key, most depended-on; run single-threaded (open issue #925: crash on concurrent `extract()` in 2.2.0) |
| microsoft/markitdown | Files and HTML to Markdown | 2026-09-21 | 0.1.8, 2026-09-21; every 1–2 months | 3,490 repos / 596 packages · 187k★ | MIT | Core: none. Optional Azure / OpenAI features need keys and send data — keep off | Complements; also reads PDF Terms | **trial (second)** — a plain converter, not boilerplate removal; useful for PDF Terms |
| mozilla/readability | Firefox Reader View's main-content finder (JS) | 2026-07-09 | 0.6.0, 2025-03-03 | 13,334 repos / 1,500 packages · 11.5k★ | Apache-2.0 | None | Could be injected into the Playwright page | **watch** — tuned for articles, not rule/FAQ pages; issue replies not seen |
| unclecode/crawl4ai | Crawler framework: Playwright + Markdown + optional LLM step | 2026-09-25 | 0.9.4, 2026-09-23 (a security release) | 3,290 repos / 256 packages · 84.3k★ | Apache-2.0 **plus an added "Attribution Requirement"**: every public use must display a credit line prominently | Core: none. Cloud is keyed and paid | Wraps its own Playwright — two browser stacks | **watch** — whole-framework adoption, an attribution obligation on the site, recent advisories |
| firecrawl/firecrawl | Scrape/crawl API to Markdown/JSON | 2026-09-25 | v2.11.0, date not verified | not read · 184.7k★ | **AGPL-3.0** core (SDKs MIT) | Cloud keyed and paid; pages go to firecrawl.dev | Duplicates | **reject** — AGPL, and the practical path sends firm pages to a hosted service |
| jina-ai/reader | URL to LLM-ready text | 2026-05-22 | none | not read | Apache-2.0 | Hosted r.jina.ai: URLs go to Jina; rate-limited, payment errors reported | Duplicates | **reject** — no commit in 3 months; the open branch trails the SaaS |

**Top pick: trafilatura.** Keep troid's Playwright read unchanged and pass the rendered HTML to one Apache-2.0
function. A clean, stable snapshot is also what makes the N1 diffs readable, so the two picks go together.

## N3 — is a strategy's edge real?

Tests for overfitting and multiple comparisons, to strengthen the method behind shadow-2. troid already has
`backtest/noise_math.py` (expected best of k under zero edge).

| repo | what it does | last commit | releases | used-by / stars | licence (as read) | keys / data / cost | overlap | verdict |
|---|---|---|---|---|---|---|---|---|
| bashtage/arch | `arch.bootstrap`: Hansen's SPA, White's reality check, Romano-Wolf StepM, model confidence set; stationary, circular and moving block bootstraps; optimal block length | 2026-09-24 | v8.0.0, 2025-10-21; 1–2 a year | 3,735 repos / 183 packages · 1.6k★ | Permissive NCSA/BSD-style (`LICENSE.md`; GitHub labels it "Other") | None | Complements `noise_math.py`: a bootstrap p-value beside the closed-form E[max] | **adopt** — one import, no framework; 36 commits since June, a StepM fix merged 2026-09-20 |
| statsmodels/statsmodels | `multipletests`: Holm, Benjamini-Hochberg and others | 2026-09-25 | v0.15.0, 2026-08-27 | not read · 11.7k★ | BSD-3-Clause | None | None | **adopt (baseline)** — family-wise and FDR correction across the ten-asset grid |
| esvhd/pypbo | PBO via CSCV, PSR, DSR, minTRL | 2026-07-07 (before that 2022-03) | none | not read · 140★ | **AGPL-3.0** | None | `expected_max` duplicates `noise_math.py` | **reject for code; idea referenced** — AGPL, dormant, open correctness issue on PBO unanswered since 2020–23 |
| hudson-and-thames/mlfinlab | ML-finance toolbox; DSR/PBO in the paid product | 2021-12-01 | none | not read · 4.9k★ | **Proprietary** licensing agreement; business licences sold | Commercial | Would overlap a DSR helper | **reject** — not open source; the public repo holds no code |
| quantskills/skill-backtest-overfit | DSR, PBO, purged k-fold, Harvey-Liu haircut scripts | 2026-07-16 | none | not read · 37★ | **GPL-3.0** | None | Same gap as pypbo | **reject (GPL)** — a second reference for a clean-room check only |

**Top pick: arch**, with statsmodels' `multipletests` for the cross-section. No maintained, permissively licensed
deflated-Sharpe or PBO library was found; both are short, published formulas (Bailey and López de Prado) and belong
in troid's own code beside `noise_math.py`, written from the papers — not from the AGPL or GPL implementations.

## N4 — faster backtests for the ten-asset cross-section and shadow-2

| repo | what it does | last commit | releases | used-by / stars | licence (as read) | keys / data / cost | overlap | verdict |
|---|---|---|---|---|---|---|---|---|
| polakowo/vectorbt | NumPy/Numba vectorised simulation across many columns and parameters at once | 2026-09-17 | v1.1.0, 2026-07-05; v1.0.0, 2026-04-22 | 876 repos / 49 packages · 9.2k★ | **Apache-2.0 with Commons Clause v1.0** — no right to "Sell", including hosting or consulting whose value derives from it. Not OSI open source. VectorBT PRO is a separate paid product | Core free, no key. Optional extras pull yfinance, ccxt, python-telegram-bot — not to be installed. Tight pins: numpy ≥2.4.6, pandas ≥3.0.3 | Duplicates troid's pandas engine; overlaps quantstats' statistics | **trial (flagged)** — the only maintained candidate built for assets × grid in one pass; fine as internal research compute, never vendored into troid's MIT code and never in anything sold |
| pmorissette/bt | Tree-of-algos portfolio backtester on ffn | 2026-09-25 | v1.2.4, 2026-09-17; frequent | 1,736 repos / 18 packages · 3.0k★ | MIT | None (ffn's licence not verified) | Weight-based allocation, not troid's per-trade engine | **watch** — licence-clean and active, but not vectorised and not a speed win |
| nautechsystems/nautilus_trader | Rust event-driven engine with live broker/exchange adapters | 2026-09-25 | v1.231.0, 2026-08-02; 2.0 in release candidates | not read · 29.4k★ | LGPL-3.0 | Live adapters need exchange keys | Replaces the whole engine | **reject** — built to execute orders; LGPL; mid 1.x→2.0 migration |
| kernc/backtesting.py | Single-asset strategy backtester with plots | 2026-08-05 | 0.6.6, 2026-07-22 | not read · 9.0k★ | **AGPL-3.0** | None | Duplicates the engine | **reject** — AGPL, single-asset by design |
| mementum/backtrader | Event-driven backtester with broker adapters | 2023-04-19 | none since | not read · 23.3k★ | **GPL-3.0** | Broker adapters exist | Duplicates the engine | **reject** — GPL, no commit in about 2.5 years |

**Top pick: vectorbt as a flagged trial — with the honest alternative stated.** At 4h bar counts, looping troid's
existing engine over ten assets may be fast enough; that has not been timed. A trial should time the existing engine
first, and only then vectorbt, in a separate environment so its pins can't move quantstats'.

## N5 — testing ask troid's answers

troid's runner (`web/eval_character.js`) sends each case in `web/eval/character.json` to the deployment, applies
pattern checks, records a person's read with severity and kind, tracks tokens and cost, and applies the promotion
rule in `CLAUDE.md`.

| repo | what it does | last commit | releases | used-by / stars | licence (as read) | keys / data / cost | overlap | verdict |
|---|---|---|---|---|---|---|---|---|
| UKGovernmentBEIS/inspect_ai | Python eval framework: datasets, solvers, scorers, epochs, log viewer | 2026-09-25 | tags roughly daily, 0.3.269 on 2026-09-25 | not read · 2.9k★ | MIT | Model key for grading (would be the eval key); no telemetry module found (search only, not verified in full); no account | Scorers overlap the pattern checks; nothing covers severity or promotion | **trial (ideas only)** — clean licence, very active; borrow epochs and a graded pre-screen, don't port the runner |
| promptfoo/promptfoo | Node CLI: declarative cases, regex/JS/rubric assertions, prompt comparison, red-team | 2026-09-25 | 0.123.1, 2026-09-18; weekly, still 0.x | 679 repos / 73 packages · 25.5k★ | MIT | **Telemetry on by default** (PostHog: commands and assertion types used; email when logged in); off with `PROMPTFOO_DISABLE_TELEMETRY=1`; npm update check | Could replace the case harness, not the read, severity, promotion rule or pacing | **watch** — default telemetry and a large dependency beside the site's single npm dependency; take the comparison view and rubric idea |
| confident-ai/deepeval | Pytest-style LLM metrics | 2026-09-25 | python-v4.2.4, 2026-09-22 | not read · 18.4k★ | Apache-2.0 | **Telemetry on by default** (PostHog), opt-out variable; login prompts for its paid cloud | Graded metrics only | **reject** — default telemetry and cloud upsell; nothing inspect_ai doesn't also offer |
| openai/evals | Eval framework and benchmark registry | 2026-04-14 | last tag 3.0.1, 2024-04-30 | not read · 19.5k★ | MIT (GitHub labels it "Other") | Built around OpenAI's models | Graded templates only | **reject** — maintenance mode |
| langfuse/langfuse | Tracing, evals and prompt management platform | 2026-09-25 | v4.46.0, 2026-09-25 | not read · 35.1k★ | MIT outside `ee/`; `ee/` under its own licence (not read) | Server or cloud account; tracing sends prompts and outputs there | Observability, not the runner | **reject** — a platform, with an enterprise-licensed part |
| Arize-ai/phoenix | Observability and evals | 2026-09-25 | v20.16.0, 2026-09-23 | not read · 11.6k★ | **Elastic License 2.0** | — | — | **reject** — not open source |
| vibrantlabsai/ragas | Metrics for retrieval (RAG) apps | 2026-02-24 | v0.4.3, 2026-01-13 | not read · 15.9k★ | Apache-2.0 | Telemetry on by default | — | **reject** — wrong fit, no commit in 7 months |
| stanford-crfm/helm | Benchmark suite for comparing models | 2026-06-05 | v0.5.16, 2026-04-29 | not read · 2.9k★ | Apache-2.0 | — | — | **reject** — compares models, not an app's prompt |

**Verdict for N5: none replaces the runner; they add ideas.** What makes troid's runner troid's — the critical/major/minor
read, the three-run promotion rule against the live baseline, candidate/live/patch routing, pacing under a visitor's
hourly limit, cost tied to recorded prices — exists in no framework, and porting it would cost more than the file
it replaces. Ideas worth taking, each a change to troid's own runner, not a dependency:

1. **Repeat each case k times per run** (inspect's epochs) and report a failure rate with a standard error. The owner's
   premise, "a few one-off slips per 24 answers", is a rate; rule (b) currently compares means with no error bar.
2. **A model-graded pre-screen** on the eval key that flags likely critical failures and scores "why it works" / "what
   it means for you" for the person's read. It marks cases for reading; it never writes `_errors` and never decides a
   promotion.
3. **Candidate-vs-live side by side per case** in the `.md` report.
4. **Cost and latency thresholds as checks**: an over-budget run fails.
5. **Hand-written adversarial variants** of the `s-*` (which firm or product), `u-*` (unread firm) and `o-*` (out of scope) cases in `character.json`.

## N6 — accessibility checks on the site

| repo | what it does | last commit | releases | used-by / stars | licence (as read) | keys / data / cost | overlap | verdict |
|---|---|---|---|---|---|---|---|---|
| dequelabs/axe-core | The WCAG rules engine every tool below wraps | 2026-09-23 | v4.13.0, 2026-08-05; monthly | dependents figure not trusted · 7.6k★ | MPL-2.0 | Runs in the page; no key, no data out (not verified in code), free | Adds a check the Playwright tests don't have | **adopt (as the engine)** — pin `axe.min.js` unmodified, inject with `page.add_script_tag`, call `axe.run()` from the existing Python Playwright tests: about ten lines, no wrapper |
| pamelafox/axe-playwright-python | Python wrapper: `Axe().run(page)` with a bundled axe | 2026-07-24 | 0.1.8, 2026-07-24 (bundles axe 4.12.1) | not read · 31★ | MIT (bundled axe keeps its MPL header) | None | Plugs straight into `web/test_desk.py`, `phone_check.py` | **trial** — zero-friction fit, but one maintainer and lags axe (upgrade issue open since 2026-08-29) |
| dequelabs/axe-core-npm | `@axe-core/playwright` for Playwright's Node API | 2026-09-02 | 4.13.0, 2026-08-11 | not read · 725★ | MPL-2.0 | None | JS only; troid's tests are Python | **watch** — only if the tests move to Playwright Test for Node |
| pa11y/pa11y | CLI runner on Puppeteer | 2026-08-28 | v10.0.0, 2026-08-28 | not read · 4.6k★ | LGPL-3.0 | None | A second browser stack | **reject** — LGPL, Puppeteer beside Playwright |
| GoogleChrome/lighthouse | Chrome audits including a subset of axe | 2026-09-18 | v13.5.0, 2026-09-17 | not read · 30.8k★ | Apache-2.0 | Local | Chrome only; can't audit the WebKit/iPhone layout | **reject** for this need |
| abhinaba-ghosh/axe-playwright | JS wrapper | 2025-09-12 | v2.2.2 | not read · 232★ | MIT | — | JS only | **reject** — a year idle |

**Top pick: axe-core directly.** MPL-2.0 is per-file copyleft: using axe unmodified at test time, with its header
intact, puts no obligation on troid's MIT code; only an edit to axe's own files would have to be published under
MPL. Rules are set through `axe.run` options, never by patching. A clean axe run is not a claim of WCAG conformance —
automated rules find only part of what WCAG covers — and the page must never say otherwise.

---

## jev-mcp — carried from the owner's review, re-read 2026-09-25

`jkudish/jev-mcp` connects TypeSafe's Jev model as MCP tools that return typed verdicts with probabilities.

**What changed since the owner's review.** Recorded then as a 10-star, one-maintainer proof of concept. Read
2026-09-25: created 2026-09-17, 346★, MIT, v0.8.0 released 2026-09-24, last commit 2026-09-25, outside contributors
credited in the changelog, eleven tools (was three). Still eight days old, and the changelog says "no versioning
policy has been declared yet; treat 0.x APIs as unstable". Growth is fast; maturity is not established. Providers:
TypeSafe direct (default), OpenRouter, Cloudflare Workers AI, Vercel AI Gateway — each a third party receiving the
text sent, each needing a key. Every result reports token use and estimated cost.

| tool | verdict | why |
|---|---|---|
| `jev_verify` | **trial candidate (N1, second layer)** | Monthly: the page-change layer says which pages changed; for those, `jev_verify` checks troid's recorded claims (`firms_evidence.json`) against the current text and returns supports / contradicts / says nothing. |
| `jev_compare` (new since the review) | **consider inside the same trial** | Judges two passages as same fact / contradicts / different facts — the recorded evidence quote against the page's current wording, with no claim restatement in between. |
| `jev_find` | **watch** (FAQ gaps) | Run the weekly digest's paraphrased topic labels against the FAQ and glossary; "absent" topics are candidate FAQ entries. Never visitors' messages. |
| `jev_screen` | **reject for now** | ask troid doesn't browse; the calendar reads government sites. |
| the other seven | **not evaluated** | No troid need for them. |

Conditions that stand, whatever the trial finds:

- **It flags; it never publishes.** A contradiction becomes a review item; a person or Code confirms against the page
  before a number changes. Its probability is not evidence; troid's evidence stays reproducible.
- **Exact figures are matched in code** ("4%", "$999"), which the repo's own README also recommends before sending
  anything to the model. Jev is for rules written in prose: hold-limit tiers, refund conditions, prohibited practices.
- **Trial design, if approved:** about 20 recorded Bitfunded rules with their source texts, including the known
  conflicts (refund wording differs between Terms 9(a) and the help centre; the Terms say 10 open positions, the help
  centre 5). Measure whether Jev's verdicts match what troid already knows, and the cost per run.
- **Before any trial:** read TypeSafe's pricing and data terms (retention, training on inputs) — or those of whichever
  provider is chosen; pin the install to a commit, not `main`; the key lives in Code's environment only, never on the
  public site; only firm pages and troid's own claims are sent, never a visitor's words.

---

## Earlier evaluations (seed)

| repo | verdict | why | note from the 2026-09-25 read |
|---|---|---|---|
| tradingview/lightweight-charts | adopted | Draws the ledger's trade charts. Computes/draws only. | Apache-2.0 with a NOTICE; its README asks every site using it to show the NOTICE attribution and a link to tradingview.com (the `attributionLogo` chart option satisfies the link). The ledger loads v4.2.3; whether its page meets this was not checked in this read. |
| ranaroussi/quantstats | adopted | The tearsheet over the shadow journal. | Apache-2.0 confirmed. |
| polakowo/vectorbt | watch → **trial (flagged), N4** | Fast backtests for shadow-2. | Licence re-checked: Apache-2.0 with Commons Clause. See N4. |
| jkudish/jev-mcp | trial (verify) / watch (find) / reject (screen) | See the section above. | Re-read; `jev_compare` added as a trial consideration. |
| TauricResearch/TradingAgents | reject | Its agents output trade decisions — troid never generates signals. | |
| virattt/ai-hedge-fund | reject | Trade decisions; stocks only; needs a second paid data key. | |
| alpacahq/alpaca-mcp-server | reject (crypto) / watch (TradFi read-only) | Crypto is spot and long-only; no 5× perps. | |
| CCXT-based MCP servers | reject | Small community projects; exchange testnets geo-restricted for US users. | |
| mvanhorn/last30days-skill | adopted (content research) | Topic monitoring for posts; data only, never strategy input. | |
| microsoft/playwright-mcp | adopted (read-only use) | Reading JS-rendered pages; never logged into trading accounts. | |
| tt-a1i/archify | adopted | Architecture diagrams for docs. | |
| garrytan/gstack | partial | Planning/review commands only; conflicts with other browser tools. | |
| msitarzewski/agency-agents | partial | Marketing and legal-review personas only; brand rules override them. | |
| AgriciDaniel/claude-ads | reject | troid runs no paid ads; affiliate contracts prohibit paid promotion. | |
| block/buzz | reject for now | Pre-1.0; hosted data; built for teams. | |

The seed rows other than those noted were carried as recorded and not re-read on 2026-09-25.

---

## Awaiting the owner's approval

Nothing below is installed or run until approved.

1. **N2 + N1, together:** add `trafilatura` (Apache-2.0) to the backtest requirements, and a monthly Actions job that
   reads each recorded source page with Playwright, extracts clean text and commits the snapshot, so a firm's edit
   shows as a dated git diff. Alternative: host changedetection.io (a server troid doesn't have).
2. **N1, second layer:** the `jev_verify` / `jev_compare` trial on ~20 Bitfunded rules — after the provider's pricing
   and data terms are read and a provider and key are chosen.
3. **N3:** add `arch` and `statsmodels` for SPA / StepM / block bootstrap and multiple-testing correction in the
   shadow-2 method; write DSR and PBO in troid's own code from the papers.
4. **N4:** a timing trial — the existing engine over ten assets first; vectorbt in a separate environment only if that
   is too slow, and only with the Commons Clause accepted as a condition.
5. **N5:** which runner ideas to build (repeated runs with an error bar are the first candidate; a graded pre-screen
   would spend eval-key budget).
6. **N6:** vendor `axe.min.js` (MPL-2.0, unmodified) into the Playwright tests, or take the pamelafox wrapper.
7. **Seed check:** confirm the ledger page carries lightweight-charts' NOTICE attribution and tradingview.com link.

## Re-checks

The watch list (mozilla/readability, crawl4ai, bt, promptfoo, axe-core-npm, alpaca-mcp-server, jev-mcp's `jev_find`)
and every trial are re-read for licence changes, activity and releases before any change of verdict. Each re-read adds
its date here.
