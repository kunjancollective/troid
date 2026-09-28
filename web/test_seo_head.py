#!/usr/bin/env python3
"""What a search engine, an AI crawler or a shared link reads in each page's head (launch handoff 2026-09-26, 5.1
items 2 and 3), for the published English pages and every language rendered with drafts (site_build.py --preview).

  python web/test_seo_head.py

- Every page: one canonical URL on troid.ai and og:url equal to it, og:type, og:site_name troid, the X card
  (summary_large_image) and twitter:site @tradingdroid, each exactly once; the tearsheet included.
- Every page: one JSON-LD block that parses, an @graph with troid as an Organization whose sameAs are exactly the
  footer's repo, X and Reddit links, and the WebSite; the page's own entity where it has one: the desk a free
  WebApplication, the FAQ a FAQPage, the ledger a Dataset described as simulated with the journal as CSV, the
  research page an Article, the sources a CollectionPage listing every source in sources.json.
- The FAQPage holds each question the page shows, in order, with the answer's text as the page shows it.
- Nothing in the JSON-LD can close its script early, and no string in it carries a tag.
Reads files only. Spends nothing, calls no one.
"""
import json
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backtest"))
import site_build  # noqa: E402
import site_text  # noqa: E402
import sources  # noqa: E402

fails, n = [], 0


def ok(name, cond, info=""):
    global n
    n += 1
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else f"  {str(info)[:500]}"))
    if not cond:
        fails.append(name)


SOCIAL = [u for u, _ in site_text.LINKS if u.startswith("https://")]
PAGE_TYPE = {"index": "WebApplication", "faq": "FAQPage", "ledger": "Dataset", "dashboard": "Article", "sources": "CollectionPage"}


def strings(x):
    if isinstance(x, str):
        yield x
    elif isinstance(x, dict):
        for v in x.values():
            yield from strings(v)
    elif isinstance(x, list):
        for v in x:
            yield from strings(v)


def check(label, path, code, page):
    s = path.read_text()
    head = s[:s.find("</head>")]
    url = site_build.BASE_URL + site_build.page_url(code, page)
    for tag, pat in (("canonical", rf'<link rel="canonical" href="{re.escape(url)}">'),
                     ("og:url", rf'<meta property="og:url" content="{re.escape(url)}">'),
                     ("og:type", r'<meta property="og:type" content="website">'),
                     ("og:site_name", r'<meta property="og:site_name" content="troid">'),
                     ("twitter:card", r'<meta name="twitter:card" content="summary_large_image">'),
                     ("twitter:site", r'<meta name="twitter:site" content="@tradingdroid">')):
        name = tag.split(":")[-1] if tag.startswith(("og:", "twitter:")) else tag
        count = len(re.findall(r'(?:property|name|rel)="' + re.escape(tag) + '"', head))
        ok(f"{label}: {tag} once, as it should read", count == 1 and re.search(pat, head) is not None, f"{count} × {name}")
    blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', s, re.S)
    ok(f"{label}: one JSON-LD block, in the head", len(blocks) == 1 and blocks[0] in head, len(blocks))
    if not blocks:
        return
    try:
        d = json.loads(blocks[0])
    except ValueError as e:
        ok(f"{label}: the JSON-LD parses", False, e)
        return
    g = {x["@type"]: x for x in d.get("@graph", [])}
    org = g.get("Organization") or {}
    ok(f"{label}: troid as an Organization, sameAs the footer's repo, X and Reddit links",
       d.get("@context") == "https://schema.org" and org.get("name") == "troid" and org.get("sameAs") == SOCIAL, org)
    ok(f"{label}: the WebSite, published by troid", (g.get("WebSite") or {}).get("publisher", {}).get("@id") == org.get("@id"))
    want = PAGE_TYPE.get(page)
    ok(f"{label}: the page's own entity ({want or 'none beyond the two'})",
       set(g) == {"Organization", "WebSite"} | ({want} if want else set()), sorted(g))
    ok(f"{label}: no string closes the script or carries a tag",
       "</" not in blocks[0] and not any(re.search(r"<[a-zA-Z/][^>]*>", x) for x in strings(d)))
    e = g.get(want) if want else None
    if want == "WebApplication":
        ok(f"{label}: the desk is free (an offer at 0 USD) and needs only a browser",
           e.get("isAccessibleForFree") is True and e.get("offers", {}).get("price") == "0" and e.get("url") == url, e)
    elif want == "Dataset":
        dist = (e.get("distribution") or [{}])[0]
        ok(f"{label}: the ledger's Dataset says it is simulated, and hypothetical",
           e.get("description", "").startswith("Simulated") and "no money is traded" in e.get("description", ""), e.get("description"))
        ok(f"{label}: the Dataset's download is the journal, as CSV, from the public repo",
           dist.get("encodingFormat") == "text/csv" and dist.get("contentUrl", "").endswith("/main/backtest/journal.csv"), dist)
    elif want == "Article":
        ok(f"{label}: the research page's Article has its headline, author and image",
           e.get("headline") and e.get("author", {}).get("@id") == org.get("@id") and e.get("image", "").startswith("https://troid.ai/"), e)
    elif want == "CollectionPage":
        items = e.get("mainEntity", {}).get("itemListElement", [])
        ok(f"{label}: the sources page lists every source in sources.json, with its link",
           [i["item"].get("url") for i in items] == [x.get("url") for x in sources.SOURCES.values()] and len(items) == len(sources.SOURCES), items)
    elif want == "FAQPage":
        shown = site_build.faq_pairs(s)
        qs = e.get("mainEntity", [])
        heads = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", h)).strip()
                 for h in re.findall(r'<div class="q"[^>]*>\s*<h[23][^>]*>(.*?)</h[23]>', s, re.S)]
        ok(f"{label}: the FAQPage holds each question the page shows, in order ({len(heads)})",
           [q["name"] for q in qs] == heads and len(heads) >= 10, ([q["name"] for q in qs][:3], heads[:3]))
        ok(f"{label}: each answer is the page's own text, its source line included",
           [q["acceptedAnswer"]["text"] for q in qs] == [a for _, a in shown] and all(len(a) > 40 for _, a in shown))


def main():
    for page in site_build.PAGES:
        check(f"en {page}", site_build.out_path("en", page), "en", page)
    out = tempfile.TemporaryDirectory()
    import subprocess
    subprocess.run([sys.executable, str(ROOT / "backtest" / "site_build.py"), "--preview", out.name], check=True,
                   capture_output=True)
    for code in site_build.targets(preview=True):
        if code == "en":
            continue
        for page in site_build.PAGES:
            p = site_build.out_path(code, page, out.name)
            if p.exists():
                check(f"{code} {page}", p, code, page)
    print(f"\n{n - len(fails)} of {n} checks passed" + (f"; FAILED: {fails}" if fails else ""))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
