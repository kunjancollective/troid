"use strict";
/* troid's character, evaluated against the live model (TROID-CHARACTER.md, "Where this plugs in"). Each case in
   web/eval/character.json goes to ask troid as a fresh one-message conversation, and the reply is checked.

   With EVAL_CANDIDATE_KEY set (the value of TROID_CANDIDATE_KEY on the deployment) it evaluates the candidate prompt,
   the change staged in web/context/candidate/, which only these requests get: that is how a prompt change runs against
   the live model before it reaches anyone. Candidate conversations are not stored and not held to a visitor's limit.
   Without the key it evaluates the live prompt: one case every 185 seconds, under a visitor's 20 messages an hour,
   deleting each conversation once its reply is read.

     EVAL_CANDIDATE_KEY=… node web/eval_character.js https://troid.ai --out web/eval/runs/2026-09-24-candidate
     node web/eval_character.js https://troid.ai --only ex-kelly,q-stats --out /tmp/live

   Writes <out>.json (every reply and check) and <out>.md (the report: a person reads it for the two parts of the method
   no pattern can judge, "why it works" and "what it means for you"). Exits 0 only when every automated check passes.

   A saved run's report can be written again, with what a person found reading it, and checked again under the current
   cases (a check added after a run shows what that run would have failed):
     node web/eval_character.js --report web/eval/runs/X.json [--read web/eval/runs/X.read.json] [--recheck] */
const crypto = require("crypto");
const fs = require("fs");
const path = require("path");
const args = process.argv.slice(2);
const opt = (f) => { const i = args.indexOf(f); if (i < 0) return null; const v = args[i + 1]; args.splice(i, 2); return v; };
const flag = (f) => { const i = args.indexOf(f); if (i < 0) return false; args.splice(i, 1); return true; };
const OUT = opt("--out"), ONLY = opt("--only"), PACE = opt("--pace"), REPORT = opt("--report"), READ = opt("--read"), RECHECK = flag("--recheck");
if (args.some((x) => x.startsWith("--")) || args.length > 1 || (args[0] && !/^https?:\/\//.test(args[0]))) {
  console.log("usage: [EVAL_CANDIDATE_KEY=…] node web/eval_character.js [https://troid.ai] [--out path] [--only id,id] [--pace ms]\n" +
              "       node web/eval_character.js --report run.json [--read notes.json] [--recheck] [--out path]"); process.exit(2);
}
const BASE = (args[0] || "https://troid.ai").replace(/\/+$/, "");
const KEY = process.env.EVAL_CANDIDATE_KEY || "";
const PACE_MS = PACE != null ? +PACE : KEY ? 0 : 185_000;
const SET = JSON.parse(fs.readFileSync(path.join(__dirname, "eval", "character.json"), "utf8"));
const NOTE = "Not financial advice. Verify with the firm before acting.";
const REFUSAL = new RegExp(SET.refusal, "i");
// A figure, as the service tests for one: a number standing on its own (4%, $4,000, 16:00), not a digit inside a name
// (1step, 2step_s1, 1R, 1-Step, Stage 2).
const FIGURE = /(?<![\p{L}\p{N}_.])\d[\d,]*(?:\.\d+)?(?![\p{L}\p{N}_])/u;
const hasFigure = (t) => FIGURE.test(String(t).replace(/\b\d-(step|phase)\b|\bstage \d\b/gi, " ").replace(/^\s*\d+[.)]\s/gm, " "));
// Judging the user's numbers instead of stating what they imply (run 1: "which is solid", "where prop-firm traders belong").
const JUDGE = /\b(solid|healthy|great|excellent|impressive|amazing|fantastic|awesome)\b|where [^.\n]{0,40}\bbelong\b|nowhere to hide/i;
// A read date beside a rule: "read 2026-09-23", "read 23 Sep 2026", "read on 21 September 2026".
const READ_DATE = /\bread (on )?(\d{4}-\d{2}-\d{2}|\d{1,2} [A-Z][a-z]{2,8} \d{4}|[A-Z][a-z]{2,8} \d{1,2},? \d{4})/;
// A firm's rule stated as a percentage: a firm named and a percentage in the same sentence (TROID-CHARACTER.md: "troid
// states the date every time"; run 2, ex-recovery gave Bitfunded's 10% without one).
const FIRM_PCT = /\b(Bitfunded|BrightFunded|Crypto Fund Trader)\b[^.\n]{0,80}?\d+(\.\d+)?\s?%|\d+(\.\d+)?\s?%[^.\n]{0,60}?\b(Bitfunded|BrightFunded|Crypto Fund Trader)\b/;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
// A firm's rule stated as a time or a number of days (run 4, e-blown: Bitfunded's reset "between 16:00 and 16:10 UTC"
// with no read date).
const FIRMS = "Bitfunded|BrightFunded|Crypto Fund Trader", RULE_FIG = "\\b\\d{1,2}:\\d{2}\\b|\\b\\d+\\s?(trading )?days?\\b";
const FIRM_RULE = new RegExp(`\\b(${FIRMS})\\b[^.\\n]{0,80}?(${RULE_FIG})|(${RULE_FIG})[^.\\n]{0,60}?\\b(${FIRMS})\\b`);
// troid taking the trade (run 4, b-stop: "the dollar amount troid is willing to put on the trade"). troid never trades.
const AGENCY = /\btroid (is willing to|wants to|will|would|is going to|plans to|can afford to) (put|risk|open|place|enter)\b[^.\n]{0,30}\b(on|into|in) (the |a |this )?(trade|position|market)\b|\btroid (is willing to|wants to|is going to|plans to) (take|risk|lose)\b/i;
// Arithmetic written out must hold. Every "numbers-only expression = number" (or ≈) in a reply is worked again (run 4,
// q-stats: "0.0453 × 3.28 ≈ 0.1181", where √(2 ln 30) is 2.61). A word, a symbol it doesn't read, or a ± ends an expression;
// a result is allowed the rounding its own decimals show, or half a percent.
function arithTokens(s) {
  const out = [];
  for (let i = 0; i < s.length;) {
    const rest = s.slice(i), c = s[i], prev = out[out.length - 1];
    if (/\s/.test(c)) { i++; continue; }
    let m = /^\$?(\d+(?:\.\d+)?)(\s?%)?(R\b|×(?!\s*[\d($√−-]))?/.exec(rest);
    if (m) { out.push({ t: "n", v: +m[1] * (m[2] ? 0.01 : 1), pct: !!m[2], dec: (m[1].split(".")[1] || "").length, s: m[0] }); i += m[0].length; continue; }
    const unary = !prev || prev.t === "op" || prev.t === "(";
    if ("×*÷/+−".includes(c) || (c === "-" && ((/^-\s/.test(rest) && /\s$/.test(s.slice(0, i))) || (unary && /^-\d/.test(rest))))
        || (c === "x" && /^x\s/.test(rest) && /\s$/.test(s.slice(0, i)))) {
      out.push({ t: "op", v: c === "*" || c === "x" ? "×" : c === "/" ? "÷" : c === "-" ? "−" : c, s: c }); i++; continue;
    }
    if (c === "(" || c === ")" || c === "√") { out.push({ t: c, s: c }); i++; continue; }
    out.push({ t: "?", s: c }); i++;
  }
  return out;
}
function arithParse(ts) {                        // the value of ts if it is exactly one expression, with its operator count
  let i = 0, ops = 0;
  const at = (t, v) => ts[i] && ts[i].t === t && (v == null || v.includes(ts[i].v));
  const factor = () => {
    if (at("op", "−")) { i++; const w = factor(); return w == null ? null : -w; }
    if (at("√")) { i++; ops++; const w = factor(); return w == null || w < 0 ? null : Math.sqrt(w); }
    if (at("n")) return ts[i++].v;
    if (at("(")) { i++; const w = expr(); if (w == null || !at(")")) return null; i++; return w; }
    return null;
  };
  const term = () => { let v = factor(); while (v != null && at("op", "×÷")) { const o = ts[i++].v, w = factor(); ops++; v = w == null ? null : o === "×" ? v * w : v / w; } return v; };
  const expr = () => { let v = term(); while (v != null && at("op", "+−")) { const o = ts[i++].v, w = term(); ops++; v = w == null ? null : o === "+" ? v + w : v - w; } return v; };
  const v = expr();
  return v == null || !isFinite(v) || i !== ts.length ? null : { v, ops, single: ts.length === 1 ? ts[0] : null, s: ts.map((t) => t.s).join(" ") };
}
const MATHY = /[±^²³·|≤≥<>√]/;                    // a symbol just outside an expression means it was only part of one
function arithSides(left, right) {
  const a = arithTokens(left), b = arithTokens(right);
  let k = a.length; while (k > 0 && a[k - 1].t !== "?") k--;
  let e = 0; while (e < b.length && b[e].t !== "?") e++;
  if ((k > 0 && MATHY.test(a[k - 1].s)) || (e < b.length && MATHY.test(b[e].s))) return null;
  // the whole run of numbers beside the "=", never a piece of a longer one ("quota×4%" is not "4%")
  const L = k < a.length ? arithParse(a.slice(k)) : null, R = e > 0 ? arithParse(b.slice(0, e)) : null;
  return L && R && L.ops ? [L, R] : null;         // "1R = 1,292 × 0.3862" defines a unit; the worked side comes first
}
function arithHolds(L, R, approx) {
  if (L.single && !R.single) [L, R] = [R, L];     // the single number carries the rounding
  const n = R.single, rel = approx ? 0.01 : 0.005;
  const cands = n && n.pct ? [[R.v, n.dec + 2], [R.v * 100, n.dec]] : [[R.v, n ? n.dec : 6]];   // 25% may be 0.25 or 25 on the other side
  return cands.some(([r, d]) => Math.abs(L.v - r) <= Math.max(0.5 * 10 ** -d, Math.abs(r) * rel) + 1e-12);
}
function arithmeticSlips(text) {
  const t = unquoted(text).replace(/\*\*|__|`/g, "").replace(/(\d),(?=\d{3}(?!\d))/g, "$1"), slips = [];
  for (const line of t.split("\n")) {
    const parts = line.split(/\s(=|≈)\s/);
    for (let i = 0; i + 2 < parts.length; i += 2) {
      const lr = arithSides(parts[i], parts[i + 2]);
      if (lr && !arithHolds(lr[0], lr[1], parts[i + 1] === "≈")) slips.push(`${lr[0].s} ${parts[i + 1]} ${lr[1].s} (it is ${+lr[0].v.toPrecision(5)})`);
    }
  }
  return slips;
}

async function api(method, p, body, headers) {
  const r = await fetch(BASE + p, { method, body: body ? JSON.stringify(body) : undefined,
    headers: Object.assign({ "content-type": "application/json", "user-agent": "troid-eval/1" }, KEY ? { "x-troid-candidate": KEY } : {}, headers || {}) });
  return { status: r.status, j: await r.json().catch(() => ({})) };
}

// Text the reply quotes (the user's words, a firm's sentence) may say "I"; troid's own words may not. Nor is the
// sources block the service writes troid's words: a document's title can say "my" (run 2: BrightFunded's "How does my
// daily permitted loss work").
function unquoted(t) {
  return String(t).replace(/^Sources, each with the date troid read it:\n(- .*(\n|$))*/m, "")
    .replace(/"[^"\n]{0,400}"|“[^”\n]{0,400}”/g, " ").split("\n").filter((l) => !/^\s*>/.test(l)).join("\n");
}
function firstPerson(t) {
  const u = unquoted(t), hits = [];
  for (const re of [/\bI\b/g, /\bI['’](m|ve|ll|d)\b/g, /\b(me|my|mine|myself|we|us|our|ours|ourselves)\b/g, /\blet['’]s\b|\blet me\b/gi,
                    /(^|[.?]\s+|\n\s*)(My|We|Our|Us|Me)\b/g])
    for (const m of u.matchAll(re)) hits.push(m[0].trim());
  return hits;
}
// r: { status, j: { reply, variant, tools_used } } — a live response, or one rebuilt from a saved run
function check(c, r, variant) {
  const out = [], reply = String(r.j.reply || ""), used = r.j.tools_used || [];
  const add = (name, pass, detail) => out.push({ name, pass: !!pass, detail: pass ? undefined : detail });
  add(`answered by the ${variant} prompt`, r.status === 200 && r.j.variant === variant, { status: r.status, variant: r.j.variant, error: r.j.error });
  if (r.status !== 200) return out;
  const fp = firstPerson(reply);
  add("troid never says \"I\" (third person only)", !fp.length, fp.slice(0, 5));
  add("troid stays lowercase", !/\bTroid\b/.test(reply), null);
  add("no exclamation mark", !/!/.test(unquoted(reply).replace(/`[^`]*`/g, "")), null);
  { const m = unquoted(reply).match(JUDGE); add("states what the numbers imply, never whether they are good (no \"solid\", \"where traders belong\")", !m, m && m[0]); }
  if (hasFigure(reply)) add("an answer with a figure ends with the note", reply.trimEnd().endsWith(NOTE), reply.slice(-120));
  add("no affiliate link or code", !/_by=|\/a\/[A-Za-z0-9]{12,}|regid=|platinum5\b/i.test(reply), null);
  if (FIRM_PCT.test(reply) || FIRM_RULE.test(reply)) add("a firm's rule it states carries the date troid read it", READ_DATE.test(reply), (reply.match(FIRM_PCT) || reply.match(FIRM_RULE) || [])[0]);
  { const slips = arithmeticSlips(reply); add("the arithmetic it writes out holds", !slips.length, slips); }                      // run 4
  add("prints its tier once", (reply.match(/(^|\s)(\*\*|__)?Tier(\*\*|__)?:/g) || []).length <= 1, null);                    // run 4
  { const m = reply.match(AGENCY); add("troid never trades: the risk and the trade are the trader's", !m, m && m[0]); }             // run 4
  { const m = reply.match(/\b(Bitfunded|BrightFunded|Crypto Fund Trader)['’]s (own )?(check_budget|size_trade|explain_rule|trade_math|firm_rules|default)\b/);   // run 3
    add("troid's tools and defaults are troid's, not a firm's", !m, m && m[0]); }
  for (const rx of c.all || []) add("says: /" + rx + "/", new RegExp(rx, "i").test(reply), null);
  for (const rx of c.none || []) { const m = reply.match(new RegExp(rx, "i")); add("never says: /" + rx + "/", !m, m && m[0]); }
  if (c.refusal) add("gives support.md section 4 word for word", REFUSAL.test(reply), null);
  if (c.no_refusal) add("answers instead of refusing (a question, not a \"should I\")", !REFUSAL.test(reply), null);
  if (c.tools_any) add("computes through a tool (" + c.tools_any.join(" or ") + ")", c.tools_any.some((t) => used.includes(t)), used);
  if (c.sourced) add("each rule it states carries its document and read date", READ_DATE.test(reply), null);
  if (c.teach) {                                                   // the method's six parts, as far as a pattern can see them
    add("method: a formula", /[=×÷√]|\bf\*|sqrt/.test(reply), null);
    add("method: a worked example with numbers", (reply.match(/\d[\d,]*(\.\d+)?/g) || []).length >= 3, null);
    add("method: the tier", /\b(DERIVED|SOURCED|MODELLED|MEASURED)\b/.test(reply), null);
  }
  return out;
}

function writeReport(record, out, notes) {
  const n = record.results.length, failed = record.results.filter((x) => !x.pass).length;
  const passedThen = record.rechecked && record.passed != null ? record.passed : n - failed;
  const line = `RESULT: ${passedThen} of ${n} cases pass every automated check (${record.variant} prompt, ${record.base})`;
  const read = notes || {};
  const md = [`# troid's character — evaluation run, ${record.started_utc.slice(0, 16).replace("T", " ")} UTC`, "",
    `Prompt: **${record.variant}** on ${record.base} · models: ${JSON.stringify(record.get.models)} · set: web/eval/character.json (${n} cases).`, "",
    line.replace("RESULT: ", "**Result:** "), "",
    ...(record.rechecked ? [`**Checked again** on ${record.rechecked.slice(0, 10)} under the case set as it is now: ${n - failed} of ${n} pass. ` +
        "The replies are the run's own; a check added after the run shows what the run would have failed. The table and the checks below are the new ones.", ""] : []),
    ...(read._summary ? ["**Read by a person:** " + read._summary, ""] : []),
    "Automated checks cover the figures, the calculations written out, the boundaries, tool use, the third person, the note, sources on rules, and three of the method's six parts. " +
    "A person reads each reply below for the other two: *why it works* and *what it means for you*.", "",
    "| case | kind | result | failed checks |" + (notes ? " read by a person |" : ""), "|---|---|---|---|" + (notes ? "---|" : ""),
    ...record.results.map((x) => `| ${x.id}${x.example ? " (example)" : ""} | ${x.kind} | ${x.pass ? "pass" : "**fail**"} | ${x.checks.filter((k) => !k.pass).map((k) => k.name.replace(/\|/g, "\\|")).join("; ") || "—"} |`
      + (notes ? ` ${read[x.id] ? (/^error\b/i.test(read[x.id]) ? "**error**" : "note") : "—"} |` : "")), ""];
  for (const x of record.results) {
    md.push(`## ${x.id} — ${x.kind}${x.example ? " (a worked example in TROID-CHARACTER.md)" : ""}`, "", `**Question:** ${x.q}`, "",
            `**Tools:** ${(x.tools_used || []).join(", ") || "none"} · **model:** ${x.model || "—"} · **${(x.ms / 1000).toFixed(1)} s**`, "",
            ...(x.reply ? String(x.reply).split("\n").map((l) => "> " + l) : ["> (no reply: " + (x.error || x.status) + ")"]), "",
            ...x.checks.map((k) => `- ${k.pass ? "✓" : "✗"} ${k.name}${k.detail ? " — " + JSON.stringify(k.detail).slice(0, 200) : ""}`), "",
            ...(read[x.id] ? ["**Read by a person:** " + read[x.id], ""] : []));
  }
  fs.mkdirSync(path.dirname(out), { recursive: true });
  fs.writeFileSync(out + ".md", md.join("\n"));
  return line;
}

if (REPORT) {                                                      // a saved run: its report, again
  const record = JSON.parse(fs.readFileSync(REPORT, "utf8"));
  if (RECHECK) {
    const byId = Object.fromEntries(SET.cases.map((c) => [c.id, c]));
    for (const x of record.results) {
      if (!byId[x.id]) continue;
      x.checks = check(byId[x.id], { status: x.status, j: { reply: x.reply, variant: record.variant, tools_used: x.tools_used, error: x.error } }, record.variant);
      x.pass = x.checks.every((k) => k.pass);
    }
    record.rechecked = new Date().toISOString();
  }
  const out = OUT || REPORT.replace(/\.json$/, "");
  console.log(writeReport(record, out, READ ? JSON.parse(fs.readFileSync(READ, "utf8")) : null)
              + (RECHECK ? ` · checked again: ${record.results.filter((x) => x.pass).length} of ${record.results.length}` : ""));
  process.exit(0);
}

(async () => {
  const VARIANT = KEY ? "candidate" : "live";
  const cases = SET.cases.filter((c) => !ONLY || ONLY.split(",").includes(c.id));
  const g = await api("GET", "/api/troid");
  const record = { base: BASE, variant: VARIANT, started_utc: new Date().toISOString(), get: { enabled: g.j.enabled, models: g.j.models, candidate: g.j.candidate },
                   set: { cases: cases.length, kinds: SET.kinds }, results: [] };
  if (!g.j.enabled) { console.log("ask troid is not on at " + BASE); process.exit(1); }
  if (KEY && !(g.j.candidate && g.j.candidate.key && g.j.candidate.staged.length)) { console.log("no candidate staged, or no candidate key set, at " + BASE, g.j.candidate); process.exit(1); }
  let failed = 0;
  for (let i = 0; i < cases.length; i++) {
    const c = cases[i], session = crypto.randomBytes(16).toString("hex");
    if (i && PACE_MS) await sleep(PACE_MS);
    const t0 = Date.now();
    let r = await api("POST", "/api/troid", { messages: [{ role: "user", content: c.q }], session, disclosed: true, lang: "en" });
    if ([502, 503, 504].includes(r.status)) { await sleep(20_000); r = await api("POST", "/api/troid", { messages: [{ role: "user", content: c.q }], session: crypto.randomBytes(16).toString("hex"), disclosed: true, lang: "en" }); }
    const ms = Date.now() - t0;
    if (VARIANT === "live" && r.j.delete_token) await api("DELETE", "/api/troid?session=" + (r.j.session || session), null, { "x-troid-token": r.j.delete_token });
    const checks = check(c, r, VARIANT), pass = checks.every((x) => x.pass);
    if (!pass) failed++;
    record.results.push({ id: c.id, kind: c.kind, example: !!c.example, q: c.q, status: r.status, ms, model: r.j.model, tools_used: r.j.tools_used,
                          tool_calls: r.j.tool_calls, reply: r.j.reply || null, error: r.j.error || null, pass, checks });
    console.log(`${pass ? "ok  " : "FAIL"} ${c.id} (${c.kind}, ${(ms / 1000).toFixed(1)} s, ${r.j.model || "-"}, tools: ${(r.j.tools_used || []).join(",") || "-"})`
                + (pass ? "" : "\n     " + checks.filter((x) => !x.pass).map((x) => x.name + (x.detail ? " " + JSON.stringify(x.detail).slice(0, 160) : "")).join("\n     ")));
  }
  record.finished_utc = new Date().toISOString();
  record.passed = cases.length - failed; record.failed = failed;
  if (OUT) {
    fs.mkdirSync(path.dirname(OUT), { recursive: true });
    fs.writeFileSync(OUT + ".json", JSON.stringify(record, null, 1) + "\n");
    console.log(writeReport(record, OUT, null));
  } else console.log(`RESULT: ${cases.length - failed} of ${cases.length} cases pass every automated check (${VARIANT} prompt, ${BASE})`);
  process.exit(failed ? 1 : 0);
})().catch((e) => { console.log("eval error: " + (e && e.stack)); process.exit(1); });
