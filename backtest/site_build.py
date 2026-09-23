#!/usr/bin/env python3
"""Render troid's static pages from web/templates and web/i18n, one copy per published language.

English renders to web/public/{page}.html, exactly as before the pages became templates. Every other
language renders to web/public/{lang}/{page}.html, and only when its file says _status 'live'
(i18n_import.py sets that from the reviewer's sheet). A language that is not live is not published,
not linked, not in hreflang and not in the switcher; its directory is removed if one exists.

  python site_build.py                      # the live languages, into web/public (gen_compare.py calls this)
  python site_build.py --preview OUT        # every language with a file, drafts included, into OUT
  python site_build.py --preview OUT --langs ar,zh

A template asks for strings by key; a key missing from en.json stops the build.
"""
from __future__ import annotations
import argparse
import html
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import i18n  # noqa: E402
import site_text  # noqa: E402
from jinja2 import Environment, FileSystemLoader, StrictUndefined  # noqa: E402

ROOT = HERE.parent
PUB = ROOT / "web" / "public"
TEMPLATES = ROOT / "web" / "templates"
SITE = json.loads((ROOT / "web" / "i18n" / "site.json").read_text())
STATIC = ["index", "faq", "dashboard", "chat", "terms"]   # rendered here; compare, ledger, tearsheet by their generators
PAGES = ["index", "compare", "ledger", "dashboard", "tearsheet", "chat", "faq", "terms"]
BASE_URL = "https://troid.ai"

ENV = Environment(loader=FileSystemLoader(str(TEMPLATES)), autoescape=False, keep_trailing_newline=True,
                  undefined=StrictUndefined)


def targets(preview=False, only=None):
    """The languages to render: live ones, or in a preview every language that has a file."""
    codes = [l["code"] for l in i18n.LANGS if l["code"] == "en" or
             (i18n.load(l["code"])[0].get("_status") in (("live", "draft") if preview else ("live",)))]
    return [c for c in codes if not only or c in only]


def out_path(code, page, out=None):
    base = Path(out) if out else PUB
    name = "index.html" if page == "index" else f"{page}.html"
    return base / name if code == "en" else base / code / name


def page_url(code, page):
    """The public path of a page in a language: /compare, /zh/compare, /, /zh."""
    if page == "index":
        return "/" if code == "en" else f"/{code}"
    return f"/{page}" if code == "en" else f"/{code}/{page}"


def features_on(T):
    """The i18n reading aids (local time beside UTC, Intl formatting, the country selector) show on
    translated pages, and on English once site.json turns them on (launch day)."""
    return T.code != "en" or bool(SITE.get("english_features"))


RUNTIME_KEYS = {"country_label": "common.country.label", "country_unset": "common.country.unset",
                "country_note": "common.country.note", "avail_excluded": "common.avail.excluded",
                "avail_platform": "common.avail.platform", "avail_not_recorded": "common.avail.not_recorded",
                "avail_not_excluded": "common.avail.not_excluded", "time_local": "common.time.local",
                "share": "common.share", "share_copied": "common.share.copied", "share_line": "share.line"}


def availability(T):
    """Each firm's recorded country exclusions (firms.json 'availability'), for the country selector, with the
    firm's own note where troid recorded one (Bitfunded: its Terms list no countries; 4(b) puts local law on the
    trader), translated by content like other firm text."""
    F = json.loads((ROOT / "firms.json").read_text())
    out = {}
    for k, f in F.items():
        if k.startswith("_") or not isinstance(f, dict) or not f.get("availability"):
            continue
        a = f["availability"]
        out[k] = {"recorded": bool(a.get("recorded")), "excluded": a.get("excluded") or [],
                  "platform": a.get("platform") or {}}
        if a.get("note"):
            out[k]["note"] = T.data(a["note"])
    return out


def runtime(T):
    """window.TROID for web/public/i18n.js: the locale, the strings it shows, the availability record. Loaded in
    the head, before the page's own scripts, so they can format with TROID.usd / TROID.num."""
    cfg = {"code": T.code, "loc": T.lang["intl"], "t": {n: T(k) for n, k in RUNTIME_KEYS.items()},
           "avail": availability(T)}
    return ('<script>window.TROID=' + json.dumps(cfg, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
            + ';</script>\n<script src="/i18n.js"></script>')


def head_extra(T, page, live):
    """The page's canonical URL on troid.ai (and og:url), then hreflang alternates, the language's og tags and
    font. The alternates, og locale, font and i18n.css appear on English only once a second language is live."""
    lang = T.lang
    url = BASE_URL + page_url(T.code, page)
    parts = [f'<link rel="canonical" href="{url}">', f'<meta property="og:url" content="{url}">']
    if len(live) > 1:
        for c in live:
            parts.append(f'<link rel="alternate" hreflang="{c}" href="{BASE_URL}{page_url(c, page)}">')
        parts.append(f'<link rel="alternate" hreflang="x-default" href="{BASE_URL}{page_url("en", page)}">')
    if T.code != "en":
        parts.append(f'<meta property="og:locale" content="{lang["og_locale"]}">')
        for c in live:
            if c != T.code:
                parts.append(f'<meta property="og:locale:alternate" content="{i18n.BY_CODE[c]["og_locale"]}">')
    if lang.get("font"):
        fam = lang["font"].replace(" ", "+")
        parts.append(f'<link href="https://fonts.googleapis.com/css2?family={fam}:wght@400;500;600;700&display=swap" rel="stylesheet">')
        parts.append('<style>:root{--sans:"Inter","' + lang["font"] + '",ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}</style>')
    if T.code != "en" or len(live) > 1 or features_on(T):
        parts.append('<link rel="stylesheet" href="/i18n.css">')   # switcher, governing line, RTL details
    if features_on(T):
        parts.append(runtime(T))
    return "".join(p + "\n" for p in parts)


def og(T):
    """og:image / og:title / og:description for this language."""
    has = (PUB / "og" / f"{T.code}.png").exists()     # gen_og.py renders it (English too; a language when it goes live)
    img = f"{BASE_URL}/og/{T.code}.png" if has else f"{BASE_URL}/og-image.png"
    return {"image": img, "title": T.attr("og.title"), "description": T.attr("og.description")}


def switcher(T, page, live):
    """Each published language, named in its own script. Nothing while only English is published."""
    if len(live) < 2:
        return ""
    items = []
    for c in live:
        name = html.escape(i18n.BY_CODE[c]["name"])
        if c == T.code:
            items.append(f'<span class="lang-cur" lang="{c}" aria-current="true">{name}</span>')
        else:
            items.append(f'<a href="{page_url(c, page)}" hreflang="{c}" lang="{c}">{name}</a>')
    share = f' <button type="button" class="share" data-share>{T("common.share")}</button>' if features_on(T) else ""
    return (f'\n    <span class="langs" aria-label="{T.attr("common.languages")}">' + " · ".join(items) + "</span>"
            + share)


def mark(T):
    """The tr●id wordmark, the same on every page. "tr" and "id" link home; the dot is troid's status light and
    links to troid's ledger. It holds still until /live.js reads /status.json and finds both the last shadow run and
    the last bar inside the windows that file states, then it ripples. Its label is neutral until then. Pinned left to right on a translated page (.mark is inline-flex, so a
    right-to-left page would otherwise read id·tr)."""
    ltr = "" if T.code == "en" else ' dir="ltr"'
    return (f'<span class="mark"{ltr} translate="no"><a href="{T.H}" aria-label="{T.attr("common.mark.home")}">tr</a>'
            f'<a class="dot" href="{T.L}/ledger" aria-label="{T.attr("common.mark.ledger")}" title="{T.attr("common.mark.ledger")}"'
            f' data-live="{T.attr("common.mark.live")}" data-still="{T.attr("common.mark.still")}" data-unknown="{T.attr("common.mark.unknown")}"></a>'
            f'<a href="{T.H}" tabindex="-1" aria-hidden="true">id</a></span><script src="/live.js" defer></script>')


def html_attrs(T):
    return f' lang="{T.code}"' + ("" if T.code == "en" else f' dir="{T.lang["dir"]}"')


def common(T, page, live, preview=False):
    """What every template gets."""
    return {"t": T, "T": T, "code": T.code, "lang": T.lang, "dir": T.lang["dir"], "L": T.L, "H": T.H, "page": page,
            "html_attrs": html_attrs(T), "head_extra": head_extra(T, page, live), "og": og(T),
            "switcher": switcher(T, page, live), "mark": mark(T), "features": features_on(T), "live": live, "preview": preview,
            "footer": site_text.footer_html(T), "governs": governs_html(T),
            "governs_for": lambda key=None: governs_html(T, key),
            "intl": T.lang["intl"], "site_text": site_text,
            "country_box": country_box(T), "avail_attr": avail_attr(T)}


def country_box(T):
    """Where i18n.js puts the country selector (compare page, firms panel). Nothing where the features are off."""
    return '<div class="country" data-country></div>' if features_on(T) else ""


def avail_attr(T):
    """A function for templates and generators: the data-avail attribute for a firm's block, or nothing."""
    return (lambda key: f' data-avail="{key}"') if features_on(T) else (lambda key: "")


def governs_html(T, summary_key=None):
    """On a translated page, before English legal text or quotation: a one-line summary in the reader's
    language, then 'This translation is provided for convenience. The English version governs.'"""
    if site_text._english(T):
        return ""
    s = f'<span class="gov-sum">{T(summary_key)}</span> ' if summary_key else ""
    return f'<p class="governs">{s}<span class="gov-line">{T("legal.governs")}</span></p>'


def render(template, T, page, live, preview=False, **extra):
    ctx = common(T, page, live, preview)
    ctx.update(extra)
    return ENV.get_template(template).render(**ctx)


def extra_context(T):
    """Generated fragments the static templates embed (from gen_compare), imported lazily so this module
    stays importable by the generators themselves."""
    import regions
    return regions.template_context(T)


GENERATED = {"compare": ("gen_compare", "render_compare"), "ledger": ("gen_ledger", "render_ledger"),
             "tearsheet": ("gen_tearsheet", "render_stub")}


def render_page(page, T, live, preview=False, ctx=None):
    """One page in T's language as HTML, or None where there is nothing to render yet (a page still waiting
    for its template, or the English tearsheet, which quantstats writes). The generators' own mains write their
    pages for every live language; the checks (i18n_equiv.py, i18n_pseudo.py) and previews come through here."""
    if page in STATIC:
        if not (TEMPLATES / f"{page}.html").exists():
            return None
        return render(f"{page}.html", T, page, live, preview, **(ctx if ctx is not None else extra_context(T)))
    if page == "tearsheet" and T.code == "en" and not getattr(T, "pseudo", False):
        return None
    mod_name, fn_name = GENERATED[page]
    fn = getattr(__import__(mod_name), fn_name, None)
    return fn(T, live) if fn else None


def render_static(codes, out=None, preview=False):
    live = targets(preview=preview) if preview else targets()
    written = []
    for code in codes:
        T = i18n.Strings(code, fallback=preview)
        ctx = extra_context(T)
        for page in STATIC:
            if not (TEMPLATES / f"{page}.html").exists():
                continue                                    # not converted yet: the page in public/ stays as it is
            p = out_path(code, page, out)
            p.parent.mkdir(parents=True, exist_ok=True)
            text = render(f"{page}.html", T, page, live, preview, **ctx)
            if not p.exists() or p.read_text() != text:
                p.write_text(text)
                written.append(str(p.relative_to(out if out else PUB)))
        if T.missing:
            print(f"  {code}: {len(T.missing)} string(s) fell back to English (draft preview)")
    return written


def write_seo(out=None):
    """robots.txt (allow all, with the sitemap line) and sitemap.xml: every published page in every live language,
    with its hreflang alternates once a second language is live. Written with each build."""
    base = Path(out) if out else PUB
    live = targets()
    urls = []
    for code in live:
        for page in PAGES:
            if not out_path(code, page, out).exists() and not (code == "en" and page == "tearsheet"):
                continue
            alts = ""
            if len(live) > 1:
                alts = "".join(f'\n    <xhtml:link rel="alternate" hreflang="{c}" href="{BASE_URL}{page_url(c, page)}"/>' for c in live)
                alts += f'\n    <xhtml:link rel="alternate" hreflang="x-default" href="{BASE_URL}{page_url("en", page)}"/>'
            urls.append(f"  <url>\n    <loc>{BASE_URL}{page_url(code, page)}</loc>{alts}\n  </url>")
    sitemap = ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
               'xmlns:xhtml="http://www.w3.org/1999/xhtml">\n' + "\n".join(urls) + "\n</urlset>\n")
    robots = f"User-agent: *\nAllow: /\n\nSitemap: {BASE_URL}/sitemap.xml\n"
    written = []
    for name, text in (("sitemap.xml", sitemap), ("robots.txt", robots)):
        f = base / name
        if not f.exists() or f.read_text() != text:
            f.write_text(text); written.append(name)
    return written


def prune(out=None):
    """Remove the directory of any language that is not live, so an unpublished language is not served."""
    base = Path(out) if out else PUB
    live = set(targets())
    gone = []
    for l in i18n.LANGS:
        d = base / l["code"]
        if l["code"] != "en" and l["code"] not in live and d.is_dir():
            shutil.rmtree(d)
            gone.append(l["code"])
        og_png = base / "og" / f"{l['code']}.png"
        if l["code"] != "en" and l["code"] not in live and og_png.exists():
            og_png.unlink()                          # its share image goes with it
    return gone


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", metavar="OUT", help="render drafts too, into OUT (never web/public)")
    ap.add_argument("--langs", help="comma-separated codes")
    a = ap.parse_args()
    only = a.langs.split(",") if a.langs else None
    if a.preview:
        out = Path(a.preview).resolve()
        if out == PUB.resolve() or PUB.resolve() in out.parents:
            sys.exit("--preview must not write into web/public")
        codes = targets(preview=True, only=only)
        w = render_static(codes, out, preview=True)
        live = targets(preview=True)
        for code in codes:
            T = i18n.Strings(code, fallback=True)
            for page in GENERATED:
                text = render_page(page, T, live, preview=True)
                if text is not None:
                    q = out_path(code, page, out); q.parent.mkdir(parents=True, exist_ok=True); q.write_text(text)
                    w.append(str(q.relative_to(out)))
        for f in PUB.iterdir():                     # assets, so the preview serves as a site
            if f.is_file() and f.suffix != ".html" and not (out / f.name).exists():
                shutil.copy(f, out / f.name)
    else:
        w = render_static(targets(only=only))
        gone = prune()
        w += write_seo()
        if gone:
            print(f"removed unpublished language directories: {gone}")
    print(f"site_build: {len(w)} page(s) written" + (f": {w}" if w and len(w) < 12 else ""))


if __name__ == "__main__":
    main()
