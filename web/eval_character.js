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
const READ_DATE = /\bread (on )?(\d{4}[-\u2010\u2011]\d{2}[-\u2010\u2011]\d{2}|\d{1,2} [A-Z][a-z]{2,8} \d{4}|[A-Z][a-z]{2,8} \d{1,2},? \d{4})/;
// A firm's rule stated as a percentage: a firm named and a percentage in the same sentence (TROID-CHARACTER.md: "troid
// states the date every time"; run 2, ex-recovery gave Bitfunded's 10% without one).
const FIRM_PCT = /\b(Bitfunded|BrightFunded|Crypto Fund Trader)\b[^.\n]{0,80}?\d+(\.\d+)?\s?%|\d+(\.\d+)?\s?%[^.\n]{0,60}?\b(Bitfunded|BrightFunded|Crypto Fund Trader)\b/;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
// A firm's rule stated as a time or a number of days (run 4, e-blown: Bitfunded's reset "between 16:00 and 16:10 UTC"
// with no read date).
const FIRMS = "Bitfunded|BrightFunded|Crypto Fund Trader", RULE_FIG = "\\b\\d{1,2}:\\d{2}\\b|\\b\\d+\\s?(trading )?days?\\b";
const FIRM_RULE = new RegExp(`\\b(${FIRMS})\\b[^.\\n]{0,80}?(${RULE_FIG})|(${RULE_FIG})[^.\\n]{0,60}?\\b(${FIRMS})\\b`);
// ...or as a fee (run 5, s-firm: "Bitfunded's 1-Step at $999"), or as "the largest maximum loss troid has read" (run 5, ex-recovery).
const MONEY = "(\\$|€|USD\\s?|EUR\\s?)\\d[\\d,]*(\\.\\d+)?|\\d[\\d,]*(\\.\\d+)?\\s?(USD|EUR)\\b";
const FIRM_FEE = new RegExp(`\\b(${FIRMS})\\b[^.\\n]{0,80}?(${MONEY})|(${MONEY})[^.\\n]{0,60}?\\b(${FIRMS})\\b`);
const TROID_READ_PCT = /troid has read[^.\n]{0,80}?\d+(\.\d+)?\s?%|\d+(\.\d+)?\s?%[^.\n]{0,80}?troid has read/;
// A tool's parameters in a reply (run 5: ex-recovery 'firm "all"', b-stop "stop_pct").
const TOOL_PARAM = /\bfirm ["“]all["”]|\btopic:\s*\w+|\bstop_pct\b|\bcalc\s*[:=]|\bdrawdown_pct\b|\bwin_rate_pct\b|`(kelly|position_size|r_multiple|expectancy|recovery|fee_share|losses_to_limit|capped_budget|stats|atr_scale|effective_bets)`/;   // run 13: "`kelly`"
// A rule that differs by product stated as the whole firm's (run 7, b-limits: "Crypto Fund Trader's trail the high-water
// mark"; its 1-Phase trails, its 2-Phase is static; the service's own source line had said "trailing on balance").
const PH1 = "(1-Phase|1 Phase|one-phase|1phase)";
const BY_PRODUCT = new RegExp(`(?<!${PH1}\\b[^.\\n]{0,40})(Crypto Fund Trader|\\bCFT)\\b(?![^.\\n]{0,80}\\b${PH1}\\b)[^.\\n]{0,60}\\btrail` +
  `|(?<!${PH1}\\b[^.\\n]{0,40})\\btrail[^.\\n]{0,40}\\b(Crypto Fund Trader|CFT)\\b(?![^.\\n]{0,30}\\b${PH1}\\b)`, "i");
// troid's own instructions named, or the reply's form announced, in a reply (run 8: "support.md section 4 applies here",
// "Result first, one line:"; run 6: "troid's fixed answer").
const INTERNAL = /\bsupport\.md\b|\bTROID-CHARACTER\b|\bcharacter section\b|\bfixed (answer|reply|refusal)\b|\b(result|answer),? (first,? )?(in )?one line\b|\bin one line:|\bretract(ing|ed|s)?\b|\b(earlier|previous|prior) (version|draft) of (this|the) answer\b|\b(result|answer)s? first\b|\bone[- ]line answer\b|\b(getting|fetching|pulling|computing|running) (those|that|them|it|the numbers) now\b/i;   // run 15: "Getting those now:"   // run 13: "Result first:", "One-line answer:"   // run 11: "Answer, one line:"; run 12: "Retracting the earlier version of this answer"
// troid's own in-sample figure before its out-of-sample one (run 8, q-stats; CLAUDE.md: out of sample first).
const OOS_LATE = /^(?:(?!0\.008\s?R)[\s\S])*\btroid['’]s own\b[^.\n]{0,60}\b(in[- ]sample|search|best of)/i;
// A firm's floating-loss rule with no source line for it (run 10, b-limits: "Bitfunded auto-fails on either without requiring
// a close"; troid had read it and recorded it nowhere).
const FLOAT_RULE = new RegExp(`\\b(${FIRMS})\\b[^.\\n]{0,120}\\bfloat|\\bfloat[^.\\n]{0,120}\\b(${FIRMS})\\b`, "i");
const FLOAT_SOURCED = /^- [^\n]*\bfloat[^\n]*(\bread (on )?\d|source not yet recorded)/im;
// Every rule called sourced where a source line says one isn't (run 10, s-product: "all SOURCED with their read dates" over a
// split and a 2-Step trading fee whose sources are not yet recorded).
const ALL_SOURCED = /\ball (of them |the rules |rules )?(are |is )?(SOURCED|sourced|dated)\b|\b(all|every) (rules?|figures?)\b[^.\n]{0,40}\b(with|carr(y|ies)) (its|their) (sources?|read dates?)\b|\ball\b[^.\n]{0,20}\bwith their read dates\b/;
// troid's published Monte Carlo with a figure beside the wrong risk (run 10, o-montecarlo: "2% fixed risk with a 68% simulated
// failure rate"; 68% is at 1% a trade, 100% at 2%).
const RUIN_MIX = /\b2(\.0)?\s?%[^.\n;,]{0,50}\b68\s?%|\b68\s?%[^.\n;]{0,30}\bat 2\s?%|\b1(\.0)?\s?%[^.\n;,]{0,50}\b100\s?%\s?(of|blow|fail|ruin)/i;
// A worked example on a firm's product at leverage above its cap, the cap unsaid (run 10, b-leverage: 10x "on a Bitfunded
// 1-Step account"; run 6: on the reference account). A paragraph naming Bitfunded, leverage above 5x, and no cap.
function levOverCap(t) {
  for (const para of unquoted(t).split(/\n\s*\n/)) {
    if (!/\bBitfunded\b/.test(para) || !/leverage/i.test(para)) continue;
    if (/1:5\b|\bcap(s|ped)?\b[^.\n]{0,30}\b5\s?[×x]|\b5\s?[×x][^.\n]{0,20}\bcap/i.test(para)) continue;
    const m = para.match(/(?<![\d.,])(?:[6-9]|[1-9]\d{1,2})\s?[×x](?![\w])(?!\s*[\d(])/);   // a leverage, not a product (77,872 × 0.04%)
    if (m) return m[0];
  }
  return null;
}
// A firm's rule as a percentage that the service's sources don't list (run 11, ex-r: "Bitfunded's 4% daily limit" under a
// sources block holding only the fee; before, any read date anywhere in the reply passed it). A percentage the user gave
// is theirs, not a rule.
const LINT_FIRM = /\b(Bitfunded|BrightFunded|Crypto Fund Trader|CFT)\b/;
const LINT_WORD = "(daily|max(?:imum)?|loss|limit|target|drawdown|fee|split|floor)";
const PCT_AFTER = new RegExp(`(?<![\\d.,])(\\d+(?:\\.\\d+)?)\\s?%\\s?(?:[\\w'’()-]+\\s){0,3}?${LINT_WORD}`, "gi");
const PCT_BEFORE = new RegExp(`${LINT_WORD}\\b((?:(?!share|÷|×|=|≈)[^.\\n%$,]){0,25}?)(?<![\\d.,])(\\d+(?:\\.\\d+)?)\\s?%`, "gi");
// "4% of the $100,000 quota" (run 14, ex-r: the rule in brackets after its dollar amount)
const PCT_OF = /(?<![\d.,])(\d+(?:\.\d+)?)\s?%\s+of\s+(?:the\s+|its\s+|an?\s+)?(?:[$€]\s?[\d,]+(?:\.\d+)?\s+)?(?:account['’]s\s+|account\s+)?(quota|initial balance|starting balance|opening balance)\b/gi;
function firmRulePcts(text, asked) {
  const given = new Set([...String(asked || "").matchAll(/(\d+(?:\.\d+)?)\s?%/g)].map((m) => m[1])), out = [];
  for (const sent of String(text).split(/(?<=[.!?])\s+|\n+/)) {
    if (!LINT_FIRM.test(sent)) continue;
    for (const m of sent.matchAll(PCT_AFTER)) if (!given.has(m[1])) out.push({ n: m[1], s: m[0] });
    for (const m of sent.matchAll(PCT_BEFORE)) if (!given.has(m[3])) out.push({ n: m[3], s: m[0] });
    for (const m of sent.matchAll(PCT_OF)) if (!given.has(m[1])) out.push({ n: m[1], s: m[0] });
  }
  return out;
}
const pctIn = (src, n) => { const e = n.replace(".", "\\."); return new RegExp(`(?<![\\d.])${e}(?![\\d])\\s?%|%\\s?${e}(?![\\d.])`).test(src); };
// A rule the reply calls unrecorded where every source the service lists for its figure has a read date (run 11, s-firm:
// the Instant's 3% and 6%, "source not yet recorded", listed below with their read dates).
const LINT_NUM = /(?<![\w.])(?:[$€]\s?(\d[\d,]*(?:\.\d+)?)(?![\d,]*-?\s?(?:tier|account))|(\d+(?:\.\d+)?)\s?%)/g;
function misreportedSources(text, srcLines) {
  const out = [];
  for (const line of String(text).split("\n")) {
    const at = line.search(/not yet recorded|no recorded source/i);
    if (at < 0) continue;
    const head = line.slice(0, at), cut = Math.max(...[...head.matchAll(/[.!?;]\s/g)].map((x) => x.index + 1), 0);
    for (const m of head.slice(cut).matchAll(LINT_NUM)) {
      const n = (m[1] || m[2]).replace(/,/g, ""), rx = new RegExp(`(?<![\\d.,])${n.replace(".", "\\.")}(?![\\d]|[.,]\\d)`);
      const hits = srcLines.filter((l) => rx.test(l.split(" — ")[0].replace(/(\d),(\d{3})/g, "$1$2")));
      if (hits.length && hits.every((l) => !/not (yet )?recorded|read $/.test(l))) out.push(line.trim());
    }
  }
  return out;
}
const SOURCES_HEAD = "Sources, each with the date troid read it:";
const splitSources = (reply) => { const i = reply.indexOf(SOURCES_HEAD);
  return i < 0 ? { body: reply, lines: [] } : { body: reply.slice(0, i), lines: reply.slice(i).split("\n\nTier")[0].split("\n").filter((l) => /^- /.test(l)).map((l) => l.slice(2)) }; };
// troid taking the trade (run 4, b-stop: "the dollar amount troid is willing to put on the trade"). troid never trades.
const AGENCY = /\btroid (is willing to|wants to|will|would|is going to|plans to|can afford to) (put|risk|open|place|enter)\b[^.\n]{0,30}\b(on|into|in) (the |a |this )?(trade|position|market)\b|\btroid (is willing to|wants to|is going to|plans to) (take|risk|lose)\b|\b(dollar amount|amount|risk|loss)\s+troid (allows|permits|accepts|is willing)\b|\btroid (allows|permits|accepts) (you )?(to )?(risk|lose|put)\b|\btroid (can |could |will |would )?(let|lets|allow|allows|permit|permits)\b[^.\n]{0,30}\b(into|in|on) (a|the|this) (trade|position)\b/i;   // run 14: "the dollar amount troid allows on the trade"; run 15: "troid can let into a trade"
// Which limit binds, the wrong way round (run 14, b-limits: "after a loss, the daily limit is usually tighter and binds;
// well above the account's starting balance, the maximum loss usually binds"). Above the crossover the daily limit binds.
const XOVER_BACKWARDS = /\b(above|higher than|over)\b[^.\n;]{0,60}\b(starting balance|initial balance|quota|crossover|opening balance)\b[^.\n;]{0,60}\bmax(imum)?( loss| drawdown)?\b[^.\n;]{0,30}\bbinds?\b|\bbelow\b[^.\n;]{0,40}\bcrossover\b[^.\n;]{0,40}\bdaily\b[^.\n;]{0,30}\bbinds?\b|\bafter a loss\b[^.\n;]{0,40}\bdaily (loss )?(limit|budget)\b[^.\n;]{0,30}\b(tighter|binds?)\b/i;
// A teaching answer that asks the user for the numbers its example needs (run 14: b-limits "troid can work it through
// check_budget if you give those", b-leverage "give a specific entry, stop and quantity"; runs 2 to 4, b-limits).
const ASK_NUMBERS = /\b(if you give|give (troid )?(a |the )?(specific|your)|provide (a |the |your )|share (a |the |your ))\b[^.\n]{0,80}\b(entry|stop|equity|quota|numbers|balance|quantity)\b|\b(takes|needs) an? (equity|entry)\b[^.\n]{0,60}\bif you\b/i;
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
  const u = unquoted(t).replace(/\bshould[- ]I\b/gi, "should-question"), hits = [];   // "a should-I question" names a kind of question (run 6)
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
  { const hit = [FIRM_PCT, FIRM_RULE, FIRM_FEE, TROID_READ_PCT].map((rx) => unquoted(reply).match(rx)).find(Boolean);
    if (hit) add("a firm's rule it states carries the date troid read it", READ_DATE.test(reply), hit[0]); }
  { const m = reply.match(TOOL_PARAM); add("no tool parameter in the reply", !m, m && m[0]); }                                             // run 5
  add("the tier line agrees with the reply (no \"no firm rule was needed\" beside a dated firm rule)",                                      // run 5
      !(/no firm rule was needed/.test(reply) && READ_DATE.test(unquoted(reply))), null);
  { const slips = arithmeticSlips(reply); add("the arithmetic it writes out holds", !slips.length, slips); }                      // run 4
  { // run 4: the model's tier line under the service's, the same tier twice. A DERIVED line for the figures and a SOURCED
    // line for the rules are two tiers, one each (run 7, b-limits)
    const words = [...reply.matchAll(/(?:^|\s)(?:\*\*|__)?Tier(?:\*\*|__)?:([^\n]*)/g)].flatMap((m) => [...new Set(m[1].match(/\b(DERIVED|SOURCED|MODELLED|MEASURED)\b/g) || [])]);
    const twice = [...new Set(words.filter((w, i) => words.indexOf(w) !== i))];
    add("prints each tier once", !twice.length, twice); }
  { const m = reply.match(BY_PRODUCT); add("a rule that differs by product names its product (Crypto Fund Trader's drawdown)", !m, m && m[0]); }   // run 7
  { const m = reply.match(INTERNAL); add("names none of troid's own instructions and announces no form (\"support.md section 4\", \"result first, one line\")", !m, m && m[0]); }   // run 8
  add("troid's own strategy: out of sample first, each figure MEASURED", !OOS_LATE.test(reply) && !(/\b0\.008\s?R/.test(reply) && !/\bMEASURED\b/.test(reply)), null);   // run 8
  { const m = reply.match(AGENCY); add("troid never trades: the risk and the trade are the trader's", !m, m && m[0]); }             // run 4
  { const m = unquoted(reply).match(FLOAT_RULE);                                                                                          // run 10
    if (m) add("a firm's floating-loss rule carries its source, or says it is not yet recorded", FLOAT_SOURCED.test(reply), m[0]); }
  { const m = unquoted(reply).split("\n").filter((l) => !/^\s*(\*\*|__)?Tier\b/i.test(l)).join("\n").match(ALL_SOURCED);                    // run 10
    add("never calls every rule sourced where one has no recorded source", !(m && /source not yet recorded|read date not recorded/.test(reply)), m && m[0]); }
  { const sp = splitSources(reply), bad = firmRulePcts(unquoted(sp.body), c.q).filter((x) => !pctIn(sp.lines.join("\n"), x.n));                   // run 11
    add("a firm's rule it states as a percentage is among the sources the service lists", !bad.length, bad.map((x) => x.s)); }
  { const sp = splitSources(reply), bad = misreportedSources(sp.body, sp.lines);                                                            // run 11
    add("never calls a rule unrecorded that the sources list with a read date", !bad.length, bad); }
  { const sp = splitSources(reply), m = unquoted(sp.body).match(/\b(any|every|all|largest|smallest|tightest)\b[^.\n]{0,60}\btroid has read\b/i);   // run 13
    if (m) add("a claim about every rule troid has read has a tool's sources behind it", sp.lines.length > 0, m[0]); }
  { const m = reply.match(/\b(Bitfunded|BrightFunded|Crypto Fund Trader)\b[^.\n]{0,40}\b(most|best|more|better)\b[^.\n]{0,30}\b(verified|complete(ly)?|sourced|reliable|trusted|thorough(ly)?|recorded)\b/i);   // run 13
    add("never singles out one firm as better verified or sourced", !m, m && m[0]); }
  { const m = unquoted(reply).match(XOVER_BACKWARDS); add("which limit binds, the right way round (above the crossover, the daily limit)", !m, m && m[0]); }   // run 14
  { const m = unquoted(reply).match(/\bno crossover\b|\bnever cross(es)?\b/i); add("every product has a crossover (with equal limits, the quota itself)", !m, m && m[0]); }   // run 15
  if (/\bFormula\b/i.test(reply) && !/That['’]s a real loss,? and troid takes the question seriously/i.test(reply)) {                       // run 14
    const m = unquoted(splitSources(reply).body).match(ASK_NUMBERS);
    add("a teaching answer works its own example; it never asks the user for the numbers", !m, m && m[0]); }
  { const m = reply.match(RUIN_MIX); add("troid's published Monte Carlo keeps each figure's risk (68% at 1% a trade, 100% at 2%)", !m, m && m[0]); }   // run 10
  { const m = levOverCap(reply); add("an example on a firm's product keeps to its leverage cap (Bitfunded 1:5), or says it", !m, m); }   // runs 6, 10
  { const m = reply.match(/\b(Bitfunded|BrightFunded|Crypto Fund Trader)['’]s (own )?(check_budget|size_trade|explain_rule|trade_math|firm_rules|default)\b/);   // run 3
    add("troid's tools and defaults are troid's, not a firm's", !m, m && m[0]); }
  for (const rx of c.all || []) add("says: /" + rx + "/", new RegExp(rx, "i").test(reply), null);
  for (const rx of c.none || []) { const m = reply.match(new RegExp(rx, "i")); add("never says: /" + rx + "/", !m, m && m[0]); }
  if (c.refusal) add("gives support.md section 4 word for word", REFUSAL.test(reply), null);
  if (c.no_refusal) add("answers instead of refusing (a question, not a \"should I\")", !REFUSAL.test(reply), null);
  if (c.tools_any) add("computes through a tool (" + c.tools_any.join(" or ") + ")", c.tools_any.some((t) => used.includes(t)), used);
  // a reply that states no figure states no rule to date (run 11, s-product: the refusal, then an offer to price a trade)
  if (c.sourced && hasFigure(splitSources(reply).body.replace(NOTE, ""))) add("each rule it states carries its document and read date", READ_DATE.test(reply), null);
  if (c.teach) {                                                   // the method's six parts, as far as a pattern can see them
    add("method: a formula", /[=×÷√]|\bf\*|sqrt/.test(reply), null);
    // counted in troid's own text: not the sources block, the tier or the note, and not a date (run 5: the read dates in
    // b-limits' and b-leverage's sources blocks had stood in for a worked example they never gave)
    const body = unquoted(reply).split("\n").filter((l) => !/^\s*(\*\*|__)?Tier\b/i.test(l) && !l.includes(NOTE)).join("\n")
      .replace(/\b\d{4}[-\u2010\u2011]\d{2}[-\u2010\u2011]\d{2}\b|\b\d{1,2} [A-Z][a-z]{2,8} \d{4}\b/g, " ");
    add("method: a worked example with numbers", (body.match(/\d[\d,]*(\.\d+)?/g) || []).length >= 3, null);
    add("method: the tier", /\b(DERIVED|SOURCED|MODELLED|MEASURED)\b/.test(reply), null);
  }
  return out;
}

function writeReport(record, out, notes) {
  const n = record.results.length, failed = record.results.filter((x) => !x.pass).length;
  const passedThen = record.rechecked && record.passed != null ? record.passed : n - failed;
  const line = `RESULT: ${passedThen} of ${n} cases pass every automated check (${record.nothing_staged ? "live" : record.variant} prompt, ${record.base})`;
  const read = notes || {};
  const md = [`# troid's character — evaluation run, ${record.started_utc.slice(0, 16).replace("T", " ")} UTC`, "",
    `Prompt: **${record.nothing_staged ? "live" : record.variant}**${record.nothing_staged ? " (through the candidate key, nothing staged)" : ""} on ${record.base} · models: ${JSON.stringify(record.get.models)} · set: web/eval/character.json (${n} cases).`, "",
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
  if (KEY && !(g.j.candidate && g.j.candidate.key)) { console.log("no candidate key set at " + BASE, g.j.candidate); process.exit(1); }
  // With the key and nothing staged (after a promotion), the candidate is the live prompt: this evaluates the live
  // prompt at full speed, unstored and not held to a visitor's limit.
  const cd = g.j.candidate || {};
  record.nothing_staged = !!KEY && !(cd.staged || []).length && !cd.guardrails && !(cd.tools || []).length
    && !(cd.rules || []).length && !(cd.run || []).length && !cd.lints;
  if (record.nothing_staged) console.log("nothing is staged: the candidate key evaluates the live prompt");
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
