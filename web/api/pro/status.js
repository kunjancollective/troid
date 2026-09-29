"use strict";
/* GET /api/pro/status. Without a token: whether troid Pro is switched on here and, off production, which settings are
   missing (names only). With "Authorization: Bearer <Supabase access token>": the signed-in user's own Pro state, the
   same check every Pro feature makes (lib/pro.js proStatus). The success page polls this; it never grants anything. */
const P = require("../../lib/pro.js");

module.exports = async (req, res) => {
  const c = P.config();
  if (req.method !== "GET") return P.json(res, 405, { error: "GET" });
  const token = P.bearer(req);
  if (!token || !c.on) return P.json(res, c.on ? 200 : 503, P.report(c));
  let st;
  try { st = await P.proStatus(c, token); } catch (e) {
    P.log({ route: "status", error: "store", status: e.status || null });
    return P.json(res, 502, { error: "The account service didn't answer. Try again." });
  }
  if (!st) return P.json(res, 401, { error: "Sign in again." });
  return P.json(res, 200, { mode: c.mode, pro: st.pro, status: st.status, pro_until: st.pro_until,
                            cancel_at_period_end: st.cancel_at_period_end, payment_failed_at: st.payment_failed_at,
                            manage: !!st.customer });
};
