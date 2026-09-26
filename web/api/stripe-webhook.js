"use strict";
/* POST /api/stripe-webhook — Stripe's events for troid Pro (handoff item 4). Verified against the raw body with
   STRIPE_WEBHOOK_SECRET; an event of the other mode is refused. Acts on five types, through one database function that
   records the event id and applies the change in one transaction (supabase/migrations/…_troid_pro_billing.sql):
     checkout.session.completed      links the Stripe customer and subscription to the user
     customer.subscription.*         sets status and pro_until (the period's end; when it ended, once it has)
     invoice.payment_failed          marks the account past due; access continues until Stripe gives up
   A repeat changes nothing ("duplicate"); anything else is answered 200 "ignored". A failure to record answers 500,
   so Stripe retries. The only place access is granted. */
const P = require("../lib/pro.js");
const S = require("../lib/stripe.js");

module.exports = async (req, res) => {
  const c = P.config();
  if (!c.on) return P.json(res, 503, { error: "troid Pro is switched off here." });
  if (req.method !== "POST") return P.json(res, 405, { error: "POST" });

  let raw;
  try { raw = await P.rawBody(req); } catch (e) {
    P.log({ route: "webhook", refused: e.message });
    return P.json(res, e.status || 400, { error: e.message });
  }
  const sig = S.verifySignature(raw, req.headers["stripe-signature"], c.webhookSecret);
  if (!sig.ok) {
    P.log({ route: "webhook", refused: sig.reason });
    return P.json(res, 400, { error: "signature: " + sig.reason });
  }
  let event;
  try { event = JSON.parse(raw.toString("utf8")); } catch (e) { return P.json(res, 400, { error: "the body is not JSON" }); }
  if ((event.livemode === true) !== (c.mode === "live")) {
    P.log({ route: "webhook", event: event.id, refused: "mode" });
    return P.json(res, 400, { error: "a " + (event.livemode ? "live" : "test") + "-mode event reached troid Pro in " + c.mode + " mode" });
  }

  const args = P.eventArgs(event);
  if (!args) {
    P.log({ route: "webhook", event: event.id, type: event.type, outcome: "ignored" });
    return P.json(res, 200, { received: true, outcome: "ignored" });
  }
  try {
    const outcome = await P.applyEvent(c, args);
    P.log({ route: "webhook", event: event.id, type: event.type, outcome });
    return P.json(res, 200, { received: true, outcome });
  } catch (e) {
    P.log({ route: "webhook", event: event.id, type: event.type, error: "store", status: e.status || null });
    return P.json(res, 500, { error: "not recorded; Stripe will retry" });
  }
};
