#!/usr/bin/env python3
"""What a search engine, an AI crawler or a shared link reads in each page's head (launch handoff 2026-09-26, 5.1
items 2 and 3), for the published English pages and every language rendered with drafts (site_build.py --preview).

  python web/test_seo_head.py

- Every page: one meta description, its own ({page}.meta.description, else the line it previews with when shared;
  no two pages share one), one canonical URL on troid.ai and og:url equal to it, og:type, og:site_name troid, the X card
  (summary_large_image) and twitter:site @tradingdroid, each exactly once; the tearsheet included.
- Every page: one JSON-LD block that parses, an @graph with troid as an Organization whose sameAs are exactly the
  footer's repo, X and Reddit links, and the WebSite; the page's own entity where it has one: the desk a free
  WebApplication, the FAQ a FAQPage, the ledger a Dataset described as simulated with the journal as CSV, the
  research page an Article, the sources a CollectionPage listing every source in sources.json.
- The FAQPage holds each question the page shows, in order, with the answer's text as the page shows it.
- Nothing in the JSON-LD can close its script early, and no string in it carries a tag.

And the rest of 5.1 (items 5 to 8):
- /llms.txt: troid's summary, the footer's disclosure, a line for every page with its address and its own description
  (the ledger's "Simulated: …"), the files for assistants; every troid.ai address in it is a file the site serves.
- The footer links /sources on every page; /research redirects to /dashboard, permanently (vercel.json).
- sitemap.xml: every page with a lastmod, no later than today; a change to a page's text moves it to today, a change to
  its head or to nothing keeps it; the page for an address with no page is not in it.
- /404.html: noindex, no canonical, a link to each page it lists, every one a page the site serves; English only.
- Headings: one h1 on every page; the FAQ's sections h2 and its questions and disclaimers h3, no level skipped; the
  ledger's h1 is its name, troid's ledger.
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
PAGE_TYPE = {"index": "WebApplication", "faq": "FAQPage", "ledger": "Dataset", "dashboard": "Article", "sources": "CollectionPage",
             **{pg: "WebPage" for pg in site_build.FIRM_PAGES}}


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
    T = site_build.page_T(site_build.i18n.Strings(code, fallback=True), page)
    desc = T.attr(site_build.description_key(T, page))
    ok(f"{label}: one meta description, the page's own ({site_build.description_key(T, page)})",
       head.count('name="description"') == 1 and f'<meta name="description" content="{desc}">' in head)
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
    elif want == "WebPage":
        firm = site_build.FIRMS_JSON[site_build.FIRM_PAGES[page]]["name"]
        ok(f"{label}: a firm's page is about the firm, by name, part of troid's site",
           e.get("about") == {"@type": "Organization", "name": firm} and e.get("url") == url and firm in e.get("name", "")
           and e.get("isPartOf", {}).get("@id") == site_build.BASE_URL + "/#website", e)
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


def served(href):
    """A troid.ai address as web/public serves it (cleanUrls): a page, or a file; or a published page a function serves
    (site_build.PRIVATE: /pro, which vercel.json rewrites to web/api/pro/page.js, with its rendered page)."""
    path = href.replace(site_build.BASE_URL, "", 1).split("#")[0].split("?")[0] or "/"
    if path == "/":
        return (site_build.PUB / "index.html").exists()
    name = path.strip("/")
    if name in site_build.PRIVATE:
        V = json.loads((ROOT / "web" / "vercel.json").read_text())
        fn = next((r["destination"] for r in V.get("rewrites", []) if r["source"] == path), "").split("?")[0]
        return site_build.published(name) and site_build.PRIVATE[name].is_file() and fn.startswith("/api/") \
            and (ROOT / "web" / (fn.lstrip("/") + ".js")).is_file()
    f = site_build.PUB / path.lstrip("/")
    return f.is_file() or f.with_suffix(".html").is_file() or (f / "index.html").is_file()


def levels(s):
    return [int(x) for x in re.findall(r"<h([1-6])\b", s[s.find("<body"):])]


def rest():
    T = site_build.i18n.Strings("en")
    # ---------------------------------------------------------------- descriptions (5.1 item 1)
    D = {pg: re.search(r'<meta name="description" content="([^"]*)">', site_build.out_path("en", pg).read_text()) for pg in site_build.PAGES}
    ok("descriptions: every page has one, and no two pages share one",
       all(D.values()) and len({m.group(1) for m in D.values()}) == len(D), {k: bool(v) for k, v in D.items()})

    # ---------------------------------------------------------------- llms.txt
    L = (site_build.PUB / "llms.txt").read_text()
    ok("llms.txt: a title, then troid's summary as its blockquote",
       L.startswith("# troid\n\n> ") and site_build._plain(T("index.meta.description")) in L.split("\n")[2])
    ok("llms.txt: the footer's disclosure, word for word", site_text.FOOTER_TEXT in L)
    for page in site_build.PAGES:
        url = site_build.BASE_URL + site_build.page_url("en", page)
        m = re.search(r"^- \[[^\]]+\]\(" + re.escape(url) + r"\): (.+)$", L, re.M)
        ok(f"llms.txt: {page} listed at {url} with a line of its own", m is not None and len(m.group(1)) > 30)
    ok("llms.txt: the ledger's line says it is simulated",
       re.search(r"\(https://troid\.ai/ledger\): Simulated: ", L) is not None)
    links = re.findall(r"\]\((https://troid\.ai[^)]*)\)", L)
    ok(f"llms.txt: every troid.ai address in it is served ({len(links)})", links and all(served(u) for u in links),
       [u for u in links if not served(u)])
    ok("llms.txt: TROID.md, the MCP server and METHODOLOGY.md for assistants",
       all(x in L for x in ("(https://troid.ai/TROID.md)", "/tree/main/mcp)", "(https://troid.ai/METHODOLOGY.md)")))
    ok("llms.txt: troid's accounts, as the footer links them", all(f"({u})" in L for u in SOCIAL))
    ok("llms.txt: written by the build (site_build.llms_txt), unedited", L == site_build.llms_txt())

    # ---------------------------------------------------------------- footer and redirect
    for page in site_build.PAGES:
        f = site_build.out_path("en", page)
        ok(f"footer: {page} links /sources", '<a href="/sources">sources</a>' in f.read_text())
    V = json.loads((ROOT / "web" / "vercel.json").read_text())
    ok("vercel.json: /research redirects to /dashboard, permanently",
       {"source": "/research", "destination": "/dashboard", "permanent": True} in V.get("redirects", []))

    # ---------------------------------------------------------------- sitemap lastmod
    X = (site_build.PUB / "sitemap.xml").read_text()
    today = site_build.datetime.now(site_build.timezone.utc).date().isoformat()
    marks = site_build.LASTMOD.findall(X)
    locs = re.findall(r"<loc>([^<]+)</loc>", X)
    ok(f"sitemap: every page has a lastmod no later than today ({len(locs)})",
       len(marks) == len(locs) == len(site_build.PAGES) + sum(map(site_build.published, site_build.PRIVATE))
       and all(d <= today for _, d, _ in marks), marks)
    ok("sitemap: the page for an address with no page is not in it", not any("404" in u for u in locs))
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        for f in site_build.PUB.glob("*.html"):
            (d / f.name).write_bytes(f.read_bytes())
        (d / "sitemap.xml").write_text(re.sub(r"<lastmod>\d{4}-\d{2}-\d{2}</lastmod>", "<lastmod>2026-01-02</lastmod>", X))
        site_build.write_seo(d, today="2026-09-30")
        kept = dict((u, m) for u, m, _ in site_build.LASTMOD.findall((d / "sitemap.xml").read_text()))
        ok("sitemap: nothing changed, every lastmod kept", set(kept.values()) == {"2026-01-02"}, kept)
        faq = (d / "faq.html").read_text()
        (d / "faq.html").write_text(faq.replace("<title>", '<meta name="x-test" content="head only"><title>', 1))
        site_build.write_seo(d, today="2026-09-30")
        kept = dict((u, m) for u, m, _ in site_build.LASTMOD.findall((d / "sitemap.xml").read_text()))
        ok("sitemap: a change to a page's head keeps its lastmod", kept["https://troid.ai/faq"] == "2026-01-02", kept)
        (d / "faq.html").write_text(faq.replace("</h1>", " (a test edit)</h1>", 1))
        site_build.write_seo(d, today="2026-09-30")
        kept = dict((u, m) for u, m, _ in site_build.LASTMOD.findall((d / "sitemap.xml").read_text()))
        ok("sitemap: a change to a page's text moves its lastmod to today, and only its",
           kept["https://troid.ai/faq"] == "2026-09-30" and sum(v == "2026-09-30" for v in kept.values()) == 1, kept)

    # ---------------------------------------------------------------- 404
    N = (site_build.PUB / "404.html").read_text()
    nh = N[:N.find("</head>")]
    ok("404: noindex, and no canonical or og:url of its own",
       '<meta name="robots" content="noindex">' in nh and 'rel="canonical"' not in nh and 'property="og:url"' not in nh)
    hrefs = re.findall(r'<ul class="pages">(.*?)</ul>', N, re.S)
    hrefs = re.findall(r'href="([^"]+)"', hrefs[0]) if hrefs else []
    ok(f"404: lists the pages, each one served ({len(hrefs)})",
       set(hrefs) >= {"/", "/compare", "/ledger", "/dashboard", "/chat", "/faq", "/sources"} and all(served(h) for h in hrefs), hrefs)
    ok("404: one h1, and the footer", levels(N).count(1) == 1 and site_text.FOOTER_TEXT in site_build.html.unescape(N))

    # ---------------------------------------------------------------- headings
    for page in site_build.PAGES:
        f = site_build.out_path("en", page)
        if page == "tearsheet":
            continue                                        # quantstats' report: troid's box sits above it, no h1 of troid's
        lv = levels(f.read_text())
        ok(f"headings: {page} has one h1", lv.count(1) == 1, lv)
    F = (site_build.PUB / "faq.html").read_text()
    lv = levels(F)
    ok("headings: the FAQ's sections are h2, its questions and disclaimers h3, no h4",
       F.count('<h2 class="sec">') == 4 and len(re.findall(r'<div class="q"[^>]*>\s*<h3>', F)) >= 10 and 4 not in lv, lv)
    ok("headings: the FAQ skips no level going down", all(b - a <= 1 for a, b in zip(lv, lv[1:])), lv)
    G = (site_build.PUB / "ledger.html").read_text()
    h1 = re.findall(r"<h1[^>]*>(.*?)</h1>", G, re.S)
    ok("headings: the ledger's h1 is its name, troid's ledger", h1 == [T("product.ledger")], h1)


def pro_waitlist():
    """troid Pro's waitlist (launch handoff 6.4 step 1), published while site.json pro_waitlist is true (gate 0, Vercel's
    plan, cleared 2026-09-28): the FAQ's "Will troid charge?" and its FAQPage entry, the Terms' waitlist paragraph,
    /pro in the sitemap and llms.txt, and claim_check finding nothing; false takes every one of them down again. The
    committed pages must match site.json, and the other state is rendered here to prove the switch works both ways."""
    import claim_check
    T = site_build.i18n.Strings("en")
    on = bool(site_build.SITE.get("pro_waitlist"))
    ok("the waitlist page is rendered for the function only, never into web/public",
       not (site_build.PUB / "pro.html").exists() and site_build.PRIVATE["pro"].exists())

    def state(d):
        faq, terms, X, L = ((d / f).read_text() for f in ("faq.html", "terms.html", "sitemap.xml", "llms.txt"))
        return {"faq": re.search(r'<div class="q" id="charge">\s*<h3>Will troid charge\?</h3>', faq) is not None
                and 'href="/pro"' in faq and "$19/month or $190/year, tax included" in faq,
                "faq_ld": '"name":"Will troid charge?"' in faq[:faq.find("</head>")],
                "terms": re.search(r'<p id="waitlist">troid Pro\'s waitlist, at <a href="/pro">', terms) is not None
                and "one year after you last joined" in terms,
                "sitemap": re.search(r"<loc>https://troid\.ai/pro</loc>\s*<lastmod>\d{4}-\d\d-\d\d</lastmod>", X) is not None,
                "llms": re.search(r"^- \[troid Pro\]\(https://troid\.ai/pro\): .{30,}$", L, re.M) is not None}

    pub = state(site_build.PUB)
    ok(f"web/public matches site.json (pro_waitlist {on}): the FAQ entry and its structured data, the Terms' paragraph, "
       "/pro in the sitemap and llms.txt all " + ("there" if on else "absent"), all(v == on for v in pub.values()), pub)
    site_build.SITE["pro_waitlist"] = not on
    try:
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            for f in site_build.PUB.glob("*.html"):
                (d / f.name).write_bytes(f.read_bytes())
            for page in ("faq", "terms"):
                (d / f"{page}.html").write_text(site_build.render(f"{page}.html", T, page, ["en"], False,
                                                                  **site_build.extra_context(T)))
            site_build.write_seo(d, today="2026-10-06")
            other = state(d)
            ok(f"pro_waitlist {not on}, rendered: every one of them " + ("there" if not on else "absent"),
               all(v == (not on) for v in other.values()), other)
            shown = site_build.PUB if on else d
            claim_check.PUB = shown
            found = claim_check.e1_page("faq", claim_check.allow_list()) + claim_check.e1_page("terms", claim_check.allow_list())
            ok("published: claim_check finds nothing on the FAQ or the Terms (the price is troid's own offer, allow-listed "
               "with its reason)", not found, found)
    finally:
        site_build.SITE["pro_waitlist"] = on
        claim_check.PUB = site_build.PUB


def main():
    rest()
    pro_waitlist()
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
