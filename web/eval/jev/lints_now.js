// The regex baseline for the Jev trial (REPORT.md): which of the candidate's current lint notes (web/api/troid.js
// _lintNotesFor, read only) fire on each saved reply with a person's read. Replayed offline from the reply and its
// question; the lints that need the turn's tool results (a firm rule's source among them) can't be replayed this way.
//   OUT=/tmp/lints.json node web/eval/jev/lints_now.js web/eval/runs [DIR …]
const fs = require("fs"), path = require("path");
const T = require(path.resolve("web/api/troid.js"));
const seen = new Set(), out = {};
for (const d of process.argv.slice(2)) for (const f of fs.readdirSync(d).filter((f) => f.endsWith(".read.json")).sort()) {
  const run = f.slice(0, -".read.json".length);
  if (seen.has(run)) continue;
  seen.add(run);
  const read = JSON.parse(fs.readFileSync(path.join(d, f))), res = JSON.parse(fs.readFileSync(path.join(d, run + ".json")));
  for (const x of res.results) {
    if (typeof read[x.id] !== "string" || !x.reply) continue;
    out[run + "|" + x.id] = T._lintNotesFor(x.reply, "candidate", x.tools_used || [], x.q, x.q).map((n) => String(n).slice(0, 90));
  }
}
fs.writeFileSync(process.env.OUT || "lints.json", JSON.stringify(out));
console.log(Object.keys(out).length, "replies");
