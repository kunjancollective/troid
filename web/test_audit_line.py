#!/usr/bin/env python3
"""The two lines under troid's desk (web/public/audit.js; calculator audit, 2026-09-29), in Chromium against web/public
served locally and the Arabic draft preview built for the run. /audit.json is answered by the test with fixtures,
TradingView's script by backtest/tv_stub.py; /status.json, /calendar.json and /api/ticker get 404: spends nothing,
calls no one.

  python web/test_audit_line.py

- Passed: "Calculators audited 4 Oct 2026 · 1,023 checks passed · report", the link to that week's report on GitHub.
- Failed: "… · mismatches found: 2 · report", said as plainly, and one mismatch reads as plainly as two: the count
  stands after a colon, so no language needs a plural form for it.
- Hidden when /audit.json is missing, isn't JSON, or doesn't hold together (checks ≠ passed + failed, a date that isn't
  one, a report not named for its week, a commit that isn't one, a count that isn't a whole number).
- An old audit shows its date as it is, with no other wording.
- "Rules read {range}" on its own line, its dates firms.json's (audit/provenance.py derives them on its own), put in
  the page's language by Intl; the ISO dates are in the page before the script runs.
- Right to left (/ar, a draft preview): the same lines in the page's locale, nothing off a phone's edge.
- site.json calc_audit false: neither line nor the script is in the page.
"""
import datetime as dt
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "audit"))
from i18n_equiv import PUB, serve  # noqa: E402
from tv_stub import route_tv  # noqa: E402
import provenance  # noqa: E402

EN = json.loads((ROOT / "web" / "i18n" / "en.json").read_text())
REPO = "https://github.com/kunjancollective/troid/blob/main/"
RULES = provenance.rules_read()
fails, n = [], 0


def ok(name, cond, info=""):
    global n
    n += 1
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else f"  {str(info)[:400]}"))
    if not cond:
        fails.append(name)


def doc(**kw):
    d = {"date": "2026-10-04", "week": "2026-W40", "commit": "0123456789abcdef0123456789abcdef01234567", "checks": 1023,
         "passed": 1023, "failed": 0, "report": "audit/reports/2026-W40.md", "pages": ["/", "/ar"], "cases": 1128,
         "seed": "2026-W40", "rules_read": RULES, "stale_rules": [], "unsourced_rules": []}
    d.update(kw)
    return json.dumps(d)


LINES = """()=>{const a=document.getElementById('audit'),r=document.getElementById('rulesread'),res=document.getElementById('result');
  const l=a&&a.querySelector('a');
  return {a:!!a,hidden:a?a.hidden:null,vis:a?getComputedStyle(a).display!=='none':null,text:a?a.textContent:null,
    href:l?l.getAttribute('href'):null,rules:r?r.textContent:null,from:r&&r.dataset.from,to:r&&r.dataset.to,
    order:!!(a&&r&&res.nextElementSibling===a&&a.nextElementSibling===r),inside:!!(a&&res.contains(a)),
    dir:document.documentElement.dir||'ltr',sw:document.scrollingElement.scrollWidth,iw:innerWidth}}"""


def main():
    srv, url = serve(PUB)
    tmp = tempfile.TemporaryDirectory()
    subprocess.run([sys.executable, str(ROOT / "backtest" / "site_build.py"), "--preview", tmp.name, "--langs", "ar"],
                   cwd=ROOT, check=True, capture_output=True)
    srv_ar, url_ar = serve(tmp.name)
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")

        # what Intl says, in a page with nothing of troid's in it: the expected dates and counts
        blank = b.new_page()
        intl = blank.evaluate("""([f,t])=>{const o={day:'numeric',month:'short',year:'numeric',timeZone:'UTC'},D=s=>new Date(s+'T00:00:00Z');
          const out={};for(const l of ['en-GB','ar-u-nu-latn']){const F=new Intl.DateTimeFormat(l,o);
            const x=l==='en-GB'?s=>s.replace(/\\bSept\\b/g,'Sep'):s=>s;   // troid's English writes Sep, as the calendar strip does
            out[l]={d:x(F.format(D('2026-10-04'))),old:x(F.format(D('2026-08-30'))),range:x(F.formatRange(D(f),D(t))),sep:x(F.format(D('2026-09-18'))),n:new Intl.NumberFormat(l).format(1023)}}
          return out}""", [RULES["from"], RULES["to"]])
        blank.close()
        ok("Intl en-GB writes the handoff's date form (4 Oct 2026; 18 Sep 2026, not en-GB's 'Sept')",
           intl["en-GB"]["d"] == "4 Oct 2026" and intl["en-GB"]["sep"] == "18 Sep 2026", intl)

        def page(body=None, status=200, base=url, path="/", w=1280, **kw):
            ctx = b.new_context(viewport={"width": w, "height": 900}, timezone_id="UTC", locale="en-US", **kw)

            def handler(r):
                u = r.request.url.split("?")[0]
                if u.endswith("/audit.json"):
                    return r.fulfill(status=status, body=body if body is not None else doc(), content_type="application/json")
                if u.endswith(("/status.json", "/calendar.json")) or "/api/ticker" in u:
                    return r.fulfill(status=404, body="")
                return r.continue_() if u.startswith("http://127.0.0.1") else r.abort()
            ctx.route("**/*", handler)
            route_tv(ctx, "ok")
            pg = ctx.new_page()
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto(base + path, wait_until="load")
            pg.wait_for_timeout(500)
            return ctx, pg, errs

        # before any script: the ISO dates, firms.json's
        raw = (PUB / "index.html").read_text()
        iso = EN["desk2.audit.rules"].replace("{range}", f"{RULES['from']} – {RULES['to']}")
        ok(f"the page carries the rules-read line with firms.json's dates before its script runs ({iso})",
           f">{iso}</p>" in raw and f'data-from="{RULES["from"]}" data-to="{RULES["to"]}"' in raw)
        ok("audit.js is its own script, not in desk2.js", '<script src="/audit.js" defer></script>' in raw
           and "audit.json" not in (PUB / "desk2.js").read_text())

        # passed
        ctx, pg, errs = page()
        s = pg.evaluate(LINES)
        want = f"Calculators audited {intl['en-GB']['d']} · {intl['en-GB']['n']} checks passed · report"
        ok("passed: the line shows", s["a"] and not s["hidden"] and s["vis"], s)
        ok(f"passed: '{want}'", s["text"] == want == "Calculators audited 4 Oct 2026 · 1,023 checks passed · report", s["text"])
        ok("passed: 'report' links that week's report on GitHub", s["href"] == REPO + "audit/reports/2026-W40.md", s["href"])
        ok(f"the rules-read line: 'Rules read {intl['en-GB']['range']}', firms.json's dates in the page's language",
           s["rules"] == "Rules read " + intl["en-GB"]["range"] and (s["from"], s["to"]) == (RULES["from"], RULES["to"]), s)
        ok("both lines sit right after the result, outside it, the audit first", s["order"] and not s["inside"], s)
        ok("no page error", not errs, errs)
        ctx.close()

        # failed, two and one
        for k in (2, 1):
            ctx, pg, errs = page(doc(passed=1023 - k, failed=k))
            s = pg.evaluate(LINES)
            ok(f"failed: 'Calculators audited 4 Oct 2026 · mismatches found: {k} · report'",
               not s["hidden"] and s["text"] == f"Calculators audited {intl['en-GB']['d']} · mismatches found: {k} · report"
               and s["href"] == REPO + "audit/reports/2026-W40.md", s)
            ctx.close()

        # an old audit: its date as it is, nothing added
        ctx, pg, errs = page(doc(date="2026-08-30", week="2026-W35", report="audit/reports/2026-W35.md"))
        s = pg.evaluate(LINES)
        ok(f"an old audit shows its date as it is ({intl['en-GB']['old']}), no other wording",
           not s["hidden"] and s["text"] == f"Calculators audited {intl['en-GB']['old']} · 1,023 checks passed · report", s)
        ctx.close()

        # missing or malformed: hidden, and the rules line stays
        bad = [("404", {"status": 404, "body": ""}), ("not JSON", {"body": "not json"}),
               ("checks ≠ passed + failed", {"body": doc(checks=1024)}), ("not a date", {"body": doc(date="2026-13-01")}),
               ("a date with a time", {"body": doc(date="2026-10-04T00:00:00Z")}),
               ("report not named for its week", {"body": doc(report="audit/reports/2026-W39.md")}),
               ("report elsewhere", {"body": doc(report="https://example.com/x.md")}),
               ("commit not a commit", {"body": doc(commit="HEAD")}), ("a count below 0", {"body": doc(passed=1025, failed=-2)}),
               ("a count as text", {"body": doc(checks="1023")}), ("no checks", {"body": doc(checks=0, passed=0)}),
               ("markup in a field", {"body": doc(week="<b>x</b>")}), ("an array", {"body": "[]"})]
        for name, kw in bad:
            ctx, pg, errs = page(**kw)
            s = pg.evaluate(LINES)
            ok(f"{name}: the audit line stays hidden, the rules line shows", s["a"] and s["hidden"] and not s["vis"]
               and s["rules"] == "Rules read " + intl["en-GB"]["range"] and not errs, (s, errs))
            ctx.close()

        # a phone: nothing off the edge
        ctx, pg, errs = page(doc(passed=1021, failed=2), w=375, is_mobile=True, has_touch=True)
        s = pg.evaluate(LINES)
        ok("375 px: the page never scrolls sideways with both lines", not s["hidden"] and s["sw"] <= s["iw"], s)
        ctx.close()

        # right to left: the Arabic draft preview
        ctx, pg, errs = page(base=url_ar, path="/ar")
        s = pg.evaluate(LINES)
        ar = json.loads((ROOT / "web" / "i18n" / "ar.json").read_text())
        tpl = ar.get("desk2.audit.pass") or EN["desk2.audit.pass"]
        want = tpl.replace("{date}", intl["ar-u-nu-latn"]["d"]).replace("{n}", intl["ar-u-nu-latn"]["n"]).replace('<a href="{href}">', "").replace("</a>", "")
        ok("/ar is right to left", s["dir"] == "rtl", s["dir"])
        ok(f"/ar: the audit line in the page's locale ({intl['ar-u-nu-latn']['d']}), the same report",
           not s["hidden"] and s["text"] == want and s["href"] == REPO + "audit/reports/2026-W40.md", (s, want))
        rtpl = ar.get("desk2.audit.rules") or EN["desk2.audit.rules"]
        ok(f"/ar: the rules line in the page's locale ({intl['ar-u-nu-latn']['range']})",
           s["rules"] == rtpl.replace("{range}", intl["ar-u-nu-latn"]["range"]), s["rules"])
        ok("/ar: no page error", not errs, errs)
        ctx.close()
        ctx, pg, errs = page(base=url_ar, path="/ar", w=375, is_mobile=True, has_touch=True)
        s = pg.evaluate(LINES)
        ok("/ar at 375 px: the page never scrolls sideways", not s["hidden"] and s["sw"] <= s["iw"], s)
        ctx.close()
        b.close()
    srv.shutdown()
    srv_ar.shutdown()
    tmp.cleanup()

    # site.json calc_audit false: nothing of either line in the page
    import site_build
    import i18n
    site_build.SITE["calc_audit"] = False
    T = i18n.Strings("en")
    off = site_build.render_page("index", T, site_build.targets())
    site_build.SITE["calc_audit"] = True
    on = site_build.render_page("index", i18n.Strings("en"), site_build.targets())
    ok("calc_audit false: neither line nor audit.js is in the page", 'id="audit"' not in off and 'id="rulesread"' not in off
       and "/audit.js" not in off and 'id="audit"' in on and "/audit.js" in on)

    print(f"\n{n - len(fails)}/{n} passed")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
