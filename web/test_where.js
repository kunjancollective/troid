"use strict";
/* Tests for /api/where (web/api/where.js): the visitor's country from Vercel's x-vercel-ip-country, or null; never
   cached; GET and HEAD only. node web/test_where.js */
const W = require("./api/where.js");
let fails = 0, n = 0;
const ok = (name, cond, info) => { n++; if (cond) console.log("ok   " + name); else { fails++; console.log("FAIL " + name, info === undefined ? "" : JSON.stringify(info).slice(0, 400)); } };
function call(headers, method = "GET") {
  const r = { headers: {}, statusCode: 0, body: "" };
  r.setHeader = (k, v) => { r.headers[k.toLowerCase()] = v; };
  r.end = (b) => { r.body = b || ""; };
  W({ method, url: "/api/where", headers }, r);
  return { r, j: r.body ? JSON.parse(r.body) : null };
}
let c = call({ "x-vercel-ip-country": "FR" });
ok("FR: 200 {country: FR}", c.r.statusCode === 200 && c.j.country === "FR" && Object.keys(c.j).join() === "country", c.j);
ok("never cached: private, no-store", c.r.headers["cache-control"] === "private, no-store", c.r.headers);
ok("JSON", /^application\/json/.test(c.r.headers["content-type"]), c.r.headers);
ok("lower case is normalised: us -> US", call({ "x-vercel-ip-country": " us " }).j.country === "US");
for (const bad of [undefined, "", "XX", "U", "USA", "1A", "F R", ["FR"]]) {
  const h = bad === undefined ? {} : { "x-vercel-ip-country": bad };
  ok(`no country read from ${JSON.stringify(bad)}: null (the page hides every link)`, call(h).j.country === null, call(h).j);
}
ok("nothing else answered: no address, no other header echoed",
   JSON.stringify(call({ "x-vercel-ip-country": "IN", "x-forwarded-for": "203.0.113.9", "x-vercel-ip-city": "Pune" }).j) === '{"country":"IN"}');
c = call({ "x-vercel-ip-country": "FR" }, "POST");
ok("POST: 405, GET and HEAD allowed", c.r.statusCode === 405 && c.r.headers.allow === "GET, HEAD", c.r);
ok("HEAD answers like GET", call({ "x-vercel-ip-country": "DE" }, "HEAD").r.statusCode === 200);
console.log(`\n${fails ? fails + " failed" : "all passed"} (${n} checks)`);
process.exit(fails ? 1 : 0);
