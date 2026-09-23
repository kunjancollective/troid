"use strict";
/* Offline checks for api/troid.js: the tool port against the calculator's reference case,
   then the handler end to end against a scripted fake of the Messages API. Spends nothing. */
const assert = require("assert");
process.env.TROID_ASSISTANT = "on"; process.env.ANTHROPIC_API_KEY = "test-key";
process.env.ANTHROPIC_BASE_URL = "http://127.0.0.1:18765";   // the local fake below
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

// --- CFT: day-start basis; Instant has drawdown pending; Instant 5× (Student band), 1-Phase 100× (Advanced)
r = T.check_budget({ firm: "crypto_fund_trader", product: "1phase", quota: 100000, equity: 96000, day_start: 96000 });
ok("CFT day-start budget 3840, dd 2000", r.daily_budget === 3840 && r.dd_budget === 2000 && r.binding === "max drawdown", r);
ok("CFT day-start crossover 97916.67", r.crossover_equity === 97916.67, r.crossover_equity);
r = T.size_trade({ firm: "crypto_fund_trader", product: "instant", quota: 10000, equity: 10000, side: "long", entry: 77872, stop: 74814, leverage: 150 });
ok("CFT instant drawdown pending, sized on daily", r.pending.includes("drawdown_type") && r.binding === "daily loss limit" && r.dd_floor === null, r);
ok("CFT Instant capped at 5 (Student band, $2.5k-$10k)", r.leverage_used === 5 && r.notes.some((x) => x.includes("capped at 5×")), r);
r = T.size_trade({ firm: "crypto_fund_trader", product: "1phase", quota: 100000, equity: 100000, side: "long", entry: 77872, stop: 74814, leverage: 150 });
ok("CFT 1-Phase capped at 100 (Advanced)", r.leverage_used === 100 && r.notes.some((x) => x.includes("capped at 100×")), r);

// --- unknown firm / product, blocks, compliance, rules
ok("unknown firm", /unknown firm/.test(T.size_trade({ firm: "ftmo", product: "x", quota: 1, equity: 1, side: "long", entry: 2, stop: 1 }).error));
ok("block: stop above entry on a long", T.size_trade({ firm: "bitfunded", product: "1step", quota: 100000, equity: 100000, side: "long", entry: 100, stop: 101 }).verdict === "BLOCK");
r = T.check_compliance({ firm: "bitfunded", product: "1step", symbol: "SOLUSDT", hold_days: 12, open_trades: 6, margin_pct_of_capital: 70, trading_days_so_far: 3, uses_third_party_strategy: true, accounts_at_this_level: 2, closed_trades_this_stage: 1 });
ok("compliance: seven findings", r.findings.length === 7 && !r.clear, r.findings.map((f) => f.rule));
ok("compliance: other firm pending", T.check_compliance({ firm: "brightfunded" }).pending === true);
ok("explain_rule crossover", /98,000/.test(T.explain_rule({ topic: "crossover" }).explanation));
ok("explain_rule unknown", /unknown topic/.test(T.explain_rule({ topic: "moon" }).error));


// --- section 4: provenance in tool output, leverage bands, reset text
r = T.size_trade({ firm: "bitfunded", product: "1step", quota: 100000, equity: 96000, day_start: 96000, side: "short", entry: 77872, stop: 77872 * 1.003 });
ok("sources: every rule used is listed", r.sources.map((x) => x.rule).join("|") === "daily 4%|daily basis (initial)|max 6%|drawdown type (static)|fee 0.04% per side|leverage cap 5×", r.sources);
ok("sources: Criteria read 2026-09-18, FAQ read 2026-09-21", r.sources[0].read_on[0] === "2026-09-18" && /FAQ/.test(r.sources[1].document_section) && r.sources[1].read_on[0] === "2026-09-21", r.sources);
ok("assumption named: MMR", /0\.5% maintenance margin/.test(r.assumptions[0]));
r = T.size_trade({ firm: "bitfunded", product: "2step_s1", quota: 100000, equity: 100000, side: "long", entry: 77872, stop: 74814 });
ok("2-Step S1: limits, fee and leverage say not yet recorded", ["daily 5%", "max 10%", "fee 0.04% per side", "leverage cap 5×"].every((k) => r.sources.find((x) => x.rule === k).source === "not yet recorded"), r.sources);
r = T.size_trade({ firm: "crypto_fund_trader", product: "1phase", quota: 10000, equity: 10000, side: "long", entry: 77872, stop: 74814, leverage: 150 });
ok("CFT 1-Phase at $10k: Student band 5×, cited to the Student class", r.leverage_used === 5 && /Student up to \$25k/.test(r.sources.find((x) => /leverage/.test(x.rule)).document_section), r);
r = T.size_trade({ firm: "crypto_fund_trader", product: "1phase", quota: 30000, equity: 30000, side: "long", entry: 77872, stop: 74814, leverage: 150 });
ok("CFT 1-Phase at $30k: cap pending, held to 100×", r.leverage_used === 100 && r.pending.includes("max_leverage") && r.notes.some((x) => /held to 100×/.test(x)), r);
ok("reset rule: CFT at 00:05 UTC", /Crypto Fund Trader resets at 00:05 UTC/.test(T.explain_rule({ topic: "reset" }).explanation));

// --- handler end to end: the real SDK against a local fake of the Messages API
const http = require("http");
const calls = [];
let script = null;            // (body) => { status, json }
const fake = http.createServer((req, res) => {
  let raw = ""; req.on("data", (c) => (raw += c)); req.on("end", () => {
    const body = JSON.parse(raw); calls.push(body);
    const out = script(body);
    res.writeHead(out.status || 200, { "content-type": "application/json", "request-id": "req_test" });
    res.end(JSON.stringify(out.json));
  });
});
const msg = (stop_reason, content, extra) => ({ status: 200, json: Object.assign({ id: "msg_" + calls.length, type: "message", role: "assistant", model: "m",
  content, stop_reason, stop_sequence: null, usage: { input_tokens: 10, output_tokens: 10 } }, extra || {}) });
function fakeRes() { return { headers: {}, body: "", setHeader(k, v) { this.headers[k] = v; }, end(b) { this.body = b; } }; }
async function post(messages, extra, ip) {
  const res = fakeRes();
  await handler({ method: "POST", headers: { "x-forwarded-for": ip || "203.0.113." + calls.length }, body: Object.assign({ messages }, extra || {}) }, res);
  return { status: res.statusCode, j: JSON.parse(res.body) };
}
const F = handler.fixed;
fake.listen(18765, async () => {
  try {
    let res = fakeRes();
    await handler({ method: "GET", headers: {} }, res);
    let j = JSON.parse(res.body);
    ok("GET: flag, models, context incl. support.md, disclosure", j.enabled === true && j.models.lookup === "claude-haiku-4-5" && j.models.tools === "claude-sonnet-5"
       && j.context.support_md > 500 && j.context.firms.length === 3 && j.disclosure === F.DISCLOSURE, j);

    // 1. a lookup: Haiku answers; the service prepends the disclosure on the first message
    script = () => msg("end_turn", [{ type: "text", text: "troid's desk sizes against both ceilings (DERIVED)." }]);
    calls.length = 0;
    let r = await post([{ role: "user", content: "what is the crossover?" }]);
    ok("lookup: one Haiku call, disclosure first", r.status === 200 && calls.length === 1 && calls[0].model === "claude-haiku-4-5" && r.j.reply.startsWith(F.DISCLOSURE), r.j);
    ok("request: support.md in the system prompt, cache breakpoint on the last block, 4 tools", calls[0].system.length === 4 && /support\.md/.test(calls[0].system[1].text)
       && calls[0].system[3].cache_control.type === "ephemeral" && calls[0].tools.length === 4 && calls[0].max_tokens === 4096, calls[0].system.map((b) => b.text.slice(0, 40)));
    ok("guardrails carry the audit's additions", ["support.md section 2", "scam", "doesn't recommend", F.END_SESSION, "opening disclosure"].every((k) => calls[0].system[0].text.includes(k)));
    r = await post([{ role: "user", content: "what is the crossover?" }], { disclosed: true });
    ok("page already showed the disclosure: not repeated", !r.j.reply.includes(F.DISCLOSURE), r.j.reply);
    r = await post([{ role: "user", content: "a" }, { role: "assistant", content: "b" }, { role: "user", content: "c" }]);
    ok("later turns: no disclosure", !r.j.reply.includes(F.DISCLOSURE), r.j.reply);

    // 2. a tool turn: Haiku wants a tool, rerun on Sonnet, tool result carries sources
    script = (b) => {
      const last = b.messages[b.messages.length - 1];
      if (Array.isArray(last.content) && last.content[0].type === "tool_result") return msg("end_turn", [{ type: "text", text: "Risk $480.00 (DERIVED)." }]);
      return msg("tool_use", [{ type: "thinking", thinking: "", signature: "sig" }, { type: "tool_use", id: "tu_1", name: "size_trade",
        input: { firm: "bitfunded", product: "1step", quota: 100000, equity: 96000, day_start: 96000, side: "short", entry: 77872, stop: 78105.616 } }]);
    };
    calls.length = 0;
    r = await post([{ role: "user", content: "size it" }], { disclosed: true });
    const toolResult = JSON.parse(calls[2].messages[2].content[0].content);
    ok("tool turn: haiku, sonnet, sonnet with the tool result", calls.map((c) => c.model).join(",") === "claude-haiku-4-5,claude-sonnet-5,claude-sonnet-5" && r.j.tool_calls === 1 && calls[1].max_tokens === 8192, calls.map((c) => c.model));
    ok("tool turn: assistant content passed back unchanged, thinking block included", calls[2].messages[1].content[0].type === "thinking" && calls[2].messages[1].content[0].signature === "sig");
    ok("tool result carries sources and the risk", toolResult.risk === 480 && toolResult.sources.length === 6, toolResult);

    // 3. refusal: a fixed reply, never partial content
    script = () => msg("refusal", [{ type: "text", text: "partial" }], { stop_details: { type: "refusal", category: null, explanation: null } });
    r = await post([{ role: "user", content: "x" }], { disclosed: true });
    ok("refusal: the fixed reply", r.j.reply === F.REFUSAL_REPLY, r.j);

    // 4. abuse: the sentinel ends the session; the service writes the words
    script = () => msg("end_turn", [{ type: "text", text: F.END_SESSION }]);
    r = await post([{ role: "user", content: "abuse" }, { role: "assistant", content: "warning" }, { role: "user", content: "abuse again" }]);
    ok("abuse: ended, fixed reply, no disclosure, sentinel never shown", r.j.ended === true && r.j.reply === F.ENDED_REPLY && !r.j.reply.includes(F.END_SESSION), r.j);

    // 5. max_tokens: the cut is said out loud
    script = () => msg("max_tokens", [{ type: "text", text: "long answer" }]);
    r = await post([{ role: "user", content: "x" }], { disclosed: true });
    ok("max_tokens: the answer says it was cut", /length limit/.test(r.j.reply), r.j.reply);

    // 6. upstream 429: a typed SDK error becomes "busy"
    script = () => ({ status: 429, json: { type: "error", error: { type: "rate_limit_error", message: "slow down" } } });
    r = await post([{ role: "user", content: "x" }], { disclosed: true });
    ok("429 upstream: 503 busy, via Anthropic.RateLimitError", r.status === 503 && /busy/.test(r.j.error), r);

    // 7. shape, rate limit, flag
    res = fakeRes();
    await handler({ method: "POST", headers: {}, body: { messages: [{ role: "assistant", content: "x" }] } }, res);
    ok("POST: bad shape → 400", res.statusCode === 400);
    script = () => msg("end_turn", [{ type: "text", text: "ok" }]);
    let last;
    for (let i = 0; i < 21; i++) last = await post([{ role: "user", content: "hi" }], { disclosed: true }, "198.51.100.7");
    ok("rate limit: 21st message in an hour → 429", last.status === 429, last.status);
    process.env.TROID_ASSISTANT = "off";
    delete require.cache[require.resolve("./api/troid.js")];
    const off = require("./api/troid.js"); res = fakeRes(); const before = calls.length;
    await off({ method: "POST", headers: {}, body: { messages: [{ role: "user", content: "hi" }] } }, res);
    ok("flag off → 503, no upstream call", res.statusCode === 503 && calls.length === before, res.statusCode);
  } catch (e) { ok("no exception in the handler tests", false, String(e && e.stack)); }
  fake.close();
  console.log(`RESULT: ${process.exitCode ? "FAILED" : "0 failed"} (${n} checks)`);
});
