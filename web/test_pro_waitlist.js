"use strict";
/* troid Pro's waitlist (launch handoff 2026-09-26, 6.4 step 1): web/api/pro/waitlist.js against a local fake of Upstash's
 * REST API, and web/api/pro/page.js's waitlist views. Spends nothing, calls no one.
 *
 *   node web/test_pro_waitlist.js
 */
const http = require("http");
const path = require("path");
let n = 0, failed = 0;
function ok(name, cond, info) {
  n++;
  if (cond) console.log("ok   " + name);
  else { failed++; console.log("FAIL " + name + (info === undefined ? "" : "  " + JSON.stringify(info).slice(0, 500))); }
}

// Upstash's REST API, as much as the waitlist uses: POST /multi-exec with SET (EX) and DEL
const KV = new Map(), KV_CALLS = [];
let kvDown = false;
const kv = http.createServer((req, res) => {
  let raw = ""; req.on("data", (c) => (raw += c)); req.on("end", () => {
    const send = (code, j) => { res.writeHead(code, { "content-type": "application/json" }); res.end(JSON.stringify(j)); };
    if (req.headers.authorization !== "Bearer test-store-token") return send(401, { error: "unauthorized" });
    if (kvDown) return send(500, { error: "down" });
    const cmds = JSON.parse(raw); KV_CALLS.push({ path: req.url, cmds });
    send(200, cmds.map(([op, key, ...a]) => {
      if (op === "SET") { KV.set(key, { value: a[0], ttl: a[1] === "EX" ? +a[2] : -1 }); return { result: "OK" }; }
      if (op === "DEL") return { result: KV.delete(key) ? 1 : 0 };
      return { error: "unknown command " + op };
    }));
  });
});

const WL_KEY = "w".repeat(40);
function fresh(env) {
  for (const k of ["TROID_WAITLIST", "TROID_WAITLIST_KEY", "KV_REST_API_URL", "KV_REST_API_TOKEN", "TROID_PRO"]) delete process.env[k];
  Object.assign(process.env, env);
  for (const m of ["./api/pro/waitlist.js", "./api/pro/page.js"]) delete require.cache[require.resolve(m)];
  return { wl: require("./api/pro/waitlist.js"), page: require("./api/pro/page.js") };
}
function fakeRes() { return { headers: {}, body: "", statusCode: 200, setHeader(k, v) { this.headers[k.toLowerCase()] = v; }, end(b) { this.body = b || ""; } }; }
const LOGS = [], log0 = console.log;
async function call(h, body, opts) {
  opts = opts || {};
  const res = fakeRes();
  const headers = Object.assign({ "content-type": "application/json", "x-real-ip": opts.ip || "203.0.113.9" }, opts.headers || {});
  console.log = (x) => LOGS.push(x);
  try { await h({ method: opts.method || "POST", headers, body, url: opts.url || "/api/pro/waitlist", query: opts.query }, res); } finally { console.log = log0; }
  let j = null; try { j = JSON.parse(res.body); } catch (e) { j = res.body; }
  return { status: res.statusCode, j, headers: res.headers };
}
async function view(p, v, method) {
  const res = fakeRes();
  await p({ method: method || "GET", headers: {}, url: "/api/pro/page?view=" + v, query: { view: v } }, res);
  return res;
}

kv.listen(0, "127.0.0.1", async () => {
  const STORE = `http://127.0.0.1:${kv.address().port}`;
  const ENV = { TROID_WAITLIST: "on", TROID_WAITLIST_KEY: WL_KEY, KV_REST_API_URL: STORE, KV_REST_API_TOKEN: "test-store-token" };
  try {
    // off: nothing answers, as before it existed
    let { wl, page } = fresh({});
    let r = await call(wl, { email: "a@example.com", pro: true });
    ok("off: the waitlist answers 404", r.status === 404, r);
    let pr = await view(page, "pro");
    ok("off: /pro answers 404 (troid Pro's test mode off too)", pr.statusCode === 404, pr.statusCode);
    ({ wl, page } = fresh({ TROID_WAITLIST: "on", TROID_WAITLIST_KEY: "short", KV_REST_API_URL: STORE, KV_REST_API_TOKEN: "test-store-token" }));
    r = await call(wl, { email: "a@example.com", pro: true });
    ok("a key under 32 bytes: still off", r.status === 404 && (await view(page, "waitlist")).statusCode === 404, r.status);

    ({ wl, page } = fresh(ENV));
    // the page
    pr = await view(page, "pro");
    ok("on, test mode off (production): /pro is the waitlist page", pr.statusCode === 200 && /troid Pro is in preparation\./.test(pr.body)
       && /id="wl"/.test(pr.body) && pr.headers["referrer-policy"] === "no-referrer" && !pr.headers["x-robots-tag"], [pr.statusCode, pr.headers]);
    ok("the page has no price tape: no TradingView script, no ticker.js, no tape where an email is typed",
       !/<script[^>]*(tradingview|embed-widget|\/ticker\.js)/i.test(pr.body) && !/class="tk[" ]/.test(pr.body) && /<script[^>]*>/.test(pr.body),
       (pr.body.match(/<script[^>]*>/g) || []));
    const lv = await view(page, "leave");
    ok("/pro/leave: the same page, not indexed, no Referer", lv.statusCode === 200 && lv.headers["x-robots-tag"] === "noindex, nofollow" && lv.headers["referrer-policy"] === "no-referrer", lv.headers);
    ok("the page takes GET only", (await view(page, "waitlist", "POST")).statusCode === 405);
    const P = require("./lib/pro.js"), cfg0 = P.config;
    P.config = () => ({ on: true, mode: "test", supabaseUrl: "https://x.supabase.co", supabasePublishable: "sb_publishable_x" });
    pr = await view(page, "pro");
    const pw = await view(page, "waitlist");
    P.config = cfg0;
    ok("test mode on (a preview): /pro stays the test page; the waitlist is at /pro/waitlist", pr.statusCode === 200 && /\{\{CONFIG\}\}|"mode":"test"/.test(pr.body) && !/id="wl"/.test(pr.body)
       && pw.statusCode === 200 && /id="wl"/.test(pw.body), [pr.statusCode, pw.statusCode]);

    // join
    KV.clear(); KV_CALLS.length = 0; LOGS.length = 0;
    r = await call(wl, { email: "  Trader@Example.com ", pro: true, agents: true }, { ip: "198.51.100.5", headers: { "user-agent": "UA-CANARY/1.0" } });
    const id = wl._idOf("trader@example.com");
    const e = KV.get("waitlist:e:" + id), stored = e && JSON.parse(e.value);
    ok("join: 200 with a leave link troid signed", r.status === 200 && r.j.joined === true && r.j.leave_url === "/pro/leave?t=" + wl._token(id), r.j);
    ok("join: the email, both choices, the consent's version and the date, a year to live", stored && stored.email === "Trader@Example.com" && stored.pro === true
       && stored.agents === true && stored.consent === "2026-09-28" && /^\d{4}-\d\d-\d\dT/.test(stored.joined_utc) && e.ttl === 31536000, [stored, e && e.ttl]);
    ok("join: never the address or the user agent", !e.value.includes("198.51.100.5") && !e.value.includes("UA-CANARY") && !/"ip"|agent"/.test(e.value.replace('"agents"', "")), e.value);
    ok("join: the second box kept as waitlist:a:<id>, a year to live", KV.has("waitlist:a:" + id) && KV.get("waitlist:a:" + id).ttl === 31536000, [...KV.keys()]);
    ok("join: only those two keys, each with a year at most (nothing about an email outlives its year)",
       [...KV.keys()].sort().join() === ["waitlist:a:" + id, "waitlist:e:" + id].join() && [...KV.values()].every((x) => x.ttl > 0 && x.ttl <= 31536000), [...KV]);
    ok("join: the log line is counts only", LOGS.length === 1 && LOGS[0] === JSON.stringify({ troid: "waitlist", joined: 1, agents: 1 }), LOGS);
    r = await call(wl, { email: "trader@example.com", pro: true, agents: false }, { ip: "198.51.100.6" });
    ok("join again, same email in another case: the same entry, agents off, the same answer", r.status === 200 && r.j.leave_url === "/pro/leave?t=" + wl._token(id)
       && JSON.parse(KV.get("waitlist:e:" + id).value).agents === false && !KV.has("waitlist:a:" + id) && [...KV.keys()].join() === "waitlist:e:" + id, r.j);

    // refusals
    for (const [name, body, field] of [["no email", { pro: true }, "email"], ["not an email", { email: "trader.example.com", pro: true }, "email"],
                                         ["an email with a space", { email: "a b@example.com", pro: true }, "email"],
                                         ["an email over 254", { email: "a".repeat(250) + "@x.io", pro: true }, "email"],
                                         ["the first box not ticked", { email: "b@example.com", agents: true }, "pro"],
                                         ["pro not true", { email: "b@example.com", pro: "yes" }, "pro"]]) {
      r = await call(wl, body, { ip: "198.51.100.40" });
      ok(`refused, ${name}: 400 naming the field`, r.status === 400 && r.j.field === field, r);
    }
    ok("nothing stored by a refusal", !KV.has("waitlist:e:" + wl._idOf("b@example.com")));
    r = await call(wl, { email: "c@example.com", pro: true }, { headers: { "sec-fetch-site": "cross-site" } });
    ok("another site's page: 403", r.status === 403, r);
    r = await call(wl, "email=c@example.com", { headers: { "content-type": "text/plain" } });
    ok("not JSON: 415", r.status === 415, r);
    r = await call(wl, { email: "c@example.com", pro: true }, { method: "GET" });
    ok("GET: 405", r.status === 405, r);
    let last;
    for (let i = 0; i < 11; i++) last = await call(wl, { email: `r${i}@example.com`, pro: true }, { ip: "192.0.2.50" });
    ok("the eleventh try in an hour from one address: 429", last.status === 429, last);
    kvDown = true;
    r = await call(wl, { email: "d@example.com", pro: true }, { ip: "192.0.2.51" });
    kvDown = false;
    ok("the store down: 503, and the page says try again", r.status === 503, r);

    // leave
    LOGS.length = 0;
    r = await call(wl, { leave: wl._token(id) }, { ip: "192.0.2.52" });
    ok("leave: 200, the entry and the second box's key gone", r.status === 200 && r.j.left === true && !KV.has("waitlist:e:" + id) && !KV.has("waitlist:a:" + id)
       && KV_CALLS.at(-1).cmds.some(([op, k]) => op === "DEL" && k === "waitlist:a:" + id), [r, [...KV.keys()]]);
    ok("leave: the log line is a count", LOGS.length === 1 && LOGS[0] === JSON.stringify({ troid: "waitlist", left: 1 }), LOGS);
    r = await call(wl, { leave: wl._token(id) }, { ip: "192.0.2.52" });
    ok("leave twice: still 200 (nothing left to delete)", r.status === 200 && r.j.left === true, r);
    const forged = id + "." + "A".repeat(43), other = wl._idOf("someone@example.com") + "." + wl._token(id).split(".")[1];
    for (const [name, t] of [["a forged signature", forged], ["another email's id with this signature", other], ["nothing", ""], ["junk", "x.y"]]) {
      r = await call(wl, { leave: t }, { ip: "192.0.2.53" });
      ok(`leave refused, ${name}: 403, nothing deleted`, r.status === 403 && r.j.left === false, r);
    }
    ({ wl } = fresh(Object.assign({}, ENV, { TROID_WAITLIST_KEY: "k".repeat(40) })));
    r = await call(wl, { leave: fresh(ENV).wl._token(id) }, { ip: "192.0.2.54" });
    ok("a link signed under another key is refused", r.status === 403, r);

    // RFC 8058: a mail client's one-click unsubscribe
    ({ wl } = fresh(ENV));
    await call(wl, { email: "mail@example.com", pro: true }, { ip: "192.0.2.60" });
    const mid = wl._idOf("mail@example.com"), t = wl._token(mid);
    r = await call(wl, { "List-Unsubscribe": "One-Click" }, { headers: { "content-type": "application/x-www-form-urlencoded" }, url: "/api/pro/waitlist?t=" + t, query: { t } });
    ok("one-click unsubscribe (RFC 8058): the mail client's POST removes the entry", r.status === 200 && r.j.left === true && !KV.has("waitlist:e:" + mid), r);
    r = await call(wl, "List-Unsubscribe=One-Click", { headers: { "content-type": "application/x-www-form-urlencoded" }, url: "/api/pro/waitlist?t=" + t });
    ok("one-click unsubscribe, the body as a string and the token from the URL", r.status === 200 && r.j.left === true, r);
    r = await call(wl, { "List-Unsubscribe": "Other" }, { headers: { "content-type": "application/x-www-form-urlencoded" }, url: "/api/pro/waitlist?t=" + t, query: { t } });
    ok("a form POST that isn't List-Unsubscribe=One-Click: 400", r.status === 400, r);

    // vercel.json and the rendered page
    const V = require("./vercel.json");
    const rw = Object.fromEntries(V.rewrites.map((x) => [x.source, x.destination]));
    ok("vercel.json: /pro/waitlist and /pro/leave reach the page function; the waitlist has its function",
       rw["/pro/waitlist"] === "/api/pro/page?view=waitlist" && rw["/pro/leave"] === "/api/pro/page?view=leave" && V.functions["api/pro/waitlist.js"]
       && V.rewrites.findIndex((x) => x.source === "/pro/leave") < V.rewrites.findIndex((x) => x.source === "/pro"), V.rewrites);
    ok("the page function bundles the waitlist page", V.functions["api/pro/page.js"].includeFiles === "pro/*.html"
       && require("fs").existsSync(path.join(__dirname, "pro", "waitlist.html")));
  } catch (err) { ok("ran", false, String(err && err.stack)); }
  kv.close();
  console.log(`RESULT: ${failed} failed (${n} checks)`);
  process.exitCode = failed ? 1 : 0;
});
