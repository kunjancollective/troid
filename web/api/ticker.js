"use strict";
/* GET /api/ticker — the price strip under every page's header (design handoff 2026-09-24, section 3): the last spot
   price and 24-hour change of the five assets troid's research covers.

   From api.binance.us, the feed troid's ledger runs on (CLAUDE.md, Feeds: one feed end to end; api.binance.com refuses
   US regions), in USDT pairs. The server fetches and the CDN keeps the answer for 15 seconds (s-maxage=15,
   stale-while-revalidate=30), so there is about one upstream call per 15 s whatever the traffic; a warm instance also
   remembers its last answer for 15 s, so a query string can't turn visitors' requests into upstream calls. A visitor's
   browser talks only to troid.ai: no cookie, no third party. Display only: nothing here is stored, sized against or
   turned into a signal. A failed upstream answers 502, briefly cached, and the page hides the strip.

   Each price keeps the exchange's own digits ("84496.41"), so "use as entry" on the desk takes the price as quoted.
   `as_of` is the exchange's time for the figures and `served` this function's; with the CDN's Age header they tell
   the page how old a price is without trusting the visitor's clock. */
const SYMBOLS = [["BTC", "BTCUSDT"], ["ETH", "ETHUSDT"], ["SOL", "SOLUSDT"], ["XRP", "XRPUSDT"], ["BNB", "BNBUSDT"]];
const SOURCE = "Binance.US";
const UPSTREAM = "https://api.binance.us/api/v3/ticker/24hr?symbols=" + encodeURIComponent(JSON.stringify(SYMBOLS.map((s) => s[1])));
const TIMEOUT_MS = 4000;
const KEEP_MS = 15000;
const CACHE_OK = "public, max-age=0, s-maxage=15, stale-while-revalidate=30";
const CACHE_FAIL = "public, max-age=0, s-maxage=10";

const digits = (s) => (/^\d+\.\d+$/.test(s) ? s.replace(/0+$/, "").replace(/\.$/, "") : s);   // "84496.41000000" -> "84496.41"

function parse(rows, now) {
  if (!Array.isArray(rows)) throw new Error("upstream answered something other than a list");
  const by = new Map(rows.filter((r) => r && typeof r.symbol === "string").map((r) => [r.symbol, r]));
  const items = [];
  for (const [sym, pair] of SYMBOLS) {
    const r = by.get(pair);
    if (!r || typeof r.lastPrice !== "string" || !/^\d+(\.\d+)?$/.test(r.lastPrice) || !(+r.lastPrice > 0)) continue;
    const chg = Number(r.priceChangePercent), at = Number(r.closeTime);
    items.push({ sym, pair, last: digits(r.lastPrice), chg_pct: Number.isFinite(chg) ? chg : null, at: Number.isFinite(at) ? at : null });
  }
  if (!items.length) throw new Error("no prices in the upstream answer");
  const times = items.map((i) => i.at).filter((t) => t != null && t <= now + 60000);
  return { source: SOURCE, quote: "USDT", as_of: times.length ? Math.max(...times) : now, served: now, items };
}

let kept = null;          // { at, body } — this instance's last good answer
let inflight = null;      // one upstream call at a time per instance

async function upstream() {
  const ctl = new AbortController(), t = setTimeout(() => ctl.abort(), TIMEOUT_MS);
  try {
    const r = await fetch(UPSTREAM, { signal: ctl.signal, headers: { accept: "application/json" } });
    if (!r.ok) throw new Error("upstream " + r.status);
    return parse(await r.json(), Date.now());
  } finally { clearTimeout(t); }
}

module.exports = async (req, res) => {
  const send = (code, cache, obj) => {
    res.statusCode = code;
    res.setHeader("content-type", "application/json; charset=utf-8");
    res.setHeader("cache-control", cache);
    res.end(JSON.stringify(obj));
  };
  if (req.method !== "GET" && req.method !== "HEAD") { res.setHeader("allow", "GET, HEAD"); return send(405, "no-store", { error: "GET only" }); }
  const now = Date.now();
  if (kept && now - kept.at < KEEP_MS) return send(200, CACHE_OK, kept.body);
  try {
    inflight = inflight || upstream().finally(() => { inflight = null; });
    const body = await inflight;
    kept = { at: Date.now(), body };
    return send(200, CACHE_OK, body);
  } catch (e) {
    return send(502, CACHE_FAIL, { error: "prices unavailable", source: SOURCE });
  }
};
module.exports._parse = parse;
module.exports._reset = () => { kept = null; inflight = null; };
module.exports.SYMBOLS = SYMBOLS;
module.exports.SOURCE = SOURCE;
module.exports.UPSTREAM = UPSTREAM;
