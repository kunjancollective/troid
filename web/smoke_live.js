"use strict";
/* The live smoke test for ask troid (launch handoff step 3). Spends a few model calls; run it after switch-on.

     node web/smoke_live.js                       # https://troid.ai
     node web/smoke_live.js https://troid.ai

   With KV_REST_API_URL and KV_REST_API_TOKEN in the environment (vercel env pull, or the Upstash console), it also
   reads the conversation store: the entries, their 30-day TTL, and that no address or user agent reached them.
   It checks: the disclosure comes first, with the session ID sentence; a sizing question returns a formula and its
   sources; a second message in the same session works; "should I buy a challenge" gets troid's refusal; the
   conversation is in the store with a 30-day TTL and no IP; deletion removes it at once. */
const crypto = require("crypto");
const BASE = (process.argv[2] || "https://troid.ai").replace(/\/+$/, "");
const KV_URL = (process.env.KV_REST_API_URL || process.env.UPSTASH_REDIS_REST_URL || "").replace(/\/+$/, "");
const KV_TOKEN = process.env.KV_REST_API_TOKEN || process.env.UPSTASH_REDIS_REST_TOKEN || "";
const UA = "troid-smoke/" + crypto.randomBytes(4).toString("hex");
let fails = 0;
const ok = (name, cond, got) => { console.log((cond ? "ok   " : "FAIL ") + name + (cond || got === undefined ? "" : "  " + JSON.stringify(got).slice(0, 300))); if (!cond) fails++; };
async function api(method, path, body, headers) {
  const r = await fetch(BASE + path, { method, headers: Object.assign({ "content-type": "application/json", "user-agent": UA }, headers || {}),
                                       body: body ? JSON.stringify(body) : undefined });
  return { status: r.status, j: await r.json().catch(() => ({})) };
}
async function kv(cmds) {
  const r = await fetch(KV_URL + "/multi-exec", { method: "POST", headers: { authorization: "Bearer " + KV_TOKEN, "content-type": "application/json" }, body: JSON.stringify(cmds) });
  return (await r.json()).map((x) => x.result);
}
(async () => {
  const s = await api("GET", "/api/troid");
  ok("GET: ask troid is on, with the store", s.status === 200 && s.j.enabled === true && s.j.store === true && s.j.retention_days === 30, s.j);
  if (!s.j.enabled) { console.log("RESULT: stopped; ask troid is not on"); process.exit(1); }

  const S = crypto.randomBytes(16).toString("hex"), hist = [];
  const say = async (text, session, sig) => { const m = hist.concat([{ role: "user", content: text }]);
    const r = await api("POST", "/api/troid", { messages: m, session, sig, disclosed: false, lang: "en" }); return { r, m }; };
  let { r, m } = await say("What is the crossover on a $100,000 Bitfunded 1-Step?", S, null);
  ok("first message: 200, the disclosure first, with the 30-day session sentence", r.status === 200 && r.j.reply.startsWith(s.j.disclosure)
     && /30 days under the session ID/.test(r.j.reply) && r.j.session === S && r.j.delete_token && r.j.sig, r.j);
  hist.push(...m, { role: "assistant", content: r.j.reply });
  const token = r.j.delete_token;
  ({ r, m } = await say("Size a short on the Bitfunded 1-Step: quota 100000, equity 96000, day start 96000, entry 77872, stop 78105.6, risk 0.5%.", S, r.j.sig));
  ok("second message in the same session: 200", r.status === 200, r.j);
  ok("sizing: a tool call, a formula and its sources with read dates", r.j.tool_calls >= 1 && /(=|×|min\()/.test(r.j.reply) && /(20\d\d-\d\d-\d\d|read|Criteria to be Success|FAQ)/i.test(r.j.reply), r.j);

  const S2 = crypto.randomBytes(16).toString("hex");
  const q = await api("POST", "/api/troid", { messages: [{ role: "user", content: "Should I buy a challenge?" }], session: S2, disclosed: true, lang: "en" });
  ok("'should I buy a challenge': refused and redirected", q.status === 200 && /doesn't recommend/i.test(q.j.reply), q.j);

  if (KV_URL && KV_TOKEN) {
    const [len, ttl, items] = await kv([["LLEN", "conv:" + S], ["TTL", "conv:" + S], ["LRANGE", "conv:" + S, "0", "-1"]]);
    ok("store: two entries under conv:<session>", len === 2, len);
    ok("store: TTL about 30 days", ttl > 2_592_000 - 600 && ttl <= 2_592_000, ttl);
    const raw = (items || []).join("\n");
    ok("store: no user agent, no address field", !raw.includes(UA) && !/"ip"\s*:|x-forwarded|x-real-ip/i.test(raw), raw.slice(0, 200));
  } else console.log("skip store checks: set KV_REST_API_URL and KV_REST_API_TOKEN to read the store");

  let d = await api("DELETE", "/api/troid?session=" + S, null, {});
  ok("delete without the token: refused", d.status === 403, d);
  d = await api("DELETE", "/api/troid?session=" + S, null, { "x-troid-token": token });
  ok("delete with the session's token: deleted", d.status === 200 && d.j.deleted === true, d);
  if (KV_URL && KV_TOKEN) {
    const [exists] = await kv([["EXISTS", "conv:" + S]]);
    ok("store: the conversation is gone", exists === 0, exists);
  }
  const d2 = await api("DELETE", "/api/troid?session=" + S2, null, { "x-troid-token": q.j.delete_token });
  ok("clean-up: the refusal session deleted too", d2.status === 200, d2);
  console.log(`RESULT: ${fails} failed`);
  process.exit(fails ? 1 : 0);
})().catch((e) => { console.log("FAIL " + e); process.exit(1); });
