#!/usr/bin/env python3
"""The owner's launch handoff, section 0, held in place: no network, nothing written.

  python web/test_retired_wording.py

- troid's result is "no measurable edge": never "no statistical edge" or its variants, anywhere troid publishes or
  ask troid reads.
- Bitfunded's reset is stated in UTC. 16:00 UTC is noon in New York only while New York keeps daylight saving; from
  Sunday 1 November 2026 it is 11:00. So no fixed local hour for the reset, anywhere; a local hour appears only where it
  is computed for the date shown.
- The phone menu stays labelled "data".
- Prices include tax (the owner's addendum, 28 Sep 2026): $19 is what every buyer pays, so never "plus tax" or its
  variants, in English or in any language file, on troid Pro's pages or in its Checkout copy.

What is scanned is what goes live: the English strings and templates, the English pages as built, the repo's documents,
the MCP server, the desk skill's references, and ask troid's prompt and reset explanation as they will go live (a copy
staged in web/context/patch/ stands in for its live file until the patch's evaluation publishes it, as in
backtest/claim_check.py, which the daily loop runs with the same two patterns).
"""
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backtest"))
from claim_check import RETIRED_EDGE, FIXED_LOCAL_RESET, PLUS_TAX  # noqa: E402  (one definition, shared with the daily check)

fails = 0


def ok(name, cond, info=""):
    global fails
    fails += 0 if cond else 1
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else f"  {str(info)[:400]}"))


# --- why: the same UTC time is a different New York hour on either side of 1 November 2026 -------------------------------
ny = ZoneInfo("America/New_York")
at = lambda day: dt.datetime.combine(day, dt.time(16, 0), tzinfo=dt.timezone.utc).astimezone(ny).strftime("%H:%M %Z")
ok("16:00 UTC is 12:00 in New York on Saturday 31 October 2026 (EDT) and 11:00 on Sunday 1 November (EST)",
   at(dt.date(2026, 10, 31)) == "12:00 EDT" and at(dt.date(2026, 11, 1)) == "11:00 EST", [at(dt.date(2026, 10, 31)), at(dt.date(2026, 11, 1))])

# --- the patterns catch what they are for, and pass what replaced it ------------------------------------------------------
retired = ["troid's own strategy shows no statistical edge.", "no statistically significant edge", "16:00 UTC — noon in New York in summer",
           "noon in New York, 11:00 in winter", "a loss at 11:45 and a loss at 12:15 EDT", "in New York it is noon"]
kept = ["troid's own strategy shows no measurable edge.", "16:00 UTC all year", "For a trader in New York it lands mid-session in every season",
        "a loss at 15:45 UTC and a loss at 16:15 UTC", "can't distinguish +0.033R from no edge at all", "8:30 ET"]
ok("the patterns catch every retired phrasing", all(RETIRED_EDGE.search(t) or FIXED_LOCAL_RESET.search(t) for t in retired),
   [t for t in retired if not (RETIRED_EDGE.search(t) or FIXED_LOCAL_RESET.search(t))])
ok("and pass what replaced them (a bare 'no edge at all' names the statistical null)", not any(RETIRED_EDGE.search(t) or FIXED_LOCAL_RESET.search(t) for t in kept),
   [t for t in kept if RETIRED_EDGE.search(t) or FIXED_LOCAL_RESET.search(t)])
taxed = ["$19/month plus tax", "$19 + tax", "$19/month (excl. VAT)", "plus applicable taxes", "VAT is added at checkout", "19 € HT",
         "US$19 más IVA", "mais impostos", "плюс НДС", "belum termasuk pajak", "不含税", "稅金另計", "غير شامل الضريبة", "कर अतिरिक्त", "কর আলাদা"]
included = ["$19/month or $190/year, tax included.", "risco ÷ (distância do stop + taxa por unidade)", "19 $ TTC", "impuestos incluidos",
            "stop + fee", "HTML", "taxonomy", "含税"]
ok("the 'plus tax' pattern catches it in English and the launch languages", all(PLUS_TAX.search(t) for t in taxed),
   [t for t in taxed if not PLUS_TAX.search(t)])
ok("and passes 'tax included', a Portuguese 'taxa' (a fee) and the like", not any(PLUS_TAX.search(t) for t in included),
   [t for t in included if PLUS_TAX.search(t)])

# --- what goes live ---------------------------------------------------------------------------------------------------------
def staged_or_live(name, live):
    p = ROOT / "web" / "context" / "patch" / name
    return p if p.exists() else live


en = json.loads((ROOT / "web" / "i18n" / "en.json").read_text())
texts = {f"en.json {k}": v for k, v in en.items() if isinstance(v, str) and not k.startswith("_")}
files = ([*(ROOT / "web" / "templates").rglob("*.html"), *(ROOT / "web" / "public").glob("*.html"), *(ROOT / "web" / "public" / "firms").glob("*.html"),
          ROOT / "README.md", ROOT / "web" / "public" / "llms.txt", ROOT / "backtest" / "STRATEGY.md", ROOT / "backtest" / "WALKFORWARD.md", ROOT / "mcp" / "server.py",
          *(ROOT / ".claude" / "skills" / "prop-trading-desk").rglob("*.md"), ROOT / ".claude" / "skills" / "prop-trading-desk" / "config.example.json",
          ROOT / "backtest" / "bitfunded_config.json", ROOT / "firms.json",
          staged_or_live("TROID.md", ROOT / "web" / "public" / "TROID.md"),
          staged_or_live("support.md", ROOT / "web" / "context" / "support.md"),
          staged_or_live("TROID-CHARACTER.md", ROOT / "web" / "context" / "TROID-CHARACTER.md")])
for f in files:
    texts[str(f.relative_to(ROOT))] = f.read_text()
# METHODOLOGY's corrections table quotes each error it corrects: its rows are the record, not claims (as in claim_check.py)
texts["METHODOLOGY.md"] = re.sub(r"(?m)^\| \d{4}-\d{2}-\d{2} \|.*$", "", (ROOT / "METHODOLOGY.md").read_text())

# ask troid's reset explanation as it goes live: the patch's, while one is staged, else the live one
node = subprocess.run(["node", "-e", """
  process.env.TROID_ASSISTANT = "";
  const h = require("./api/troid.js");
  const variant = h._patchRules && h._patchRules.reset ? "patch" : "live";
  process.stdout.write(JSON.stringify({ variant, text: h._runTool("explain_rule", { topic: "reset" }, variant).explanation }));
"""], cwd=ROOT / "web", capture_output=True, text=True)
reset = json.loads(node.stdout) if node.returncode == 0 else {"variant": "?", "text": node.stderr}
texts[f"ask troid's reset explanation ({reset['variant']})"] = reset["text"]
ok("ask troid's reset explanation as it goes live says 16:00 UTC", "16:00 UTC" in reset["text"], reset)

hits = []
for name, s in texts.items():
    for rx in (RETIRED_EDGE, FIXED_LOCAL_RESET):
        for m in rx.finditer(re.sub(r"\s+", " ", s)):
            hits.append((name, m.group(0)))
ok(f"none of {len(texts)} texts troid publishes or ask troid reads says 'no statistical edge' or gives the reset a fixed local hour",
   not hits, hits[:10])

# prices include tax: every language file, troid Pro's pages and its Checkout copy too
taxed_texts = dict(texts)
for f in sorted((ROOT / "web" / "i18n").glob("*.json")):
    for k, v in json.loads(f.read_text()).items():
        if isinstance(v, str) and not k.startswith("_"):
            taxed_texts[f"{f.name} {k}"] = v
for f in [*(ROOT / "web" / "pro").glob("*.html"), ROOT / "web" / "lib" / "pro.js", ROOT / "web" / "public" / "llms.txt"]:
    taxed_texts[str(f.relative_to(ROOT))] = f.read_text()
tax_hits = [(name, m.group(0)) for name, s in taxed_texts.items() for m in PLUS_TAX.finditer(re.sub(r"\s+", " ", s))]
ok(f"none of {len(taxed_texts)} texts, every language file and troid Pro's pages among them, says 'plus tax' (prices include tax)",
   not tax_hits, tax_hits[:10])

ok('the phone menu stays labelled "data" (launch handoff, section 0)', en.get("common.nav.menu") == "data", en.get("common.nav.menu"))

print(f"\n{'FAILURES above' if fails else 'all passed'}")
sys.exit(1 if fails else 0)
