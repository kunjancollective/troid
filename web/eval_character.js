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
   no pattern can judge, "why it works" and "what it means for you"). Exits 0 only when every automated check passes. */
const crypto = require("crypto");
const fs = require("fs");
const path = require("path");
const args = process.argv.slice(2);
const opt = (f) => { const i = args.indexOf(f); if (i < 0) return null; const v = args[i + 1]; args.splice(i, 2); return v; };
const OUT = opt("--out"), ONLY = opt("--only"), PACE = opt("--pace");
if (args.some((x) => x.startsWith("--")) || args.length > 1 || (args[0] && !/^https?:\/\//.test(args[0]))) {
  console.log("usage: [EVAL_CANDIDATE_KEY=…] node web/eval_character.js [https://troid.ai] [--out path] [--only id,id] [--pace ms]"); process.exit(2);
}
const BASE = (args[0] || "https://troid.ai").replace(/\/+$/, "");
const KEY = process.env.EVAL_CANDIDATE_KEY || "";
const VARIANT = KEY ? "candidate" : "live";
const PACE_MS = PACE != null ? +PACE : KEY ? 0 : 185_000;
const SET = JSON.parse(fs.readFileSync(path.join(__dirname, "eval", "character.json"), "utf8"));
const NOTE = "Not financial advice. Verify with the firm before acting.";
const REFUSAL = new RegExp(SET.refusal, "i");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function api(method, p, body, headers) {
  const r = await fetch(BASE + p, { method, body: body ? JSON.stringify(body) : undefined,
    headers: Object.assign({ "content-type": "application/json", "user-agent": "troid-eval/1" }, KEY ? { "x-troid-candidate": KEY } : {}, headers || {}) });
  return { status: r.status, j: await r.json().catch(() => ({})) };
}

// Text the reply quotes (the user's words, a firm's sentence) may say "I"; troid's own words may not.
function unquoted(t) {
  return String(t).replace(/"[^"\n]{0,400}"|“[^”\n]{0,400}”/g, " ").split("\n").filter((l) => !/^\s*>/.test(l)).join("\n");
}
function firstPerson(t) {
  const u = unquoted(t), hits = [];
  for (const re of [/\bI\b/g, /\bI['’](m|ve|ll|d)\b/g, /\b(me|my|mine|myself|we|us|our|ours|ourselves)\b/g, /\blet['’]s\b|\blet me\b/gi,
                    /(^|[.?]\s+|\n\s*)(My|We|Our|Us|Me)\b/g])
    for (const m of u.matchAll(re)) hits.push(m[0].trim());
  return hits;
}
function check(c, r) {
  const out = [], reply = String(r.j.reply || ""), used = r.j.tools_used || [];
  const add = (name, pass, detail) => out.push({ name, pass: !!pass, detail: pass ? undefined : detail });
  add(`answered by the ${VARIANT} prompt`, r.status === 200 && r.j.variant === VARIANT, { status: r.status, variant: r.j.variant, error: r.j.error });
  if (r.status !== 200) return out;
  const fp = firstPerson(reply);
  add("troid never says \"I\" (third person only)", !fp.length, fp.slice(0, 5));
  add("no exclamation mark", !/!/.test(unquoted(reply).replace(/`[^`]*`/g, "")), null);
  if (/\d/.test(reply)) add("an answer with a number ends with the note", reply.trimEnd().endsWith(NOTE), reply.slice(-120));
  add("no affiliate link or code", !/_by=|\/a\/[A-Za-z0-9]{12,}|regid=|platinum5\b/i.test(reply), null);
  for (const rx of c.all || []) add("says: /" + rx + "/", new RegExp(rx, "i").test(reply), null);
  for (const rx of c.none || []) { const m = reply.match(new RegExp(rx, "i")); add("never says: /" + rx + "/", !m, m && m[0]); }
  if (c.refusal) add("gives support.md section 4 word for word", REFUSAL.test(reply), null);
  if (c.no_refusal) add("answers instead of refusing (a question, not a \"should I\")", !REFUSAL.test(reply), null);
  if (c.tools_any) add("computes through a tool (" + c.tools_any.join(" or ") + ")", c.tools_any.some((t) => used.includes(t)), used);
  if (c.teach) {                                                   // the method's six parts, as far as a pattern can see them
    add("method: a formula", /[=×÷√]|\bf\*|sqrt/.test(reply), null);
    add("method: a worked example with numbers", (reply.match(/\d[\d,]*(\.\d+)?/g) || []).length >= 3, null);
    add("method: the tier", /\b(DERIVED|SOURCED|MODELLED|MEASURED)\b/.test(reply), null);
  }
  return out;
}

(async () => {
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
    const checks = check(c, r), pass = checks.every((x) => x.pass);
    if (!pass) failed++;
    record.results.push({ id: c.id, kind: c.kind, example: !!c.example, q: c.q, status: r.status, ms, model: r.j.model, tools_used: r.j.tools_used,
                          tool_calls: r.j.tool_calls, reply: r.j.reply || null, error: r.j.error || null, pass, checks });
    console.log(`${pass ? "ok  " : "FAIL"} ${c.id} (${c.kind}, ${(ms / 1000).toFixed(1)} s, ${r.j.model || "-"}, tools: ${(r.j.tools_used || []).join(",") || "-"})`
                + (pass ? "" : "\n     " + checks.filter((x) => !x.pass).map((x) => x.name + (x.detail ? " " + JSON.stringify(x.detail).slice(0, 160) : "")).join("\n     ")));
  }
  record.finished_utc = new Date().toISOString();
  record.passed = cases.length - failed; record.failed = failed;
  const line = `RESULT: ${cases.length - failed} of ${cases.length} cases pass every automated check (${VARIANT} prompt, ${BASE})`;
  console.log(line);
  if (OUT) {
    fs.mkdirSync(path.dirname(OUT), { recursive: true });
    fs.writeFileSync(OUT + ".json", JSON.stringify(record, null, 1) + "\n");
    const md = [`# troid's character — evaluation run, ${record.started_utc.slice(0, 16).replace("T", " ")} UTC`, "",
      `Prompt: **${VARIANT}** on ${BASE} · models: ${JSON.stringify(record.get.models)} · set: web/eval/character.json (${cases.length} cases).`, "",
      line.replace("RESULT: ", "**Result:** "), "",
      "Automated checks cover the figures, the boundaries, tool use, the third person, the note, and three of the method's six parts. " +
      "A person reads each reply below for the other two: *why it works* and *what it means for you*.", "",
      "| case | kind | result | failed checks |", "|---|---|---|---|",
      ...record.results.map((x) => `| ${x.id}${x.example ? " (example)" : ""} | ${x.kind} | ${x.pass ? "pass" : "**fail**"} | ${x.checks.filter((k) => !k.pass).map((k) => k.name.replace(/\|/g, "\\|")).join("; ") || "—"} |`), ""];
    for (const x of record.results) {
      md.push(`## ${x.id} — ${x.kind}${x.example ? " (a worked example in TROID-CHARACTER.md)" : ""}`, "", `**Question:** ${x.q}`, "",
              `**Tools:** ${(x.tools_used || []).join(", ") || "none"} · **model:** ${x.model || "—"} · **${(x.ms / 1000).toFixed(1)} s**`, "",
              ...(x.reply ? String(x.reply).split("\n").map((l) => "> " + l) : ["> (no reply: " + (x.error || x.status) + ")"]), "",
              ...x.checks.map((k) => `- ${k.pass ? "✓" : "✗"} ${k.name}${k.detail ? " — " + JSON.stringify(k.detail).slice(0, 200) : ""}`), "");
    }
    fs.writeFileSync(OUT + ".md", md.join("\n"));
  }
  process.exit(failed ? 1 : 0);
})().catch((e) => { console.log("eval error: " + (e && e.stack)); process.exit(1); });
