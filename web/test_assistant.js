"use strict";
/* Offline checks for api/troid.js: the tool port against the calculator's reference case,
   then the handler end to end against a scripted fake of the Messages API. Spends nothing. */
const assert = require("assert");
process.env.TROID_ASSISTANT = "on"; process.env.ANTHROPIC_API_KEY = "test-key";
process.env.ANTHROPIC_API_URL = "http://fake.invalid/v1/messages";
const handler = require("./api/troid.js");
const T = handler.tools;
let n = 0;
function ok(name, cond, got) { n++; if (!cond) { console.log("FAIL " + name, got === undefined ? "" : JSON.stringify(got).slice(0, 300)); process.exitCode = 1; } else console.log("ok   " + name); }

// --- reference case 2 (web/README.md): Bitfunded 1-Step, equity below the crossover, short, 0.3% stop
let r = T.size_trade({ firm: "bitfunded", product: "1step", quota: 100000, equity: 96000, day_start: 96000, side: "short", entry: 77872, stop: 77872 * 1.003, target_r: 2 });
ok("ref2 verdict OK", r.verdict === "OK", r);
ok("ref2 binding max drawdown", r.binding === "max drawdown", r.binding);
ok("ref2 budgets 4000 / 2000", r.daily_budget === 4000 && r.dd_budget === 2000, [r.daily_budget, r.dd_budget]);
ok("ref2 risk 480", r.risk === 480, r.risk);
ok("ref2 qty 1.622095", r.quantity === 1.622095, r.quantity);
ok("ref2 notional 126315.79", r.notional === 126315.79, r.notional);
ok("ref2 margin 25263.16", r.margin === 25263.16, r.margin);
ok("ref2 fees 101.05 = 21.05%", r.fees === 101.05 && r.fee_share_of_risk_pct === 21.05, [r.fees, r.fee_share_of_risk_pct]);
ok("ref2 consumes 24, losses left 4", r.consumes_pct_of_budget === 24 && r.losses_remaining === 4, [r.consumes_pct_of_budget, r.losses_remaining]);
ok("ref2 crossover 98000", r.crossover_equity === 98000, r.crossover_equity);
ok("ref2 breakers order", r.circuit_breakers.map((b) => b.event).join(">") === "your stop>max-loss floor>daily limit>exchange liquidation (cross)", r.circuit_breakers);
ok("ref2 cross liq 75.88", r.circuit_breakers[3].adverse_move_pct === 75.88, r.circuit_breakers[3]);

// --- BrightFunded: max_balance_equity + trailing on equity, fee and leverage pending
r = T.size_trade({ firm: "brightfunded", product: "1step", quota: 100000, equity: 100000, side: "long", entry: 77872, stop: 74814 });
ok("BF binding daily 3000", r.binding === "daily loss limit" && r.effective_budget === 3000, [r.binding, r.effective_budget]);
ok("BF trailing floor 94000", r.dd_floor === 94000 && r.trailing_locked === false, [r.dd_floor, r.trailing_locked]);
ok("BF fees pending, gross qty 0.163506", r.fees === null && r.pending.includes("fee_per_side") && r.pending.includes("max_leverage") && r.quantity === 0.163506, r);
ok("BF equity note", r.notes.some((x) => x.includes("trails on equity intraday")), r.notes);
r = T.check_budget({ firm: "brightfunded", product: "1step", quota: 100000, equity: 106000, day_start: 106000, high_water_mark: 106000, high_at_rollover: 106000 });
ok("BF locked at +6%", r.trailing_locked === true && r.dd_floor === 100000 && r.daily_budget === 3000, r);

// --- CFT: day-start basis; instant has drawdown pending; leverage capped at 100
r = T.check_budget({ firm: "crypto_fund_trader", product: "1phase", quota: 100000, equity: 96000, day_start: 96000 });
ok("CFT day-start budget 3840, dd 2000", r.daily_budget === 3840 && r.dd_budget === 2000 && r.binding === "max drawdown", r);
ok("CFT day-start crossover 97916.67", r.crossover_equity === 97916.67, r.crossover_equity);
r = T.size_trade({ firm: "crypto_fund_trader", product: "instant", quota: 100000, equity: 100000, side: "long", entry: 77872, stop: 74814, leverage: 150 });
ok("CFT instant drawdown pending, sized on daily", r.pending.includes("drawdown_type") && r.binding === "daily loss limit" && r.dd_floor === null, r);
ok("CFT leverage capped 100", r.leverage_used === 100 && r.notes.some((x) => x.includes("capped at 100")), r);

// --- unknown firm / product, blocks, compliance, rules
ok("unknown firm", /unknown firm/.test(T.size_trade({ firm: "ftmo", product: "x", quota: 1, equity: 1, side: "long", entry: 2, stop: 1 }).error));
ok("block: stop above entry on a long", T.size_trade({ firm: "bitfunded", product: "1step", quota: 100000, equity: 100000, side: "long", entry: 100, stop: 101 }).verdict === "BLOCK");
r = T.check_compliance({ firm: "bitfunded", product: "1step", symbol: "SOLUSDT", hold_days: 12, open_trades: 6, margin_pct_of_capital: 70, trading_days_so_far: 3, uses_third_party_strategy: true, accounts_at_this_level: 2, closed_trades_this_stage: 1 });
ok("compliance: seven findings", r.findings.length === 7 && !r.clear, r.findings.map((f) => f.rule));
ok("compliance: other firm pending", T.check_compliance({ firm: "brightfunded" }).pending === true);
ok("explain_rule crossover", /98,000/.test(T.explain_rule({ topic: "crossover" }).explanation));
ok("explain_rule unknown", /unknown topic/.test(T.explain_rule({ topic: "moon" }).error));

// --- handler end to end with a scripted fake of the API
const calls = [];
global.fetch = async (url, opts) => {
  const body = JSON.parse(opts.body); calls.push(body);
  if (calls.length === 1) ok("request carries system blocks with cache_control and 4 tools", body.system.length === 3 && body.system[2].cache_control.type === "ephemeral" && body.tools.length === 4);
  const last = body.messages[body.messages.length - 1];
  const hasResult = Array.isArray(last.content) && last.content[0].type === "tool_result";
  let out;
  if (hasResult) out = { stop_reason: "end_turn", content: [{ type: "text", text: "Risk $480.00 (DERIVED). Not financial advice. Verify with the firm before acting." }] };
  else out = { stop_reason: "tool_use", content: [{ type: "tool_use", id: "tu_1", name: "size_trade", input: { firm: "bitfunded", product: "1step", quota: 100000, equity: 96000, day_start: 96000, side: "short", entry: 77872, stop: 78105.616 } }] };
  return { ok: true, json: async () => out };
};
function fakeRes() { const r = { headers: {}, body: "", setHeader(k, v) { this.headers[k] = v; }, end(b) { this.body = b; } }; return r; }
(async () => {
  let res = fakeRes();
  await handler({ method: "GET", headers: {} }, res);
  let j = JSON.parse(res.body);
  ok("GET reports flag, models, context sizes, 3 firms", j.enabled === true && j.context.firms.length === 3 && j.context.troid_md > 1000 && j.tools.length === 4, j);
  res = fakeRes();
  await handler({ method: "POST", headers: { "x-forwarded-for": "203.0.113.9" }, body: { messages: [{ role: "user", content: "size it" }] } }, res);
  j = JSON.parse(res.body);
  ok("POST: Haiku wanted a tool, rerun on Sonnet, one tool call, reply", res.statusCode === 200 && j.model === "claude-sonnet-5" && j.tool_calls === 1 && /480/.test(j.reply), j);
  ok("three upstream calls: haiku, sonnet, sonnet with tool_result", calls.length === 3 && calls[0].model === "claude-haiku-4-5-20251001" && calls[1].model === "claude-sonnet-5" && calls[2].messages.length === 3, calls.map((c) => c.model));
  res = fakeRes();
  await handler({ method: "POST", headers: {}, body: { messages: [{ role: "assistant", content: "x" }] } }, res);
  ok("POST: bad shape → 400", res.statusCode === 400);
  for (let i = 0; i < 25; i++) { res = fakeRes(); await handler({ method: "POST", headers: { "x-forwarded-for": "198.51.100.7" }, body: { messages: [{ role: "user", content: "hi" }] } }, res); }
  ok("rate limit: 21st message in an hour → 429", res.statusCode === 429, res.statusCode);
  process.env.TROID_ASSISTANT = "off";
  delete require.cache[require.resolve("./api/troid.js")];
  const off = require("./api/troid.js"); res = fakeRes(); const before = calls.length;
  await off({ method: "POST", headers: {}, body: { messages: [{ role: "user", content: "hi" }] } }, res);
  ok("flag off → 503, no upstream call", res.statusCode === 503 && calls.length === before, res.statusCode);
  console.log(`RESULT: ${process.exitCode ? "FAILED" : "0 failed"} (${n} checks)`);
})();
