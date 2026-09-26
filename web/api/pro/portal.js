"use strict";
/* POST /api/pro/portal, with "Authorization: Bearer <Supabase access token>" → {url}: Stripe's customer portal for the
   signed-in user's Stripe customer, where they cancel, switch between monthly and yearly and download invoices
   (handoff item 5: cancelling online must be as simple as signing up, under ROSCA and Connecticut's law). The account
   page's "Manage subscription" link opens it. No Stripe-Version: the account's default answers. */
const P = require("../../lib/pro.js");
const S = require("../../lib/stripe.js");

module.exports = async (req, res) => {
  const c = P.config();
  if (!c.on) return P.json(res, 503, { error: "troid Pro is switched off here.", ...P.report(c) });
  if (req.method !== "POST") return P.json(res, 405, { error: "POST" });
  const no = P.refused(req);
  if (no) return P.json(res, no.code, { error: no.error });
  const token = P.bearer(req);
  if (!token) return P.json(res, 401, { error: "Sign in first." });

  let st;
  try { st = await P.proStatus(c, token); } catch (e) {
    P.log({ route: "portal", error: "store", status: e.status || null });
    return P.json(res, 502, { error: "The account service didn't answer. Try again." });
  }
  if (!st) return P.json(res, 401, { error: "Sign in again." });
  if (!st.customer) return P.json(res, 404, { error: "This account has no troid Pro subscription to manage." });

  try {
    const session = await S.request(c.secretKey, "POST", "/v1/billing_portal/sessions",
                                    { customer: st.customer, return_url: P.returnOrigin(c, req) + "/account" });
    P.log({ route: "portal", mode: c.mode });
    return P.json(res, 200, { url: session.url });
  } catch (e) {
    P.log({ route: "portal", mode: c.mode, error: "stripe", status: e.status || null, type: e.type || null, code: e.code || null });
    return P.json(res, 502, P.stripeError(c, e));
  }
};
