"use strict";
/* Offline checks for the weekly question digest (lib/faq_digest.js, api/digest.js) against a local fake of Upstash's
   REST pipeline. Spends nothing. */
const http = require("http");
process.env.KV_REST_API_URL = "http://127.0.0.1:18776"; process.env.KV_REST_API_TOKEN = "t";
const D = require("./lib/faq_digest.js");
const route = require("./api/digest.js");
let n = 0, failed = 0;
const ok = (name, cond, got) => { n++; if (!cond) { failed++; console.log("FAIL " + name, got === undefined ? "" : JSON.stringify(got).slice(0, 400)); } else console.log("ok   " + name); };

const CANARY = "CANARY-7781 my account is 5550123";
const S1 = "0123456789abcdef0123456789abcdef", S2 = "fedcba9876543210fedcba9876543210", S3 = "00000000000000000000000000000abc";
const at = (s) => new Date(s).toISOString();
const E = (when, user, extra) => JSON.stringify(Object.assign({ at: at(when), lang: "en", user, reply: "r", model: "m", tool_calls: [], sources: [] }, extra || {}));
const KV = new Map([
  ["conv:" + S1, [E("2026-09-22T10:00Z", "Size a short on Bitfunded 1-Step, " + CANARY,
                    { tool_calls: [{ name: "size_trade", input: { firm: "bitfunded", product: "1step" }, result: { risk: 480 } }] }),
                  E("2026-09-22T10:05Z", "when does the daily reset happen?", { tool_calls: [{ name: "explain_rule", input: { topic: "reset" } }] })]],
  ["conv:" + S2, [E("2026-09-24T09:00Z", "should I buy FTMO or BrightFunded?", { refusal: 1 }), E("2026-09-27T23:59Z", "zzz nothing matches", { reply: null, error: 503 })]],
  ["conv:" + S3, [E("2026-09-20T23:59Z", "out of the week: fees?")]],   // the Sunday before
  ["other:key", ["not a conversation"]],
]);
const CMDS = [];
const kv = http.createServer((req, res) => {
  let raw = ""; req.on("data", (c) => (raw += c)); req.on("end", () => {
    if (req.headers.authorization !== "Bearer t" || req.url !== "/pipeline") { res.writeHead(401); return res.end("{}"); }
    const cmds = JSON.parse(raw); CMDS.push(...cmds);
    const out = cmds.map(([op, ...a]) => {
      if (op === "SCAN") { const re = new RegExp("^" + a[2].replace("*", ".*") + "$"); return { result: ["0", [...KV.keys()].filter((k) => re.test(k))] }; }
      if (op === "LRANGE") return { result: KV.get(a[0]) || [] };
      if (op === "SET") { KV.set(a[0], a[1]); return { result: "OK" }; }
      if (op === "GET") return { result: KV.get(a[0]) || null };
      return { error: "unknown " + op };
    });
    res.writeHead(200, { "content-type": "application/json" }); res.end(JSON.stringify(out));
  });
});
const fakeRes = () => ({ statusCode: 200, headers: {}, body: "", setHeader(k, v) { this.headers[k] = v; }, end(b) { this.body = b; } });
async function call(headers, url) { const r = fakeRes(); await route({ method: "GET", headers: headers || {}, url: url || "/api/digest", query: {} }, r); return { status: r.statusCode, j: JSON.parse(r.body) }; }

kv.listen(18776, async () => {
  try {
    // classify: labels by rule, never the user's words
    let c = D.classify(JSON.parse(E("2026-09-22T10:00Z", "Is FunderPro legit? What about the crossover on bright funded", {})));
    ok("classify: topics and firms by rule", c.topics.includes("is it legit") && c.topics.includes("the crossover (which loss ceiling binds)")
       && c.firms.includes("BrightFunded") && c.firms.includes("not covered: FunderPro") && c.outcome === "answered", c);
    c = D.classify({ user: "¿cuánto puedo arriesgar?", lang: "es", tool_calls: [{ name: "check_budget", input: { firm: "crypto_fund_trader" } }] });
    ok("classify: a tool call names the topic and firm in any language", c.topics[0] === "room left under the loss ceilings" && c.firms[0] === "Crypto Fund Trader" && c.lang === "es", c);
    ok("classify: nothing matched is 'other'", D.classify({ user: "hmm" }).topics.join() === "other");

    // weeks
    ok("ISO week of 24 Sep 2026 is 2026-W39, Monday 21 to Monday 28", D.isoWeek(new Date("2026-09-24T12:00Z")) === "2026-W39"
       && D.weekRange("2026-W39")[0].toISOString() === "2026-09-21T00:00:00.000Z" && D.weekRange("2026-W39")[1].toISOString() === "2026-09-28T00:00:00.000Z");
    ok("the cron's Monday counts the week just ended", D.lastWeek(new Date("2026-09-28T04:30Z")) === "2026-W39");

    // the route: nobody but the cron
    delete process.env.CRON_SECRET;
    let r = await call({});
    ok("no CRON_SECRET: 503, nothing counted", r.status === 503 && !CMDS.length, r);
    process.env.CRON_SECRET = "s3cret-s3cret-s3cret-1234";
    r = await call({ authorization: "Bearer wrong" });
    ok("wrong secret: 401, nothing counted", r.status === 401 && !CMDS.length, r);
    r = await call({ authorization: "Bearer s3cret-s3cret-s3cret-1234" }, "/api/digest?week=2026-39");
    ok("malformed week: 400", r.status === 400, r);
    r = await call({ authorization: "Bearer s3cret-s3cret-s3cret-1234" }, "/api/digest?week=2026-W39");
    ok("the cron: 200 with totals only", r.status === 200 && r.j.key === "digest:2026-W39" && r.j.conversations === 2 && r.j.messages === 4
       && Object.keys(r.j).sort().join() === "conversations,key,messages,topics,week", r.j);

    const raw = KV.get("digest:2026-W39"), d = JSON.parse(raw);
    ok("digest: the week's messages only (the Sunday before is out)", d.messages === 4 && d.conversations === 2 && !("fees" in d.topics), d);
    ok("digest: topics, firms, tools, languages and outcomes counted", d.topics["position size"] === 1 && d.topics["the daily reset"] === 1
       && d.topics["asked for a recommendation"] === 1 && d.topics.other === 1 && d.firms.Bitfunded === 1 && d.firms.BrightFunded === 1
       && d.firms["not covered: FTMO"] === 1 && d.tools.size_trade === 1 && d.tools.explain_rule === 1 && d.languages.en === 4
       && d.outcomes["model refusal"] === 1 && d.outcomes.error === 1 && d.outcomes.answered === 2, d);
    ok("digest: no message text, no quotation, no session ID", ![CANARY, "CANARY", "5550123", "should I buy", "daily reset happen", "zzz", S1, S2, S3, "conv:"].some((s) => raw.includes(s)), raw.slice(0, 300));
    ok("digest: kept with no expiry (SET, never EXPIRE)", CMDS.some((x) => x[0] === "SET" && x[1] === "digest:2026-W39" && x.length === 3) && !CMDS.some((x) => x[0] === "EXPIRE"), CMDS.filter((x) => x[0] !== "LRANGE"));
    ok("digest: only conversation keys read", CMDS.filter((x) => x[0] === "LRANGE").every((x) => x[1].startsWith("conv:")));
  } catch (e) { ok("no exception", false, String(e && e.stack)); }
  kv.close();
  console.log(`RESULT: ${failed ? failed + " failed" : "0 failed"} (${n} checks)`);
  process.exit(failed ? 1 : 0);
});
