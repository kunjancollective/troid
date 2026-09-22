#!/usr/bin/env python3
"""A quantstats tearsheet over the shadow journal. Runs after gen_ledger.py in the daily loop.

  python gen_tearsheet.py   ->   ../web/public/tearsheet.html

Returns series: each closed trade's P&L in dollars, summed by exit day, divided by the
quota. Days with no exit are zero, so the calendar is complete from the first entry to
the last bar processed. Returns are on the fixed quota, so cumulative figures are sums,
not products (compounded=False). Crypto trades seven days a week: 365 periods a year.

Every metric on the page is MEASURED. The header line says so, verbatim from the brief.
"""
from __future__ import annotations
import os, re, csv, json, html, datetime as dt
from pathlib import Path
os.environ.setdefault("MPLBACKEND", "Agg")
import logging
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)   # quantstats asks for Arial; the runner has DejaVu
import pandas as pd
import quantstats as qs

HERE = Path(__file__).parent
JOURNAL, STATE, CFG = HERE/"journal.csv", HERE/"state.json", HERE/"strategy_config.json"
OUT = HERE.parent/"web"/"public"/"tearsheet.html"
QUOTA = 100_000.0
HEADER = ("A full tearsheet on a strategy whose holdout expectancy is +0.008R. Every metric below is "
          "MEASURED and inside noise. Published because that is what noise looks like when someone "
          "shows you all of it.")


def returns_series():
    rows = list(csv.DictReader(JOURNAL.open())) if JOURNAL.exists() else []
    st = json.loads(STATE.read_text()) if STATE.exists() else {}
    if not rows: return None, rows
    pnl = {}
    for r in rows:
        d = dt.datetime.fromisoformat(r["exit_utc"]).date()
        pnl[d] = pnl.get(d, 0.0) + float(r["pnl"])
    first = min(dt.datetime.fromisoformat(r.get("entry_utc") or r["exit_utc"]).date() for r in rows)
    last = dt.datetime.fromisoformat(st["as_of_bar_utc"]).date() if st.get("as_of_bar_utc") else max(pnl)
    idx = pd.date_range(first, last, freq="D")
    s = pd.Series([pnl.get(d.date(), 0.0) / QUOTA for d in idx], index=idx, name="troid-shadow-1")
    return s, rows


def main():
    s, rows = returns_series()
    cfg = json.loads(CFG.read_text())
    if s is None or len(rows) < 2:
        OUT.write_text("<!DOCTYPE html><html><head><meta charset='utf-8'><title>troid — tearsheet</title></head>"
                       "<body><p>No closed trades yet.</p></body></html>")
        print("tearsheet.html: no trades"); return
    tmp = OUT.with_suffix(".tmp.html")
    qs.reports.html(s, output=str(tmp), title=cfg["name"], compounded=False, periods_per_year=365,
                    download_filename="troid-tearsheet.html", figfmt="svg")
    page = tmp.read_text(); tmp.unlink()
    head = (f'<div id="troid-head" style="max-width:960px;margin:0 auto;padding:18px 20px 0;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:13px;line-height:1.6">'
            f'<div style="margin-bottom:10px"><a href="/" style="text-decoration:none;color:inherit;font-weight:600;font-size:18px;letter-spacing:-.04em">troid</a>'
            f' &nbsp;·&nbsp; <a href="/ledger">ledger</a> &nbsp;·&nbsp; <a href="/dashboard">research</a> &nbsp;·&nbsp; <a href="/faq">faq</a></div>'
            f'<p style="border-left:2px solid #e0a33c;padding:10px 14px;margin:0 0 6px;background:#f4f6f9">{html.escape(HEADER)}</p>'
            f'<p style="margin:0 0 4px;color:#5f6f86">{len(rows)} closed trades on {cfg["instrument"]} {cfg["timeframe"]}, '
            f'{s.index[0]:%Y-%m-%d} to {s.index[-1]:%Y-%m-%d}. Daily P&amp;L on the ${QUOTA:,.0f} quota, days without an exit count as zero, '
            f'365 periods a year, sums not products. Source: journal.csv in the repo. Not financial advice.</p></div>')
    i = page.lower().index("<body")
    j = page.index(">", i) + 1
    page = page[:j] + "\n" + head + page[j:]
    # our title and icon; the page is public, so no robots exclusion; no third-party favicon fetch
    page = re.sub(r"<title>.*?</title>", "<title>troid — tearsheet</title>", page, count=1, flags=re.S)
    page = re.sub(r'\s*<meta name="robots"[^>]*>', "", page, count=1)
    page = re.sub(r'<link rel="shortcut icon"[^>]*>', '<link rel="icon" href="/favicon.ico">', page, count=1)
    # the template calls save() on load but this build ships no such function; drop the call, and
    # let the two columns stack on a phone (the template only has a print media rule)
    page = page.replace(' onload="save()"', "", 1)
    page = page.replace("</head>", "<style>#troid-head a{color:#1f6fd1}@media (max-width:760px){body{margin:12px}#left,#right{width:100%;float:none;margin:0}"
                        "#left svg,#right svg{max-width:100%;height:auto}table{width:100%}}</style>\n</head>", 1)
    OUT.write_text(page)
    print(f"tearsheet.html: {len(rows)} trades, {len(s)} days, {OUT.stat().st_size//1024} KB -> {OUT}")


if __name__ == "__main__":
    main()
