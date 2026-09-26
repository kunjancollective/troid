"use strict";
/* Stripe's REST API for troid Pro (web/api/pro/*.js, web/api/stripe-webhook.js, web/pro_prices.js). No SDK: a few calls
   and one signature, the way the site already calls Upstash and Binance.US. Stripe-Version goes only on the call that
   needs one, the Checkout Session (managed_payments); every other call leaves it unset, so the account's default API
   version answers (the owner's handoff, after Stripe's blueprint). */
const crypto = require("crypto");

// managed_payments on Checkout Sessions is generally available from API version 2026-04-22.dahlia: stripe-node 22.1.0's
// changelog adds "managed_payments on Checkout.SessionCreateParams, Checkout.Session, PaymentIntent, PaymentLinkCreateParams,
// PaymentLink, SetupIntent, and Subscription", and Stripe's GA OpenAPI spec describes the setting as covering the session's
// "resulting PaymentIntents, Invoices, and Subscriptions". The blueprint's 2026-02-25.preview predates that; the handoff
// asks for it "or later". This is the version stripe-node 22.6.2 pins, the newest GA version on 2026-09-26.
const CHECKOUT_API_VERSION = "2026-08-26.dahlia";
const TOLERANCE_S = 300;   // stripe-node's DEFAULT_TOLERANCE: an event signed more than five minutes ago is refused

// Tests point the client at a local fake; nothing else may, so the key can only ever go to Stripe.
const apiBase = () => {
  const b = (process.env.STRIPE_API_BASE || "").replace(/\/+$/, "");
  return /^http:\/\/(127\.0\.0\.1|localhost)(:\d+)?$/.test(b) ? b : "https://api.stripe.com";
};

// "test" or "live" from a key's prefix (secret or restricted; publishable); null for anything else.
const keyMode = (key) => { const m = /^[rs]k_(test|live)_/.exec(String(key || "")); return m ? m[1] : null; };
const publishableMode = (key) => { const m = /^pk_(test|live)_/.exec(String(key || "")); return m ? m[1] : null; };

// Stripe's form encoding: nested objects as a[b][c]=v, arrays as a[0][b]=v; null and undefined are left out.
function form(params) {
  const out = [];
  (function walk(v, key) {
    if (v === undefined || v === null) return;
    if (typeof v === "object") { for (const [k, x] of Object.entries(v)) walk(x, key ? key + "[" + k + "]" : k); return; }
    out.push(encodeURIComponent(key) + "=" + encodeURIComponent(String(v)));
  })(params || {}, "");
  return out.join("&");
}

// One API call. Throws with Stripe's error type, code, param and message on a non-2xx answer.
async function request(key, method, path, params, opts = {}) {
  const headers = { authorization: "Bearer " + key };
  if (opts.version) headers["stripe-version"] = opts.version;
  let url = apiBase() + path, body;
  const q = form(params);
  if (method === "GET") { if (q) url += "?" + q; }
  else { headers["content-type"] = "application/x-www-form-urlencoded"; body = q; }
  const r = await fetch(url, { method, headers, body, signal: AbortSignal.timeout(opts.timeoutMs || 10_000) });
  const text = await r.text();
  let data = null;
  try { data = JSON.parse(text); } catch (e) { /* not JSON: reported by status below */ }
  if (!r.ok) {
    const e = (data && data.error) || {};
    throw Object.assign(new Error(e.message || "Stripe answered " + r.status),
                        { stripe: true, status: r.status, type: e.type || null, code: e.code || null, param: e.param || null });
  }
  return data;
}

// Stripe-Signature is "t=<unix time>,v1=<hex>[,v1=<hex>…]": HMAC-SHA256 of "<t>.<raw body>" under the endpoint's signing
// secret. As stripe-node's verifyHeader: any v1 may match (Stripe signs with both secrets while one is rolled), and an
// event signed more than TOLERANCE_S ago is refused. The body must be the bytes Stripe sent, never re-serialised JSON.
function verifySignature(payload, header, secret, nowS = Math.floor(Date.now() / 1000)) {
  if (!secret) return { ok: false, reason: "no signing secret" };
  if (typeof header !== "string" || !header) return { ok: false, reason: "no Stripe-Signature header" };
  let t = -1;
  const sigs = [];
  for (const item of header.split(",")) {
    const [k, v] = item.split("=");
    if (k === "t") t = parseInt(v, 10);
    else if (k === "v1" && v) sigs.push(v);
  }
  if (!(t > 0) || !sigs.length) return { ok: false, reason: "malformed Stripe-Signature header" };
  const want = Buffer.from(crypto.createHmac("sha256", secret).update(t + ".").update(payload).digest("hex"));
  const match = sigs.some((s) => { const got = Buffer.from(s); return got.length === want.length && crypto.timingSafeEqual(got, want); });
  if (!match) return { ok: false, reason: "signature mismatch" };
  if (nowS - t > TOLERANCE_S) return { ok: false, reason: "signed more than " + TOLERANCE_S + " s ago" };
  return { ok: true, t };
}

module.exports = { CHECKOUT_API_VERSION, TOLERANCE_S, keyMode, publishableMode, form, request, verifySignature };
