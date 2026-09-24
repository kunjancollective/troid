"use strict";
/* The weekly count of what people ask ask troid (terms section 10, the fourth purpose: understanding which questions
   come up most, to improve troid's pages and answers). Once a week, the week's stored messages (conv:<session>, kept
   30 days) are counted by topic, by the firms and tools they involve, and by the page's language. Fixed rules do the
   counting: keyword patterns on the message and the tools ask troid called. The digest holds no text from any
   conversation, no quotation and no session ID, and it is kept after the conversations expire: digest:<ISO week> in
   the store, with no expiry, and business/faq_digest/<week>.json when run locally (gitignored). Nothing is published.

   Used by api/digest.js (Vercel cron, weekly) and faq_digest.js (run by hand). */

// Paraphrased topics: a label troid wrote, matched by rule, never the user's words.
const TOPICS = [
  ["the crossover (which loss ceiling binds)", /crossover|which (ceiling|limit) binds|binding (ceiling|limit)/i],
  ["daily loss limit", /daily (loss|limit|drawdown|dd)\b|daily loss/i],
  ["max loss and drawdown", /max(imum)? (loss|drawdown)|drawdown|trailing/i],
  ["the daily reset", /\breset|rollover|roll over|new (trading )?day|midnight/i],
  ["fees", /\bfees?\b|commission|spread/i],
  ["leverage and margin", /leverage|margin|liquidat/i],
  ["position size", /position size|sizing|\bsize\b|how (much|many) (can|should) i (risk|buy|trade)|\blots?\b|quantity/i],
  ["hold limits and overnight", /\bhold|overnight|weekend|how long can i keep/i],
  ["minimum trading days", /minimum (trading )?days|min(\.|imum)? days|trading days/i],
  ["profit target", /profit target|\btarget\b/i],
  ["payouts and profit split", /payout|withdraw|profit split|\bsplit\b/i],
  ["refunds", /refund/i],
  ["challenge prices and discounts", /\bprice|\bcost|expensive|cheap|discount|coupon|promo/i],
  ["country availability", /countr|available in|resident|citizen|restricted/i],
  ["restricted practices (hedging, copy trading, bots)", /hedg|copy.?trad|news trad|\bbots?\b|\bea\b|martingale|allowed|prohibited|banned/i],
  ["asked for a recommendation", /should i|which (firm|one|prop)|best (firm|prop)|recommend|will i pass|worth it/i],
  ["asked for signals or entries", /signal|what (should i|to) trade|buy or sell|long or short|entry point|where (do|should) i enter/i],
  ["is it legit", /scam|legit|trust(worthy)?|fraud/i],
  ["privacy and deletion", /delete|privacy|stored|keep my (data|conversation)|session id/i],
  ["about troid", /\btroid\b|affiliate|who (made|runs|owns)|how .* make money/i],
];
// What a tool call says the message was about.
const TOOL_TOPIC = { size_trade: "position size", check_budget: "room left under the loss ceilings",
  check_compliance: "restricted practices (hedging, copy trading, bots)", check_availability: "country availability" };
const RULE_TOPIC = { crossover: "the crossover (which loss ceiling binds)", reset: "the daily reset", fees: "fees",
  leverage: "leverage and margin", cross: "leverage and margin", drawdown: "max loss and drawdown", ladder: "position size",
  ruin: "max loss and drawdown", min_days: "minimum trading days", hold_limit: "hold limits and overnight",
  accounts: "restricted practices (hedging, copy trading, bots)", marketed_strategies: "restricted practices (hedging, copy trading, bots)",
  strategy_switching: "restricted practices (hedging, copy trading, bots)", opposite_positions: "restricted practices (hedging, copy trading, bots)",
  funded_stage: "the funded stage" };
// Firms by name: the three troid covers, and others by a fixed list (which firm to add next). Names, never quotes.
const COVERED = [["Bitfunded", /bit ?funded/i], ["BrightFunded", /bright ?funded/i], ["Crypto Fund Trader", /crypto ?fund ?trader|\bcft\b/i]];
const FIRM_KEYS = { bitfunded: "Bitfunded", brightfunded: "BrightFunded", crypto_fund_trader: "Crypto Fund Trader" };
const OTHERS = [["FTMO", /\bftmo\b/i], ["FundedNext", /funded ?next/i], ["The5ers", /the ?5 ?%?ers/i], ["Topstep", /topstep/i],
  ["Apex Trader Funding", /\bapex\b/i], ["E8 Markets", /\be8\b/i], ["Alpha Capital", /alpha capital/i], ["FunderPro", /funder ?pro/i],
  ["Breakout", /\bbreakout ?(prop|funding)\b/i], ["HyroTrader", /hyro ?trader/i], ["Funding Pips", /funding ?pips/i],
  ["Blue Guardian", /blue ?guardian/i], ["Maven", /\bmaven\b/i], ["FXIFY", /fxify/i], ["Goat Funded Trader", /goat funded/i],
  ["Instant Funding", /instant funding/i], ["MyFundedFutures", /my ?funded ?futures/i], ["Take Profit Trader", /take profit trader/i],
  ["Earn2Trade", /earn ?2 ?trade/i]];

// One stored entry → what it counts toward. Reads the message to match rules; returns labels only.
function classify(e) {
  const text = String(e.user || ""), topics = new Set(), firms = new Set(), tools = [];
  for (const [label, re] of TOPICS) if (re.test(text)) topics.add(label);
  for (const t of e.tool_calls || []) {
    tools.push(t.name);
    if (TOOL_TOPIC[t.name]) topics.add(TOOL_TOPIC[t.name]);
    if (t.name === "explain_rule" && t.input && RULE_TOPIC[t.input.topic]) topics.add(RULE_TOPIC[t.input.topic]);
    if (t.input && FIRM_KEYS[t.input.firm]) firms.add(FIRM_KEYS[t.input.firm]);
  }
  for (const [name, re] of COVERED) if (re.test(text)) firms.add(name);
  for (const [name, re] of OTHERS) if (re.test(text)) firms.add("not covered: " + name);
  if (!topics.size) topics.add("other");
  const outcome = e.ended ? "session ended" : e.refusal ? "model refusal" : e.error || e.reply == null ? "error" : "answered";
  return { topics: [...topics], firms: [...firms], tools, outcome, lang: e.lang || "?" };
}

// ISO 8601 week, UTC: "2026-W39". Monday to Monday.
function isoWeek(date) {
  const d = new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate()));
  const day = d.getUTCDay() || 7;
  d.setUTCDate(d.getUTCDate() + 4 - day);
  const y = d.getUTCFullYear(), w = Math.ceil(((d - Date.UTC(y, 0, 1)) / 86400000 + 1) / 7);
  return y + "-W" + String(w).padStart(2, "0");
}
function weekRange(week) {
  const m = /^(\d{4})-W(\d{2})$/.exec(String(week || ""));
  if (!m) throw new Error("week must look like 2026-W39");
  const y = +m[1], w = +m[2], jan4 = new Date(Date.UTC(y, 0, 4)), day = jan4.getUTCDay() || 7;
  const from = new Date(jan4.getTime() + ((w - 1) * 7 - (day - 1)) * 86400000);
  return [from, new Date(from.getTime() + 7 * 86400000)];
}
// The last complete week before `now`.
const lastWeek = (now) => isoWeek(new Date((now || new Date()).getTime() - 7 * 86400000));

function bump(o, k, n) { o[k] = (o[k] || 0) + (n || 1); }
const sorted = (o) => Object.fromEntries(Object.entries(o).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])));

// conversations: [[entry, entry, ...], ...] (one list per session). Counts the entries inside the week.
function aggregate(conversations, week, madeAt) {
  const [from, to] = weekRange(week);
  const out = { what: "ask troid, " + week + ": counts of the topics, firms, tools and languages in that week's messages, by fixed rules. " +
                      "No text from any conversation, no quotation, no session ID. Not published.",
                week, from_utc: from.toISOString(), to_utc: to.toISOString(), made_utc: (madeAt || new Date()).toISOString(),
                conversations: 0, messages: 0, languages: {}, topics: {}, firms: {}, tools: {}, outcomes: {} };
  for (const convo of conversations) {
    let counted = false;
    for (const e of convo) {
      const at = Date.parse(e && e.at);
      if (!(at >= from.getTime() && at < to.getTime())) continue;
      const c = classify(e);
      counted = true; out.messages++;
      bump(out.languages, c.lang); bump(out.outcomes, c.outcome);
      for (const t of c.topics) bump(out.topics, t);
      for (const f of c.firms) bump(out.firms, f);
      for (const t of c.tools) bump(out.tools, t);
    }
    if (counted) out.conversations++;
  }
  for (const k of ["languages", "topics", "firms", "tools", "outcomes"]) out[k] = sorted(out[k]);
  return out;
}

// Upstash's REST API, pipelined (one request, commands run in order, not as a transaction).
function upstash(url, token) {
  return async (cmds) => {
    const r = await fetch(url.replace(/\/+$/, "") + "/pipeline", { method: "POST", signal: AbortSignal.timeout(10000),
      headers: { authorization: "Bearer " + token, "content-type": "application/json" }, body: JSON.stringify(cmds) });
    const j = await r.json().catch(() => null);
    if (!r.ok || !Array.isArray(j) || j.some((x) => !x || x.error)) throw new Error("store " + r.status);
    return j.map((x) => x.result);
  };
}
// Read every stored conversation (SCAN conv:*, then LRANGE in batches), count the week, keep digest:<week> with no expiry.
async function run(kv, week, now) {
  const keys = [];
  let cursor = "0";
  do {
    const [[next, batch]] = await kv([["SCAN", cursor, "MATCH", "conv:*", "COUNT", "500"]]);
    cursor = String(next); keys.push(...batch);
  } while (cursor !== "0");
  const convos = [];
  for (let i = 0; i < keys.length; i += 100) {
    const lists = await kv(keys.slice(i, i + 100).map((k) => ["LRANGE", k, "0", "-1"]));
    for (const l of lists) convos.push((l || []).map((s) => { try { return JSON.parse(s); } catch (e) { return null; } }).filter(Boolean));
  }
  const digest = aggregate(convos, week, now);
  await kv([["SET", "digest:" + week, JSON.stringify(digest)]]);
  return digest;
}

module.exports = { classify, aggregate, isoWeek, weekRange, lastWeek, upstash, run, TOPICS };
