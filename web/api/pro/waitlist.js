"use strict";
/* troid Pro's waitlist (launch handoff 2026-09-26, 6.4 step 1): POST /api/pro/waitlist, from the page at /pro.
 *
 *   {email, pro: true, agents}   join, or change the choices: the email and the two choices into the store, with the
 *                                version of the consent the page showed and the date; the reply carries the leave link
 *   {leave: <token>}             leave, from the leave link's page: the email and its choices deleted at once
 *   ?t=<token> with the form body List-Unsubscribe=One-Click   a mail client's one-click unsubscribe (RFC 8058), for
 *                                the email that says troid Pro has opened
 *
 * Kept under waitlist:e:<sha256 of the email, lower-cased>, a year at most (set again on every join), the ids also in
 * the sets waitlist:pro and waitlist:agents, so SCARD counts each list in the Upstash console. Never an address, a user
 * agent or anything the page didn't send; the log line is counts only. A join answers the same whether the email was on
 * the list or not. A leave link is the id and an HMAC of it under TROID_WAITLIST_KEY, so only troid can make one.
 *
 * On with TROID_WAITLIST=on, TROID_WAITLIST_KEY (32 bytes or more) and the store (KV_REST_API_URL / KV_REST_API_TOKEN,
 * ask troid's); otherwise 404, as before it existed. Publishing the page is gate 0 in the handoff's 6.3: Vercel's Hobby
 * plan is for non-commercial use.
 */
const crypto = require("crypto");

const ON = process.env.TROID_WAITLIST === "on";
const KEY = process.env.TROID_WAITLIST_KEY || "";
const STORE_URL = (process.env.KV_REST_API_URL || process.env.UPSTASH_REDIS_REST_URL || "").replace(/\/+$/, "");
const STORE_TOKEN = process.env.KV_REST_API_TOKEN || process.env.UPSTASH_REDIS_REST_TOKEN || "";
const YEAR_S = "31536000";
const CONSENT = "2026-09-28";               // the page's two boxes and privacy line as shown (web/i18n/en.json pro.form.*)
const LIMIT_PER_HOUR = 10;
const EMAIL = /^[^\s@<>"',;:()[\]\\]+@[^\s@<>"',;:()[\]\\.]+(\.[^\s@<>"',;:()[\]\\.]+)+$/;

const on = () => ON && Buffer.byteLength(KEY) >= 32 && !!STORE_URL && !!STORE_TOKEN;
const idOf = (email) => crypto.createHash("sha256").update(email.trim().toLowerCase()).digest("hex");
const mac = (id) => crypto.createHmac("sha256", KEY).update("troid-waitlist-leave:" + id).digest("base64url");
const token = (id) => id + "." + mac(id);
function verify(t) {
  const m = /^([0-9a-f]{64})\.([A-Za-z0-9_-]{43})$/.exec(String(t || ""));
  if (!m) return null;
  const want = Buffer.from(mac(m[1])), got = Buffer.from(m[2]);
  return want.length === got.length && crypto.timingSafeEqual(want, got) ? m[1] : null;
}

function send(res, code, body) {
  res.statusCode = code;
  res.setHeader("content-type", "application/json; charset=utf-8");
  res.end(JSON.stringify(body));
}
async function store(commands) {
  const r = await fetch(STORE_URL + "/multi-exec", { method: "POST", signal: AbortSignal.timeout(3000),
    headers: { authorization: "Bearer " + STORE_TOKEN, "content-type": "application/json" }, body: JSON.stringify(commands) });
  const out = await r.json().catch(() => null);
  if (!r.ok || !Array.isArray(out) || out.some((x) => !x || x.error)) throw new Error("store " + r.status);
  return out.map((x) => x.result);
}
// a few joins an hour per address (IPv6 by /64), in memory, per instance, as ask troid limits its messages
const HITS = new Map();
function clientKey(req) {
  const ip = String(req.headers["x-real-ip"] || req.headers["x-forwarded-for"] || (req.socket && req.socket.remoteAddress) || "?").split(",")[0].trim();
  if (!ip.includes(":") || ip.includes(".")) return ip.replace(/^::ffff:/i, "");
  const [h, t = ""] = ip.split("%")[0].split("::"), a = h ? h.split(":") : [], b = t ? t.split(":") : [];
  return [...a, ...Array(Math.max(0, 8 - a.length - b.length)).fill("0"), ...b].slice(0, 4).join(":").toLowerCase() + "::/64";
}
function allow(key) {
  const now = Date.now(), keep = (HITS.get(key) || []).filter((t) => now - t < 3600e3);
  HITS.delete(key);
  if (keep.length >= LIMIT_PER_HOUR) { HITS.set(key, keep); return false; }
  keep.push(now); HITS.set(key, keep);
  for (const k of HITS.keys()) { if (HITS.size <= 5000) break; if (k !== key) HITS.delete(k); }
  return true;
}
function queryT(req) {
  try { return (req.query && req.query.t) || new URL(req.url || "/", "http://x").searchParams.get("t"); } catch (e) { return null; }
}

async function leave(res, t) {
  const id = verify(t);
  if (!id) return send(res, 403, { left: false, error: "not a leave link troid made" });
  try { await store([["DEL", "waitlist:e:" + id], ["SREM", "waitlist:pro", id], ["SREM", "waitlist:agents", id]]); }
  catch (e) { return send(res, 503, { left: false, error: "the waitlist can't be reached" }); }
  console.log(JSON.stringify({ troid: "waitlist", left: 1 }));
  return send(res, 200, { left: true });
}

module.exports = async (req, res) => {
  res.setHeader("cache-control", "no-store");
  if (!on()) return send(res, 404, { error: "Not found" });
  if (req.method !== "POST") return send(res, 405, { error: "POST" });
  const ct = String(req.headers["content-type"] || "");
  if (/^application\/x-www-form-urlencoded\b/i.test(ct)) {           // RFC 8058: the mail client's own POST
    const b = typeof req.body === "string" ? Object.fromEntries(new URLSearchParams(req.body)) : (req.body || {});
    if (b["List-Unsubscribe"] !== "One-Click") return send(res, 400, { error: "List-Unsubscribe=One-Click" });
    return leave(res, queryT(req));
  }
  if (!/^application\/json\b/i.test(ct)) return send(res, 415, { error: "Send application/json." });
  const site = req.headers["sec-fetch-site"];
  if (site && site !== "same-origin") return send(res, 403, { error: "troid's waitlist answers on troid.ai only." });
  if (!allow(clientKey(req))) return send(res, 429, { error: "too many tries from this address; try again in an hour" });
  let body = req.body;
  if (typeof body === "string") { try { body = JSON.parse(body); } catch (e) { body = null; } }
  if (!body || typeof body !== "object" || Array.isArray(body)) return send(res, 400, { error: "{email, pro: true, agents} or {leave}" });
  if (Object.prototype.hasOwnProperty.call(body, "leave")) return leave(res, body.leave);
  const email = typeof body.email === "string" ? body.email.trim() : "";
  if (!email || email.length > 254 || !EMAIL.test(email)) return send(res, 400, { field: "email", error: "an email address" });
  if (body.pro !== true) return send(res, 400, { field: "pro", error: "the first box: tell me when troid Pro opens" });
  const agents = body.agents === true, id = idOf(email);
  const entry = JSON.stringify({ email, pro: true, agents, consent: CONSENT, joined_utc: new Date().toISOString() });
  try {
    await store([["SET", "waitlist:e:" + id, entry, "EX", YEAR_S], ["SADD", "waitlist:pro", id], ["EXPIRE", "waitlist:pro", YEAR_S],
                 agents ? ["SADD", "waitlist:agents", id] : ["SREM", "waitlist:agents", id], ["EXPIRE", "waitlist:agents", YEAR_S]]);
  } catch (e) { return send(res, 503, { error: "the waitlist can't be reached" }); }
  console.log(JSON.stringify({ troid: "waitlist", joined: 1, agents: agents ? 1 : 0 }));
  return send(res, 200, { joined: true, leave_url: "/pro/leave?t=" + token(id) });
};
module.exports._token = token;
module.exports._idOf = idOf;
