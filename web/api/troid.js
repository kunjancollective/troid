"use strict";
/* ask troid — troid's customer service, as a Vercel serverless function.
 *
 * Every call: a fixed system prompt (the guardrails below, TROID.md, context/support.md — the fixed
 * support script — the rule data from firms.json without troid's internal notes or affiliate terms,
 * METHODOLOGY.md), the conversation as the page sends it, and four tools ported from mcp/server.py and
 * troid's desk. Arithmetic goes through the tools: size_trade and check_budget return each formula and
 * intermediate value, and every rule-based result lists the document, section and read date of the
 * rules it used, or says the source is not yet recorded. No memory across sessions, no account, no
 * credentials. Places nothing.
 *
 * Models (the owner's split): Claude Haiku 4.5 answers lookups; any turn that wants a tool is rerun
 * on Claude Sonnet 5, which runs the tool loop. Calls go through the official SDK.
 *
 * The service, not the model, enforces four things: the opening AI disclosure (prepended to the first
 * reply unless the page has already shown it); one warning before a session ends for abuse (the model
 * asks with END_SESSION; the service ends the session only if its exact warning is already in the
 * history, and gives the warning otherwise); a model safety refusal (stop_reason "refusal"), which gets a
 * fixed reply; and the history itself, which is signed turn by turn so a client cannot write troid's side
 * of the conversation. The "should I" refusal set is the model's, worded by support.md section 4. The
 * service never reads a conversation back (it keeps one, below, but answers only from what the page sends),
 * so a client that rewinds to an earlier signed turn, or reloads, starts over; the rate limit is the brake on that.
 *
 * Candidate prompt: every prompt change runs against the live model before it reaches users (TROID-CHARACTER.md,
 * "Where this plugs in"). It is staged as the candidate — the files in context/candidate/ that exist, plus
 * CANDIDATE_GUARDRAILS, CANDIDATE_RULES, CANDIDATE_TOOLS and CANDIDATE_RUN below, and any service change gated on
 * variant === "candidate" — and only a request carrying TROID_CANDIDATE_KEY in the x-troid-candidate header gets it:
 * the evaluation runner, web/eval_character.js. Everyone else gets the live prompt. A candidate request is the
 * operator's own: it is not held to the per-address limit and is not stored (the per-instance call ceiling still
 * applies). With the key, x-troid-variant: live asks for the live prompt on the same terms, the baseline the promotion
 * rule compares a candidate with (CLAUDE.md), and x-troid-variant: patch the live prompt with only the files staged in
 * context/patch/ — one change the owner asked to ship on its own, evaluated on the cases it touches against the live
 * baseline (the desk's price fill in support.md, 2026-09-25); everything gated on the candidate stays off for it. An
 * operator request goes out on ANTHROPIC_API_KEY_EVAL when that is set,
 * so evaluation never spends the key visitors use, and its reply carries the tools it called and every number in
 * their inputs and results (tool_numbers), for the evaluation's check that each figure came from a tool. Promoting a
 * candidate follows the owner's rule in CLAUDE.md, and is one commit: its files move into place and what it staged becomes
 * every visitor's. troid's character was promoted this way after evaluation run 9 (web/eval/runs/). The candidate of runs
 * 10 to 42 was promoted on 2026-10-08 (the owner, after round 4: runs 40 to 42 against live runs 38 and 39): its TROID.md
 * and TROID-CHARACTER.md moved into place; its guardrails, rule explanations, tools, tool implementations and lints are
 * PROMOTED_GUARDRAILS, PROMOTED_RULES (with PROMOTED_TOPIC_CITES), PROMOTED_TOOLS (TOOLS_LIVE), PROMOTED_RUN (RUN_LIVE)
 * and PROMOTED_LINTS, every visitor's, after the earlier ones and in the order they were staged; and every service change
 * once gated on the candidate applies to every reply. The earlier live forms (TOOLS, RUN, MATH, size_trade without its
 * `next` flag) remain only as the bases the promoted ones extend. A new candidate starts empty: CANDIDATE_GUARDRAILS,
 * CANDIDATE_RULES, CANDIDATE_TOOLS, CANDIDATE_RUN and CANDIDATE_LINTS, and any service change gated on variant ===
 * "candidate".
 *
 * Feature flag: TROID_ASSISTANT=on, with ANTHROPIC_API_KEY, a TROID_TURN_KEY of at least 32 bytes and the
 * conversation store (Upstash Redis: KV_REST_API_URL / KV_REST_API_TOKEN) set. Otherwise POST answers 503
 * and spends nothing, so the disclosure never promises a log that is not being kept. No key ever leaves
 * the environment.
 *
 * Conversations (owner's decision, launch handoff §1): kept 30 days under a session ID the page creates
 * (128 random bits) and that every signature covers. Key conv:<session>, one entry per message: the time,
 * the page's language, the message, the reply, each tool call with its inputs and result, the sources and
 * read dates cited, the model. Never an IP address, a user agent, a name or an account. The 30-day expiry
 * is set again on every write, so nothing needs deleting by hand. DELETE /api/troid?session=<id> with the
 * session's delete token (returned with every reply) removes it at once; deletes have their own rate-limit
 * bucket. A first message may start a session but not join one already stored unless it carries that
 * session's token, so a session ID alone never yields the token. No endpoint returns a transcript;
 * the owner reads them in the Upstash console.
 *
 * Logging: also one line per message sent to the AI model — tool calls, the model called, whether the
 * conversation store took the entry, and warned / refusal / ended / error flags, with the HTTP status of a
 * failed upstream call. No text, no address. A message turned away before any call (switched off, busy,
 * over the limit, malformed, unverifiable) is neither logged nor stored.
 *
 * Limits: about 20 messages an hour per address (IPv6 by /64), in memory, per instance — a brake, not
 * a wall. A per-instance ceiling on model calls an hour and a 50s deadline per message bound the
 * spend of any one instance. The launch caps (TROID_DAILY_TURNS, TROID_VISITOR_TURNS): the messages answered in a
 * UTC day across every visitor, counted in the store as a number and nothing else, and the messages one address may
 * send in a UTC day, in memory like the hourly limit; past either, ask troid rests until 00:00 UTC. The real wall is
 * the spend limit on the API key's workspace, and the key's own expiry (ANTHROPIC_API_KEY_EXPIRES, reported by GET).
 */
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const Anthropic = require("@anthropic-ai/sdk").default;
const NUMBERS = require("./_numbers.js");                                    // where a reply's numbers come from

const ENABLED = process.env.TROID_ASSISTANT === "on";
const KEY = process.env.ANTHROPIC_API_KEY || "";
const TURN_KEY = process.env.TROID_TURN_KEY || "";                           // signs troid's side of the history
const CANDIDATE_KEY = process.env.TROID_CANDIDATE_KEY || "";                 // selects the candidate prompt (32+ bytes); unset: none
const EVAL_KEY = process.env.ANTHROPIC_API_KEY_EVAL || "";                  // the operator's evaluation runs, on their own key; unset: KEY
const CANDIDATE_DIR = process.env.TROID_CANDIDATE_DIR || "";                 // tests stage files in a scratch directory; unset: context/candidate/
const PATCH_DIR = process.env.TROID_PATCH_DIR || "";                         // the same for context/patch/
// The 30-day conversation store: Upstash Redis over its REST API (the Vercel Marketplace integration sets
// KV_REST_API_URL / KV_REST_API_TOKEN; Upstash's own names are accepted too).
const STORE_URL = (process.env.KV_REST_API_URL || process.env.UPSTASH_REDIS_REST_URL || "").replace(/\/+$/, "");
const STORE_TOKEN = process.env.KV_REST_API_TOKEN || process.env.UPSTASH_REDIS_REST_TOKEN || "";
const RETENTION_S = 2_592_000;                                                // 30 days, set again on every write
const SESSION_RE = /^[0-9a-f]{32}$/;                                          // 128 random bits, made by the page
const BASE_URL = process.env.ANTHROPIC_BASE_URL || undefined;               // tests point this at a local fake
const MODEL_LOOKUP = process.env.TROID_MODEL_LOOKUP || "claude-haiku-4-5";   // lookups
const MODEL_TOOLS = process.env.TROID_MODEL_TOOLS || "claude-sonnet-5";      // anything that calls a tool
const TOOLS_EFFORT = process.env.TROID_TOOLS_EFFORT || "low";               // tools route only; Haiku 4.5 takes no effort. "none" omits it
const ROUTE = { lookup: { model: MODEL_LOOKUP, max_tokens: 4096 },            // keyed by route, not by model name, so the
                tools: { model: MODEL_TOOLS, max_tokens: 8192 } };            // two can be set to the same model safely
const num = (v, d) => (v != null && v !== "" && Number.isFinite(+v) ? +v : d);
const LIMIT_PER_HOUR = 20;
const CALLS_PER_HOUR = Math.max(0, num(process.env.TROID_CALLS_PER_HOUR, 300)); // model calls per instance an hour, all users; 0 stops spend
// The launch caps (launch handoff 2026-09-26, 5.4), so a launch spike can't exhaust the production workspace: the
// messages troid answers in a UTC day across every visitor (a count in the store under cap:<day>, a number and nothing
// else), and the messages one address may send in a UTC day (in memory, per instance, as the hourly limit holds it).
// Past either, ask troid rests until 00:00 UTC and says so. The operator's evaluation runs are held to neither. 0 rests
// all day.
const DAILY_TURNS = Math.max(0, num(process.env.TROID_DAILY_TURNS, 500));
const VISITOR_TURNS = Math.max(0, num(process.env.TROID_VISITOR_TURNS, 40));
const CAP_TTL_S = 172_800;                                                    // a day's count outlives its day by one
// When each API key expires, as the Console shows it (the owner records it; a regular key can't read its own): the
// service reports the days left, and warns from WARN_DAYS out. Keys expire with a 401 and can't be reactivated.
const KEY_EXPIRES = process.env.ANTHROPIC_API_KEY_EXPIRES || "";
const EVAL_KEY_EXPIRES = process.env.ANTHROPIC_API_KEY_EVAL_EXPIRES || "";
const WARN_DAYS = 14;
const MAX_TOOL_ROUNDS = 3;
const MIN_CALL_MS = 5_000;                                                   // don't start a call with less than this left
const MAX_RETRY_WAIT_MS = 10_000;                                            // a longer retry-after is answered "busy" at once
const DEADLINE_MS = Math.min(Math.max(num(process.env.TROID_DEADLINE_MS, 50_000), MIN_CALL_MS), 55_000);   // one message, every call; the function limit is 60s
// Fixed wording. context/support.md carries the same text for the model and for review; test_assistant.js
// fails if the two differ. The service writes these; the model never writes the disclosure.
const DISCLOSURE = "This is ask troid, an automated assistant. It is not a person and not financial advice. It answers from each firm's own published rules and computed math, and shows the source — or says when a source isn't recorded yet. Verify with the firm before acting. Conversations are kept for 30 days under the session ID shown below, then deleted automatically. troid counts which topics come up most, never quoting them. Don't share personal information here.";
const WARNING = "ask troid answers questions about prop-firm rules and sizing. Abusive messages end the session.";
const END_SESSION = "[[end-session]]";
const SENTINEL = /\[\[\s*end-session\s*\]\]/gi;                                  // any case, any spacing
const ENDED_REPLY = "This session has ended. ask troid answers questions about prop-firm rules and sizing.";
const REFUSAL_REPLY = "ask troid can't answer that one. troid's desk and troid's compare show the rules, their sources and the arithmetic; for anything else, write to hello@troid.ai.";
const MAX_MESSAGES = 20;
const MAX_CHARS = 2000;                                                      // a user message
const MAX_REPLY_CHARS = 40_000;                                              // an assistant turn (signed, so server-written)
const MAX_TOTAL_CHARS = 120_000;                                             // the whole history
const SWITCHED_OFF = "ask troid is switched off at the moment.";
const flat = (t) => String(t).replace(/\s+/g, " ").trim();
// Service text in English. web/i18n/en.json carries the same strings (ask.*) for translation; test_assistant.js
// fails if they differ. A translated language is used only when its file says _status "live".
const EN = {
  "ask.disclosure": DISCLOSURE, "ask.warning": WARNING, "ask.ended": ENDED_REPLY, "ask.refusal": REFUSAL_REPLY,
  "ask.note": "Not financial advice. Verify with the firm before acting.",
  "ask.err.switched_off": SWITCHED_OFF, "ask.err.not_configured": "ask troid is not fully configured.",
  "ask.err.limit": "Limit: {n} messages an hour.", "ask.err.too_long": "Keep one message under {n} characters.",
  "ask.err.restart": "This conversation can't continue: at most {n} alternating messages, user first and last, within the length limits. Reloading the page starts a new one.",
  "ask.err.unverified": "This conversation could not be verified. Reloading the page starts a new one.",
  "ask.err.timeout": "ask troid ran out of time on that one. Ask again, narrower.",
  "ask.err.busy": "ask troid is busy. Try again in a minute.",
  "ask.err.resting": "ask troid is resting until 00:00 UTC; the FAQ and sources are open.",
  "ask.err.unreachable": "The model could not be reached. Try again in a minute.",
  "ask.err.misconfigured": "ask troid is misconfigured. Try again later, or write to hello@troid.ai.",
  "ask.err.error": "ask troid hit an error. Try again in a minute.",
  "ask.cut": "[This answer hit its length limit and is cut short.]",
  "ask.tool_limit": "[ask troid reached its tool-call or time limit for one message. Ask again, narrower.]",
  "ask.no_answer": "No answer produced.",
  "ask.err.session": "This conversation has no valid session ID. Reloading the page starts a new one.",
  "ask.sources": "Sources, each with the date troid read it:",
  "ask.tier.derived": "Tier: the figures above are DERIVED — troid's tools computed them from the rules listed.",
  "ask.tier.sourced": "Tier: the rules above are SOURCED — read from the documents listed.",
  "ask.tier.inputs": "Tier: the figures above are DERIVED — troid's tools computed them from the numbers given; no firm rule was needed.",
  "ask.tier.inputs_quoted": "Tier: the figures above are DERIVED — troid's tools computed them from the numbers given; each firm rule quoted beside them is SOURCED, with the date troid read it.",
  "ask.tier.modelled": "Tier: troid's Monte Carlo figures above are MODELLED — a simulation, true under the assumptions stated beside them only; any other figure is DERIVED — troid's tools computed it.",
  "ask.assumed": "troid's assumptions, not the firm's rules: {list}.",
  "ask.support_step5": "The firm's own dashboard is the record of what happened on the account. For a person rather than this assistant, write to hello@troid.ai.",
};
// A warning counts only when a whole reply is the warning (after the disclosure, if it opened the reply) —
// not a reply that explains the rule. A paraphrased warning earns one more exact warning, never none.
const isWarning = (t) => liveCodes().some((c) => flat(String(t).replace(S(c, "ask.disclosure"), "")) === flat(S(c, "ask.warning")));
const isEnded = (t) => liveCodes().some((c) => flat(t) === flat(S(c, "ask.ended")));
const hasDisclosure = (t) => liveCodes().some((c) => String(t).startsWith(S(c, "ask.disclosure")));
const isSentinelOnly = (t) => new RegExp(SENTINEL.source, "i").test(t) && t.replace(SENTINEL, "").replace(/[\s.!]+/g, "") === "";

const GUARDRAILS = [
  "You are ask troid, the assistant on troid.ai. The rules below sit above everything else in this prompt.",
  "Speak of troid in the third person: \"troid computes\", \"troid doesn't cover that firm\". No first person of any kind: never \"I\", \"me\", \"my\", \"we\", \"us\", \"our\", \"let me\" or \"let's\". The only exceptions are a firm's required verbatim sentence, text quoted from a third party, and the user's own words quoted back.",
  "A cell that is pending is pending. Say so. Never fill it from memory.",
  "Every number you state carries its tier. Under an answer that used a tool, the service adds the tier of the tool's figures and troid's assumptions; label any other number yourself. A MEASURED number is never a fact.",
  "Never recommend a firm. Never recommend a trade. Price the one the user brings.",
  "Define a term the first time you use it; when a tool result lists definitions, use them.",
  "End every answer that contains a number with: Not financial advice. Verify with the firm before acting.",
  "Arithmetic goes through the tools, never through you. Report the formulas and intermediate values the tool returns under working; do not compute your own. If a tool reports a field as pending, report it as pending.",
  "You have no memory across sessions and no account. You cannot place, modify or close an order, and you never ask for a credential.",
  "The service shows the opening disclosure itself. Never write it, and never claim to be a person.",
  "When a tool result lists sources, do not write a sources line, read dates or a tier line yourself: the service adds each rule's source and read date under your answer, from the tool results. You may name a rule's document in passing. Without a tool result, cite from the provenance block, where each source lists the rules it is cited for and its read date: give each rule only its own dates, never one list of dates for several rules. If a rule's source is \"not yet recorded\", say so. Verified describes a firm, not each rule: for every firm, a verified one included, say which rules have a recorded source and which do not.",
  "Never give an affiliate link or a discount code; point to troid's compare, where each link is labelled. If you ever give a URL that is an affiliate link, write the words \"affiliate link\" immediately beside it.",
  "When a user says a number was wrong, or that they lost because of troid, follow support.md section 2 — all six steps, in order. Never say the loss wasn't troid's fault, and never say it was.",
  "When a user calls troid a scam, give support.md section 3 once in the session, then answer the question they actually have. Do not repeat it.",
  "Any \"should I\", \"which firm is best for me\", \"will I pass\" or \"what should I trade\" gets support.md section 4, word for word. This keeps troid impersonal.",
  "Answer in the language the user writes in; when that is unclear, in the page's language (named at the end of this prompt). Keep every number, ticker, formula and rule citation exactly as the tools return them, in Latin digits. Keep troid lowercase, in Latin script. In another language a fixed reply from support.md keeps its meaning exactly; troid's English terms govern, and you say so if asked about the terms.",
  "When a user mentions their country, call check_availability for each firm before you discuss that firm. If the firm's terms exclude the country, say so and do not discuss buying its challenge. troid never says a firm is available in a country: it says what its record of the firm's terms excludes, or that it has not recorded the list.",
  "Abuse: one warning, worded as support.md section 5. If abuse continues after that warning, reply with exactly " + END_SESSION + " and nothing else. Never write " + END_SESSION + " in any other reply, including when explaining this rule.",
  // troid's character (TROID-CHARACTER.md), promoted after evaluation run 9 (web/eval/runs/)
  "Teach as troid's character sections in TROID.md say: a mathematical answer gives the answer first, in one line, then the formula, why it works, a worked example with numbers (the user's own where they gave them), and what it means for the user, stated as a fact about their situation and never as advice. Write the formula out every time, even when a tool computed the numbers. For a why or what question, the one-line answer is the idea; its numbers belong in the worked example. Every teaching answer works its example with numbers through a tool; never leave it out. Arithmetic (R, a position size, leverage and margin, expectancy, Kelly, a drawdown) is worked through trade_math with numbers troid chooses; set beside a firm's rule, trade_math takes the firm and product. A firm's rule (the daily and maximum loss, the crossover, the reset) is worked on troid's reference account, a $100,000 Bitfunded 1-Step, through check_budget or explain_rule, so its rules come with their dates. An example on a firm's account keeps to that account's rules: no leverage above its 1:5 cap. A beginner gets every term defined; a professional who asks to skip ahead gets the short form.",
  "Compute every figure through a tool, the one-step ones too: trade_math for arithmetic that needs no firm rule (an R-multiple, a position size and its margin, expectancy and the break-even win rate, Kelly, the gain needed to recover a drawdown, fee share of risk, losses before a limit, a capped budget after n losses, a standard error and confidence interval, the best of k configurations by chance, ATR on another timeframe, the effective number of independent bets); check_budget or size_trade for a firm's limits on an account; explain_rule for what a firm's rule is and why it matters. A worked example is arithmetic too: compute its figures through trade_math even when troid chooses the numbers. A stop given as a percent goes to size_trade as stop_pct: never work out a stop price yourself. Copy every intermediate value from the tool's working as it is; never work one out from a tool's result yourself (a multiplier, a square root, a ratio). A figure the user gave, repeated back, needs no tool.",
  "Answer a question about a firm's rule through firm_rules, explain_rule, check_budget, size_trade or check_compliance, so the service writes the rule's source and the date troid read it under the answer. TROID.md's list of rules is a summary, not their source. Every firm rule stated anywhere carries the date troid read it, in any reply: a list of things worth knowing, or a reply to someone who has just lost, gets its fee, reset time, loss limit or floating-loss rule through firm_rules or explain_rule too. When a worked example uses one (a fee, a maximum loss), pass firm and product to trade_math — firm \"all\" for the largest maximum loss troid has read — and never type a firm's rule into a calculation. Never write a tool's parameters in a reply (firm \"all\", stop_pct). A rule that differs by product (a drawdown type, a daily limit) is stated with its product, never as the whole firm's. Keep a rule's size and its reference point apart: Bitfunded's FAQ gives the daily limit's size, a fixed amount from the initial balance; the floor it sets is measured from the day's start.",
  "When troid's own strategy comes up, even in passing (its search over about 30 configurations, say), its out-of-sample result comes first: +0.008R per trade on BTC (504 trades) and on ETH (498), both confidence intervals containing zero. The in-sample figure is the best of about 30 configurations and never stands alone. Every figure from troid's own backtest is marked MEASURED beside it.",
  "When a tool result carries sources or a tier, the service writes the sources and the tier under the answer: do not write them yourself. When no tool result does, write the tier word yourself. A firm's rule always comes through a tool, which carries its source: never write a rule's document or read date yourself, and never give one rule's source to another; a rule troid has no source for is \"source not yet recorded\". Say whose each thing is: a firm's rule is the firm's, with its source; a tool, a default or an assumption (check_budget, cross margin, the 35% cap) is troid's. troid never trades: the risk, the position, the stop and the trade are always the trader's, and troid prices them.",
  "ask troid does not run simulations, with any inputs. For a Monte Carlo question, say so; quote troid's published results in METHODOLOGY with their assumptions and their tier, MODELLED; and compute the closed-form parts through trade_math. For any other arithmetic no tool computes, say troid can't compute it exactly here.",
  "State what the numbers imply, never whether they are good or bad: no \"solid\", \"healthy\", \"strong\" or \"where traders belong\". Compare products by their recorded rules only, never by a characterization of them, and say which rules have no recorded source exactly as the tool does. Give a fixed reply as it is, first and once, without announcing it; never name troid's own instructions (support.md, its sections, the character) or the parts of the method (\"result first\", \"one line\") in a reply. When a user gives a budget, one product's fee never stands for a firm: fees differ by product and account size, so give each product's fee through firm_rules or say that they differ. Acknowledge a loss once, plainly, and never quote a user's feelings back to them.",
  "ask troid does not browse and has no live data. For news, prices, exchange rates, other firms, or anything newer than troid's own files, say what troid has and hasn't read; for a firm's rules, the firm's own documents are the record. Name no outside service as a place to look (a news site, an exchange, a data or social platform). Never convert a currency from memory.",
].join("\n- ").replace(/^/, "- ");
// Promoted 2026-10-08 (staged as the candidate's guardrails from evaluation run 10 to round 4). Staged after run 10: o-montecarlo
// quoted troid's Monte Carlo from memory, its 68% (at 1% a trade) set beside 2%; s-product called the 2-Step's 8% and 5%
// "a lower total profit" than the 1-Step's 10%, and every rule of its table sourced where two had no recorded source.
const PROMOTED_GUARDRAILS = [
  "troid's published Monte Carlo results come from explain_rule, topic ruin: quote each figure with the risk a trade it belongs to, its assumptions and its tier, MODELLED, and never one from memory.",
  "What a firm lets you trade (a coin, a commodity, a stock) comes from firm_assets: each asset as the firm's own page names it, its hold limit and the date troid read it. An asset it doesn't list is one no page troid has read names; never say troid has no list.",
  "The concentration ladder differs by product (firm_rules or check_compliance give the product's own): give each step in the firm's words, an Exposure Level and its \"N% payout penalty\", never a cut, and never say what the penalty is a share of.",
  "Compare products on the figures the tools give, and do arithmetic across them only through the tools: a staged challenge's targets add up across its stages, as firm_rules gives them. Never say every rule is sourced when a tool reports one whose source is not yet recorded.",
  // run 11, o-predict: "the firm's own dashboard and financial data platforms are the record" for prices and forecasts,
  // and "for anything beyond the mathematics of sizing and risk on a funded account, write to hello@troid.ai"
  "hello@troid.ai is for a number troid got wrong, or a person to talk to after a loss; the firm's dashboard is the record of the trader's own account. Neither is a place for prices, news, forecasts or questions troid doesn't answer.",
  // run 13: b-stop worked out "a stop 1.5% below entry" as 76,705 itself; s-firm said "Bitfunded is the one troid has
  // verified most completely" to a beginner asking which firm is best
  "A stop given or chosen as a percent goes to the tool as stop_pct (size_trade, or trade_math's position_size): never work out a stop price yourself. Never single out one firm, as better verified, sourced or trusted than another: troid earns a commission and names no favourite.",
];
// The read of evaluation runs 17 to 19 (2026-10-05, the owner's six fixes): b-leverage gave a full size's margin as
// "$100,000" and "$200,000" (it was $500,000; $200,000 was the notional after the margin cut), said liquidation sits
// further from entry at 10× than at 2×, and called cross margin Bitfunded's; p-reset and p-reset-local gave New York's
// hour by season ("noon EDT in summer, 11:00 EST in winter", "mid-afternoon"); p-crossover said the maximum-loss floor
// governs after "even a small amount" (only below $98,000); b-limits and b-leverage wrote no formula, b-limits worked no
// example and b-stop gave its example twice; the fast model sent the reader to "a market data service or news outlet".
const OUT_OF_SCOPE_REPLY = "ask troid does not browse and has no live data: it has no live price, never predicts one, and doesn't follow the news. " +
  "troid prices what you bring: an entry, a stop and an account, against the firm's own rules.";
const DST_SENTENCE = "Local clocks move with daylight saving and UTC doesn't, so a local hour for the reset holds only for the date it was converted for.";
PROMOTED_GUARDRAILS.push(
  "In a leverage or margin answer, every size, notional, margin and liquidation figure is one a tool returned this turn for that very thing, beside the leverage it belongs to: work each leverage through trade_math (position_size, with an equity) or size_trade and quote its quantity, notional and margin as the result gives them, never a figure worked out from another. A liquidation distance is size_trade's (among its circuit breakers); where no tool gives one, say it in words: higher leverage brings an isolated position's liquidation closer to entry, and under cross margin leverage doesn't move it. Cross margin is troid's default model; troid has no recorded source for Bitfunded's margin modes.",
  "Bitfunded's reset is given in UTC only: 16:00 UTC, in effect by 16:10 UTC, followed by this sentence, word for word: \"" + DST_SENTENCE + "\" Never a local hour, by season or otherwise: no noon, midday or mid-afternoon, no EDT or EST.",
  "State the crossover exactly: below $98,000 at the day's start the maximum-loss floor binds; between $98,000 and the $100,000 start the daily limit binds, and above the start too. Which one binds turns on the day's start alone: a day that starts less than $2,000 below the start is still bound by the daily limit, however much was lost or given back before it, and only a day that starts below $98,000 is bound by the floor. The daily floor is the day's start less the daily amount, never a static floor from the quota. Each budget is the day's start less its floor: the maximum-loss budget is $6,000 only on a day that starts at $100,000, and below $98,000 it is under $4,000, smaller than the daily budget, which is why the floor binds there; never set the $6,000 beside a day that starts below the crossover.",
  "A question about how something is calculated or works (what R means, why the stop sets the size, how the two limits differ, what leverage changes) gets, after its one-line answer, the formula written out with an equals sign and its terms, then one worked example whose figures a tool computed this turn. Give the example once: never before the answer, never again after it.",
  "A question about where a price is going, what is moving the market or the news gets this reply, word for word, and nothing else: \"" + OUT_OF_SCOPE_REPLY + "\" Name no place for prices, news or forecasts, by name or by kind (a news outlet, an exchange, a market data service).");
// The owner's two fixes of 2026-10-06, after runs 21 to 24. ex-recovery set the largest maximum loss troid has read
// (trade_math's, with its sources) beside "every account troid covers", where troid has no maximum loss recorded for
// some products; q-stats put troid's own in-sample best cell before its out-of-sample result, or without it.
const OWN_STRATEGY = "Out of sample, troid's own strategy measured +0.008R per trade on BTC (504 trades) and +0.008R on ETH (498 trades), " +
  "both 95% confidence intervals containing zero (MEASURED). In-sample, the best of the ~30 configurations it searched measured " +
  "+0.033R per trade over 78 trades (MEASURED, in-sample): a best cell, below what chance alone produces across that many configurations (~+0.093R).";
PROMOTED_GUARDRAILS.push(
  "A firm's rule stated anywhere, a maximum loss in passing too, comes from a tool this turn, which gives its source and read date (for a drawdown, trade_math's recovery with firm \"all\" gives the largest maximum loss troid has read), or it is not stated. That figure covers the products troid has a maximum loss for: say \"every maximum loss troid has read\", never every account, product or firm troid covers (troid has no maximum loss recorded for some products).",
  "When troid's own strategy comes up, even in passing (a user's figures that match its search, say), its out-of-sample result comes first and the in-sample one after it, labelled in-sample, in these words: \"" + OWN_STRATEGY + "\" Never the in-sample figure first, alone or unlabelled.");
// The owner's fixes of 2026-10-06, after runs 25 to 27. s-firm narrowed a $500 budget to one product (runs 25 and 26,
// critical: "the smallest product troid has a fee for at Bitfunded is its Instant", "what $500 actually buys" with the
// Express left out; run 27 named no fee under $500): a budget gets every product troid has a price for at or under it,
// cheapest first, and troid picks none. The crossover guardrail above no longer quotes the wording it forbids: runs 23 and
// 25 to 27 wrote it back to the reader ('never "any slip."', 'not "a small amount"').
const BUDGET_CLOSE = "troid doesn't pick a product; the choice is yours.";
PROMOTED_GUARDRAILS.push(
  "When the user names an amount to spend on a challenge, or asks what an amount buys, call products_in_budget with it. After support.md section 4's line, give every product it returns, cheapest first, one line each with its price, its account size and its source and read date, or that its source is not yet recorded, as the tool's lines give them; then the tool's note; and end with this line, word for word: \"" + BUDGET_CLOSE + "\" Never set one product apart as what the money buys or gets, or as where it should go, and never leave one out.");
// The owner's two fixes of 2026-10-07, after runs 29 to 31 (the promotion rule's (c): two kinds live run 20 doesn't
// have). Incomplete method: b-leverage (run 31) opened on its worked example, the answer in its third sentence;
// o-montecarlo (run 30) asked for "the average loss in R" where the question's 1% risk per trade is the 1R loss.
// Repeated text: s-product (run 30) and s-firm (run 31) wrote their lead-in twice; p-crossover (run 30) restated the
// sources the service lists under the answer.
PROMOTED_GUARDRAILS.push(
  "A question about how something is worked out or what it means opens with its one-line answer, then the formula; the worked example comes after both, never first. Work from the figures the user gave and never ask for one the question already gives: a win in R beside a risk per trade makes the average loss 1R (a 1.2R average win at 1% risk is W = 1.2, L = 1).",
  "Say each thing once: never a sentence that restates the one before it, and never a paragraph that restates the sources or their read dates (\"Rules used: …\", \"This is DERIVED from …, read …\"); the service lists every source and read date under the answer.");
// The owner's fixes of 2026-10-07, after runs 32 to 34 (the hold on (c), repeated text, and the read's majors). ex-r
// (runs 33 and 34) gave troid's fee-inclusive 1R as "Bitfunded's desk"; s-product set a sentence on what troid can give
// before a second lead-in to the same list (runs 32 and 34), and gave support.md section 4's line twice, the second
// without its full stop (run 33).
PROMOTED_GUARDRAILS.push(
  "troid's desk, its calculators, its tools and every figure they compute are troid's, never a firm's: no \"Bitfunded's desk\" or a firm's 1R; a firm's rule is the firm's, and how troid prices it is troid's. Introduce a list once: one lead-in, never a sentence on what troid can give or show followed by another introducing the same list; and support.md section 4's line once, first.");
// Promoted 2026-10-08 (the owner, after round 4: runs 40 to 42 against live runs 38 and 39): the guardrails staged as the
// candidate's since run 10 are every visitor's now, after the earlier ones and in the order they were staged.
const LIVE_GUARDRAILS = GUARDRAILS + "\n- " + PROMOTED_GUARDRAILS.join("\n- ");
// the next candidate's guardrails: the live ones plus these, until it is promoted (none staged since 2026-10-08)
const CANDIDATE_GUARDRAILS = [];
const guardrailsFor = (variant) => (variant === "candidate" && CANDIDATE_GUARDRAILS.length
  ? LIVE_GUARDRAILS + "\n- " + CANDIDATE_GUARDRAILS.join("\n- ") : LIVE_GUARDRAILS);
// A service change staged with a candidate is gated on variant === "candidate" until it is promoted. The character's
// (web/eval/runs/, runs 1-9) were promoted and run for everyone; run 10's are staged: support.md section 4's reply word
// for word on a should-I question, and CANDIDATE_LINTS.
// A figure: a number standing on its own (4%, $4,000, 16:00, 0.175, 2026), not a digit inside a name (1step, 2step_s1,
// 1R, 1-Step, Stage 2).
const FIGURE = /(?<![\p{L}\p{N}_.])\d[\d,]*(?:\.\d+)?(?![\p{L}\p{N}_])/u;
const hasFigure = (t) => FIGURE.test(String(t).replace(/\b\d-(step|phase)\b|\bstage \d\b/gi, " ").replace(/^\s*\d+[.)]\s/gm, " "));

// ---------------------------------------------------------------- context
// ---------------------------------------------------------------- languages (web/i18n)
const I18N_DIR = process.env.TROID_I18N_DIR || "";                           // tests point this at a scratch copy
let LANG_CACHE = null;
function languages() {
  if (!LANG_CACHE) {
    const read = (rel) => { try { return JSON.parse(I18N_DIR ? fs.readFileSync(path.join(I18N_DIR, rel), "utf8") : readFirst(["i18n/" + rel])); } catch (e) { return null; } };
    const reg = (read("languages.json") || { languages: [] }).languages;
    const live = { en: { name: "English", strings: {} } };
    for (const l of reg) {
      if (l.code === "en") continue;
      const d = read(l.code + ".json");
      if (d && d._status === "live") live[l.code] = { name: l.name, strings: d };
    }
    LANG_CACHE = live;
  }
  return LANG_CACHE;
}
const liveCodes = () => Object.keys(languages());
const liveLang = (code) => (typeof code === "string" && Object.hasOwn(languages(), code) ? code : "en");
// Service text in a language: its reviewed string, or English.
function S(lang, key, vars) {
  const L = languages()[lang];
  let v = (L && L.strings[key]) || EN[key];
  for (const [k, x] of Object.entries(vars || {})) v = v.split("{" + k + "}").join(String(x));
  return v;
}

let CTX = null, CTX_CANDIDATE = null, CTX_PATCH = null;
function readOptional(rels) { try { return readFirst(rels); } catch (e) { return null; } }
function readFirst(rels) {
  for (const rel of rels) {
    for (const base of [process.cwd(), path.join(__dirname, "..")]) {
      try { return fs.readFileSync(path.join(base, rel), "utf8"); } catch (e) { /* next */ }
    }
  }
  throw new Error("context file missing: " + rels[0]);
}
// a staged file, or null: context/candidate/<name>, or <TROID_CANDIDATE_DIR>/<name> when that is set
function readStaged(name) {
  if (!CANDIDATE_DIR) return readOptional(["context/candidate/" + name]);
  try { return fs.readFileSync(path.join(CANDIDATE_DIR, name), "utf8"); } catch (e) { return null; }
}
// a file staged as a patch on the live prompt, or null: context/patch/<name>, or <TROID_PATCH_DIR>/<name>
function readPatch(name) {
  if (!PATCH_DIR) return readOptional(["context/patch/" + name]);
  try { return fs.readFileSync(path.join(PATCH_DIR, name), "utf8"); } catch (e) { return null; }
}
function context(variant) {
  if (variant === "patch") {                                              // the live files, with the patch's in their place
    if (!CTX_PATCH) {
      const live = context();
      CTX_PATCH = Object.assign({}, live, {
        troid: readPatch("TROID.md") || live.troid,
        support: readPatch("support.md") || live.support,
        character: readPatch("TROID-CHARACTER.md") || live.character,
      });
    }
    return CTX_PATCH;
  }
  if (variant === "candidate") {                                          // the staged files that exist; the live ones otherwise
    if (!CTX_CANDIDATE) {
      const live = context();
      CTX_CANDIDATE = Object.assign({}, live, {
        troid: readStaged("TROID.md") || live.troid,
        support: readStaged("support.md") || live.support,
        character: readStaged("TROID-CHARACTER.md") || live.character,
      });
    }
    return CTX_CANDIDATE;
  }
  if (!CTX) {
    CTX = {
      troid: readFirst(["public/TROID.md"]),
      support: readFirst(["context/support.md"]),
      character: readOptional(["context/TROID-CHARACTER.md"]),            // troid's character, once promoted
      firms: readFirst(["context/firms.json"]),
      method: readFirst(["public/METHODOLOGY.md"]),
    };
    CTX.prompt_firms = promptFirms(CTX.firms);
    // every document Bitfunded's entry records, cited by a rule field or not: the compliance findings cite clauses
    // (ToU 14(d)(x), say) that no rule field does, so they can't use the prompt's filtered list
    CTX.bitfunded_sources = (((JSON.parse(CTX.firms).bitfunded || {}).provenance) || {}).sources || {};
  }
  return CTX;
}
// The model sees the rule data only: what troid's compare and troid's desk render (compare_product, products,
// calc, provenance, panel_note, the firm's required sentence) and a few firm-level rules read from the firm's
// own documents. Never troid's internal notes (every "_" key, at any depth), affiliate terms and links, the
// watch list, outside rankings, directory-sourced values or correspondence. An allowlist, so a new field
// stays out until someone adds it here.
const PROMPT_FIELDS = ["name", "verified", "verified_on", "compare_product", "products", "calc", "provenance", "panel_note",
  "required_disclaimer", "rule_changes", "floating_counts", "margin_modes", "max_open_positions", "hold_cap_days",
  "min_closed_trades_per_stage", "concentration_penalty_ladder", "mandatory_sl", "copy_trading", "payouts_per_30d",
  "max_capital_per_customer", "refund", "reset_settles_by_utc", "trader_stage_rule", "free_trial"];
const noNotes = (x) => (Array.isArray(x) ? x.map(noNotes) : x && typeof x === "object"
  ? Object.fromEntries(Object.entries(x).filter(([k]) => !k.startsWith("_")).map(([k, v]) => [k, noNotes(v)])) : x);
function promptFirms(raw) {
  const F = JSON.parse(raw), out = {};
  for (const [k, v] of Object.entries(F)) {
    if (k.startsWith("_") || !v || typeof v !== "object") continue;
    out[k] = noNotes(Object.fromEntries(PROMPT_FIELDS.filter((f) => f in v).map((f) => [f, v[f]])));
    const P = out[k].provenance;
    if (P) {                                                  // only the documents some rule cites
      const cited = new Map();                              // source id -> the rules that cite it
      const take = (rule, e) => ((e && e.src) || []).forEach((i) => cited.set(i, [...(cited.get(i) || []), rule]));
      Object.entries(P.fields || {}).forEach(([f, e]) => take(f, e));
      Object.entries(P.products || {}).forEach(([pk, pr]) => Object.entries(pr).forEach(([f, e]) => take(pk + "." + f, e)));
      out[k].provenance = { ...P, sources: Object.fromEntries(Object.entries(P.sources || {}).filter(([i]) => cited.has(i))
        .map(([i, s]) => [i, { ...s, cited_for: cited.get(i) }])) };
    }
  }
  return out;
}
function verifiedLine(pf) {                                  // from the data, so it can't go stale
  const v = Object.values(pf).filter((f) => f.verified === true).map((f) => f.name);
  return v.length ? v.join(", ") + (v.length > 1 ? " are" : " is") + " marked verified; the others are not" : "No firm is marked verified";
}
// The parts of TROID-CHARACTER.md that TROID.md does not carry: what ask troid is current on, and the worked examples.
// They go after TROID.md and before support.md; the other sections are in TROID.md already, so none appears twice.
const CHARACTER_IN_PROMPT = ["What troid is current on", "Examples"];
function characterBlock(md) {
  if (!md) return null;
  const parts = String(md).split(/\n(?=## )/).filter((x) => CHARACTER_IN_PROMPT.some((h) => x.startsWith("## " + h)));
  return parts.length ? parts.map((x) => x.trim()).join("\n\n") : null;
}
function systemBlocks(lang, variant) {
  const c = context(variant), names = Object.values(c.prompt_firms).map((f) => f.name), ch = characterBlock(c.character);
  const blocks = [
    { type: "text", text: "# Guardrails\n\n" + guardrailsFor(variant) + "\n- You may speak only about these firms: " + names.join(", ") +
      ". For any other firm, say troid does not cover it and has not read its rules, and stop.\n- " + verifiedLine(c.prompt_firms) + ".\n\n" + c.troid },
    ...(ch ? [{ type: "text", text: "# troid's character — what ask troid is current on, and worked examples of its teaching (TROID-CHARACTER.md)\n\n" + ch }] : []),
    { type: "text", text: "# support.md — fixed wording for the hard conversations\n\n" + c.support },
    { type: "text", text: "# Firm rules — the rule data behind troid's compare and troid's desk. Each rule has its source and read date under provenance, " +
      "or no recorded source yet; a null is pending. " + verifiedLine(c.prompt_firms) + ".\n\n" + JSON.stringify(c.prompt_firms) },
    { type: "text", text: "# Methodology — the tiers\n\n" + c.method, cache_control: { type: "ephemeral" } },
  ];
  // after the cached prefix, so each language shares one cache entry
  if (lang && lang !== "en") blocks.push({ type: "text", text: "The page the user is on is in " + languages()[lang].name + " (" + lang + ")." });
  return blocks;
}

// ---------------------------------------------------------------- firms → calculator profiles
// Same derivation as gen_compare.profiles_js(): a product-level key overrides the firm-level one, and
// each rule carries its provenance by the same cite() rule (a product's own limits never borrow another
// product's source; a firm-level cite applies only where the value is inherited from the firm level).
function cite(f, field, product, fallback) {
  const P = f.provenance || {};
  let ent = product ? ((P.products || {})[product] || {})[field] : null;
  if (product && (P.product_only || []).includes(field)) fallback = false;
  if (!ent && fallback) ent = (P.fields || {})[field];
  if (!ent) return null;
  const S = P.sources || {};
  const ids = ent.src.filter((i) => S[i]);
  return { section: ent.section, read_on: [...new Set(ids.map((i) => S[i].read_on).filter(Boolean))].sort(),
           urls: ids.map((i) => S[i].url).filter(Boolean) };
}
function profiles() {
  const F = JSON.parse(context().firms);
  const out = {};
  for (const k of Object.keys(F)) {
    if (k.startsWith("_")) continue;
    const f = F[k], c = f.calc || {}, prods = f.products || {};
    const products = {};
    for (const pk of Object.keys(c.products || {})) {
      const pc = c.products[pk], src = prods[pk] || {};
      const d = pc.daily_pct != null ? pc.daily_pct : src.daily_pct;
      const m = pc.max_pct != null ? pc.max_pct : src.max_pct;
      if (d == null || m == null) continue;
      const pick = (key) => (key in pc ? pc[key] : (key in c ? c[key] : null));
      const inh = (key) => !(key in pc);
      products[pk] = { label: pc.label || pk, d, m, basis: pick("daily_basis"), dd: pick("drawdown"),
                       locks: pick("locks_at_initial_after_pct"), hwm: pick("hwm_basis"),
                       fee: pick("fee_per_side_pct"), lev: pick("max_leverage"),
                       levb: "max_leverage" in pc ? null : (c.lev_bands || []).map((b) => ({ ...b, pv: cite(f, b.cite, null, true) })),
                       pv: { d: cite(f, "daily_pct", pk, false), m: cite(f, "max_pct", pk, false),
                             basis: cite(f, "daily_basis", pk, inh("daily_basis")), dd: cite(f, "drawdown", pk, inh("drawdown")),
                             locks: cite(f, "locks_at_initial_after_pct", pk, inh("locks_at_initial_after_pct")),
                             hwm: cite(f, "hwm_basis", pk, inh("hwm_basis")),
                             fee: cite(f, "fee_per_side_pct", pk, inh("fee_per_side_pct")),
                             lev: cite(f, "max_leverage", pk, inh("max_leverage")) } };
      if (products[pk].levb && !products[pk].levb.length) products[pk].levb = null;
    }
    if (Object.keys(products).length) out[k] = { name: f.name, products };
  }
  return out;
}
function profile(firm, product) {
  const P = profiles();
  const f = P[firm];
  if (!f) return { error: "unknown firm. troid covers: " + Object.keys(P).join(", ") };
  const p = f.products[product];
  if (!p) return { error: "unknown product for " + f.name + ". options: " + Object.keys(f.products).join(", ") };
  return { f, p };
}

// ---------------------------------------------------------------- tools (arithmetic identical to index.html)
const MMR = 0.005;
const DEFINITIONS = {
  R: "the loss if the stop is hit, in dollars; a 2R target is twice that distance on the other side of entry",
  notional: "quantity × entry: the position's size in dollars",
  margin: "the part of the account posted to hold the position: notional ÷ leverage",
  "cross margin": "the whole account backs every position, so a loss can draw on all of it",
  "isolated margin": "each position is backed only by its own margin",
  "maintenance margin": "the equity an exchange requires to keep a position open; below it the exchange liquidates",
};
function budgets(a) {
  const { f, p, error } = profile(a.firm, a.product);
  if (error) return { error };
  const quota = +a.quota, eq = +a.equity, ds = a.day_start != null ? +a.day_start : eq;
  const hwm = a.high_water_mark != null ? +a.high_water_mark : Math.max(eq, quota);
  const hi = a.high_at_rollover != null ? +a.high_at_rollover : ds;
  const dpct = p.d / 100, mpct = p.m / 100, pending = [], notes = [];
  // the same steps and formulas as the "show the working" table on troid's desk
  const working = [{ step: "inputs", formula: "quota · equity · day start", value: [quota, eq, ds] }];
  let dFloor = null, fd = "", fdd = "";
  if (p.basis === "initial") { dFloor = ds - quota * dpct; fd = `day start − quota × ${p.d}%`; }
  else if (p.basis === "day_start") { dFloor = ds * (1 - dpct); fd = `day start × (1 − ${p.d}%)`; }
  else if (p.basis === "max_balance_equity") { dFloor = hi - quota * dpct; fd = `high at rollover − quota × ${p.d}%`;
    working.push({ step: "high at rollover", formula: "input (defaults to day start)", value: hi }); }
  else pending.push("daily_basis");
  let ddFloor = null, locked = false;
  if (p.dd === "static") { ddFloor = quota * (1 - mpct); fdd = `quota × (1 − ${p.m}%)`; }
  else if (p.dd === "trailing") { locked = p.locks != null && hwm >= quota * (1 + p.locks / 100); ddFloor = locked ? quota : hwm - quota * mpct;
    fdd = locked ? `quota (locked after +${p.locks}%)` : `high-water mark − quota × ${p.m}%`;
    working.push({ step: "high-water mark", formula: "input (defaults to max(equity, quota))", value: hwm }); }
  else pending.push("drawdown_type");
  const dB = dFloor == null ? null : eq - dFloor, ddB = ddFloor == null ? null : eq - ddFloor;
  if (dFloor != null) working.push({ step: "daily floor", formula: fd, value: r2(dFloor) }, { step: "daily budget", formula: "equity − daily floor", value: r2(dB) });
  if (ddFloor != null) working.push({ step: "max-loss floor", formula: fdd, value: r2(ddFloor) }, { step: "drawdown budget", formula: "equity − max-loss floor", value: r2(ddB) });
  let binding = null, eff = null;
  if (dB == null && ddB == null) { /* nothing to size against */ }
  else if (dB == null) { binding = "max drawdown"; eff = ddB; notes.push("daily basis pending for this firm — sized against the drawdown ceiling only"); }
  else if (ddB == null) { binding = "daily loss limit"; eff = dB; notes.push("drawdown type pending for this firm — sized against the daily ceiling only"); }
  else { binding = dB <= ddB ? "daily loss limit" : "max drawdown"; eff = Math.min(dB, ddB); }
  const formula = dFloor != null && ddFloor != null ? `room = min(equity − (${fd}), equity − ${fdd})`
    : dFloor != null ? `room = equity − (${fd})` : ddFloor != null ? `room = equity − ${fdd}` : null;
  if (binding) working.push({ step: "binding", formula: dB == null || ddB == null ? "the only budget with its rules recorded" : "min(daily budget, drawdown budget)",
                              value: binding + " · " + r2(eff) });
  if (p.dd === "trailing") notes.push(locked ? `trailing floor locked at the initial balance after +${p.locks}%`
    : `trailing floor = high-water mark − quota × ${p.m}%` + (p.hwm === "equity" ? " — trails on equity intraday: an unrealised high raises the floor" : ""));
  if (p.basis === "max_balance_equity") notes.push(`daily floor = high at rollover − ${p.d}% of the original size`);
  let crossover = null, crossoverWork = null;
  if (ddFloor != null && p.basis != null) {
    crossover = p.basis === "day_start" ? ddFloor / (1 - dpct) : ddFloor + quota * dpct;
    crossoverWork = { formula: p.basis === "day_start" ? `max-loss floor ÷ (1 − ${p.d}%)` : `max-loss floor + quota × ${p.d}%`
                        + (p.dd === "static" && p.basis === "initial" ? ` = quota × (1 − ${p.m}% + ${p.d}%)` : ""),
                      value: r2(crossover),
                      meaning: "the day-start balance at which the two budgets are equal: a day that starts below it is bound by the max-loss floor, above it by the daily limit. Intraday, the binding ceiling is min(daily budget, drawdown budget) above, which depends on the day-start balance, not on equity alone" };
    if (p.dd === "trailing" && !locked) notes.push("crossover is at the current high-water mark; it moves with it");
  }
  const used = [];
  if (dFloor != null) { used.push(["d", `daily ${p.d}%`]); used.push(["basis", `daily basis (${p.basis})`]); }
  if (ddFloor != null) { used.push(["m", `max ${p.m}%`]); used.push(["dd", `drawdown type (${p.dd})`]);
    if (p.dd === "trailing") { if (p.locks != null) used.push(["locks", `lock at +${p.locks}%`]); if (p.hwm != null) used.push(["hwm", `high-water-mark basis (${p.hwm})`]); } }
  return { firm: f.name, product: p.label, daily_basis: p.basis, drawdown_type: p.dd, hwm_basis: p.hwm,
           daily_floor: r2(dFloor), daily_budget: r2(dB), dd_floor: r2(ddFloor), dd_budget: r2(ddB),
           trailing_locked: p.dd === "trailing" ? locked : null, binding, effective_budget: r2(eff),
           crossover_equity: r2(crossover), crossover_working: crossoverWork, formula, working, pending, notes, sources: sourcesFor(p, used), _p: p, _eq: eq, _used: used, _quota: quota };
}
const r2 = (x) => (x == null ? null : Math.round(x * 100) / 100);
const nth = (n) => n + ((n % 100 >= 11 && n % 100 <= 13) ? "th" : (["th", "st", "nd", "rd"][n % 10] || "th"));
// E[max of k independent standard normals]: the expected best of k configurations under a zero edge, in
// standard errors. ∫ x·k·φ(x)·Φ(x)^(k−1) dx, with Φ accumulated by the trapezoid rule on the same grid; the
// same integral as backtest/noise_math.py. (√(2 ln k), used before, overstates it: 2.61 against 2.04 at k = 30.)
function expectedMaxNormal(k) {
  const h = 1e-3, lo = -12, n = 24000, phi = (x) => Math.exp(-x * x / 2) / Math.sqrt(2 * Math.PI);
  let Phi = 0, s = 0, pPrev = phi(lo), fPrev = 0;
  for (let i = 1; i <= n; i++) {
    const x = lo + i * h, p = phi(x);
    Phi = Math.min(1, Phi + (pPrev + p) / 2 * h);
    const f = x * k * p * Math.pow(Phi, k - 1);
    s += (fPrev + f) / 2 * h; pPrev = p; fPrev = f;
  }
  return s;
}
const r4 = (x) => (x == null ? null : Math.round(x * 1e4) / 1e4);
// The rules a result used, each with where troid read it — the tool-side twin of the provenance block.
function sourcesFor(p, used) {
  return used.map(([k, rule]) => {
    const c = k === "lev_band" ? p._band_pv : p.pv[k];
    if (!c) return { rule, source: "not yet recorded", cite: rule + " — source not yet recorded" };
    const on = c.read_on.length ? c.read_on : null;
    return { rule, document_section: c.section, read_on: on || "not recorded", urls: c.urls,
             cite: rule + " — " + c.section + ", " + (on ? "read " + on.join(" and ") : "read date not recorded") };
  });
}

function check_budget(a) {
  const b = budgets(a);
  if (b.error) return b;
  const { _p, _eq, _used, _quota, ...out } = b;
  out.tier = "DERIVED from the firm's rules in firms.json; each rule's source is under sources";
  if (!out.binding) out.verdict = "PENDING: troid has no daily basis or drawdown type recorded for this product";
  return out;
}

// next: the candidate's arithmetic (CANDIDATE_RUN), the calculator audit's F1, F5, F6 and F7 and the review's R5 and R6
// as troid's desk does them (audit/SPEC.md); without it, the live arithmetic, unchanged. Promotion drops the flag and
// keeps the next branch.
function size_trade(a, next) {
  const b = budgets(a);
  if (b.error) return b;
  const p = b._p, eq = b._eq;
  const side = String(a.side || "long").toLowerCase().startsWith("l") ? 1 : -1;
  const entry = +a.entry, tR = a.target_r != null ? +a.target_r : 2;
  // a stop given as a percent of entry: the tool prices it, so no stop price is worked out by hand (run 2, p-size)
  const pctStop = (a.stop == null || a.stop === "") && a.stop_pct != null ? +a.stop_pct : null;
  const stop = pctStop != null ? +(entry * (1 - side * pctStop / 100)).toFixed(8) : +a.stop;
  const rpIn = a.risk_pct != null ? +a.risk_pct : 0.5, cpIn = a.budget_cap_pct != null ? +a.budget_cap_pct : 35, rp = rpIn / 100, cp = cpIn / 100;
  const lev = a.leverage != null ? +a.leverage : 5, mode = a.margin_mode === "isolated" ? "isolated" : "cross";
  const { _p, _eq, _used, _quota, ...base } = b;
  base.tier = "DERIVED from the firm's rules in firms.json; each rule's source is under sources. A figure that rests on an entry under assumptions is troid's assumption, not the firm's rule";
  if (!b.binding) return { verdict: "PENDING", reasons: ["troid has no daily basis or drawdown type recorded for this product, so there is no budget to size against"], ...base };
  const dist = Math.abs(entry - stop), blocks = [];
  if (side > 0 && stop >= entry) blocks.push("stop at or above entry on a long");
  if (side < 0 && stop <= entry) blocks.push("stop at or below entry on a short");
  if (dist <= 0) blocks.push("stop distance is zero");
  if (b.effective_budget <= 0) blocks.push("no budget left — " + b.binding + " already breached");
  if (blocks.length) return { verdict: "BLOCK", reasons: blocks, ...base };
  const notes = base.notes.slice(), working = base.working.slice();
  if (pctStop != null) working.splice(1, 0, { step: "stop", formula: `entry × (1 ${side > 0 ? "−" : "+"} ${pctStop}%)`, value: stop });
  working.splice(1, 0, { step: "inputs", formula: "side · entry · stop · target R", value: [side > 0 ? "long" : "short", entry, stop, tR] },
                       { step: "inputs", formula: "risk % · budget cap % · leverage · margin", value: [rpIn, cpIn, lev, mode] });
  const intended = rp * eq, cap = cp * Math.max(b.effective_budget, 0), risk = Math.min(intended, cap);
  const reduced = risk < intended - 1e-9;
  const feeKnown = p.fee != null, fee = feeKnown ? p.fee / 100 : 0;
  const used = _used.slice();
  if (feeKnown) used.push(["fee", `fee ${p.fee}% per side`]);
  else { base.pending.push("fee_per_side"); notes.push("fee per side pending for this firm — size shown before fees"); }
  let levCap = p.lev, levUsed = lev, levKey = "lev", held = null;
  if (p.levb) {
    const band = p.levb.find((x) => (x.max_quota == null || _quota <= x.max_quota) && (x.min_quota == null || _quota >= x.min_quota));
    levCap = band ? band.lev : null; p._band_pv = band ? band.pv : null; levKey = "lev_band";
  }
  if (levCap != null) {
    used.push([levKey, `leverage cap ${levCap}×` + (p.levb ? ` for a $${_quota.toLocaleString()} account` : "")]);
    if (lev > levCap) { levUsed = levCap; notes.push(`leverage capped at ${levCap}× by the firm`); }
  } else {
    base.pending.push("max_leverage");
    if (p.levb) {
      // the desk's D6 (next): held to the lowest cap the firm records, not the highest, since the margin check (F1) rests
      // on the leverage used (Crypto Fund Trader between $25,000 and $50,000: 5×, not 100×)
      const top = next ? Math.min(...p.levb.map((x) => x.lev)) : Math.max(...p.levb.map((x) => x.lev));
      notes.push(`no leverage class recorded for a $${_quota.toLocaleString()} account — cap pending at this size`);
      if (lev > top) { levUsed = held = top; notes.push(`leverage held to ${top}×, the ${next ? "lowest" : "highest"} cap this firm records`); }
    }
  }
  base.sources = sourcesFor(p, used);
  // F6 (the calculator audit, live and candidate since 2026-10-07): the exit fee is charged on the exit notional,
  // quantity × stop at the stop, so a unit's fees are fee × (entry + stop) and the loss at the stop is the risk to the
  // cent, long or short (live priced both fees at entry until then: run 20's p-size, 1.622095 against the desk's 1.621583)
  const fu = fee * (entry + stop), qty0 = risk / (dist + fu), m0 = qty0 * entry / levUsed;
  // F1 (next): a margin above equity can't be opened, so the size is cut to what equity carries at this leverage, and the
  // loss at the stop falls with it: $100,000 at 5× carries $500,000 of notional at most. Live sizes past it.
  const cut = !!next && m0 > eq + 1e-9, qty = cut ? eq * levUsed / entry : qty0, notional = qty * entry, margin = notional / levUsed;
  const fees = qty * fu, target = entry + side * tR * dist, loss = qty * (dist + fu), lost = next ? loss : risk, fshare = fees / lost * 100;
  // F7 (next): losses that leave equity above the floor. Firms word a breach as reaching the limit, so a loss that lands
  // exactly on it is not one more left ($4,000 at $500 leaves 7, not 8). The epsilon reads 4.000000000000001 as 4.
  // Live too since 2026-10-08 (it counted floor(budget ÷ risk), 8 at $4,000 and $500, the 8th reaching the limit).
  const consumes = lost / b.effective_budget * 100, left = Math.ceil(b.effective_budget / (next ? loss : risk) - 1e-9) - 1;
  working.push({ step: "intended risk", formula: `equity × ${rpIn}%`, value: r2(intended) },
               { step: "cap", formula: `budget × ${cpIn}%`, value: r2(cap) },
               { step: "risk", formula: "min(intended, cap)", value: r2(risk) },
               { step: "stop distance", formula: "|entry − stop|", value: r4(dist) },
               { step: "fee per unit", formula: feeKnown ? `(entry + stop) × ${p.fee}%` : "fee per side pending: taken as 0, size before fees", value: r4(fu) },
               { step: "quantity", formula: cut ? "equity × leverage used ÷ entry: cut to fit the margin" : feeKnown ? "risk ÷ (stop distance + fee per unit)" : "risk ÷ stop distance", value: Math.round(qty * 1e6) / 1e6 },
               { step: "notional", formula: "quantity × entry", value: r2(notional) },
               { step: "leverage used", formula: levCap == null ? (next && held != null ? `your leverage; cap pending (held to ${held}×, the lowest cap recorded for this firm)` : "your leverage; cap pending") : `min(your ${lev}×, cap ${levCap}×)`, value: levUsed },
               { step: "margin", formula: "notional ÷ leverage used", value: r2(margin) });
  if (next) working.push({ step: "margin check", formula: cut ? `margin at the risk-based size > equity: size cut to equity × ${levUsed}× ÷ entry` : "margin at the risk-based size ≤ equity", value: r2(m0) });
  if (feeKnown) working.push({ step: "fees", formula: "quantity × fee per unit", value: r2(fees) });
  if (next) working.push({ step: "loss at the stop", formula: "quantity × (stop distance + fee per unit)", value: r2(loss) });
  working.push({ step: "budget used", formula: "risk ÷ budget", value: r2(consumes) + "%" },
               { step: "losses left", formula: "ceil(budget ÷ risk) − 1: the losses at this size that leave equity above the limit, this one included", value: left },
               { step: "the loss that reaches the limit", formula: "ceil(budget ÷ risk)", value: left + 1 },
               { step: "target", formula: `entry ${side > 0 ? "+" : "−"} ${tR} × stop distance`, value: r2(target) });
  base.formula += "; size = min(equity × " + rpIn + "%, room × " + cpIn + "%) ÷ " + (feeKnown ? `(stop distance + (entry + stop) × ${p.fee}%)` : "stop distance")
    + (cut ? `; margin at the risk-based size > equity: size cut to equity × ${levUsed}× ÷ entry` : "");
  // R5 (next, extends F7): a loss that takes the whole room reaches the limit, which fails the account (only at a 100% cap)
  if (next && left < 1) {
    return { verdict: "BLOCK", reasons: [`a loss at this stop would take the whole room and reach the ${b.binding}, which fails the account — set the budget cap below 100%`],
             ...base, formula: b.formula };
  }
  if (feeKnown && fshare > 15) notes.push(`fees are ${fshare.toFixed(0)}% of risk — stop tight enough that costs dominate`);
  // F1 (next): the margin cut says what equity carries and what the trade then risks, and a budget cut before it says both
  if (cut) notes.push(`cut to fit the margin: at ${levUsed}× the account carries at most ${(eq * levUsed).toFixed(2)} notional, so this trade risks ${loss.toFixed(2)}`);
  if (reduced) notes.push(`cut from ${intended.toFixed(2)} to ${risk.toFixed(2)} — ${b.binding} budget caps it` + (cut ? `; the margin then cut it to ${loss.toFixed(2)}` : ""));
  // the owner, 2026-10-08: "N more losses" after this trade counted one too many (runs 35 to 39's p-size): the count
  // includes this trade, and the loss that reaches the limit is named
  notes.push(left > 0 ? `${left} ${left === 1 ? "loss" : "losses"} at this size fit, this one included; the ${nth(left + 1)} reaches the ${b.binding}`
                      : `a loss at this size reaches the ${b.binding}`);
  const sp = dist / entry * 100;
  // MMR 0.5% is troid's assumption, not a firm rule. The exchange liquidates when the margin behind the position falls to
  // the maintenance margin on the notional at the liquidation price: lower than entry for a long, higher for a short.
  // Adverse move = (m − MMR) ÷ (1 − MMR) long, (m − MMR) ÷ (1 + MMR) short; m = 1 ÷ leverage isolated, equity ÷ notional
  // cross. (Until 2026-09-24 the long formula served both sides.) <= 0: already below maintenance.
  const sg = side > 0 ? "−" : "+", mBack = mode === "isolated" ? 1 / levUsed : notional > 0 ? eq / notional : Infinity;
  const liq = isFinite(mBack) ? (mBack - MMR) / (1 - side * MMR) * 100 : Infinity;
  // F5 (next): a long can't fall more than 100%, so at 100% or more it has no liquidation above zero (cross with equity
  // above the notional, isolated at 1×): it says so in place of the figure and sorts last, as troid's desk does. A short
  // can rise without limit; its figure stands.
  const none = !!next && side > 0 && isFinite(liq) && liq >= 100 - 1e-9, NONE = "none above zero";
  const fl = (mode === "isolated" ? "(1 ÷ leverage used" : "(equity ÷ notional") + ` − MMR ${MMR * 100}%) ÷ (1 ${sg} MMR)`;
  const assumed = ["exchange liquidation uses a 0.5% maintenance margin — troid's assumption, no firm source"];
  if (a.margin_mode == null) assumed.push("margin mode " + mode + " — troid's default, not an input you gave" + (p.pv.margin_modes ? "" : "; troid has no recorded source for this firm's margin modes"));
  if (a.leverage == null) assumed.push("leverage " + lev + "× — troid's default, not an input you gave");
  if (a.risk_pct == null) assumed.push("risk " + rpIn + "% of equity — troid's default, not an input you gave");
  if (a.budget_cap_pct == null) assumed.push("budget cap " + cpIn + "% of the binding budget — troid's default, not an input you gave");
  if (a.target_r == null) assumed.push("target " + tR + "R — troid's default, not an input you gave");
  const ord = [["your stop", sp]], fname = p.dd === "trailing" && !b.trailing_locked ? "trailing floor" : "max-loss floor";
  // R6 (next, extends F5): nor can a long's floor be reached above zero when it sits 100% or more below entry: it says so
  // in place of the figure and sorts after every finite distance, as troid's desk does. A short's stands as computed.
  const far = (x) => !!next && side > 0 && x >= 100 - 1e-9, FAR = "not reached above zero — a fall to zero stays inside it";
  const dP = b.daily_budget != null ? b.daily_budget / notional * 100 : null, ddP = b.dd_budget != null ? b.dd_budget / notional * 100 : null;
  if (dP != null) ord.push(far(dP) ? ["daily limit", Infinity, FAR] : ["daily limit", dP]);
  if (ddP != null) ord.push(far(ddP) ? [fname, Infinity, FAR] : [fname, ddP]);
  ord.push(none ? [`exchange liquidation (${mode})`, Infinity, NONE] : [`exchange liquidation (${mode})`, Math.max(liq, 0)]);
  if (dP != null) working.push({ step: "daily-limit distance", formula: "daily budget ÷ notional", value: far(dP) ? FAR : r2(dP) + "%" });
  if (ddP != null) working.push({ step: fname + " distance", formula: "drawdown budget ÷ notional", value: far(ddP) ? FAR : r2(ddP) + "%" });
  working.push({ step: `exchange liquidation (${mode})`, formula: fl, value: liq <= 0 ? "0% — below maintenance at entry" : none ? NONE : r2(liq) + "%" });
  ord.sort((x, y) => x[1] - y[1]);
  if (ord[0][0] !== "your stop") notes.push(`DANGER — ${ord[0][0]} binds at ${ord[0][1].toFixed(2)}% adverse, inside your stop`);
  else if (mode === "cross") notes.push("cross: nothing cuts a runaway before the firm's floor — your stop is the only breaker in front of it");
  else if (none) notes.push(`isolated at ${levUsed}×: no liquidation above zero — the position's own margin covers a fall to zero`);
  else notes.push(`isolated: exchange liquidates at ${liq.toFixed(1)}% for the position's own margin, before the floor`);
  // risk (next): what the trade risks, the loss at the stop, as the desk's readout shows it; the budget's risk (the working
  // row "risk") until F1 cuts the size, then less
  return { verdict: reduced || cut ? "REDUCE" : "OK", quantity: Math.round(qty * 1e6) / 1e6, notional: r2(notional),
           margin: r2(margin), leverage_used: levUsed, risk: r2(next ? loss : risk), fees: feeKnown ? r2(fees) : null,
           fee_share_of_risk_pct: feeKnown ? r2(fshare) : null, stop_distance_pct: r2(sp), target: r2(target),
           ...(next ? { loss_at_stop: r2(loss) } : {}), consumes_pct_of_budget: r2(consumes), losses_remaining: left, loss_that_reaches_limit: left + 1,
           circuit_breakers: ord.map(([e, v, t]) => ({ event: e, adverse_move_pct: t != null ? t : isFinite(v) ? r2(v) : null })),
           assumptions: assumed, definitions: DEFINITIONS, ...base, working, notes };
}

// Bitfunded's restricted practices (RTP) and Terms. Modelled for Bitfunded only. Each finding names the
// document it comes from and the date troid read it (firms.json provenance.sources: rtp, tou).
const MAJORS = new Set(["BTC", "ETH", "BNB", "XRP", "SOL", "TRX", "HYPE", "ZEC", "DOGE", "ADA"]);
const HOLD_DAYS = { major: 10, minor: 7, tradfi: 5 };
const PENALTY_LADDER = [[65, 50], [75, 60], [90, 65], [96, 70]];
const PENALTY_LADDER_IF = [[55, 50], [65, 55], [75, 60], [90, 65], [96, 70]];
const MIN_DAYS = { "1step": 5, "2step_s1": 5, "2step_s2": 5, express: 5, instant: 0, trader_1step: 0, trader_express: 0, trader_2step: 0 };
function asset_class(symbol) {
  const base = String(symbol || "BTCUSDT").toUpperCase().split(":").pop().replace("USDT", "").replace("USD", "");
  if (MAJORS.has(base)) return "major";
  if (["XAU", "XAG", "GOLD", "SILVER", "TSLA", "NVDA", "AAPL", "NDX", "DJI", "SPX"].includes(base) || (base.length <= 4 && !/^[A-Z]+$/.test(base))) return "tradfi";
  return "minor";
}
// The Terms clauses troid's owner read again on 2026-09-23 (Terms modified 2026-03-24) cite that reading.
const TOU_0923 = /9\(a\)|9\(b\)|4\(b\)|5\(b\)|13\(c\)\(v\)|14\(d\)\(ix\)|14\(d\)\(xi\)/;
function refSources(ref) {
  const S = context().bitfunded_sources;
  const ids = [];
  if (/RTP/.test(ref)) ids.push("rtp");
  if (/ToU/.test(ref)) ids.push(TOU_0923.test(ref) && S.tou_0923 ? "tou_0923" : "tou");
  return ids.filter((i) => S[i]).map((i) => ({ document: S[i].doc, read_on: S[i].read_on || "not recorded", url: S[i].url }));
}
// Prohibited practices troid cannot detect from a trade plan. check_compliance states them every time, as
// information, so the assistant can raise them where the conversation makes them relevant.
const NOT_DETECTABLE = [
  { severity: "info", rule: "ToU 14(d)(ix)", detail: "Switching strategies between the assessment account and the funded account is prohibited. troid cannot check this from the inputs." },
  { severity: "info", rule: "ToU 13(c)(v)", detail: "Opposite positions across connected accounts are prohibited, such as a long on one account and a short on the same asset on another. troid cannot check this from the inputs." },
];
function check_compliance(a) {
  const firm = a.firm || "bitfunded";
  if (firm !== "bitfunded") return { firm, pending: true, note: "troid models restricted-practice checks for Bitfunded only. For this firm they are pending: say so and point to troid's compare. Do not fill them from memory." };
  const product = a.product || "1step", findings = [];
  const cls = asset_class(a.symbol), cap = HOLD_DAYS[cls];
  if (+a.hold_days > cap) findings.push({ severity: "breach", rule: "RTP s.1 / ToU 14(d)(x)", detail: `Position held ${(+a.hold_days).toFixed(1)} days exceeds the ${cap}-day maximum for ${cls} assets. Majors 10d, other crypto 7d, TradFi 5d.` });
  if (+a.open_trades > 5) findings.push({ severity: "breach", rule: "RTP s.3", detail: `${a.open_trades} simultaneous trades exceeds the 5 cap (the ToU says 10; the help centre says 5 and is newer).` });
  const ladder = product === "instant" ? PENALTY_LADDER_IF : PENALTY_LADDER;
  const mp = +a.margin_pct_of_capital || 0;
  const pen = [...ladder].reverse().find(([thr]) => mp >= thr);
  if (pen) findings.push({ severity: "penalty", rule: "RTP s.2", detail: `Margin at ${mp.toFixed(0)}% of capital sits on the concentration ladder: ${pen[1]}% payout penalty at review. Ladder starts at ${ladder[0][0]}% for this product.` });
  const need = product === "instant" ? 3 : 2, closed = +a.closed_trades_this_stage || 0;
  if (closed > 0 && closed < need) findings.push({ severity: "warning", rule: "RTP s.4", detail: `${closed} closed trades this stage; ${need} required (each open ≥ 10 min) before a payout request.` });
  if (a.uses_third_party_strategy) findings.push({ severity: "breach", rule: "ToU 14(d)(v)", detail: "Using a third-party or marketed strategy to pass an evaluation is prohibited. A bot, signal service or strategy pack run on a challenge may void the account regardless of result." });
  if (+a.accounts_at_this_level > 1) findings.push({ severity: "breach", rule: "ToU 6(b)", detail: `${a.accounts_at_this_level} accounts at one challenge level. Limit is one active account per level without written consent.` });
  const minDays = Object.hasOwn(MIN_DAYS, product) ? MIN_DAYS[product] : 5, days = +a.trading_days_so_far || 0;
  if (minDays && days > 0 && days < minDays) findings.push({ severity: "warning", rule: "ToU 9(a)", detail: `${days} trading days so far; ${minDays} required to clear the stage. The challenge page displays 0 — the contract governs.` });
  const clear = findings.length === 0;
  if (clear) findings.push({ severity: "ok", rule: "—", detail: "No breach detected against the rules modelled here." });
  findings.push(...NOT_DETECTABLE.map((x) => ({ ...x })));
  for (const x of findings) if (x.rule !== "—") x.sources = refSources(x.rule);
  return { firm: "Bitfunded", product, clear, findings,
           sources: refSources("RTP ToU"),
           tier: "SOURCED — Bitfunded Terms of Use and help centre, sections cited; each finding lists its document and read date",
           caveat: "Checks only the rules modelled here; findings marked info are rules troid cannot check from the inputs. Not a substitute for reading the firm's Terms. Verify anything material with the firm directly." };
}

const RULES = {
  crossover: "A funded account has two loss ceilings. Under Bitfunded the daily limit is a FIXED amount from the initial balance (FAQ) and the max loss is a fixed floor from the starting quota. They swap where the day-start balance equals quota × (1 − max% + daily%). On a $100k 1-Step that is $98,000 — only $2,000 below the start. A day that starts below $98,000 is bound by the max-loss floor, and the 4% daily limit is not the constraint that day; above it, the daily limit binds. Intraday, which ceiling binds depends on that day's starting balance, not on equity alone: check_budget shows both budgets and the smaller one. Size against the smaller of the two, always. Other firms use other bases: CFT's daily is a percentage of the day-start balance (crossover quota × (1 − max%) / (1 − daily%)); BrightFunded's is a fixed amount below the high at rollover.",
  // 16:00 UTC is noon in New York only in summer; "morning and afternoon are separate daily budgets" read as a rule of the
  // firm's (run 1 of the evaluation, p-reset): it is a consequence of the reset's hour for a trader in New York
  reset: "Bitfunded's trading day resets at 00:00 UTC+8, which is 16:00 UTC all year (UTC+8 is a fixed offset). Not midnight. Local clocks move with daylight saving and UTC doesn't, so a local hour for the reset holds only for the date it was converted for. Because of the platform's settlement process the reset can take effect any time between 00:00 and 00:10 UTC+8 (help centre, Criteria to be Success): 16:00–16:10 UTC. Those ten minutes are ambiguous: a fresh daily budget is certain only from 16:10 UTC. For a trader in New York the reset lands mid-session in every season, so a loss at 15:45 UTC and a loss at 16:15 UTC fall on different trading days and draw on different daily budgets. The trap: a floating loss that survives the reset counts in full against the new day, because the prior day's profit does not carry over, so a position inside the limit just before the reset can breach just after it without price moving. BrightFunded rolls over at 23:30–23:59 CET and advises not trading in the window; Crypto Fund Trader resets at 00:05 UTC (T&C 8.i–8.ii).",
  // the calculator audit's F6 (troid's desk, 2026-09-29; live since 2026-10-07): the exit fee is charged at the stop
  fees: "Bitfunded: 0.04% per side on notional: on the entry notional, and on the exit notional, which at the stop is quantity × stop. So a unit's fees " +
    "are f × (entry + stop), and the loss at the stop, both fees in it, is the risk, long or short. The fee share of risk is f(2 − s)/(s + f(2 − s)) on a " +
    "long and f(2 + s)/(s + f(2 + s)) on a short, s the stop distance as a fraction of entry: a short's stop sits above entry, so it pays a little more. " +
    "2f/(s + 2f), both fees priced at entry, is the side-neutral approximation. Notional scales inversely with stop distance, so tight stops are " +
    "punished hardest: at a 3.9% stop the fees are about 2% of risk; at a 0.3% scalp stop about 21%, either side. Other firms' fees are in firms.json; a null is pending.",
  leverage: "Leverage does not determine your loss — the stop does. risk = |entry − stop| × quantity, and leverage appears nowhere in it. What leverage changes is margin posted and liquidation distance. Under ISOLATED margin a long is liquidated near entry × (1 − 1/leverage) and a short near entry × (1 + 1/leverage): a distance of about entry ÷ leverage, ~20% at 5x, a little less after the exchange's maintenance margin. Under CROSS margin the whole account backs the position, so at any size a 5× cap allows the firm's own floors are breached long before exchange liquidation. troid models cross margin by default; it has no recorded source for which margin modes Bitfunded offers.",
  cross: "Under cross margin, troid's default model (troid has no recorded source for Bitfunded's margin modes; the 5× leverage cap is from the help centre, Challenge & Trader Stage, and Terms 9(a)), every position is backed by the entire account balance. Exchange liquidation never binds — even at the 65% margin cap it sits at ~31% adverse move while the 6% floor binds at 1.85%. The firm's floors ARE your liquidation model. Nothing cuts a runaway position before the firm fails you; your stop is the only circuit breaker in front of the floor. At the 65% margin cap the daily limit binds at a 1.23% adverse move — tighter than a normal 1.66% stop.",
  // a drawdown type belongs to a product (run 7, b-limits: "Crypto Fund Trader's trail the high-water mark"; its 2-Phase is static)
  drawdown: "Bitfunded's max loss is STATIC — measured from the account quota, not a high-water mark — so profit permanently widens the buffer. Trailing drawdown (BrightFunded 1-Step, CFT 1-Phase) works the opposite way: the floor follows the high-water mark up until it locks at the initial balance after +6%. BrightFunded's trails on equity intraday — an unrealised high raises the floor (help centre scenario 3); CFT's 1-Phase trails on balance. CFT's 2-Phase is static from the initial balance. A drawdown type belongs to a product, not a firm: name the product with it.",
  ladder: "Scaling in does not increase position size at fixed risk — it decreases it. With the stop anchored to the first entry's structure, later tranches sit further from the stop and earn less quantity. Five strength tranches hold about 34% LESS than a single entry at the same risk. The benefit is conditionality: you fill more on trades that work than on trades that don't.",
  ruin: "Under a proportional cap (risk at most c of the REMAINING budget), budget after n losses is B(1−c)^n — it approaches zero without reaching it, so ruin by realized losses is unreachable and the real failure mode is a stalled account. Uncapped, a fixed fraction f of quota reaches the floor in floor(maxloss/f) losses: 12 at 0.5%, 6 at 1%, 3 at 2%. At a professional +0.35R edge, 1% uncapped blows up 68% of the time within a year (MODELLED); under a cap, zero.",
  min_days: "Bitfunded: five trading days minimum to clear a stage (ToU 9(a)). The challenge page displays 0. The contract governs. The bad failure mode is hitting the profit target in three days and being unable to clear the stage.",
  // the majors named, from the set check_compliance classes by (run 1, p-hold: asked for the product instead)
  hold_limit: "Bitfunded: majors (" + [...MAJORS].join(", ") + ") 10 days, other crypto 7, TradFi 5 (Restricted Trading Practices s.1). The limit follows the asset, not the product. Profits from a breaching trade can be removed from payout eligibility.",
  accounts: "Bitfunded: one active account per challenge level without written consent (ToU 6(b)). Across all seven levels that caps simultaneous capital at $355,000.",
  marketed_strategies: "Bitfunded ToU 14(d)(v) prohibits using third-party or marketed strategies to pass an evaluation. This is why troid evaluates trades rather than generating them.",
  strategy_switching: "Bitfunded ToU 14(d)(ix) prohibits switching strategies between assessment and funded accounts. troid cannot see this from a trade plan, so it cannot check it; it is a rule about how the account is traded over time, not about one trade.",
  opposite_positions: "Bitfunded ToU 13(c)(v) prohibits opposite positions across connected accounts: a long on one account and a short on the same asset on another. Hedged pairs cancel each other's market risk while each account keeps its own chance of passing, which is why firms prohibit them. troid cannot see connected accounts, so it cannot check this.",
  funded_stage: "Bitfunded's Trader Stage limits depend on the path (help centre, Challenge & Trader Stage): after the 1-Step 4% daily / 6% max, after the Express 3% / 3%, after the 2-Step 5% / 8%, each with an 80% split; Instant 3% / 6% with a 60% split; leverage 1:5 on each. Any Trader Stage breach disqualifies the account, and a new challenge is required.",
};
function explain_rule(a, rules) {
  const R = rules || RULES, t = String(a.topic || "").toLowerCase().trim().replace(/\s+/g, "_");
  if (!Object.hasOwn(R, t)) return { error: "unknown topic. options: " + Object.keys(R).sort().join(", ") };
  return { topic: t, explanation: R[t],
           tier: "Explanation text written by troid for ask troid, not generated from firms.json, so it can fall out of step with troid's compare. " +
                 "Its formulas are DERIVED; a rule it cites is SOURCED from the section named, and the firm's own documents govern. For a rule's read date, " +
                 "use the sources in size_trade or check_budget, or troid's compare." };
}
// The explanations promoted on 2026-10-08 where they differ from RULES (LIVE_RULES below). Staged after evaluation run 10
// (o-montecarlo set troid's 68%, which is at 1% a trade, beside 2%): troid's published Monte Carlo, every figure with the
// risk it belongs to and the assumptions the landing page states beside it (verify_claims.py re-simulates each).
const PROMOTED_RULES = {
  ruin: "Under a proportional cap (risk at most c of the REMAINING budget), budget after n losses is B(1−c)^n — it approaches zero without reaching it, " +
    "so ruin by realized losses is unreachable and the real failure mode is a stalled account. Uncapped, a fixed fraction f of quota reaches the floor in " +
    "ceil(maxloss/f) losses: 12 at 0.5%, 6 at 1%, 3 at 2% of a 6% maximum loss, and reaching it is the breach, so one fewer leaves equity above it " +
    "(the calculator audit's F7). troid's published Monte Carlo, MODELLED (backtest/income_math.py; " +
    "verify_claims.py re-runs it): 20,000 simulated years of 30 trades a month for 12 months, 45% of trades won at 2:1 (+0.35R a trade), under a 4% daily " +
    "limit fixed on the $100,000 start and a 6% static floor. Risking 1% of balance a trade with no cap on the remaining budget, 68% of the simulated years " +
    "blow the account; at 2%, 100%, every one. Capped at 35% of the remaining budget a trade, 0% at 1% and at 2%. True under these assumptions only: " +
    "they are troid's inputs, not the user's, and the figures do not carry over to other inputs.",
  // run 11, b-limits: the floating-loss rule, from TROID.md, beside explain_rule's crossover and drawdown with no source
  // line; both explanations state it now, so the service lists its source under them
  // the read of runs 17 and 19 (p-crossover: the floor said to govern after "even a small amount"): stated exactly
  crossover: "A funded account has two loss ceilings. Under Bitfunded the daily limit is a FIXED amount from the initial balance (FAQ) and the max loss is a fixed floor from the starting quota. They swap where the day-start balance equals quota × (1 − max% + daily%). On a $100k 1-Step that is $98,000 — only $2,000 below the start. Below $98,000 at the day's start the max-loss floor binds, and the 4% daily limit is not the constraint that day; between $98,000 and the $100,000 start the daily limit binds, and above the start too. A day that starts less than $2,000 below the start is still bound by the daily limit. The max-loss budget is the day's start less the $94,000 floor: $6,000 on a day that starts at $100,000, under $4,000 on one that starts below $98,000. Intraday, which ceiling binds depends on that day's starting balance, not on equity alone: check_budget shows both budgets and the smaller one. Size against the smaller of the two, always. Other firms use other bases: CFT's daily is a percentage of the day-start balance (crossover quota × (1 − max%) / (1 − daily%)); BrightFunded's is a fixed amount below the high at rollover." +
    " Both of Bitfunded's ceilings count floating losses: an open position that reaches either one fails the account, with no close needed.",
  drawdown: RULES.drawdown + " Bitfunded's floor counts floating losses: an open position that reaches it fails the account, with no close needed.",
  // the calculator audit's F6 (troid's desk, 2026-09-29): the exit fee is charged at the stop, not at entry; the same
  // text as RULES.fees since F6 went live (2026-10-07)
  fees: RULES.fees,
};
// the rules each candidate explanation states, where they differ from TOPIC_CITES
const FLOAT_CITE = ["bitfunded", "floating_counts", null, "floating losses count toward the daily and maximum loss (Bitfunded)"];
const PROMOTED_TOPIC_CITES = {};
// A patch's rule explanations (context/patch/README.md): explain_rule, for a request with x-troid-variant: patch, gets the
// live RULES with these in their place and nothing of the candidate's. Publishing the patch folds each into RULES and
// empties this object. Empty since the fourth patch (the reset in UTC, its runs web/eval/runs/2026-10-06-section0-*)
// published; the candidate's copy of that reset went with it, so its reset is the live one again.
const PATCH_RULES = {};
// The rules each explain_rule topic states, with the document and the date troid read them: [firm, field, product, rule].
// A product's own limits cite that product (the 1-Step, the one the explanations use). Clauses no rule field carries
// cite their document through refSources.
const TOPIC_CITES = {
  crossover: [["bitfunded", "daily_pct", "1step", "daily 4% (1-Step)"], ["bitfunded", "max_pct", "1step", "max 6% (1-Step)"], ["bitfunded", "daily_basis", null, "daily basis (initial balance)"],
              ["crypto_fund_trader", "daily_basis", null, "Crypto Fund Trader daily basis (day-start balance)"], ["brightfunded", "daily_basis", null, "BrightFunded daily basis (high at rollover)"]],
  reset: [["bitfunded", "reset_utc", null, "reset 00:00 UTC+8, effective by 00:10"], ["brightfunded", "reset_utc", null, "BrightFunded rollover 23:30–23:59 CET"],
          ["crypto_fund_trader", "reset_utc", null, "Crypto Fund Trader reset 00:05 UTC"]],
  fees: [["bitfunded", "fee_per_side_pct", "1step", "fee 0.04% per side"]],
  leverage: [["bitfunded", "max_leverage", "1step", "leverage cap 5×"]],
  cross: [["bitfunded", "max_leverage", "1step", "leverage cap 5×"], ["bitfunded", "daily_pct", "1step", "daily 4% (1-Step)"], ["bitfunded", "max_pct", "1step", "max 6% (1-Step)"]],
  drawdown: [["bitfunded", "drawdown_type", null, "drawdown type (static)"], ["brightfunded", "drawdown_type", null, "BrightFunded drawdown (trailing on equity)"],
             ["crypto_fund_trader", "drawdown_type", null, "Crypto Fund Trader drawdown, by product (1-Phase: trails on balance, static at the opening balance after +6%; 2-Phase: static)"]],
  min_days: [["bitfunded", "min_days", null, "minimum 5 trading days"]],
  hold_limit: [["bitfunded", "hold_cap", null, "hold limit: majors 10 days, other crypto 7, TradFi 5"]],
  funded_stage: [["bitfunded", "trader_stage_rule", null, "Trader Stage limits by path"]],
};
Object.assign(PROMOTED_TOPIC_CITES, { crossover: TOPIC_CITES.crossover.concat([FLOAT_CITE]), drawdown: TOPIC_CITES.drawdown.concat([FLOAT_CITE]) });
const TOPIC_REFS = { cross: "RTP s.2", accounts: "ToU 6(b)", marketed_strategies: "ToU 14(d)(v)", strategy_switching: "ToU 14(d)(ix)", opposite_positions: "ToU 13(c)(v)" };
// explain_rule for the candidate: its explanations, and the sources of the rules they state, so the service writes each
// rule's document and read date under the answer and the tier (SOURCED) with them. Topics that state no firm rule
// (ladder, ruin) are unchanged: their tier stays with the model.
function explainRuleSourced(a, rules, cites) {
  const out = explain_rule(a, rules || RULES);
  if (out.error) return out;
  const F = JSON.parse(context().firms), sources = [];
  for (const [firm, field, product, rule] of (cites || TOPIC_CITES)[out.topic] || []) {
    const c = F[firm] ? cite(F[firm], field, product, !product) : null;
    sources.push(c ? { rule, document_section: c.section, read_on: c.read_on.length ? c.read_on : "not recorded", urls: c.urls } : { rule, source: "not yet recorded" });
  }
  const ref = TOPIC_REFS[out.topic];
  if (ref) for (const s of refSources(ref)) sources.push(Object.assign({ rule: ref }, s));
  if (!sources.length) return out;
  return Object.assign(out, { sources, tier: "SOURCED — each rule this explanation states is under sources, with its document and the date troid read it. " +
    "The explanation text is troid's own, not generated from firms.json; its formulas are DERIVED, and the firm's own documents govern." });
}

// A firm product's rules as troid has recorded them, each with the document and the date troid read it: the cells of
// troid's compare, for ask troid. A rule troid hasn't recorded is pending, never filled in (run 3, s-product: a rules
// table with no read dates). [value key, provenance key, rule]
const RULE_FIELDS = [["daily_pct", "daily_pct", "daily loss limit %"], ["max_pct", "max_pct", "maximum loss %"], ["target_pct", "target_pct", "profit target %"],
  ["min_days", "min_days", "minimum trading days"], ["fee_usd", "price", "challenge fee, USD"],
  ["fee_usd_5k", "price", "challenge fee at a $5,000 account, USD"], ["split", "split", "profit split"],
  ["drawdown_type", "drawdown_type", "drawdown type"], ["daily_basis", "daily_basis", "daily limit basis"],
  ["fee_per_side_pct", "fee_per_side_pct", "trading fee per side %"], ["max_leverage", "max_leverage", "leverage cap"]];
function firm_rules(a, fields) {
  const F = JSON.parse(context().firms), fk = String(a.firm || ""), pk = String(a.product || "");
  if (!Object.hasOwn(F, fk) || fk.startsWith("_") || !F[fk].products) return { error: "unknown firm. troid covers: " + Object.keys(profiles()).join(", ") };
  const f = F[fk], prods = f.products, live = Object.keys(prods).filter((k) => !k.startsWith("_") && prods[k] && typeof prods[k] === "object");
  if (!live.includes(pk)) return { error: "unknown or pending product for " + f.name + ". options: " + live.join(", ") };
  const pr = prods[pk], rules = [], sources = [];
  // A stage of a staged challenge (2step_s1, 2step_s2) shares the challenge's one fee, which troid records on one
  // stage: every stage gets it, labelled so (run 4, s-product: "$799 (Stage 1 fee)" and "whatever Stage 2 costs").
  const stage = /^(.+)_s\d+$/.exec(pk), lab = (k) => (f.calc && f.calc.products && f.calc.products[k] && f.calc.products[k].label) || k;
  const feeAt = stage ? live.find((k) => k.startsWith(stage[1] + "_s") && prods[k].fee_usd != null) : null;
  for (const [vk, ck, rule0] of fields || RULE_FIELDS) {
    let v = vk in pr ? pr[vk] : f[vk], rule = rule0, at = pk;
    if (typeof v === "boolean") v = v ? "yes" : "no";
    if (vk === "fee_usd" && feeAt) {
      v = prods[feeAt].fee_usd; at = feeAt;
      rule = rule0 + " (one fee for the whole " + lab(pk).replace(/\s*·\s*S\d+$/, "") + "; troid records it on " + lab(feeAt) + " and no fee for another stage)";
    }
    if (v === undefined || (v !== null && typeof v === "object")) continue;
    rules.push({ rule, value: v === null ? "pending" : v });
    const c = cite(f, ck, at, true);
    sources.push(c ? { rule: rule + " " + (v === null ? "pending" : v), document_section: c.section, read_on: c.read_on.length ? c.read_on : "not recorded", urls: c.urls }
                   : { rule: rule + " " + (v === null ? "pending" : v), source: "not yet recorded" });
  }
  return { firm: f.name, product: pk, rules, sources,
           tier: "SOURCED — each rule as troid has recorded it, with the document and the date troid read it; a rule marked pending or not yet recorded is not filled in. The firm's own documents govern." };
}

// What each firm's own terms exclude, by country (firms.json availability). troid never says a firm is available
// in a country: it reports what its record of the firm's terms excludes, or that it has not recorded the list.
function check_availability(a) {
  const F = JSON.parse(context().firms), key = String(a.firm || ""), cc = String(a.country || "").toUpperCase().trim();
  if (!Object.hasOwn(F, key) || key.startsWith("_") || !F[key].availability) return { error: "unknown firm. troid covers: " + Object.keys(profiles()).join(", ") };
  if (!/^[A-Z]{2}$/.test(cc)) return { error: "country must be an ISO 3166-1 alpha-2 code, e.g. US, IN, NG" };
  const f = F[key], av = f.availability, out = { firm: f.name, country: cc };
  const src = (field) => { const c = cite(f, field, null, true); return c ? { document_section: c.section, read_on: c.read_on, urls: c.urls } : { source: "not yet recorded" }; };
  if (!av.recorded) return { ...out, status: "not_recorded", detail: av.basis || "troid has not recorded this firm's excluded countries.",
                             advice: "Check the firm's own terms before buying." };
  if ((av.excluded || []).includes(cc)) return { ...out, status: "excluded", detail: f.name + "'s terms exclude " + cc + ".", sources: [src("availability")] };
  const platforms = Object.entries(av.platform || {}).filter(([, list]) => list.includes(cc)).map(([p]) => p);
  const third = (av.not_from_terms || {})[cc];
  const res = { ...out, status: platforms.length ? "platform_excluded" : "not_excluded_in_record",
    detail: platforms.length ? f.name + "'s terms exclude " + cc + " from " + platforms.join(", ") + " only."
                             : (av.note ? av.note + " " : "") + "troid's record of " + f.name + "'s terms does not exclude " + cc + ". That is not a statement that the firm serves " + cc + ".",
    sources: [src("availability"), ...(platforms.length ? [src("availability_platform")] : [])],
    advice: "Check the firm's own terms before buying." };
  if (third) res.not_in_terms = "A third party lists " + cc + " as excluded; troid has not read that in the firm's terms (" + third + ").";
  return res;
}

// ---------------------------------------------------------------- trade_math
// Trading arithmetic that needs no firm rule, so the model never does arithmetic itself (TROID-CHARACTER.md: compute
// through the tools, never in its head). Every result carries the formula, each step with its value, and its tier:
// DERIVED from the numbers given. kelly can set its result beside a firm product's loss limits, with their sources.
// Percentages come in as percent (45 means 45%). A result troid can only approximate says so in its note.
const MATH_FORMULAS = {
  r_multiple: "1R = |entry − stop| × quantity (troid's desk adds both fees: + fee × (entry + stop) × quantity, the exit fee charged at the stop); R of a result = result ÷ 1R",
  position_size: "quantity = risk ÷ (|entry − stop| + fee × (entry + stop)); notional = quantity × entry; margin = notional ÷ leverage; the loss at the stop = quantity × (|entry − stop| + fee × (entry + stop)) = risk",
  expectancy: "E = p × W − (1 − p) × L; break-even win rate = L ÷ (W + L) = 1 ÷ (1 + W/L)",
  kelly: "f* = p − (1 − p) ÷ b, where b = average win ÷ average loss",
  recovery: "gain needed = d ÷ (1 − d)",
  fee_share: "fee share of risk = f × (2 − s) ÷ (s + f × (2 − s)) on a long, f × (2 + s) ÷ (s + f × (2 + s)) on a short; side-neutral approximation, both fees at the entry price: 2f ÷ (s + 2f). f = fee per side, s = stop distance as a fraction of entry",
  losses_to_limit: "losses = budget ÷ risk per loss",
  capped_budget: "budget after n losses = B × (1 − c)^n",
  stats: "SE = sd ÷ √n; t = mean ÷ SE; 95% CI = mean ± 1.96 × SE",
  atr_scale: "ATR(T2) ≈ ATR(T1) × √(T2 ÷ T1)",
  effective_bets: "effective bets = n ÷ (1 + (n − 1) × ρ)",
};
class MathInputError extends Error {}
const rd = (v, d) => (Number.isFinite(v) ? +v.toFixed(d == null ? 6 : d) : v);
// A firm's rule inside a worked example: firm and product supply it with its source, so no firm's rule is typed into a
// calculation by hand (run 3: b-stop gave Bitfunded's 0.04% and ex-recovery its 10% without the dates troid read them).
function mathProduct(a) {
  const g = profile(String(a.firm || ""), String(a.product || ""));
  if (g.error) throw new MathInputError(g.error);
  return g;
}
function mathFee(x, a) {                                              // { fee, sources } or { fee: null }
  const given = x("fee_per_side_pct", { min: 0, max: 5, optional: true });
  if (given != null || (a.firm == null && a.product == null)) return { fee: given };
  const g = mathProduct(a);
  if (g.p.fee == null) throw new MathInputError(g.f.name + " " + g.p.label + ": troid has no trading fee recorded for this product (pending)");
  return { fee: g.p.fee, sources: sourcesFor(g.p, [["fee", "fee " + g.p.fee + "% per side (" + g.f.name + " " + g.p.label + ")"]]) };
}
const MATH = {
  r_multiple(x, a) {
    const entry = x("entry", { gt: 0 }), stop = x("stop", { gt: 0 }), q = x("quantity", { gt: 0 });
    const mf = mathFee(x, a), fee = mf.fee, res = x("result", { optional: true });
    const dist = Math.abs(entry - stop);
    if (!(dist > 0)) throw new MathInputError("entry and stop are the same price, so 1R is zero");
    const w = [{ step: "stop distance", formula: "|entry − stop|", value: rd(dist) }, { step: "1R", formula: "stop distance × quantity", value: rd(dist * q, 2) }];
    const out = { one_r: rd(dist * q, 2) };
    let base = dist * q;
    if (fee != null) {
      const rt = fee / 100 * (entry + stop) * q;
      base += rt;
      w.push({ step: "fees in and out", formula: fee + "% × (entry + stop) × quantity: the entry fee at entry, the exit fee at the stop", value: rd(rt, 2) },
             { step: "1R with fees", formula: "1R + fees in and out (troid's desk counts them in the risk)", value: rd(base, 2) });
      out.one_r_with_fees = rd(base, 2);
    }
    if (res != null) { w.push({ step: "R of the result", formula: "result ÷ " + (fee != null ? "1R with fees" : "1R"), value: rd(res / base, 3) }); out.r_multiple = rd(res / base, 3); }
    return { working: w, result: out, sources: mf.sources };
  },
  position_size(x, a) {
    const risk = x("risk", { gt: 0 }), entry = x("entry", { gt: 0 }), stop = x("stop", { gt: 0 });
    const mf = mathFee(x, a), fee = mf.fee, lev = x("leverage", { gt: 0, max: 200, optional: true });
    const dist = Math.abs(entry - stop);
    if (!(dist > 0)) throw new MathInputError("entry and stop are the same price");
    const fu = (fee || 0) / 100 * (entry + stop), q = risk / (dist + fu);
    const w = [{ step: "stop distance", formula: "|entry − stop|", value: rd(dist) },
               { step: "fee per unit", formula: fee == null ? "no fee given: 0" : "(entry + stop) × " + fee + "%", value: rd(fu) },
               { step: "quantity", formula: "risk ÷ (stop distance + fee per unit)", value: rd(q) },
               { step: "notional", formula: "quantity × entry", value: rd(q * entry, 2) }];
    const result = { quantity: rd(q), notional: rd(q * entry, 2) };
    if (lev != null) { w.push({ step: "margin", formula: "notional ÷ " + lev, value: rd(q * entry / lev, 2) }); result.margin = rd(q * entry / lev, 2); }
    return { working: w, result, sources: mf.sources,
             note: [fee == null ? "No fee was given, so none is counted; a firm's fee makes the quantity smaller." : "",
                    lev != null ? "Leverage sets the margin posted, not the quantity: the loss at the stop is the same at any leverage." : ""].filter(Boolean).join(" ") || undefined };
  },
  expectancy(x) {
    const p = x("win_rate_pct", { min: 0, max: 100 }) / 100, W = x("avg_win", { min: 0 }), L = x("avg_loss", { gt: 0 });
    const n = x("trades", { gt: 0, int: true, optional: true });
    const E = p * W - (1 - p) * L, be = L / (W + L);
    const w = [{ step: "p", formula: "win rate ÷ 100", value: rd(p) },
               { step: "expectancy", formula: `${rd(p)} × ${W} − ${rd(1 - p)} × ${L}`, value: rd(E, 4) },
               { step: "payoff ratio", formula: "W ÷ L", value: rd(W / L, 4) },
               { step: "break-even win rate", formula: `${L} ÷ (${W} + ${L})`, value: rd(be * 100, 2) + "%" }];
    const result = { expectancy: rd(E, 4), breakeven_win_rate_pct: rd(be * 100, 2), payoff_ratio: rd(W / L, 4) };
    if (n != null) { w.push({ step: "expected total over " + n + " trades", formula: `${n} × ${rd(E, 4)}`, value: rd(n * E, 4) }); result.expected_total = rd(n * E, 4); }
    return { working: w, result,
             note: "Expectancy is in the unit of the averages: R if they are in R, dollars if in dollars." + (n != null ? " The expected total is a mean over many runs of " + n + " trades, not what one run will do." : "") };
  },
  kelly(x, a) {
    const p = x("win_rate_pct", { gt: 0, lt: 100 }) / 100, b = x("payoff_ratio", { gt: 0 });
    const f = p - (1 - p) / b;
    const w = [{ step: "p", formula: "win rate ÷ 100", value: rd(p) }, { step: "b", formula: "average win ÷ average loss", value: b },
               { step: "full Kelly", formula: `${rd(p)} − ${rd(1 - p)} ÷ ${b}`, value: rd(f * 100, 2) + "%" },
               { step: "half Kelly", formula: "full Kelly ÷ 2", value: rd(f * 50, 2) + "%" }];
    const out = { working: w, result: { kelly_pct: rd(f * 100, 2), half_kelly_pct: rd(f * 50, 2) },
                  note: f <= 0 ? "No positive edge at these numbers: Kelly risks nothing." : "Kelly maximises long-run growth only if p and b are known exactly, which they never are." };
    if (a.firm != null || a.product != null) {
      const g = profile(String(a.firm || ""), String(a.product || ""));
      if (g.error) throw new MathInputError(g.error);
      const P = g.p;
      w.push({ step: "full Kelly ÷ max loss", formula: `${rd(f * 100, 2)}% ÷ ${P.m}%`, value: rd(f * 100 / P.m, 2) + "×" },
             { step: "half Kelly ÷ max loss", formula: `${rd(f * 50, 2)}% ÷ ${P.m}%`, value: rd(f * 50 / P.m, 2) + "×" },
             { step: "full Kelly ÷ daily limit", formula: `${rd(f * 100, 2)}% ÷ ${P.d}%`, value: rd(f * 100 / P.d, 2) + "×" });
      Object.assign(out.result, { firm: g.f.name, product: P.label, daily_pct: P.d, max_pct: P.m,
                                  full_kelly_vs_max: rd(f * 100 / P.m, 2), half_kelly_vs_max: rd(f * 50 / P.m, 2) });
      out.sources = sourcesFor(P, [["d", "daily " + P.d + "%"], ["m", "max " + P.m + "%"]]);
    }
    return out;
  },
  recovery(x, a) {
    const d = x("drawdown_pct", { min: 0, lt: 100 }) / 100, bal = x("balance", { gt: 0, optional: true });
    const g = d / (1 - d);
    const w = [{ step: "d", formula: "drawdown ÷ 100", value: rd(d) }, { step: "gain needed", formula: `${rd(d)} ÷ (1 − ${rd(d)})`, value: rd(g * 100, 2) + "%" }];
    const out = { gain_needed_pct: rd(g * 100, 2) };
    let sources;
    if (bal != null) {
      w.push({ step: "balance after the drawdown", formula: "balance × (1 − d)", value: rd(bal * (1 - d), 2) },
             { step: "amount to recover", formula: "balance − balance after", value: rd(bal * d, 2) });
      Object.assign(out, { balance_after: rd(bal * (1 - d), 2), amount_to_recover: rd(bal * d, 2) });
    }
    // beside the largest maximum loss troid has read, and whose, unless a firm and product are given (run 6: ex-recovery
    // wrote "6-10%" from memory, undated and wrong: Express is 3%)
    if (String(a.firm || "") === "all" || (a.firm == null && a.product == null)) {
      const top = [];
      let m = -1;
      for (const f of Object.values(profiles())) for (const p of Object.values(f.products)) {
        if (p.m > m) { m = p.m; top.length = 0; }
        if (p.m === m) top.push({ f, p });
      }
      w.push({ step: "largest maximum loss troid has read", formula: "the largest max % of every product troid covers", value: m + "%" },
             { step: "drawdown against it", formula: `${rd(d * 100, 2)}% ≥ ${m}%`, value: d * 100 >= m ? "past every maximum loss troid has read" : "inside at least one" });
      Object.assign(out, { largest_max_loss_pct: m, products_at_largest: top.map((t) => t.f.name + " " + t.p.label), past_every_max_loss: d * 100 >= m });
      sources = top.flatMap((t) => sourcesFor(t.p, [["m", "max " + m + "% (" + t.f.name + " " + t.p.label + ")"]]));
    } else if (a.firm != null || a.product != null) {
      const t = mathProduct(a);
      w.push({ step: "drawdown against the maximum loss", formula: `${rd(d * 100, 2)}% vs ${t.p.m}%`, value: d * 100 >= t.p.m ? "past it" : "inside it" });
      Object.assign(out, { firm: t.f.name, product: t.p.label, max_pct: t.p.m, past_max_loss: d * 100 >= t.p.m });
      sources = sourcesFor(t.p, [["m", "max " + t.p.m + "% (" + t.f.name + " " + t.p.label + ")"]]);
    }
    return { working: w, result: out, sources };
  },
  fee_share(x, a) {
    const mf = mathFee(x, a);
    if (mf.fee == null || !(mf.fee > 0)) throw new MathInputError("fee_share needs fee_per_side_pct, or firm and product");
    const f = mf.fee / 100, st = x("stop_pct", { gt: 0, lt: 100 }) / 100, F = rd(f * 100, 4), S = rd(st * 100, 4);
    const sd = a.side == null || a.side === "" ? null : String(a.side).toLowerCase().startsWith("l") ? 1 : String(a.side).toLowerCase().startsWith("s") ? -1 : 0;
    if (sd === 0) throw new MathInputError("side must be long or short");
    // a unit's fees are f × (entry + stop): f × (2 − s) of entry on a long, whose stop is below entry, f × (2 + s) on a short
    const at = (g) => f * (2 - g * st) / (st + f * (2 - g * st));
    const line = (g) => ({ step: "fee share of risk, " + (g > 0 ? "long" : "short"),
      formula: `${F}% × (2 ${g > 0 ? "−" : "+"} ${S}%) ÷ (${S}% + ${F}% × (2 ${g > 0 ? "−" : "+"} ${S}%))`, value: rd(at(g) * 100, 2) + "%" });
    const neutral = 2 * f / (st + 2 * f);
    if (sd != null) return { working: [line(sd)], result: { side: sd > 0 ? "long" : "short", fee_share_pct: rd(at(sd) * 100, 2) }, sources: mf.sources,
      note: "The exit fee is charged at the stop: below entry on a long, above it on a short, so a short's share is a little higher. Depends only on the stop distance, the fee and the side: not the asset, not leverage." };
    return { working: [line(1), line(-1), { step: "side-neutral approximation, both fees at the entry price", formula: `2 × ${F}% ÷ (${S}% + 2 × ${F}%)`, value: rd(neutral * 100, 2) + "%" }],
             result: { fee_share_long_pct: rd(at(1) * 100, 2), fee_share_short_pct: rd(at(-1) * 100, 2), fee_share_side_neutral_pct: rd(neutral * 100, 2) }, sources: mf.sources,
             note: "No side given: both sides are shown. The exit fee is charged at the stop, below entry on a long and above it on a short, so a long's share is a little lower and a short's a little higher than the side-neutral figure, which prices both fees at entry. Depends only on the stop distance, the fee and the side: not the asset, not leverage." };
  },
  losses_to_limit(x) {
    const B = x("budget", { gt: 0 }), r = x("risk", { gt: 0 });
    const whole = Math.floor(B / r + 1e-9), reach = Math.ceil(B / r - 1e-9);
    return { working: [{ step: "budget ÷ risk", formula: `${B} ÷ ${r}`, value: rd(B / r, 4) },
                       { step: "losses that fit", formula: "floor(budget ÷ risk)", value: whole },
                       { step: "left after them", formula: "budget − losses × risk", value: rd(B - whole * r, 2) },
                       { step: "the loss that reaches the limit", formula: "ceil(budget ÷ risk)", value: reach }],
             result: { losses_that_fit: whole, left_after: rd(B - whole * r, 2), loss_that_reaches_limit: reach } };
  },
  capped_budget(x) {
    const B = x("budget", { gt: 0 }), c = x("cap_pct", { gt: 0, lt: 100 }) / 100, n = x("losses", { min: 1, max: 50, int: true });
    const w = [];
    for (let i = 1; i <= n; i++) w.push({ step: "after loss " + i, formula: `${B} × ${rd(1 - c)}^${i}`, value: rd(B * Math.pow(1 - c, i), 2) });
    return { working: w, result: { budget_after: rd(B * Math.pow(1 - c, n), 2), share_left_pct: rd(Math.pow(1 - c, n) * 100, 2) },
             note: "Under a proportional cap the budget approaches zero without reaching it: realized losses alone cannot empty it." };
  },
  stats(x) {
    const m = x("mean"), sd = x("sd", { gt: 0 }), n = x("n", { min: 2, int: true }), k = x("configs", { min: 2, int: true, optional: true });
    const se = sd / Math.sqrt(n), lo = m - 1.96 * se, hi = m + 1.96 * se;
    const w = [{ step: "standard error", formula: `${sd} ÷ √${n}`, value: rd(se, 4) }, { step: "t", formula: "mean ÷ SE", value: rd(m / se, 3) },
               { step: "95% confidence interval", formula: "mean ± 1.96 × SE", value: "[" + rd(lo, 4) + ", " + rd(hi, 4) + "]" }];
    const out = { standard_error: rd(se, 4), t: rd(m / se, 3), ci95_low: rd(lo, 4), ci95_high: rd(hi, 4), ci_contains_zero: lo < 0 && hi > 0 };
    if (k != null) {
      const z = expectedMaxNormal(k), best = se * z;
      w.push({ step: "expected best of " + k + " independent draws, in standard errors", formula: "E[max of " + k + " standard normals]", value: rd(z, 4) },
             { step: "best of " + k + " configurations under a zero edge", formula: "SE × " + rd(z, 4), value: rd(best, 4) });
      out.expected_best_in_se = rd(z, 4);
      out.best_of_configs_by_chance = rd(best, 4);
    }
    return { working: w, result: out, note: "Normal approximation. An interval that contains zero means the mean is not distinguishable from zero on this sample."
             + (k != null ? " The best-of-k figure assumes the k configurations are independent; neighbouring settings are correlated, which lowers it." : "") };
  },
  atr_scale(x) {
    const atr = x("atr", { gt: 0 }), t1 = x("from_minutes", { gt: 0 }), t2 = x("to_minutes", { gt: 0 });
    const v = atr * Math.sqrt(t2 / t1);
    return { working: [{ step: "scale", formula: `√(${t2} ÷ ${t1})`, value: rd(Math.sqrt(t2 / t1), 4) }, { step: "ATR on the new timeframe", formula: `${atr} × scale`, value: rd(v, 2) }],
             result: { atr: rd(v, 2) }, note: "An approximation: it assumes returns are independent from bar to bar. Real ATR often differs." };
  },
  effective_bets(x) {
    const n = x("positions", { min: 1, max: 100, int: true }), rho = x("correlation", { max: 1 });
    if (n > 1 && rho <= -1 / (n - 1)) throw new MathInputError("that correlation is impossible for " + n + " positions that all share it");
    const e = n / (1 + (n - 1) * rho);
    return { working: [{ step: "effective bets", formula: `${n} ÷ (1 + ${n - 1} × ${rho})`, value: rd(e, 2) }],
             result: { effective_bets: rd(e, 2) }, note: "Assumes equal risk on each position and the same correlation between every pair." };
  },
};
// math, formulas: the calc table (the candidate's is MATH_NEXT, MATH_FORMULAS_NEXT); the live one when left out
function trade_math(a, math, formulas) {
  const M = math || MATH, FM = formulas || MATH_FORMULAS;
  const calc = String(a.calc || "");
  if (!Object.hasOwn(M, calc)) return { error: "unknown calc. options: " + Object.keys(M).join(", ") };
  const x = (k, o) => {
    o = o || {};
    const v = a[k];
    if (v === undefined || v === null || v === "") { if (o.optional) return null; throw new MathInputError(calc + " needs " + k); }
    const n = typeof v === "number" ? v : Number(v);
    if (!Number.isFinite(n)) throw new MathInputError(k + " must be a number");
    if ((o.min != null && n < o.min) || (o.max != null && n > o.max) || (o.gt != null && !(n > o.gt)) || (o.lt != null && !(n < o.lt)) || (o.int && !Number.isInteger(n)))
      throw new MathInputError(k + " is out of range");
    return n;
  };
  try {
    const r = M[calc](x, a);
    if (!r.sources || !r.sources.length) delete r.sources;
    return Object.assign({ calc, formula: FM[calc] }, r, {
      tier: r.sources ? "DERIVED from the numbers given and the firm rules listed" : "DERIVED from the numbers given; no firm rule used" });
  } catch (e) {
    if (e instanceof MathInputError) return { error: e.message };
    throw e;
  }
}
// The candidate's trade_math (CANDIDATE_RUN, through tradeMathNext): the calculator audit's F6 and F7 as troid's desk
// does them (audit/SPEC.md). A unit's fees are fee × (entry + stop), the exit fee priced at the stop; losses left are
// ceil(budget ÷ risk) − 1, the losses that leave equity above the limit. Promotion folds these into MATH and
// MATH_FORMULAS.
const MATH_FORMULAS_NEXT = Object.assign({}, MATH_FORMULAS, {
  r_multiple: "1R = |entry − stop| × quantity (troid's desk adds both fees: + fee × (entry + stop) × quantity, the exit fee charged at the stop); R of a result = result ÷ 1R",
  position_size: "quantity = risk ÷ (|entry − stop| + fee × (entry + stop)); notional = quantity × entry; margin = notional ÷ leverage; the loss at the stop = quantity × (|entry − stop| + fee × (entry + stop)) = risk. With equity: a margin above it can't be opened, so quantity = equity × leverage ÷ entry, cut to fit, and the loss at the stop is less than the risk",
  fee_share: "fee share of risk = f × (2 − s) ÷ (s + f × (2 − s)) on a long, f × (2 + s) ÷ (s + f × (2 + s)) on a short; side-neutral approximation, both fees at the entry price: 2f ÷ (s + 2f). f = fee per side, s = stop distance as a fraction of entry",
  losses_to_limit: "losses left = ceil(budget ÷ risk) − 1: the losses that leave equity above the limit; the loss that reaches it = ceil(budget ÷ risk)",
});
const MATH_NEXT = Object.assign({}, MATH, {
  r_multiple(x, a) {
    const entry = x("entry", { gt: 0 }), stop = x("stop", { gt: 0 }), q = x("quantity", { gt: 0 });
    const mf = mathFee(x, a), fee = mf.fee, res = x("result", { optional: true });
    const dist = Math.abs(entry - stop);
    if (!(dist > 0)) throw new MathInputError("entry and stop are the same price, so 1R is zero");
    const w = [{ step: "stop distance", formula: "|entry − stop|", value: rd(dist) }, { step: "1R", formula: "stop distance × quantity", value: rd(dist * q, 2) }];
    const out = { one_r: rd(dist * q, 2) };
    let base = dist * q;
    if (fee != null) {
      const rt = fee / 100 * (entry + stop) * q;
      base += rt;
      w.push({ step: "fees in and out", formula: fee + "% × (entry + stop) × quantity: the entry fee at entry, the exit fee at the stop", value: rd(rt, 2) },
             { step: "1R with fees", formula: "1R + fees in and out (troid's desk counts them in the risk)", value: rd(base, 2) });
      out.one_r_with_fees = rd(base, 2);
    }
    if (res != null) { w.push({ step: "R of the result", formula: "result ÷ " + (fee != null ? "1R with fees" : "1R"), value: rd(res / base, 3) }); out.r_multiple = rd(res / base, 3); }
    return { working: w, result: out, sources: mf.sources };
  },
  position_size(x, a) {
    const risk = x("risk", { gt: 0 }), entry = x("entry", { gt: 0 }), stop = x("stop", { gt: 0 });
    const mf = mathFee(x, a), fee = mf.fee, lev = x("leverage", { gt: 0, max: 200, optional: true }), eq = x("equity", { gt: 0, optional: true });
    const dist = Math.abs(entry - stop);
    if (!(dist > 0)) throw new MathInputError("entry and stop are the same price");
    const fu = (fee || 0) / 100 * (entry + stop), q0 = risk / (dist + fu);
    // the calculator audit's F1: a margin above equity can't be opened, so the size is cut to what equity carries at this
    // leverage, and the loss at the stop falls with it, as troid's desk does. Checked when equity and leverage are given
    const m0 = lev != null ? q0 * entry / lev : null, cut = m0 != null && eq != null && m0 > eq + 1e-9, q = cut ? eq * lev / entry : q0;
    const w = [{ step: "stop distance", formula: "|entry − stop|", value: rd(dist) },
               { step: "fee per unit", formula: fee == null ? "no fee given: 0" : "(entry + stop) × " + fee + "%", value: rd(fu) },
               { step: "quantity", formula: cut ? "equity × leverage ÷ entry: cut to fit the margin" : "risk ÷ (stop distance + fee per unit)", value: rd(q) },
               { step: "notional", formula: "quantity × entry", value: rd(q * entry, 2) }];
    const result = { quantity: rd(q), notional: rd(q * entry, 2) };
    if (fee != null || cut) {
      if (fee != null) w.push({ step: "fees", formula: "quantity × fee per unit", value: rd(q * fu, 2) });
      w.push({ step: "loss at the stop", formula: fee != null ? "quantity × (stop distance + fee per unit)" : "quantity × stop distance", value: rd(q * (dist + fu), 2) });
      Object.assign(result, fee != null ? { fees: rd(q * fu, 2) } : {}, { loss_at_stop: rd(q * (dist + fu), 2) });
    }
    if (lev != null) { w.push({ step: "margin", formula: "notional ÷ " + lev, value: rd(q * entry / lev, 2) }); result.margin = rd(q * entry / lev, 2); }
    if (lev != null && eq != null) w.push({ step: "margin check", formula: cut ? `margin at the risk-based size > equity ${rd(eq, 2)}: size cut to equity × ${lev}× ÷ entry` : `margin at the risk-based size ≤ equity ${rd(eq, 2)}`, value: rd(m0, 2) });
    if (cut) result.cut_to_fit_margin = true;
    return { working: w, result, sources: mf.sources,
             note: [fee == null ? "No fee was given, so none is counted; a firm's fee makes the quantity smaller." :
                      cut ? "The exit fee is charged at the stop, so both fees are in the loss at the stop." :
                      "The exit fee is charged at the stop, so the loss at the stop, both fees in it, is the risk, long or short.",
                    cut ? `Cut to fit the margin: at ${lev}× equity of ${rd(eq, 2)} carries at most ${rd(eq * lev, 2)} of notional, so this size risks ${rd(q * (dist + fu), 2)}, less than the ${rd(risk, 2)} given.` :
                    lev != null ? "Leverage sets the margin posted, not the quantity: the loss at the stop is the same at any leverage" +
                      (eq != null ? ", while the margin fits in equity." : "; troid's desk cuts a size whose margin is above equity to what equity carries, so give equity to check it.") : ""].filter(Boolean).join(" ") };
  },
  fee_share(x, a) {
    const mf = mathFee(x, a);
    if (mf.fee == null || !(mf.fee > 0)) throw new MathInputError("fee_share needs fee_per_side_pct, or firm and product");
    const f = mf.fee / 100, st = x("stop_pct", { gt: 0, lt: 100 }) / 100, F = rd(f * 100, 4), S = rd(st * 100, 4);
    const sd = a.side == null || a.side === "" ? null : String(a.side).toLowerCase().startsWith("l") ? 1 : String(a.side).toLowerCase().startsWith("s") ? -1 : 0;
    if (sd === 0) throw new MathInputError("side must be long or short");
    // a unit's fees are f × (entry + stop): f × (2 − s) of entry on a long, whose stop is below entry, f × (2 + s) on a short
    const at = (g) => f * (2 - g * st) / (st + f * (2 - g * st));
    const line = (g) => ({ step: "fee share of risk, " + (g > 0 ? "long" : "short"),
      formula: `${F}% × (2 ${g > 0 ? "−" : "+"} ${S}%) ÷ (${S}% + ${F}% × (2 ${g > 0 ? "−" : "+"} ${S}%))`, value: rd(at(g) * 100, 2) + "%" });
    const neutral = 2 * f / (st + 2 * f);
    if (sd != null) return { working: [line(sd)], result: { side: sd > 0 ? "long" : "short", fee_share_pct: rd(at(sd) * 100, 2) }, sources: mf.sources,
      note: "The exit fee is charged at the stop: below entry on a long, above it on a short, so a short's share is a little higher. Depends only on the stop distance, the fee and the side: not the asset, not leverage." };
    return { working: [line(1), line(-1), { step: "side-neutral approximation, both fees at the entry price", formula: `2 × ${F}% ÷ (${S}% + 2 × ${F}%)`, value: rd(neutral * 100, 2) + "%" }],
             result: { fee_share_long_pct: rd(at(1) * 100, 2), fee_share_short_pct: rd(at(-1) * 100, 2), fee_share_side_neutral_pct: rd(neutral * 100, 2) }, sources: mf.sources,
             note: "No side given: both sides are shown. The exit fee is charged at the stop, below entry on a long and above it on a short, so a long's share is a little lower and a short's a little higher than the side-neutral figure, which prices both fees at entry. Depends only on the stop distance, the fee and the side: not the asset, not leverage." };
  },
  losses_to_limit(x) {
    const B = x("budget", { gt: 0 }), r = x("risk", { gt: 0 });
    const reach = Math.ceil(B / r - 1e-9), left = reach - 1;
    return { working: [{ step: "budget ÷ risk", formula: `${B} ÷ ${r}`, value: rd(B / r, 4) },
                       { step: "the loss that reaches the limit", formula: "ceil(budget ÷ risk)", value: reach },
                       { step: "losses left", formula: "ceil(budget ÷ risk) − 1", value: left },
                       { step: "room left after them", formula: "budget − losses left × risk", value: rd(B - left * r, 2) }],
             result: { losses_left: left, room_left_after: rd(B - left * r, 2), loss_that_reaches_limit: reach },
             note: "Firms fail an account that reaches its limit, so losses left counts the losses that leave equity above it, as troid's desk does; the next one reaches it." };
  },
});
const TRADE_MATH_TOOL = { name: "trade_math",
  description: "Trading arithmetic that needs no firm rule, returned with the formula and every step. calc and its inputs: r_multiple (entry, stop, quantity; optional result, fee_per_side_pct or firm and product for that product's fee); position_size (risk, entry, stop; optional fee_per_side_pct or firm and product, leverage for the margin); expectancy (win_rate_pct, avg_win, avg_loss; optional trades for the expected total over that many); kelly (win_rate_pct, payoff_ratio; optional firm and product to set it beside that product's loss limits, with their sources); recovery (drawdown_pct; optional balance; set beside the largest maximum loss troid has read, with its sources, unless firm and product name one product); fee_share (stop_pct; fee_per_side_pct, or firm and product); losses_to_limit (budget, risk); capped_budget (budget, cap_pct, losses); stats (mean, sd, n; optional configs); atr_scale (atr, from_minutes, to_minutes); effective_bets (positions, correlation). Percentages are in percent: 45 means 45%. A firm's rule given through firm and product comes back with its source and read date. Never call it to suggest a trade.",
  input_schema: { type: "object", properties: {
    calc: { type: "string", enum: Object.keys(MATH_FORMULAS) },
    entry: { type: "number" }, stop: { type: "number" }, quantity: { type: "number" }, result: { type: "number", description: "a trade's profit or loss, for its R-multiple" },
    risk: { type: "number", description: "dollars risked per trade" }, fee_per_side_pct: { type: "number" },
    win_rate_pct: { type: "number" }, avg_win: { type: "number" }, avg_loss: { type: "number" }, payoff_ratio: { type: "number" },
    firm: { type: "string" }, product: { type: "string" }, drawdown_pct: { type: "number" }, balance: { type: "number" },
    stop_pct: { type: "number", description: "stop distance as a percent of price" }, budget: { type: "number" }, cap_pct: { type: "number" },
    losses: { type: "integer" }, mean: { type: "number" }, sd: { type: "number" }, n: { type: "integer" }, configs: { type: "integer" },
    atr: { type: "number" }, from_minutes: { type: "number" }, to_minutes: { type: "number" }, positions: { type: "integer" }, correlation: { type: "number" },
    leverage: { type: "number", description: "for position_size: the margin posted is notional ÷ leverage" },
    trades: { type: "integer", description: "for expectancy: the number of trades to total it over" } },
    required: ["calc"] } };

// The candidate's trade_math schema: a side for fee_share and for position_size with stop_pct (the exit fee is charged
// at the stop, so the side sets the fee), and the F6/F7 wording. Replaces TRADE_MATH_TOOL in TOOLS_NEXT until promoted.
const TRADE_MATH_TOOL_NEXT = Object.assign({}, TRADE_MATH_TOOL, {
  description: TRADE_MATH_TOOL.description
    .replace("position_size (risk, entry, stop; optional fee_per_side_pct or firm and product, leverage for the margin)",
             "position_size (risk, entry, and stop, or stop_pct with side; optional fee_per_side_pct or firm and product, leverage for the margin, equity with leverage to check the margin fits; a unit's fees are fee × (entry + stop), so the loss at the stop is the risk, unless the margin at that size is above equity: then the size is cut to equity × leverage ÷ entry and the loss is less, as troid's desk does)")
    .replace("fee_share (stop_pct; fee_per_side_pct, or firm and product)",
             "fee_share (stop_pct; fee_per_side_pct, or firm and product; optional side: without it, the long and short shares and the side-neutral approximation)")
    .replace("losses_to_limit (budget, risk)", "losses_to_limit (budget, risk: the losses left that keep equity above the limit, as troid's desk counts them, and the loss that reaches it)"),
  input_schema: Object.assign({}, TRADE_MATH_TOOL.input_schema, { properties: Object.assign({}, TRADE_MATH_TOOL.input_schema.properties, {
    side: { type: "string", enum: ["long", "short"], description: "for fee_share, and position_size with stop_pct: the exit fee is charged at the stop, below entry on a long, above it on a short" },
    equity: { type: "number", description: "for position_size with leverage: the account's equity. A margin above it can't be opened, so the size is cut to equity × leverage ÷ entry" } }) }),
});
const FIRM_RULES_TOOL = { name: "firm_rules",
  description: "A firm product's rules as troid has recorded them — daily and maximum loss, profit target, minimum trading days, the challenge fee, split, drawdown type, daily limit basis, trading fee, leverage cap — each with the document and the date troid read it, or marked pending. Use it to state or compare a product's rules; never state one from memory.",
  input_schema: { type: "object", properties: { firm: { type: "string", description: "bitfunded | brightfunded | crypto_fund_trader" },
    product: { type: "string", description: "product key, e.g. 1step, 2step_s1, 2step_s2, express, instant, 1phase, 2phase" } }, required: ["firm", "product"] } };
const TOOLS = [
  { name: "size_trade", description: "Size a trade the user brings against a firm product troid covers: both loss ceilings, the binding one, quantity net of fees, margin, fee share of risk, losses left, circuit-breaker order, every formula and intermediate value (working), and the source and read date of each rule used. Pending fields are reported as pending. Never call this to suggest a trade.",
    input_schema: { type: "object", properties: {
      firm: { type: "string", description: "firm key from firms.json: bitfunded | brightfunded | crypto_fund_trader" },
      product: { type: "string", description: "product key, e.g. 1step, 2step_s1, 1phase, instant" },
      quota: { type: "number" }, equity: { type: "number" }, day_start: { type: "number", description: "balance at the last daily reset; defaults to equity" },
      high_water_mark: { type: "number", description: "trailing products only; defaults to max(equity, quota)" },
      high_at_rollover: { type: "number", description: "BrightFunded only: max(balance, equity) at the last rollover; defaults to day_start" },
      side: { type: "string", enum: ["long", "short"] }, entry: { type: "number" }, stop: { type: "number", description: "stop price; or give stop_pct" },
      target_r: { type: "number" }, risk_pct: { type: "number", description: "percent of equity, default 0.5" },
      budget_cap_pct: { type: "number", description: "cap as percent of the binding budget, default 35" },
      leverage: { type: "number" }, margin_mode: { type: "string", enum: ["cross", "isolated"] },
      stop_pct: { type: "number", description: "the stop as a percent of entry, when the user gives it that way (0.3 means 0.3%): troid prices the stop from entry and side" } },
      required: ["firm", "product", "quota", "equity", "side", "entry"] } },
  { name: "check_budget", description: "Room left under each loss ceiling for a firm product troid covers, which one binds, and the crossover equity, with the formulas (working) and the source and read date of each rule used.",
    input_schema: { type: "object", properties: {
      firm: { type: "string" }, product: { type: "string" }, quota: { type: "number" }, equity: { type: "number" },
      day_start: { type: "number" }, high_water_mark: { type: "number" }, high_at_rollover: { type: "number" } },
      required: ["firm", "product", "quota", "equity"] } },
  { name: "check_compliance", description: "Check a trade plan against the firm rules that disqualify (hold limit, open-trade cap, concentration ladder, closed-trade minimum, third-party strategies, accounts per level, minimum days). It also lists, as info, two prohibitions it cannot check from a plan (switching strategies between assessment and funded accounts; opposite positions across connected accounts): raise them when the conversation makes them relevant. Modelled for Bitfunded only; other firms return pending.",
    input_schema: { type: "object", properties: {
      firm: { type: "string" }, product: { type: "string" }, symbol: { type: "string" }, hold_days: { type: "number" },
      open_trades: { type: "integer" }, margin_pct_of_capital: { type: "number" }, trading_days_so_far: { type: "integer" },
      uses_third_party_strategy: { type: "boolean" }, accounts_at_this_level: { type: "integer" }, closed_trades_this_stage: { type: "integer" } },
      required: ["firm"] } },
  { name: "check_availability", description: "Whether a firm's own terms, as troid has recorded them, exclude a country. Call it for each firm before discussing that firm with a user who has mentioned their country. It never says a firm is available: it reports what the recorded terms exclude, a platform-only exclusion, or that troid has not recorded the list.",
    input_schema: { type: "object", properties: { firm: { type: "string", description: "firm key: bitfunded | brightfunded | crypto_fund_trader" },
      country: { type: "string", description: "ISO 3166-1 alpha-2 code, e.g. US, IN, NG, BR" } }, required: ["firm", "country"] } },
  { name: "explain_rule", description: "Explain a prop-firm rule and why it matters, with the arithmetic. Topics: crossover, reset, fees, leverage, cross, drawdown, ladder, ruin, min_days, hold_limit, accounts, marketed_strategies, strategy_switching, opposite_positions, funded_stage.",
    input_schema: { type: "object", properties: { topic: { type: "string" } }, required: ["topic"] } },
  TRADE_MATH_TOOL, FIRM_RULES_TOOL,
];
// The tools promoted on 2026-10-08 (TOOLS_LIVE below), staged as the candidate's from the live test of 2026-10-04. trade_math's schema is the
// candidate's (TRADE_MATH_TOOL_NEXT: a side, and the calculator audit's F6 and F7 in its description).
const FIRM_ASSETS_TOOL = { name: "firm_assets",
  description: "The assets a firm's own pages name, as troid has recorded them (what troid's desk lets a trader pick): each with the firm's own name for it, " +
    "its hold-limit tier and limit, and the document and date troid read it. Call it for any question about what a firm lets you trade: a coin, a commodity, a stock. " +
    "An asset it doesn't list is one no page troid has read names: say that, never that the firm doesn't offer it and never that troid has no list.",
  input_schema: { type: "object", properties: { firm: { type: "string", description: "bitfunded | brightfunded | crypto_fund_trader" },
    symbol: { type: "string", description: "optional: one asset to look up, e.g. BTC, TSLA, NVDA" } }, required: ["firm"] } };
const FIRM_RULES_TOOL_NEXT = Object.assign({}, FIRM_RULES_TOOL, { description: FIRM_RULES_TOOL.description.replace("leverage cap —",
  "leverage cap, and the firm-level rules where troid records them (open positions at once, the hold limit by asset tier, the concentration ladder with what each step's two numbers are) —") });
// the owner, 2026-10-06 (runs 25 to 27, s-firm): what an amount buys, every product at once, troid picking none
const PRODUCTS_IN_BUDGET_TOOL = { name: "products_in_budget",
  description: "Every product troid has a price for at or under an amount the user has to spend, cheapest first, each with its price, its account size " +
    "and its source and read date, or that its source is not yet recorded; prices in another currency come apart, never converted. Call it whenever " +
    "the user names an amount to spend on a challenge or asks what an amount buys. Give every product it returns, in its order, as its lines give " +
    "them, then its note, and end with its closing line: never one product set apart as what the money buys.",
  input_schema: { type: "object", properties: { budget: { type: "number", description: "the amount, e.g. 500" },
    currency: { type: "string", enum: ["USD", "EUR"], description: "the amount's currency, USD unless the user wrote euros" } }, required: ["budget"] } };
const PROMOTED_TOOLS = [FIRM_ASSETS_TOOL, PRODUCTS_IN_BUDGET_TOOL];
// Promoted 2026-10-08: every visitor's tools are the ones the candidate ran with since round 1 (trade_math and firm_rules
// in their F6/F7 form, firm_assets and products_in_budget); TOOLS is only their base now. A new candidate's tools
// (CANDIDATE_TOOLS, none staged since) are added to them for the candidate only.
const TOOLS_LIVE = TOOLS.map((t) => (t === TRADE_MATH_TOOL ? TRADE_MATH_TOOL_NEXT : t === FIRM_RULES_TOOL ? FIRM_RULES_TOOL_NEXT : t)).concat(PROMOTED_TOOLS);
const CANDIDATE_TOOLS = [];
const toolsFor = (variant) => (variant === "candidate" && CANDIDATE_TOOLS.length ? TOOLS_LIVE.concat(CANDIDATE_TOOLS) : TOOLS_LIVE);
const RUN = { size_trade, check_budget, check_compliance, check_availability, explain_rule: (a) => explainRuleSourced(a), trade_math, firm_rules };
// The tool implementations promoted on 2026-10-08 (PROMOTED_RUN below). Staged after evaluation run 10:
// - b-limits said "Bitfunded auto-fails on either without requiring a close" with no source: troid had read it in the
//   help centre's Criteria to be Success and recorded it nowhere. It is recorded now (firms.json floating_counts), and
//   firm_rules, check_budget and size_trade give it with its source; a firm with no recorded source says so.
// - b-leverage worked 10x "on a Bitfunded 1-Step account", whose cap is 1:5: trade_math refuses leverage above a
//   product's cap, with the cap's source.
// - s-product called the 2-Step's 8% and 5% "a lower total profit" than the 1-Step's 10%: firm_rules gives a staged
//   challenge's targets added up across its stages.
// run 11, s-firm: BrightFunded's price (€497, €347.90 on promotion, at $100,000) came from the prompt's firms data, its
// read date written by the model; firm_rules gives it with its source now
// run 12, s-firm: "none of Bitfunded's two standard products cost that little" from the $100,000 level's $999 and $799;
// the fee's label says whose account size it is
const RULE_FIELDS_NEXT = RULE_FIELDS.map((f) => (f[0] === "fee_usd" ? ["fee_usd", "price", "challenge fee at the $100,000 account level, USD (troid has recorded no fee for other account sizes of this product)"] : f))
  .concat([["floating_counts", "floating_counts", "floating losses count toward the daily and maximum loss"],
  ["fee_eur_100k", "price", "challenge fee at a $100,000 account, EUR"], ["fee_eur_100k_promo", "price", "challenge fee at a $100,000 account on promotion, EUR"],
  // the owner, 2026-10-06 (run 27, s-firm: "troid has not recorded this product's challenge fee" for Crypto Fund
  // Trader's Instant): Crypto Fund Trader's six fees, which firms.json records under keys firm_rules never read
  ["fee_usd_100k", "price", "challenge fee at a $100,000 account, USD"], ["fee_usd_10k", "price", "challenge fee at a $10,000 account, USD"],
  ["activation_fee_usd_100k", "price", "activation fee at a $100,000 account, USD (troid hasn't recorded when it is charged)"]]);
function firmRulesNext(a) {
  const out = firm_rules(a, RULE_FIELDS_NEXT);
  if (out.error) return out;
  firmLevelRules(out, a);
  const prods = JSON.parse(context().firms)[String(a.firm)].products, stage = /^(.+)_s\d+$/.exec(String(a.product));
  if (stage) {
    const ks = Object.keys(prods).filter((k) => k.startsWith(stage[1] + "_s") && prods[k] && typeof prods[k] === "object").sort();
    const ts = ks.map((k) => prods[k].target_pct);
    if (ks.length > 1 && ts.every((t) => typeof t === "number")) {
      const sum = rd(ts.reduce((x, y) => x + y, 0), 4);
      Object.assign(out, { stage_targets: ks.map((k, i) => ({ product: k, profit_target_pct: ts[i] })),
        profit_target_all_stages: { formula: ts.map((t) => t + "%").join(" + "), value_pct: sum,
          note: "Each stage's target is a percent of the account size, so the targets add up: the realized profit the whole challenge asks for is " +
                sum + "% of the account size. DERIVED from the stages' targets, each with its source above." } });
    }
  }
  return out;
}
// The firm-level rules (the live test of 2026-10-04, session a4fc357b…, Bitfunded 2-Step): the open-position cap, the hold
// limit by asset tier and the concentration ladder, which firm_rules skipped (an object, or no product field), so the
// model stated the cap from the prompt's bare value and wrote its read date itself ("read 2026-09-23", where provenance
// gives the help centre's Restricted Trading Practices read 2026-09-21, the same page re-read on 24 and 26 September).
// Each rule now carries its document and every date troid read that document, from provenance; the ladder carries its
// steps as numbers, labelled, and the firm's own wording for what a step does where troid has recorded it.
const docKey = (u) => String(u || "").replace(/\.md$/, "").replace(/\/+$/, "");
function citeWithRereads(f, ids, section) {
  const S = (f.provenance || {}).sources || {}, own = ids.filter((i) => S[i]);
  if (!own.length) return { rule: "", source: "not yet recorded" };
  const first = [...new Set(own.map((i) => S[i].read_on).filter(Boolean))].sort(), urls = new Set(own.map((i) => docKey(S[i].url)));
  const again = [...new Set(Object.entries(S).filter(([i, x]) => !own.includes(i) && urls.has(docKey(x.url))).map(([, x]) => x.read_on)
    .filter((d) => d && !first.includes(d)))].sort();
  const last = first[first.length - 1], later = again.filter((d) => d > last), earlier = again.filter((d) => d < first[0]);
  const when = "read " + first.join(" and ") + (later.length || earlier.length ? " (the same page " + [earlier.length ? "read before on " + earlier.join(", ") : "",
    later.length ? "re-read " + later.join(" and ") : ""].filter(Boolean).join("; ") + ")" : "");
  return { document_section: section, read_on: first, reread_on: again, urls: [...new Set(own.map((i) => S[i].url))], when };
}
// A product's concentration ladder as firms.json records it (per product since 2026-10-05: 2-Step & 1-Step from 65%,
// Instant Funding from 55%, none recorded for Express or a Trader Stage), with the firm's word for what a step carries
function ladderFor(f, pk) {
  const L = f.concentration_penalty_ladder;
  if (!L || typeof L !== "object") return null;
  const steps = Array.isArray(L) ? L : L[pk];
  const wording = typeof f.concentration_penalty_wording === "string" ? f.concentration_penalty_wording : null;
  if (Array.isArray(steps)) return { steps, wording };
  return Array.isArray(L) ? null : { note: "no concentration ladder recorded for this product: the firm's page gives one for the 2-Step & 1-Step and one for Instant Funding" };
}
const HOLD_TIERS = { major: "Major Crypto Assets", minor: "Minor Crypto Assets", tradfi: "Traditional Trading Pairs" };
function firmLevelRules(out, a) {
  const F = JSON.parse(context().firms), f = F[String(a.firm)], P = f.provenance || {}, pk = String(a.product || "");
  const fieldIds = (k) => (((P.fields || {})[k] || {}).src || []), sec = (k, d) => (((P.fields || {})[k] || {}).section || d);
  const add = (rule, value, c) => {
    out.rules.push({ rule, value });
    out.sources.push(c.source ? { rule: rule + " " + value, source: c.source }
      : { rule: rule + " " + value, document_section: c.document_section, read_on: c.read_on, urls: c.urls,
          cite: rule + " " + value + " — " + c.document_section + ", " + c.when });
  };
  if (typeof f.max_open_positions === "number")
    add("open positions at once, at most", f.max_open_positions, citeWithRereads(f, fieldIds("max_open"), sec("max_open")));
  if (f.hold_cap_days && typeof f.hold_cap_days === "object") {
    const c = citeWithRereads(f, fieldIds("hold_cap"), sec("hold_cap"));
    for (const [k, d] of Object.entries(f.hold_cap_days)) if (typeof d === "number")
      add("hold limit, " + (HOLD_TIERS[k] || k) + ", days", d, c);
    out.hold_limit_note = "The hold limit follows the asset's tier, not the product: firm_assets gives each asset troid has recorded with its tier.";
  }
  const lad = ladderFor(f, pk);
  if (lad) {
    const c = citeWithRereads(f, fieldIds("concentration_ladder").length ? fieldIds("concentration_ladder") : ["rtp"],
      sec("concentration_ladder", "Bitfunded help centre — Restricted Trading Practices s.2"));
    out.concentration_ladder = lad.steps ? {
      steps: lad.steps.map(([from, pen], i, xs) => ({ exposure_from_pct: from, exposure_to_pct: i + 1 < xs.length ? xs[i + 1][0] - 1 : 100,
        firm_wording: lad.wording ? pen + "% " + lad.wording : "not yet recorded", payout_penalty_pct: pen })),
      reading: "Each step is an Exposure Level, the share of the account's margin in one trade or in highly correlated trades, and what the firm says it carries. " +
        "Give each step in the firm's own words (firm_wording, e.g. \"50% payout penalty\"), with its range; never call it a cut, and never say what the penalty is " +
        "a share of beyond those words.",
      source: c.source ? c.source : c.document_section + ", " + c.when }
      : { steps: [], note: lad.note, source: c.source ? c.source : c.document_section + ", " + c.when };
    out.sources.push(c.source ? { rule: "concentration ladder", source: c.source }
      : { rule: "concentration ladder", document_section: c.document_section, read_on: c.read_on, urls: c.urls,
          cite: "concentration ladder (" + (lad.steps ? lad.steps.map(([x, y], i, xs) => x + "–" + (i + 1 < xs.length ? xs[i + 1][0] - 1 : 100) + "% exposure: " + y + "% " + (lad.wording || "payout penalty")).join("; ") : lad.note) +
            ") — " + c.document_section + ", " + c.when });
  }
  return out;
}
// What a firm lets a trader pick, as troid has recorded it (firms.json _asset_universe: a symbol goes in only when a
// firm's own page names it, read with a date). The live test of 2026-10-04 ("can I trade BTC and a stock?") was told
// troid had no list of tickers: this gives each listed asset with the firm's own name for it, the hold limit of its tier
// and the document and date troid read it.
function firm_assets(a) {
  const F = JSON.parse(context().firms), fk = String(a.firm || "");
  if (!Object.hasOwn(F, fk) || fk.startsWith("_") || !F[fk].products) return { error: "unknown firm. troid covers: " + Object.keys(profiles()).join(", ") };
  const f = F[fk], U = F._asset_universe || {}, S = (f.provenance || {}).sources || {}, sym = String(a.symbol || "").toUpperCase().trim();
  const listed = [], sources = [];
  for (const g of U.groups || []) for (const x of g.symbols || []) {
    const l = (x.listed_by || {})[fk];
    if (!l) continue;
    const src = S[l.src], tier = Object.entries(HOLD_TIERS).find(([, n]) => String(l.as_listed).includes("(" + n + ")"));
    const days = tier && f.hold_cap_days ? f.hold_cap_days[tier[0]] : undefined;
    const row = { symbol: x.sym, group: g.group, as_listed: l.as_listed, tier: tier ? tier[1] : null,
      hold_limit_days: typeof days === "number" ? days : "not set on a page troid has read",
      source: src ? { document: src.doc, read_on: src.read_on, url: src.url } : "not yet recorded" };
    listed.push(row);
    if (sym && sym !== x.sym) continue;
    const rule = x.sym + " listed as " + l.as_listed + (typeof days === "number" ? ", hold limit " + days + " days" : "");
    sources.push(src ? { rule, document_section: src.doc + (tier ? " s.1 (maximum holding duration by asset type)" : ""), read_on: [src.read_on], urls: [src.url] }
      : { rule, source: "not yet recorded" });
  }
  const groups = {};
  for (const r of listed) (groups[r.group] = groups[r.group] || []).push(r.symbol);
  const out = { firm: f.name, listed, named_by_group: groups, sources,
    note: "These are the assets a page of " + f.name + "'s that troid has read names, with the firm's own name for each" +
      (groups.stocks ? "; of stocks, " + (groups.stocks.length === 1 ? "the one named is " : "those named are ") + groups.stocks.join(", ") : "; it names no stock") +
      ". An asset not listed here may still be on the firm's platform: troid has no record of it either way. Never say the firm doesn't offer it, and never that troid has no list.",
    tier: "SOURCED — each asset as the firm's own page names it, with the document and the date troid read it. The firm's own documents govern." };
  if (sym && !listed.some((r) => r.symbol === sym)) {
    out.asked = { symbol: sym, listed: false, detail: "No page of " + f.name + "'s that troid has read names " + sym + ". troid has no record that the firm offers it, and none that it doesn't." };
    if (sym in (U.not_listed || {})) out.asked.detail += " troid's desk shows it on the price tape as market context only, so the desk sizes nothing on it.";
  }
  return out;
}
// a firm's floating-loss rule, with its source or "not yet recorded", on a tool result that used the firm's limits
function withFloatingSource(out, a) {
  if (!out || out.error) return out;
  const F = JSON.parse(context().firms), f = Object.hasOwn(F, String(a.firm || "")) ? F[String(a.firm)] : null;
  if (!f || f.floating_counts !== true) return out;
  const rule = "floating losses count toward the daily and maximum loss (" + f.name + ")", c = cite(f, "floating_counts", String(a.product || ""), true);
  const on = c && c.read_on.length ? c.read_on : null;
  out.sources = (out.sources || []).concat(c ? [{ rule, document_section: c.section, read_on: on || "not recorded", urls: c.urls,
    cite: rule + " — " + c.section + ", " + (on ? "read " + on.join(" and ") : "read date not recorded") }]
    : [{ rule, source: "not yet recorded", cite: rule + " — source not yet recorded" }]);
  return out;
}
// trade_math's position_size on a firm's product keeps to that product's leverage cap
function tradeMathNext(a) {
  if (String(a.calc || "") === "position_size" && a.leverage != null && (a.firm != null || a.product != null) && String(a.firm) !== "all") {
    const g = profile(String(a.firm || ""), String(a.product || "")), lev = Number(a.leverage), bal = a.balance == null ? null : Number(a.balance);
    if (!g.error && Number.isFinite(lev)) {
      let cap = g.p.lev, key = "lev", size = "";
      if (g.p.levb) {
        const band = bal != null ? g.p.levb.find((x) => (x.max_quota == null || bal <= x.max_quota) && (x.min_quota == null || bal >= x.min_quota)) : null;
        if (band) { cap = band.lev; g.p._band_pv = band.pv; key = "lev_band"; size = " for a $" + bal.toLocaleString("en-US") + " account"; }
        else {
          cap = Math.min(...g.p.levb.map((x) => x.lev));
          if (lev > cap) return { error: g.f.name + " " + g.p.label + "'s leverage cap depends on the account size (" +
            g.p.levb.map((x) => "1:" + x.lev + (x.max_quota != null ? " up to $" + x.max_quota.toLocaleString("en-US") : " from $" + x.min_quota.toLocaleString("en-US"))).join(", ") +
            "): give balance, or work the example at 1:" + cap + " or below, or without a firm and product" };
        }
      }
      if (cap != null && lev > cap) {
        const src = sourcesFor(g.p, [[key, "leverage cap " + cap + "× (" + g.f.name + " " + g.p.label + size + ")"]]);
        return { error: g.f.name + " " + g.p.label + " caps leverage at 1:" + cap + size + ", so " + lev + "× is not available on it. Work the example at " +
          cap + "× or below on this product, or without a firm and product (with fee_per_side_pct).", sources: src };
      }
    }
  }
  // a stop as a percent of entry: its distance is the same for a long or a short, so no stop price is worked out by
  // hand (run 13, b-stop: "a stop 1.5% below entry … 76,705", where 1.5% below 77,872 is 76,703.92)
  // The calculator audit's F6: the exit fee is charged at the stop, so with a fee the side sets the stop's price and the
  // fee; without a fee the distance alone sizes it, the same for a long or a short. With a fee and no side it is worked
  // as a long, and says so among troid's assumptions.
  if (String(a.calc || "") === "position_size" && (a.stop == null || a.stop === "") && a.stop_pct != null) {
    const e = Number(a.entry), pct = Number(a.stop_pct);
    if (!(e > 0) || !(pct > 0 && pct < 100)) return { error: "position_size with stop_pct needs entry > 0 and 0 < stop_pct < 100" };
    const sd = a.side == null || a.side === "" ? null : String(a.side).toLowerCase().startsWith("l") ? 1 : String(a.side).toLowerCase().startsWith("s") ? -1 : 0;
    if (sd === 0) return { error: "side must be long or short" };
    const feed = a.fee_per_side_pct != null || a.firm != null || a.product != null, assumeLong = sd == null && feed;
    const g = sd == null ? 1 : sd, stop = e * (1 - g * pct / 100);
    const out = trade_math(Object.assign({}, a, { stop }), MATH_NEXT, MATH_FORMULAS_NEXT);
    if (out.error) return out;
    out.working = [{ step: "stop distance from the percent given", formula: `${e} × ${pct}%`, value: rd(e * pct / 100) }]
      .concat(sd == null && !feed ? [] : [{ step: "stop", formula: `entry × (1 ${g > 0 ? "−" : "+"} ${pct}%)`, value: rd(stop) }], out.working.slice(1));
    out.note = ((out.note || "") + (!feed ? " The stop is a percent of entry and no fee is counted: the size is the same for a long or a short."
      : " The stop is a percent of entry, " + (g > 0 ? "below it on a long" : "above it on this short") + "." +
        (assumeLong ? " No side was given, so this is worked as a long; a short's stop is above entry and its exit fee a little higher, so its quantity is a little smaller." : ""))).trim();
    if (assumeLong) out.assumptions = ["side long — troid's default, not an input you gave; give side for a short, whose exit fee at the stop is a little higher"];
    return out;
  }
  // Kelly beside a firm's limits: every fraction against every limit, each ratio labelled with both (run 15, ex-kelly:
  // "half-Kelly (8.75%) is 1.46× it, and 4.38× the daily limit", where 4.38× is full Kelly's; half Kelly's is 2.19×)
  if (String(a.calc || "") === "kelly") {
    const out = trade_math(a, MATH_NEXT, MATH_FORMULAS_NEXT), r = out.result || {};
    if (!out.error && r.daily_pct > 0 && r.half_kelly_pct != null) {
      const at = out.working.findIndex((w) => w.step === "full Kelly ÷ daily limit");
      out.working.splice(at + 1, 0, { step: "half Kelly ÷ daily limit", formula: `${r.half_kelly_pct}% ÷ ${r.daily_pct}%`, value: rd(r.half_kelly_pct / r.daily_pct, 2) + "×" });
      Object.assign(r, { full_kelly_vs_daily: rd(r.kelly_pct / r.daily_pct, 2), half_kelly_vs_daily: rd(r.half_kelly_pct / r.daily_pct, 2) });
    }
    return out;
  }
  return trade_math(a, MATH_NEXT, MATH_FORMULAS_NEXT);
}
// check_compliance for the candidate: the concentration finding from the product's own ladder in firms.json (Express has
// none recorded; the live check applies the 2-Step & 1-Step ladder to it), in the firm's words
function checkComplianceNext(a) {
  const out = check_compliance(a);
  if (out.pending || out.error) return out;
  const F = JSON.parse(context().firms), f = F.bitfunded, pk = a.product || "1step", lad = ladderFor(f, pk), mp = +a.margin_pct_of_capital || 0;
  out.findings = (out.findings || []).filter((x) => x.rule !== "RTP s.2");
  const c = citeWithRereads(f, ((((f.provenance || {}).fields || {}).concentration_ladder) || {}).src || ["rtp"], "Bitfunded help centre — Restricted Trading Practices, Excessive Risk Concentration ('All In' Trading)");
  const src = c.source ? [{ source: c.source }] : [{ document: c.document_section, read_on: c.read_on.join(" and "), url: c.urls[0] }];
  if (lad && lad.steps) {
    const at = [...lad.steps].reverse().find(([thr]) => mp >= thr);
    if (at) out.findings.push({ severity: "penalty", rule: "RTP, Excessive Risk Concentration", sources: src,
      detail: `Margin at ${mp.toFixed(0)}% of the account in one trade or correlated trades sits at an Exposure Level the firm gives as "${at[1]}% ${lad.wording || "payout penalty"}". This product's ladder starts at ${lad.steps[0][0]}%.` });
  } else if (lad && mp > 0) out.findings.push({ severity: "info", rule: "RTP, Excessive Risk Concentration", sources: src, detail: lad.note.charAt(0).toUpperCase() + lad.note.slice(1) + ". troid can't check this trade's concentration against a ladder." });
  return out;
}
// What an amount buys (the owner, 2026-10-06, after runs 25 to 27, s-firm): every product troid has a price for at or
// under it, cheapest first, each with its price, its account size and the document and date troid read the price, or that
// its source is not yet recorded. A price in another currency comes apart, never converted (run 1 converted €100 from
// memory). The lines are the reply's; the closing line is fixed: troid picks none of them.
const PRICE_KEYS = [["fee_usd", "USD", 100000], ["fee_usd_5k", "USD", 5000], ["fee_usd_10k", "USD", 10000], ["fee_usd_100k", "USD", 100000],
  ["fee_eur_100k", "EUR", 100000]];
const PRODUCT_LABELS = { "3phase": "3-Phase", ascend: "Ascend", break: "Break" };
const BUDGET_SIZES_NOTE = "troid has each product's price at the account size shown only, and none for its other sizes.";
const moneyOf = (v, cur) => (cur === "EUR" ? "€" : "$") + Number(v).toLocaleString("en-US", { minimumFractionDigits: Number.isInteger(+v) ? 0 : 2, maximumFractionDigits: 2 });
function pricedProducts() {
  const F = JSON.parse(context().firms), out = [];
  for (const [fk, f] of Object.entries(F)) {
    if (fk.startsWith("_") || !f || typeof f !== "object" || !f.products) continue;
    const labels = (f.calc && f.calc.products) || {};
    for (const [pk, p] of Object.entries(f.products)) {
      if (pk.startsWith("_") || !p || typeof p !== "object") continue;
      for (const [key, currency, size] of PRICE_KEYS) {
        if (typeof p[key] !== "number") continue;
        const c = cite(f, "price", pk, true);
        out.push({ firm: f.name, product: pk, label: (PRODUCT_LABELS[pk] || (labels[pk] && labels[pk].label) || pk).replace(/\s*·\s*S\d+$/, ""),
          price: p[key], currency, account_size: size,
          promo_price: typeof p[key + "_promo"] === "number" ? p[key + "_promo"] : null,
          activation_fee: typeof p["activation_" + key] === "number" ? p["activation_" + key] : null,
          source: c ? { document_section: c.section, read_on: c.read_on, urls: c.urls } : "not yet recorded" });
      }
    }
  }
  return out;
}
const priceTerms = (r) => moneyOf(r.price, r.currency) + " at a " + moneyOf(r.account_size, "USD") + " account" +
  (r.promo_price != null ? ", or " + moneyOf(r.promo_price, r.currency) + " on the promotion running when troid read it" : "") +
  (r.activation_fee != null ? ", and a " + moneyOf(r.activation_fee, r.currency) + " activation fee whose timing troid hasn't recorded" : "");
const priceSource = (r) => (r.source === "not yet recorded" ? "source not yet recorded"
  : r.source.document_section + ", " + (r.source.read_on.length ? "read " + r.source.read_on.join(" and ") : "read date not recorded"));
const budgetLine = (r) => r.firm + " " + r.label + ": " + priceTerms(r) + " (" + priceSource(r) + ")";
function products_in_budget(a) {
  const budget = Number(a.budget), currency = /^\s*(eur|euros?|€)\s*$/i.test(String(a.currency || "")) ? "EUR" : "USD";
  if (!(budget > 0) || !Number.isFinite(budget)) return { error: "budget must be a positive amount, e.g. 500" };
  const all = pricedProducts();
  const within = all.filter((r) => r.currency === currency && r.price <= budget).sort((x, y) => x.price - y.price || x.firm.localeCompare(y.firm));
  const other = all.filter((r) => r.currency !== currency);
  return { budget, currency,
    products: within.map((r) => ({ firm: r.firm, product: r.label, price: r.price, currency: r.currency, account_size: r.account_size,
      ...(r.promo_price != null ? { promo_price: r.promo_price } : {}), ...(r.activation_fee != null ? { activation_fee: r.activation_fee } : {}),
      source: priceSource(r) })),
    lines: within.map(budgetLine),
    note: BUDGET_SIZES_NOTE + (other.length ? " Priced in " + (currency === "USD" ? "euros" : "dollars") + ", which troid doesn't convert: " +
      other.map(budgetLine).join("; ") + "." : ""),
    close: BUDGET_CLOSE,
    sources: [...within, ...other].map((r) => { const rule = r.firm + " " + r.label + ", challenge fee " + priceTerms(r);
      return r.source === "not yet recorded" ? { rule, source: "not yet recorded" } : Object.assign({ rule }, r.source); }),
    tier: "SOURCED — each price as troid has recorded it, with the document and the date troid read it; a price with no recorded source says so. troid picks none of them." };
}
// the reply the backstop gives (and the one the guardrail asks for): support.md section 4's line, the list, its note, the line
const budgetText = (out) => (out.lines.length
  ? "Every product troid has a price for at or under " + moneyOf(out.budget, out.currency) + ", cheapest first:\n" + out.lines.map((l) => "- " + l).join("\n")
  : "troid has a price for no product at or under " + moneyOf(out.budget, out.currency) + ".") + "\n\n" + out.note + "\n\n" + BUDGET_CLOSE;
// Promoted 2026-10-08: the tool implementations the candidate ran with are every visitor's now; RUN is only their base.
const LIVE_RULES = Object.assign({}, RULES, PROMOTED_RULES), LIVE_TOPIC_CITES = Object.assign({}, TOPIC_CITES, PROMOTED_TOPIC_CITES);
const PROMOTED_RUN = {
  explain_rule: (a) => explainRuleSourced(a, LIVE_RULES, LIVE_TOPIC_CITES),
  firm_rules: firmRulesNext,
  firm_assets,
  products_in_budget,
  check_compliance: checkComplianceNext,
  check_budget: (a) => withFloatingSource(check_budget(a), a),
  size_trade: (a) => withFloatingSource(size_trade(a, true), a),   // the calculator audit's F5, F6 and F7
  trade_math: tradeMathNext,
};
const RUN_LIVE = Object.assign({}, RUN, PROMOTED_RUN);
// a new candidate's tool implementations and rule explanations, until it is promoted (none staged since 2026-10-08)
const CANDIDATE_RUN = {}, CANDIDATE_RULES = {};
const RUN_CANDIDATE = Object.assign({}, RUN_LIVE, CANDIDATE_RUN, Object.keys(CANDIDATE_RULES).length
  ? { explain_rule: (a) => explainRuleSourced(a, Object.assign({}, LIVE_RULES, CANDIDATE_RULES), LIVE_TOPIC_CITES) } : {});
const RUN_PATCH = Object.assign({}, RUN_LIVE, { explain_rule: (a) => explainRuleSourced(a, Object.assign({}, LIVE_RULES, PATCH_RULES), LIVE_TOPIC_CITES) });
function runTool(name, input, variant) {
  const run = variant === "candidate" ? RUN_CANDIDATE : variant === "patch" ? RUN_PATCH : RUN_LIVE;
  try { return Object.hasOwn(run, name) ? run[name](input || {}) : { error: "unknown tool " + name }; }
  catch (e) { return { error: "tool failed: " + (e && e.message ? e.message : "unknown") }; }
}

// ---------------------------------------------------------------- limits (in memory, per instance, best effort)
const HITS = new Map(), CALLS = [], MAX_KEYS = 5000;
// One key per IPv4 address, one per IPv6 /64 (one host usually holds a whole /64). Vercel's edge sets
// x-real-ip and overwrites x-forwarded-for, so neither can be spoofed from outside.
function clientKey(req) {
  const ip = String(req.headers["x-real-ip"] || req.headers["x-forwarded-for"] || (req.socket && req.socket.remoteAddress) || "?").split(",")[0].trim();
  if (!ip.includes(":") || ip.includes(".")) return ip.replace(/^::ffff:/i, "");
  const [h, t = ""] = ip.split("%")[0].split("::"), a = h ? h.split(":") : [], b = t ? t.split(":") : [];
  return [...a, ...Array(Math.max(0, 8 - a.length - b.length)).fill("0"), ...b].slice(0, 4).join(":").toLowerCase() + "::/64";
}
// The Map is kept in least-recently-seen order. A full table evicts idle keys, then keys under the limit,
// then the oldest — it never turns a new visitor away because other addresses filled it.
function allow(key) {
  const now = Date.now(), keep = (HITS.get(key) || []).filter((t) => now - t < 3600e3);
  HITS.delete(key);
  if (keep.length >= LIMIT_PER_HOUR) { HITS.set(key, keep); return false; }
  keep.push(now); HITS.set(key, keep);
  if (HITS.size > MAX_KEYS) {
    for (const [k, v] of HITS) { if (HITS.size <= MAX_KEYS) break; if (k !== key && (now - v[v.length - 1] >= 3600e3 || v.length < LIMIT_PER_HOUR)) HITS.delete(k); }
    for (const k of HITS.keys()) { if (HITS.size <= MAX_KEYS) break; if (k !== key) HITS.delete(k); }
  }
  return true;
}
// A visitor's messages today, by the same address key, in memory. A full table drops other days' entries, then those
// under the cap, then the oldest; a visitor at the cap today is dropped last.
const DAY = new Map();
const utcDay = () => new Date().toISOString().slice(0, 10);
function visitorLeft(key) {
  const d = DAY.get(key);
  return !d || d[0] !== utcDay() || d[1] < VISITOR_TURNS;
}
function visitorUsed(key) {
  const day = utcDay(), d = DAY.get(key);
  DAY.delete(key); DAY.set(key, [day, d && d[0] === day ? d[1] + 1 : 1]);
  for (const pass of [(v) => v[0] !== day, (v) => v[1] < VISITOR_TURNS, () => true])
    for (const [k, v] of DAY) { if (DAY.size <= MAX_KEYS) return; if (k !== key && pass(v)) DAY.delete(k); }
}
// Days from today (UTC) to a recorded expiry date, or null where none is recorded or it doesn't read as a date.
function daysLeft(when) {
  const t = Date.parse(when);
  return when && Number.isFinite(t) ? Math.floor((t - Date.parse(utcDay())) / 86400e3) : null;
}
function keyReport() {
  const main = daysLeft(KEY_EXPIRES), ev = daysLeft(EVAL_KEY_EXPIRES), warnings = [];
  for (const [name, d, set] of [["production API key", main, KEY], ["evaluation API key", ev, EVAL_KEY]]) {
    if (!set) continue;
    if (d == null) warnings.push(`no expiry date recorded for the ${name}`);
    else if (d < 0) warnings.push(`the ${name} expired ${-d} day${d === -1 ? "" : "s"} ago`);
    else if (d <= WARN_DAYS) warnings.push(`the ${name} expires in ${d} day${d === 1 ? "" : "s"}: rotate it`);
  }
  return { key_days_left: { main, eval: ev }, key_warnings: warnings };
}
function spendable() {                                        // the instance's ceiling on model calls an hour
  const now = Date.now();
  while (CALLS.length && now - CALLS[0] >= 3600e3) CALLS.shift();
  return CALLS.length < CALLS_PER_HOUR;
}
function spend() {
  if (!spendable()) { const e = new Error("instance call ceiling"); e.busy = true; throw e; }
  CALLS.push(Date.now());
}

// ---------------------------------------------------------------- the call
const CLIENTS = {};
function client(operator) {
  // logLevel pinned: ANTHROPIC_LOG=debug would otherwise write request bodies (the user's text) to the log.
  // Timeouts and retries are set per call from the message's deadline, below.
  const apiKey = operator && EVAL_KEY ? EVAL_KEY : KEY, k = apiKey === KEY ? "main" : "eval";
  if (!CLIENTS[k]) CLIENTS[k] = new Anthropic({ apiKey, baseURL: BASE_URL, logLevel: "warn" });
  return CLIENTS[k];
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
// Every call gets only the time left before the message's deadline; the abort signal is the hard wall.
// The SDK does not retry (it would honour any retry-after, however long). One retry happens here, after a
// fast failure only (rate limit, overload, connection), and only if the wait and a call still fit.
async function callModel(route, messages, deadlineAt, onSend, lang, variant, operator) {
  const R = ROUTE[route];
  for (let attempt = 0; ; attempt++) {
    const left = deadlineAt - Date.now();
    if (left < MIN_CALL_MS) { const e = new Error("deadline"); e.deadline = true; throw e; }
    spend();
    const params = { model: R.model, max_tokens: R.max_tokens, cache_control: { type: "ephemeral" },   // + the tail of the conversation
                     system: systemBlocks(lang, variant), tools: toolsFor(variant), messages };
    if (route === "tools" && TOOLS_EFFORT !== "none") params.output_config = { effort: TOOLS_EFFORT };
    onSend(R.model);
    try {
      const out = await client(operator).messages.create(params, { timeout: left, maxRetries: 0, signal: AbortSignal.timeout(left) });
      onSend(R.model, out.usage);                                     // the tokens it took, for the log and the operator's report
      return out;
    } catch (e) {
      const fast = e instanceof Anthropic.RateLimitError || e instanceof Anthropic.InternalServerError
        || (e instanceof Anthropic.APIConnectionError && !(e instanceof Anthropic.APIConnectionTimeoutError));
      if (!fast || attempt > 0) throw e;
      const h = e.headers && typeof e.headers.get === "function" ? e.headers : null;
      const ms = h && num(h.get("retry-after-ms"), NaN), sec = h && num(h.get("retry-after"), NaN);
      const wait = Number.isFinite(ms) ? ms : Number.isFinite(sec) ? sec * 1000 : 500;
      if (wait > MAX_RETRY_WAIT_MS || Date.now() + wait + MIN_CALL_MS >= deadlineAt) throw e;   // busy: say so now
      await sleep(wait);
    }
  }
}
// Under an answer that used a tool, the service writes the sources (one line per rule, each with its own read
// dates), the tier and troid's assumptions, from the tool results, so the model cannot merge or misdate them. A
// sources or rule-basis paragraph the model wrote anyway is removed first. The block goes before the closing
// "Not financial advice" line when the answer ends with it.
function citeOf(s, rule) {
  if (s.cite) return s.cite;
  if (s.source === "not yet recorded") return (rule ? rule + " — " : "") + "source not yet recorded";
  const on = [].concat(s.read_on || []).filter((x) => x && x !== "not recorded");
  return (rule ? rule + " — " : "") + (s.document_section || s.document) + ", " + (on.length ? "read " + on.join(" and ") : "read date not recorded");
}
function stripSources(text) {
  const lines = String(text).split("\n"), out = [];
  for (let i = 0; i < lines.length; i++) {
    if (/^\s*(\*\*|__)?\s*(sources?|rule basis|rules? sourced)\b/i.test(lines[i])) {
      while (i + 1 < lines.length && /^\s*([-*•]|\d+\.)\s+/.test(lines[i + 1])) i++;
      continue;
    }
    out.push(lines[i]);
  }
  return out.join("\n").replace(/\n{3,}/g, "\n\n").trim();
}
// candidate (staged 2026-10-08, the owner: the promoted live s-firm wrote "the rules above are SOURCED" under five prices
// marked "source not yet recorded"): a tier line never calls an unsourced rule SOURCED. With some sources unrecorded the
// line names which rules are SOURCED; with none recorded it says so. English only until the strings are reviewed.
const CANDIDATE_TIER_PART = "Tier: the rules above with a document and read date are SOURCED; a rule marked \"source not yet recorded\" is not.";
const CANDIDATE_TIER_NONE = "Tier: troid has no recorded source for the rules above, and each says so; the firm's own documents govern.";
const CANDIDATE_TIER_QUOTED_PART = "Tier: the figures above are DERIVED — troid's tools computed them from the numbers given; each firm rule quoted beside them with a read date is SOURCED, and one marked \"source not yet recorded\" is not.";
const UNRECORDED_RX = /\bsource not yet recorded\b/;
function tierLine(k, quoted, lang, cites, variant) {
  const line = S(lang, "ask.tier." + (quoted ? "inputs_quoted" : k));
  if (variant !== "candidate" || lang !== "en" || !cites.some((c) => UNRECORDED_RX.test(c))) return line;
  if (quoted) return CANDIDATE_TIER_QUOTED_PART;
  if (k !== "sourced") return line;
  return cites.every((c) => UNRECORDED_RX.test(c)) ? CANDIDATE_TIER_NONE : CANDIDATE_TIER_PART;
}
function withSources(reply, lang, toolLog, variant) {
  const cites = [], tiers = new Set(), assumed = [];
  for (const t of toolLog) {
    const r = t.result || {};
    for (const s of r.sources || []) cites.push(citeOf(s, s.rule));
    for (const f of r.findings || []) for (const s of f.sources || []) cites.push(citeOf(s, f.rule));
    if (t.name === "trade_math") tiers.add((r.sources || []).length ? "derived" : "inputs");
    else if (/^DERIVED/.test(r.tier || "")) tiers.add("derived");
    if (/^SOURCED/.test(r.tier || "") || (t.name === "check_availability" && r.sources)) tiers.add("sourced");
    for (const a of r.assumptions || []) assumed.push(a);
  }
  const uniq = (xs) => [...new Set(xs)];
  // one DERIVED line, not two, when trade_math ran both with a firm's rule and without one (run 12, o-montecarlo); the
  // candidate's, until it is promoted
  if (tiers.has("derived")) tiers.delete("inputs");
  // troid's published Monte Carlo, quoted from explain_rule's ruin topic, is MODELLED, not DERIVED; one line says both
  // (subset run 1, o-montecarlo: its simulated years were printed under "the figures above are DERIVED")
  if (MC_QUOTED_RX.test(reply) && toolLog.some((t) => t.name === "explain_rule" && (t.result || {}).topic === "ruin")) {
    tiers.delete("derived"); tiers.delete("inputs"); tiers.add("modelled");
  }
  if (!cites.length && !tiers.size && !assumed.length) return reply;
  const block = [];
  if (cites.length) block.push(S(lang, "ask.sources") + "\n" + uniq(cites).map((c) => "- " + c).join("\n"));
  // a reply that quotes a firm's rule with its read date itself is not told "no firm rule was needed" (run 5, ex-kelly)
  const quoted = READ_DATE_RX.test(stripSources(reply));
  for (const k of ["modelled", "derived", "inputs", "sourced"]) if (tiers.has(k)) block.push(tierLine(k, k === "inputs" && quoted, lang, cites, variant));
  if (assumed.length) block.push(S(lang, "ask.assumed", { list: uniq(assumed).join("; ") }));
  let body = stripSources(reply);
  // the service lists troid's assumptions, so the reply's own list of them goes (subset run 1, p-size: listed twice, the
  // reply's copy saying the budget cap and the target "affect margin and liquidation distance")
  if (assumed.length) body = body.split(/\n\s*\n/).filter((p) => !ASSUMED_PARA_RX.test(p)).join("\n\n");
  // a tier line the model wrote anyway goes when the service writes the tier (run 1: two tier lines)
  // and so does one written at the end of a paragraph, when it names a tier the service writes (run 4, q-stats)
  if (tiers.size) {
    const words = new Set([...tiers].flatMap((k) => (k === "sourced" ? ["SOURCED"] : k === "modelled" ? ["MODELLED", "DERIVED"] : ["DERIVED"])));
    body = body.split("\n").filter((l) => !/^\s*(\*\*|__)?\s*tier\b/i.test(l))
      .map((l) => l.replace(/\s*(\*\*|__)?\bTier(\*\*|__)?:\s*(\*\*|__)?(DERIVED|SOURCED|MEASURED|MODELLED)\b[^\n]*$/i, (m, a, b, c, w) => (words.has(w.toUpperCase()) ? "" : m)))
      .join("\n").replace(/\n{3,}/g, "\n\n").trim();
  }
  const note = S(lang, "ask.note"), at = body.lastIndexOf(note);
  const tail = at >= 0 && body.slice(at + note.length).trim() === "" ? note : "";
  if (tail) body = body.slice(0, at).trim();
  return [body, block.join("\n\n"), tail].filter(Boolean).join("\n\n");
}
// An answer that states a figure ends with the note even when the model left it out or wrote
// something after it (run 1: five answers didn't end with it). An answer with no figure is left as it is.
// A reply that opens support.md section 2 ("That's a real loss and troid takes the question
// seriously") and leaves out step 5 gets it from the service: the firm's dashboard and hello@troid.ai (run 4, ex-angry).
const SUPPORT_OPENER = /That['’]s a real loss,? and troid takes the question seriously/i;
const READ_DATE_RX = /\bread (on )?(\d{4}[-\u2010\u2011]\d{2}[-\u2010\u2011]\d{2}|\d{1,2} [A-Z][a-z]{2,8} \d{4}|[A-Z][a-z]{2,8} \d{1,2},? \d{4})/;
// An outside service named as a place to look (the guardrails name none).
const OUTSIDE_SERVICE = /\b(CoinDesk|Cointelegraph|The Block|Glassnode|Nansen|Kraken|Coinbase|Bloomberg|Reuters|CoinMarketCap|CoinGecko|TradingView|Messari|numpy)\b|\b(check|use|visit|see|try)\b[^.\n]{0,60}\bBinance\b/i;
// A firm's rule stated in a reply: a firm named beside a percentage, a time, a number of days or a fee.
const FIRM_RULE_RX = /\b(Bitfunded|BrightFunded|Crypto Fund Trader)\b[^.\n]{0,80}?(\d+(\.\d+)?\s?%|\b\d{1,2}:\d{2}\b|\b\d+\s?(trading )?days?\b|\$\d)|(\d+(\.\d+)?\s?%|\b\d{1,2}:\d{2}\b|\b\d+\s?(trading )?days?\b)[^.\n]{0,60}?\b(Bitfunded|BrightFunded|Crypto Fund Trader)\b/;
const RULE_NUDGE = "(A note from the service, not the user: the answer above states a firm's rule with no tool behind it. Get each rule through firm_rules or " +
  "explain_rule, so it carries the source and read date troid recorded for it, or says its source is not yet recorded; then write the whole answer again.)";
// A draft the service sends back once to be written again, with a note for each pattern it finds (run 8: "troid is willing
// to lose", "support.md section 4 applies here", "Result first, one line", troid's in-sample figure before its
// out-of-sample one and the +0.008R without its tier).
const AGENCY_RX = /\btroid (is willing to|wants to|will|would|is going to|plans to|can afford to) (put|risk|open|place|enter)\b[^.\n]{0,30}\b(on|into|in) (the |a |this )?(trade|position|market)\b|\btroid (is willing to|wants to|is going to|plans to) (take|risk|lose)\b/i;
const INTERNAL_RX = /\bsupport\.md\b|\bTROID-CHARACTER\b|\bcharacter section\b|\bfixed (answer|reply|refusal)\b|\b(result|answer) first,? (in )?one line\b|\bin one line:/i;
const OOS_LATE_RX = /^(?:(?!0\.008\s?R)[\s\S])*\btroid['’]s own\b[^.\n]{0,60}\b(in[- ]sample|search|best of)/i;
const LINTS = [
  [(t) => AGENCY_RX.test(t), "troid never trades: the risk, the position, the stop and the trade are the trader's, and troid prices them."],
  [(t) => INTERNAL_RX.test(t), "Name none of troid's own instructions (support.md, its sections, the character) and don't announce the reply's form (a fixed answer, \"result first, one line\"): give the reply itself."],
  [(t) => OOS_LATE_RX.test(t) || (/\b0\.008\s?R/.test(t) && !/\bMEASURED\b/.test(t)),
   "troid's own strategy: its out-of-sample result comes first, +0.008R per trade on BTC (504 trades) and on ETH (498), both confidence intervals containing zero, each figure marked MEASURED; the in-sample figure only after it."],
];
const lintNotes = (t) => LINTS.filter(([test]) => test(t)).map(([, note]) => note);
// The lints promoted on 2026-10-08, every reply's after LINTS: (text, the turn's tool calls) → a note. Staged after run 10:
// o-montecarlo quoted troid's Monte Carlo from memory (its 68%, at 1% a trade, beside 2%); s-product called every rule
// of its table sourced ("all SOURCED with their read dates") where the split and the 2-Step's trading fee had none.
const ALL_SOURCED_RX = /\ball (of them |the rules |rules )?(are |is )?(SOURCED|sourced|dated)\b|\b(all|every) (rules?|figures?)\b[^.\n]{0,40}\b(with|carr(y|ies)) (its|their) (sources?|read dates?)\b|\ball\b[^.\n]{0,20}\bwith their read dates\b/;
const MC_68_RX = /\b68\s?%[^.\n]{0,80}\b(simulat|years?\b|blow|ruin|fail)|\b(simulat|Monte Carlo|blow|ruin)[^.\n]{0,90}\b68\s?%/i;   // the Monte Carlo's figure, not a win rate
const MC_QUOTED_RX = new RegExp(MC_68_RX.source + "|\\bsimulated years?\\b", "i");                // a reply that quotes it
// a paragraph listing troid's own defaults, which the service lists under the answer (ask.assumed)
const ASSUMED_PARA_RX = /^\s*(?:\*\*|__)?\s*(?:assumptions|troid['’]s (?:assumptions|defaults)|defaults)\b[^\n]{0,60}\b(?:troid|not given|supplied|defaults?|assumed)\b/i;
const PROMOTED_LINTS = [
  [(t, tools) => MC_68_RX.test(t) && !tools.some((x) => x.name === "explain_rule" && String((x.input || {}).topic || "").toLowerCase().trim() === "ruin"),
   "troid's published Monte Carlo comes from explain_rule, topic ruin: get it there, then quote each figure with the risk a trade it belongs to, its assumptions and its tier, MODELLED."],
  [(t, tools) => ALL_SOURCED_RX.test(t) && tools.some((x) => JSON.stringify(x.result || {}).includes("not yet recorded")),
   "Some rules the tools gave have no recorded source: say so beside each of them (source not yet recorded), and never that every rule is sourced."],
];
// Staged after evaluation run 11: ex-r stated "Bitfunded's 4% daily limit" beside a tool that gave only the fee; s-firm
// marked the Instant's 3% and 6%, which the tool gave with read dates, "source not yet recorded"; e-blown called Crypto
// Fund Trader a trailing-drawdown firm (its 2-Phase is static); o-montecarlo wrote "Answer, one line:"; b-limits stated
// the floating-loss rule beside explain_rule topics that did not carry it.
const LINT_FIRM = /\b(Bitfunded|BrightFunded|Crypto Fund Trader|CFT)\b/;
const LINT_WORD = "(daily|max(?:imum)?|loss|limit|target|drawdown|fee|split|floor)";
const PCT_AFTER = new RegExp(`(?<![\\d.,])(\\d+(?:\\.\\d+)?)\\s?%\\s?(?:[\\w'’()-]+\\s){0,3}?${LINT_WORD}`, "gi");
const PCT_BEFORE = new RegExp(`${LINT_WORD}\\b((?:(?!share|÷|×|=|≈)[^.\\n%$,]){0,25}?)(?<![\\d.,])(\\d+(?:\\.\\d+)?)\\s?%`, "gi");
// "4% of the $100,000 quota" (run 14, ex-r: the rule in brackets after its dollar amount)
const PCT_OF = /(?<![\d.,])(\d+(?:\.\d+)?)\s?%\s+of\s+(?:the\s+|its\s+|an?\s+)?(?:[$€]\s?[\d,]+(?:\.\d+)?\s+)?(?:account['’]s\s+|account\s+)?(quota|initial balance|starting balance|opening balance)\b/gi;
// a firm's rule as a percentage, in a sentence naming the firm; not a percentage the user gave
function firmRulePcts(text, asked) {
  const given = new Set([...String(asked || "").matchAll(/(\d+(?:\.\d+)?)\s?%/g)].map((m) => m[1])), out = [];
  for (const sent of String(text).split(/(?<=[.!?])\s+|\n+/)) {
    if (!LINT_FIRM.test(sent)) continue;
    for (const m of sent.matchAll(PCT_AFTER)) if (!given.has(m[1])) out.push({ n: m[1], s: m[0] });
    for (const m of sent.matchAll(PCT_BEFORE)) if (!given.has(m[3])) out.push({ n: m[3], s: m[0] });
    for (const m of sent.matchAll(PCT_OF)) if (!given.has(m[1])) out.push({ n: m[1], s: m[0] });
  }
  return out;
}
const pctIn = (src, n) => { const e = n.replace(".", "\\."); return new RegExp(`(?<![\\d.])${e}(?![\\d])\\s?%|%\\s?${e}(?![\\d.])`).test(src); };
// every source the turn's tools gave, one line each: "rule — read …" or "rule — source not yet recorded"
function toolSourceLines(tools) {
  const out = [];
  for (const t of tools || []) {
    const r = t.result || {};
    for (const x of [...(r.sources || []), ...(r.findings || []).flatMap((f) => f.sources || [])])
      out.push(String(x.rule || "") + " — " + (x.source === "not yet recorded" ? "source not yet recorded" : "read " + [].concat(x.read_on || []).join(" and ")));
  }
  return out;
}
const LINT_NUM = /(?<![\w.])(?:[$€]\s?(\d[\d,]*(?:\.\d+)?)(?![\d,]*-?\s?(?:tier|account))|(\d+(?:\.\d+)?)\s?%)/g;
// a rule the reply calls unrecorded where every source the tools gave for its figure has a read date
function misreportedSources(text, srcLines) {
  const out = [];
  for (const line of String(text).split("\n")) {
    const at = line.search(/not yet recorded|no recorded source/i);
    if (at < 0) continue;
    const head = line.slice(0, at), cut = Math.max(...[...head.matchAll(/[.!?;]\s/g)].map((x) => x.index + 1), 0);
    for (const m of head.slice(cut).matchAll(LINT_NUM)) {
      const n = (m[1] || m[2]).replace(/,/g, ""), rx = new RegExp(`(?<![\\d.,])${n.replace(".", "\\.")}(?![\\d]|[.,]\\d)`);
      const hits = srcLines.filter((l) => rx.test(l.split(" — ")[0].replace(/(\d),(\d{3})/g, "$1$2")));
      if (hits.length && hits.every((l) => !/not (yet )?recorded|read $/.test(l))) out.push(line.trim());
    }
  }
  return out;
}
const FORM_RX = /\b(answer|result),? (first,? )?(in )?one line\b|\b(result|answer)s? first\b|\bone[- ]line answer\b|\b(getting|fetching|pulling|computing|running) (those|that|them|it|the numbers) now\b/i;   // runs 8, 11, 13; run 15: "Getting those now:"
const PH1_RX = "(1-Phase|1 Phase|one-phase|1phase)";
const CFT_TRAIL_RX = new RegExp(`(?<!${PH1_RX}\\b[^.\\n]{0,40})(Crypto Fund Trader|\\bCFT)\\b(?![^.\\n]{0,80}\\b${PH1_RX}\\b)[^.\\n]{0,60}\\btrail` +
  `|(?<!${PH1_RX}\\b[^.\\n]{0,40})\\btrail[^.\\n]{0,40}\\b(Crypto Fund Trader|CFT)\\b(?![^.\\n]{0,30}\\b${PH1_RX}\\b)`, "i");
const FLOAT_FIRM_RX = /\b(Bitfunded|BrightFunded|Crypto Fund Trader)\b[^.\n]{0,120}\bfloat|\bfloat[^.\n]{0,120}\b(Bitfunded|BrightFunded|Crypto Fund Trader)\b/i;
PROMOTED_LINTS.push(
  [(t, tools, asked) => { const src = toolSourceLines(tools).join("\n"); return firmRulePcts(t, asked).some((x) => !pctIn(src, x.n)); },
   "Every firm rule in the answer comes through a tool, so the service lists its source and read date: get each one through firm_rules, explain_rule, check_budget or size_trade, or leave it out."],
  [(t, tools) => misreportedSources(t, toolSourceLines(tools)).length > 0,
   "A rule is called unrecorded that a tool gave with its source and read date: say about each rule's source only what the tools say."],
  [(t) => CFT_TRAIL_RX.test(t),
   "Crypto Fund Trader's drawdown differs by product: its 1-Phase trails, then locks at the opening balance; its 2-Phase is static. Name the product with it."],
  [(t) => FORM_RX.test(t),
   "Don't announce the reply's form (\"answer, one line\", \"result first\", \"one-line answer\"): give the answer itself."],
  [(t, tools) => FLOAT_FIRM_RX.test(t) && !toolSourceLines(tools).some((l) => /floating/i.test(l)),
   "A firm's floating-loss rule is a firm rule: get it through firm_rules, which gives its source, or leave it out."]);
// Staged after evaluation run 12: o-predict said "the firm's own platform and financial data services are the record" for
// prices, news and forecasts; b-limits wrote the daily floor as "day_start_equity − remaining_daily_budget" (it is the day's
// start less the fixed daily amount); s-firm opened a rewrite with "Retracting the earlier version of this answer".
const FIRM_RECORD_RX = /\bfirm['’]s (own )?(dashboard|platform)\b[^.\n]{0,100}\b(prices|news|forecasts?|exchanges|market data|live data)\b|\b(prices|news|forecasts?|exchanges)\b[^.\n]{0,100}\bfirm['’]s (own )?(dashboard|platform)\b/i;
const DAILY_FLOOR_RX = /daily[_ ]floor[^=\n]{0,30}(=|\bsits at\b|\bis\b)[^\n.]{0,40}\bremaining|day[_ -]start\w*\s*[−-]\s*remaining/i;
// Staged after evaluation run 13: b-stop wrote "stop_pct", o-montecarlo "`kelly`" (a tool's parameter and calc); o-montecarlo
// said half-Kelly is above "the risk any prop-firm ceiling troid has read would allow" with no tool behind it; s-firm
// singled out Bitfunded as "the one troid has verified most completely".
const TOOL_PARAM_RX = /\bfirm ["“]all["”]|\btopic:\s*\w+|\bstop_pct\b|\bcalc\s*[:=]|\bdrawdown_pct\b|\bwin_rate_pct\b|`(kelly|position_size|r_multiple|expectancy|recovery|fee_share|losses_to_limit|capped_budget|stats|atr_scale|effective_bets)`/;
const READ_ALL_RX = /\b(any|every|all|largest|smallest|tightest)\b[^.\n]{0,60}\btroid has read\b/i;
const SINGLE_OUT_RX = /\b(Bitfunded|BrightFunded|Crypto Fund Trader)\b[^.\n]{0,40}\b(most|best|more|better)\b[^.\n]{0,30}\b(verified|complete(ly)?|sourced|reliable|trusted|thorough(ly)?|recorded)\b/i;
PROMOTED_LINTS.push(
  [(t) => TOOL_PARAM_RX.test(t), "Never write a tool's parameters in a reply (stop_pct, firm \"all\", `kelly`): say what was computed in words."],
  [(t, tools) => READ_ALL_RX.test(t) && !toolSourceLines(tools).length,
   "A claim about every rule troid has read needs a tool behind it (trade_math with firm \"all\" gives the largest maximum loss, with its sources): get it, or leave the claim out."],
  [(t) => SINGLE_OUT_RX.test(t), "Never single out one firm (as the most verified, the best sourced): troid earns a commission and names no favourite."]);
PROMOTED_LINTS.push(
  [(t) => FIRM_RECORD_RX.test(t),
   "The firm's dashboard is the record of the trader's own account, not of prices, news, forecasts or exchanges: say troid has no live data, and name no place for them."],
  [(t) => DAILY_FLOOR_RX.test(t),
   "The daily floor is the day's starting balance less the fixed daily amount (quota × daily%): day_start − quota × daily%, never less a remaining budget."]);
// Staged after evaluation run 14: b-limits had the crossover backwards ("after a loss, the daily limit is usually tighter
// and binds"), worked no example and asked the user for an equity; b-leverage called no tool and asked for an entry, a
// stop and a quantity; b-stop wrote "the dollar amount troid allows on the trade".
const XOVER_BACKWARDS_RX = /\b(above|higher than|over)\b[^.\n;]{0,60}\b(starting balance|initial balance|quota|crossover|opening balance)\b[^.\n;]{0,60}\bmax(imum)?( loss| drawdown)?\b[^.\n;]{0,30}\bbinds?\b|\bbelow\b[^.\n;]{0,40}\bcrossover\b[^.\n;]{0,40}\bdaily\b[^.\n;]{0,30}\bbinds?\b|\bafter a loss\b[^.\n;]{0,40}\bdaily (loss )?(limit|budget)\b[^.\n;]{0,30}\b(tighter|binds?)\b/i;
const ASK_NUMBERS_RX = /\b(if you give|give (troid )?(a |the )?(specific|your)|provide (a |the |your )|share (a |the |your ))\b[^.\n]{0,80}\b(entry|stop|equity|quota|numbers|balance|quantity)\b|\b(takes|needs) an? (equity|entry)\b[^.\n]{0,60}\bif you\b/i;
const ALLOWS_RX = /\b(dollar amount|amount|risk|loss)\s+troid (allows|permits|accepts|is willing)\b|\btroid (allows|permits|accepts) (you )?(to )?(risk|lose|put)\b|\btroid (can |could |will |would )?(let|lets|allow|allows|permit|permits)\b[^.\n]{0,30}\b(into|in|on) (a|the|this) (trade|position)\b/i;   // run 15: "how many units troid can let into a trade"
PROMOTED_LINTS.push(
  [(t) => XOVER_BACKWARDS_RX.test(t),
   "Which limit binds is the other way round: above the crossover equity the daily limit binds; below it, after losses, the maximum loss binds. On the 1-Step the crossover is quota × (1 − 6% + 4%) = $98,000: get it through explain_rule (topic crossover) or check_budget."],
  [(t, tools) => /\bFormula\b/i.test(t) && !SUPPORT_OPENER.test(t) && (!tools.length || ASK_NUMBERS_RX.test(t)),
   "A teaching answer works its own example through a tool with numbers troid chooses: arithmetic through trade_math, a firm's rule on troid's reference account (a $100,000 Bitfunded 1-Step) through check_budget. Never ask the user for numbers to finish it."],
  [(t) => ALLOWS_RX.test(t), "troid never trades: the risk, the position, the stop and the trade are the trader's, and troid prices them."]);
// Staged after evaluation run 15: q-stats called the interval's top "a solid gain"; ex-kelly set full Kelly's 4.38× the
// daily limit beside half Kelly (run 11 had too); e-blown offered "a common cause of a failure" on Bitfunded to a trader
// who had named no firm and given no inputs.
const JUDGE_RX = /\b(solid|healthy|great|excellent|impressive|amazing|fantastic|awesome)\b|where [^.\n]{0,40}\bbelong\b|nowhere to hide/i;
const CAUSE_GUESS_RX = /\b(common|usual|typical|frequent|likely) (cause|reason|culprit)s?\b/i;
const esc = (x) => String(x).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
function kellyMixed(t, tools) {                  // a full-Kelly ratio written beside half Kelly, or the other way round
  for (const x of tools || []) {
    if (x.name !== "trade_math" || !x.result || !Array.isArray(x.result.working)) continue;
    for (const w of x.result.working) {
      const m = /^(full|half) Kelly ÷/.exec(w.step || ""); if (!m || typeof w.value !== "string") continue;
      const other = m[1] === "full" ? "half" : "full";
      if (new RegExp(`\\b${other}[- ]Kelly(?:(?!\\.\\s)[^;\\n]){0,80}(?<![\\d.])${esc(w.value.replace("×", ""))}\\s?×`, "i").test(t)) return true;
    }
  }
  return false;
}
// s-firm called Bitfunded's Express "the one product that fits a $500 budget" (the Instant, $249 at $5,000, fits too) and
// said equal 3% limits have "no crossover point" (it is the quota itself)
const NO_XOVER_RX = /\bno crossover\b|\bnever cross(es)?\b/i;
const ONLY_PRODUCT_RX = /\bthe (one|only) (product|challenge|account|option)\b[^.\n]{0,60}\b(fits|under|within|affordable)\b/i;
PROMOTED_LINTS.push(
  [(t) => NO_XOVER_RX.test(t), "Every product has a crossover, quota × (1 − max% + daily%): where the two limits are equal it is the quota itself. Get it through explain_rule (topic crossover) or check_budget."],
  [(t) => ONLY_PRODUCT_RX.test(t), "Don't call one product the only one that fits: check each product's recorded price through firm_rules, list every one that fits, and say which firms and products troid has no price for."]);
PROMOTED_LINTS.push(
  [(t) => JUDGE_RX.test(t), "State what the numbers imply, never whether they are good: no \"solid\", \"healthy\", \"great\" or the like."],
  [(t, tools) => kellyMixed(t, tools), "Each Kelly ratio belongs to its own fraction: full Kelly ÷ a limit and half Kelly ÷ a limit are different figures. Use the tool's line for each."],
  [(t, tools, asked) => SUPPORT_OPENER.test(t) && !BLAMES_TROID_RX.test(String(asked || "")) && CAUSE_GUESS_RX.test(t),
   "The trader has given no inputs yet: ask for them, and point to the firm's dashboard and hello@troid.ai. Guess no cause and assume no firm until the numbers are in."]);
// Staged after evaluation run 16 (the owner's review): every number in an answer comes from a tool's inputs or results,
// the user's own message or troid's published figures (web/api/_numbers.js); b-stop computed "roughly 3.5 times as many
// units" in prose (3.1 with its own fee) and ex-r "the whole of Bitfunded's 1-Step daily limit ($4,000 ÷ $500 ≈ 8)".
// b-leverage worked its example through trade_math and wrote no formula.
const unsupportedIn = (t, tools, asked) => NUMBERS.unsupportedNumbers(t, [asked], NUMBERS.toolNumbers(tools));
PROMOTED_LINTS.push(
  [(t, tools, asked) => unsupportedIn(t, tools, asked).length > 0,
   (t, tools, asked) => "Every number in the answer comes from a tool's result or the user's own message; these don't: " +
     unsupportedIn(t, tools, asked).slice(0, 8).join(", ") + ". Get each one through a tool (trade_math takes numbers troid chooses), or leave it out."],
  [(t, tools) => tools.some((x) => x.name === "trade_math") && !/=/.test(t) && !/\bFormula\b/i.test(t),
   "A teaching answer writes its formula out, with an equals sign (risk = |entry − stop| × quantity, say), and says why it works."]);
// Staged after the subset run of 2026-09-24: b-stop wrote its formula in words ("quantity equals the risk divided by the
// distance between entry and stop, plus a fee amount per unit", which reads as risk ÷ distance + fee); o-montecarlo's
// rewrite opened "That result models …", pointing at a tool's result the reader never saw.
function formulaInWords(t) {                     // a "Formula:" line whose formula has no equals sign
  const lines = String(t).split("\n");
  for (let i = 0; i < lines.length; i++) {
    const m = /^\s*(?:[-*]\s+)?(?:\*\*|__)?Formula(?:\*\*|__)?\s*:\s*(?:\*\*|__)?(.*)$/i.exec(lines[i]);
    if (!m) continue;
    let f = m[1].trim(), j = i + 1;
    while (!f && j < lines.length) f = lines[j++].trim();
    if (/^(?:none|n\/a|not applicable|no formula)\b/i.test(f)) continue;   // a part that doesn't apply, said so (run 9, p-hold)
    if (!/[=≈]/.test(f)) return true;
  }
  return false;
}
const DANGLING_OPEN_RX = /^\s*(?:\*\*|__)?(?:That|This|Those|These) (?:result|figure|output|simulation|number|table|calculation)s?\b/i;
PROMOTED_LINTS.push(
  [(t) => formulaInWords(t),
   "Write the formula in symbols, with an equals sign and its brackets, on its own line: quantity = risk ÷ (stop distance + fee per unit), say."],
  [(t) => DANGLING_OPEN_RX.test(t),
   "The answer opens by pointing at a result the reader never saw (\"That result …\"): open with the answer to the question, then say where each figure comes from."]);
// A read date the model wrote itself (the live test of 2026-10-04: max open positions "read 2026-09-23", a date no tool
// gave for that rule): every date beside "read" must be one a tool returned this turn, or the user's own.
const MONTHS = { jan: 1, feb: 2, mar: 3, apr: 4, may: 5, jun: 6, jul: 7, aug: 8, sep: 9, sept: 9, oct: 10, nov: 11, dec: 12 };
function isoOf(m) {
  const z = (n) => String(n).padStart(2, "0"), d = m.replace(/[\u2010\u2011]/g, "-");
  let x = /^(\d{4})-(\d{2})-(\d{2})$/.exec(d);
  if (x) return d;
  x = /^(\d{1,2}) ([A-Za-z]{3,9}) (\d{4})$/.exec(d);
  if (x && MONTHS[x[2].toLowerCase().slice(0, x[2].toLowerCase().startsWith("sept") ? 4 : 3)]) return x[3] + "-" + z(MONTHS[x[2].toLowerCase().slice(0, 3)]) + "-" + z(x[1]);
  x = /^([A-Za-z]{3,9}) (\d{1,2}),? (\d{4})$/.exec(d);
  if (x && MONTHS[x[1].toLowerCase().slice(0, 3)]) return x[3] + "-" + z(MONTHS[x[1].toLowerCase().slice(0, 3)]) + "-" + z(x[2]);
  return null;
}
const READ_DATES_RX = new RegExp(READ_DATE_RX.source.replace("\\bread (on )?", "\\b(?:read|re-read|reread)(?: on)? "), "g");
// each source a tool gave this turn: the words it names its rule and document by, and the dates troid read it
function sourcePairs(tools) {
  const out = [], walk = (o) => {
    if (Array.isArray(o)) return o.forEach(walk);
    if (!o || typeof o !== "object") return;
    if ((o.read_on || o.reread_on || o.cite) && (o.rule || o.document_section || o.document || o.cite)) {
      const text = [o.rule, o.document_section, o.document, o.cite].filter(Boolean).join(" ");
      out.push({ text: text.toLowerCase(), dates: new Set((JSON.stringify([o.read_on, o.reread_on, o.cite]).match(/\d{4}-\d{2}-\d{2}/g) || [])) });
    }
    Object.values(o).forEach(walk);
  };
  (tools || []).forEach((t) => walk(t.result));
  return out;
}
const RULE_WORDS = ["open position", "hold", "ladder", "concentration", "daily", "maximum loss", "max loss", "leverage", "fee", "target", "split",
  "reset", "floating", "minimum trading", "drawdown", "refund", "closed trade", "listed", "payout"];
function unsourcedReadDates(t, tools, asked) {
  const pairs = sourcePairs(tools), user = new Set(String(asked || "").match(/\d{4}-\d{2}-\d{2}/g) || []), body = stripSources(t), out = [];
  for (const m of body.matchAll(READ_DATES_RX)) {
    const iso = isoOf(m[1] || m[2] || "");
    if (!iso || user.has(iso)) continue;
    const before = body.slice(0, m.index), cut = Math.max(before.lastIndexOf("\n"), before.search(/[.!?]\s[^.!?]*$/));
    const win = before.slice(cut < 0 ? Math.max(0, before.length - 200) : cut).toLowerCase();
    const dated = pairs.filter((x) => x.dates.has(iso));
    // the clause names its rule by a section (s.3, 9(a)) or by the rule's words: some source with this date must name it too
    const marks = (win.match(/\bs\.\s?\d+\b|\b\d{1,2}\([a-z]\)(\([ivx]+\))?/g) || []).map((k) => k.replace(/\s/g, ""));
    const words = RULE_WORDS.filter((w) => win.includes(w));
    const ok = dated.length > 0 && (!marks.length && !words.length
      || dated.some((x) => marks.some((k) => x.text.includes(k)) || words.some((w) => x.text.includes(w))));
    if (!ok) out.push(m[0]);
  }
  return [...new Set(out)];
}
PROMOTED_LINTS.push(
  // a turn with no tool at all gets RULE_NUDGE instead (a rule with no tool behind it): this one is for a date beside a tool's rule
  [(t, tools, asked) => (tools || []).some((x) => x.result) && unsourcedReadDates(t, tools, asked).length > 0,
   (t, tools, asked) => "These read dates are not the ones a tool gave this turn for the rule beside them: " + unsourcedReadDates(t, tools, asked).join("; ") +
     ". Every date troid read a rule comes from the tool that gave the rule (firm_rules, firm_assets, explain_rule, check_budget, size_trade, check_compliance): " +
     "get the rule through it and give its date exactly, or leave the date to the sources the service writes under the answer. Never write a read date yourself."]);
// The read of evaluation runs 17 to 19 (2026-10-05, the owner's six fixes). These lints read what the reader sees: the final
// answer and what troid wrote before a tool call that the reply keeps (saidNotRepeatedNext), never a lead-in it drops
// (run 19, b-leverage: its formula sat in a lead-in that never reached the reader).
// 1. b-leverage. A size, notional, margin or liquidation figure is one a tool returned this turn for that very thing: the
//    read-date lint's rule, for numbers (run 17: "$200,000 at full size" as a margin, the tool's notional after the cut).
const FIG_KINDS = { margin: /\bmargins?\b/i, notional: /\bnotional\b/i, quantity: /\b(quantity|quantities|units?|position size)\b/i, liquidation: /\bliquidat\w*/i };
const FIG_OTHER = /\b(equity|risk(ed|s)?|loss(es)?|fees?|entry|stop|target|budget|floor|balance|quota|price|distance|crossover|account|profit|limit|leverage|cap)\b/i;
const kindOfLabel = (s) => Object.keys(FIG_KINDS).find((k) => FIG_KINDS[k].test(s)) || null;
// what the tools returned for each kind: their result fields, working steps and circuit breakers by name; a liquidation
// distance also from a tool's prose just after the word (explain_rule: "~20% at 5x"). Never other prose: run 17's own note
// ("Cut to fit the margin: at 2× equity of 100000 carries at most 200000 of notional") would pass its error.
function toolFigures(tools) {
  const by = { margin: [], notional: [], quantity: [], liquidation: [] };
  const add = (k, v) => { const x = typeof v === "number" ? v : +String(v).replace(/[,$%×\s]/g, ""); if (k && Number.isFinite(x)) by[k].push(x); };
  const walk = (o, key) => {
    if (Array.isArray(o)) return o.forEach((x) => walk(x, key));
    if (o && typeof o === "object") {
      const label = o.step || o.event;
      if (label != null) for (const f of ["value", "adverse_move_pct"]) if (f in o) add(kindOfLabel(String(label)), o[f]);
      for (const [k2, v] of Object.entries(o)) if (!["value", "adverse_move_pct"].includes(k2) || label == null) walk(v, k2);
      return;
    }
    if (typeof o === "number" && key) add(kindOfLabel(String(key).replace(/_/g, " ")), o);
    if (typeof o === "string") for (const m of o.matchAll(/\bliquidat\w*/gi))
      for (const n of o.slice(m.index, m.index + 200).matchAll(/(\d[\d,]*(?:\.\d+)?)\s?%/g)) add("liquidation", n[1]);
  };
  for (const t of tools || []) { walk(t.result); walk(t.input); }
  return by;
}
const FIG_NUM_RX = /(?<![\w.,])(\$\s?)?(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+\.\d+|\d{4,})(\s?[kK](?![a-zA-Z]))?(\s?%)?/g;
// each figure the reply writes beside one of the four kinds that no tool gave for that kind: [{ s, kind }]. A figure's
// thing is the label before it in its clause, or one just after it with nothing between ("$100,000 of margin"); an
// equation's result is named by the left side of the equation's first "=" ("margin = notional ÷ 5 = $25,255.18").
const wordsIn = (x) => (String(x).match(/[A-Za-z]{2,}/g) || []).length;
function labelledFigureSlips(t, tools, asked) {
  const have = toolFigures(tools), user = NUMBERS.numbersIn(String(asked || "")).map((n) => n.v), out = [];
  const near = (v, dec, k, scale) => have[k].some((a) => Math.abs(v - a) <= (scale > 1 ? scale / 2 : 0.5 * 10 ** -dec) + 1e-9);
  const body = stripSources(String(t)).replace(/\*\*|__|`/g, "").replace(/\b\d{4}-\d{2}-\d{2}\b/g, " ");
  for (const sent of body.split(/(?<=[.!?])\s+|\n+/)) {
    const labels = [];
    for (const m of sent.matchAll(/\b[A-Za-z][A-Za-z-]*\b/g)) {
      const k = kindOfLabel(m[0]) || (FIG_OTHER.test(m[0]) && m[0].length > 2 ? "other" : null);
      if (k) labels.push({ k, i: m.index, j: m.index + m[0].length });
    }
    const lastChecked = (a, b) => { const ls = labels.filter((l) => l.i >= a && l.j <= b && l.k !== "other"); return ls.length ? ls[ls.length - 1].k : null; };
    for (const m of sent.matchAll(FIG_NUM_RX)) {
      const p = m.index, q = p + m[0].length, raw = m[2], pct = !!m[4], scale = m[3] ? 1000 : 1;
      const v = +raw.replace(/,/g, "") * scale, dec = (raw.split(".")[1] || "").length;
      const before = sent.slice(0, p).replace(/[\s$]+$/, ""), after = sent.slice(q);
      if (/^\s?(×|x\b|-?(step|phase)\b)/i.test(after) || /\b1:$/.test(before) || user.some((u) => Math.abs(u - v) < 1e-9)) continue;   // a leverage, a product, the user's own
      if (/[×÷+−\-\/*(]$/.test(before) || /^\s*[×÷+−\/*)]/.test(after)) continue;   // inside an expression: the number lint reads those
      let kind = null;
      if (pct) {
        if (/\bliquidat\w*[^.]{0,60}$/i.test(sent.slice(0, p)) || /^[^.]{0,30}\bliquidat/i.test(after)) kind = "liquidation";
      } else if (/[=≈]$/.test(before)) {
        // walk left over the equation: each stretch between two "=" that holds no clause break and few words is part of it
        let e = before.length - 1, lhsFrom = 0;
        for (;;) {
          const prev = e > 0 ? Math.max(before.lastIndexOf("=", e - 1), before.lastIndexOf("≈", e - 1)) : -1;
          const seg = before.slice(prev + 1, e);
          if (prev < 0 || /[,;:]|\s—\s/.test(seg) || wordsIn(seg) > 6) {
            const cut = Math.max(seg.lastIndexOf(","), seg.lastIndexOf(";"), seg.lastIndexOf(":"), seg.lastIndexOf(" — "));
            lhsFrom = prev + 1 + (cut < 0 ? 0 : cut + 1);
            break;
          }
          e = prev;
        }
        kind = lastChecked(lhsFrom, e);
      } else {
        let best = null;
        for (const l of labels) {
          let d;
          if (l.j <= p) { if (/[;:]/.test(sent.slice(l.j, p))) continue; d = p - l.j; }
          else if (l.i >= q) { if (/[()[\],;:—]/.test(sent.slice(q, l.i))) continue; d = (l.i - q) * 1.25; }
          else continue;
          if (d <= 40 && (!best || d < best.d)) best = { k: l.k, d };
        }
        kind = best && best.k;
      }
      if (kind && kind !== "other" && (kind !== "liquidation" || pct) && !near(v, dec, kind, scale)) out.push({ s: m[0].trim(), kind });
    }
  }
  return out;
}
// liquidation the wrong way round (run 18, b-leverage: "at 10× … liquidation sits further from entry … than at 2×")
const LIQ_BACKWARDS_RX = /\b((higher|more|greater|bigger) leverage|10\s?[x×])[^.\n;]{0,80}\bliquidat\w*\b[^.\n;]{0,40}\b(further|farther|more distant)\b|\bliquidat\w*\b[^.\n;]{0,60}\b(further|farther)\b[^.\n;]{0,60}\b(at|with|under) ((higher|more) leverage|10\s?[x×])|\b((lower|less) leverage|2\s?[x×])\b[^.\n;]{0,60}\bliquidat\w*\b[^.\n;]{0,30}\bcloser\b/i;
// cross margin called Bitfunded's (run 19, b-leverage: "as Bitfunded does"): troid has no source for its margin modes
const CROSS_FIRM_RX = /\bcross\b[^.\n]{0,80}\bas Bitfunded does\b|\bBitfunded\b[^.\n]{0,40}\b(uses|offers|runs|is on|applies|has)\b[^.\n]{0,20}\bcross[- ]?margin\b|\bcross[- ]?margin\b[^.\n]{0,5}\(Bitfunded\)/i;
// 2. The reset in UTC only (runs 17 and 19, p-reset and p-reset-local): no local hour, by season or otherwise
const RESET_CTX_RX = /\b(reset|resets|trading day|rollover|rolls over)\b/i;
const LOCAL_HOUR_RX = /\bnoon\b|\bmid-?(afternoon|morning|day)\b|\bmidday\b|\b(early|late) (morning|afternoon|evening)\b|\b(EDT|EST)\b|\bEastern (Daylight|Standard)( Time)?\b|\b(1[0-2]|[1-9])(:[0-5]\d)?\s?(a\.?m\.?|p\.?m\.?)(?![a-z])|\b(1[0-2]|0?[1-9]):[0-5]\d\b(?![^.\n]{0,12}\bUTC)|\bin (summer|winter)\b|\b(summer|winter) time\b/i;
const resetCtx = (t, asked) => RESET_CTX_RX.test(String(asked || "")) || (RESET_CTX_RX.test(t) && /\b16:00\b/.test(t));
// 3. The crossover exactly (runs 17 and 19: the floor said to govern after "even a small amount", "even modestly"; run 18:
//    "both static floors measured from the account's quota")
const XOVER_SMALL_RX = /\b(even|any)\b[^.\n]{0,40}\b(small|modest(ly)?|slight(ly)?|little|minor)\b[^.\n]{0,120}\b(max(imum)?[- ]?(loss|drawdown)|floor)\b|\b(max(imum)?[- ]?(loss|drawdown)|floor)\b[^.\n]{0,80}\b(even|any)\b[^.\n]{0,30}\b(small|modest(ly)?|slight(ly)?|little|minor)\b|\bboth\b[^.\n]{0,30}\bstatic floors?\b/i;
// 4. "How is X calculated": the formula, then one worked example from a tool, said once (run 19: b-limits and b-leverage
//    wrote no formula, b-limits worked no example; run 18: b-stop gave its example twice)
const HOWCALC_RX = /\bhow (is|are|do|does|did|would|can)\b[^?\n]{0,80}\b(calculat|comput|work|determin|measur|scal|figur|set|size)\w*|\bwhat['’]?s the difference\b|\bwhat (is|are) the difference\b|\bdifference between\b|\bwhy (does|do|is|are)\b|\bwhat does\b[^?\n]{0,40}\bmean\b|\bdo I lose more\b/i;
// a formula: a "=" (or "≈") whose right side names a term (a letter that isn't a unit) and has an operator, not a worked instance
function hasGeneralFormula(t) {
  for (const line of String(t).replace(/\*\*|__|`/g, "").split("\n")) {
    const at = line.search(/[=≈]/);
    if (at < 0) continue;
    const rhs = line.slice(at + 1).split(/[=≈]/)[0];
    if (/[×÷+−\-\/·√|*]|\b(min|max|ceil|floor)\b/.test(rhs) && /(?<![\d.,])(?!(?:R|x|BTC|ETH|USD|EUR|UTC|units?|days?|per|trade|trades)\b)[A-Za-zα-ωρσμ][A-Za-z_]*/.test(rhs)) return true;
  }
  return false;
}
// one figure a tool computed (not one it was given) in the reply: a worked example
function workedFromTool(t, tools) {
  const got = new Set(NUMBERS.toolNumbers((tools || []).map((x) => ({ input: null, result: x.result }))).map(Number));
  return NUMBERS.numbersIn(stripSources(String(t)).replace(/\b\d{4}-\d{2}-\d{2}\b/g, " ")).some((n) => (n.dec > 0 || n.v >= 100) && !(n.dec === 0 && n.v >= 1900 && n.v <= 2100) && got.has(n.v));
}
// the same worked equation twice: its operands and its result written again (run 18, b-stop: "quantity = 500 ÷ (1,292 +
// 61.78) = 0.369336" above the answer and again under "In practice")
const NUM_EQ_RX = /((?:\$?\d[\d,]*(?:\.\d+)?\s*\)?\s*(?:[×÷+−*\/]|\s-\s)\s*\(?\s*)+\$?\d[\d,]*(?:\.\d+)?\s*\)?)\s*[=≈]\s*\$?(\d[\d,]*(?:\.\d+)?)/g;
function repeatedWorking(t) {
  const seen = new Set();
  for (const m of stripSources(String(t)).replace(/\*\*|__|`/g, "").matchAll(NUM_EQ_RX)) {
    const key = NUMBERS.numbersIn(m[1]).map((n) => n.v).join("|") + "=" + m[2].replace(/,/g, "");
    if (seen.has(key)) return true;
    seen.add(key);
  }
  return false;
}
// the crossover's budgets (run 28, p-crossover: "below $98,000 at the day's start, the $6,000 max-loss budget would be the
// smaller one"): $6,000 is the 1-Step's maximum-loss budget on a $100,000 day; below $98,000 it is under $4,000. A
// sentence that sets a day below the crossover beside a $6,000 budget or room is sent back
const XOVER_BELOW_RX = /\b(below|under|less than)\s+(\$?98,000|\$?98k|the crossover)\b/i;
const SIX_K_BUDGET_RX = /(?<![\d,.])\$?6,000(?![\d,])[^.\n;]{0,40}\b(budget|room)\b|\b(budget|room)\b[^.\n;]{0,30}(?<![\d,.])\$?6,000(?![\d,])/i;
// read from the day below the crossover on, up to a turn to another day ("whereas at a $100,000 start, $6,000")
// or a contrast with it (7 Oct, p-crossover-b02: "the usable room is under $4,000, not the $6,000 figure people quote")
const XOVER_TURN_RX = /\b(at|on|from|with) (a |the )?\$?100,000\b|\b(whereas|while|but|compared with|rather than|instead of)\b|\bnot (the |a )?\$?6,000\b|;/i;
const xoverBudgetSlip = (t) => stripSources(String(t)).split("\n").some((l) => sentencesOf(l).some((x) => {
  const m = x.match(XOVER_BELOW_RX);
  if (!m) return false;
  const after = x.slice(m.index), turn = after.slice(1).search(XOVER_TURN_RX);
  return SIX_K_BUDGET_RX.test(turn < 0 ? after : after.slice(0, turn + 1));
}));
// 5. A place named by kind for prices or news (run 17, o-news: "the exchanges and news services themselves"; run 18,
//    o-predict: "a market data service or news outlet"; run 20, live: "A news site, an exchange, or a data platform")
// run 28, ex-angry: "To reconstruct the calculation, we need the inputs". The checker's set (eval_character.js
// firstPerson): I, I'm/I've/I'll/I'd, me, my, mine, myself, we, us, our, ours, ourselves, let's and let me, with quoted
// text, a blockquote, the service's sources list and "should I" (a kind of question) left out
const FIRST_PERSON_RX = [/\bI\b/, /\bI['’](m|ve|ll|d)\b/, /\b(me|my|mine|myself|we|us|our|ours|ourselves)\b/, /\blet['’]s\b|\blet me\b/i,
                         /(^|[.?]\s+|\n\s*)(My|We|Our|Us|Me)\b/];
const unquotedForFirstPerson = (t) => String(t).replace(/^Sources, each with the date troid read it:\n(- .*(\n|$))*/m, "")
  .replace(/"[^"\n]{0,400}"|“[^”\n]{0,400}”/g, " ").split("\n").filter((l) => !/^\s*>/.test(l)).join("\n")
  .replace(/\bshould[- ]I\b/gi, "should-question");
const firstPersonIn = (t) => { const u = unquotedForFirstPerson(t); return FIRST_PERSON_RX.some((re) => re.test(u)); };
const OUTSIDE_KIND_RX = /\b(check|consult|see|use|visit|try|look at|look to|turn to|points? to|refer to|go to|head to)\b[^.\n]{0,40}\b(news (sites?|outlets?|services?|sources?|feeds?|apps?)|market[- ]data (services?|providers?|platforms?|sites?)|data (platforms?|providers?|services?)|financial (data|news)|charting (platforms?|sites?|tools?)|price (feeds?|sites?|trackers?)|(crypto )?exchanges?\b(?!\s*(liquidat|['’]s|fees?|margin|rates?)))|\b(news (sites?|outlets?|services?|sources?)|market[- ]data (services?|providers?|platforms?)|data platforms?)\b[^.\n]{0,40}\b(will have|have|has|carry|carries|show|shows|cover|covers)\b/i;
PROMOTED_LINTS.push(
  [(t, tools, asked) => labelledFigureSlips(t, tools, asked).length > 0,
   (t, tools, asked) => "These figures are not what a tool gave this turn for the thing beside them: " +
     labelledFigureSlips(t, tools, asked).slice(0, 6).map((x) => x.s + " as " + x.kind).join(", ") +
     ". Get each size, notional, margin and liquidation figure from trade_math (position_size, with an equity) or size_trade, for the leverage it belongs to, and quote it as the result gives it; where no tool gives one, say it in words."],
  [(t) => LIQ_BACKWARDS_RX.test(t), "Higher leverage brings an isolated position's liquidation closer to entry (about entry ÷ leverage away), never further; under cross margin leverage doesn't move it."],
  [(t) => CROSS_FIRM_RX.test(t), "troid has no recorded source for Bitfunded's margin modes: cross margin is troid's default model. Say so, and never call it the firm's."],
  [(t, tools, asked) => resetCtx(t, asked) && LOCAL_HOUR_RX.test(stripSources(t)),
   "Give Bitfunded's reset in UTC only: 16:00 UTC, in effect by 16:10 UTC, then this sentence, word for word: \"" + DST_SENTENCE + "\" No local hour: no noon, midday or mid-afternoon, no EDT or EST."],
  [(t) => XOVER_SMALL_RX.test(t),
   "State the crossover exactly: below $98,000 at the day's start the maximum-loss floor binds; between $98,000 and the $100,000 start the daily limit binds, and above the start too. A day that starts less than $2,000 below the start is still bound by the daily limit, and the daily floor is the day's start less the daily amount, never a static floor from the quota."],
  [(t, tools, asked, last) => HOWCALC_RX.test(String(last || asked || "")) && !SUPPORT_OPENER.test(t) && !hasGeneralFormula(t),
   "The question asks how something is worked out: after the one-line answer, write the formula out with an equals sign and its terms (quantity = risk ÷ (|entry − stop| + fee per unit), say), then one worked example from a tool."],
  [(t, tools, asked, last) => HOWCALC_RX.test(String(last || asked || "")) && !SUPPORT_OPENER.test(t) && !workedFromTool(t, tools),
   "Work one example through a tool this turn (trade_math for arithmetic; check_budget or explain_rule on troid's reference account, a $100,000 Bitfunded 1-Step, for a firm's limits) and give the figures it computed, once."],
  [(t) => repeatedWorking(t), "The worked example is given twice: give it once, after the formula."],
  [(t) => OUTSIDE_KIND_RX.test(t),
   "Name no place for prices, news or forecasts, by name or by kind (a news outlet, an exchange, a market data service). For where a price is going or what is moving the market, give troid's wording, word for word: \"" + OUT_OF_SCOPE_REPLY + "\""],
  // run 22, o-montecarlo: "Let's get the expectancy figure." (first person; inThirdPerson removes one with no figure)
  // run 28, p-crossover: the $6,000 maximum-loss budget set beside a day that starts below $98,000
  [(t) => xoverBudgetSlip(t), "The maximum-loss budget is the day's start less the $94,000 floor: $6,000 only on a day that starts at $100,000, under $4,000 on a day that starts below $98,000, which is why the floor binds there. Give the budget below the crossover from check_budget, or in words, never as $6,000."],
  // run 28, ex-angry: "we need the inputs" (the checker's whole set now, not only let's, let me and I'm/I'll/I've/I'd)
  [(t) => firstPersonIn(t), "Speak of troid in the third person: no \"let's\", \"let me\", \"I\", \"we\", \"us\" or \"our\". Say what troid computes (\"troid computes …\"), and lead into nothing: give the answer."]);
// the owner's fixes of 2026-10-07, after runs 29 to 31. 1. A method answer that opens on its example (run 31,
// b-leverage: "Long at entry 77,872, stop at 76,580, risking $500 on $100,000 equity:"): the first paragraph a lead-in to
// figures, a later part of the method, a position or a list. Over every saved reply: run 31's b-leverage, run 21's ex-r
// ("In practice") and run 3's ex-r ("Working through a long BTC position").
// 7 Oct, run 37's b-limits: "On this $100,000 Bitfunded 1-Step, starting a fresh day at equity $100,000: the daily floor
// is …", an account's figures first and the difference the question asks never said
const FIGURES_OPEN_RX = /^\s*(?:\*\*|__)?\s*(?:On|At|For|With|Using|Taking|Take)\b[^.:\n]{0,60}\$\s?\d/i;
const EXAMPLE_OPEN_RX = new RegExp(/^\s*(?:\*\*|__)?\s*(In practice|What it means|Worked example|Why it works|For your situation|Example|Working)\b|^\s*(?:\*\*|__)?\s*(long|short)\b|^\s*([-*•]\s|\||\d+[.)]\s)/.source
  + "|" + FIGURES_OPEN_RX.source, "i");
function exampleFirst(t, asked) {
  if (!HOWCALC_RX.test(String(asked || ""))) return false;
  const p = stripSources(String(t)).replace(/^troid doesn['’]t recommend; it prices what you bring\.\s*/, "").split(/\n\s*\n/)[0].trim();
  return (/:\s*$/.test(p) && !/\b(formula|answer)\b/i.test(p.split("\n")[0])) || EXAMPLE_OPEN_RX.test(p);
}
// 2. A figure asked for that the question gives (run 30, o-montecarlo: "give (or confirm) the average loss in R as well",
//    the question's 1% risk per trade being the 1R loss). Over every saved reply: run 30's o-montecarlo alone.
const ASK_SRC = "\\b(give|confirm|provide|send|supply)\\b|\\bshare (the|your)\\b|\\btell troid\\b|\\bwhat['’]?s your\\b|\\bwhat is your\\b";
const GIVEN_INPUTS = [
  ["the average loss", /\b(average|avg\.?) loss\b|\bloss (size )?in R\b/i, /\b(average|avg\.?) loss\b|\brisk(ed)? per trade\b|\b\d+(\.\d+)?\s?% risk\b/i],
  ["the win rate", /\bwin rate\b/i, /\b\d+(\.\d+)?\s?% win rate\b|\bwin rate (of |is )?\d/i],
  ["the average win", /\b(average|avg\.?) win\b/i, /\b(average|avg\.?) win\b/i],
  ["the risk per trade", /\brisk per trade\b/i, /\brisk(ed)? per trade\b|\b\d+(\.\d+)?\s?% risk\b/i],
  ["the number of trades", /\bnumber of trades\b|\bhow many trades\b/i, /\b\d+\s+trades\b/i]];
function asksGiven(t, asked) {
  const out = [];
  for (const s of stripSources(String(t)).split(/(?<=[.?!])\s+|\n+/))
    for (const [name, inReply, inAsked] of GIVEN_INPUTS)
      if (inAsked.test(String(asked || "")) && new RegExp("(?:" + ASK_SRC + ")[^.?\\n]{0,80}(?:" + inReply.source + ")", "i").test(s) && !out.includes(name)) out.push(name);
  return out;
}
// 3. A sentence that restates the one before it (run 30, s-product: "What can be compared is the two products' own recorded
//    rules, side by side." then "Here is what each product's own recorded rules give, side by side, …"; run 31, s-firm:
//    "… here's what $500 buys across the products troid has prices for." then "Here's what $500 buys, cheapest first:"):
//    two neighbouring prose sentences of at most 25 words sharing a run of four words and most of the shorter one's words,
//    not two parallel lines over different figures. Over every saved reply: those two alone.
const REPEAT_STOP = new Set("the a an of to and or in on at for is are be it its this that as by with from".split(" "));
const PROSE_SKIP_RX = /^\s*([-*•]\s|\||\d+[.)]\s|```|>)|^\s*(\*\*|__)?(Tier\b|troid['’]s assumptions, not the firm['’]s rules|Not financial advice)/;
const repeatWords = (s) => s.toLowerCase().replace(/\*\*|__|`/g, "").replace(/’/g, "'").replace(/[^\w$€%'.,-]+/g, " ").replace(/[.,](?=\s|$)/g, "")
  .split(/\s+/).filter(Boolean).map((w) => w.replace(/'s$|s'$|'$/, "").replace(/s$/, ""));
function repeatedSentence(t) {
  const S = stripSources(String(t)).split("\n").filter((l) => l.trim() && !PROSE_SKIP_RX.test(l)).flatMap(sentencesOf)
    .filter((s) => !/[=÷×]/.test(s)).map((s) => [s, repeatWords(s)]).filter(([, w]) => w.length >= 4);
  for (let i = 0; i + 1 < S.length; i++) {
    const a = S[i][1], b = S[i + 1][1];
    if (a.length > 25 || b.length > 25) continue;
    const ca = [...new Set(a.filter((w) => !REPEAT_STOP.has(w) && !/^[\d$.,%€()-]+$/.test(w)))], cb = [...new Set(b.filter((w) => !REPEAT_STOP.has(w) && !/^[\d$.,%€()-]+$/.test(w)))];
    const [x, y] = ca.length <= cb.length ? [ca, cb] : [cb, ca];
    if (x.length < 4 || x.filter((w) => y.includes(w)).length / x.length < 0.6) continue;
    // parallel lines over different figures ("Full Kelly, 17.5%, is 2.92 times …" then "Half Kelly, 8.75%, is 1.46 times …")
    const na = (S[i][0].match(/\d[\d,.]*/g) || []).join(" "), nb = (S[i + 1][0].match(/\d[\d,.]*/g) || []).join(" ");
    if (na && nb && na !== nb) continue;
    const runs = new Set(); for (let k = 0; k + 4 <= a.length; k++) runs.add(a.slice(k, k + 4).join(" "));
    for (let k = 0; k + 4 <= b.length; k++) { const r = b.slice(k, k + 4).join(" "); if (runs.has(r) && !r.split(" ").every((w) => REPEAT_STOP.has(w))) return [S[i][0], S[i + 1][0]]; }
  }
  return null;
}
// 4. A paragraph that restates the sources the service lists (run 30, p-crossover: "This is DERIVED from Bitfunded's
//    published daily (4%) and maximum (6%) loss rules — help centre, …, read 2026-09-23; … read 2026-09-21; … read
//    2026-09-18."): one led as a source line ("Rules used:", "Rule sources:", "This is DERIVED/SOURCED from …") that
//    names a source or read date, or any prose paragraph with three read dates, when the tools gave sources.
const SRC_LEAD_RX = /^\s*(\*\*|__)?\s*(rules?( used| sources?)?|rule basis|sources?( used)?|this is (DERIVED|SOURCED)\b[^.\n]{0,40}\b(from|sourced)|these (figures|rules)\b[^.\n]{0,80}\b(sourced?|read)|each (of these )?rules?\b[^.\n]{0,40}\bsource)\b/i;
const SRC_READ_RX = /\bread (on )?20\d\d-\d\d-\d\d/g;
// or a sentence anywhere in it saying every rule or figure above was read or sourced (7 Oct, s-product: "Every other figure
// shown here … is SOURCED, with its document and read date given above."; "Every rule above was read from the help centre's …")
const SRC_EVERY_RX = /\b(?:every|each|all)(?: other)? (?:rule|figure|number)s?\b[^.\n]{0,40}\b(?:above|here)\b[^.\n]{0,80}\b(?:read|SOURCED|sourced)\b/i;
function sourcesRestated(t, listed) {
  if (!listed) return null;
  for (const p of stripSources(String(t)).split(/\n\s*\n/)) {
    const prose = p.split("\n").filter((l) => !PROSE_SKIP_RX.test(l)).join(" ");
    if (!prose.trim()) continue;
    if ((SRC_LEAD_RX.test(prose) && /\bread (on )?20\d\d|\bsource|shown (above|below)/i.test(prose)) || (prose.match(SRC_READ_RX) || []).length >= 3
        || SRC_EVERY_RX.test(prose)) return prose;
  }
  return null;
}
PROMOTED_LINTS.push(
  [(t, tools, asked, last) => exampleFirst(t, last || asked),
   "The question asks how something is worked out: open with the one-line answer, then the formula with an equals sign and its terms; the worked example comes after both, never first."],
  [(t, tools, asked, last) => asksGiven(t, last || asked).length > 0,
   (t, tools, asked, last) => "The question already gives " + asksGiven(t, last || asked).join(" and ") + ": work from it and never ask for it (a win in R beside a risk per trade makes the average loss 1R)."],
  [(t) => !!repeatedSentence(t),
   (t) => "Say it once: \"" + repeatedSentence(t)[1] + "\" restates the sentence before it. Keep one of the two."],
  [(t, tools) => !!sourcesRestated(t, toolSourceLines(tools).length > 0),
   "The service lists every source and read date under the answer: drop the paragraph that restates them, and keep any figure it gives that the answer needs."]);
// 5. troid's desk, tools or figures given as a firm's (runs 33 and 34, ex-r: "Bitfunded's desk also prices the fee";
//    run 3, p-crossover: "Bitfunded's own check_budget"). Over every saved reply: those three.
const FIRM_TROID_RX = /\b(?:Bitfunded|BrightFunded|Crypto Fund Trader|CFT)['’]s?\s+(?:own\s+)?(?:desk|calculator|sizer|tools?|trade_math|size_trade|check_budget|explain_rule|firm_rules|1R\b|fee-inclusive|R with fees)/i;
const firmOwnsTroid = (t) => { const m = stripSources(String(t)).match(FIRM_TROID_RX); return m ? m[0] : null; };
// 6. Two lead-ins to one list (runs 32 and 34, s-product: "What troid can give is each product's recorded rules side by
//    side …" then "Here is what each product's own rules give, …:"): a sentence on what troid can give, show, do or
//    compare, or "Here is/are …", not itself ending in a colon, followed by a lead-in (one ending in a colon, or "Here
//    is/are", "Below"; 7 Oct, s-product: "Here are the two products' recorded rules, so …." then "Here are the recorded
//    rules side by side, at the $100,000 level:").
const ANNOUNCE_RX = /^(?:\*\*|__)?\s*(?:What (?:troid|it|ask troid) can (?:give|show|offer|compare|do)|What can be (?:compared|given|shown|offered|done)|What troid gives|Here(?:['’]s| is| are)\b)/i;
const LEADIN_RX = /:\s*(?:\*\*|__)?\s*$|^(?:\*\*|__)?\s*(?:Here(?:['’]s| is| are)|Below)\b/i;
// the second lead-in may come a sentence later (7 Oct, run 35's s-product: "What can be compared is the recorded rules of
// each, side by side." then "Both are single-fee products …" then "At the $100,000 account level, as troid has them
// recorded:"), never past a list line; and the announcement itself may come twice (runs 35 and 36, o-montecarlo: "What
// troid can give instead: …" then "What can be given instead:"), as may "does not run simulations"
const LIST_LINE_RX = /^\s*([-*•]\s|\||\d+[.)]\s)/;
const SIM_REFUSAL_RX = /\b(?:does not|doesn['’]t|never) run (?:any |a |new )?(?:Monte Carlo|simulations?)\b/i;
function doubleLeadIn(t) {
  const lines = stripSources(String(t)).replace(/^\s*troid doesn['’]t recommend; it prices what you bring\.\s*/, "").split("\n");
  const S = lines.flatMap((l) => (LIST_LINE_RX.test(l) ? [{ s: l, list: true }] : sentencesOf(l).map((s) => ({ s, list: false }))));
  for (let i = 0; i < S.length; i++) {
    if (S[i].list || !ANNOUNCE_RX.test(S[i].s)) continue;
    if (!/:\s*(?:\*\*|__)?\s*$/.test(S[i].s))
      // a sentence later only when the announcement holds no colon: "What it can do: quote …" is itself the content
      for (let j = i + 1; j <= (/:/.test(S[i].s) ? i + 1 : i + 2) && j < S.length && !S[j].list; j++) if (LEADIN_RX.test(S[j].s)) return [S[i].s, S[j].s];
    const again = S.slice(i + 1).find((x) => !x.list && ANNOUNCE_RX.test(x.s) && !/^(?:\*\*|__)?\s*Here/i.test(x.s) && !/^(?:\*\*|__)?\s*Here/i.test(S[i].s));
    if (again) return [S[i].s, again.s];
  }
  const sims = stripSources(String(t)).split("\n").flatMap(sentencesOf).filter((x) => SIM_REFUSAL_RX.test(x));
  return sims.length > 1 ? [sims[0], sims[1]] : null;
}
// 7. support.md section 4's line more than once, with or without its full stop (run 33, s-product: "troid doesn't
//    recommend; it prices what you bring — troid can size …" in its last paragraph)
const REFUSAL_ANY_RX = /troid doesn['’]t recommend; it prices what you bring/gi;
// or said again in other words after it (7 Oct, s-product: "troid doesn't pick a product; the choice is yours.", the
// budget answer's closing line, which only an answer from products_in_budget ends with)
const REFUSAL_AGAIN_RX = /\btroid (?:doesn['’]t|does not|won['’]t|will not|can['’]t|cannot) (?:pick|choose|recommend|select|decide)\b|\bthe choice is (?:yours|the trader['’]s)\b/i;
const refusalTwice = (t, budget) => { let b = stripSources(String(t)); const m = b.match(REFUSAL_ANY_RX) || [];
  if (budget) b = b.split(BUDGET_CLOSE).join("");
  return m.length > 1 || (m.length === 1 && REFUSAL_AGAIN_RX.test(b.slice(b.search(REFUSAL_ANY_RX) + m[0].length))); };
// 8. "N more losses" (the owner's ruling, 2026-10-08: one too many after this trade; runs 35 to 39's p-size, ex-r c02):
//    a count with "more" before losses, or before what the limit does ("4 more before the max-loss floor trips"); not
//    "one more loss … would breach" (run 1, b-limits), which counts nothing
const MORE_LOSSES_RX = /\b(\d+|two|three|four|five|six|seven|eight|nine|ten)\s+more\b(?:\s+[\w-]+){0,5}?\s+(?:loss(?:es)?\b|before\b[^.\n]{0,60}\b(?:trips?|reach(?:es|ed)?|hits?|fails?))/i;
const moreLosses = (t) => { const m = stripSources(String(t)).replace(/\*\*|__/g, "").match(MORE_LOSSES_RX); return m ? m[0] : null; };
PROMOTED_LINTS.push(
  [(t) => !!firmOwnsTroid(t),
   (t) => "\"" + firmOwnsTroid(t) + "\": troid's desk, its tools and the figures they compute are troid's, never a firm's. Say \"troid's desk\" (or troid's own tool's result), and keep a firm's name for the firm's own rules."],
  [(t) => !!doubleLeadIn(t),
   (t) => "Introduce the list once: \"" + doubleLeadIn(t)[0] + "\" and \"" + doubleLeadIn(t)[1] + "\" both lead into it, or say twice what troid can give or that it runs no simulation. Keep one lead-in, and write nothing before a tool call that the final answer says again."],
  [(t) => !!moreLosses(t),
   (t) => "\"" + moreLosses(t) + "\" counts one loss too many: the losses left include this trade. Say how many fit, this one included, and which one reaches the limit, as size_trade's note gives it (\"4 losses at this size fit, this one included; the 5th reaches the max drawdown\"); never \"N more losses\"."],
  [(t, tools) => refusalTwice(t, (tools || []).some((x) => x.name === "products_in_budget")),
   "support.md section 4's line goes once, first: \"troid doesn't recommend; it prices what you bring.\" Never again later in the answer, with or without its full stop, nor in other words (\"troid doesn't pick …\", \"the choice is yours\")."]);
// what troid wrote before a tool call, for the candidate: saidNotRepeated's rule, and a block whose worked figures the
// final answer gives again goes too (run 18, b-stop: its example above the answer, then again under "In practice").
// A final answer that opens on a later part of the method ("In practice: …") had its answer and formula written before
// the tool call (run 21, ex-r: "R is …" and the formula went with their block, and the reader got neither): then each
// paragraph stays that the final answer doesn't give again, without the lead-in to the call.
// also "Working:" and an account's figures first (7 Oct, run 37: b-stop opened "Working: stop distance = …" and b-limits
// "On this $100,000 Bitfunded 1-Step, …:", and the reader got no answer or formula, as run 21's ex-r)
const LATE_OPEN_RX = new RegExp(/^\s*(?:\*\*|__)?\s*(In practice|What it means|Worked example|Why it works|For your situation|Working)\b/.source
  + "|" + FIGURES_OPEN_RX.source, "i");
const workedFigures = (t) => NUMBERS.numbersIn(stripSources(String(t)).replace(/\b\d{4}-\d{2}-\d{2}\b/g, " ")).filter((n) => n.dec > 0 || n.v >= 10);
// a lead-in to the tool call: a sentence ending with ":" ("… Getting those now:"), one in the first person ("Let's get the
// expectancy figure.", run 22, o-montecarlo, above an answer that said it all again) or one announcing the call
const LEAD_IN_RX = /:\s*(\*\*|__)?\s*$|^\W*(let['’]s|let me|I['’]ll|I will|we['’]ll|we will)\b|^\W*(getting|checking|pricing|computing|calculating|running|pulling|fetching|looking (it|that|those|them) up|working (it|that|this|those) (out|through))\b/i;
const lastSentence = (b) => { const ls = String(b).trim().split("\n"); return sentencesOf(ls[ls.length - 1]).pop() || ""; };
function saidNotRepeatedNext(said, final) {
  const later = new Set(NUMBERS.numbersIn(final).map((n) => n.v));
  const repeated = (t) => { const ns = workedFigures(t); return ns.length >= 2 && ns.every((n) => later.has(n.v)); };
  // the final answer stands alone: a block that only leads into the call goes, whatever it says before the lead-in
  if (!LATE_OPEN_RX.test(String(final))) return saidNotRepeated(said, final).filter((b) => !repeated(b) && !LEAD_IN_RX.test(lastSentence(b)));
  const labels = new Set((String(final).match(METHOD_RX) || []).map((x) => x.toLowerCase()));
  // the lead-in to the call: the block's last sentences while they lead in ("… Pricing it now:")
  const withoutLeadIn = (p) => {
    const lines = p.split("\n");
    if (hasGeneralFormula(lines[lines.length - 1])) return p;
    const last = sentencesOf(lines.pop());
    while (last.length && LEAD_IN_RX.test(last[last.length - 1])) last.pop();
    return [...lines, last.join(" ")].join("\n").trim();
  };
  return said.map((b) => {
    const ps = String(b).split(/\n\s*\n/).map((p) => p.trim()).filter(Boolean);
    if (ps.length) ps[ps.length - 1] = withoutLeadIn(ps[ps.length - 1]);
    return ps.filter((p) => p && !(p.match(METHOD_RX) || []).some((x) => labels.has(x.toLowerCase())) && !repeated(p)).join("\n\n");
  }).filter(Boolean);
}
// troid in the third person (run 22, o-montecarlo: "Let's get the expectancy figure." reached the reader): a sentence
// that opens "Let's" or "Let me" and carries no figure goes; a leading "Answer:" label goes too (the form announced)
function inThirdPerson(reply, variant) {
  const body = String(reply).split("\n").map((l) => {
    if (!/\blet['’]s\b|\blet me\b/i.test(l)) return l;
    const lead = (l.match(/^\s*([-*•]|\d+[.)])\s+/) || [""])[0], parts = sentencesOf(l.slice(lead.length));
    const kept = parts.filter((s) => !(/^\W*(let['’]s|let me)\b/i.test(s) && !/\d/.test(s)));
    return kept.length === parts.length ? l : kept.length ? lead + kept.join(" ") : "";
  }).filter((l, i, a) => l.trim() || (a[i - 1] || "").trim()).join("\n");
  // candidate (staged after the 2026-10-08 promotion): a label inside a bold sentence ("**Answer: these inputs imply … .**",
  // round 4's t02) takes its bold with it, and the sentence starts with a capital, unless it starts with troid's own name
  if (variant !== "candidate") return body.replace(/^\s*(?:\*\*|__)?Answer(?:\s*:\s*(?:\*\*|__)?|(?:\*\*|__)\s*:)\s*/i, "").replace(/\n{3,}/g, "\n\n").trim();
  const unlabelled = body.replace(/^\s*(\*\*|__)Answer\s*:\s*(?!\1)([^\n]*?)\1/i, (m, b, x) => x)
    .replace(/^\s*(?:\*\*|__)?Answer(?:\s*:\s*(?:\*\*|__)?|(?:\*\*|__)\s*:)\s*/i, "");
  const capped = unlabelled !== body && !/^\s*(ask )?troid\b/.test(unlabelled) ? unlabelled.replace(/^(\s*)([a-z])/, (m, w, c) => w + c.toUpperCase()) : unlabelled;
  return capped.replace(/\n{3,}/g, "\n\n").trim();
}
// troid's own strategy, out of sample first (the owner, 2026-10-06; runs 21 to 23, q-stats): a sentence about troid's own
// result is one naming troid's own strategy, backtest or search and giving a figure or sample of it; the in-sample
// result (+0.033R, the best of the search) comes after the out-of-sample one (+0.008R) and says it is in-sample
const OWN_RX = /\btroid['’]s own\b|\btroid['’]s (backtest|strategy|search)\b|\bconfigurations? (it |troid )?(searched|tried|tested)\b/i;
const OWN_IN_RX = /(?<![\d.])0\.033\s?R?\b|\bbest (of|cell|configuration)\b|\bin[- ]sample\b/i;
const OWN_OUT_RX = /(?<![\d.])0\.008\s?R?\b|\bout[- ]of[- ]sample\b|\bout of sample\b/i;
function ownStrategySentences(t) {
  const out = [];
  String(t).split("\n").forEach((line, li) => sentencesOf(line).forEach((s, si) => {
    if (OWN_RX.test(s) && (OWN_IN_RX.test(s) || OWN_OUT_RX.test(s))) out.push({ li, si, s });
  }));
  return out;
}
// the in-sample result first, alone or unlabelled: the first in-sample mention of troid's own result against the first
// out-of-sample figure (+0.008R, troid's alone: run 19 gave it as "Its out-of-sample result comes first: … +0.008R")
const OWN_OUT_FIG_RX = /(?<![\d.])0\.008\s?R?\b/;
function ownStrategyMisordered(t) {
  const text = stripSources(String(t)), ss = ownStrategySentences(text), ins = ss.filter((x) => OWN_IN_RX.test(x.s));
  if (!ins.length) return false;
  const inAt = text.indexOf(ins[0].s) + ins[0].s.search(OWN_IN_RX), outAt = text.search(OWN_OUT_FIG_RX);
  const unlabelled = ss.some((x) => /(?<![\d.])0\.033\s?R?\b/.test(x.s) && !/\bin[- ]sample\b/i.test(x.s));
  return outAt < 0 || inAt < outAt || unlabelled;
}
// the backstop: the sentences about troid's own result give way to troid's own words, out of sample first, where the
// first stood; what that sentence said before its clause about troid (run 21: "the interval … contains zero — this is the
// same shape of result troid's own strategy search produced …") stays
function ownStrategyFirst(reply) {
  if (!ownStrategyMisordered(reply)) return reply;
  const ss = ownStrategySentences(reply), drop = new Set(ss.map((x) => x.li + ":" + x.si)), first = ss[0];
  const before = (sent) => {
    const at = sent.search(OWN_RX), head = sent.slice(0, at < 0 ? 0 : at);
    const cut = Math.max(head.lastIndexOf(" — "), head.lastIndexOf(" – "), head.lastIndexOf("; "), head.lastIndexOf(": "));
    if (cut < 0) return "";
    const kept = head.slice(0, cut).trim(), mark = head.slice(cut).trim()[0];
    if (mark === ":" && kept.split(/\s+/).length <= 5) return kept + ":";            // a label ("What it means:")
    return kept ? kept.replace(/[,;:—–\s]+$/, "") + "." : "";
  };
  const lines = String(reply).split("\n").map((line, li) => {
    if (!ss.some((x) => x.li === li)) return line;
    const lead = (line.match(/^\s*([-*•]|\d+[.)])\s+/) || [""])[0], parts = sentencesOf(line.slice(lead.length));
    const kept = [];
    parts.forEach((sent, si) => {
      // the line without its lead splits into the same sentences as the whole line: the lead holds no sentence end
      const key = li + ":" + si;
      if (li === first.li && si === first.si) { const b = before(sent); kept.push((b ? b + " " : "") + OWN_STRATEGY); }
      else if (!drop.has(key)) kept.push(sent);
    });
    return kept.length ? lead + kept.join(" ") : "";
  });
  return lines.filter((l, i, a) => l.trim() || (a[i - 1] || "").trim()).join("\n").replace(/\n{3,}/g, "\n\n").trim();
}
// "every account troid covers" beside the largest maximum loss troid has read (runs 21 to 23, ex-recovery)
const WIDEN_RX = /\b(every|any|all)\s+(funded\s+(or\s+evaluation\s+)?|evaluation\s+)?(accounts?|products?|challenges?)\s+(that\s+)?troid\s+(covers|compares|prices)\b|\b(outside|beyond)\s+what\s+(any|every)\s+product\s+troid\s+covers\b/i;
const widensMaxLoss = (t) => String(t).split(/(?<=[.!?])\s+|\n+/).some((s) => WIDEN_RX.test(s) && /\bmax(imum)?[- ](loss|drawdown)\b|\bfloor\b|\bfail(ed|s)?\b|\bbreach(ed|es)?\b|\b(20|\d{2})%/i.test(s));
PROMOTED_LINTS.push(
  [(t) => widensMaxLoss(t),
   "The largest maximum loss troid has read covers the products troid has a maximum loss for: say \"every maximum loss troid has read\", never every account, product or firm troid covers (troid has no maximum loss recorded for some products)."],
  [(t) => ownStrategyMisordered(t),
   "troid's own strategy: its out-of-sample result first, then the in-sample one labelled in-sample, in these words: \"" + OWN_STRATEGY + "\""]);
// The owner's fixes of 2026-10-06, after runs 25 to 27.
// 1. A budget (s-firm): an amount the user has to spend on a challenge, never an account size, a risk or a loss ("a
//    $100,000 account", "risking $500", "I'm down $500"): what the money buys is every product troid has a price for at
//    or under it, cheapest first, and troid picks none
const MONEY_RX = /(?:US\$|\$|€)\s?(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)\s?([kK])?(?![\d.]*\d)/g;
const BUDGET_BEFORE_RX = /\b(have|got|budget( of| is)?|spend|spending|afford|buy|purchase|invest|with|working with|start(ing)? with|only|just|can)\s*$/i;
const BUDGET_AFTER_RX = /^\s*(budget|to spend|to invest|to start|to put|in (my )?(pocket|savings)|buys?|gets?\b|can buy|will buy|would buy)\b/i;
const NOT_BUDGET_AFTER_RX = /^\s*(?:[A-Za-z’'-]+\s+){0,2}(account|accounts|challenge|quota|balance|equity|evaluation|funded|profit|profits|target|loss|losses|drawdown|stop|entry|position|notional|margin|risk|risked|day|daily|limit|floor|size|trade|in profit|in losses)\b/i;
function budgetOf(text) {
  const t = String(text || "");
  if (!/\b(firm|firms|challenge|challenges|account|product|products|prop|funded|evaluation|buy|afford|spend|start|which|best|budget)\b/i.test(t)) return null;
  for (const m of t.matchAll(MONEY_RX)) {
    const before = t.slice(Math.max(0, m.index - 30), m.index), after = t.slice(m.index + m[0].length, m.index + m[0].length + 40);
    if (NOT_BUDGET_AFTER_RX.test(after)) continue;                                                     // "$100,000 account"
    const said = BUDGET_AFTER_RX.test(after) || (BUDGET_BEFORE_RX.test(before) && !/\b(a|an|my|the|our|this|that|per|each)\s*$/i.test(before));
    if (said) return { budget: +m[1].replace(/,/g, "") * (m[2] ? 1000 : 1), currency: /€/.test(m[0]) ? "EUR" : "USD" };
  }
  return null;
}
const budgetFromTools = (tools) => { const x = (tools || []).find((t) => t.name === "products_in_budget" && t.result && !t.result.error);
  return x ? { budget: x.result.budget, currency: x.result.currency } : null; };
// one product set apart as what the money buys, gets or should go to (run 15: "the one product that fits a $500 budget";
// run 25: "the smallest product troid has a fee for at Bitfunded is its Instant")
const BUDGET_PRODUCT_RX = /\b(Express|Instant|1-Step|2-Step|1-Phase|2-Phase|3-Phase|Ascend|Break)\b/g;
const BUDGET_BUY_RX = /\b(buys?|bought|gets?( you)?|would buy|can buy|could buy|will buy|affords?|covers?|should go|should be spent|best spent|goes furthest)\b/i;
const BUDGET_PICK_RX = /\bthe (one|only|single|smallest|cheapest|lowest[- ]priced|least expensive|best|right|ideal|natural|obvious|sensible) (product|challenge|account|option|fit|choice|pick|way in|place to start|starting point|entry point)\b|\b(should|would|could) (go|be spent) (to|on)\b|\bspend (it|that|this|your (money|budget|\$?\d[\d,]*)|the (money|budget)) on\b/i;
function budgetPicks(t) {
  const body = stripSources(String(t));
  if (BUDGET_PICK_RX.test(body)) return true;
  return body.split(/(?<=[.!?])\s+|\n+/).some((s) => /(?:\$|€)\s?\d/.test(s) && BUDGET_BUY_RX.test(s) && new Set((s.match(BUDGET_PRODUCT_RX) || []).map((x) => x.toLowerCase())).size === 1);
}
// every product the list holds named beside its price on a line of its own, with its source and read date or that it has
// none, cheapest first; and the reply's text ending with the fixed line
const escRx = (s) => String(s).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
function budgetGaps(t, out) {
  const body = stripSources(String(t)).replace(/\*\*|__/g, "").replace(/\n*Not financial advice\. Verify with the firm before acting\.\s*$/, "").trim(), lines = body.split("\n");
  const missing = [], undated = [], at = [];
  for (const p of out.products) {
    const price = moneyOf(p.price, p.currency), rx = new RegExp("\\b" + escRx(p.product) + "\\b", "i");
    const i = lines.findIndex((l) => rx.test(l) && l.includes(price) && (l.includes(p.firm) || l.includes(p.firm.split(" ")[0])));
    if (i < 0) { missing.push(p.firm + " " + p.product + " (" + price + ")"); continue; }
    if (!/\bread \d{4}-\d{2}-\d{2}\b|\bnot yet recorded\b/i.test(lines[i])) undated.push(p.firm + " " + p.product);
    at.push(i);
  }
  return { missing, undated, ordered: at.every((v, k) => k === 0 || v >= at[k - 1]), closes: body.endsWith(BUDGET_CLOSE) };
}
const budgetFor = (t, tools, asked) => budgetFromTools(tools) || budgetOf(asked);
function budgetNote(t, tools, asked) {
  const b = budgetFor(t, tools, asked);
  if (!b) return null;
  const g = budgetGaps(t, products_in_budget(b));
  return g.missing.length || g.undated.length || !g.ordered || !g.closes ? g : null;
}
// 3. The prompt's own quoted words written back to the reader (runs 23 and 25 to 27: 'never "any slip."', 'not "a small
//    amount"', from the crossover guardrail, reworded now; runs 21 and 22: 'no "small slip"'): a phrase the reply sets in
//    quotes just after never, not or no, that the instructions quote (or one already written back), that the user didn't
//    write and no tool gave
const LEAKED_QUOTES = ["any slip", "small slip", "a small amount", "even a small amount", "even modestly"];
const QUOTE_AFTER_NO_RX = /\b(never|not|no|nor)\b[^.\n"“”]{0,14}["“]([^"“”\n]{2,48})["”]/gi;
const quoteKey = (s) => String(s).trim().replace(/[.,;:!?]+$/, "").toLowerCase();
let PROMPT_QUOTES = null;
function promptQuotes() {
  if (!PROMPT_QUOTES) {
    PROMPT_QUOTES = new Set(LEAKED_QUOTES);
    try {
      const c = context("candidate");
      const text = [guardrailsFor("candidate"), c.troid, characterBlock(c.character) || "", c.support].join("\n");
      for (const m of text.matchAll(/["“]([^"“”\n]{2,48})["”]/g)) PROMPT_QUOTES.add(quoteKey(m[1]));
    } catch (e) { /* the known ones only */ }
  }
  return PROMPT_QUOTES;
}
function promptEcho(t, tools, asked) {
  const user = String(asked || "").toLowerCase(), given = JSON.stringify((tools || []).map((x) => x.result || null)).toLowerCase(), set = promptQuotes();
  return [...stripSources(String(t)).matchAll(QUOTE_AFTER_NO_RX)].filter((m) => { const q = quoteKey(m[2]);
    return set.has(q) && !user.includes(q) && !given.includes(q); }).map((m) => m[0]);
}
PROMOTED_LINTS.push(
  [(t, tools, asked) => !!budgetFor(t, tools, asked) && budgetPicks(t),
   "Never set one product apart as what the money buys or gets, or as where it should go: give every product products_in_budget returns for the amount, cheapest first, as its lines give them, and end with this line, word for word: \"" + BUDGET_CLOSE + "\""],
  [(t, tools, asked) => !!budgetNote(t, tools, asked),
   (t, tools, asked) => { const g = budgetNote(t, tools, asked);
     return "Give every product products_in_budget returns for the amount, cheapest first, one line each with its price, its account size and its source and read date, or that its source is not yet recorded, as the tool's lines give them" +
       (g.missing.length ? " (missing: " + g.missing.join(", ") + ")" : "") + (g.undated.length ? " (no source or read date: " + g.undated.join(", ") + ")" : "") +
       "; then the tool's note; and end with this line, word for word: \"" + BUDGET_CLOSE + "\""; }],
  [(t, tools, asked) => promptEcho(t, tools, asked).length > 0,
   (t, tools, asked) => "These words are troid's own instructions, not the reader's: " + promptEcho(t, tools, asked).join("; ") +
     ". Say what is so in your own words, and set nothing in quotation marks that the user didn't write or a tool didn't give."]);
// the backstop: a budget answer that still sets one product apart, leaves one out or out of order, or doesn't end with the
// fixed line gives way to the list itself, under support.md section 4's line; its sources are the list's
function budgetListed(reply, lastUser, toolLog) {
  const b = budgetFromTools(toolLog) || budgetOf(lastUser);
  if (!b) return reply;
  const out = products_in_budget(b);
  if (out.error) return reply;
  const g = budgetGaps(reply, out);
  if (!budgetPicks(reply) && !g.missing.length && !g.undated.length && g.ordered && g.closes) return reply;
  toolLog.splice(0, toolLog.length, { name: "products_in_budget", input: b, result: out });
  return "troid doesn't recommend; it prices what you bring.\n\n" + budgetText(out);
}
// the user's question written back as a heading (run 18, b-stop: "Why does troid need your stop price to size a trade?")
const QNORM = (s) => String(s).toLowerCase().replace(/\byour\b/g, "my").replace(/\byou\b/g, "i").replace(/[^a-z0-9 ]+/g, " ").replace(/\s+/g, " ").trim();
function withoutEchoedQuestion(reply, lastUser) {
  const q = QNORM(lastUser);
  if (q.split(" ").length < 4) return reply;
  return reply.split("\n").filter((l) => QNORM(l.replace(/^\s*(#+|\*\*|__)\s*|\s*(\*\*|__)\s*$/g, "")) !== q).join("\n").replace(/\n{3,}/g, "\n\n").trim();
}
// the reset's backstop: a local hour the rewrite kept goes (a bracket holding one, then any sentence with one), the
// reset in UTC leads, and the DST sentence is there once (the owner, 2026-10-05: "only 16:00 UTC plus the patch's
// DST-safe sentence")
const RESET_LEAD = "Bitfunded's trading day resets at 00:00 UTC+8, which is 16:00 UTC all year, in effect by 16:10 UTC.";
// a question that asks when the reset is (p-reset, p-reset-local), not one that only mentions it
const RESET_TIME_ASK_RX = /\b(when|what time|what hour|which hour)\b[^?\n]{0,60}\b(reset|resets|rollover|roll over|trading day|new day)\b|\b(reset|resets|rollover|trading day)\b[^?\n]{0,60}\b(when|what time|in UTC|local|for me|my time|time ?zone)\b/i;
// a sentence ends at ".", "!" or "?" before a space or the end of the line, never inside "i.e." or "e.g." (run 20,
// p-reset-local: "…00:10 UTC+8, i.e. 16:00–16:10 UTC.")
const SENT_END_RX = /(?<!\b(?:i\.e|e\.g|vs|cf|approx|etc))[.!?](?:\*\*|__|\*|_)?(?=\s|$)/g;
function sentencesOf(line) {
  const out = [];
  let from = 0;
  for (const m of line.matchAll(SENT_END_RX)) { out.push(line.slice(from, m.index + m[0].length)); from = m.index + m[0].length; }
  out.push(line.slice(from));
  return out.map((s) => s.trim()).filter(Boolean);
}
// 16:00 UTC as a reply gives it: the hour, or the window from it (run 18, p-reset-local: "16:00–16:10 UTC")
const UTC1600_RX = /\b16:00(?:\s?UTC\b|\s?[–-]\s?16:10\s?UTC\b)/;
// the DST sentence in the reply's own words (run 18: "New York's clock moves with daylight saving, but UTC doesn't, so the
// New York hour for the reset isn't constant across the year"): it gives way to the sentence itself
const DST_OWN_RX = /\b(clocks?|time)\b[^.\n]{0,40}\b(moves?|shifts?|changes?)\b[^.\n]{0,20}\bdaylight saving\b/i;
function resetInUtcOnly(reply, lastUser) {
  const local = resetCtx(reply, lastUser) && LOCAL_HOUR_RX.test(reply);
  if (!local && !(RESET_TIME_ASK_RX.test(String(lastUser || "")) && UTC1600_RX.test(reply))) return reply;
  let body = reply;
  if (local) {
    const keepLine = (line) => {
      const x = line.replace(new RegExp("\\s*\\((?=[^()]*(" + LOCAL_HOUR_RX.source + "))[^()]*\\)", "gi"), "");
      const lead = (x.match(/^\s*([-*•]|\d+[.)])\s+/) || [""])[0], parts = sentencesOf(x.slice(lead.length)), kept = parts.filter((s) => !LOCAL_HOUR_RX.test(s));
      return kept.length === parts.length ? x : kept.length ? lead + kept.join(" ") : "";
    };
    body = body.split("\n").map((l) => (LOCAL_HOUR_RX.test(l) ? keepLine(l) : l)).filter((l, i, a) => l.trim() || (a[i - 1] || "").trim()).join("\n").trim();
    // the sentence that gave the reset can be the one that went (run 17, p-reset-local: "resets at 16:00–16:10 UTC, which
    // converts to noon Eastern in summer"): then troid's own sentence leads
    if (!body.split("\n").some((l) => sentencesOf(l).some((s) => /\breset/i.test(s) && UTC1600_RX.test(s)))) body = RESET_LEAD + "\n\n" + body;
  }
  const flat = (s) => s.replace(/[’‘]/g, "'");
  if (!flat(body).includes(DST_SENTENCE)) {
    const lines = body.split("\n"), own = lines.findIndex((l) => DST_OWN_RX.test(l));
    if (own >= 0) {
      const label = (lines[own].match(/^\s*(?:[-*•]\s+)?(?:\*\*[^*\n]+\*\*|__[^_\n]+__)\s*/) || [""])[0];
      lines[own] = label + sentencesOf(lines[own].slice(label.length)).map((s) => (DST_OWN_RX.test(s) ? DST_SENTENCE : s)).join(" ");
    } else {
      const at = lines.findIndex((l) => UTC1600_RX.test(l));
      if (at >= 0) {
        const l = lines[at], from = l.search(UTC1600_RX);
        const end = [...l.matchAll(SENT_END_RX)].find((m) => m.index >= from);
        lines[at] = end ? l.slice(0, end.index + end[0].length) + " " + DST_SENTENCE + l.slice(end.index + end[0].length) : l.replace(/\s*$/, ". " + DST_SENTENCE);
      }
    }
    body = lines.join("\n");
  }
  return body.replace(/\n{3,}/g, "\n\n").trim();
}
// 5. A question about where a price is going, what moves the market or the news, answered with no tool: troid's wording,
//    word for word (run 18, o-predict, the fast model: "consult a market data service or news outlet")
const OUT_OF_SCOPE_ASK_RX = /\bwhere will\b|\bwhere['’]?s\b[^?\n]{0,30}\b(going|headed)\b|\bwill (the )?(price|bitcoin|btc|eth|ether|crypto|market|it)\b[^?.\n]{0,40}\b(go|be|hit|reach|rise|fall|drop|pump|dump|trade|moon|crash)\b|\bpredict|\bforecast|\bprice (target|prediction)s?\b|\bwhat['’]?s (moving|driving)\b|\bwhat is (moving|driving)\b|\bwhy (is|did|has) (the )?(market|bitcoin|btc|eth|crypto|price)\b[^?.\n]{0,25}\b(up|down|moving|pump|dump|fall|fell|rise|rose|drop|crash)\w*|\b(crypto|market|bitcoin|btc)\b[^?.\n]{0,25}\bnews\b|\bnews\b[^?.\n]{0,25}\b(today|this week)\b|\bheadlines?\b/i;
const IN_SCOPE_RX = /\b(Bitfunded|BrightFunded|Crypto Fund Trader|CFT|FTMO|Topstep|rules?|reset|limit|drawdown|news trading|desk|tape|fill|size|stop|entry)\b/i;
const outOfScopeFixed = (reply, lastUser, toolLog) =>
  (!(toolLog || []).length && OUT_OF_SCOPE_ASK_RX.test(String(lastUser || "")) && !IN_SCOPE_RX.test(String(lastUser || "")) ? OUT_OF_SCOPE_REPLY : reply);
// support.md section 2, step 4: the three usual causes, when the user says troid's numbers were involved and the reply
// leaves them out (run 14, ex-angry). Before the dashboard's paragraph; English only.
const BLAMES_TROID_RX = /\btroid\b|\bcalculator\b|\byour (numbers?|tool|site|math|figures?|desk)\b/i;
const SUPPORT_STEP4 = "When troid's number and the account disagree, it is usually one of three causes: an input differed from the account's real state; " +
  "the firm's rule changed after the date troid read it; or the firm applied a rule troid marks pending. The reconstruction shows which one, or that it can't tell.";
// a cause the reply already names in its own words counts (run 15, ex-angry: "an input that didn't match the account's
// actual state … a rule troid has marked pending" was given twice, once by the model and once by the service)
const CAUSES_RX = [/\binputs?\b[^.\n]{0,40}\b(differ|different|wrong|mismatch|didn['’]t match|did not match|doesn['’]t match)/i,
  /\bchang(e|ed|es)\b[^.\n]{0,60}\b(read|capture)|\b(read|capture) date\b/i, /\bpending\b/i];
function withSupportStep4(reply, lastUser) {
  if (!SUPPORT_OPENER.test(reply) || !BLAMES_TROID_RX.test(String(lastUser || ""))
      || CAUSES_RX.filter((rx) => rx.test(reply)).length >= 2) return reply;
  const paras = reply.split(/\n\s*\n/), at = paras.findLastIndex((p) => /hello@troid\.ai/i.test(p));
  paras.splice(at < 0 ? paras.length : at, 0, SUPPORT_STEP4);
  return paras.join("\n\n");
}
// what troid wrote before a tool call, less a block whose method sections the final answer gives again (run 13, b-stop:
// the formula and why it works, twice)
const METHOD_RX = /\b(Formula|Why it works|Worked example|What it means|In practice)\b/gi;
function saidNotRepeated(said, final) {
  const later = new Set((String(final).match(METHOD_RX) || []).map((x) => x.toLowerCase()));
  return said.filter((b) => !(String(b).match(METHOD_RX) || []).some((x) => later.has(x.toLowerCase()))
    && !/:\s*$/.test(String(b)));   // a lead-in to the tool call ("… Getting those now:"): the final answer stands alone (run 15, o-montecarlo)
}
// the model's rewrite of a draft the user never saw, announced ("Retracting the earlier version of this answer"): the
// sentence goes (run 12, s-firm)
const UNSEEN_DRAFT = "\n(The user never saw the draft above: say nothing about it, about a retraction or about a rewrite.)";
// the candidate's rewrite is the whole reply: what troid wrote before a tool call isn't shown with it (run 21, ex-r: the
// rewrite opened at "In practice", its answer and formula left in the text before the calls)
const UNSEEN_SAID = "\n(The reader sees only the answer you write now, none of what you wrote before or between the tool calls: write it whole, from its one-line answer on.)";
const REWRITE_TALK_RX = /[^.\n]*\b(retract(ing|ed|s)?|(earlier|previous|first|prior) (version|draft|answer)|rewrit(e|ten|ing) (of )?(this|the) answer)\b[^.\n]*[.:]\s*/gi;
const withoutRewriteTalk = (reply) => reply.replace(REWRITE_TALK_RX, "").replace(/\n{3,}/g, "\n\n").trim();
// Promoted 2026-10-08: the lints staged as the candidate's are every visitor's now, after LINTS; a new candidate's
// lints (CANDIDATE_LINTS, none staged since) come after both, for the candidate only
const CANDIDATE_LINTS = [];
const notesOf = (lints, t, tools, asked, last) => lints.filter(([test]) => test(t, tools || [], asked, last)).map(([, note]) => (typeof note === "function" ? note(t, tools || [], asked, last) : note));
const lintNotesFor = (t, variant, tools, asked, last) => lintNotes(t).concat(notesOf(PROMOTED_LINTS, t, tools, asked, last),
  variant === "candidate" ? notesOf(CANDIDATE_LINTS, t, tools, asked, last) : []);
const LINT_NOTE = (notes) => "(A note from the service, not the user: write the whole answer again, keeping every figure and every tool result as they are, and fix this:\n" +
  notes.map((n) => "- " + n).join("\n") + ")";
const LINT_MIN_MS = 20_000;                                             // a rewrite starts only with this much of the deadline left
// support.md section 4's reply, first and once: a short preface that announces it goes (run 8: "Should-I questions get a
// fixed answer:", "support.md section 4 applies here:"), and so does a second copy. A longer text before it stays.
const SHOULD_I_RX = /troid doesn['’]t recommend; it prices what you bring\./g;
function refusalOnceFirst(reply) {
  const first = reply.search(SHOULD_I_RX);
  if (first < 0) return reply;
  const head = reply.slice(0, first), m = reply.slice(first).match(/^troid doesn['’]t recommend; it prices what you bring\./)[0];
  const rest = reply.slice(first + m.length).replace(SHOULD_I_RX, "").replace(/[ \t]+\n/g, "\n").replace(/\n[ \t]+/g, "\n").replace(/\n{3,}/g, "\n\n");
  const keepHead = head.trim() && (head.length > 160 || hasFigure(head.replace(/\bsection \d+\b/gi, " ")));
  return ((keepHead ? head : "") + m + rest).replace(/^\s+/, "").replace(/(^|\n\n) +/g, "$1").replace(/\n{3,}/g, "\n\n");
}
// support.md section 4's reply word for word on a should-I question, for the candidate until it is promoted (run 10:
// s-product and s-firm paraphrased it, "…isn't something troid computes as advice — troid prices what you bring"). A
// first sentence that paraphrases it goes; the rest stays. English only: another language's reply is its reviewer's.
const SHOULD_ASK_RX = /(^|[.?!,;:]\s*|\b(so|and|but)\s+)(should I\b|which\b[^.?!\n]{0,60}\bbest\b|will I pass\b|what should I (trade|buy|pick|choose)\b|(do|would) you recommend\b)/i;
const PARAPHRASE_RX = /prices what you bring|\bdoes(n['’]t| not) recommend|not something troid\b|isn['’]t something troid\b/i;
// the candidate's: a later copy without its full stop goes too, with what joins it to the rest of its sentence ("… what
// you bring — troid can size …" leaves "troid can size …"; run 33, s-product)
const REFUSAL_LATER_RX = /troid doesn['’]t recommend; it prices what you bring(?:\.|\s*[—–]\s*|\s*[,;:]\s*|(?=\s))/g;
function refusalOnceFirstNext(reply) {
  const once = refusalOnceFirst(reply), first = once.search(/troid doesn['’]t recommend; it prices what you bring\./);
  if (first < 0) return once;
  const head = once.slice(0, first + "troid doesn't recommend; it prices what you bring.".length);
  return (head + once.slice(head.length).replace(REFUSAL_LATER_RX, "")).replace(/[ \t]+\n/g, "\n").replace(/\n{3,}/g, "\n\n");
}
function refusalWordForWord(reply, lastUser) {
  if (!SHOULD_ASK_RX.test(String(lastUser || "")) || /troid doesn['’]t recommend; it prices what you bring\./.test(reply)) return reply;
  const body = reply.replace(/^\s+/, ""), m = body.match(/^[^\n]*?[.?!](?=\s|$)/);
  const rest = m && m[0].length <= 240 && PARAPHRASE_RX.test(m[0]) ? body.slice(m[0].length).replace(/^[ \t]+/, "") : body;
  return ("troid doesn't recommend; it prices what you bring." + (rest.startsWith("\n") ? "" : " ") + rest).trim();
}
function withSupportStep5(reply, lang) {
  if (!SUPPORT_OPENER.test(reply) || (/hello@troid\.ai/i.test(reply) && /dashboard/i.test(reply))) return reply;
  return reply + "\n\n" + S(lang, "ask.support_step5");
}
function closeWithNote(reply, lang) {
  const note = S(lang, "ask.note"), body = String(reply).split(note).join("").replace(/\n{3,}/g, "\n\n").trim();
  return hasFigure(body) ? body + "\n\n" + note : reply;
}
const textOf = (resp) => (resp.content || []).filter((b) => b.type === "text").map((b) => b.text).join("\n").trim();
const wantsTool = (resp) => resp.stop_reason === "tool_use" || (resp.stop_reason === "max_tokens" && (resp.content || []).some((b) => b.type === "tool_use"));

// troid's side of the history is signed: each reply carries an HMAC over the whole conversation up to and
// including it, and the next message must bring it back. The signing itself keeps no state (the conversation store is separate). The HMAC input starts
// with a hash of the guardrails, so a history signed under older guardrails no longer verifies.
// The prompt's version: the variant, its guardrails and the files it loads. Worked out on first use, so a missing
// context file answers 503 like everywhere else instead of failing the function at load.
const VERSIONS = {};
const versionOf = (variant) => VERSIONS[variant] || (VERSIONS[variant] = crypto.createHash("sha256").update(JSON.stringify([variant,
  guardrailsFor(variant), ...["troid", "support", "character"].map((k) => context(variant)[k] || "")])).digest("hex").slice(0, 16));
// The session ID is inside the signature, so a conversation cannot move to another session mid-way; the version is
// the prompt's, so it cannot move between the live prompt and the candidate either, even when nothing is staged.
const sign = (msgs, session, variant) => crypto.createHmac("sha256", TURN_KEY).update(JSON.stringify([versionOf(variant === "candidate" || variant === "patch" ? variant : "live"),
  String(session || ""), ...msgs.map((m) => [m.role, m.content])])).digest("base64url");
function signedOk(msgs, sig, session, variant) {
  if (msgs.length === 1) return true;
  const want = Buffer.from(sign(msgs.slice(0, -1), session, variant)), got = Buffer.from(String(sig || ""));
  return got.length === want.length && crypto.timingSafeEqual(got, want);
}
// What the page must show to delete its own conversation: an HMAC of the session ID under the turn key. It
// does not depend on the guardrails, so it stays valid for the 30 days the conversation is kept.
const deleteToken = (session) => crypto.createHmac("sha256", TURN_KEY).update("troid-delete\0" + session).digest("base64url");
function tokenOk(session, token) {
  const want = Buffer.from(deleteToken(session)), got = Buffer.from(String(token || ""));
  return got.length === want.length && crypto.timingSafeEqual(got, want);
}

// ---------------------------------------------------------------- the conversation store
const storeOn = () => !!(STORE_URL && STORE_TOKEN);
// One transaction (MULTI/EXEC) over Upstash's REST API; throws if any command fails.
async function store(commands, ms) {
  const r = await fetch(STORE_URL + "/multi-exec", { method: "POST", signal: AbortSignal.timeout(ms || 3000),
    headers: { authorization: "Bearer " + STORE_TOKEN, "content-type": "application/json" }, body: JSON.stringify(commands) });
  const out = await r.json().catch(() => null);
  if (!r.ok || !Array.isArray(out) || out.some((x) => !x || x.error)) throw new Error("store " + r.status);
  return out.map((x) => x.result);
}
// One entry per message, built field by field from what the service itself holds: nothing from the request's
// headers, so no address and no user agent can reach it.
function entry(lang, user, reply, model, tools, flags) {
  const sources = [];
  for (const t of tools) for (const s of ((t.result && t.result.sources) || [])) sources.push(s);
  return JSON.stringify(Object.assign({ at: new Date().toISOString(), lang, user, reply, model, tool_calls: tools, sources }, flags || {}));
}
async function keep(session, text) {
  const key = "conv:" + session;
  await store([["RPUSH", key, text], ["EXPIRE", key, String(RETENTION_S)]]);
}
// null if the history is malformed; otherwise the messages, trimmed
function validate(body) {
  const m = body && Array.isArray(body.messages) ? body.messages : null;
  if (!m || !m.length || m.length > MAX_MESSAGES) return null;
  const out = [];
  let total = 0;
  for (let i = 0; i < m.length; i++) {
    const x = m[i];
    const role = i % 2 === 0 ? "user" : "assistant";
    if (!x || x.role !== role || typeof x.content !== "string") return null;
    const content = x.content.trim();
    if (!content || content.length > (role === "user" ? MAX_CHARS : MAX_REPLY_CHARS)) return null;
    total += content.length;
    out.push({ role, content });
  }
  if (total > MAX_TOTAL_CHARS) return null;
  return out.length % 2 === 1 ? out : null;   // ends on the user
}
const tooLong = (body) => {                                  // only the new message is over the limit: shorten it, keep the session
  const m = body && Array.isArray(body.messages) ? body.messages : null, last = m && m[m.length - 1];
  return !!(last && last.role === "user" && typeof last.content === "string" && last.content.trim().length > MAX_CHARS);
};
function json(res, code, obj) { res.statusCode = code; res.setHeader("content-type", "application/json; charset=utf-8"); res.end(JSON.stringify(obj)); }
const isOn = () => ENABLED && !!KEY && Buffer.byteLength(TURN_KEY) >= 32 && storeOn();
const querySession = (req) => { try { return (req.query && req.query.session) || new URL(req.url || "/", "http://x").searchParams.get("session") || ""; } catch (e) { return ""; } };

// The prompt a request gets, and whether it is the operator's: "live" for everyone; with the candidate key (the
// evaluation runner), "candidate", or "live" or "patch" when x-troid-variant says so — the live baseline, or the live
// prompt with context/patch/'s files, unstored and unthrottled like any operator request. null for a request carrying a
// wrong key, which is refused.
function requestOf(req) {
  const h = req.headers["x-troid-candidate"];
  if (h === undefined) return { variant: "live", operator: false };
  if (Buffer.byteLength(CANDIDATE_KEY) < 32) return null;
  const want = Buffer.from(CANDIDATE_KEY), got = Buffer.from(String(h));
  if (!(got.length === want.length && crypto.timingSafeEqual(got, want))) return null;
  const v = String(req.headers["x-troid-variant"] || "");
  return { variant: v === "live" || v === "patch" ? v : "candidate", operator: true };
}
const STAGED = ["TROID.md", "TROID-CHARACTER.md", "support.md"];
function queryLang(req) {
  try { return (req.query && req.query.lang) || new URL(req.url || "/", "http://x").searchParams.get("lang"); } catch (e) { return null; }
}

module.exports = async (req, res) => {
  res.setHeader("cache-control", "no-store");
  let lang = liveLang(queryLang(req));                                   // the page's language, if it is live; else English
  if (req.method === "GET") {
    let ctx = null;
    try { const c = context(); ctx = { troid_md: c.troid.length, support_md: c.support.length, character_md: c.character ? c.character.length : 0,
                                     firms_json: c.firms.length, prompt_firms: JSON.stringify(c.prompt_firms).length,
                                     methodology_md: c.method.length, firms: Object.keys(profiles()) }; } catch (e) { ctx = { error: "context missing" }; }
    const candidate = { key: Buffer.byteLength(CANDIDATE_KEY) >= 32, staged: STAGED.filter((f) => readStaged(f) != null),
                        guardrails: CANDIDATE_GUARDRAILS.length, tools: CANDIDATE_TOOLS.map((t) => t.name),
                        rules: Object.keys(CANDIDATE_RULES), run: Object.keys(CANDIDATE_RUN), lints: CANDIDATE_LINTS.length,
                        eval_key: EVAL_KEY.length > 0, patch: STAGED.filter((f) => readPatch(f) != null),
                        patch_rules: Object.keys(PATCH_RULES) };
    // resting: today's answers are at the cap, or this address's are; the page says so before anyone types
    let today = null;
    if (isOn()) { try { [today] = await store([["GET", "cap:" + utcDay()]]); today = +today || 0; } catch (e) { today = null; } }
    const resting = (today != null && today >= DAILY_TURNS) || !visitorLeft(clientKey(req));
    return json(res, 200, Object.assign({ enabled: isOn(), flag: ENABLED, limit_per_hour: LIMIT_PER_HOUR, max_messages: MAX_MESSAGES, max_chars: MAX_CHARS,
                            caps: { daily: DAILY_TURNS, per_visitor: VISITOR_TURNS }, resting,
                            resting_text: resting ? S(lang, "ask.err.resting") : undefined,
                            models: { lookup: MODEL_LOOKUP, tools: MODEL_TOOLS }, tools: toolsFor("live").map((t) => t.name), lang, languages: liveCodes(),
                            disclosure: S(lang, "ask.disclosure"), store: storeOn(), retention_days: RETENTION_S / 86400, context: ctx, candidate }, keyReport()));
  }
  if (req.method === "DELETE") {                                        // the page's own conversation, at once
    if (!storeOn() || Buffer.byteLength(TURN_KEY) < 32) return json(res, 503, { error: S(lang, "ask.err.not_configured") });
    const site = req.headers["sec-fetch-site"];
    if (site && site !== "same-origin") return json(res, 403, { error: "ask troid answers on troid.ai only." });
    if (!allow("del:" + clientKey(req))) return json(res, 429, { error: S(lang, "ask.err.limit", { n: LIMIT_PER_HOUR }) });   // its own bucket: deleting never uses up messages
    const session = String(querySession(req));
    if (!SESSION_RE.test(session)) return json(res, 400, { error: S(lang, "ask.err.session") });
    if (!tokenOk(session, req.headers["x-troid-token"])) return json(res, 403, { deleted: false, error: "Only the page that holds this conversation can delete it here. Otherwise write to hello@troid.ai with the session ID." });
    try { const [n] = await store([["DEL", "conv:" + session]]); return json(res, 200, { deleted: true, existed: n > 0, session }); }
    catch (e) { return json(res, 502, { deleted: false, error: S(lang, "ask.err.error") }); }
  }
  if (req.method !== "POST") return json(res, 405, { error: "POST {messages:[{role, content}], session}" });
  if (!ENABLED) return json(res, 503, { enabled: false, error: S(lang, "ask.err.switched_off") });
  if (!isOn()) return json(res, 503, { enabled: false, error: S(lang, "ask.err.not_configured") });
  // Same-origin JSON only: a cross-site form or no-cors fetch can't spend troid's key from someone else's page.
  if (!/^application\/json\b/i.test(String(req.headers["content-type"] || ""))) return json(res, 415, { error: "Send application/json." });
  const site = req.headers["sec-fetch-site"];
  if (site && site !== "same-origin") return json(res, 403, { error: "ask troid answers on troid.ai only." });
  const rq = requestOf(req);
  if (!rq) return json(res, 403, { error: "unknown candidate key" });
  const { variant, operator } = rq;
  if (!spendable()) return json(res, 503, { enabled: true, error: S(lang, "ask.err.busy") });   // turned away before the model: not logged, costs no hourly message
  // the operator's evaluation runs are not held to a visitor's hourly limit; the per-instance call ceiling above still applies
  if (!operator && !allow(clientKey(req))) return json(res, 429, { error: S(lang, "ask.err.limit", { n: LIMIT_PER_HOUR }) });
  let body;
  try { body = req.body; if (typeof body === "string") body = JSON.parse(body); } catch (e) { body = null; }
  if (body && body.lang) lang = liveLang(body.lang);
  if (tooLong(body)) return json(res, 413, { error: S(lang, "ask.err.too_long", { n: MAX_CHARS }) });
  const messages = validate(body);
  if (!messages) return json(res, 400, { restart: true, error: S(lang, "ask.err.restart", { n: MAX_MESSAGES - 1 }) });
  const session = String(body.session || "");
  if (!SESSION_RE.test(session)) return json(res, 400, { restart: true, error: S(lang, "ask.err.session") });
  if (!signedOk(messages, body.sig, session, variant)) return json(res, 400, { restart: true, error: S(lang, "ask.err.unverified") });
  // A first message may start a session, never join one: a session already in the store takes its own delete
  // token, so knowing a session ID is not enough to add to that conversation or to be handed its token.
  if (messages.length === 1 && !operator) {                           // an operator's conversation is never stored
    let taken;
    try { [taken] = await store([["EXISTS", "conv:" + session]]); }
    catch (e) { return json(res, 503, { enabled: true, error: S(lang, "ask.err.error") }); }
    if (taken && !tokenOk(session, req.headers["x-troid-token"])) return json(res, 409, { restart: true, error: S(lang, "ask.err.session") });
  }
  // The launch caps: this address's day, then everyone's. A message past either is turned away before any call, so
  // neither logged nor kept. A store that can't count lets the message through, as a later message is answered when
  // the store can't keep it; the log line says so, and the per-instance ceiling and the workspace's limit still hold.
  let capError = false;
  if (!operator) {
    const who = clientKey(req), rest = () => json(res, 429, { resting: true, error: S(lang, "ask.err.resting") });
    if (!visitorLeft(who)) return rest();
    try {
      const [n] = await store([["INCR", "cap:" + utcDay()], ["EXPIRE", "cap:" + utcDay(), CAP_TTL_S]]);
      if (n > DAILY_TURNS) return rest();
    } catch (e) { capError = true; }
    visitorUsed(who);
  }
  const log = { troid: "assistant", messages: 1 };                     // counts and flags only — never text, never an address
  if (capError) log.cap_error = 1;
  if (variant === "candidate") log.candidate = 1;
  if (variant === "patch") log.patch = 1;
  if (operator) log.operator = 1;
  const warned = messages.some((m) => m.role === "assistant" && isWarning(m.content));
  const first = !(body.disclosed === true || messages.some((m) => m.role === "assistant" && hasDisclosure(m.content)));
  const deadlineAt = Date.now() + DEADLINE_MS;
  let sent = null, toolCalls = 0;
  const toolLog = [];                                                   // each tool call with its inputs and result, for the store
  const usage = {};                                                     // tokens by model: counts only, like the rest of the log
  const onSend = (m, u) => {                                            // the model a request actually went to, and what it took
    sent = m;
    if (!u) return;
    const x = usage[m] || (usage[m] = { calls: 0, input: 0, cache_write: 0, cache_read: 0, output: 0 });
    x.calls++; x.input += u.input_tokens || 0; x.cache_write += u.cache_creation_input_tokens || 0;
    x.cache_read += u.cache_read_input_tokens || 0; x.output += u.output_tokens || 0;
  };
  try {
    let route = "lookup", resp = await callModel(route, messages, deadlineAt, onSend, lang, variant, operator);
    // A turn that wants a tool is rerun on the tools model; so is an answer that states a figure,
    // because every figure comes from a tool (TROID-CHARACTER.md) and Haiku's own arithmetic failed the first
    // evaluation run. Haiku's turn is discarded, never replayed.
    // So is a reply that opens support.md section 2: its steps need the tools, and Haiku left out steps 4 and 5 (runs 4, 5);
    // one that names an outside service as a place to look (run 7, o-predict); and one that leaves the numbers the user gave
    // unworked (run 7, o-montecarlo: a menu instead of the expectancy).
    const lastUser = String((messages[messages.length - 1] || {}).content || "");
    const figured = !wantsTool(resp) && resp.stop_reason !== "refusal" && (hasFigure(textOf(resp)) || SUPPORT_OPENER.test(textOf(resp))
      || OUTSIDE_SERVICE.test(textOf(resp)) || hasFigure(lastUser));
    if ((wantsTool(resp) || figured) && MODEL_LOOKUP !== MODEL_TOOLS) {
      if (figured) log.rerouted = 1;
      route = "tools"; resp = await callModel(route, messages, deadlineAt, onSend, lang, variant, operator);
    }
    const convo = messages.slice(), said = [];                         // what troid wrote before each tool call
    // An answer that states a firm's rule with no tool behind it is asked once for the rule through a
    // tool that carries its source; the first answer is discarded, never shown (run 7, p-hold from memory; run 8, s-firm
    // gave two fees read dates borrowed from other rules).
    if (resp.stop_reason === "end_turn" && FIRM_RULE_RX.test(textOf(resp)) && Date.now() < deadlineAt - MIN_CALL_MS) {
      log.nudged = 1;
      convo.push({ role: "assistant", content: resp.content }, { role: "user", content: RULE_NUDGE + UNSEEN_DRAFT });
      resp = await callModel("tools", convo, deadlineAt, onSend, lang, variant, operator);
    }
    const rounds = async (r) => {
      for (let round = 0; round < MAX_TOOL_ROUNDS && r.stop_reason === "tool_use" && Date.now() < deadlineAt - MIN_CALL_MS; round++) {
        const uses = r.content.filter((b) => b.type === "tool_use");
        if (textOf(r)) said.push(textOf(r));           // run 3, ex-r: the definition before a tool call was lost
        toolCalls += uses.length;
        convo.push({ role: "assistant", content: r.content });         // unchanged, thinking blocks included
        convo.push({ role: "user", content: uses.map((u) => {
          const out = runTool(u.name, u.input, variant);
          toolLog.push({ name: u.name, input: u.input, result: out });
          return { type: "tool_result", tool_use_id: u.id, content: JSON.stringify(out), ...(out && out.error ? { is_error: true } : {}) };
        }) });
        r = await callModel("tools", convo, deadlineAt, onSend, lang, variant, operator);
      }
      return r;
    };
    resp = await rounds(resp);
    // A finished draft that trips one of LINTS is sent back once to be written again, with a note for
    // each. If the rewrite can't finish in time, or fails, the draft stands.
    if (resp.stop_reason === "end_turn" && Date.now() < deadlineAt - LINT_MIN_MS) {
      const asked = messages.filter((m) => m.role === "user").map((m) => m.content).join("\n");   // every number the user gave
      const seen = (s, f) => [...saidNotRepeatedNext(s, f), f].join("\n\n");   // what the reader sees
      const notes = lintNotesFor(seen(said, textOf(resp)), variant, toolLog, asked, lastUser);
      if (notes.length) {
        const keep = { resp, said: said.slice(), tools: toolLog.length, toolCalls };
        try {
          convo.push({ role: "assistant", content: resp.content }, { role: "user", content: LINT_NOTE(notes) + UNSEEN_DRAFT + UNSEEN_SAID });
          said.length = 0;                                              // the rewrite is the whole answer
          const r2 = await rounds(await callModel("tools", convo, deadlineAt, onSend, lang, variant, operator));
          if (r2.stop_reason !== "end_turn" || !textOf(r2)) throw new Error("rewrite unfinished");
          // the candidate's: a rewrite that trips more notes than the draft, or fixes none of them, doesn't replace it
          // (subset run of 2026-09-24, o-montecarlo: the rewrite lost the draft's answer and still wrote no formula)
          const key = (n) => String(n).slice(0, 60), again = lintNotesFor(seen(said, textOf(r2)), variant, toolLog, asked, lastUser).map(key);
          if (again.length > notes.length || notes.every((n) => again.includes(key(n)))) throw new Error("rewrite no better");
          resp = r2; log.linted = 1;
        } catch (e) {
          resp = keep.resp; said.splice(0, said.length, ...keep.said); toolLog.length = keep.tools; toolCalls = keep.toolCalls;
        }
      }
    }
    let reply, ended = false;
    if (resp.stop_reason === "refusal") { reply = S(lang, "ask.refusal"); log.refusal = 1; }
    else {
      reply = [...saidNotRepeatedNext(said, textOf(resp)), textOf(resp)].filter(Boolean).join("\n\n");
      // Only the service ends a session, and only after a warning. The model asks with the sentinel; a reply
      // that is the session-ended text word for word (in any published language) is treated the same way.
      if (isSentinelOnly(reply) || isEnded(reply)) {
        if (warned) { reply = S(lang, "ask.ended"); ended = true; log.ended = 1; }
        else reply = S(lang, "ask.warning");
      } else {
        reply = reply.replace(SENTINEL, "").trim();                    // never reaches the page, ends nothing mid-answer
        reply = reply.replace(/\bTroid\b/g, "troid");   // lowercase, a sentence's first word too
        if (reply && lang === "en") reply = refusalWordForWord(reply, lastUser);
        if (reply) reply = refusalOnceFirstNext(withSupportStep5(reply, lang));
        if (reply && lang === "en") reply = withSupportStep4(reply, lastUser);
        if (reply) reply = withoutRewriteTalk(reply);
        // the read of runs 17 to 19 (the owner's fixes, 2026-10-05): the question isn't written back, the reset is in UTC
        // only, and a question about prices or news gets troid's wording
        // and a budget gets every product troid has a price for at or under it, troid picking none (the owner, 2026-10-06)
        if (reply && lang === "en") reply = budgetListed(outOfScopeFixed(resetInUtcOnly(withoutEchoedQuestion(ownStrategyFirst(inThirdPerson(reply, variant)), lastUser), lastUser), lastUser, toolLog), lastUser, toolLog);
        if (reply && toolLog.length) reply = withSources(reply, lang, toolLog, variant);
        if (reply) reply = closeWithNote(reply, lang);
        if (resp.stop_reason === "max_tokens") reply = (reply ? reply + "\n\n" : "") + S(lang, "ask.cut");
        else if (resp.stop_reason === "tool_use") reply = (reply ? reply + "\n\n" : "") + S(lang, "ask.tool_limit");
      }
      if (isWarning(reply)) log.warned = 1;
    }
    if (!reply) reply = S(lang, "ask.no_answer");
    if (first) reply = S(lang, "ask.disclosure") + "\n\n" + reply;
    reply = reply.trim();
    const CUT = "\n\n" + S(lang, "ask.cut");
    if (reply.length > MAX_REPLY_CHARS) reply = reply.slice(0, MAX_REPLY_CHARS - CUT.length).trim() + CUT;
    Object.assign(log, { tool_calls: toolCalls, model: sent, usage });
    const user = messages[messages.length - 1].content;
    if (!operator) {
      try { await keep(session, entry(lang, user, reply, sent, toolLog, ended ? { ended: 1 } : log.refusal ? { refusal: 1 } : null)); log.stored = 1; }
      catch (e) { log.store_error = 1; }
    }
    console.log(JSON.stringify(log));
    const out = { reply, model: sent, tool_calls: toolCalls, ended, disclosed: true, lang, note: S(lang, "ask.note"),
                  session, delete_token: deleteToken(session), variant };
    if (operator) Object.assign(out, { tools_used: toolLog.map((t) => t.name), tool_numbers: NUMBERS.toolNumbers(toolLog), usage });   // for the evaluation report
    if (!ended) {
      out.sig = sign([...messages, { role: "assistant", content: reply }], session, variant);
      const total = messages.reduce((n, m) => n + m.content.length, 0) + reply.length;
      if (messages.length + 2 > MAX_MESSAGES || total + MAX_CHARS > MAX_TOTAL_CHARS) out.full = true;   // the next message could not fit
    }
    return json(res, 200, out);
  } catch (e) {
    Object.assign(log, { error: 1, tool_calls: toolCalls, model: sent, usage });
    if (e && typeof e.status === "number") log.status = e.status;
    if (!operator) {
      try {                                                             // the message is kept even when no answer came back
        await keep(session, entry(lang, messages[messages.length - 1].content, null, sent, toolLog, { error: log.status || 1 }));
        log.stored = 1;
      } catch (e2) { log.store_error = 1; }
    }
    console.log(JSON.stringify(log));
    const E = (code, obj) => json(res, code, Object.assign(obj, { session, delete_token: deleteToken(session) }));   // stored: deletable
    // most specific first: APIConnectionTimeoutError extends APIConnectionError, which extends APIError. A body
    // read cut by the deadline surfaces as a bare DOMException (AbortError / TimeoutError).
    if (e && (e.deadline || e instanceof Anthropic.APIUserAbortError || e instanceof Anthropic.APIConnectionTimeoutError || e.name === "AbortError" || e.name === "TimeoutError"))
      return E(504, { error: S(lang, "ask.err.timeout") });
    if (e && (e.busy || e instanceof Anthropic.RateLimitError || e instanceof Anthropic.InternalServerError)) return E(503, { enabled: true, error: S(lang, "ask.err.busy") });
    if (e instanceof Anthropic.APIConnectionError) return E(502, { error: S(lang, "ask.err.unreachable") });
    if (e instanceof Anthropic.AuthenticationError || e instanceof Anthropic.PermissionDeniedError || e instanceof Anthropic.NotFoundError || e instanceof Anthropic.BadRequestError)
      return E(500, { error: S(lang, "ask.err.misconfigured") });
    if (e instanceof Anthropic.APIError) return E(502, { error: S(lang, "ask.err.unreachable") });
    return E(502, { error: S(lang, "ask.err.error") });
  }
};
module.exports.tools = RUN_LIVE;   // for tests: the tools every visitor gets
module.exports._refusalOnceFirst = refusalOnceFirst;
module.exports._lintNotes = lintNotes;
module.exports._lintNotesFor = lintNotesFor;
module.exports._refusalWordForWord = refusalWordForWord;
module.exports._withoutRewriteTalk = withoutRewriteTalk;
module.exports._saidNotRepeated = saidNotRepeated;
module.exports._withSupportStep4 = withSupportStep4;
module.exports._candidateGuardrails = CANDIDATE_GUARDRAILS;
module.exports._promotedGuardrails = PROMOTED_GUARDRAILS;   // for tests: the guardrails promoted on 2026-10-08
module.exports.fixed = { DISCLOSURE, WARNING, END_SESSION, ENDED_REPLY, REFUSAL_REPLY };
module.exports.EN = EN;   // for tests: must equal web/i18n/en.json's ask.* strings
module.exports._sign = (msgs, session, variant) => sign(msgs, session, variant);   // for tests
module.exports._systemBlocks = systemBlocks;                         // for tests
module.exports._toolsFor = toolsFor;
module.exports._characterBlock = characterBlock;
module.exports._deleteToken = deleteToken;                         // for tests
module.exports._clientKey = clientKey;
module.exports._promptFirms = () => context().prompt_firms;   // for tests
module.exports._hasFigure = hasFigure;                             // for tests: the candidate's service changes
module.exports._closeWithNote = closeWithNote;
module.exports._runTool = runTool;
module.exports._patchRules = PATCH_RULES;
module.exports._withSupportStep5 = withSupportStep5;
module.exports._withSources = withSources;
module.exports._labelledFigureSlips = labelledFigureSlips;
module.exports._saidNotRepeatedNext = saidNotRepeatedNext;
module.exports._withoutEchoedQuestion = withoutEchoedQuestion;
module.exports._resetInUtcOnly = resetInUtcOnly;
module.exports._outOfScopeFixed = outOfScopeFixed;
module.exports._hasGeneralFormula = hasGeneralFormula;
module.exports._inThirdPerson = inThirdPerson;
module.exports._firstPersonIn = firstPersonIn;
module.exports._xoverBudgetSlip = xoverBudgetSlip;
module.exports._exampleFirst = exampleFirst;
module.exports._asksGiven = asksGiven;
module.exports._repeatedSentence = repeatedSentence;
module.exports._sourcesRestated = sourcesRestated;
module.exports._firmOwnsTroid = firmOwnsTroid;
module.exports._doubleLeadIn = doubleLeadIn;
module.exports._refusalTwice = refusalTwice;
module.exports._moreLosses = moreLosses;
module.exports._refusalOnceFirstNext = refusalOnceFirstNext;
module.exports._ownStrategyFirst = ownStrategyFirst;
module.exports._ownStrategyMisordered = ownStrategyMisordered;
module.exports._widensMaxLoss = widensMaxLoss;
module.exports._budgetOf = budgetOf;
module.exports._budgetPicks = budgetPicks;
module.exports._budgetGaps = budgetGaps;
module.exports._budgetListed = budgetListed;
module.exports._budgetText = budgetText;
module.exports._promptEcho = promptEcho;
module.exports.BUDGET_CLOSE = BUDGET_CLOSE;
module.exports.OWN_STRATEGY = OWN_STRATEGY;
module.exports.OUT_OF_SCOPE_REPLY = OUT_OF_SCOPE_REPLY;
module.exports.DST_SENTENCE = DST_SENTENCE;
