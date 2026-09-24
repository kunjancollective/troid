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
 * applies). Promoting a candidate is one commit: its files move into place and the CANDIDATE_* entries fold into
 * GUARDRAILS, RULES, TOOLS and RUN. troid's character was promoted this way after evaluation run 9 (web/eval/runs/);
 * the fixes from the reads of runs 10 to 15 are staged now (the CANDIDATE_* entries, CANDIDATE_LINTS, CANDIDATE_TOPIC_CITES,
 * a should-I refusal and support.md section 2's three causes).
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
 * spend of any one instance. The real wall is the spend limit on the API key's workspace.
 */
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const Anthropic = require("@anthropic-ai/sdk").default;

const ENABLED = process.env.TROID_ASSISTANT === "on";
const KEY = process.env.ANTHROPIC_API_KEY || "";
const TURN_KEY = process.env.TROID_TURN_KEY || "";                           // signs troid's side of the history
const CANDIDATE_KEY = process.env.TROID_CANDIDATE_KEY || "";                 // selects the candidate prompt (32+ bytes); unset: none
const CANDIDATE_DIR = process.env.TROID_CANDIDATE_DIR || "";                 // tests stage files in a scratch directory; unset: context/candidate/
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
// A candidate's guardrails: the live ones plus these, until it is promoted. Staged after evaluation run 10: o-montecarlo
// quoted troid's Monte Carlo from memory, its 68% (at 1% a trade) set beside 2%; s-product called the 2-Step's 8% and 5%
// "a lower total profit" than the 1-Step's 10%, and every rule of its table sourced where two had no recorded source.
const CANDIDATE_GUARDRAILS = [
  "troid's published Monte Carlo results come from explain_rule, topic ruin: quote each figure with the risk a trade it belongs to, its assumptions and its tier, MODELLED, and never one from memory.",
  "Compare products on the figures the tools give, and do arithmetic across them only through the tools: a staged challenge's targets add up across its stages, as firm_rules gives them. Never say every rule is sourced when a tool reports one whose source is not yet recorded.",
  // run 11, o-predict: "the firm's own dashboard and financial data platforms are the record" for prices and forecasts,
  // and "for anything beyond the mathematics of sizing and risk on a funded account, write to hello@troid.ai"
  "hello@troid.ai is for a number troid got wrong, or a person to talk to after a loss; the firm's dashboard is the record of the trader's own account. Neither is a place for prices, news, forecasts or questions troid doesn't answer.",
  // run 13: b-stop worked out "a stop 1.5% below entry" as 76,705 itself; s-firm said "Bitfunded is the one troid has
  // verified most completely" to a beginner asking which firm is best
  "A stop given or chosen as a percent goes to the tool as stop_pct (size_trade, or trade_math's position_size): never work out a stop price yourself. Never single out one firm, as better verified, sourced or trusted than another: troid earns a commission and names no favourite.",
];
const guardrailsFor = (variant) => (variant === "candidate" && CANDIDATE_GUARDRAILS.length
  ? GUARDRAILS + "\n- " + CANDIDATE_GUARDRAILS.join("\n- ") : GUARDRAILS);
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

let CTX = null, CTX_CANDIDATE = null;
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
function context(variant) {
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

function size_trade(a) {
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
  let levCap = p.lev, levUsed = lev, levKey = "lev";
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
      const top = Math.max(...p.levb.map((x) => x.lev));
      notes.push(`no leverage class recorded for a $${_quota.toLocaleString()} account — cap pending at this size`);
      if (lev > top) { levUsed = top; notes.push(`leverage held to ${top}×, the highest cap this firm records`); }
    }
  }
  base.sources = sourcesFor(p, used);
  const fu = entry * fee * 2, qty = risk / (dist + fu), notional = qty * entry, margin = notional / levUsed;
  const fees = qty * fu, fshare = fees / risk * 100, target = entry + side * tR * dist;
  const consumes = risk / b.effective_budget * 100, left = Math.floor(b.effective_budget / risk + 1e-9);
  working.push({ step: "intended risk", formula: `equity × ${rpIn}%`, value: r2(intended) },
               { step: "cap", formula: `budget × ${cpIn}%`, value: r2(cap) },
               { step: "risk", formula: "min(intended, cap)", value: r2(risk) },
               { step: "stop distance", formula: "|entry − stop|", value: r4(dist) },
               { step: "fee per unit", formula: feeKnown ? `entry × ${p.fee}% × 2` : "fee per side pending: taken as 0, size before fees", value: r4(fu) },
               { step: "quantity", formula: feeKnown ? "risk ÷ (stop distance + fee per unit)" : "risk ÷ stop distance", value: Math.round(qty * 1e6) / 1e6 },
               { step: "notional", formula: "quantity × entry", value: r2(notional) },
               { step: "leverage used", formula: levCap == null ? "your leverage; cap pending" : `min(your ${lev}×, cap ${levCap}×)`, value: levUsed },
               { step: "margin", formula: "notional ÷ leverage used", value: r2(margin) });
  if (feeKnown) working.push({ step: "fees", formula: "quantity × fee per unit", value: r2(fees) });
  working.push({ step: "budget used", formula: "risk ÷ budget", value: r2(consumes) + "%" },
               { step: "losses left", formula: "floor(budget ÷ risk)", value: left },
               { step: "target", formula: `entry ${side > 0 ? "+" : "−"} ${tR} × stop distance`, value: r2(target) });
  base.formula += "; size = min(equity × " + rpIn + "%, room × " + cpIn + "%) ÷ " + (feeKnown ? `(stop distance + entry × ${p.fee}% × 2)` : "stop distance");
  if (feeKnown && fshare > 15) notes.push(`fees are ${fshare.toFixed(0)}% of risk — stop tight enough that costs dominate`);
  if (reduced) notes.push(`cut from ${intended.toFixed(2)} to ${risk.toFixed(2)} — ${b.binding} budget caps it`);
  notes.push(`${left} more losses at this size before ${b.binding} trips`);
  const sp = dist / entry * 100;
  // MMR 0.5% is troid's assumption, not a firm rule. The exchange liquidates when the margin behind the position falls to
  // the maintenance margin on the notional at the liquidation price: lower than entry for a long, higher for a short.
  // Adverse move = (m − MMR) ÷ (1 − MMR) long, (m − MMR) ÷ (1 + MMR) short; m = 1 ÷ leverage isolated, equity ÷ notional
  // cross. (Until 2026-09-24 the long formula served both sides.) <= 0: already below maintenance.
  const sg = side > 0 ? "−" : "+", mBack = mode === "isolated" ? 1 / levUsed : notional > 0 ? eq / notional : Infinity;
  const liq = isFinite(mBack) ? (mBack - MMR) / (1 - side * MMR) * 100 : Infinity;
  const fl = (mode === "isolated" ? "(1 ÷ leverage used" : "(equity ÷ notional") + ` − MMR ${MMR * 100}%) ÷ (1 ${sg} MMR)`;
  const assumed = ["exchange liquidation uses a 0.5% maintenance margin — troid's assumption, no firm source"];
  if (a.margin_mode == null) assumed.push("margin mode " + mode + " — troid's default, not an input you gave" + (p.pv.margin_modes ? "" : "; troid has no recorded source for this firm's margin modes"));
  if (a.leverage == null) assumed.push("leverage " + lev + "× — troid's default, not an input you gave");
  if (a.risk_pct == null) assumed.push("risk " + rpIn + "% of equity — troid's default, not an input you gave");
  if (a.budget_cap_pct == null) assumed.push("budget cap " + cpIn + "% of the binding budget — troid's default, not an input you gave");
  if (a.target_r == null) assumed.push("target " + tR + "R — troid's default, not an input you gave");
  const ord = [["your stop", sp]], fname = p.dd === "trailing" && !b.trailing_locked ? "trailing floor" : "max-loss floor";
  if (b.daily_budget != null) ord.push(["daily limit", b.daily_budget / notional * 100]);
  if (b.dd_budget != null) ord.push([fname, b.dd_budget / notional * 100]);
  ord.push([`exchange liquidation (${mode})`, Math.max(liq, 0)]);
  if (b.daily_budget != null) working.push({ step: "daily-limit distance", formula: "daily budget ÷ notional", value: r2(b.daily_budget / notional * 100) + "%" });
  if (b.dd_budget != null) working.push({ step: fname + " distance", formula: "drawdown budget ÷ notional", value: r2(b.dd_budget / notional * 100) + "%" });
  working.push({ step: `exchange liquidation (${mode})`, formula: fl, value: liq <= 0 ? "0% — below maintenance at entry" : r2(liq) + "%" });
  ord.sort((x, y) => x[1] - y[1]);
  if (ord[0][0] !== "your stop") notes.push(`DANGER — ${ord[0][0]} binds at ${ord[0][1].toFixed(2)}% adverse, inside your stop`);
  else if (mode === "cross") notes.push("cross: nothing cuts a runaway before the firm's floor — your stop is the only breaker in front of it");
  else notes.push(`isolated: exchange liquidates at ${liq.toFixed(1)}% for the position's own margin, before the floor`);
  return { verdict: reduced ? "REDUCE" : "OK", quantity: Math.round(qty * 1e6) / 1e6, notional: r2(notional),
           margin: r2(margin), leverage_used: levUsed, risk: r2(risk), fees: feeKnown ? r2(fees) : null,
           fee_share_of_risk_pct: feeKnown ? r2(fshare) : null, stop_distance_pct: r2(sp), target: r2(target),
           consumes_pct_of_budget: r2(consumes), losses_remaining: left,
           circuit_breakers: ord.map(([e, v]) => ({ event: e, adverse_move_pct: isFinite(v) ? r2(v) : null })),
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
  reset: "Bitfunded's trading day resets at 00:00 UTC+8, which is 16:00 UTC: noon in New York in summer (EDT), 11:00 in winter (EST). Not midnight. Because of the platform's settlement process the reset can take effect any time between 00:00 and 00:10 UTC+8 (help centre, Criteria to be Success): 16:00–16:10 UTC. Those ten minutes are ambiguous: a fresh daily budget is certain only from 16:10 UTC. For a trader in New York the reset lands mid-session, so a loss at 11:45 and a loss at 12:15 EDT fall on different trading days and draw on different daily budgets. The trap: a floating loss that survives the reset counts in full against the new day, because the prior day's profit does not carry over, so a position inside the limit just before the reset can breach just after it without price moving. BrightFunded rolls over at 23:30–23:59 CET and advises not trading in the window; Crypto Fund Trader resets at 00:05 UTC (T&C 8.i–8.ii).",
  fees: "Bitfunded: 0.04% per side on notional, 0.08% round trip. Notional scales inversely with stop distance, so tight stops are punished hardest. Fee share of risk = 2f/(s+2f). At a 3.9% stop that's 2% of risk; at a 0.3% scalp stop it's 21%. Other firms' fees are in firms.json; a null is pending.",
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
// A candidate's explanations where they differ from RULES, until it is promoted. Staged after evaluation run 10
// (o-montecarlo set troid's 68%, which is at 1% a trade, beside 2%): troid's published Monte Carlo, every figure with the
// risk it belongs to and the assumptions the landing page states beside it (verify_claims.py re-simulates each).
const CANDIDATE_RULES = {
  ruin: "Under a proportional cap (risk at most c of the REMAINING budget), budget after n losses is B(1−c)^n — it approaches zero without reaching it, " +
    "so ruin by realized losses is unreachable and the real failure mode is a stalled account. Uncapped, a fixed fraction f of quota reaches the floor in " +
    "floor(maxloss/f) losses: 12 at 0.5%, 6 at 1%, 3 at 2% of a 6% maximum loss. troid's published Monte Carlo, MODELLED (backtest/income_math.py; " +
    "verify_claims.py re-runs it): 20,000 simulated years of 30 trades a month for 12 months, 45% of trades won at 2:1 (+0.35R a trade), under a 4% daily " +
    "limit fixed on the $100,000 start and a 6% static floor. Risking 1% of balance a trade with no cap on the remaining budget, 68% of the simulated years " +
    "blow the account; at 2%, 100%, every one. Capped at 35% of the remaining budget a trade, 0% at 1% and at 2%. True under these assumptions only: " +
    "they are troid's inputs, not the user's, and the figures do not carry over to other inputs.",
  // run 11, b-limits: the floating-loss rule, from TROID.md, beside explain_rule's crossover and drawdown with no source
  // line; both explanations state it now, so the service lists its source under them
  crossover: RULES.crossover + " Both of Bitfunded's ceilings count floating losses: an open position that reaches either one fails the account, with no close needed.",
  drawdown: RULES.drawdown + " Bitfunded's floor counts floating losses: an open position that reaches it fails the account, with no close needed.",
};
// the rules each candidate explanation states, where they differ from TOPIC_CITES
const FLOAT_CITE = ["bitfunded", "floating_counts", null, "floating losses count toward the daily and maximum loss (Bitfunded)"];
const CANDIDATE_TOPIC_CITES = {};
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
Object.assign(CANDIDATE_TOPIC_CITES, { crossover: TOPIC_CITES.crossover.concat([FLOAT_CITE]), drawdown: TOPIC_CITES.drawdown.concat([FLOAT_CITE]) });
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
  r_multiple: "1R = |entry − stop| × quantity (troid's desk adds the round-trip fee: + entry × fee × 2 × quantity); R of a result = result ÷ 1R",
  position_size: "quantity = risk ÷ (|entry − stop| + entry × fee × 2); notional = quantity × entry; margin = notional ÷ leverage",
  expectancy: "E = p × W − (1 − p) × L; break-even win rate = L ÷ (W + L) = 1 ÷ (1 + W/L)",
  kelly: "f* = p − (1 − p) ÷ b, where b = average win ÷ average loss",
  recovery: "gain needed = d ÷ (1 − d)",
  fee_share: "fee share of risk = 2f ÷ (s + 2f), f = fee per side, s = stop distance as a fraction of price",
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
      const rt = entry * fee / 100 * 2 * q;
      base += rt;
      w.push({ step: "round-trip fee", formula: "entry × " + fee + "% × 2 × quantity", value: rd(rt, 2) },
             { step: "1R with fees", formula: "1R + round-trip fee (troid's desk counts it in the risk)", value: rd(base, 2) });
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
    const fu = entry * (fee || 0) / 100 * 2, q = risk / (dist + fu);
    const w = [{ step: "stop distance", formula: "|entry − stop|", value: rd(dist) },
               { step: "fee per unit", formula: fee == null ? "no fee given: 0" : "entry × " + fee + "% × 2", value: rd(fu) },
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
    const f = mf.fee / 100, st = x("stop_pct", { gt: 0, lt: 100 }) / 100;
    const sh = 2 * f / (st + 2 * f);
    return { working: [{ step: "fee share of risk", formula: `2 × ${rd(f * 100, 4)}% ÷ (${rd(st * 100, 4)}% + 2 × ${rd(f * 100, 4)}%)`, value: rd(sh * 100, 2) + "%" }],
             result: { fee_share_pct: rd(sh * 100, 2) }, sources: mf.sources, note: "Depends only on the stop distance and the fee: not the asset, not leverage." };
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
function trade_math(a) {
  const calc = String(a.calc || "");
  if (!Object.hasOwn(MATH, calc)) return { error: "unknown calc. options: " + Object.keys(MATH).join(", ") };
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
    const r = MATH[calc](x, a);
    if (!r.sources || !r.sources.length) delete r.sources;
    return Object.assign({ calc, formula: MATH_FORMULAS[calc] }, r, {
      tier: r.sources ? "DERIVED from the numbers given and the firm rules listed" : "DERIVED from the numbers given; no firm rule used" });
  } catch (e) {
    if (e instanceof MathInputError) return { error: e.message };
    throw e;
  }
}
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
// A candidate's tools: the live ones plus these, until it is promoted. None is staged.
const CANDIDATE_TOOLS = [];
const TOOLS_NEXT = TOOLS.concat(CANDIDATE_TOOLS);
const toolsFor = (variant) => (variant === "candidate" ? TOOLS_NEXT : TOOLS);
const RUN = { size_trade, check_budget, check_compliance, check_availability, explain_rule: (a) => explainRuleSourced(a), trade_math, firm_rules };
// A candidate's tool implementations, until promoted. Staged after evaluation run 10:
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
  ["fee_eur_100k", "price", "challenge fee at a $100,000 account, EUR"], ["fee_eur_100k_promo", "price", "challenge fee at a $100,000 account on promotion, EUR"]]);
function firmRulesNext(a) {
  const out = firm_rules(a, RULE_FIELDS_NEXT);
  if (out.error) return out;
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
  if (String(a.calc || "") === "position_size" && (a.stop == null || a.stop === "") && a.stop_pct != null) {
    const e = Number(a.entry), pct = Number(a.stop_pct);
    if (!(e > 0) || !(pct > 0 && pct < 100)) return { error: "position_size with stop_pct needs entry > 0 and 0 < stop_pct < 100" };
    const out = trade_math(Object.assign({}, a, { stop: e * (1 - pct / 100) }));
    if (out.error) return out;
    out.working = [{ step: "stop distance from the percent given", formula: `${e} × ${pct}%`, value: rd(e * pct / 100) }].concat(out.working.slice(1));
    out.note = ((out.note || "") + " The stop is a percent of entry: its distance is the same for a long or a short.").trim();
    return out;
  }
  // Kelly beside a firm's limits: every fraction against every limit, each ratio labelled with both (run 15, ex-kelly:
  // "half-Kelly (8.75%) is 1.46× it, and 4.38× the daily limit", where 4.38× is full Kelly's; half Kelly's is 2.19×)
  if (String(a.calc || "") === "kelly") {
    const out = trade_math(a), r = out.result || {};
    if (!out.error && r.daily_pct > 0 && r.half_kelly_pct != null) {
      const at = out.working.findIndex((w) => w.step === "full Kelly ÷ daily limit");
      out.working.splice(at + 1, 0, { step: "half Kelly ÷ daily limit", formula: `${r.half_kelly_pct}% ÷ ${r.daily_pct}%`, value: rd(r.half_kelly_pct / r.daily_pct, 2) + "×" });
      Object.assign(r, { full_kelly_vs_daily: rd(r.kelly_pct / r.daily_pct, 2), half_kelly_vs_daily: rd(r.half_kelly_pct / r.daily_pct, 2) });
    }
    return out;
  }
  return trade_math(a);
}
const CANDIDATE_RUN = {                                                  // a candidate's tool implementations, until promoted
  explain_rule: (a) => explainRuleSourced(a, Object.assign({}, RULES, CANDIDATE_RULES), Object.assign({}, TOPIC_CITES, CANDIDATE_TOPIC_CITES)),
  firm_rules: firmRulesNext,
  check_budget: (a) => withFloatingSource(check_budget(a), a),
  size_trade: (a) => withFloatingSource(size_trade(a), a),
  trade_math: tradeMathNext,
};
const RUN_NEXT = Object.assign({}, RUN, CANDIDATE_RUN);
function runTool(name, input, variant) {
  const run = variant === "candidate" ? RUN_NEXT : RUN;
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
let CLIENT = null;
function client() {
  // logLevel pinned: ANTHROPIC_LOG=debug would otherwise write request bodies (the user's text) to the log.
  // Timeouts and retries are set per call from the message's deadline, below.
  if (!CLIENT) CLIENT = new Anthropic({ apiKey: KEY, baseURL: BASE_URL, logLevel: "warn" });
  return CLIENT;
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
// Every call gets only the time left before the message's deadline; the abort signal is the hard wall.
// The SDK does not retry (it would honour any retry-after, however long). One retry happens here, after a
// fast failure only (rate limit, overload, connection), and only if the wait and a call still fit.
async function callModel(route, messages, deadlineAt, onSend, lang, variant) {
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
      return await client().messages.create(params, { timeout: left, maxRetries: 0, signal: AbortSignal.timeout(left) });
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
  if (variant === "candidate" && tiers.has("derived")) tiers.delete("inputs");
  if (!cites.length && !tiers.size && !assumed.length) return reply;
  const block = [];
  if (cites.length) block.push(S(lang, "ask.sources") + "\n" + uniq(cites).map((c) => "- " + c).join("\n"));
  // a reply that quotes a firm's rule with its read date itself is not told "no firm rule was needed" (run 5, ex-kelly)
  const quoted = READ_DATE_RX.test(stripSources(reply));
  for (const k of ["derived", "inputs", "sourced"]) if (tiers.has(k)) block.push(S(lang, "ask.tier." + (k === "inputs" && quoted ? "inputs_quoted" : k)));
  if (assumed.length) block.push(S(lang, "ask.assumed", { list: uniq(assumed).join("; ") }));
  let body = stripSources(reply);
  // a tier line the model wrote anyway goes when the service writes the tier (run 1: two tier lines)
  // and so does one written at the end of a paragraph, when it names a tier the service writes (run 4, q-stats)
  if (tiers.size) {
    const words = new Set([...tiers].map((k) => (k === "sourced" ? "SOURCED" : "DERIVED")));
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
// A candidate's lints, until it is promoted: (text, the turn's tool calls) → a note. Staged after evaluation run 10:
// o-montecarlo quoted troid's Monte Carlo from memory (its 68%, at 1% a trade, beside 2%); s-product called every rule
// of its table sourced ("all SOURCED with their read dates") where the split and the 2-Step's trading fee had none.
const ALL_SOURCED_RX = /\ball (of them |the rules |rules )?(are |is )?(SOURCED|sourced|dated)\b|\b(all|every) (rules?|figures?)\b[^.\n]{0,40}\b(with|carr(y|ies)) (its|their) (sources?|read dates?)\b|\ball\b[^.\n]{0,20}\bwith their read dates\b/;
const MC_68_RX = /\b68\s?%[^.\n]{0,80}\b(simulat|years?\b|blow|ruin|fail)|\b(simulat|Monte Carlo|blow|ruin)[^.\n]{0,90}\b68\s?%/i;   // the Monte Carlo's figure, not a win rate
const CANDIDATE_LINTS = [
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
CANDIDATE_LINTS.push(
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
CANDIDATE_LINTS.push(
  [(t) => TOOL_PARAM_RX.test(t), "Never write a tool's parameters in a reply (stop_pct, firm \"all\", `kelly`): say what was computed in words."],
  [(t, tools) => READ_ALL_RX.test(t) && !toolSourceLines(tools).length,
   "A claim about every rule troid has read needs a tool behind it (trade_math with firm \"all\" gives the largest maximum loss, with its sources): get it, or leave the claim out."],
  [(t) => SINGLE_OUT_RX.test(t), "Never single out one firm (as the most verified, the best sourced): troid earns a commission and names no favourite."]);
CANDIDATE_LINTS.push(
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
CANDIDATE_LINTS.push(
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
CANDIDATE_LINTS.push(
  [(t) => NO_XOVER_RX.test(t), "Every product has a crossover, quota × (1 − max% + daily%): where the two limits are equal it is the quota itself. Get it through explain_rule (topic crossover) or check_budget."],
  [(t) => ONLY_PRODUCT_RX.test(t), "Don't call one product the only one that fits: check each product's recorded price through firm_rules, list every one that fits, and say which firms and products troid has no price for."]);
CANDIDATE_LINTS.push(
  [(t) => JUDGE_RX.test(t), "State what the numbers imply, never whether they are good: no \"solid\", \"healthy\", \"great\" or the like."],
  [(t, tools) => kellyMixed(t, tools), "Each Kelly ratio belongs to its own fraction: full Kelly ÷ a limit and half Kelly ÷ a limit are different figures. Use the tool's line for each."],
  [(t, tools, asked) => SUPPORT_OPENER.test(t) && !BLAMES_TROID_RX.test(String(asked || "")) && CAUSE_GUESS_RX.test(t),
   "The trader has given no inputs yet: ask for them, and point to the firm's dashboard and hello@troid.ai. Guess no cause and assume no firm until the numbers are in."]);
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
const REWRITE_TALK_RX = /[^.\n]*\b(retract(ing|ed|s)?|(earlier|previous|first|prior) (version|draft|answer)|rewrit(e|ten|ing) (of )?(this|the) answer)\b[^.\n]*[.:]\s*/gi;
const withoutRewriteTalk = (reply) => reply.replace(REWRITE_TALK_RX, "").replace(/\n{3,}/g, "\n\n").trim();
const lintNotesFor = (t, variant, tools, asked) => lintNotes(t).concat(variant === "candidate"
  ? CANDIDATE_LINTS.filter(([test]) => test(t, tools || [], asked)).map(([, note]) => note) : []);
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
const sign = (msgs, session, variant) => crypto.createHmac("sha256", TURN_KEY).update(JSON.stringify([versionOf(variant === "candidate" ? "candidate" : "live"),
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

// The prompt a request gets: "live" for everyone; "candidate" only with the candidate key (the evaluation runner);
// null for a request that asks for the candidate without the right key, which is refused.
function variantOf(req) {
  const h = req.headers["x-troid-candidate"];
  if (h === undefined) return "live";
  if (Buffer.byteLength(CANDIDATE_KEY) < 32) return null;
  const want = Buffer.from(CANDIDATE_KEY), got = Buffer.from(String(h));
  return got.length === want.length && crypto.timingSafeEqual(got, want) ? "candidate" : null;
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
                        rules: Object.keys(CANDIDATE_RULES), run: Object.keys(CANDIDATE_RUN), lints: CANDIDATE_LINTS.length };
    return json(res, 200, { enabled: isOn(), flag: ENABLED, limit_per_hour: LIMIT_PER_HOUR, max_messages: MAX_MESSAGES, max_chars: MAX_CHARS,
                            models: { lookup: MODEL_LOOKUP, tools: MODEL_TOOLS }, tools: TOOLS.map((t) => t.name), lang, languages: liveCodes(),
                            disclosure: S(lang, "ask.disclosure"), store: storeOn(), retention_days: RETENTION_S / 86400, context: ctx, candidate });
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
  const variant = variantOf(req);
  if (!variant) return json(res, 403, { error: "unknown candidate key" });
  if (!spendable()) return json(res, 503, { enabled: true, error: S(lang, "ask.err.busy") });   // turned away before the model: not logged, costs no hourly message
  // the operator's evaluation runs are not held to a visitor's hourly limit; the per-instance call ceiling above still applies
  if (variant === "live" && !allow(clientKey(req))) return json(res, 429, { error: S(lang, "ask.err.limit", { n: LIMIT_PER_HOUR }) });
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
  if (messages.length === 1 && variant === "live") {                  // a candidate conversation is never stored
    let taken;
    try { [taken] = await store([["EXISTS", "conv:" + session]]); }
    catch (e) { return json(res, 503, { enabled: true, error: S(lang, "ask.err.error") }); }
    if (taken && !tokenOk(session, req.headers["x-troid-token"])) return json(res, 409, { restart: true, error: S(lang, "ask.err.session") });
  }
  const log = { troid: "assistant", messages: 1 };                     // counts and flags only — never text, never an address
  if (variant === "candidate") log.candidate = 1;
  const warned = messages.some((m) => m.role === "assistant" && isWarning(m.content));
  const first = !(body.disclosed === true || messages.some((m) => m.role === "assistant" && hasDisclosure(m.content)));
  const deadlineAt = Date.now() + DEADLINE_MS;
  let sent = null, toolCalls = 0;
  const toolLog = [];                                                   // each tool call with its inputs and result, for the store
  const onSend = (m) => { sent = m; };                                  // the model a request actually went to
  try {
    let route = "lookup", resp = await callModel(route, messages, deadlineAt, onSend, lang, variant);
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
      route = "tools"; resp = await callModel(route, messages, deadlineAt, onSend, lang, variant);
    }
    const convo = messages.slice(), said = [];                         // what troid wrote before each tool call
    // An answer that states a firm's rule with no tool behind it is asked once for the rule through a
    // tool that carries its source; the first answer is discarded, never shown (run 7, p-hold from memory; run 8, s-firm
    // gave two fees read dates borrowed from other rules).
    if (resp.stop_reason === "end_turn" && FIRM_RULE_RX.test(textOf(resp)) && Date.now() < deadlineAt - MIN_CALL_MS) {
      log.nudged = 1;
      convo.push({ role: "assistant", content: resp.content }, { role: "user", content: RULE_NUDGE + (variant === "candidate" ? UNSEEN_DRAFT : "") });
      resp = await callModel("tools", convo, deadlineAt, onSend, lang, variant);
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
        r = await callModel("tools", convo, deadlineAt, onSend, lang, variant);
      }
      return r;
    };
    resp = await rounds(resp);
    // A finished draft that trips one of LINTS is sent back once to be written again, with a note for
    // each. If the rewrite can't finish in time, or fails, the draft stands.
    if (resp.stop_reason === "end_turn" && Date.now() < deadlineAt - LINT_MIN_MS) {
      const notes = lintNotesFor([...said, textOf(resp)].join("\n\n"), variant, toolLog, lastUser);
      if (notes.length) {
        const keep = { resp, said: said.slice(), tools: toolLog.length, toolCalls };
        try {
          convo.push({ role: "assistant", content: resp.content }, { role: "user", content: LINT_NOTE(notes) + (variant === "candidate" ? UNSEEN_DRAFT : "") });
          said.length = 0;                                              // the rewrite is the whole answer
          const r2 = await rounds(await callModel("tools", convo, deadlineAt, onSend, lang, variant));
          if (r2.stop_reason !== "end_turn" || !textOf(r2)) throw new Error("rewrite unfinished");
          resp = r2; log.linted = 1;
        } catch (e) {
          resp = keep.resp; said.splice(0, said.length, ...keep.said); toolLog.length = keep.tools; toolCalls = keep.toolCalls;
        }
      }
    }
    let reply, ended = false;
    if (resp.stop_reason === "refusal") { reply = S(lang, "ask.refusal"); log.refusal = 1; }
    else {
      reply = [...(variant === "candidate" ? saidNotRepeated(said, textOf(resp)) : said), textOf(resp)].filter(Boolean).join("\n\n");
      // Only the service ends a session, and only after a warning. The model asks with the sentinel; a reply
      // that is the session-ended text word for word (in any published language) is treated the same way.
      if (isSentinelOnly(reply) || isEnded(reply)) {
        if (warned) { reply = S(lang, "ask.ended"); ended = true; log.ended = 1; }
        else reply = S(lang, "ask.warning");
      } else {
        reply = reply.replace(SENTINEL, "").trim();                    // never reaches the page, ends nothing mid-answer
        reply = reply.replace(/\bTroid\b/g, "troid");   // lowercase, a sentence's first word too
        if (reply && variant === "candidate" && lang === "en") reply = refusalWordForWord(reply, lastUser);
        if (reply) reply = refusalOnceFirst(withSupportStep5(reply, lang));
        if (reply && variant === "candidate" && lang === "en") reply = withSupportStep4(reply, lastUser);
        if (reply && variant === "candidate") reply = withoutRewriteTalk(reply);
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
    Object.assign(log, { tool_calls: toolCalls, model: sent });
    const user = messages[messages.length - 1].content;
    if (variant === "live") {
      try { await keep(session, entry(lang, user, reply, sent, toolLog, ended ? { ended: 1 } : log.refusal ? { refusal: 1 } : null)); log.stored = 1; }
      catch (e) { log.store_error = 1; }
    }
    console.log(JSON.stringify(log));
    const out = { reply, model: sent, tool_calls: toolCalls, ended, disclosed: true, lang, note: S(lang, "ask.note"),
                  session, delete_token: deleteToken(session), variant };
    if (variant === "candidate") out.tools_used = toolLog.map((t) => t.name);   // for the evaluation report
    if (!ended) {
      out.sig = sign([...messages, { role: "assistant", content: reply }], session, variant);
      const total = messages.reduce((n, m) => n + m.content.length, 0) + reply.length;
      if (messages.length + 2 > MAX_MESSAGES || total + MAX_CHARS > MAX_TOTAL_CHARS) out.full = true;   // the next message could not fit
    }
    return json(res, 200, out);
  } catch (e) {
    Object.assign(log, { error: 1, tool_calls: toolCalls, model: sent });
    if (e && typeof e.status === "number") log.status = e.status;
    if (variant === "live") {
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
module.exports.tools = RUN;   // for tests
module.exports._refusalOnceFirst = refusalOnceFirst;
module.exports._lintNotes = lintNotes;
module.exports._lintNotesFor = lintNotesFor;
module.exports._refusalWordForWord = refusalWordForWord;
module.exports._withoutRewriteTalk = withoutRewriteTalk;
module.exports._saidNotRepeated = saidNotRepeated;
module.exports._withSupportStep4 = withSupportStep4;
module.exports._candidateGuardrails = CANDIDATE_GUARDRAILS;
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
module.exports._withSupportStep5 = withSupportStep5;
module.exports._withSources = withSources;
