"use strict";
/* web/key_expiry.js against a local fake of the Admin API's key list. Spends nothing, calls no one.
 *
 *   node web/test_key_expiry.js
 */
const http = require("http");
let n = 0, failed = 0;
function ok(name, cond, info) {
  n++;
  if (cond) console.log("ok   " + name);
  else { failed++; console.log("FAIL " + name + (info === undefined ? "" : "  " + JSON.stringify(info).slice(0, 400))); }
}
const ADMIN = "sk-ant-admin01-" + "a".repeat(40), SEEN = [];
const at = (d) => new Date(Date.now() + d * 86400e3 + 3600e3).toISOString();
const PAGES = [
  { data: [{ id: "apikey_1", type: "api_key", name: "troid production", status: "active", expires_at: at(5), partial_key_hint: "sk-ant-api03-R2D...igAA",
             scope: { type: "workspace", workspace_id: "wrkspc_prod" }, workspace_id: "wrkspc_prod" },
           { id: "apikey_2", type: "api_key", name: "troid-eval", status: "active", expires_at: at(30), partial_key_hint: "sk-ant-api03-X9Z...b2QA",
             scope: { type: "workspace", workspace_id: "wrkspc_eval" }, workspace_id: "wrkspc_eval" }], has_more: true, last_id: "apikey_2" },
  { data: [{ id: "apikey_3", type: "api_key", name: "laptop", status: "active", expires_at: null, partial_key_hint: "sk-ant-api03-Q1W...zzAA",
             scope: { type: "organization" }, workspace_id: null }], has_more: false, last_id: "apikey_3" },
];
let mode = "ok";
const fake = http.createServer((req, res) => {
  const u = new URL(req.url, "http://x");
  SEEN.push({ path: u.pathname, q: Object.fromEntries(u.searchParams), key: req.headers["x-api-key"], version: req.headers["anthropic-version"] });
  const send = (code, j) => { res.writeHead(code, { "content-type": "application/json" }); res.end(JSON.stringify(j)); };
  if (mode === "401" || req.headers["x-api-key"] !== ADMIN) return send(401, { type: "error", error: { type: "authentication_error", message: "invalid x-api-key" } });
  send(200, u.searchParams.get("after_id") === "apikey_2" ? PAGES[1] : PAGES[0]);
});
const { main } = require("./key_expiry.js");
async function run(args, env) {
  let out = "";
  const code = await main(args, env, (s) => { out += s; });
  return { code, out };
}
fake.listen(0, "127.0.0.1", async () => {
  const base = `http://127.0.0.1:${fake.address().port}`;
  try {
    let r = await run([], { ANTHROPIC_ADMIN_KEY: ADMIN, ANTHROPIC_ADMIN_BASE_URL: base });
    ok("both pages read: the list follows has_more and last_id", r.out.startsWith("3 active API keys") && SEEN.length === 2 && SEEN[1].q.after_id === "apikey_2", [r.out, SEEN]);
    ok("the request: GET /v1/organizations/api_keys, active keys, the admin key and anthropic-version",
       SEEN.length === 2 && SEEN.every((s) => s.path === "/v1/organizations/api_keys" && s.q.status === "active" && s.q.limit === "100" && s.key === ADMIN && s.version === "2023-06-01"), SEEN);
    ok("each key: name, where it works, the hint, expiry and days left; soonest first", /troid production  ·  wrkspc_prod  ·  sk-ant-api03-R2D\.\.\.igAA  ·  expires \d{4}-\d\d-\d\d \d\d:\d\d UTC  ·  5 days left  ROTATE/.test(r.out)
       && /troid-eval  ·  wrkspc_eval  ·  .*30 days left\n/.test(r.out) && /laptop  ·  any workspace  ·  .*expires never\n/.test(r.out)
       && r.out.indexOf("troid production") < r.out.indexOf("troid-eval") && r.out.indexOf("troid-eval") < r.out.indexOf("laptop"), r.out);
    ok("a key within 14 days: exit 1, and the count to rotate", r.code === 1 && /1 key to rotate within 14 days\./.test(r.out), [r.code, r.out]);
    ok("never prints a key", !r.out.includes(ADMIN), r.out);
    r = await run(["--days", "3"], { ANTHROPIC_ADMIN_KEY: ADMIN, ANTHROPIC_ADMIN_BASE_URL: base });
    ok("--days 3: nothing due, exit 0", r.code === 0 && /None expires within 3 days\./.test(r.out) && !/ROTATE/.test(r.out), [r.code, r.out]);
    r = await run([], {});
    ok("no admin key in the environment: says so, exit 2, no request", r.code === 2 && /Set ANTHROPIC_ADMIN_KEY/.test(r.out), r);
    const before = SEEN.length;
    r = await run([], { ANTHROPIC_ADMIN_KEY: ADMIN, ANTHROPIC_ADMIN_BASE_URL: "https://example.com" });
    ok("the admin key goes nowhere but api.anthropic.com (or the local test)", r.code === 2 && SEEN.length === before && /local test only/.test(r.out), r);
    mode = "401";
    r = await run([], { ANTHROPIC_ADMIN_KEY: ADMIN, ANTHROPIC_ADMIN_BASE_URL: base });
    ok("a refused admin key: exit 2 with the API's error type", r.code === 2 && /answered 401 \(authentication_error\)/.test(r.out), r);
  } catch (e) { ok("ran", false, String(e && e.stack)); }
  fake.close();
  console.log(`RESULT: ${failed} failed (${n} checks)`);
  process.exitCode = failed ? 1 : 0;
});
