"use strict";
/* The weekly question digest, run by hand (the Vercel cron at /api/digest does the same each Monday).

     node web/faq_digest.js                  # last complete ISO week
     node web/faq_digest.js --week 2026-W39  # any week whose conversations are still inside their 30 days

   Needs KV_REST_API_URL and KV_REST_API_TOKEN (vercel env pull). Keeps digest:<week> in the store with no expiry and
   writes business/faq_digest/<week>.json, which is gitignored: counts only, never committed, never published. */
const fs = require("fs"), path = require("path");
const D = require("./lib/faq_digest.js");
const args = process.argv.slice(2), i = args.indexOf("--week");
const week = i >= 0 ? args[i + 1] : D.lastWeek(new Date());
const url = process.env.KV_REST_API_URL || process.env.UPSTASH_REDIS_REST_URL, token = process.env.KV_REST_API_TOKEN || process.env.UPSTASH_REDIS_REST_TOKEN;
if (!url || !token) { console.log("set KV_REST_API_URL and KV_REST_API_TOKEN (vercel env pull)"); process.exit(2); }
D.weekRange(week);
D.run(D.upstash(url, token), week, new Date()).then((d) => {
  const dir = path.join(__dirname, "..", "business", "faq_digest");
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, week + ".json"), JSON.stringify(d, null, 1) + "\n");
  console.log(`${week}: ${d.conversations} conversations, ${d.messages} messages -> digest:${week} and business/faq_digest/${week}.json`);
  for (const [k, n] of Object.entries(d.topics).slice(0, 10)) console.log(String(n).padStart(4) + "  " + k);
}).catch((e) => { console.log("failed: " + e.message); process.exit(1); });
