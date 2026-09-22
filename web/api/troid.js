"use strict";
/* troid assistant — a Vercel serverless function.
 *
 * One call per message: fixed system prompt (TROID.md, firms.json, METHODOLOGY.md, the
 * guardrails below), the user's conversation as sent by the page, four arithmetic tools
 * ported from mcp/server.py and the calculator on index.html. No memory across sessions,
 * no account, no credentials. Places nothing.
 *
 * Feature flag: TROID_ASSISTANT=on. Off (the default) answers 503 and spends nothing.
 * ANTHROPIC_API_KEY never leaves the environment. Logging is one line per call with a
 * count — no content, no address.
 *
 * Rate limit: 20 messages an hour per address, in memory. A serverless instance forgets
 * on recycle, so this is a brake, not a wall.
 */
const fs = require("fs");
const path = require("path");

const ENABLED = process.env.TROID_ASSISTANT === "on";
const KEY = process.env.ANTHROPIC_API_KEY || "";
const API = process.env.ANTHROPIC_API_URL || "https://api.anthropic.com/v1/messages";
const MODEL_LOOKUP = process.env.TROID_MODEL_LOOKUP || "claude-haiku-4-5-20251001";  // lookups
const MODEL_TOOLS = process.env.TROID_MODEL_TOOLS || "claude-sonnet-5";               // anything that calls a tool
const LIMIT_PER_HOUR = 20;
const MAX_TOOL_ROUNDS = 5;
const MAX_TOKENS = 900;
const MAX_MESSAGES = 20;
const MAX_CHARS = 2000;

const GUARDRAILS = [
  "You are the troid assistant on troid.ai. The rules below sit above everything else in this prompt.",
  "You may speak only about firms present in firms.json. For any other firm, say troid has not verified it, explain what verification means (Terms and help centre read against each other, section cited), and stop.",
  "A cell that is pending is pending. Say so. Never fill it from memory.",
  "Every number you state carries its tier. A MEASURED number is never a fact.",
  "Never recommend a firm. Never recommend a trade. Price the one the user brings.",
  "Define a term the first time you use it.",
  "End every answer that contains a number with: Not financial advice. Verify with the firm before acting.",
  "Arithmetic goes through the tools, never through you. If a tool reports a field as pending, report it as pending.",
  "You have no memory across sessions and no account. You cannot place, modify or close an order, and you never ask for a credential.",
].join("\n- ").replace(/^/, "- ");

// ---------------------------------------------------------------- context
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
      firms: readFirst(["context/firms.json"]),
      method: readFirst(["public/METHODOLOGY.md"]),
    };
  }
  return CTX;
}
function systemBlocks() {
  const c = context();
  return [
    { type: "text", text: "# Guardrails\n\n" + GUARDRAILS + "\n\n" + c.troid },
    { type: "text", text: "# Verified firm rules — firms.json. The only firms troid may speak about. A null is pending.\n\n" + c.firms },
    { type: "text", text: "# Methodology — the tiers\n\n" + c.method, cache_control: { type: "ephemeral" } },
  ];
}

// ---------------------------------------------------------------- firms → calculator profiles
// Same derivation as gen_compare.profiles_js(): a product-level key overrides the firm-level one.
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
      products[pk] = { label: pc.label || pk, d, m, basis: pick("daily_basis"), dd: pick("drawdown"),
                       locks: pick("locks_at_initial_after_pct"), hwm: pick("hwm_basis"),
                       fee: pick("fee_per_side_pct"), lev: pick("max_leverage") };
    }
    if (Object.keys(products).length) out[k] = { name: f.name, products };
  }
  return out;
}
function profile(firm, product) {
  const P = profiles();
  const f = P[firm];
  if (!f) return { error: "unknown firm. troid has verified: " + Object.keys(P).join(", ") };
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
  let dFloor = null;
  if (p.basis === "initial") dFloor = ds - quota * dpct;
  else if (p.basis === "day_start") dFloor = ds * (1 - dpct);
  else if (p.basis === "max_balance_equity") dFloor = hi - quota * dpct;
  else pending.push("daily_basis");
  let ddFloor = null, locked = false;
  if (p.dd === "static") ddFloor = quota * (1 - mpct);
  else if (p.dd === "trailing") { locked = p.locks != null && hwm >= quota * (1 + p.locks / 100); ddFloor = locked ? quota : hwm * (1 - mpct); }
  else pending.push("drawdown_type");
  const dB = dFloor == null ? null : eq - dFloor, ddB = ddFloor == null ? null : eq - ddFloor;
  let binding = null, eff = null;
  if (dB == null && ddB == null) { /* nothing to size against */ }
  else if (dB == null) { binding = "max drawdown"; eff = ddB; notes.push("daily basis pending for this firm — sized against the drawdown ceiling only"); }
  else if (ddB == null) { binding = "daily loss limit"; eff = dB; notes.push("drawdown type pending for this firm — sized against the daily ceiling only"); }
  else { binding = dB <= ddB ? "daily loss limit" : "max drawdown"; eff = Math.min(dB, ddB); }
  if (p.dd === "trailing") notes.push(locked ? `trailing floor locked at the initial balance after +${p.locks}%`
    : `trailing floor = high-water mark × (1 − ${p.m}%)` + (p.hwm === "equity" ? " — trails on equity intraday: an unrealised high raises the floor" : ""));
  if (p.basis === "max_balance_equity") notes.push(`daily floor = high at rollover − ${p.d}% of the original size`);
  let crossover = null;
  if (ddFloor != null && p.basis != null) {
    crossover = p.basis === "day_start" ? ddFloor / (1 - dpct) : ddFloor + quota * dpct;
    if (p.dd === "trailing" && !locked) notes.push("crossover is at the current high-water mark; it moves with it");
  }
  return { firm: f.name, product: p.label, daily_basis: p.basis, drawdown_type: p.dd, hwm_basis: p.hwm,
           daily_floor: r2(dFloor), daily_budget: r2(dB), dd_floor: r2(ddFloor), dd_budget: r2(ddB),
           trailing_locked: p.dd === "trailing" ? locked : null, binding, effective_budget: r2(eff),
           crossover_equity: r2(crossover), pending, notes, _p: p, _eq: eq };
}
const r2 = (x) => (x == null ? null : Math.round(x * 100) / 100);

function check_budget(a) {
  const b = budgets(a);
  if (b.error) return b;
  const { _p, _eq, ...out } = b;
  out.tier = "DERIVED from the firm's verified rules in firms.json";
  if (!out.binding) out.verdict = "PENDING: daily basis and drawdown type are not yet verified for this product";
  return out;
}

function size_trade(a) {
  const b = budgets(a);
  if (b.error) return b;
  const p = b._p, eq = b._eq;
  const side = String(a.side || "long").toLowerCase().startsWith("l") ? 1 : -1;
  const entry = +a.entry, stop = +a.stop, tR = a.target_r != null ? +a.target_r : 2;
  const rp = (a.risk_pct != null ? +a.risk_pct : 0.5) / 100, cp = (a.budget_cap_pct != null ? +a.budget_cap_pct : 35) / 100;
  const lev = a.leverage != null ? +a.leverage : 5, mode = a.margin_mode === "isolated" ? "isolated" : "cross";
  const { _p, _eq, ...base } = b;
  base.tier = "DERIVED from the firm's verified rules in firms.json";
  if (!b.binding) return { verdict: "PENDING", reasons: ["daily basis and drawdown type not yet verified for this product; troid sizes against verified rules only"], ...base };
  const dist = Math.abs(entry - stop), blocks = [];
  if (side > 0 && stop >= entry) blocks.push("stop at or above entry on a long");
  if (side < 0 && stop <= entry) blocks.push("stop at or below entry on a short");
  if (dist <= 0) blocks.push("stop distance is zero");
  if (b.effective_budget <= 0) blocks.push("no budget left — " + b.binding + " already breached");
  if (blocks.length) return { verdict: "BLOCK", reasons: blocks, ...base };
  const notes = base.notes.slice();
  const intended = rp * eq, cap = cp * Math.max(b.effective_budget, 0), risk = Math.min(intended, cap);
  const reduced = risk < intended - 1e-9;
  const feeKnown = p.fee != null, fee = feeKnown ? p.fee / 100 : 0;
  if (!feeKnown) { base.pending.push("fee_per_side"); notes.push("fee per side pending for this firm — size shown before fees"); }
  let levUsed = lev;
  if (p.lev != null && lev > p.lev) { levUsed = p.lev; notes.push(`leverage capped at ${p.lev}× by the firm`); }
  if (p.lev == null) base.pending.push("max_leverage");
  const fu = entry * fee * 2, qty = risk / (dist + fu), notional = qty * entry, margin = notional / levUsed;
  const fees = qty * fu, fshare = fees / risk * 100, target = entry + side * tR * dist;
  const consumes = risk / b.effective_budget * 100, left = Math.floor(b.effective_budget / risk + 1e-9);
  if (feeKnown && fshare > 15) notes.push(`fees are ${fshare.toFixed(0)}% of risk — stop tight enough that costs dominate`);
  if (reduced) notes.push(`cut from ${intended.toFixed(2)} to ${risk.toFixed(2)} — ${b.binding} budget caps it`);
  notes.push(`${left} more losses at this size before ${b.binding} trips`);
  const sp = dist / entry * 100;
  let liq;
  if (mode === "isolated") liq = (1 - (1 - 1 / levUsed) / (1 - MMR)) * 100;
  else liq = notional < eq / MMR ? (1 - (1 - eq / notional) / (1 - MMR)) * 100 : Infinity;
  const ord = [["your stop", sp]];
  if (b.daily_budget != null) ord.push(["daily limit", b.daily_budget / notional * 100]);
  if (b.dd_budget != null) ord.push([p.dd === "trailing" && !b.trailing_locked ? "trailing floor" : "max-loss floor", b.dd_budget / notional * 100]);
  ord.push([`exchange liquidation (${mode})`, Math.max(liq, 0)]);
  ord.sort((x, y) => x[1] - y[1]);
  if (ord[0][0] !== "your stop") notes.push(`DANGER — ${ord[0][0]} binds at ${ord[0][1].toFixed(2)}% adverse, inside your stop`);
  else if (mode === "cross") notes.push("cross: nothing cuts a runaway before the firm's floor — your stop is the only breaker in front of it");
  else notes.push(`isolated: exchange liquidates at ${liq.toFixed(1)}% for the position's own margin, before the floor`);
  return { verdict: reduced ? "REDUCE" : "OK", quantity: Math.round(qty * 1e6) / 1e6, notional: r2(notional),
           margin: r2(margin), leverage_used: levUsed, risk: r2(risk), fees: feeKnown ? r2(fees) : null,
           fee_share_of_risk_pct: feeKnown ? r2(fshare) : null, stop_distance_pct: r2(sp), target: r2(target),
           consumes_pct_of_budget: r2(consumes), losses_remaining: left,
           circuit_breakers: ord.map(([e, v]) => ({ event: e, adverse_move_pct: isFinite(v) ? r2(v) : null })),
           ...base, notes };
}

// Bitfunded's restricted practices (RTP) and Terms. Verified for Bitfunded only.
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
function check_compliance(a) {
  const firm = a.firm || "bitfunded";
  if (firm !== "bitfunded") return { firm, pending: true, note: "Restricted-practice rules are verified for Bitfunded only. For this firm they are pending: say so and point to the compare page. Do not fill them from memory." };
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
  const minDays = MIN_DAYS[product] != null ? MIN_DAYS[product] : 5, days = +a.trading_days_so_far || 0;
  if (minDays && days > 0 && days < minDays) findings.push({ severity: "warning", rule: "ToU 9(a)", detail: `${days} trading days so far; ${minDays} required to clear the stage. The challenge page displays 0 — the contract governs.` });
  return { firm: "Bitfunded", product, clear: findings.length === 0, findings: findings.length ? findings : [{ severity: "ok", rule: "—", detail: "No breach detected against the rules modelled here." }],
           tier: "SOURCED — Bitfunded Terms and help centre, sections cited",
           caveat: "Checks only the rules modelled here. Not a substitute for reading the firm's Terms. Verify anything material with the firm directly." };
}

const RULES = {
  crossover: "A funded account has two loss ceilings. Under Bitfunded the daily limit is a FIXED amount from the initial balance (FAQ) and the max loss is a fixed floor from the starting quota. They swap at equity = quota × (1 − max% + daily%). On a $100k 1-Step that is $98,000 — only $2,000 below the start. Below it the max loss binds and the advertised 4% daily is fiction. Size against the smaller of the two, always. Other firms use other bases: CFT's daily is a percentage of the day-start balance (crossover quota × (1 − max%) / (1 − daily%)); BrightFunded's is a fixed amount below the high at rollover.",
  reset: "Bitfunded's trading day resets at 00:00 UTC+8 = 16:00 UTC, which is noon in New York. Not midnight. Morning and afternoon sessions draw on separate daily budgets. The trap: a floating loss that survives the reset counts in full against the new day, because the prior day's profit does not carry over. A position inside the limit at 11:59 can breach at 12:01 without price moving. BrightFunded rolls over at 23:30–23:59 CET and advises not trading in the window; CFT at 00:00 UTC.",
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
  if (!RULES[t]) return { error: "unknown topic. options: " + Object.keys(RULES).sort().join(", ") };
  return { topic: t, explanation: RULES[t], tier: "DERIVED or SOURCED — reproduced by verify_claims.py in the repo. Firm-specific unless it says otherwise." };
}

const TOOLS = [
  { name: "size_trade", description: "Size a trade the user brings against a verified firm product: both loss ceilings, the binding one, quantity net of fees, margin, fee share of risk, losses left, circuit-breaker order. Pending fields are reported as pending. Never call this to suggest a trade.",
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
  { name: "check_budget", description: "Room left under each loss ceiling for a verified firm product, which one binds, and the crossover equity.",
    input_schema: { type: "object", properties: {
      firm: { type: "string" }, product: { type: "string" }, quota: { type: "number" }, equity: { type: "number" },
      day_start: { type: "number" }, high_water_mark: { type: "number" }, high_at_rollover: { type: "number" } },
      required: ["firm", "product", "quota", "equity"] } },
  { name: "check_compliance", description: "Check a trade plan against the firm rules that disqualify (hold limit, open-trade cap, concentration ladder, closed-trade minimum, third-party strategies, accounts per level, minimum days). Verified for Bitfunded only; other firms return pending.",
    input_schema: { type: "object", properties: {
      firm: { type: "string" }, product: { type: "string" }, symbol: { type: "string" }, hold_days: { type: "number" },
      open_trades: { type: "integer" }, margin_pct_of_capital: { type: "number" }, trading_days_so_far: { type: "integer" },
      uses_third_party_strategy: { type: "boolean" }, accounts_at_this_level: { type: "integer" }, closed_trades_this_stage: { type: "integer" } },
      required: ["firm"] } },
  { name: "explain_rule", description: "Explain a prop-firm rule and why it matters, with the arithmetic. Topics: crossover, reset, fees, leverage, cross, drawdown, ladder, ruin, min_days, hold_limit, accounts, marketed_strategies.",
    input_schema: { type: "object", properties: { topic: { type: "string" } }, required: ["topic"] } },
];
const RUN = { size_trade, check_budget, check_compliance, explain_rule };
function runTool(name, input) {
  try { return RUN[name] ? RUN[name](input || {}) : { error: "unknown tool " + name }; }
  catch (e) { return { error: "tool failed: " + (e && e.message ? e.message : "unknown") }; }
}

// ---------------------------------------------------------------- rate limit (in memory, best effort)
const HITS = new Map();
function allow(ip) {
  const now = Date.now(), keep = (HITS.get(ip) || []).filter((t) => now - t < 3600e3);
  if (keep.length >= LIMIT_PER_HOUR) { HITS.set(ip, keep); return false; }
  keep.push(now); HITS.set(ip, keep);
  if (HITS.size > 5000) HITS.clear();
  return true;
}

// ---------------------------------------------------------------- the call
async function callModel(model, messages) {
  const r = await fetch(API, {
    method: "POST",
    headers: { "content-type": "application/json", "x-api-key": KEY, "anthropic-version": "2023-06-01" },
    body: JSON.stringify({ model, max_tokens: MAX_TOKENS, system: systemBlocks(), tools: TOOLS, messages }),
  });
  if (!r.ok) throw new Error("upstream " + r.status);
  return r.json();
}
function validate(body) {
  const m = body && Array.isArray(body.messages) ? body.messages : null;
  if (!m || !m.length || m.length > MAX_MESSAGES) return null;
  const out = [];
  for (let i = 0; i < m.length; i++) {
    const x = m[i];
    const role = i % 2 === 0 ? "user" : "assistant";
    if (!x || x.role !== role || typeof x.content !== "string") return null;
    const content = x.content.trim();
    if (!content || content.length > MAX_CHARS) return null;
    out.push({ role, content });
  }
  return out.length % 2 === 1 ? out : null;   // ends on the user
}
function json(res, code, obj) { res.statusCode = code; res.setHeader("content-type", "application/json; charset=utf-8"); res.end(JSON.stringify(obj)); }

module.exports = async (req, res) => {
  res.setHeader("cache-control", "no-store");
  if (req.method === "GET") {
    let ctx = null;
    try { const c = context(); ctx = { troid_md: c.troid.length, firms_json: c.firms.length, methodology_md: c.method.length, firms: Object.keys(profiles()) }; } catch (e) { ctx = { error: "context missing" }; }
    return json(res, 200, { enabled: ENABLED, limit_per_hour: LIMIT_PER_HOUR, models: { lookup: MODEL_LOOKUP, tools: MODEL_TOOLS }, tools: TOOLS.map((t) => t.name), context: ctx });
  }
  if (req.method !== "POST") return json(res, 405, { error: "POST {messages:[{role, content}]}" });
  if (!ENABLED) return json(res, 503, { enabled: false, error: "The assistant is switched off until its disclaimer has had a legal review." });
  if (!KEY) return json(res, 503, { enabled: false, error: "The assistant has no API key configured." });
  const ip = String(req.headers["x-forwarded-for"] || req.socket?.remoteAddress || "?").split(",")[0].trim();
  if (!allow(ip)) return json(res, 429, { error: `Limit: ${LIMIT_PER_HOUR} messages an hour.` });
  let body = req.body;
  if (typeof body === "string") { try { body = JSON.parse(body); } catch (e) { body = null; } }
  const messages = validate(body);
  if (!messages) return json(res, 400, { error: `Send 1–${MAX_MESSAGES} alternating messages, user first and last, each under ${MAX_CHARS} characters.` });
  try {
    let model = MODEL_LOOKUP, toolCalls = 0;
    let resp = await callModel(model, messages);
    if (resp.stop_reason === "tool_use") { model = MODEL_TOOLS; resp = await callModel(model, messages); }
    const convo = messages.slice();
    for (let round = 0; round < MAX_TOOL_ROUNDS && resp.stop_reason === "tool_use"; round++) {
      const uses = resp.content.filter((b) => b.type === "tool_use");
      toolCalls += uses.length;
      convo.push({ role: "assistant", content: resp.content });
      convo.push({ role: "user", content: uses.map((u) => ({ type: "tool_result", tool_use_id: u.id, content: JSON.stringify(runTool(u.name, u.input)) })) });
      resp = await callModel(model, convo);
    }
    const text = (resp.content || []).filter((b) => b.type === "text").map((b) => b.text).join("\n").trim();
    console.log(JSON.stringify({ troid: "assistant", messages: 1, tool_calls: toolCalls, model }));   // a count, nothing else
    return json(res, 200, { reply: text || "No answer produced.", model, tool_calls: toolCalls, note: "Not financial advice. Verify with the firm before acting." });
  } catch (e) {
    console.log(JSON.stringify({ troid: "assistant", messages: 1, error: 1 }));
    return json(res, 502, { error: "The model could not be reached. Try again in a minute." });
  }
};
module.exports.tools = RUN;   // for tests
