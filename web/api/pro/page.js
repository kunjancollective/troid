"use strict";
/* /pro, /pro/thanks and /account (vercel.json rewrites) → web/pro/index.html, the test-mode page: sign in, choose monthly
   or yearly, come back from Checkout, see the account's state and open Stripe's portal. Served only while troid Pro is
   switched on here (lib/pro.js config); everywhere else, production included, the three routes answer 404 as they did
   before they existed. Not a published page: the real ones go through web/templates and web/i18n at launch.
   The page gets the Supabase URL and publishable key (public by design) and a fresh CSP nonce on every response. */
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const P = require("../../lib/pro.js");

const VIEWS = new Set(["pro", "thanks", "account"]);
let HTML = null;
function page() {
  if (HTML) return HTML;
  for (const base of [process.cwd(), path.join(__dirname, "..", "..")]) {
    try { return (HTML = fs.readFileSync(path.join(base, "pro", "index.html"), "utf8")); } catch (e) { /* next */ }
  }
  throw new Error("pro/index.html missing");
}
function view(req) {
  let v = null;
  try { v = (req.query && req.query.view) || new URL(req.url || "/", "http://x").searchParams.get("view"); } catch (e) { v = null; }
  return VIEWS.has(v) ? v : "pro";
}

module.exports = (req, res) => {
  res.setHeader("cache-control", "no-store");
  const c = P.config();
  if (!c.on || (req.method !== "GET" && req.method !== "HEAD")) {
    res.statusCode = c.on ? 405 : 404;
    res.setHeader("content-type", "text/plain; charset=utf-8");
    return res.end(c.on ? "GET" : "Not found");
  }
  let html;
  try { html = page(); } catch (e) { res.statusCode = 500; return res.end("page missing"); }
  const nonce = crypto.randomBytes(16).toString("base64");
  const cfg = { mode: c.mode, view: view(req), supabaseUrl: c.supabaseUrl, supabaseKey: c.supabasePublishable, copy: P.CHECKOUT_COPY };
  html = html.replaceAll("{{NONCE}}", nonce).replace("{{CONFIG}}", JSON.stringify(cfg).replace(/</g, "\\u003c"));
  res.statusCode = 200;
  res.setHeader("content-type", "text/html; charset=utf-8");
  res.setHeader("x-robots-tag", "noindex, nofollow");
  res.setHeader("content-security-policy", [
    "default-src 'none'",
    "script-src 'nonce-" + nonce + "' https://cdn.jsdelivr.net",
    "style-src 'unsafe-inline'",
    "connect-src 'self' " + c.supabaseUrl,
    "img-src 'self' data:",
    "base-uri 'none'", "form-action 'self'", "frame-ancestors 'none'",
  ].join("; "));
  res.end(req.method === "HEAD" ? undefined : html);
};
