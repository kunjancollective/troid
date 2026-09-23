#!/usr/bin/env python3
"""A quantstats tearsheet over the shadow journal. Runs after gen_ledger.py in the daily loop.

  python gen_tearsheet.py   ->   ../web/public/tearsheet.html, and ../web/public/{lang}/tearsheet.html for every
                                 other published language (site_build.targets())

Returns series: each closed trade's P&L in dollars, summed by exit day, divided by the
quota. Days with no exit are zero, so the calendar is complete from the first entry to
the last bar processed. Returns are on the fixed quota, so cumulative figures are sums,
not products (compounded=False). Crypto trades seven days a week: 365 periods a year.

Every metric on the page is MEASURED. The header line says so, verbatim from the brief (tearsheet.head.box in
web/i18n). troid's header box and footer are keyed; the report itself is quantstats' own English. A translated
route gets render_stub: troid's header box in its language, the 4.41 box, and a link to the English report, not
a 370 KB copy of it.
"""
from __future__ import annotations
import os, re, csv, json, datetime as dt
import sys
from pathlib import Path
os.environ.setdefault("MPLBACKEND", "Agg")
import logging
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)   # quantstats asks for Arial; the runner has DejaVu

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import i18n
import site_build
import site_text
JOURNAL, STATE, CFG = HERE/"journal.csv", HERE/"state.json", HERE/"strategy_config.json"
OUT = HERE.parent/"web"/"public"/"tearsheet.html"
QUOTA = 100_000.0


def load():
    rows = list(csv.DictReader(JOURNAL.open())) if JOURNAL.exists() else []
    st = json.loads(STATE.read_text()) if STATE.exists() else {}
    return rows, st


def span(rows, st):
    """First and last day of the returns calendar: the first entry, the last bar processed."""
    first = min(dt.datetime.fromisoformat(r.get("entry_utc") or r["exit_utc"]).date() for r in rows)
    last = (dt.datetime.fromisoformat(st["as_of_bar_utc"]).date() if st.get("as_of_bar_utc")
            else max(dt.datetime.fromisoformat(r["exit_utc"]).date() for r in rows))
    return first, last


def returns_series():
    import pandas as pd
    rows, st = load()
    if not rows: return None, rows
    pnl = {}
    for r in rows:
        d = dt.datetime.fromisoformat(r["exit_utc"]).date()
        pnl[d] = pnl.get(d, 0.0) + float(r["pnl"])
    first, last = span(rows, st)
    idx = pd.date_range(first, last, freq="D")
    s = pd.Series([pnl.get(d.date(), 0.0) / QUOTA for d in idx], index=idx, name="troid-shadow-1")
    return s, rows


def _english(T):
    return T.code == "en" and not getattr(T, "pseudo", False)


def head_html(T, live, n, cfg, first, last, tail=""):
    """troid's header box above the report: the site's links, the MEASURED line, the sample, the 4.41 box.
    English renders exactly as it always has; tail goes inside the box, after the 4.41 box (the stub's line)."""
    market = f'{cfg["instrument"]} {cfg["timeframe"]}'
    if not _english(T):
        market = f'<bdi translate="no">{market}</bdi>'        # a ticker: never translated, left to right
    sep = " &nbsp;·&nbsp; "
    nav = sep.join(f'<a href="{u}">{T(k)}</a>' for u, k in (
        (T.H, "product.desk"), (f"{T.L}/compare", "product.compare"), (f"{T.L}/ledger", "product.ledger"),
        (f"{T.L}/dashboard", "product.research"), (f"{T.L}/chat", "product.ask"), (f"{T.L}/faq", "common.nav.faq")))
    return (f'<div id="troid-head" style="max-width:960px;margin:0 auto;padding:18px 20px 0;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:13px;line-height:1.6">'
            f'<div style="margin-bottom:10px"><a href="{T.H}" style="text-decoration:none;color:inherit;font-weight:600;font-size:18px;letter-spacing:-.04em">troid</a>'
            f'{sep}{nav}{site_build.switcher(T, "tearsheet", live)}</div>'
            f'<p style="margin:0 0 8px;font-size:11px;color:#5f6f86;letter-spacing:.12em">{T("tearsheet.head.eyebrow")}</p>'
            f'<p style="border-inline-start:2px solid #e0a33c;padding:10px 14px;margin:0 0 6px;background:#f4f6f9">{T("tearsheet.head.box")}</p>'
            + (f'<p style="margin:0 0 4px;color:#5f6f86">'
               + T("tearsheet.head.sample", n=n, market=market, start=f"{first:%Y-%m-%d}", end=f"{last:%Y-%m-%d}", quota=f"${QUOTA:,.0f}")
               + '</p>' + site_text.hypo_html(site_text.NO_EDGE_SHORT, T=T) if n else "")
            + tail + '</div>')


def foot_html(T):
    return ('<div id="troid-foot" style="clear:both;max-width:960px;margin:30px auto 40px;padding:14px 20px 0;border-top:1px solid #dde4ee;'
            'font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11px;line-height:1.8;color:#5f6f86">'
            + site_text.footer_html(T) + '</div>')


def render_stub(T, live):
    """The tearsheet on a translated route (site_build.GENERATED): troid's header box in T's language, the 4.41 box,
    and one line pointing to the full report, which quantstats generates in English and which is published once,
    at /tearsheet."""
    rows, st = load()
    cfg = json.loads(CFG.read_text())
    if len(rows) >= 2:
        first, last = span(rows, st)
        body = head_html(T, live, len(rows), cfg, first, last,
                         tail=f'<p style="margin:0 0 14px">{T("tearsheet.stub.english")}</p>')
    else:
        body = head_html(T, live, 0, cfg, None, None, tail=f'<p style="margin:0 0 14px">{T("tearsheet.empty")}</p>')
    og = site_build.og(T)
    return f'''<!DOCTYPE html>
<html{site_build.html_attrs(T)}>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{T("tearsheet.meta.title")}</title>
<link rel="icon" href="/favicon.ico">
<meta property="og:image" content="{og["image"]}">
<meta property="og:title" content="{og["title"]}">
<meta property="og:description" content="{og["description"]}">
<style>:root{{--ink:#000;--dim:#5f6f86;--line:#dde4ee;--surface2:#eef2f7;--warn:#96661a;--sans:Arial,sans-serif;--mono:ui-monospace,SFMono-Regular,Menlo,monospace}}
body{{-webkit-font-smoothing:antialiased;margin:30px;background:#fff;color:#000;font:13px/1.4 var(--sans)}}#troid-head a,#troid-foot a{{color:#1f6fd1}}
@media (max-width:760px){{body{{margin:12px}}}}</style>
{site_build.head_extra(T, "tearsheet", live)}</head>
<body>
{body}
{foot_html(T)}
</body>
</html>
'''


def main(out=None):
    """The English report at web/public/tearsheet.html (quantstats); a stub for every other published language."""
    live = site_build.targets()
    for c in live:
        if c != "en":
            p = site_build.out_path(c, "tearsheet", out)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(render_stub(i18n.Strings(c), live))
    T = i18n.Strings("en")
    dest = site_build.out_path("en", "tearsheet", out)
    s, rows = returns_series()
    cfg = json.loads(CFG.read_text())
    if s is None or len(rows) < 2:
        dest.write_text(f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>{T('tearsheet.meta.title')}</title></head>"
                        f"<body><p>{T('tearsheet.empty')}</p></body></html>")
        print("tearsheet.html: no trades"); return
    import quantstats as qs
    tmp = dest.with_suffix(".tmp.html")
    qs.reports.html(s, output=str(tmp), title=cfg["name"], compounded=False, periods_per_year=365,
                    download_filename="troid-tearsheet.html", figfmt="svg")
    page = tmp.read_text(); tmp.unlink()
    head = head_html(T, live, len(rows), cfg, s.index[0], s.index[-1])
    i = page.lower().index("<body")
    j = page.index(">", i) + 1
    page = page[:j] + "\n" + head + page[j:]
    # troid's title and icon; the page is public, so no robots exclusion; no third-party favicon fetch
    page = re.sub(r"<title>.*?</title>", lambda m: f"<title>{T('tearsheet.meta.title')}</title>", page, count=1, flags=re.S)
    page = re.sub(r'\s*<meta name="robots"[^>]*>', "", page, count=1)
    page = re.sub(r'<link rel="shortcut icon"[^>]*>', '<link rel="icon" href="/favicon.ico">', page, count=1)
    # the template calls save() on load but this build ships no such function; drop the call, and
    # let the two columns stack on a phone (the template only has a print media rule)
    page = page.replace(' onload="save()"', "", 1)
    page = page.replace("</head>", "<style>#troid-head a{color:#1f6fd1}@media (max-width:760px){body{margin:12px}#left,#right{width:100%;float:none;margin:0}"
                        "#left svg,#right svg{max-width:100%;height:auto}table{width:100%}}</style>\n"
                        + "".join(f'<meta property="og:{k}" content="{v}">\n' for k, v in site_build.og(T).items())
                        + site_build.head_extra(T, "tearsheet", live) + "</head>", 1)
    page = page.replace('</body>', foot_html(T) + '\n</body>', 1)
    dest.write_text(page)
    print(f"tearsheet.html: {len(rows)} trades, {len(s)} days, {dest.stat().st_size//1024} KB -> {dest}"
          + (f" (stubs: {', '.join(c for c in live if c != 'en')})" if len(live) > 1 else ""))


if __name__ == "__main__":
    main()
