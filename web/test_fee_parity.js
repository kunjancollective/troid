// The fee convention, one across troid (the calculator audit's F6, live since 2026-10-07): a unit's fees are
// fee × (entry + stop), the exit fee charged on the exit notional at the stop, so the loss at the stop, both fees in it,
// is the risk to the cent, long or short. ask troid's live tools, its candidate's, the desk's figures (audit/model.py,
// the audit's own derivation of every figure the desk shows, which audit/run.py holds the built desk to each week) and
// the MCP server (mcp/server.py) give the same quantity, notional and loss at the stop on p-size's inputs and on the
// audit's fixed long and short cases (audit/cases.py, F6 and edge 05).
//   node web/test_fee_parity.js
"use strict";
const path = require("path");
const { execFileSync } = require("child_process");
const handler = require("./api/troid.js");
const RC = handler._runTool, ROOT = path.join(__dirname, "..");
let n = 0, bad = 0;
const ok = (name, cond, got) => { n++; if (!cond) { bad++; console.log("FAIL " + name, String(JSON.stringify(got)).slice(0, 600)); } else console.log("ok   " + name); };

// each case in the desk's inputs (audit/model.py's x): p-size's question, then the audit's F6 regressions and edge 05
const BASE = { quota: 100000, equity: 100000, daystart: 100000, side: 1, entry: 60000, stop: 59400, targetR: 2, riskPct: 0.5, capPct: 35, lev: 5, mode: "cross" };
const CASES = [
  ["p-size: short 77,872 with a 0.3% stop at $96,000, 0.5% risk", { quota: 100000, equity: 96000, daystart: 96000, side: -1, entry: 77872, stop: 77872 * 1.003 }],
  ["F6: long, 1% stop", { stop: 59400 }],
  ["F6: short, 1% stop", { side: -1, stop: 60600 }],
  ["F6: long, 0.2% stop", { stop: 59880 }],
  ["F6: short, 0.2% stop", { side: -1, stop: 60120 }],
].map(([name, x]) => [name, Object.assign({}, BASE, x)]);

// the desk's figures and the MCP server's, from Python (the MCP SDK isn't needed to call the function: a stand-in for FastMCP)
const PY = `
import json, sys, types
sys.path.insert(0, "audit"); sys.path.insert(0, "mcp")
class _F:
    def __init__(self, *a, **k): pass
    def tool(self, *a, **k): return lambda f: f
    def resource(self, *a, **k): return lambda f: f
    def prompt(self, *a, **k): return lambda f: f
    def run(self, *a, **k): pass
m = types.ModuleType("mcp"); s = types.ModuleType("mcp.server"); f = types.ModuleType("mcp.server.fastmcp"); f.FastMCP = _F
sys.modules.update({"mcp": m, "mcp.server": s, "mcp.server.fastmcp": f})
import model as M, server as S
out = []
for x in json.loads(sys.argv[1]):
    d = M.model("bitfunded", "1step", x)
    t = S.size_trade(quota=x["quota"], equity=x["equity"], day_start_balance=x["daystart"], side="long" if x["side"] > 0 else "short",
                     entry=x["entry"], stop=x["stop"], target_r=x["targetR"], risk_pct_of_balance=x["riskPct"], leverage=x["lev"],
                     profile="1step", margin_mode=x["mode"])
    q = t["quantity"]
    out.append({"desk": {"quantity": d["qty"], "notional": d["notional"], "loss": d["loss"]},
                "mcp": {"quantity": q, "notional": t["notional"], "loss": q * abs(x["entry"] - x["stop"]) + 0.0004 * q * (x["entry"] + x["stop"])}})
print(json.dumps(out))
`;
const py = JSON.parse(execFileSync("python3", ["-c", PY, JSON.stringify(CASES.map(([, x]) => x))], { cwd: ROOT, encoding: "utf8" }));

const r6 = (v) => Math.round(v * 1e6) / 1e6, c2 = (v) => Math.round(v * 100) / 100;
CASES.forEach(([name, x], i) => {
  const a = { firm: "bitfunded", product: "1step", quota: x.quota, equity: x.equity, day_start: x.daystart, side: x.side > 0 ? "long" : "short",
              entry: x.entry, stop: x.stop, risk_pct: x.riskPct, budget_cap_pct: x.capPct, leverage: x.lev, margin_mode: x.mode, target_r: x.targetR };
  const live = RC("size_trade", a, "live"), cand = RC("size_trade", a, "candidate");
  const lossOf = (r) => r.quantity * Math.abs(x.entry - x.stop) + 0.0004 * r.quantity * (x.entry + x.stop);
  const risk = cand.risk;
  // trade_math's position_size on the same risk, both variants
  const pm = { calc: "position_size", risk, entry: x.entry, stop: x.stop, firm: "bitfunded", product: "1step" };
  const tmL = RC("trade_math", pm, "live").result, tmC = RC("trade_math", pm, "candidate").result;
  const rows = {
    "live size_trade": [live.quantity, live.notional, c2(lossOf(live))],
    "candidate size_trade": [cand.quantity, cand.notional, cand.loss_at_stop],
    "live trade_math": [tmL.quantity, tmL.notional, c2(tmL.quantity * Math.abs(x.entry - x.stop) + 0.0004 * tmL.quantity * (x.entry + x.stop))],
    "candidate trade_math": [tmC.quantity, tmC.notional, tmC.loss_at_stop],
    "the desk (audit/model.py)": [r6(py[i].desk.quantity), c2(py[i].desk.notional), c2(py[i].desk.loss)],
    "the MCP server": [r6(py[i].mcp.quantity), py[i].mcp.notional, c2(py[i].mcp.loss)],
  };
  const ref = rows["the desk (audit/model.py)"];
  ok(`${name}: quantity ${ref[0]}, notional ${ref[1]}, loss at the stop ${ref[2]} = the risk, in all six`,
     Object.values(rows).every((v) => v[0] === ref[0] && v[1] === ref[1] && v[2] === ref[2]) && ref[2] === c2(risk), rows);
});
// p-size's own figures, as run 20's read and the desk give them (the live baseline gave 1.622095 before 2026-10-07)
const ps = RC("size_trade", { firm: "bitfunded", product: "1step", quota: 100000, equity: 96000, day_start: 96000, side: "short", entry: 77872, stop_pct: 0.3, risk_pct: 0.5 }, "live");
ok("live p-size: 1.621583, $126,275.91, margin $25,255.18, fees $101.17 (21.08%), cross liquidation 75.15%",
   ps.quantity === 1.621583 && ps.notional === 126275.91 && ps.margin === 25255.18 && ps.fees === 101.17 && ps.fee_share_of_risk_pct === 21.08
   && ps.circuit_breakers.find((b) => /liquidation/.test(b.event)).adverse_move_pct === 75.15
   && ps.working.find((w) => w.step === "fee per unit").formula === "(entry + stop) × 0.04%", ps);
// no live text left with the old convention
const src = require("fs").readFileSync(path.join(__dirname, "api", "troid.js"), "utf8"), TR = require("fs").readFileSync(path.join(ROOT, "TROID.md"), "utf8");
ok("no entry × fee × 2 left in ask troid's tools or the live TROID.md", !/entry × \$\{p\.fee\}% × 2|"entry × " \+ fee \+ "% × 2|entry \* fee \* 2|entry \* \(fee \|\| 0\) \/ 100 \* 2|entry × fee × 2|round-trip fee/.test(src)
   && /fee_unit   = fee_per_side × \(entry \+ stop\)/.test(TR) && !/entry × fee_per_side × 2/.test(TR));
console.log(`RESULT: ${bad ? "FAILED" : "0 failed"} (${n} checks)`);
process.exitCode = bad ? 1 : 0;
