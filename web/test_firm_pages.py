#!/usr/bin/env python3
"""troid's page of each compared firm's rules, /firms/<slug> (launch handoff 2026-09-26, 5.2 A), as the build writes it.

  python web/test_firm_pages.py

- One page per firm on troid's compare (firms.json compare_product), at /firms/<key with - for _>, in the sitemap and
  llms.txt; /firms itself goes to troid's compare, not permanently (a list of firms may live there one day).
- The rules section is troid's compare column for that firm, row for row, without its sizing block (whose "from your
  inputs" would be untrue on a page with no inputs) and without its foot, which holds the firm's link: no affiliate link,
  code or referral id anywhere on the page. A partner firm's page says troid is its affiliate, near the top.
- Each other product the desk sizes: a figure shows only beside a source recorded for that product (never the firm-wide
  one, which would credit one product's source to another), and equals firms.json; anything else is held, with no figure.
- The funded stage and the countries, where a source is recorded; every conflict between the firm's own documents under
  its own heading; every rule change troid logged, with its date.
- claim_check finds nothing on any of them. The words are the generic firm.* strings: no firm's name is in en.json.
- troid's compare links each firm's name to its page.
Reads files only. Spends nothing, calls no one.
"""
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backtest"))
import claim_check  # noqa: E402
import gen_compare  # noqa: E402
import i18n  # noqa: E402
import site_build  # noqa: E402

fails, n = [], 0


def ok(name, cond, info=""):
    global n
    n += 1
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else f"  {str(info)[:500]}"))
    if not cond:
        fails.append(name)


def section(s, sid):
    m = re.search(rf'<section class="fr" id="{sid}">(.*?)</section>', s, re.S)
    return m.group(1) if m else ""


F = gen_compare.FIRMS
T = i18n.Strings("en")
EN = json.loads((ROOT / "web" / "i18n" / "en.json").read_text())
V = json.loads((ROOT / "web" / "vercel.json").read_text())
SITEMAP = (site_build.PUB / "sitemap.xml").read_text()
LLMS = (site_build.PUB / "llms.txt").read_text()
COMPARE = (site_build.PUB / "compare.html").read_text()

ok("one page per firm on troid's compare, each at /firms/<slug>",
   sorted(site_build.FIRM_PAGES.values()) == sorted(gen_compare.ORDER)
   and all(pg == "firms/" + k.replace("_", "-") for pg, k in site_build.FIRM_PAGES.items()), site_build.FIRM_PAGES)
ok("/firms goes to troid's compare, not permanently",
   any(r["source"] == "/firms" and r["destination"] == "/compare" and r["permanent"] is False for r in V["redirects"]), V["redirects"])
names = [F[k]["name"] for k in gen_compare.ORDER]
firm_keys = {k: v for k, v in EN.items() if k.startswith("firm.")}
ok(f"the page's words are the generic firm.* strings ({len(firm_keys)}): no firm named in en.json",
   firm_keys and not [k for k, v in firm_keys.items() if any(nm in v for nm in names)], [k for k, v in firm_keys.items() if any(nm in v for nm in names)])

for page, k in site_build.FIRM_PAGES.items():
    f = F[k]
    path = site_build.out_path("en", page)
    ok(f"{page}: written", path.exists(), path)
    if not path.exists():
        continue
    s = path.read_text()
    FT = site_build.page_T(T, page)
    url = site_build.BASE_URL + site_build.page_url("en", page)
    ok(f"{page}: its title and h1 name the firm, from firms.json", f"<title>{FT(page + '.meta.title')}</title>" in s
       and f["name"] in FT(page + ".meta.title") and re.search(rf"<h1>{re.escape(f['name'])}'s rules</h1>", s) is not None)
    ok(f"{page}: in the sitemap and llms.txt", f"<loc>{url}</loc>" in SITEMAP and f"]({url}): " in LLMS)

    # the rules: the compare column, without its sizing block and its foot
    rows, foot = gen_compare.static_column(gen_compare.js_data(k, f, FT), FT)
    K_ = gen_compare._Kit(FT)
    i, j = rows.index(K_.sec(K_.J["sec_sizing"])), rows.index(K_.sec(K_.J["sec_cost"]))
    rules = section(s, "rules")
    ok(f"{page}: the rules are troid's compare column for {f['name']}, row for row, without the sizing block",
       f'<div class="rows">{rows[:i] + rows[j:]}</div>' in rules and K_.J["sec_sizing"] not in rules and "From your inputs" not in s)
    ok(f"{page}: every rule's value is the compare's, with its provenance line",
       all(m in rules for m in re.findall(r'<div class="r"><div class="rt">.*?</div>(?:<div class="pv">.*?</div>)?</div>', rows[:i])))
    aff = [x for x in (f.get("affiliate_url"), f.get("affiliate_code"), (f.get("affiliate_agreement") or {}).get("customer_code"), "regid=") if x]
    ok(f"{page}: no affiliate link, code or referral id (where a firm's link shows is the owner's call)",
       not any(a in s for a in aff) and foot[:40] not in s, [a for a in aff if a in s])
    disc = FT(f"{page}.disclosure")
    ok(f"{page}: " + ("says troid is its affiliate, near the top" if f.get("affiliate_url") else "no affiliate line: not a partner"),
       (disc in s and s.index(disc) < s.index('id="rules"')) if f.get("affiliate_url") else disc not in s)

    # the other products: a figure only beside that product's own source
    prod = section(s, "products")
    cp = f["compare_product"]["key"]
    shown, held = 0, 0
    for pk, meta in ((f.get("calc") or {}).get("products") or {}).items():
        label = html.escape(T.data(meta.get("label") or pk)).replace('"', "&quot;")
        if pk == cp:
            ok(f"{page}: the compare product ({pk}) isn't repeated among the other products",
               f'<div class="r sec">{label}</div>' not in prod)
            continue
        vals = (f.get("products") or {}).get(pk) or {}
        for x, lab, unit in gen_compare.PRODUCT_FIELDS:
            v = vals.get(x)
            if not isinstance(v, (int, float, str)) or isinstance(v, bool) or v == "":
                continue
            c = gen_compare.cite(f, x, pk, fallback=False)
            if c:
                shown += 1
                val = html.escape(T.data(v)) if isinstance(v, str) else f"{v}{unit}"
                ok(f"{page}: {pk} {x} = {val}, beside the source recorded for {pk} (read {', '.join(c['o'])})",
                   re.search(re.escape(f'<span class="l">{K_.J[lab]}</span><span class="v">{val}</span></div><div class="pv">Computed from {html.escape(f["name"])} {label} rules as published on ') + ".*?" + re.escape(html.escape(c["c"]).replace("&#x27;", "'")), prod) is not None)
            else:
                held += 1
    if held:
        ok(f"{page}: {held} figure(s) with no source for their product held, none shown", prod.count(T("firm.products.held")) == held)
    if k == "bitfunded":
        ok("firms/bitfunded: the Instant's split is held, though the firm-wide split has a source (80%, not the Instant's 60%)",
           re.search(r'Instant</div>.*?<span class="l">' + re.escape(K_.J["row_split"]) + r'</span><span class="v"><span class="pend">', prod, re.S) is not None)

    # the funded stage, the countries, the conflicts, the changes
    more = section(s, "more")
    if gen_compare.cite(f, "trader_stage_rule") and f.get("trader_stage_rule"):
        ok(f"{page}: the funded stage's rule, with its source", html.escape(f["trader_stage_rule"]) in more and "rules as published on" in more)
    cf = f.get("_conflicts_found") or []
    if cf:
        con = section(s, "conflicts")
        ok(f"{page}: its {len(cf)} conflicts under their own heading, each with what troid shows",
           f"<h2>{T('compare.conflicts.h', firm=html.escape(f['name']), n=len(cf))}</h2>" in con and con.count("<li>") == len(cf))
    else:
        ok(f"{page}: no conflicts logged, no conflicts section", 'id="conflicts"' not in s)
    ch = section(s, "changes")
    rc = f.get("rule_changes") or []
    ok(f"{page}: every rule change troid logged ({len(rc)}), each with its date",
       ch.count("<li>") == len(rc) and all(f'<span class="d">{c["date"]}</span>' in ch for c in rc)
       if rc else T("firm.changes.none") in ch)

    # the claim check, and troid's compare linking the page
    found = claim_check.e1_page(page, claim_check.allow_list())
    ok(f"{page}: claim_check finds nothing (every figure with its tier and source)", not found, found)
    ok(f"{page}: troid's compare links {f['name']}'s name to it", f'<a href="/{page}" style="color:inherit">{html.escape(f["name"])}</a>' in COMPARE)

print(f"\n{n - len(fails)} of {n} checks passed" + (f"; FAILED: {fails}" if fails else ""))
sys.exit(1 if fails else 0)
