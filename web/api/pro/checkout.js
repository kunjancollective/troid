"use strict";
/* POST /api/pro/checkout {plan: "monthly" | "yearly"}, with "Authorization: Bearer <Supabase access token>" → {url}.
   A Stripe Checkout Session for troid Pro in subscription mode with Managed Payments on, so Stripe is the merchant of
   record and handles sales tax worldwide (handoff items 2, 3 and 6). The page sends the browser to the url; access
   comes later, from the webhook, never from the success page. 409 when the account already has Pro. */
const P = require("../../lib/pro.js");
const S = require("../../lib/stripe.js");

module.exports = async (req, res) => {
  const c = P.config();
  if (!c.on) return P.json(res, 503, { error: "troid Pro is switched off here.", ...P.report(c) });
  if (req.method !== "POST") return P.json(res, 405, { error: 'POST {plan: "monthly" | "yearly"}' });
  const no = P.refused(req);
  if (no) return P.json(res, no.code, { error: no.error });
  const token = P.bearer(req);
  if (!token) return P.json(res, 401, { error: "Sign in first." });
  const plan = P.body(req).plan;
  if (!Object.prototype.hasOwnProperty.call(P.PRICE_ENV, plan)) return P.json(res, 400, { error: 'plan must be "monthly" or "yearly".' });

  let user, st;
  try {
    user = await P.signedIn(c, token);
    st = user ? await P.proStatus(c, token) : null;
  } catch (e) {
    P.log({ route: "checkout", error: "store", status: e.status || null });
    return P.json(res, 502, { error: "The account service didn't answer. Nothing was charged; try again." });
  }
  if (!user || !st) return P.json(res, 401, { error: "Sign in again." });
  if (st.pro) return P.json(res, 409, { error: "This account already has troid Pro. Manage it from the account page.", manage: true });

  try {
    let customer = st.customer;                          // a returning subscriber keeps one Stripe customer
    if (!customer && c.testClock) customer = await P.testClockCustomer(c, user);
    const session = await S.request(c.secretKey, "POST", "/v1/checkout/sessions",
                                    P.checkoutParams(c, user, plan, P.returnOrigin(c, req), customer),
                                    { version: S.CHECKOUT_API_VERSION });
    P.log({ route: "checkout", mode: c.mode, plan, returning: !!st.customer, session: session.id });
    return P.json(res, 200, { url: session.url });
  } catch (e) {
    P.log({ route: "checkout", mode: c.mode, plan, error: "stripe", status: e.status || null, type: e.type || null, code: e.code || null, param: e.param || null });
    return P.json(res, 502, P.stripeError(c, e));
  }
};
