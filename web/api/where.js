"use strict";
/* GET /api/where — the visitor's country, for web/public/geo.js, which hides troid's affiliate links where geo.json
   lists the country (launch handoff 5.3, the owner's decision, 2026-10-03). It returns Vercel's x-vercel-ip-country
   header and nothing else: no address, no cookie, nothing stored or logged. A missing or malformed header answers
   {"country": null}, which geo.js treats as unknown and hides every link (fail closed). Never cached: the answer is
   the visitor's own. */
module.exports = (req, res) => {
  const send = (code, obj) => {
    res.statusCode = code;
    res.setHeader("content-type", "application/json; charset=utf-8");
    res.setHeader("cache-control", "private, no-store");
    res.end(JSON.stringify(obj));
  };
  if (req.method !== "GET" && req.method !== "HEAD") { res.setHeader("allow", "GET, HEAD"); return send(405, { error: "GET only" }); }
  const h = (req.headers || {})["x-vercel-ip-country"];
  const cc = typeof h === "string" ? h.trim().toUpperCase() : "";
  return send(200, { country: /^[A-Z]{2}$/.test(cc) && cc !== "XX" ? cc : null });
};
