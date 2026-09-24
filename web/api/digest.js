"use strict";
/* GET /api/digest — the weekly count of what people ask ask troid (lib/faq_digest.js). Called by Vercel Cron
   (vercel.json, Mondays) with "Authorization: Bearer $CRON_SECRET"; answers nothing to anyone else. Keeps
   digest:<ISO week> in the conversation store with no expiry and returns only the totals. ?week=2026-W39 recounts
   a week whose conversations are still inside their 30 days. */
const crypto = require("crypto");
const D = require("../lib/faq_digest.js");

const json = (res, code, obj) => { res.statusCode = code; res.setHeader("content-type", "application/json"); res.setHeader("cache-control", "no-store"); res.end(JSON.stringify(obj)); };
const same = (a, b) => { const x = Buffer.from(String(a)), y = Buffer.from(String(b)); return x.length === y.length && crypto.timingSafeEqual(x, y); };

module.exports = async (req, res) => {
  const secret = process.env.CRON_SECRET || "";
  if (Buffer.byteLength(secret) < 16) return json(res, 503, { error: "not configured" });
  if (!same(req.headers.authorization || "", "Bearer " + secret)) return json(res, 401, { error: "unauthorized" });
  const url = process.env.KV_REST_API_URL || process.env.UPSTASH_REDIS_REST_URL || "";
  const token = process.env.KV_REST_API_TOKEN || process.env.UPSTASH_REDIS_REST_TOKEN || "";
  if (!url || !token) return json(res, 503, { error: "no store" });
  let week;
  try {
    const q = (req.query && req.query.week) || new URL(req.url || "/", "http://x").searchParams.get("week");
    week = q || D.lastWeek(new Date());
    D.weekRange(week);
  } catch (e) { return json(res, 400, { error: "week must look like 2026-W39" }); }
  try {
    const d = await D.run(D.upstash(url, token), week, new Date());
    console.log(JSON.stringify({ troid: "digest", week, conversations: d.conversations, messages: d.messages }));
    return json(res, 200, { week, key: "digest:" + week, conversations: d.conversations, messages: d.messages, topics: Object.keys(d.topics).length });
  } catch (e) { return json(res, 502, { error: "store unavailable" }); }
};
