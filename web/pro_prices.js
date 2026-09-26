"use strict";
/* troid Pro's price IDs from Stripe, read-only, for STRIPE_PRICE_MONTHLY and STRIPE_PRICE_YEARLY (the handoff: "look up
   troid Pro and its two price IDs through the API"). The owner runs it on their own machine with the key in their own
   shell, never pasted anywhere:
       STRIPE_SECRET_KEY=<the restricted test key> node web/pro_prices.js
   It prints the product, its tax code and every active price, checks them against the handoff (troid Pro, USD 19.00 a
   month and 190.00 a year, recurring), and prints the two lines to set in Vercel. Price IDs aren't secrets. Creates and
   changes nothing; no Stripe-Version, so the account's default answers. Exit 0 when every check passes. */
const S = require("./lib/stripe.js");

const WANT = { month: { amount: 1900, env: "STRIPE_PRICE_MONTHLY" }, year: { amount: 19000, env: "STRIPE_PRICE_YEARLY" } };
const idOf = (x) => (x && typeof x === "object" ? x.id : x) || null;
const money = (p) => (p.unit_amount == null ? "custom" : (p.unit_amount / 100).toFixed(2)) + " " + String(p.currency).toUpperCase();

(async () => {
  const key = process.env.STRIPE_SECRET_KEY || "";
  const mode = S.keyMode(key);
  if (!mode) { console.error("Set STRIPE_SECRET_KEY in this shell to a secret or restricted key (test mode for now)."); process.exit(2); }
  const products = (await S.request(key, "GET", "/v1/products", { active: true, limit: 100 })).data;
  const found = products.filter((p) => String(p.name || "").trim().toLowerCase() === "troid pro");
  if (found.length !== 1) {
    console.error(`${mode} mode: ${found.length} active products named "troid Pro" (of ${products.length} active). Expected one.`);
    process.exit(1);
  }
  const product = found[0];
  console.log(`${mode} mode · product ${product.id} "${product.name}" · tax code ${idOf(product.tax_code) || "none"}`);
  const prices = (await S.request(key, "GET", "/v1/prices", { product: product.id, active: true, limit: 100 })).data;
  for (const p of prices) {
    const r = p.recurring;
    console.log(`  ${p.id}  ${money(p)}  ${r ? "every " + (r.interval_count > 1 ? r.interval_count + " " : "") + r.interval : "one-time"}` +
                `  tax behavior ${p.tax_behavior || "unspecified"}${p.lookup_key ? "  lookup key " + p.lookup_key : ""}`);
  }
  let good = !!idOf(product.tax_code);
  if (!good) console.log("  ✗ the product has no tax code; Managed Payments needs an eligible one");
  const lines = [];
  for (const [interval, want] of Object.entries(WANT)) {
    const m = prices.filter((p) => p.recurring && p.recurring.interval === interval && p.recurring.interval_count === 1);
    if (m.length !== 1) { good = false; console.log(`  ✗ ${m.length} active prices billed every ${interval}; expected one`); continue; }
    const p = m[0];
    if (p.currency !== "usd" || p.unit_amount !== want.amount) {
      good = false;
      console.log(`  ✗ ${p.id} is ${money(p)}; the handoff says ${(want.amount / 100).toFixed(2)} USD`);
    }
    lines.push(`${want.env}=${p.id}`);
  }
  if (lines.length) console.log("\nSet in Vercel → Settings → Environment Variables (" + (mode === "test" ? "Preview" : "Production, after the gates") + "):\n" + lines.join("\n"));
  process.exit(good ? 0 : 1);
})().catch((e) => { console.error("Stripe refused: " + e.message + (e.code ? " (" + e.code + ")" : "")); process.exit(1); });
