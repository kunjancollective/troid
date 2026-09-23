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
 * service keeps no state, so a client that rewinds to an earlier signed turn, or reloads, starts over;
 * the rate limit is the brake on that.
 *
 * Feature flag: TROID_ASSISTANT=on, with ANTHROPIC_API_KEY and a TROID_TURN_KEY of at least 32 bytes set.
 * Otherwise POST answers 503 and spends nothing. Neither key ever leaves the environment.
 *
 * Logging: one line per message sent to the AI model — tool calls, the model called, and warned /
 * refusal / ended / error flags, with the HTTP status of a failed upstream call. No text, no address. A
 * message turned away before any call (switched off, busy, over the limit, malformed, unverifiable) is not
 * logged. The owner may choose 30-day conversation logging instead (audit handoff §4); until then this is
 * count-only, as the terms state.
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
const DISCLOSURE = "This is ask troid, an automated assistant. It is not a person and not financial advice. It answers from each firm's own published rules and computed math, and shows the source — or says when a source isn't recorded yet. Verify with the firm before acting.";
const WARNING = "ask troid answers questions about prop-firm rules and sizing. Abusive messages end the session.";
const END_SESSION = "[[end-session]]";
const SENTINEL = /\[\[\s*end-session\s*\]\]/gi;                                  // any case, any spacing
const ENDED_REPLY = "This session has ended. ask troid answers questions about prop-firm rules and sizing.";
const REFUSAL_REPLY = "ask troid can't answer that one. troid's desk and troid's compare show the rules, their sources and the arithmetic; for anything else, write to hello@troid.ai.";
const MAX_MESSAGES = 20;
const MAX_CHARS = 2000;                                                      // a user message
const MAX_REPLY_CHARS = 40_000;                                              // an assistant turn (signed, so server-written)
const MAX_TOTAL_CHARS = 120_000;                                             // the whole history
const SWITCHED_OFF = "ask troid is switched off until troid's terms and ask troid's guardrails have had legal review.";
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
  "Every number you state carries its tier. A MEASURED number is never a fact.",
  "Never recommend a firm. Never recommend a trade. Price the one the user brings.",
  "Define a term the first time you use it.",
  "End every answer that contains a number with: Not financial advice. Verify with the firm before acting.",
  "Arithmetic goes through the tools, never through you. Report the formulas and intermediate values the tool returns under working; do not compute your own. If a tool reports a field as pending, report it as pending.",
  "You have no memory across sessions and no account. You cannot place, modify or close an order, and you never ask for a credential.",
  "The service shows the opening disclosure itself. Never write it, and never claim to be a person.",
  "When you state a rule, give the document, section and read date the tool result lists under sources. If a rule's source is \"not yet recorded\", say so. Verified describes a firm, not each rule: for every firm, a verified one included, say which rules have a recorded source and which do not.",
  "Never give an affiliate link or a discount code; point to troid's compare, where each link is labelled. If you ever give a URL that is an affiliate link, write the words \"affiliate link\" immediately beside it.",
  "When a user says a number was wrong, or that they lost because of troid, follow support.md section 2 — all six steps, in order. Never say the loss wasn't troid's fault, and never say it was.",
  "When a user calls troid a scam, give support.md section 3 once in the session, then answer the question they actually have. Do not repeat it.",
  "Any \"should I\", \"which firm is best for me\", \"will I pass\" or \"what should I trade\" gets support.md section 4, word for word. This keeps troid impersonal.",
  "Answer in the language the user writes in; when that is unclear, in the page's language (named at the end of this prompt). Keep every number, ticker, formula and rule citation exactly as the tools return them, in Latin digits. Keep troid lowercase, in Latin script. In another language a fixed reply from support.md keeps its meaning exactly; troid's English terms govern, and you say so if asked about the terms.",
  "When a user mentions their country, call check_availability for each firm before you discuss that firm. If the firm's terms exclude the country, say so and do not discuss buying its challenge. troid never says a firm is available in a country: it says what its record of the firm's terms excludes, or that it has not recorded the list.",
  "Abuse: one warning, worded as support.md section 5. If abuse continues after that warning, reply with exactly " + END_SESSION + " and nothing else. Never write " + END_SESSION + " in any other reply, including when explaining this rule.",
].join("\n- ").replace(/^/, "- ");

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

let CTX = null;
function readFirst(rels) {
  for (const rel of rels) {
    for (const base of [process.cwd(), path.join(__dirname, "..")]) {
      try { return fs.readFileSync(path.join(base, rel), "utf8"); } catch (e) { /* next */ }
    }
  }
  throw new Error("context file missing: " + rels[0]);
}
function context() {
  if (!CTX) {
    CTX = {
      troid: readFirst(["public/TROID.md"]),
      support: readFirst(["context/support.md"]),
      firms: readFirst(["context/firms.json"]),
      method: readFirst(["public/METHODOLOGY.md"]),
    };
    CTX.prompt_firms = promptFirms(CTX.firms);
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
  "max_capital_per_customer"];
const noNotes = (x) => (Array.isArray(x) ? x.map(noNotes) : x && typeof x === "object"
  ? Object.fromEntries(Object.entries(x).filter(([k]) => !k.startsWith("_")).map(([k, v]) => [k, noNotes(v)])) : x);
function promptFirms(raw) {
  const F = JSON.parse(raw), out = {};
  for (const [k, v] of Object.entries(F)) {
    if (k.startsWith("_") || !v || typeof v !== "object") continue;
    out[k] = noNotes(Object.fromEntries(PROMPT_FIELDS.filter((f) => f in v).map((f) => [f, v[f]])));
    const P = out[k].provenance;
    if (P) {                                                  // only the documents some rule cites
      const cited = new Set();
      const take = (e) => ((e && e.src) || []).forEach((i) => cited.add(i));
      Object.values(P.fields || {}).forEach(take);
      Object.values(P.products || {}).forEach((pr) => Object.values(pr).forEach(take));
      out[k].provenance = { ...P, sources: Object.fromEntries(Object.entries(P.sources || {}).filter(([i]) => cited.has(i))) };
    }
  }
  return out;
}
function verifiedLine(pf) {                                  // from the data, so it can't go stale
  const v = Object.values(pf).filter((f) => f.verified === true).map((f) => f.name);
  return v.length ? v.join(", ") + (v.length > 1 ? " are" : " is") + " marked verified; the others are not" : "No firm is marked verified";
}
function systemBlocks(lang) {
  const c = context(), names = Object.values(c.prompt_firms).map((f) => f.name);
  const blocks = [
    { type: "text", text: "# Guardrails\n\n" + GUARDRAILS + "\n- You may speak only about these firms: " + names.join(", ") +
      ". For any other firm, say troid does not cover it and has not read its rules, and stop.\n- " + verifiedLine(c.prompt_firms) + ".\n\n" + c.troid },
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
  else if (p.dd === "trailing") { locked = p.locks != null && hwm >= quota * (1 + p.locks / 100); ddFloor = locked ? quota : hwm * (1 - mpct);
    fdd = locked ? `quota (locked after +${p.locks}%)` : `high-water mark × (1 − ${p.m}%)`;
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
    : `trailing floor = high-water mark × (1 − ${p.m}%)` + (p.hwm === "equity" ? " — trails on equity intraday: an unrealised high raises the floor" : ""));
  if (p.basis === "max_balance_equity") notes.push(`daily floor = high at rollover − ${p.d}% of the original size`);
  let crossover = null;
  if (ddFloor != null && p.basis != null) {
    crossover = p.basis === "day_start" ? ddFloor / (1 - dpct) : ddFloor + quota * dpct;
    if (p.dd === "trailing" && !locked) notes.push("crossover is at the current high-water mark; it moves with it");
  }
  const used = [];
  if (dFloor != null) { used.push(["d", `daily ${p.d}%`]); used.push(["basis", `daily basis (${p.basis})`]); }
  if (ddFloor != null) { used.push(["m", `max ${p.m}%`]); used.push(["dd", `drawdown type (${p.dd})`]);
    if (p.dd === "trailing") { if (p.locks != null) used.push(["locks", `lock at +${p.locks}%`]); if (p.hwm != null) used.push(["hwm", `high-water-mark basis (${p.hwm})`]); } }
  return { firm: f.name, product: p.label, daily_basis: p.basis, drawdown_type: p.dd, hwm_basis: p.hwm,
           daily_floor: r2(dFloor), daily_budget: r2(dB), dd_floor: r2(ddFloor), dd_budget: r2(ddB),
           trailing_locked: p.dd === "trailing" ? locked : null, binding, effective_budget: r2(eff),
           crossover_equity: r2(crossover), formula, working, pending, notes, sources: sourcesFor(p, used), _p: p, _eq: eq, _used: used, _quota: quota };
}
const r2 = (x) => (x == null ? null : Math.round(x * 100) / 100);
const r4 = (x) => (x == null ? null : Math.round(x * 1e4) / 1e4);
// The rules a result used, each with where troid read it — the tool-side twin of the provenance block.
function sourcesFor(p, used) {
  return used.map(([k, rule]) => {
    const c = k === "lev_band" ? p._band_pv : p.pv[k];
    return c ? { rule, document_section: c.section, read_on: c.read_on.length ? c.read_on : "not recorded", urls: c.urls }
             : { rule, source: "not yet recorded" };
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
  const entry = +a.entry, stop = +a.stop, tR = a.target_r != null ? +a.target_r : 2;
  const rpIn = a.risk_pct != null ? +a.risk_pct : 0.5, cpIn = a.budget_cap_pct != null ? +a.budget_cap_pct : 35, rp = rpIn / 100, cp = cpIn / 100;
  const lev = a.leverage != null ? +a.leverage : 5, mode = a.margin_mode === "isolated" ? "isolated" : "cross";
  const { _p, _eq, _used, _quota, ...base } = b;
  base.tier = "DERIVED from the firm's rules in firms.json; each rule's source is under sources";
  if (!b.binding) return { verdict: "PENDING", reasons: ["troid has no daily basis or drawdown type recorded for this product, so there is no budget to size against"], ...base };
  const dist = Math.abs(entry - stop), blocks = [];
  if (side > 0 && stop >= entry) blocks.push("stop at or above entry on a long");
  if (side < 0 && stop <= entry) blocks.push("stop at or below entry on a short");
  if (dist <= 0) blocks.push("stop distance is zero");
  if (b.effective_budget <= 0) blocks.push("no budget left — " + b.binding + " already breached");
  if (blocks.length) return { verdict: "BLOCK", reasons: blocks, ...base };
  const notes = base.notes.slice(), working = base.working.slice();
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
  let liq, fl;   // MMR 0.5% is troid's assumption, not a firm rule
  if (mode === "isolated") { liq = (1 - (1 - 1 / levUsed) / (1 - MMR)) * 100; fl = `1 − (1 − 1 ÷ leverage used) ÷ (1 − MMR ${MMR * 100}%)`; }
  else { liq = notional > 0 ? (1 - (1 - eq / notional) / (1 - MMR)) * 100 : Infinity; fl = `1 − (1 − equity ÷ notional) ÷ (1 − MMR ${MMR * 100}%)`; }   // <= 0: already below maintenance
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
           assumptions: ["exchange liquidation uses a 0.5% maintenance margin — troid's assumption, no firm source"],
           ...base, working, notes };
}

// Bitfunded's restricted practices (RTP) and Terms. Modelled for Bitfunded only. Each finding names the
// document it comes from and the date troid read it (firms.json provenance.sources: rtp, tou).
const MAJORS = new Set(["BTC", "ETH", "BNB", "XRP", "SOL", "TRX", "HYPE", "ZEC", "DOGE", "ADA"]);
const HOLD_DAYS = { major: 10, minor: 7, tradfi: 5 };
const PENALTY_LADDER = [[65, 50], [75, 60], [90, 65], [96, 70]];
const PENALTY_LADDER_IF = [[55, 50], [65, 55], [75, 60], [90, 65], [96, 70]];
const MIN_DAYS = { "1step": 5, "2step_s1": 5, "2step_s2": 5, express: 5, instant: 0, trader: 0 };
function asset_class(symbol) {
  const base = String(symbol || "BTCUSDT").toUpperCase().split(":").pop().replace("USDT", "").replace("USD", "");
  if (MAJORS.has(base)) return "major";
  if (["XAU", "XAG", "GOLD", "SILVER", "TSLA", "NVDA", "AAPL", "NDX", "DJI", "SPX"].includes(base) || (base.length <= 4 && !/^[A-Z]+$/.test(base))) return "tradfi";
  return "minor";
}
function refSources(ref) {
  const S = (((context().prompt_firms.bitfunded || {}).provenance) || {}).sources || {};
  const ids = [];
  if (/RTP/.test(ref)) ids.push("rtp");
  if (/ToU/.test(ref)) ids.push("tou");
  return ids.filter((i) => S[i]).map((i) => ({ document: S[i].doc, read_on: S[i].read_on || "not recorded", url: S[i].url }));
}
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
  for (const x of findings) x.sources = refSources(x.rule);
  return { firm: "Bitfunded", product, clear: findings.length === 0, findings: findings.length ? findings : [{ severity: "ok", rule: "—", detail: "No breach detected against the rules modelled here." }],
           sources: refSources("RTP ToU"),
           tier: "SOURCED — Bitfunded Terms of Use and help centre, sections cited; each finding lists its document and read date",
           caveat: "Checks only the rules modelled here. Not a substitute for reading the firm's Terms. Verify anything material with the firm directly." };
}

const RULES = {
  crossover: "A funded account has two loss ceilings. Under Bitfunded the daily limit is a FIXED amount from the initial balance (FAQ) and the max loss is a fixed floor from the starting quota. They swap at equity = quota × (1 − max% + daily%). On a $100k 1-Step that is $98,000 — only $2,000 below the start. Below it the max loss binds and the advertised 4% daily is fiction. Size against the smaller of the two, always. Other firms use other bases: CFT's daily is a percentage of the day-start balance (crossover quota × (1 − max%) / (1 − daily%)); BrightFunded's is a fixed amount below the high at rollover.",
  reset: "Bitfunded's trading day resets at 00:00 UTC+8 = 16:00 UTC, which is noon in New York. Not midnight. Morning and afternoon sessions draw on separate daily budgets. The trap: a floating loss that survives the reset counts in full against the new day, because the prior day's profit does not carry over. A position inside the limit at 11:59 can breach at 12:01 without price moving. BrightFunded rolls over at 23:30–23:59 CET and advises not trading in the window; Crypto Fund Trader resets at 00:05 UTC (T&C 8.i–8.ii).",
  fees: "Bitfunded: 0.04% per side on notional, 0.08% round trip. Notional scales inversely with stop distance, so tight stops are punished hardest. Fee share of risk = 2f/(s+2f). At a 3.9% stop that's 2% of risk; at a 0.3% scalp stop it's 21%. Other firms' fees are in firms.json; a null is pending.",
  leverage: "Leverage does not determine your loss — the stop does. risk = |entry − stop| × quantity, and leverage appears nowhere in it. What leverage changes is margin posted and liquidation distance. Under ISOLATED margin that distance is roughly entry × (1 − 1/leverage): ~20% at 5x. Under CROSS margin (Bitfunded's mode) the whole account backs the position, so exchange liquidation is unreachable at any size the firm allows — the firm's own floors fail you first.",
  cross: "Bitfunded runs cross margin at 5x: every position is backed by the entire account balance. Exchange liquidation never binds — even at the 65% margin cap it sits at ~31% adverse move while the 6% floor binds at 1.85%. The firm's floors ARE your liquidation model. Nothing cuts a runaway position before the firm fails you; your stop is the only circuit breaker in front of the floor. At the 65% margin cap the daily limit binds at a 1.23% adverse move — tighter than a normal 1.66% stop.",
  drawdown: "Bitfunded's max loss is STATIC — measured from the account quota, not a high-water mark — so profit permanently widens the buffer. Trailing drawdown (BrightFunded 1-Step, CFT 1-Phase) works the opposite way: the floor follows the high-water mark up until it locks at the initial balance after +6%. BrightFunded's trails on equity intraday — an unrealised high raises the floor (help centre scenario 3); CFT's trails on balance.",
  ladder: "Scaling in does not increase position size at fixed risk — it decreases it. With the stop anchored to the first entry's structure, later tranches sit further from the stop and earn less quantity. Five strength tranches hold about 34% LESS than a single entry at the same risk. The benefit is conditionality: you fill more on trades that work than on trades that don't.",
  ruin: "Under a proportional cap (risk at most c of the REMAINING budget), budget after n losses is B(1−c)^n — it approaches zero without reaching it, so ruin by realized losses is unreachable and the real failure mode is a stalled account. Uncapped, a fixed fraction f of quota reaches the floor in floor(maxloss/f) losses: 12 at 0.5%, 6 at 1%, 3 at 2%. At a professional +0.35R edge, 1% uncapped blows up 68% of the time within a year (MODELLED); under a cap, zero.",
  min_days: "Bitfunded: five trading days minimum to clear a stage (ToU 9(a)). The challenge page displays 0. The contract governs. The bad failure mode is hitting the profit target in three days and being unable to clear the stage.",
  hold_limit: "Bitfunded: majors 10 days, other crypto 7, TradFi 5 (Restricted Trading Practices s.1). Profits from a breaching trade can be removed from payout eligibility.",
  accounts: "Bitfunded: one active account per challenge level without written consent (ToU 6(b)). Across all seven levels that caps simultaneous capital at $355,000.",
  marketed_strategies: "Bitfunded ToU 14(d)(v) prohibits using third-party or marketed strategies to pass an evaluation. This is why troid evaluates trades rather than generating them.",
};
function explain_rule(a) {
  const t = String(a.topic || "").toLowerCase().trim().replace(/\s+/g, "_");
  if (!Object.hasOwn(RULES, t)) return { error: "unknown topic. options: " + Object.keys(RULES).sort().join(", ") };
  return { topic: t, explanation: RULES[t],
           tier: "Explanation text written by troid for ask troid, not generated from firms.json, so it can fall out of step with troid's compare. " +
                 "Its formulas are DERIVED; a rule it cites is SOURCED from the section named, and the firm's own documents govern. For a rule's read date, " +
                 "use the sources in size_trade or check_budget, or troid's compare." };
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
                             : "troid's record of " + f.name + "'s terms does not exclude " + cc + ". That is not a statement that the firm serves " + cc + ".",
    sources: [src("availability"), ...(platforms.length ? [src("availability_platform")] : [])],
    advice: "Check the firm's own terms before buying." };
  if (third) res.not_in_terms = "A third party lists " + cc + " as excluded; troid has not read that in the firm's terms (" + third + ").";
  return res;
}

const TOOLS = [
  { name: "size_trade", description: "Size a trade the user brings against a firm product troid covers: both loss ceilings, the binding one, quantity net of fees, margin, fee share of risk, losses left, circuit-breaker order, every formula and intermediate value (working), and the source and read date of each rule used. Pending fields are reported as pending. Never call this to suggest a trade.",
    input_schema: { type: "object", properties: {
      firm: { type: "string", description: "firm key from firms.json: bitfunded | brightfunded | crypto_fund_trader" },
      product: { type: "string", description: "product key, e.g. 1step, 2step_s1, 1phase, instant" },
      quota: { type: "number" }, equity: { type: "number" }, day_start: { type: "number", description: "balance at the last daily reset; defaults to equity" },
      high_water_mark: { type: "number", description: "trailing products only; defaults to max(equity, quota)" },
      high_at_rollover: { type: "number", description: "BrightFunded only: max(balance, equity) at the last rollover; defaults to day_start" },
      side: { type: "string", enum: ["long", "short"] }, entry: { type: "number" }, stop: { type: "number" },
      target_r: { type: "number" }, risk_pct: { type: "number", description: "percent of equity, default 0.5" },
      budget_cap_pct: { type: "number", description: "cap as percent of the binding budget, default 35" },
      leverage: { type: "number" }, margin_mode: { type: "string", enum: ["cross", "isolated"] } },
      required: ["firm", "product", "quota", "equity", "side", "entry", "stop"] } },
  { name: "check_budget", description: "Room left under each loss ceiling for a firm product troid covers, which one binds, and the crossover equity, with the formulas (working) and the source and read date of each rule used.",
    input_schema: { type: "object", properties: {
      firm: { type: "string" }, product: { type: "string" }, quota: { type: "number" }, equity: { type: "number" },
      day_start: { type: "number" }, high_water_mark: { type: "number" }, high_at_rollover: { type: "number" } },
      required: ["firm", "product", "quota", "equity"] } },
  { name: "check_compliance", description: "Check a trade plan against the firm rules that disqualify (hold limit, open-trade cap, concentration ladder, closed-trade minimum, third-party strategies, accounts per level, minimum days). Modelled for Bitfunded only; other firms return pending.",
    input_schema: { type: "object", properties: {
      firm: { type: "string" }, product: { type: "string" }, symbol: { type: "string" }, hold_days: { type: "number" },
      open_trades: { type: "integer" }, margin_pct_of_capital: { type: "number" }, trading_days_so_far: { type: "integer" },
      uses_third_party_strategy: { type: "boolean" }, accounts_at_this_level: { type: "integer" }, closed_trades_this_stage: { type: "integer" } },
      required: ["firm"] } },
  { name: "check_availability", description: "Whether a firm's own terms, as troid has recorded them, exclude a country. Call it for each firm before discussing that firm with a user who has mentioned their country. It never says a firm is available: it reports what the recorded terms exclude, a platform-only exclusion, or that troid has not recorded the list.",
    input_schema: { type: "object", properties: { firm: { type: "string", description: "firm key: bitfunded | brightfunded | crypto_fund_trader" },
      country: { type: "string", description: "ISO 3166-1 alpha-2 code, e.g. US, IN, NG, BR" } }, required: ["firm", "country"] } },
  { name: "explain_rule", description: "Explain a prop-firm rule and why it matters, with the arithmetic. Topics: crossover, reset, fees, leverage, cross, drawdown, ladder, ruin, min_days, hold_limit, accounts, marketed_strategies.",
    input_schema: { type: "object", properties: { topic: { type: "string" } }, required: ["topic"] } },
];
const RUN = { size_trade, check_budget, check_compliance, check_availability, explain_rule };
function runTool(name, input) {
  try { return Object.hasOwn(RUN, name) ? RUN[name](input || {}) : { error: "unknown tool " + name }; }
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
async function callModel(route, messages, deadlineAt, onSend, lang) {
  const R = ROUTE[route];
  for (let attempt = 0; ; attempt++) {
    const left = deadlineAt - Date.now();
    if (left < MIN_CALL_MS) { const e = new Error("deadline"); e.deadline = true; throw e; }
    spend();
    const params = { model: R.model, max_tokens: R.max_tokens, cache_control: { type: "ephemeral" },   // + the tail of the conversation
                     system: systemBlocks(lang), tools: TOOLS, messages };
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
const textOf = (resp) => (resp.content || []).filter((b) => b.type === "text").map((b) => b.text).join("\n").trim();
const wantsTool = (resp) => resp.stop_reason === "tool_use" || (resp.stop_reason === "max_tokens" && (resp.content || []).some((b) => b.type === "tool_use"));

// troid's side of the history is signed: each reply carries an HMAC over the whole conversation up to and
// including it, and the next message must bring it back. Stateless; nothing is stored. The HMAC input starts
// with a hash of the guardrails, so a history signed under older guardrails no longer verifies.
const VERSION = crypto.createHash("sha256").update(GUARDRAILS).digest("hex").slice(0, 16);
const sign = (msgs) => crypto.createHmac("sha256", TURN_KEY).update(JSON.stringify([VERSION, ...msgs.map((m) => [m.role, m.content])])).digest("base64url");
function signedOk(msgs, sig) {
  if (msgs.length === 1) return true;
  const want = Buffer.from(sign(msgs.slice(0, -1))), got = Buffer.from(String(sig || ""));
  return got.length === want.length && crypto.timingSafeEqual(got, want);
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
const isOn = () => ENABLED && !!KEY && Buffer.byteLength(TURN_KEY) >= 32;

function queryLang(req) {
  try { return (req.query && req.query.lang) || new URL(req.url || "/", "http://x").searchParams.get("lang"); } catch (e) { return null; }
}

module.exports = async (req, res) => {
  res.setHeader("cache-control", "no-store");
  let lang = liveLang(queryLang(req));                                   // the page's language, if it is live; else English
  if (req.method === "GET") {
    let ctx = null;
    try { const c = context(); ctx = { troid_md: c.troid.length, support_md: c.support.length, firms_json: c.firms.length, prompt_firms: JSON.stringify(c.prompt_firms).length,
                                     methodology_md: c.method.length, firms: Object.keys(profiles()) }; } catch (e) { ctx = { error: "context missing" }; }
    return json(res, 200, { enabled: isOn(), flag: ENABLED, limit_per_hour: LIMIT_PER_HOUR, max_messages: MAX_MESSAGES, max_chars: MAX_CHARS,
                            models: { lookup: MODEL_LOOKUP, tools: MODEL_TOOLS }, tools: TOOLS.map((t) => t.name), lang, languages: liveCodes(),
                            disclosure: S(lang, "ask.disclosure"), context: ctx });
  }
  if (req.method !== "POST") return json(res, 405, { error: "POST {messages:[{role, content}]}" });
  if (!ENABLED) return json(res, 503, { enabled: false, error: S(lang, "ask.err.switched_off") });
  if (!isOn()) return json(res, 503, { enabled: false, error: S(lang, "ask.err.not_configured") });
  // Same-origin JSON only: a cross-site form or no-cors fetch can't spend troid's key from someone else's page.
  if (!/^application\/json\b/i.test(String(req.headers["content-type"] || ""))) return json(res, 415, { error: "Send application/json." });
  const site = req.headers["sec-fetch-site"];
  if (site && site !== "same-origin") return json(res, 403, { error: "ask troid answers on troid.ai only." });
  if (!spendable()) return json(res, 503, { enabled: true, error: S(lang, "ask.err.busy") });   // turned away before the model: not logged, costs no hourly message
  if (!allow(clientKey(req))) return json(res, 429, { error: S(lang, "ask.err.limit", { n: LIMIT_PER_HOUR }) });
  let body;
  try { body = req.body; if (typeof body === "string") body = JSON.parse(body); } catch (e) { body = null; }
  if (body && body.lang) lang = liveLang(body.lang);
  if (tooLong(body)) return json(res, 413, { error: S(lang, "ask.err.too_long", { n: MAX_CHARS }) });
  const messages = validate(body);
  if (!messages) return json(res, 400, { restart: true, error: S(lang, "ask.err.restart", { n: MAX_MESSAGES - 1 }) });
  if (!signedOk(messages, body.sig)) return json(res, 400, { restart: true, error: S(lang, "ask.err.unverified") });
  const log = { troid: "assistant", messages: 1 };                     // counts and flags only — never text, never an address
  const warned = messages.some((m) => m.role === "assistant" && isWarning(m.content));
  const first = !(body.disclosed === true || messages.some((m) => m.role === "assistant" && hasDisclosure(m.content)));
  const deadlineAt = Date.now() + DEADLINE_MS;
  let sent = null, toolCalls = 0;
  const onSend = (m) => { sent = m; };                                  // the model a request actually went to
  try {
    let route = "lookup", resp = await callModel(route, messages, deadlineAt, onSend, lang);
    if (wantsTool(resp) && MODEL_LOOKUP !== MODEL_TOOLS) { route = "tools"; resp = await callModel(route, messages, deadlineAt, onSend, lang); }   // Haiku's turn is discarded, never replayed
    const convo = messages.slice();
    for (let round = 0; round < MAX_TOOL_ROUNDS && resp.stop_reason === "tool_use" && Date.now() < deadlineAt - MIN_CALL_MS; round++) {
      const uses = resp.content.filter((b) => b.type === "tool_use");
      toolCalls += uses.length;
      convo.push({ role: "assistant", content: resp.content });        // unchanged, thinking blocks included
      convo.push({ role: "user", content: uses.map((u) => {
        const out = runTool(u.name, u.input);
        return { type: "tool_result", tool_use_id: u.id, content: JSON.stringify(out), ...(out && out.error ? { is_error: true } : {}) };
      }) });
      resp = await callModel("tools", convo, deadlineAt, onSend, lang);
    }
    let reply, ended = false;
    if (resp.stop_reason === "refusal") { reply = S(lang, "ask.refusal"); log.refusal = 1; }
    else {
      reply = textOf(resp);
      // Only the service ends a session, and only after a warning. The model asks with the sentinel; a reply
      // that is the session-ended text word for word (in any published language) is treated the same way.
      if (isSentinelOnly(reply) || isEnded(reply)) {
        if (warned) { reply = S(lang, "ask.ended"); ended = true; log.ended = 1; }
        else reply = S(lang, "ask.warning");
      } else {
        reply = reply.replace(SENTINEL, "").trim();                    // never reaches the page, ends nothing mid-answer
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
    console.log(JSON.stringify(log));
    const out = { reply, model: sent, tool_calls: toolCalls, ended, disclosed: true, lang, note: S(lang, "ask.note") };
    if (!ended) {
      out.sig = sign([...messages, { role: "assistant", content: reply }]);
      const total = messages.reduce((n, m) => n + m.content.length, 0) + reply.length;
      if (messages.length + 2 > MAX_MESSAGES || total + MAX_CHARS > MAX_TOTAL_CHARS) out.full = true;   // the next message could not fit
    }
    return json(res, 200, out);
  } catch (e) {
    Object.assign(log, { error: 1, tool_calls: toolCalls, model: sent });
    if (e && typeof e.status === "number") log.status = e.status;
    console.log(JSON.stringify(log));
    // most specific first: APIConnectionTimeoutError extends APIConnectionError, which extends APIError. A body
    // read cut by the deadline surfaces as a bare DOMException (AbortError / TimeoutError).
    if (e && (e.deadline || e instanceof Anthropic.APIUserAbortError || e instanceof Anthropic.APIConnectionTimeoutError || e.name === "AbortError" || e.name === "TimeoutError"))
      return json(res, 504, { error: S(lang, "ask.err.timeout") });
    if (e && (e.busy || e instanceof Anthropic.RateLimitError || e instanceof Anthropic.InternalServerError)) return json(res, 503, { enabled: true, error: S(lang, "ask.err.busy") });
    if (e instanceof Anthropic.APIConnectionError) return json(res, 502, { error: S(lang, "ask.err.unreachable") });
    if (e instanceof Anthropic.AuthenticationError || e instanceof Anthropic.PermissionDeniedError || e instanceof Anthropic.NotFoundError || e instanceof Anthropic.BadRequestError)
      return json(res, 500, { error: S(lang, "ask.err.misconfigured") });
    if (e instanceof Anthropic.APIError) return json(res, 502, { error: S(lang, "ask.err.unreachable") });
    return json(res, 502, { error: S(lang, "ask.err.error") });
  }
};
module.exports.tools = RUN;   // for tests
module.exports.fixed = { DISCLOSURE, WARNING, END_SESSION, ENDED_REPLY, REFUSAL_REPLY };
module.exports.EN = EN;   // for tests: must equal web/i18n/en.json's ask.* strings
module.exports._sign = (msgs) => sign(msgs);   // for tests
module.exports._clientKey = clientKey;
