"use strict";
/* troid Pro (handoff "Stripe Managed Payments for troid Pro", 2026-09-26): the switch, the keys' mode, the signed-in user
   (Supabase Auth), their Pro row (supabase/migrations/20260926120000_troid_pro_billing.sql) and what a Stripe event
   changes in it. Used by web/api/pro/*.js and web/api/stripe-webhook.js. It sells a subscription to software; it never
   places, modifies or closes an order and never touches a brokerage account.

   The switch: TROID_PRO=test on a Preview deployment, with test-mode Stripe keys. Test mode is refused on production,
   where the Terms still say troid has no user accounts, and refused with a live key. TROID_PRO=live, with live keys,
   is for launch, after the gates in the launch plan (section 6.3): Vercel Pro, counsel, updated Terms, the owner's
   approval. Unset, every Pro route answers 404 or 503 and calls nothing. Every setting must be present before anything
   is sold: a checkout the webhook couldn't record would take money for access it can't give. */
const S = require("./stripe.js");

const CHECKOUT_COPY = "troid Pro — risk-calculation software. Not investment advice.";   // handoff item 6, word for word
const PRICE_ENV = { monthly: "STRIPE_PRICE_MONTHLY", yearly: "STRIPE_PRICE_YEARLY" };
const HANDLED = new Set(["checkout.session.completed", "customer.subscription.created", "customer.subscription.updated",
                         "customer.subscription.deleted", "invoice.payment_failed"]);
const PROD_ORIGIN = "https://troid.ai";

const httpsOrigin = (s) => /^https:\/\/[a-z0-9.-]+(:\d+)?$/i.test(s);
const localOrigin = (s) => /^http:\/\/(127\.0\.0\.1|localhost)(:\d+)?$/.test(s);

function config(env = process.env) {
  const mode = env.TROID_PRO === "test" || env.TROID_PRO === "live" ? env.TROID_PRO : null;
  const production = env.VERCEL_ENV === "production";
  const hosts = [env.VERCEL_BRANCH_URL, env.VERCEL_URL].filter(Boolean).map((h) => "https://" + h);
  let pinned = String(env.TROID_PRO_ORIGIN || "").replace(/\/+$/, "");   // tests, or an owner's fixed preview origin
  if (!(httpsOrigin(pinned) || localOrigin(pinned))) pinned = "";
  const c = {
    mode, production,
    secretKey: env.STRIPE_SECRET_KEY || "",
    publishableKey: env.STRIPE_PUBLISHABLE_KEY || "",       // hosted Checkout doesn't need it; if set, its mode must match
    webhookSecret: env.STRIPE_WEBHOOK_SECRET || "",
    prices: { monthly: env.STRIPE_PRICE_MONTHLY || "", yearly: env.STRIPE_PRICE_YEARLY || "" },
    supabaseUrl: String(env.SUPABASE_URL || "").replace(/\/+$/, ""),
    supabasePublishable: env.SUPABASE_PUBLISHABLE_KEY || env.SUPABASE_ANON_KEY || "",
    supabaseSecret: env.SUPABASE_SECRET_KEY || env.SUPABASE_SERVICE_ROLE_KEY || "",
    testClock: mode === "test" && env.TROID_PRO_TEST_CLOCK === "on",
    // where Checkout and the portal may send the browser back: troid.ai, this deployment, its branch
    origins: [PROD_ORIGIN, "https://www.troid.ai", ...hosts, ...(pinned ? [pinned] : [])],
    home: production ? PROD_ORIGIN : pinned || hosts[0] || PROD_ORIGIN,
  };
  const p = [];
  if (!mode) p.push("TROID_PRO is not test or live");
  else {
    if (mode === "test" && production) p.push("test mode is refused on production");
    if (S.keyMode(c.secretKey) !== mode) p.push("STRIPE_SECRET_KEY is not a " + mode + "-mode secret or restricted key");
    if (c.publishableKey && S.publishableMode(c.publishableKey) !== mode) p.push("STRIPE_PUBLISHABLE_KEY is not a " + mode + "-mode key");
    if (!c.webhookSecret) p.push("STRIPE_WEBHOOK_SECRET is not set");
    for (const [plan, name] of Object.entries(PRICE_ENV)) if (!/^price_[A-Za-z0-9]+$/.test(c.prices[plan])) p.push(name + " is not a price ID");
    if (!(httpsOrigin(c.supabaseUrl) || (mode === "test" && localOrigin(c.supabaseUrl)))) p.push("SUPABASE_URL is not an https origin");
    if (!c.supabasePublishable) p.push("SUPABASE_PUBLISHABLE_KEY is not set");
    if (!c.supabaseSecret) p.push("SUPABASE_SECRET_KEY is not set");
  }
  c.problems = p;
  c.on = p.length === 0;
  return c;
}

// What a request without a token learns: whether Pro is on here, and off production, which settings are missing (names only).
const report = (c) => (c.on ? { on: true, mode: c.mode } : c.production ? { on: false } : { on: false, mode: c.mode, problems: c.problems });

// --- HTTP ----------------------------------------------------------------------------------------------------------------
function json(res, code, obj) {
  res.statusCode = code;
  res.setHeader("content-type", "application/json; charset=utf-8");
  res.setHeader("cache-control", "no-store");
  res.end(JSON.stringify(obj));
}
const bearer = (req) => { const m = /^Bearer (\S{1,4096})$/.exec(String(req.headers.authorization || "")); return m ? m[1] : ""; };
// Same-origin JSON only, like ask troid: another site's form or no-cors fetch can't start a checkout or open a portal.
function refused(req) {
  if (!/^application\/json\b/i.test(String(req.headers["content-type"] || ""))) return { code: 415, error: "Send application/json." };
  const site = req.headers["sec-fetch-site"];
  if (site && site !== "same-origin") return { code: 403, error: "troid Pro answers on troid's own pages only." };
  return null;
}
function body(req) {
  let b = req.body;
  if (typeof b === "string") { try { b = JSON.parse(b); } catch (e) { b = null; } }
  return b && typeof b === "object" ? b : {};
}
const returnOrigin = (c, req) => { const o = String(req.headers.origin || ""); return c.origins.includes(o) ? o : c.home; };

// The webhook's body as the bytes Stripe sent. Vercel's Node helpers read the body before the handler runs and replay it
// on the request's "data" and "end" events (@vercel/node, restoreBody), so it can still be read here. Never req.body:
// that is parsed JSON, and a signature can't be checked against JSON re-serialised.
function rawBody(req, limit = 1 << 20, waitMs = 5000) {
  if (Buffer.isBuffer(req.rawBody)) return Promise.resolve(req.rawBody);
  return new Promise((resolve, reject) => {
    const chunks = [];
    let n = 0, done = false;
    const finish = (err, buf) => { if (done) return; done = true; clearTimeout(timer); err ? reject(err) : resolve(buf); };
    const timer = setTimeout(() => finish(Object.assign(new Error("request body unavailable"), { status: 400 })), waitMs);
    req.on("data", (chunk) => {
      n += chunk.length;
      if (n > limit) finish(Object.assign(new Error("body over " + limit + " bytes"), { status: 413 }));
      else chunks.push(Buffer.from(chunk));
    });
    req.on("end", () => finish(null, Buffer.concat(chunks)));
    req.on("error", (e) => finish(e));
  });
}

const log = (o) => console.log(JSON.stringify({ troid: "pro", ...o }));   // never a key, an email or a user id
// Stripe's refusal, with its reason in test mode, where the owner is the one reading (it answers whether Managed
// Payments took a parameter); in live mode a buyer sees only that it failed.
const stripeError = (c, e) => ({
  error: "Stripe didn't accept the request. Nothing was charged.",
  ...(c.mode === "test" && e && e.stripe ? { stripe: { status: e.status, type: e.type, code: e.code, param: e.param, message: e.message } } : {}),
});

// --- Supabase ------------------------------------------------------------------------------------------------------------
const jwtLike = (k) => /^eyJ[\w-]+\.[\w-]+\.[\w-]+$/.test(k);   // the legacy anon and service_role keys are JWTs; sb_ keys are not
async function supabase(c, path, { method = "GET", token = null, secret = false, payload } = {}) {
  const key = secret ? c.supabaseSecret : c.supabasePublishable;
  const headers = { apikey: key };
  const auth = token || (jwtLike(key) ? key : null);
  if (auth) headers.authorization = "Bearer " + auth;
  if (payload !== undefined) headers["content-type"] = "application/json";
  const r = await fetch(c.supabaseUrl + path, { method, headers, body: payload === undefined ? undefined : JSON.stringify(payload),
                                                signal: AbortSignal.timeout(8000) });
  const text = await r.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch (e) { /* not JSON */ }
  return { status: r.status, ok: r.ok, data };
}
const unavailable = (what, status) => Object.assign(new Error(what + " answered " + status), { status: 502 });

// The signed-in user from their Supabase access token, or null when Supabase refuses the token.
async function signedIn(c, token) {
  if (!token) return null;
  const r = await supabase(c, "/auth/v1/user", { token });
  if (r.status >= 400 && r.status < 500) return null;
  if (!r.ok || !r.data || typeof r.data.id !== "string") throw unavailable("Supabase Auth", r.status);
  return { id: r.data.id, email: typeof r.data.email === "string" && r.data.email ? r.data.email : null };
}

// The entitlement check every Pro feature uses: the user's own row in this mode, through pro_status() under their own
// token, so RLS decides what it can read. null when the token is refused; { pro: false, … } when there is no row.
async function proStatus(c, token) {
  const r = await supabase(c, "/rest/v1/rpc/pro_status", { method: "POST", token, payload: { p_livemode: c.mode === "live" } });
  if (r.status === 401 || r.status === 403) return null;
  if (!r.ok || !Array.isArray(r.data)) throw unavailable("pro_status", r.status);
  const row = r.data[0] || {};
  return { pro: row.pro === true, status: row.status || null, pro_until: row.pro_until || null,
           cancel_at_period_end: row.cancel_at_period_end === true, payment_failed_at: row.payment_failed_at || null,
           customer: row.stripe_customer_id || null };
}

// The webhook's one write (service key): returns the outcome pro_apply_stripe_event() records.
async function applyEvent(c, args) {
  const r = await supabase(c, "/rest/v1/rpc/pro_apply_stripe_event", { method: "POST", secret: true, payload: args });
  if (!r.ok || typeof r.data !== "string") throw unavailable("pro_apply_stripe_event", r.status);
  return r.data;
}

// --- Stripe ---------------------------------------------------------------------------------------------------------------
// The Checkout Session (handoff items 2, 3 and 6): subscription mode, Managed Payments on, one price, the user's id in
// client_reference_id and in the subscription's metadata, the email for a first purchase or the Stripe customer the user
// already has.
function checkoutParams(c, user, plan, origin, customer) {
  const params = {
    mode: "subscription",
    line_items: [{ price: c.prices[plan], quantity: 1 }],
    managed_payments: { enabled: true },
    success_url: origin + "/pro/thanks?session_id={CHECKOUT_SESSION_ID}",
    cancel_url: origin + "/pro",
    client_reference_id: user.id,
    metadata: { user_id: user.id },
    subscription_data: { metadata: { user_id: user.id } },
    custom_text: { submit: { message: CHECKOUT_COPY } },
  };
  if (customer) params.customer = customer;
  else if (user.email) params.customer_email = user.email;
  return params;
}

// Test mode only (TROID_PRO_TEST_CLOCK=on): the customer gets a Stripe test clock, so a tester can advance time in the
// Dashboard and watch a period end, a portal cancellation take effect and access lock, in minutes instead of a month.
async function testClockCustomer(c, user) {
  const clock = await S.request(c.secretKey, "POST", "/v1/test_helpers/test_clocks",
                                { frozen_time: Math.floor(Date.now() / 1000), name: "troid Pro test " + user.id.slice(0, 8) });
  const customer = await S.request(c.secretKey, "POST", "/v1/customers",
                                   { email: user.email, test_clock: clock.id, metadata: { user_id: user.id } });
  return customer.id;
}

// --- Stripe event → pro_apply_stripe_event() arguments ---------------------------------------------------------------------
const idOf = (x) => (x && typeof x === "object" ? x.id : x) || null;                        // an expandable field: id or object
const at = (s) => (Number.isFinite(s) && s > 0 ? new Date(s * 1000).toISOString() : null);   // Stripe's unix seconds
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const userIdOf = (...xs) => { for (const x of xs) if (typeof x === "string" && UUID.test(x)) return x.toLowerCase(); return null; };

// null for an event troid Pro doesn't act on. Reads both API shapes: since 2025-03-31.basil a subscription's period end is
// on its items and an invoice names its subscription under parent.subscription_details; before, both were top-level.
function eventArgs(event) {
  if (!event || typeof event !== "object" || !HANDLED.has(event.type) || typeof event.id !== "string") return null;
  const o = (event.data && event.data.object) || {};
  const base = { p_event_id: event.id, p_type: event.type, p_livemode: event.livemode === true, p_created: at(event.created) };
  if (!base.p_created) return null;
  if (event.type === "checkout.session.completed") {
    const user = userIdOf(o.client_reference_id, o.metadata && o.metadata.user_id);
    if (o.mode !== "subscription" || !user || !idOf(o.subscription)) return null;   // not a troid Pro subscription checkout
    return { ...base, p_user_id: user, p_customer: idOf(o.customer), p_subscription: idOf(o.subscription) };
  }
  if (event.type === "invoice.payment_failed") {
    const sd = (o.parent && o.parent.subscription_details) || o.subscription_details || {};
    const sub = idOf(sd.subscription) || idOf(o.subscription);
    if (!sub) return null;                                               // not a subscription's invoice
    return { ...base, p_user_id: userIdOf(sd.metadata && sd.metadata.user_id), p_customer: idOf(o.customer), p_subscription: sub };
  }
  if (typeof o.id !== "string") return null;
  const item = (o.items && Array.isArray(o.items.data) && o.items.data[0]) || {};
  const periodEnd = item.current_period_end || o.current_period_end;
  const deleted = event.type === "customer.subscription.deleted" || o.status === "canceled";
  let until = at(periodEnd);
  if (o.cancel_at && (!periodEnd || o.cancel_at < periodEnd)) until = at(o.cancel_at);   // scheduled to end before the period does
  if (deleted) until = at(o.ended_at || o.canceled_at || event.created);                 // ended: access ends when it did
  return { ...base, p_user_id: userIdOf(o.metadata && o.metadata.user_id), p_customer: idOf(o.customer), p_subscription: o.id,
           p_status: deleted ? "canceled" : String(o.status || ""), p_price: idOf(item.price) || idOf(item.plan),
           p_pro_until: until, p_cancel_at_period_end: !!(o.cancel_at_period_end || o.cancel_at) };
}

module.exports = { CHECKOUT_COPY, PRICE_ENV, HANDLED, config, report, json, bearer, refused, body, returnOrigin, rawBody, log,
                   stripeError, signedIn, proStatus, applyEvent, checkoutParams, testClockCustomer, eventArgs };
