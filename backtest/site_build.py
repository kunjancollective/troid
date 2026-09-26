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
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import i18n  # noqa: E402
import site_text  # noqa: E402
import sources  # noqa: E402
from jinja2 import Environment, FileSystemLoader, StrictUndefined  # noqa: E402

ROOT = HERE.parent
PUB = ROOT / "web" / "public"
TEMPLATES = ROOT / "web" / "templates"
SITE = json.loads((ROOT / "web" / "i18n" / "site.json").read_text())
STATIC = ["index", "faq", "dashboard", "chat", "terms", "sources"]   # rendered here; compare, ledger, tearsheet by their generators
PAGES = ["index", "compare", "ledger", "dashboard", "tearsheet", "chat", "faq", "terms", "sources"]
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


def og(T, page=None):
    """og:image / og:title / og:description for this language and page. A page with its own {page}.og.title in en.json
    previews as itself when shared; the desk, and any page without, uses the site's og.title and og.description."""
    has = (PUB / "og" / f"{T.code}.png").exists()     # gen_og.py renders it (English too; a language when it goes live)
    img = f"{BASE_URL}/og/{T.code}.png" if has else f"{BASE_URL}/og-image.png"
    key = f"{page}.og" if page and f"{page}.og.title" in T.en else "og"
    return {"image": img, "title": T.attr(key + ".title"), "description": T.attr(key + ".description")}


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


WORDMARK = json.loads((HERE / "wordmark_paths.json").read_text())


MARK_LINE = 1600     # the page's line height, 1.6, in font units: the line box the text wordmark sat in


def _letters(d):
    """A pair of the wordmark's letters as an SVG (backtest/wordmark.py): no font to wait for, so nothing moves when
    the page's fonts arrive (design handoff 2026-09-24, 1c). The box is the one the text had: Plex Mono's ascent and
    descent with half the 1.6 line height's leading on each side, 1.175em above the baseline and .425em below."""
    lead = (MARK_LINE - WORDMARK["ascent"] - WORDMARK["descent"]) // 2
    return (f'<svg viewBox="0 -{WORDMARK["ascent"] + lead} {WORDMARK["width"]} {MARK_LINE}" aria-hidden="true" focusable="false">'
            f'<path d="{d}"/></svg>')


def status_now(now=None):
    """The status light's state as web/public/status.json gives it at build time, by live.js's own rule:
    ("live" | "still" | "unknown", the minute its label names). The shadow run writes status.json before the pages
    render, so the dot is right on first paint; live.js only confirms or corrects it."""
    from datetime import datetime, timedelta, timezone
    try:
        s = json.loads((PUB / "status.json").read_text())
        run = datetime.fromisoformat(s["last_run_utc"])
        bar = datetime.fromisoformat(s["as_of_bar_utc"]) + timedelta(minutes=float(s.get("bar_minutes") or 0))
    except (OSError, ValueError, KeyError, TypeError):
        return "unknown", None
    now = now or datetime.now(timezone.utc)
    run_age, bar_age = (now - run).total_seconds() / 60, (now - bar).total_seconds() / 60
    stale = float(s["stale_after_minutes"])
    live = -30 < run_age <= stale and bar_age <= float(s.get("bar_stale_after_minutes") or stale)
    when = run if live else min(run, bar)
    return ("live" if live else "still"), when.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M")


def mark(T):
    """The tr●id wordmark, the same on every page. "tr" and "id" link home; the dot is troid's status light and
    links to troid's ledger. It ripples while the last shadow run and the last bar sit inside the windows
    /status.json states, and holds still otherwise: the state is written here from status.json at build time
    (status_now), then checked by /live.js, which fades any change and writes the label with its time (neutral until
    then). The letters are SVG paths (_letters). Pinned left to right on a
    translated page (.mark is inline-flex, so a right-to-left page would otherwise read id·tr)."""
    ltr = "" if T.code == "en" else ' dir="ltr"'
    # only the state is baked in, never its time: live.js writes the label, so a shadow run that leaves the state as it
    # was leaves every page's bytes as they were (the owner, after the first build carried the run's minute)
    state, _ = status_now()
    label = T.attr("common.mark.ledger")
    return (f'<span class="mark"{ltr} translate="no"><a class="wm" href="{T.H}" aria-label="{T.attr("common.mark.home")}">'
            f'{_letters(WORDMARK["tr"])}</a>'
            f'<a class="dot{" live" if state == "live" else ""}" href="{T.L}/ledger" aria-label="{label}" title="{label}"'
            f' data-live="{T.attr("common.mark.live")}" data-still="{T.attr("common.mark.still")}" data-unknown="{T.attr("common.mark.unknown")}">'
            f'<i class="rp"></i></a>'
            f'<a class="wm" href="{T.H}" tabindex="-1" aria-hidden="true">{_letters(WORDMARK["id"])}</a></span>'
            f'<script src="/live.js" defer></script>')


def _ticker_spec():
    """The symbols and source web/api/ticker.js serves, read from that file, so the strip and the API can't disagree."""
    import re
    js = (ROOT / "web" / "api" / "ticker.js").read_text()
    syms = re.findall(r'\["([A-Z]+)", "[A-Z]+USDT"\]', js[js.index("const SYMBOLS"):js.index("const SOURCE")])
    return syms, re.search(r'const SOURCE = "([^"]+)"', js).group(1)


TICKER_SYMBOLS, TICKER_SOURCE = _ticker_spec()
TAPE = json.loads((ROOT / "firms.json").read_text())["_ticker_universe"]
# TradingView's widget locales (its Ticker Tape page lists them, read 2026-09-24): Hindi and Bengali are not among them,
# so those pages get the English tape.
TV_LOCALE = {"en": "en", "es": "es", "fr": "fr", "ru": "ru", "id": "id", "ar": "ar_AE", "zh": "zh_CN", "pt": "br"}
TV_CREDIT = "https://www.tradingview.com/"


def _tape_name(T, s, group):
    """A symbol as the tape and the still row name it: crypto and stock tickers as they are, commodities in words."""
    return T(f"ticker.sym.{s['sym']}") if group == "commodities" else s["sym"]


def tape_config(T, path=None):
    """The Ticker Tape widget's settings (ticker v3 handoff, section B). web/public/ticker.js adds colorTheme from the
    page's theme when it loads the widget. A tapped symbol opens troid's desk with it named, never TradingView's site
    (path: another page to open instead of the language's home page). largeChartUrl is the bare page: the widget appends
    ?tvwidgetsymbol=EXCHANGE%3ASYMBOL to whatever it is given and fills no {symbolname} placeholder (captured 2026-09-25,
    web/tape_captured.json; the old ?tvwidgetsymbol={symbolname}#desk put the symbol after the #, where the desk didn't
    look). desk2.js scrolls the desk into view itself."""
    return {"symbols": [{"proName": s["tv"], "description": _tape_name(T, s, g["group"])} for g in TAPE["groups"] for s in g["symbols"]],
            "showSymbolLogo": False, "isTransparent": True, "displayMode": "regular", "locale": TV_LOCALE.get(T.code, "en"),
            "largeChartUrl": f"{BASE_URL}{path or T.L or '/'}"}


def ticker(T, desk=False, path=None, hint=False):
    """The price tape under the header (web/public/ticker.js; ticker v3 handoff, section B): TradingView's Ticker Tape,
    scrolling, with its attribution under it, and troid's still row of the same symbols in the same reserved space.
    The still row shows under prefers-reduced-motion, when the visitor pauses the tape, and when the widget fails to
    load; its crypto prices come from /api/ticker (Binance.US), and on the desk each crypto symbol is a button that opens
    a note with "use as entry" (pop.js). Gold, oil and the stocks are names there: their quotes are TradingView's, inside
    its frame, and troid doesn't copy them. Both labels share one cell and the box has one height, so the header is the
    same height whatever shows. On the desk the credit line ends with how to use the tape there (hint; ticker v3
    handoff, section D)."""
    row = []
    for i, g in enumerate(TAPE["groups"]):
        if i:                                   # the first separator is a line break when the row has room for two lines
            row.append(f'<span class="tksep{" tkbr" if i == 1 else ""}" aria-hidden="true">│</span>')
        for s in g["symbols"]:
            if g["group"] == "crypto":
                inner = f'<b>{s["sym"]}</b> <span class="p">—</span> <span class="c"></span>'
                row.append(f'<button type="button" class="tki" data-sym="{s["sym"]}" data-pop="tk-use" aria-expanded="false" aria-controls="tk-use">{inner}</button>'
                           if desk else f'<span class="tki" data-sym="{s["sym"]}">{inner}</span>')
            else:
                row.append(f'<span class="tki tkx"><b>{_tape_name(T, s, g["group"])}</b></span>')
    note = (f'<div class="pop" id="tk-use" hidden><p class="tkn"></p><p><button type="button" class="linkbtn">{T("ticker.use")}</button></p></div>'
            if desk else "")
    cfg = html.escape(json.dumps(tape_config(T, path), ensure_ascii=False, separators=(",", ":")), quote=True)
    tip = f'<span class="tkh"> · {T("desk2.tape_hint")}</span>' if hint else ""
    return (f'<div class="tk off" id="tk" role="region" aria-label="{T.attr("ticker.aria")}" data-source="{TICKER_SOURCE}"'
            f' data-up="{T.attr("ticker.up")}" data-down="{T.attr("ticker.down")}" data-note="{T.attr("ticker.note")}" data-tv="{cfg}">'
            f'<div class="tkbox"><div class="tradingview-widget-container" id="tv"><div class="tradingview-widget-container__widget"></div></div>'
            f'<div class="tkrow">{"".join(row)}</div></div>'
            f'<p class="tkl"><span class="tkt"><span class="tkc"><a href="{TV_CREDIT}" rel="noopener nofollow" target="_blank">{T("ticker.credit")}</a>{tip}</span>'
            f'<span class="tks">{T("ticker.still", source=TICKER_SOURCE)} <span class="tkd">{T("ticker.delayed")}</span></span></span>'
            f'<button type="button" class="tkp" aria-controls="tk" aria-label="{T.attr("ticker.pause_label")}"'
            f' data-pause="{T.attr("ticker.pause_label")}" data-play="{T.attr("ticker.play_label")}">'
            f'<span class="tkpp">{T("ticker.pause")}</span><span class="tkpl">{T("ticker.play")}</span></button></p>'
            f'</div>{calendar_strip(T, desk)}{note}<script src="/ticker.js" defer></script>')


CAL_KINDS = ["cpi", "ppi", "jobs", "jolts", "gdp", "pce", "fomc", "minutes"]


def calendar_strip(T, desk=False):
    """The calendar strip under the tape (web/public/calendar.js; ticker v2 handoff, section D, kept by v3): the scheduled
    US releases of the next 7 days, from web/public/calendar.json, each opening a note with its source (pop.js, which
    the desk's template loads itself). On the desk each event says how long before or after the selected firm's reset
    it lands. Hidden, its space kept, until the schedule loads, and when it can't or is over 14 days old. The note says
    why troid lists them, the MEASURED finding with its sample (verify_claims re-measures it), and what it doesn't show."""
    t = {"kinds": {k: T(f"calendar.kind.{k}") for k in CAL_KINDS}, "longs": {k: T(f"calendar.long.{k}") for k in CAL_KINDS},
         "est": {k: T(f"calendar.est.{k}") for k in ("advance", "second", "third")},
         **{k: T(f"calendar.{k}") for k in ("before", "after", "h", "hm", "m", "empty")},
         **{k: T(f"calendar.note.{k}") for k in ("what", "inside", "outside", "source")}}
    data = html.escape(json.dumps(t, ensure_ascii=False, separators=(",", ":")), quote=True)
    return (f'<div class="cal off" id="cal" role="region" aria-label="{T.attr("calendar.aria")}" data-t="{data}"><div class="calrow"></div></div>'
            f'<div class="pop" id="cal-note" hidden><p class="cn1"></p>'
            f'<p>{T("calendar.note.why")} {T("calendar.note.measured")} {T("calendar.note.cause")}</p>'
            f'<p class="cn2"></p><p class="cn3"></p></div><script src="/calendar.js" defer></script>'
            + ("" if desk else '<script src="/pop.js" defer></script>'))


def html_attrs(T):
    return f' lang="{T.code}"' + ("" if T.code == "en" else f' dir="{T.lang["dir"]}"')


def common(T, page, live, preview=False):
    """What every template gets."""
    return {"t": T, "T": T, "code": T.code, "lang": T.lang, "dir": T.lang["dir"], "L": T.L, "H": T.H, "page": page,
            "html_attrs": html_attrs(T), "head_extra": head_extra(T, page, live), "og": og(T, page),
            "switcher": switcher(T, page, live), "mark": mark(T), "features": features_on(T), "live": live, "preview": preview,
            "ticker": ticker(T, desk=page == "index", hint=page == "index"),
            "footer": site_text.footer_html(T), "governs": governs_html(T),
            "governs_for": lambda key=None: governs_html(T, key),
            "intl": T.lang["intl"], "site_text": site_text,
            "country_box": country_box(T), "avail_attr": avail_attr(T),
            "src": lambda sid: sources.tier(T, sid), "S": sources.SOURCES}


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


DATE_MARK = "\x00updated\x00"


def dated(text, old):
    """A page that shows a date ("Last updated", "Effective") shows the last change of its own content: the text
    between <!-- dated --> and <!-- /dated --> (challenge-proof audit, D4: the FAQ said "Last updated 23 September 2026"
    after changing on the 25th). The same content as the page published before (old) keeps that page's date; any
    change makes it today (UTC). Nav, ticker and footer are outside the marks, so a change there moves no date."""
    if DATE_MARK not in text:
        return text
    def region(s):
        i, j = s.find("<!-- dated"), s.find("<!-- /dated -->")
        return s[i:j] if 0 <= i < j else None
    new, prev, date = region(text), region(old) if old else None, None
    if new and prev:
        m = re.fullmatch(re.escape(new).replace(re.escape(DATE_MARK), "(.+?)"), prev, re.S)
        if m and len(set(m.groups())) == 1:
            date = m.group(1)
    from datetime import datetime, timezone
    return text.replace(DATE_MARK, date or datetime.now(timezone.utc).strftime("%Y-%m-%d"))


def render(template, T, page, live, preview=False, **extra):
    ctx = common(T, page, live, preview)
    ctx["updated"] = DATE_MARK
    ctx.update(extra)
    text = ENV.get_template(template).render(**ctx)
    prev = out_path(T.code, page)
    return dated(text, prev.read_text() if prev.exists() else None)


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
