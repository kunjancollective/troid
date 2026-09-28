"use strict";
/* /pro, /pro/thanks and /account (vercel.json rewrites) → web/pro/index.html, the test-mode page: sign in, choose monthly
   or yearly, come back from Checkout, see the account's state and open Stripe's portal. Served only while troid Pro is
   switched on here (lib/pro.js config); everywhere else, production included, the three routes answer 404 as they did
   before they existed. Not a published page: the real ones go through web/templates and web/i18n at launch.
   The page gets the Supabase URL and publishable key (public by design) and a fresh CSP nonce on every response.

   troid Pro's waitlist (launch handoff 6.4 step 1) → web/pro/waitlist.html, rendered from web/templates/pro.html by
   site_build.py, served while TROID_WAITLIST is on (with its key; web/api/pro/waitlist.js takes the form): at /pro where
   troid Pro's test mode is off (production), at /pro/waitlist anywhere, and at /pro/leave, the leave link's page. */
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const P = require("../../lib/pro.js");

const VIEWS = new Set(["pro", "thanks", "account", "waitlist", "leave"]);
const FILES = {};
function file(name) {
  if (FILES[name]) return FILES[name];
  for (const base of [process.cwd(), path.join(__dirname, "..", "..")]) {
    try { return (FILES[name] = fs.readFileSync(path.join(base, "pro", name), "utf8")); } catch (e) { /* next */ }
  }
  throw new Error("pro/" + name + " missing");
}
const page = () => file("index.html");
const waitlistOn = () => process.env.TROID_WAITLIST === "on" && Buffer.byteLength(process.env.TROID_WAITLIST_KEY || "") >= 32;
function view(req) {
  let v = null;
  try { v = (req.query && req.query.view) || new URL(req.url || "/", "http://x").searchParams.get("view"); } catch (e) { v = null; }
  return VIEWS.has(v) ? v : "pro";
}

module.exports = (req, res) => {
  res.setHeader("cache-control", "no-store");
  const c = P.config();
  let v = view(req);
  if (v === "pro" && !c.on && waitlistOn()) v = "waitlist";          // /pro: the test page where test mode is on, else the waitlist
  if (v === "waitlist" || v === "leave") {
    if (!waitlistOn() || (req.method !== "GET" && req.method !== "HEAD")) {
      res.statusCode = waitlistOn() ? 405 : 404;
      res.setHeader("content-type", "text/plain; charset=utf-8");
      return res.end(waitlistOn() ? "GET" : "Not found");
    }
    let html;
    try { html = file("waitlist.html"); } catch (e) { res.statusCode = 500; return res.end("page missing"); }
    res.statusCode = 200;
    res.setHeader("content-type", "text/html; charset=utf-8");
    res.setHeader("referrer-policy", "no-referrer");                   // the leave link's token never leaves in a Referer
    if (v === "leave") res.setHeader("x-robots-tag", "noindex, nofollow");
    return res.end(req.method === "HEAD" ? undefined : html);
  }
  if (!c.on || (req.method !== "GET" && req.method !== "HEAD")) {
    res.statusCode = c.on ? 405 : 404;
    res.setHeader("content-type", "text/plain; charset=utf-8");
    return res.end(c.on ? "GET" : "Not found");
  }
  let html;
  try { html = page(); } catch (e) { res.statusCode = 500; return res.end("page missing"); }
  const nonce = crypto.randomBytes(16).toString("base64");
  const cfg = { mode: c.mode, view: v, supabaseUrl: c.supabaseUrl, supabaseKey: c.supabasePublishable, copy: P.CHECKOUT_COPY };
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
