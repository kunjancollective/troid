"use strict";
/* Tests for /api/ticker (web/api/ticker.js) against a stubbed upstream: no network. node web/test_ticker.js */
const T = require("./api/ticker.js");
let fails = 0, n = 0;
const ok = (name, cond, info) => { n++; if (cond) console.log("ok   " + name); else { fails++; console.log("FAIL " + name, info === undefined ? "" : JSON.stringify(info).slice(0, 400)); } };

const ROWS = [
  { symbol: "XRPUSDT", lastPrice: "1.53850000", priceChangePercent: "2.923", closeTime: 1790276356006 },
  { symbol: "BTCUSDT", lastPrice: "84496.41000000", priceChangePercent: "-0.172", closeTime: 1790276355896 },
  { symbol: "ETHUSDT", lastPrice: "2692.58000000", priceChangePercent: "0.805", closeTime: 1790276355983 },
  { symbol: "BNBUSDT", lastPrice: "780.00000000", priceChangePercent: "1.844", closeTime: 1790276355996 },
  { symbol: "SOLUSDT", lastPrice: "117.47000000", priceChangePercent: "2.791", closeTime: 1790276356047 },
];
function res() {
  const r = { headers: {}, statusCode: 0, body: "" };
  r.setHeader = (k, v) => { r.headers[k.toLowerCase()] = v; };
  r.end = (b) => { r.body = b || ""; };
  return r;
}
async function call(method = "GET", url = "/api/ticker") { const r = res(); await T({ method, url, headers: {} }, r); return { r, j: r.body ? JSON.parse(r.body) : null }; }

(async () => {
  let calls = 0, answer = () => ({ ok: true, status: 200, json: async () => ROWS });
  global.fetch = async (url) => { calls++; return answer(url); };

  // parse: the five in the strip's order, the exchange's digits less trailing zeros, the change as a number
  const p = T._parse(ROWS, 1790276357000);
  ok("parse: five symbols in the strip's order", p.items.map((x) => x.sym).join() === "BTC,ETH,SOL,XRP,BNB", p.items);
  ok("parse: prices as the exchange quoted them, trailing zeros dropped", p.items.map((x) => x.last).join() === "84496.41,2692.58,117.47,1.5385,780", p.items);
  ok("parse: 24 h change and times", p.items[0].chg_pct === -0.172 && p.as_of === 1790276356047 && p.served === 1790276357000 && p.source === "Binance.US" && p.quote === "USDT", p);
  ok("parse: a missing or malformed row is left out, not guessed", T._parse([ROWS[1], { symbol: "ETHUSDT", lastPrice: "abc" }, { symbol: "SOLUSDT", lastPrice: "0" }], 1).items.map((x) => x.sym).join() === "BTC");
  let threw = false; try { T._parse({ code: -1121, msg: "Invalid symbol." }, 1); } catch (e) { threw = true; }
  ok("parse: an error object is not prices", threw);
  ok("the upstream is binance.us, one call for the five", T.UPSTREAM.startsWith("https://api.binance.us/api/v3/ticker/24hr?symbols=") && /BTCUSDT.*BNBUSDT/.test(decodeURIComponent(T.UPSTREAM)));

  // handler: cached at the CDN for 15 s, stale for 30 more; one upstream call per 15 s per instance, whatever the query
  T._reset(); calls = 0;
  let { r, j } = await call();
  ok("GET: 200 with the five prices", r.statusCode === 200 && j.items.length === 5, j);
  ok("GET: the CDN keeps it 15 s, the browser never", r.headers["cache-control"] === "public, max-age=0, s-maxage=15, stale-while-revalidate=30", r.headers);
  await call("GET", "/api/ticker?x=1"); await call("GET", "/api/ticker?x=2");
  ok("three requests, one with a query string each, make one upstream call", calls === 1, calls);
  T._reset(); calls = 0;
  await Promise.all([call(), call(), call()]);
  ok("concurrent requests share one upstream call", calls === 1, calls);

  // failure: 502, cached briefly, the page hides the strip
  T._reset(); answer = () => ({ ok: false, status: 451, json: async () => ({}) });
  ({ r, j } = await call());
  ok("upstream refused: 502, cached 10 s, no prices", r.statusCode === 502 && r.headers["cache-control"] === "public, max-age=0, s-maxage=10" && !j.items, [r.statusCode, r.headers, j]);
  T._reset(); answer = () => { throw new Error("network"); };
  ({ r } = await call());
  ok("upstream unreachable: 502", r.statusCode === 502);
  T._reset(); answer = () => ({ ok: true, status: 200, json: async () => ({ code: -1121, msg: "Invalid symbol." }) });
  ({ r } = await call());
  ok("upstream answered an error object: 502", r.statusCode === 502);
  ({ r } = await call("POST"));
  ok("POST: 405, never cached", r.statusCode === 405 && r.headers["cache-control"] === "no-store");

  // the strip and the API name the same symbols and source (site_build.py reads them from this file)
  const fs = require("fs"), path = require("path");
  const en = JSON.parse(fs.readFileSync(path.join(__dirname, "i18n", "en.json"), "utf8"));
  const page = fs.readFileSync(path.join(__dirname, "public", "index.html"), "utf8");
  ok("the desk's strip carries the five symbols and names the source", T.SYMBOLS.every(([s]) => page.includes(`data-sym="${s}"`)) && page.includes('data-source="Binance.US"')
     && page.includes(en["ticker.label"].replace("{source}", "Binance.US")));
  console.log(`RESULT: ${fails} failed (${n} checks)`);
  process.exit(fails ? 1 : 0);
})();
