"use strict";
/* Where a reply's numbers come from. Shared by ask troid's service (web/api/troid.js, which lints a draft with it) and
   the character evaluation (web/eval_character.js, which checks a reply with it). Not an endpoint: Vercel serves no
   file in api/ whose name starts with an underscore.

   Every number in a reply comes from a tool's inputs or results, the user's own message, or troid's published figures
   (TROID.md's reference account and its strategy's results); anything else was computed in prose (evaluation run 16:
   b-stop's "roughly 3.5 times as many units", 3.1 with its own fee; o-montecarlo's intermediate sums). One exception,
   arithmetic shown step by step: a written "a op b = c = d" chain whose arithmetic holds and which starts from, or ends
   at, supported numbers, as in "1 ÷ (1 + 1.5) = 1 ÷ 2.5 = 40%". Dates, times, clause and section numbers, product names
   and list numbering are not figures. */

// Arithmetic written out. A word, a symbol this doesn't read, or a ± ends an expression; a result is allowed the
// rounding its own decimals show, or half a percent (evaluation run 4, q-stats: "0.0453 × 3.28 ≈ 0.1181").
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

// troid's reference account ($100,000) and its strategy's published results (TROID.md, "Does the strategy work?"),
// with 0, 1, 2 and 100, which every answer uses without computing anything
const PUBLISHED_NUMBERS = [0, 1, 2, 100, 100000, 0.008, 504, 498, 0.016, 95, 1.96, 0.033, 78, 30, 0.046, 0.093];
const MONTHS = "(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*";
const NOT_FIGURES = [/https?:\/\/\S+/g, /\b\d{4}-\d{2}-\d{2}\b/g, new RegExp(`\\b\\d{1,2} ${MONTHS},? \\d{4}\\b`, "g"),
  new RegExp(`\\b${MONTHS} \\d{1,2},? \\d{4}\\b`, "g"), /\b\d{1,2}:\d{2}\b/g, /\bUTC\s?[+−-]\s?\d+\b/g, /\b\d+(?:\([a-z]+\))+/g,
  /\b[sS]\.\s?\d+\b/g, /\b\d+\.[ivx]+\b/g, /\b\d\s?-?\s?(?:step|phase)\b/gi, /\b(?:stage|step|phase|level|section|tier|part|rule)\s\d+\b/gi,
  /^\s*(?:#+\s*)?\d+[.)]\s/gm, /(?<![$\d,.])\b(?:19|20)\d\d\b(?![,.]?\d)/g];
const NUM_RX = /(?<![\p{L}\p{N}_.])(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)(?=(?:\s?%|R|x|×|k)?(?![\p{L}\p{N}_]))/gu;
const numbersIn = (t) => [...String(t || "").matchAll(NUM_RX)].map((m) => ({ s: m[1], v: +m[1].replace(/,/g, ""), dec: (m[1].split(".")[1] || "").length }));
// every number in the tools' inputs and results: [{ input, result }]
const toolNumbers = (log) => [...new Set((JSON.stringify((log || []).map((t) => [t.input, t.result])).match(/\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?/g) || [])
  .map((s) => s.replace(/,/g, "")))];

function unsupportedNumbers(text, allowedTexts, allowedNums) {
  // "min(480,700)" is two numbers, not 480,700
  let t = String(text || "").replace(/\*\*|__|`/g, "").replace(/\b(min|max)\((\d[\d.]*),(\d[\d.]*)\)/g, "$1($2, $3)");
  for (const rx of NOT_FIGURES) t = t.replace(rx, " ");
  const allowed = [...PUBLISHED_NUMBERS, ...(allowedNums || []).map((x) => +String(x).replace(/,/g, "")),
                   ...(allowedTexts || []).flatMap((x) => numbersIn(x).map((n) => n.v))].filter((v) => Number.isFinite(v));
  const ok = (n) => { const tol = 0.5 * 10 ** -n.dec + 1e-9;   // the tool's value, rounded as the reply shows it; 25% for 0.25
    return allowed.some((a) => Math.abs(n.v - a) <= tol || Math.abs(n.v - a * 100) <= tol || Math.abs(n.v - a / 100) <= tol); };
  const exempt = new Set();                      // the numbers of a written chain that holds and rests on supported numbers
  for (const line of t.replace(/(\d),(?=\d{3}(?!\d))/g, "$1").split("\n")) {
    const parts = line.split(/\s(=|≈)\s/), pairs = [];
    for (let i = 0; i + 2 < parts.length; i += 2) { const lr = arithSides(parts[i], parts[i + 2]); if (lr) pairs.push([lr, parts[i + 1] === "≈"]); }
    if (!pairs.length || !pairs.every(([[L, R], ap]) => arithHolds(L, R, ap))) continue;
    const exprs = pairs.flatMap(([[L, R]]) => [L, R]);
    if (!exprs.some((x) => numbersIn(x.s).every(ok) && (x.ops || x.single))) continue;
    for (const x of exprs) for (const n of numbersIn(x.s)) exempt.add(n.v);
  }
  const out = [];
  for (const n of numbersIn(t)) if (!ok(n) && !exempt.has(n.v) && !out.includes(n.s)) out.push(n.s);
  return out;
}

module.exports = { arithTokens, arithParse, arithSides, arithHolds, MATHY, PUBLISHED_NUMBERS, numbersIn, toolNumbers, unsupportedNumbers };
