#!/usr/bin/env python3
"""A draft language's address sends a visitor home, and a live one's never does: no network, nothing written.

  python web/test_lang_redirect.py

Drafts are never published (web/i18n/README.md, "The rule"), so /zh, /es, /ar and the rest have no page behind them.
web/vercel.json sends each draft's bare address to / with a temporary redirect (the owner, 2026-10-18), and a language
leaves that list the day its file says "_status": "live": a live language still in it would send its readers home,
and a draft missing from it would answer with a 404.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
fails = 0


def ok(name, cond, info=""):
    global fails
    fails += 0 if cond else 1
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else f"  {str(info)[:400]}"))


codes = [x["code"] for x in json.loads((ROOT / "web" / "i18n" / "languages.json").read_text())["languages"] if x["code"] != "en"]
status = {c: json.loads((ROOT / "web" / "i18n" / f"{c}.json").read_text()).get("_status") for c in codes}
live = sorted(c for c in codes if status[c] == "live")
draft = sorted(c for c in codes if status[c] != "live")

LANG = re.compile(r"^/:lang\(([a-z|]+)\)$")
redirects = json.loads((ROOT / "web" / "vercel.json").read_text()).get("redirects", [])
lang = [r for r in redirects if LANG.match(r.get("source", ""))]
ok("web/vercel.json has one draft-language redirect, /:lang(…)", len(lang) == 1, lang)
r = lang[0] if lang else {}
sent = sorted(LANG.match(r["source"]).group(1).split("|")) if lang else []
ok("it sends the bare address home, temporarily (307), and nothing else",
   r.get("destination") == "/" and r.get("permanent") is False and not r.get("has") and not r.get("missing"), r)
ok(f"every draft language is in it ({', '.join(draft) or 'none'})", set(draft) <= set(sent), sorted(set(draft) - set(sent)))
ok(f"no live language is in it ({', '.join(live) or 'none live'})", not set(live) & set(sent), sorted(set(live) & set(sent)))
ok("English and unknown codes aren't in it", set(sent) <= set(codes), sorted(set(sent) - set(codes)))
ok("each code is listed once", len(sent) == len(set(sent)), sent)

print(f"\n{'FAILURES above' if fails else 'all passed'}")
sys.exit(1 if fails else 0)
