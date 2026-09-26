"use strict";
/* Offline checks for troid Pro: web/lib/stripe.js, web/lib/pro.js, web/api/pro/*.js, web/api/stripe-webhook.js and
   supabase/migrations/20260926120000_troid_pro_billing.sql. The migration runs in PGlite (real Postgres, in process)
   behind a local fake of Supabase Auth and PostgREST; Stripe is a local fake too. Spends nothing and needs no key.
   Once: cd web && npm install --no-save @electric-sql/pglite@0.5.8     Then: node web/test_pro.js
   What it can't check is Stripe itself: whether Managed Payments takes these parameters, the tax it shows, the portal.
   Those are the live test-mode checks in web/README.md ("troid Pro"). */
const crypto = require("crypto");
const fs = require("fs");
const http = require("http");
const path = require("path");
const { Readable, PassThrough } = require("stream");
const { execFileSync } = require("child_process");

const ROOT = path.join(__dirname, "..");
const MIGRATION = path.join(ROOT, "supabase", "migrations", "20260926120000_troid_pro_billing.sql");
const SB_PORT = 18801, STRIPE_PORT = 18802, ORIGIN = "http://127.0.0.1:18803";
const key = (...parts) => parts.join("_");   // key-shaped strings exist only at run time, so no file in the repo holds one
const SECRET_TEST = key("rk", "test", "offline0000000000"), SECRET_LIVE = key("rk", "live", "offline0000000000");
const PK_TEST = key("pk", "test", "offline0000000000"), PK_LIVE = key("pk", "live", "offline0000000000");
const WEBHOOK_SECRET = "offline-signing-secret-0123456789";
const SB_PUBLISHABLE = "sb_publishable_offline", SB_SECRET = "sb_secret_offline";
const PRICE_M = "price_offlineMonthly", PRICE_Y = "price_offlineYearly";
const U = { A: "11111111-1111-4111-8111-111111111111", B: "22222222-2222-4222-8222-222222222222",
            C: "33333333-3333-4333-8333-333333333333", D: "44444444-4444-4444-8444-444444444444",
            E: "55555555-5555-4555-8555-555555555555", F: "66666666-6666-4666-8666-666666666666",
            G: "77777777-7777-4777-8777-777777777777" };
const TOKENS = Object.fromEntries(Object.entries(U).map(([n, id]) => ["tok-" + n, { id, email: n.toLowerCase() + "@example.com" }]));

const ENV_ON = { TROID_PRO: "test", VERCEL_ENV: "preview", STRIPE_SECRET_KEY: SECRET_TEST, STRIPE_PUBLISHABLE_KEY: PK_TEST,
                 STRIPE_WEBHOOK_SECRET: WEBHOOK_SECRET, STRIPE_PRICE_MONTHLY: PRICE_M, STRIPE_PRICE_YEARLY: PRICE_Y,
                 SUPABASE_URL: "http://127.0.0.1:" + SB_PORT, SUPABASE_PUBLISHABLE_KEY: SB_PUBLISHABLE, SUPABASE_SECRET_KEY: SB_SECRET,
                 TROID_PRO_ORIGIN: ORIGIN, STRIPE_API_BASE: "http://127.0.0.1:" + STRIPE_PORT };
const ENV_ALL = [...Object.keys(ENV_ON), "TROID_PRO_TEST_CLOCK", "SUPABASE_ANON_KEY", "SUPABASE_SERVICE_ROLE_KEY", "VERCEL_URL", "VERCEL_BRANCH_URL"];
function env(over = {}) {
  for (const k of ENV_ALL) delete process.env[k];
  for (const [k, v] of Object.entries({ ...ENV_ON, ...over })) if (v !== undefined) process.env[k] = v;
}
env();

const P = require("./lib/pro.js");
const S = require("./lib/stripe.js");
const checkout = require("./api/pro/checkout.js");
const portal = require("./api/pro/portal.js");
const status = require("./api/pro/status.js");
const page = require("./api/pro/page.js");
const webhook = require("./api/stripe-webhook.js");

let n = 0;
function ok(name, cond, got) { n++; if (!cond) { console.log("FAIL " + name, got === undefined ? "" : JSON.stringify(got).slice(0, 400)); process.exitCode = 1; } else console.log("ok   " + name); }

// --- fakes --------------------------------------------------------------------------------------------------------------
let db = null, failApplyOnce = false, stripeFail = null, seqStripe = 0;
const stripeCalls = [];
const catalog = {                                             // what web/pro_prices.js reads
  products: [{ id: "prod_other", name: "Something else", active: true }, { id: "prod_pro", name: "troid Pro", active: true, tax_code: "txcd_offline" }],
  prices: [{ id: PRICE_M, product: "prod_pro", currency: "usd", unit_amount: 1900, recurring: { interval: "month", interval_count: 1 }, tax_behavior: "exclusive" },
           { id: PRICE_Y, product: "prod_pro", currency: "usd", unit_amount: 19000, recurring: { interval: "year", interval_count: 1 }, tax_behavior: "exclusive" }],
};
const isoRow = (r) => Object.fromEntries(Object.entries(r).map(([k, v]) => [k, v instanceof Date ? v.toISOString() : v]));
async function readAll(req) { const c = []; for await (const x of req) c.push(x); return Buffer.concat(c).toString("utf8"); }
function send(res, code, obj) { res.writeHead(code, { "content-type": "application/json" }); res.end(obj === undefined ? "" : JSON.stringify(obj)); }

// Supabase: GoTrue's /auth/v1/user and PostgREST's two RPCs, run against the real migration in PGlite under the roles
// PostgREST would use (authenticated with the user's claims; service_role for the secret key).
const supabaseFake = http.createServer(async (req, res) => {
  const raw = await readAll(req);
  const url = new URL(req.url, "http://x");
  const tok = (/^Bearer (.+)$/.exec(req.headers.authorization || "") || [])[1];
  try {
    if (req.method === "GET" && url.pathname === "/auth/v1/user") {
      if (req.headers.apikey !== SB_PUBLISHABLE) return send(res, 401, { message: "Invalid API key" });
      const u = TOKENS[tok];
      return u ? send(res, 200, { id: u.id, email: u.email, aud: "authenticated" }) : send(res, 403, { code: "bad_jwt" });
    }
    if (req.method === "POST" && url.pathname === "/rest/v1/rpc/pro_status") {
      if (req.headers.apikey !== SB_PUBLISHABLE) return send(res, 401, { message: "Invalid API key" });
      const u = TOKENS[tok];
      if (!u) return send(res, 401, { code: "PGRST301", message: "JWT expired" });
      const args = JSON.parse(raw || "{}");
      const rows = await db.transaction(async (tx) => {
        await tx.exec("set local role authenticated");
        await tx.query("select set_config('request.jwt.claims', $1, true)", [JSON.stringify({ sub: u.id, role: "authenticated" })]);
        return (await tx.query("select * from public.pro_status(p_livemode => $1)", [args.p_livemode])).rows;
      });
      return send(res, 200, rows.map(isoRow));
    }
    if (req.method === "POST" && url.pathname === "/rest/v1/rpc/pro_apply_stripe_event") {
      if (req.headers.apikey !== SB_SECRET || req.headers.authorization) return send(res, 401, { message: "the secret key goes in apikey alone" });
      if (failApplyOnce) { failApplyOnce = false; return send(res, 503, { message: "unavailable" }); }
      const args = JSON.parse(raw), names = Object.keys(args);
      if (!names.every((x) => /^p_[a-z_]+$/.test(x))) return send(res, 400, { message: "bad argument name" });
      const out = await db.transaction(async (tx) => {
        await tx.exec("set local role service_role");
        const q = "select public.pro_apply_stripe_event(" + names.map((x, i) => x + " => $" + (i + 1)).join(", ") + ") as o";
        return (await tx.query(q, names.map((x) => args[x]))).rows[0].o;
      });
      return send(res, 200, out);
    }
    send(res, 404, { message: "no route " + url.pathname });
  } catch (e) { send(res, 500, { message: e.message }); }
});

// Stripe: records every call (method, path, headers, form) and answers as the API would, or with a queued error.
const stripeFake = http.createServer(async (req, res) => {
  const raw = await readAll(req);
  stripeCalls.push({ method: req.method, path: req.url, headers: req.headers, form: Object.fromEntries(new URLSearchParams(raw)) });
  if (!/^Bearer [rs]k_(test|live)_/.test(req.headers.authorization || "")) return send(res, 401, { error: { type: "invalid_request_error", message: "Invalid API Key provided" } });
  if (stripeFail) { const f = stripeFail; stripeFail = null; return send(res, f.status, { error: f.error }); }
  if (req.method === "GET" && req.url.startsWith("/v1/products?")) return send(res, 200, { object: "list", data: catalog.products });
  if (req.method === "GET" && req.url.startsWith("/v1/prices?")) {
    const product = new URL(req.url, "http://x").searchParams.get("product");
    return send(res, 200, { object: "list", data: catalog.prices.filter((p) => p.product === product) });
  }
  const i = ++seqStripe;
  if (req.url === "/v1/checkout/sessions") return send(res, 200, { id: "cs_test_" + i, object: "checkout.session", url: "https://checkout.stripe.com/c/pay/cs_test_" + i });
  if (req.url === "/v1/billing_portal/sessions") return send(res, 200, { id: "bps_" + i, object: "billing_portal.session", url: "https://billing.stripe.com/p/session/test_" + i });
  if (req.url === "/v1/test_helpers/test_clocks") return send(res, 200, { id: "clock_" + i, object: "test_helpers.test_clock" });
  if (req.url === "/v1/customers") return send(res, 200, { id: "cus_clock_" + i, object: "customer" });
  send(res, 404, { error: { type: "invalid_request_error", message: "Unrecognized request URL" } });
});

// --- calling the functions ---------------------------------------------------------------------------------------------
function fakeRes() {
  return { statusCode: 200, headers: {}, body: "", setHeader(k, v) { this.headers[k.toLowerCase()] = v; }, end(b) { this.body = b === undefined ? "" : String(b); } };
}
async function call(h, { method = "POST", headers = {}, body, url = "/" } = {}) {
  const hs = { "content-type": "application/json", "sec-fetch-site": "same-origin", origin: ORIGIN, ...headers };
  for (const k of Object.keys(hs)) if (hs[k] === undefined) delete hs[k];
  const res = fakeRes();
  await h({ method, url, headers: hs, body, query: Object.fromEntries(new URL(url, "http://x").searchParams) }, res);
  let data = null;
  try { data = JSON.parse(res.body); } catch (e) { /* html or text */ }
  return { status: res.statusCode, data, res };
}
const auth = (who) => ({ authorization: "Bearer tok-" + who });
const lastStripe = () => stripeCalls[stripeCalls.length - 1];

const nowS = () => Math.floor(Date.now() / 1000);
const sign = (payload, t = nowS(), secret = WEBHOOK_SECRET) =>
  "t=" + t + ",v1=" + crypto.createHmac("sha256", secret).update(t + "." + payload).digest("hex");
async function deliver(event, { sig, raw } = {}) {
  const payload = raw !== undefined ? raw : JSON.stringify(event);
  const req = Readable.from([Buffer.from(payload)]);
  Object.assign(req, { method: "POST", url: "/api/stripe-webhook",
                       headers: { "content-type": "application/json; charset=utf-8", "stripe-signature": sig !== undefined ? sig : sign(payload) } });
  const res = fakeRes();
  await webhook(req, res);
  let data = null;
  try { data = JSON.parse(res.body); } catch (e) { /* none */ }
  return { status: res.statusCode, data };
}

// Stripe objects, in the current API shape (period end on the item, invoice.parent) unless old: true
let seqEvt = 0;
const T0 = nowS() - 7200;                                    // event times: T0 + k, so order is explicit
function evt(type, object, { id, created, livemode = false } = {}) {
  return { id: id || "evt_offline_" + String(++seqEvt).padStart(4, "0"), object: "event", api_version: S.CHECKOUT_API_VERSION,
           created: created || nowS(), livemode, type, data: { object } };
}
function sub({ id, customer, status = "active", end, user, price = PRICE_M, cancelAtPeriodEnd = false, cancelAt = null,
               endedAt = null, canceledAt = null, reason = null, old = false }) {
  const item = { id: "si_" + id, object: "subscription_item", price: { id: price, object: "price" } };
  if (!old) Object.assign(item, { current_period_start: end - 30 * 86400, current_period_end: end });
  const o = { id, object: "subscription", customer, status, cancel_at_period_end: cancelAtPeriodEnd, cancel_at: cancelAt,
              ended_at: endedAt, canceled_at: canceledAt, cancellation_details: { reason }, livemode: false,
              metadata: user ? { user_id: user } : {}, items: { object: "list", data: [item] } };
  if (old) o.current_period_end = end;
  return o;
}
const session = ({ customer, subscription, user, mode = "subscription" }) =>
  ({ id: "cs_test_" + subscription, object: "checkout.session", mode, customer, subscription, client_reference_id: user || null,
     metadata: user ? { user_id: user } : {}, status: "complete", payment_status: "paid", livemode: false });
const invoice = ({ customer, subscription, user, old = false }) => old
  ? { id: "in_" + subscription, object: "invoice", customer, subscription, subscription_details: { metadata: user ? { user_id: user } : {} } }
  : { id: "in_" + subscription, object: "invoice", customer,
      parent: { type: "subscription_details", subscription_details: { subscription, metadata: user ? { user_id: user } : {} } } };

async function row(user, livemode = false) {
  const r = await db.query("select * from public.pro_accounts where user_id = $1 and livemode = $2", [user, livemode]);
  return r.rows[0] ? isoRow(r.rows[0]) : null;
}
async function outcome(id) { const r = await db.query("select outcome from public.stripe_events where id = $1", [id]); return r.rows[0] ? r.rows[0].outcome : null; }
async function eventCount() { return (await db.query("select count(*)::int as c from public.stripe_events")).rows[0].c; }
const statusOf = async (who) => (await call(status, { method: "GET", headers: auth(who) })).data;
const DAY = 86400;

async function main() {
  let PGlite;
  try { ({ PGlite } = await import("@electric-sql/pglite")); } catch (e) {
    console.log("FAIL PGlite missing: cd web && npm install --no-save @electric-sql/pglite@0.5.8");
    process.exitCode = 1;
    return;
  }
  db = new PGlite();
  await db.exec(`
    create schema auth;
    create table auth.users (id uuid primary key, email text);
    create function auth.uid() returns uuid language sql stable as $$
      select coalesce(nullif(current_setting('request.jwt.claim.sub', true), ''),
                      (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'sub'))::uuid $$;
    create role anon nologin; create role authenticated nologin; create role service_role nologin bypassrls;
    grant usage on schema public, auth to anon, authenticated, service_role;
    grant execute on function auth.uid() to anon, authenticated, service_role;
    alter default privileges in schema public grant all on tables to anon, authenticated, service_role;
    alter default privileges in schema public grant all on functions to anon, authenticated, service_role;`);   // Supabase's defaults
  const sql = fs.readFileSync(MIGRATION, "utf8");
  await db.exec(sql);
  await db.exec(sql);
  ok("the migration runs, and runs again over itself", true);
  for (const u of Object.values(TOKENS)) await db.query("insert into auth.users values ($1, $2)", [u.id, u.email]);
  await new Promise((r) => supabaseFake.listen(SB_PORT, "127.0.0.1", r));
  await new Promise((r) => stripeFake.listen(STRIPE_PORT, "127.0.0.1", r));

  // --- 1. Stripe primitives -------------------------------------------------------------------------------------------
  ok("form: nested objects and arrays as Stripe reads them; null left out",
     S.form({ line_items: [{ price: "p", quantity: 1 }], managed_payments: { enabled: true }, x: null }) ===
     "line_items%5B0%5D%5Bprice%5D=p&line_items%5B0%5D%5Bquantity%5D=1&managed_payments%5Benabled%5D=true");
  ok("key modes read from prefixes", S.keyMode(SECRET_TEST) === "test" && S.keyMode(SECRET_LIVE) === "live" && S.keyMode(key("sk", "live", "x")) === "live"
     && S.keyMode("nonsense") === null && S.publishableMode(PK_TEST) === "test" && S.publishableMode(SECRET_TEST) === null);
  // generated by stripe-node 22.6.2's webhooks.generateTestHeaderString, which its constructEvent accepts
  const V = { payload: '{"id":"evt_vector","object":"event","type":"customer.subscription.updated","note":"troid Pro — test"}',
              t: 1790400000, header: "t=1790400000,v1=f66bf1b276a63f286af734682c1320a76d13005b2945730c5c7a26b5a66b8ff7" };
  ok("signature: stripe-node's own vector verifies (UTF-8 body as bytes)", S.verifySignature(Buffer.from(V.payload), V.header, WEBHOOK_SECRET, V.t + 10).ok);
  ok("signature: the vector's body changed by one byte fails", S.verifySignature(Buffer.from(V.payload + " "), V.header, WEBHOOK_SECRET, V.t + 10).reason === "signature mismatch");
  ok("signature: another secret fails", !S.verifySignature(Buffer.from(V.payload), V.header, WEBHOOK_SECRET + "x", V.t + 10).ok);
  ok("signature: older than 300 s fails", /signed more than 300 s ago/.test(S.verifySignature(Buffer.from(V.payload), V.header, WEBHOOK_SECRET, V.t + 301).reason));
  ok("signature: any one of several v1 may match (a secret being rolled)",
     S.verifySignature(Buffer.from(V.payload), "t=1790400000,v1=" + "0".repeat(64) + "," + V.header.split(",")[1], WEBHOOK_SECRET, V.t).ok);
  ok("signature: missing or malformed header fails", !S.verifySignature(Buffer.from(V.payload), "", WEBHOOK_SECRET).ok
     && !S.verifySignature(Buffer.from(V.payload), "v1=abc", WEBHOOK_SECRET).ok && !S.verifySignature(Buffer.from(V.payload), V.header, "", V.t).ok);
  ok("Checkout's API version is the GA version with managed_payments, sent on that call alone", S.CHECKOUT_API_VERSION === "2026-08-26.dahlia");

  // --- 2. what an event becomes ------------------------------------------------------------------------------------------
  let a = P.eventArgs(evt("customer.subscription.updated", sub({ id: "sub_x", customer: "cus_x", end: 2000000000, user: U.A })));
  ok("subscription event, current shape: period end from the item, status, price, user", a.p_pro_until === "2033-05-18T03:33:20.000Z"
     && a.p_status === "active" && a.p_price === PRICE_M && a.p_user_id === U.A && a.p_subscription === "sub_x" && a.p_customer === "cus_x", a);
  a = P.eventArgs(evt("customer.subscription.updated", sub({ id: "sub_x", customer: "cus_x", end: 2000000000, user: U.A, old: true })));
  ok("subscription event, pre-2025-03-31 shape: period end at the top level", a.p_pro_until === "2033-05-18T03:33:20.000Z", a);
  a = P.eventArgs(evt("customer.subscription.updated", sub({ id: "sub_x", customer: "cus_x", end: 2000000000, cancelAt: 1999000000, user: U.A })));
  ok("cancel_at before the period's end: access ends then, marked cancelling", a.p_pro_until === new Date(1999000000e3).toISOString() && a.p_cancel_at_period_end === true, a);
  a = P.eventArgs(evt("customer.subscription.deleted", sub({ id: "sub_x", customer: "cus_x", status: "canceled", end: 2000000000, endedAt: 1990000000, user: U.A })));
  ok("deleted: status canceled, pro_until when it ended", a.p_status === "canceled" && a.p_pro_until === new Date(1990000000e3).toISOString(), a);
  a = P.eventArgs(evt("invoice.payment_failed", invoice({ customer: "cus_x", subscription: "sub_x", user: U.A })));
  ok("invoice, current shape: subscription and user from parent.subscription_details", a.p_subscription === "sub_x" && a.p_user_id === U.A, a);
  a = P.eventArgs(evt("invoice.payment_failed", invoice({ customer: "cus_x", subscription: "sub_x", user: U.A, old: true })));
  ok("invoice, old shape: top-level subscription", a.p_subscription === "sub_x" && a.p_user_id === U.A, a);
  ok("ignored: payment-mode checkout, a checkout troid didn't start, one with no subscription, other types, no id",
     P.eventArgs(evt("checkout.session.completed", session({ customer: "c", subscription: "s", user: U.A, mode: "payment" }))) === null
     && P.eventArgs(evt("checkout.session.completed", session({ customer: "c", subscription: "s" }))) === null
     && P.eventArgs(evt("checkout.session.completed", session({ customer: "c", subscription: null, user: U.A }))) === null
     && P.eventArgs(evt("invoice.paid", invoice({ customer: "c", subscription: "s" }))) === null
     && P.eventArgs({ type: "invoice.payment_failed", data: { object: {} } }) === null);

  // --- 3. the switch -------------------------------------------------------------------------------------------------------
  env({ TROID_PRO: undefined });
  let r = await call(status, { method: "GET" });
  ok("off: status says so, 503", r.status === 503 && r.data.on === false, r.data);
  ok("off: checkout, portal and webhook answer 503; the page 404",
     (await call(checkout, { headers: auth("A"), body: { plan: "monthly" } })).status === 503 && (await call(portal, { headers: auth("A"), body: {} })).status === 503
     && (await deliver(evt("customer.subscription.updated", sub({ id: "s", customer: "c", end: nowS() + DAY })))).status === 503
     && (await call(page, { method: "GET", url: "/api/pro/page?view=pro" })).status === 404);
  env({ VERCEL_ENV: "production" });
  r = await call(status, { method: "GET" });
  ok("test mode on production (troid.ai) is refused, and says nothing more there", r.status === 503 && JSON.stringify(r.data) === '{"on":false}', r.data);
  ok("test mode on production: no checkout, no page", (await call(checkout, { headers: auth("A"), body: { plan: "monthly" } })).status === 503
     && (await call(page, { method: "GET", url: "/api/pro/page?view=pro" })).status === 404);
  env({ STRIPE_SECRET_KEY: SECRET_LIVE });
  r = await call(status, { method: "GET" });
  ok("a live key in test mode is refused, by name", r.status === 503 && r.data.problems.some((x) => /STRIPE_SECRET_KEY is not a test-mode/.test(x)), r.data);
  env({ STRIPE_PUBLISHABLE_KEY: PK_LIVE });
  ok("a live publishable key in test mode is refused", (await call(status, { method: "GET" })).data.problems.some((x) => /STRIPE_PUBLISHABLE_KEY/.test(x)));
  env({ TROID_PRO: "live" });
  ok("live mode with test keys is refused", (await call(status, { method: "GET" })).data.problems.some((x) => /not a live-mode/.test(x)));
  env({ STRIPE_PRICE_YEARLY: "", STRIPE_WEBHOOK_SECRET: "", SUPABASE_SECRET_KEY: "" });
  r = await call(status, { method: "GET" });
  ok("nothing is sold without every setting: price, webhook secret, store key", r.data.problems.length === 3
     && (await call(checkout, { headers: auth("A"), body: { plan: "monthly" } })).status === 503, r.data);
  env({ SUPABASE_PUBLISHABLE_KEY: undefined, SUPABASE_SECRET_KEY: undefined, SUPABASE_ANON_KEY: SB_PUBLISHABLE, SUPABASE_SERVICE_ROLE_KEY: SB_SECRET });
  ok("the legacy Supabase key names are read too", (await call(status, { method: "GET" })).data.on === true);
  env();
  r = await call(status, { method: "GET" });
  ok("on: status without a token says on, test mode", r.status === 200 && r.data.on === true && r.data.mode === "test", r.data);

  // --- 4. checkout: guards ----------------------------------------------------------------------------------------------
  ok("checkout: GET is 405", (await call(checkout, { method: "GET", headers: auth("A") })).status === 405);
  ok("checkout: not JSON is 415", (await call(checkout, { headers: { ...auth("A"), "content-type": "text/plain" }, body: "plan=monthly" })).status === 415);
  ok("checkout: another site is 403", (await call(checkout, { headers: { ...auth("A"), "sec-fetch-site": "cross-site" }, body: { plan: "monthly" } })).status === 403);
  ok("checkout: no token is 401", (await call(checkout, { body: { plan: "monthly" } })).status === 401);
  ok("checkout: a token Supabase refuses is 401", (await call(checkout, { headers: { authorization: "Bearer forged" }, body: { plan: "monthly" } })).status === 401);
  ok("checkout: an unknown plan is 400", (await call(checkout, { headers: auth("A"), body: { plan: "lifetime" } })).status === 400);
  env({ SUPABASE_URL: "http://127.0.0.1:9" });
  ok("checkout: Supabase unreachable is 502 and Stripe is never called",
     (await call(checkout, { headers: auth("A"), body: { plan: "monthly" } })).status === 502 && stripeCalls.length === 0);
  env();
  ok("portal before any subscription: 404", (await call(portal, { headers: auth("A"), body: {} })).status === 404 && stripeCalls.length === 0);

  // --- 5. checkout: the Stripe call --------------------------------------------------------------------------------------
  r = await call(checkout, { headers: auth("A"), body: { plan: "monthly" } });
  let sc = lastStripe(), f = sc && sc.form;
  ok("checkout: 200 with Stripe's hosted page", r.status === 200 && /^https:\/\/checkout\.stripe\.com\//.test(r.data.url), r.data);
  ok("checkout: POST /v1/checkout/sessions with the key", sc.path === "/v1/checkout/sessions" && sc.headers.authorization === "Bearer " + SECRET_TEST);
  ok("checkout: Stripe-Version " + S.CHECKOUT_API_VERSION + " on this call", sc.headers["stripe-version"] === S.CHECKOUT_API_VERSION, sc.headers);
  ok("checkout: subscription mode, Managed Payments on, one monthly price", f.mode === "subscription" && f["managed_payments[enabled]"] === "true"
     && f["line_items[0][price]"] === PRICE_M && f["line_items[0][quantity]"] === "1" && !("line_items[1][price]" in f), f);
  ok("checkout: success and cancel URLs as the handoff sets them", f.success_url === ORIGIN + "/pro/thanks?session_id={CHECKOUT_SESSION_ID}"
     && f.cancel_url === ORIGIN + "/pro", f);
  ok("checkout: email, user id in client_reference_id and the subscription's metadata", f.customer_email === "a@example.com"
     && f.client_reference_id === U.A && f["subscription_data[metadata][user_id]"] === U.A && f["metadata[user_id]"] === U.A && !("customer" in f), f);
  ok("checkout: the copy, word for word", f["custom_text[submit][message]"] === "troid Pro — risk-calculation software. Not investment advice.", f);
  ok("checkout: no tax or payment-method settings (Managed Payments owns them)",
     !Object.keys(f).some((k) => /^(automatic_tax|payment_method_types|tax_id_collection|payment_method_configuration)/.test(k)), Object.keys(f));
  await call(checkout, { headers: auth("A"), body: { plan: "yearly" } });
  ok("checkout: yearly uses the yearly price", lastStripe().form["line_items[0][price]"] === PRICE_Y);
  await call(checkout, { headers: { ...auth("A"), origin: "https://elsewhere.example" }, body: { plan: "monthly" } });
  ok("checkout: an origin that isn't troid's never becomes a return URL", lastStripe().form.cancel_url === ORIGIN + "/pro");
  env({ TROID_PRO_ORIGIN: undefined, VERCEL_BRANCH_URL: "troid-git-branch-team.vercel.app", VERCEL_URL: "troid-abc123-team.vercel.app" });
  await call(checkout, { headers: { ...auth("A"), origin: "https://troid-abc123-team.vercel.app" }, body: { plan: "monthly" } });
  ok("checkout: back to the deployment the page was on", lastStripe().form.success_url.startsWith("https://troid-abc123-team.vercel.app/pro/thanks"));
  await call(checkout, { headers: { ...auth("A"), origin: undefined }, body: { plan: "monthly" } });
  ok("checkout: no origin → the branch URL off production", lastStripe().form.cancel_url === "https://troid-git-branch-team.vercel.app/pro");
  env();
  stripeFail = { status: 400, error: { type: "invalid_request_error", code: "parameter_unknown", param: "managed_payments", message: "Received unknown parameter: managed_payments" } };
  r = await call(checkout, { headers: auth("A"), body: { plan: "monthly" } });
  ok("checkout: Stripe's refusal reaches the tester in test mode, with its parameter", r.status === 502 && r.data.stripe.param === "managed_payments"
     && /Nothing was charged/.test(r.data.error), r.data);
  const liveCfg = P.config({ ...ENV_ON, TROID_PRO: "live", STRIPE_SECRET_KEY: SECRET_LIVE, STRIPE_PUBLISHABLE_KEY: PK_LIVE,
                             SUPABASE_URL: "https://offline.supabase.co", STRIPE_API_BASE: undefined });
  ok("in live mode a buyer never sees Stripe's error text", liveCfg.on && !("stripe" in P.stripeError(liveCfg, { stripe: true, message: "x" })), liveCfg.problems);
  ok("live mode won't use a local Supabase", P.config({ ...ENV_ON, TROID_PRO: "live", STRIPE_SECRET_KEY: SECRET_LIVE, STRIPE_PUBLISHABLE_KEY: PK_LIVE })
     .problems.includes("SUPABASE_URL is not an https origin"));

  // --- 6. webhook: what is refused before anything is written --------------------------------------------------------------
  const before = await eventCount();
  const e1 = evt("customer.subscription.created", sub({ id: "sub_A1", customer: "cus_A1", end: nowS() + 30 * DAY, user: U.A }), { created: T0 + 10 });
  const raw1 = JSON.stringify(e1);
  ok("webhook: no signature is 400", (await deliver(e1, { sig: "" })).status === 400);
  ok("webhook: a changed body is 400", (await deliver(e1, { raw: raw1.replace("active", "trialing"), sig: sign(raw1) })).status === 400);
  ok("webhook: signed with another secret is 400", (await deliver(e1, { sig: sign(raw1, nowS(), "another-secret") })).status === 400);
  ok("webhook: signed six minutes ago is 400 (a replay)", (await deliver(e1, { sig: sign(raw1, nowS() - 360) })).status === 400);
  r = await deliver(evt("customer.subscription.created", sub({ id: "sub_L", customer: "cus_L", end: nowS() + DAY, user: U.A }), { livemode: true }));
  ok("webhook: a live-mode event in test mode is 400", r.status === 400 && /live-mode event/.test(r.data.error), r.data);
  r = await deliver(evt("invoice.paid", invoice({ customer: "cus_A1", subscription: "sub_A1" })));
  ok("webhook: a type troid Pro doesn't act on is 200 ignored", r.status === 200 && r.data.outcome === "ignored", r.data);
  ok("webhook: none of that wrote anything", (await eventCount()) === before && (await row(U.A)) === null);

  // --- 7. subscribe: checkout completes, the webhook grants, a repeat changes nothing -----------------------------------------
  let e = evt("checkout.session.completed", session({ customer: "cus_A1", subscription: "sub_A1", user: U.A }), { created: T0 + 5 });
  r = await deliver(e);
  ok("checkout.session.completed links customer and subscription", r.status === 200 && r.data.outcome === "linked", r.data);
  let st = await statusOf("A");
  ok("linked, before the subscription's own event: not Pro yet, but manageable", st.pro === false && st.status === null && st.manage === true, st);
  const end1 = nowS() + 30 * DAY;
  const eCreated = evt("customer.subscription.created", sub({ id: "sub_A1", customer: "cus_A1", end: end1, user: U.A }), { created: T0 + 10 });
  r = await deliver(eCreated);
  st = await statusOf("A");
  ok("customer.subscription.created (active) turns Pro on until the period's end", r.data.outcome === "applied" && st.pro === true
     && st.status === "active" && st.pro_until === new Date(end1 * 1000).toISOString(), { r: r.data, st });
  const snap = await row(U.A);
  r = await deliver(eCreated);
  ok("the same event again: duplicate, and the row is byte-for-byte unchanged",
     r.status === 200 && r.data.outcome === "duplicate" && JSON.stringify(await row(U.A)) === JSON.stringify(snap), r.data);
  const rawC = JSON.stringify(eCreated), sigC = sign(rawC);
  await deliver(eCreated, { raw: rawC, sig: sigC });
  r = await deliver(eCreated, { raw: rawC, sig: sigC });
  ok("the same delivery replayed with its own signature: duplicate, nothing changes",
     r.data.outcome === "duplicate" && JSON.stringify(await row(U.A)) === JSON.stringify(snap), r.data);
  ok("the event is recorded once, as applied", (await outcome(eCreated.id)) === "applied"
     && (await db.query("select count(*)::int c from public.stripe_events where id = $1", [eCreated.id])).rows[0].c === 1);
  r = await call(checkout, { headers: auth("A"), body: { plan: "yearly" } });
  ok("checkout while Pro: 409, pointing to Manage subscription", r.status === 409 && r.data.manage === true, r.data);
  const nStripe = stripeCalls.length;
  r = await call(portal, { headers: auth("A"), body: {} });
  sc = lastStripe();
  ok("portal: 200 with Stripe's portal", r.status === 200 && /^https:\/\/billing\.stripe\.com\//.test(r.data.url) && stripeCalls.length === nStripe + 1, r.data);
  ok("portal: this user's customer, back to /account, no Stripe-Version", sc.path === "/v1/billing_portal/sessions" && sc.form.customer === "cus_A1"
     && sc.form.return_url === ORIGIN + "/account" && !("stripe-version" in sc.headers), sc);
  ok("status never shows the Stripe ids", !JSON.stringify(await statusOf("A")).includes("cus_A1"));
  ok("another user sees none of it", (await statusOf("B")).pro === false && (await statusOf("B")).manage === false);

  // --- 8. out of order ------------------------------------------------------------------------------------------------------
  r = await deliver(evt("customer.subscription.updated", sub({ id: "sub_A1", customer: "cus_A1", status: "past_due", end: end1, user: U.A }), { created: T0 + 9 }));
  ok("an event older than the one applied: stale, nothing changes", r.data.outcome === "stale" && (await row(U.A)).status === "active", r.data);
  r = await deliver(evt("customer.subscription.updated", sub({ id: "sub_A1", customer: "cus_A1", status: "incomplete", end: end1, user: U.A }), { created: T0 + 10 }));
  ok("same second, earlier in the subscription's life (incomplete after active): stale", r.data.outcome === "stale" && (await statusOf("A")).pro === true, r.data);

  // --- 9. cancel in the portal: access to the period's end, then locked ------------------------------------------------------
  r = await deliver(evt("customer.subscription.updated", sub({ id: "sub_A1", customer: "cus_A1", end: end1, cancelAtPeriodEnd: true, user: U.A }), { created: T0 + 20 }));
  st = await statusOf("A");
  ok("cancelled at period end: still Pro, marked as ending", r.data.outcome === "applied" && st.pro === true && st.cancel_at_period_end === true, st);
  const ended = nowS() - 1;
  r = await deliver(evt("customer.subscription.deleted", sub({ id: "sub_A1", customer: "cus_A1", status: "canceled", end: end1, cancelAtPeriodEnd: true,
                                                                 endedAt: ended, reason: "cancellation_requested", user: U.A }), { created: T0 + 30 }));
  st = await statusOf("A");
  ok("customer.subscription.deleted at the period's end: locked", r.data.outcome === "applied" && st.pro === false && st.status === "canceled"
     && st.pro_until === new Date(ended * 1000).toISOString(), st);
  r = await deliver(evt("customer.subscription.updated", sub({ id: "sub_A1", customer: "cus_A1", end: end1, user: U.A }), { created: T0 + 40 }));
  ok("an ended subscription never comes back, even on a newer event", r.data.outcome === "stale" && (await statusOf("A")).pro === false, r.data);
  ok("after it ends, Manage subscription still opens (invoices)", (await call(portal, { headers: auth("A"), body: {} })).status === 200);
  const rule = async (s, untilSql, cancel) => (await db.query(`select public.pro_entitled($1, ${untilSql}, $2) as p`, [s, cancel])).rows[0].p;
  ok("rule: cancelling locks exactly at the period's end", (await rule("active", "now() + interval '1 minute'", true)) === true
     && (await rule("active", "now() - interval '1 minute'", true)) === false);
  ok("rule: renewing keeps 24 hours past the period's end for a late renewal webhook, no more",
     (await rule("active", "now() - interval '1 hour'", false)) === true && (await rule("active", "now() - interval '25 hours'", false)) === false);
  ok("rule: past_due keeps access; unpaid, canceled, incomplete, paused and no status don't",
     (await rule("past_due", "now() + interval '1 day'", false)) === true && (await rule("unpaid", "now() + interval '1 day'", false)) === false
     && (await rule("canceled", "now() + interval '1 day'", false)) === false && (await rule("incomplete", "now() + interval '1 day'", false)) === false
     && (await rule("paused", "now() + interval '1 day'", false)) === false && (await rule(null, "now() + interval '1 day'", false)) === false);

  // --- 10. subscribing again ----------------------------------------------------------------------------------------------
  r = await call(checkout, { headers: auth("A"), body: { plan: "monthly" } });
  f = lastStripe().form;
  ok("subscribing again reuses the Stripe customer, no second email", r.status === 200 && f.customer === "cus_A1" && !("customer_email" in f), f);
  r = await deliver(evt("checkout.session.completed", session({ customer: "cus_A1", subscription: "sub_A2", user: U.A }), { created: T0 + 50 }));
  let rw = await row(U.A);
  ok("the new subscription takes the row; the old one's state is cleared", r.data.outcome === "linked" && rw.stripe_subscription_id === "sub_A2" && rw.status === null, rw);
  r = await deliver(evt("customer.subscription.updated", sub({ id: "sub_A1", customer: "cus_A1", status: "canceled", end: end1, endedAt: ended, user: U.A }), { created: T0 + 35 }));
  ok("a late event from the old subscription: stale", r.data.outcome === "stale" && (await row(U.A)).stripe_subscription_id === "sub_A2", r.data);
  const end2 = nowS() + 30 * DAY;
  r = await deliver(evt("customer.subscription.created", sub({ id: "sub_A2", customer: "cus_A1", end: end2, user: U.A }), { created: T0 + 55 }));
  ok("the new subscription's event turns Pro on again", r.data.outcome === "applied" && (await statusOf("A")).pro === true, r.data);

  // --- 11. a failed payment: past due, access kept until Stripe gives up -----------------------------------------------------
  await deliver(evt("checkout.session.completed", session({ customer: "cus_B1", subscription: "sub_B1", user: U.B }), { created: T0 + 100 }));
  await deliver(evt("customer.subscription.created", sub({ id: "sub_B1", customer: "cus_B1", end: nowS() + 30 * DAY, user: U.B }), { created: T0 + 101 }));
  const endB = nowS() + 60 * DAY;                               // Stripe has already rolled the period when the renewal fails
  r = await deliver(evt("invoice.payment_failed", invoice({ customer: "cus_B1", subscription: "sub_B1", user: U.B }), { created: T0 + 120 }));
  st = await statusOf("B");
  ok("invoice.payment_failed: past due, still Pro", r.data.outcome === "past_due" && st.status === "past_due" && st.pro === true && !!st.payment_failed_at, st);
  r = await deliver(evt("customer.subscription.updated", sub({ id: "sub_B1", customer: "cus_B1", end: endB, user: U.B }), { created: T0 + 110 }));
  st = await statusOf("B");
  ok("a state from before the failure, delivered late, doesn't show it paid", r.data.outcome === "applied" && st.status === "past_due" && st.pro === true, st);
  r = await deliver(evt("customer.subscription.updated", sub({ id: "sub_B1", customer: "cus_B1", status: "past_due", end: endB, user: U.B }), { created: T0 + 121 }));
  ok("Stripe's own past_due update: applied, still Pro", r.data.outcome === "applied" && (await statusOf("B")).pro === true, r.data);
  r = await deliver(evt("customer.subscription.deleted", sub({ id: "sub_B1", customer: "cus_B1", status: "canceled", end: endB, endedAt: nowS(),
                                                                 reason: "payment_failed", user: U.B }), { created: T0 + 200 }));
  st = await statusOf("B");
  ok("Stripe gives up and cancels: locked at once, not at the unpaid period's end", r.data.outcome === "applied" && st.pro === false && st.status === "canceled", st);

  await deliver(evt("checkout.session.completed", session({ customer: "cus_C1", subscription: "sub_C1", user: U.C }), { created: T0 + 300 }));
  await deliver(evt("customer.subscription.created", sub({ id: "sub_C1", customer: "cus_C1", end: nowS() + 30 * DAY, user: U.C }), { created: T0 + 301 }));
  await deliver(evt("invoice.payment_failed", invoice({ customer: "cus_C1", subscription: "sub_C1", user: U.C }), { created: T0 + 310 }));
  r = await deliver(evt("customer.subscription.updated", sub({ id: "sub_C1", customer: "cus_C1", end: nowS() + 30 * DAY, user: U.C }), { created: T0 + 320 }));
  st = await statusOf("C");
  ok("a retry that succeeds: active again, the failure cleared", r.data.outcome === "applied" && st.status === "active" && st.payment_failed_at === null && st.pro === true, st);
  r = await deliver(evt("invoice.payment_failed", invoice({ customer: "cus_C1", subscription: "sub_C1", user: U.C }), { created: T0 + 315 }));
  ok("a failure older than the recovery, delivered late: stale", r.data.outcome === "stale" && (await statusOf("C")).status === "active", r.data);
  await deliver(evt("invoice.payment_failed", invoice({ customer: "cus_C1", subscription: "sub_C1" }), { created: T0 + 330 }));
  r = await deliver(evt("customer.subscription.updated", sub({ id: "sub_C1", customer: "cus_C1", status: "unpaid", end: nowS() + 30 * DAY, user: U.C }), { created: T0 + 340 }));
  ok("Stripe gives up and marks it unpaid: locked", r.data.outcome === "applied" && (await statusOf("C")).pro === false, r.data);
  ok("a failure found by subscription alone (no metadata) still reaches the row", (await outcome("evt_offline_" + String(seqEvt - 1).padStart(4, "0"))) === "past_due");

  // --- 12. two subscriptions, strangers, old shapes, conflicts --------------------------------------------------------------
  await deliver(evt("checkout.session.completed", session({ customer: "cus_D1", subscription: "sub_D1", user: U.D }), { created: T0 + 400 }));
  await deliver(evt("customer.subscription.created", sub({ id: "sub_D1", customer: "cus_D1", end: nowS() + 30 * DAY, user: U.D }), { created: T0 + 401 }));
  r = await deliver(evt("checkout.session.completed", session({ customer: "cus_D2", subscription: "sub_D2", user: U.D }), { created: T0 + 402 }));
  const r2 = await deliver(evt("customer.subscription.created", sub({ id: "sub_D2", customer: "cus_D2", end: nowS() + 30 * DAY, user: U.D }), { created: T0 + 403 }));
  ok("a second subscription while the first grants Pro: recorded for the owner, the first kept",
     r.data.outcome === "other_subscription" && r2.data.outcome === "other_subscription" && (await row(U.D)).stripe_subscription_id === "sub_D1", [r.data, r2.data]);
  r = await deliver(evt("customer.subscription.created", sub({ id: "sub_X", customer: "cus_X", end: nowS() + 30 * DAY }), { created: T0 + 500 }));
  ok("a subscription troid's checkout didn't start: unmatched, no row", r.data.outcome === "unmatched"
     && (await db.query("select count(*)::int c from public.pro_accounts where stripe_subscription_id = 'sub_X'")).rows[0].c === 0, r.data);
  r = await deliver(evt("customer.subscription.created", sub({ id: "sub_Z", customer: "cus_Z", end: nowS() + 30 * DAY, user: "99999999-9999-4999-8999-999999999999" }), { created: T0 + 501 }));
  ok("a user id Supabase doesn't have: unmatched", r.data.outcome === "unmatched", r.data);
  await deliver(evt("checkout.session.completed", session({ customer: "cus_E1", subscription: "sub_E1", user: U.E }), { created: T0 + 600 }));
  r = await deliver(evt("customer.subscription.created", sub({ id: "sub_E1", customer: "cus_E1", end: nowS() + 30 * DAY, user: U.E, old: true }), { created: T0 + 601 }));
  ok("the pre-2025-03-31 event shape grants the same way", r.data.outcome === "applied" && (await statusOf("E")).pro === true, r.data);
  r = await deliver(evt("checkout.session.completed", session({ customer: "cus_A1", subscription: "sub_F1", user: U.F }), { created: T0 + 700 }));
  ok("a customer already linked to another user: conflict, answered 200, nothing moved", r.status === 200 && r.data.outcome === "conflict"
     && (await row(U.F)) === null && (await row(U.A)).stripe_customer_id === "cus_A1", r.data);

  // --- 13. the store fails: 500, so Stripe retries, and the retry applies ------------------------------------------------------
  const eG = evt("checkout.session.completed", session({ customer: "cus_G1", subscription: "sub_G1", user: U.G }), { created: T0 + 800 });
  failApplyOnce = true;
  r = await deliver(eG);
  ok("store unavailable: 500 and nothing recorded", r.status === 500 && (await outcome(eG.id)) === null, r.data);
  r = await deliver(eG);
  ok("Stripe's retry of that event applies", r.status === 200 && r.data.outcome === "linked", r.data);

  // --- 14. who can read and write what (Supabase's roles) ---------------------------------------------------------------------
  const as = (role, user, q) => db.transaction(async (tx) => {
    await tx.exec("set local role " + role);
    if (user) await tx.query("select set_config('request.jwt.claims', $1, true)", [JSON.stringify({ sub: user, role })]);
    return tx.query(q);
  });
  const denied = async (role, user, q) => { try { await as(role, user, q); return false; } catch (e) { return /permission denied/.test(e.message); } };
  ok("a user reads their own row and no one else's", (await as("authenticated", U.A, "select user_id from public.pro_accounts")).rows.every((x) => x.user_id === U.A)
     && (await as("authenticated", U.A, "select user_id from public.pro_accounts")).rows.length === 1);
  ok("a user can't write their row", await denied("authenticated", U.A, "update public.pro_accounts set status = 'active', pro_until = now() + interval '9 years'"));
  ok("a user can't call the webhook's function", await denied("authenticated", U.B,
     `select public.pro_apply_stripe_event('evt_self', 'customer.subscription.created', false, now(), '${U.B}'::uuid, 'c', 's', 'active', null, now() + interval '1 year', false)`));
  ok("anon reads nothing and can't ask for status", await denied("anon", null, "select * from public.pro_accounts") && await denied("anon", null, "select * from public.pro_status(false)"));
  ok("no one but the service reads the event log", await denied("authenticated", U.A, "select * from public.stripe_events"));
  ok("test-mode rows never count in live mode", (await as("authenticated", U.A, "select * from public.pro_status(true)")).rows.length === 0);
  const bare = new PGlite();                                  // no default grants: the migration's own grants must suffice
  await bare.exec(`
    create schema auth; create table auth.users (id uuid primary key, email text);
    create function auth.uid() returns uuid language sql stable as $$
      select (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'sub')::uuid $$;
    create role anon nologin; create role authenticated nologin; create role service_role nologin bypassrls;
    grant usage on schema public, auth to anon, authenticated, service_role;
    grant execute on function auth.uid() to anon, authenticated, service_role;`);
  await bare.exec(sql);
  await bare.query("insert into auth.users values ($1, 'a@example.com')", [U.A]);
  const bareOut = await bare.transaction(async (tx) => { await tx.exec("set local role service_role");
    return (await tx.query(`select public.pro_apply_stripe_event('evt_bare', 'customer.subscription.created', false, now(), '${U.A}'::uuid,
                             'cus_bare', 'sub_bare', 'active', null, now() + interval '30 days', false) as o`)).rows[0].o; });
  const bareRows = await bare.transaction(async (tx) => { await tx.exec("set local role authenticated");
    await tx.query("select set_config('request.jwt.claims', $1, true)", [JSON.stringify({ sub: U.A })]);
    return (await tx.query("select * from public.pro_status(false)")).rows; });
  ok("without Supabase's default grants the migration still works: the webhook writes, the user reads their own status",
     bareOut === "applied" && bareRows.length === 1 && bareRows[0].pro === true, { bareOut, bareRows });
  await bare.close();

  // --- 15. the raw body on Vercel ------------------------------------------------------------------------------------------------
  // @vercel/node 16.0.1 (serverless-handler, addHelpers → readBody → restoreBody) reads the body before the handler and
  // replays it on "data" and "end". This is that replay, word for word, over a stream already read to its end.
  const bodyText = JSON.stringify(evt("invoice.paid", {}));
  const consumed = Readable.from([Buffer.from(bodyText)]);
  for await (const x of consumed) void x;                    // the helper reads it all
  (function restoreBody(req, b) {
    const replicateBody = new PassThrough();
    const on = replicateBody.on.bind(replicateBody);
    const originalOn = req.on.bind(req);
    req.read = replicateBody.read.bind(replicateBody);
    req.on = req.addListener = (name, cb) => (name === "data" || name === "end" ? on(name, cb) : originalOn(name, cb));
    replicateBody.write(b);
    replicateBody.end();
  })(consumed, Buffer.from(bodyText));
  ok("raw body: read after Vercel's helpers, byte for byte", (await P.rawBody(consumed)).toString("utf8") === bodyText);
  const stalled = new PassThrough();
  ok("raw body: a stream that never ends is refused, not hung", await P.rawBody(stalled, 1 << 20, 50).then(() => false, (e) => e.status === 400));
  ok("raw body: over the limit is 413", await P.rawBody(Readable.from([Buffer.alloc(64)]), 16).then(() => false, (e) => e.status === 413));

  // --- 16. the test-mode page ---------------------------------------------------------------------------------------------------
  r = await call(page, { method: "GET", url: "/api/pro/page?view=thanks" });
  const csp = r.res.headers["content-security-policy"] || "";
  const nonce = (/'nonce-([^']+)'/.exec(csp) || [])[1];
  const cfgJson = (/<script id="pro-config" type="application\/json">([^<]*)<\/script>/.exec(r.res.body) || [])[1];
  const pc = cfgJson ? JSON.parse(cfgJson) : {};
  ok("page: 200, noindex, every script under the response's nonce", r.status === 200 && /noindex/.test(r.res.headers["x-robots-tag"]) && !!nonce
     && (r.res.body.match(/<script nonce="([^"]+)"/g) || []).length === 2 && !r.res.body.includes("{{"), r.res.headers);
  ok("page: CSP talks only to troid and Supabase, loads only jsDelivr", /connect-src 'self' http:\/\/127\.0\.0\.1:18801/.test(csp)
     && /default-src 'none'/.test(csp) && /frame-ancestors 'none'/.test(csp), csp);
  ok("page: gets the view, mode, Supabase URL and publishable key; never the secret", pc.view === "thanks" && pc.mode === "test"
     && pc.supabaseKey === SB_PUBLISHABLE && !r.res.body.includes(SB_SECRET) && !r.res.body.includes(SECRET_TEST) && !r.res.body.includes(WEBHOOK_SECRET), pc);
  ok("page: a fresh nonce per response", nonce !== (/'nonce-([^']+)'/.exec((await call(page, { method: "GET", url: "/api/pro/page" })).res.headers["content-security-policy"]) || [])[1]);
  ok("page: pins supabase-js with an integrity hash", /supabase-js@2\.\d+\.\d+\/dist\/umd\/supabase\.js"\s+integrity="sha384-[A-Za-z0-9+/=]{64}"/.test(r.res.body));
  ok("page: the success page never reads session_id", !/session_id/.test(fs.readFileSync(path.join(__dirname, "pro", "index.html"), "utf8")));

  // --- 17. test clocks (test mode only) -------------------------------------------------------------------------------------
  env({ TROID_PRO_TEST_CLOCK: "on" });
  const k0 = stripeCalls.length;
  r = await call(checkout, { headers: auth("B"), body: { plan: "monthly" } });
  ok("test clock: a returning customer keeps theirs (no clock made)", r.status === 200 && stripeCalls.length === k0 + 1 && lastStripe().form.customer === "cus_B1");
  await db.query("delete from public.pro_accounts where user_id = $1", [U.F]);
  r = await call(checkout, { headers: auth("F"), body: { plan: "monthly" } });
  const made = stripeCalls.slice(k0 + 1).map((x) => x.path);
  ok("test clock: a first checkout makes a clock and a customer on it, then passes that customer",
     r.status === 200 && made.join() === "/v1/test_helpers/test_clocks,/v1/customers,/v1/checkout/sessions"
     && stripeCalls[stripeCalls.length - 2].form.test_clock && lastStripe().form.customer === "cus_clock_" + (seqStripe - 1), made);
  ok("test clock: never in live mode", P.config({ ...ENV_ON, TROID_PRO: "live", STRIPE_SECRET_KEY: SECRET_LIVE, STRIPE_PUBLISHABLE_KEY: PK_LIVE, TROID_PRO_TEST_CLOCK: "on" }).testClock === false);
  env();

  // --- 18. the owner's price lookup ----------------------------------------------------------------------------------------------
  const prices = (extra = {}) => new Promise((resolve) => require("child_process").execFile(process.execPath, [path.join(__dirname, "pro_prices.js")],
    { env: { PATH: process.env.PATH, STRIPE_API_BASE: ENV_ON.STRIPE_API_BASE, STRIPE_SECRET_KEY: SECRET_TEST, ...extra } },
    (err, stdout, stderr) => resolve({ code: err ? err.code : 0, out: stdout + stderr })));
  const k1 = stripeCalls.length;
  let pr = await prices();
  ok("pro_prices.js: finds troid Pro, checks both prices, prints the two lines", pr.code === 0 && pr.out.includes("STRIPE_PRICE_MONTHLY=" + PRICE_M)
     && pr.out.includes("STRIPE_PRICE_YEARLY=" + PRICE_Y) && pr.out.includes("tax code txcd_offline") && pr.out.includes("(Preview)"), pr.out);
  ok("pro_prices.js: GETs only, no Stripe-Version", stripeCalls.slice(k1).every((x) => x.method === "GET" && !("stripe-version" in x.headers)));
  catalog.prices[1].unit_amount = 18000;
  pr = await prices();
  ok("pro_prices.js: a price that isn't the handoff's fails, naming it", pr.code === 1 && pr.out.includes("is 180.00 USD; the handoff says 190.00 USD"), pr.out);
  catalog.prices[1].unit_amount = 19000;
  pr = await prices({ STRIPE_SECRET_KEY: "" });
  ok("pro_prices.js: without a key it says what to set, and calls nothing", pr.code === 2 && /Set STRIPE_SECRET_KEY/.test(pr.out));

  // --- 19. the repo -----------------------------------------------------------------------------------------------------------
  const files = execFileSync("git", ["ls-files", "-z", "--cached", "--others", "--exclude-standard"], { cwd: ROOT }).toString("utf8").split("\0").filter(Boolean);
  const handoffGrep = new RegExp([key("sk", "live"), key("sk", "test"), key("whsec", "")].join("|"));        // the handoff's grep
  const keyBody = new RegExp("\\b(" + ["[rsp]k", "whsec"].join("|") + ")_(test|live)?_?[0-9A-Za-z]{16,}");     // anything shaped like a real key
  const hits = [];
  for (const rel of files) {
    let text;
    try { text = fs.readFileSync(path.join(ROOT, rel), "utf8"); } catch (e) { continue; }
    if (handoffGrep.test(text) || keyBody.test(text)) hits.push(rel);
  }
  ok("no key in the repo: the handoff's grep and key-shaped strings find nothing, in tracked files and new ones", hits.length === 0, hits);
  const banned = new RegExp(["get funded", "pass your challenge"].join("|"), "i");
  const proFiles = ["web/pro/index.html", "web/lib/pro.js", "web/lib/stripe.js", "web/api/pro/checkout.js", "web/api/pro/portal.js",
                    "web/api/pro/status.js", "web/api/pro/page.js", "web/api/stripe-webhook.js"];
  ok('no "get funded" or "pass your challenge" in anything troid Pro shows', proFiles.every((x) => !banned.test(fs.readFileSync(path.join(ROOT, x), "utf8"))));
  const ignored = (p) => { try { execFileSync("git", ["check-ignore", "-q", p], { cwd: ROOT }); return true; } catch (e) { return false; } };
  ok("the env files Vercel's CLI writes are ignored; the example isn't", ignored("web/.env.local") && ignored("web/.env") && ignored(".env.production.local") && !ignored("web/.env.example"));
  const example = fs.readFileSync(path.join(__dirname, ".env.example"), "utf8");
  const names = ["TROID_PRO", "STRIPE_SECRET_KEY", "STRIPE_PUBLISHABLE_KEY", "STRIPE_WEBHOOK_SECRET", "STRIPE_PRICE_MONTHLY", "STRIPE_PRICE_YEARLY",
                 "SUPABASE_URL", "SUPABASE_PUBLISHABLE_KEY", "SUPABASE_SECRET_KEY"];
  ok(".env.example: every setting, as an empty placeholder", names.every((x) => new RegExp("^" + x + "=\\s*(#.*)?$", "m").test(example)), names.filter((x) => !new RegExp("^" + x + "=\\s*(#.*)?$", "m").test(example)));

  console.log(`\n${n} checks, ${process.exitCode ? "FAILURES above" : "all passed"}`);
}

main().catch((e) => { console.log("FAIL crashed:", e && e.stack); process.exitCode = 1; })
      .finally(() => { supabaseFake.close(); stripeFake.close(); if (db) db.close().catch(() => {}); });
