#!/usr/bin/env python3
"""Render the shadow account as a public page. Runs after forward.py in the daily loop.

  python gen_ledger.py   ->   ../web/public/ledger.html

Every closed trade, the equity curve, the current state. Losers included, nothing
edited. The page carries the strategy's own verdict on itself: inside noise.
"""
from __future__ import annotations
import csv, json, html, math, statistics, datetime as dt
from pathlib import Path

HERE = Path(__file__).parent
JOURNAL, STATE, CFG = HERE/"journal.csv", HERE/"state.json", HERE/"strategy_config.json"
OUT = HERE.parent/"web"/"public"/"ledger.html"
QUOTA = 100_000.0

BRAND = (HERE.parent/"web"/"public"/"index.html").read_text()
STYLE = BRAND[BRAND.index("<link rel=\"icon\""):BRAND.index("</style>")+8]
HEADER = '''<div class="bar">
  <a class="mark" href="/">tr<span class="dot"></span>id</a>
  <nav><a href="/compare">compare</a><a href="/faq">faq</a><a href="/ledger">ledger</a><a href="/dashboard">research</a>
    <a href="https://github.com/kunjancollective/troid">source</a></nav>
</div>'''


def equity_svg(rows, w=760, h=180):
    if not rows: return ""
    eq, cur = [QUOTA], QUOTA
    for r in rows: cur += float(r["pnl"]); eq.append(cur)
    lo, hi = min(eq), max(eq); span = (hi-lo) or 1
    pad = 8
    pts = [(pad + i*(w-2*pad)/(len(eq)-1), pad + (hi-e)*(h-2*pad)/span) for i,e in enumerate(eq)]
    path = "M"+" L".join(f"{x:.1f},{y:.1f}" for x,y in pts)
    zero_y = pad + (hi-QUOTA)*(h-2*pad)/span
    return f'''<svg viewBox="0 0 {w} {h}" preserveAspectRatio="none" style="width:100%;height:{h}px;display:block">
  <line x1="{pad}" y1="{zero_y:.1f}" x2="{w-pad}" y2="{zero_y:.1f}" stroke="var(--line)" stroke-width="1" stroke-dasharray="3 4"/>
  <path d="{path}" fill="none" stroke="var(--signal)" stroke-width="1.5" vector-effect="non-scaling-stroke"/>
</svg>
<div style="display:flex;justify-content:space-between;font-family:var(--mono);font-size:10px;color:var(--dim);margin-top:4px">
  <span>${lo:,.0f}</span><span>start ${QUOTA:,.0f} · dashed</span><span>${hi:,.0f}</span></div>'''


def main():
    rows = list(csv.DictReader(JOURNAL.open())) if JOURNAL.exists() else []
    st = json.loads(STATE.read_text()) if STATE.exists() else {}
    cfg = json.loads(CFG.read_text())
    n = len(rows); wins = sum(1 for r in rows if float(r["pnl"])>0)
    net = sum(float(r["pnl"]) for r in rows)
    rs = [float(r["r"]) for r in rows]
    exp = sum(rs)/n if n else 0
    se = statistics.stdev(rs)/math.sqrt(n) if n > 1 else 0.0
    noise30 = se*math.sqrt(2*math.log(30))          # expected best of ~30 configs under a true zero edge
    flagged = sum(1 for r in rows if int(r.get("filled_bars") or 0) > 0)
    wf_path = HERE/"results"/"walkforward_BTCUSDT.json"          # the holdout, if it has been run
    hold = json.loads(wf_path.read_text())["holdout"] if wf_path.exists() else None
    gw = sum(float(r["pnl"]) for r in rows if float(r["pnl"])>0)
    gl = -sum(float(r["pnl"]) for r in rows if float(r["pnl"])<0)
    pf = gw/gl if gl else 0
    # this week / this month, by exit date
    now = dt.datetime.now(dt.timezone.utc)
    def since(days): 
        cut = now - dt.timedelta(days=days)
        return [r for r in rows if dt.datetime.fromisoformat(r["exit_utc"]) >= cut]
    wk, mo = since(7), since(30)
    # the backfill was written in one run, so every backfilled row carries the same timestamp
    live = [r for r in rows if r["logged_utc"] != rows[0]["logged_utc"]] if rows else []

    trades_html = "".join(f'''<tr><td>{r["exit_utc"][:10]}</td><td>{r["kind"]}</td><td>{r["side"]}</td>
<td class="num">{r["fills"]}</td><td class="num">{r["bars_held"]}</td><td>{r["reason"]}{' <span title="held through a forward-filled bar">⚑</span>' if int(r.get("filled_bars") or 0) else ''}</td>
<td class="num" style="color:{'var(--signal)' if float(r['pnl'])>0 else 'var(--bad)'}">{float(r["pnl"]):+,.2f}</td>
<td class="num">{float(r["r"]):+.2f}</td></tr>''' for r in reversed(rows[-40:]))

    page = f'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>troid — ledger</title>
{STYLE}
<style>.k{{font-family:var(--mono);font-size:9.5px;text-transform:uppercase;letter-spacing:.1em;color:var(--dim)}}
.v{{font-family:var(--mono);font-size:19px;font-weight:500;letter-spacing:-.02em}}
.cells{{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:1px;background:var(--line);border:1px solid var(--line);border-radius:3px;margin-bottom:14px}}
.c{{background:var(--surface);padding:12px}}
.warnbox{{border-left:2px solid var(--warn);background:var(--surface2);padding:12px 14px;font-family:var(--mono);font-size:12px;color:var(--dim);margin-bottom:14px;line-height:1.6}}</style>
</head><body><div class="wrap">
{HEADER}
<h1>{html.escape(cfg["name"])}</h1>
<p class="lede">The shadow account. Every closed trade, unedited, losers included. It places nothing — a human would.</p>
<p class="meta">as of {st.get("as_of_bar_utc","—")[:16].replace("T"," ")} UTC · {cfg["instrument"]} {cfg["timeframe"]} · {cfg["profile"]} rules · cross 5x</p>

<div class="warnbox">This strategy measures {exp:+.3f}R per trade over {n} trades — a standard error of ~{se:.3f}R, a
confidence interval that {"contains" if abs(exp) < 1.96*se else "excludes"} zero, and a result {"below" if exp < noise30 else "above"} what chance produces across the
~30 configurations searched (~{noise30:+.3f}R).{
f' Out of sample, on the {hold["n"]} trades from 2021–2025 the parameters never saw: {hold["exp"]:+.3f}R, SE {hold["se"]:.3f}R. No edge, confirmed.' if hold else ''} It is published so you can watch a null result run forward, not because it works.
{len(live)} of these trades were logged live; the rest were backfilled on {rows[0]["logged_utc"][:10] if rows else "—"}.{
f" {flagged} held through a forward-filled bar (a flat bar substituted for a feed gap), marked ⚑ below — flagged, not excluded." if flagged else ""}</div>

<div class="panel"><p class="eyebrow">Equity</p>{equity_svg(rows)}</div>

<div class="cells">
<div class="c"><div class="k">balance</div><div class="v">${st.get("balance",QUOTA):,.0f}</div></div>
<div class="c"><div class="k">net</div><div class="v" style="color:{'var(--signal)' if net>=0 else 'var(--bad)'}">{net:+,.0f}</div></div>
<div class="c"><div class="k">trades</div><div class="v">{n}</div></div>
<div class="c"><div class="k">win</div><div class="v">{(wins/n*100 if n else 0):.0f}%</div></div>
<div class="c"><div class="k">exp</div><div class="v">{exp:+.3f}R</div></div>
<div class="c"><div class="k">pf</div><div class="v">{pf:.2f}</div></div>
<div class="c"><div class="k">max dd</div><div class="v">${st.get("max_drawdown",0):,.0f}</div></div>
<div class="c"><div class="k">to floor</div><div class="v">${st.get("distance_to_floor",0):,.0f}</div></div>
</div>

<div class="cells">
<div class="c"><div class="k">this week</div><div class="v">{len(wk)} trades · {sum(float(r["r"]) for r in wk):+.2f}R</div></div>
<div class="c"><div class="k">this month</div><div class="v">{len(mo)} trades · {sum(float(r["r"]) for r in mo):+.2f}R</div></div>
<div class="c"><div class="k">status</div><div class="v">{st.get("outcome","—")}</div></div>
</div>

<div class="panel"><p class="eyebrow">Last {min(n,40)} trades</p><div class="scroll"><table>
<tr><th>closed</th><th>kind</th><th>side</th><th class="num">fills</th><th class="num">bars</th><th>exit</th><th class="num">pnl</th><th class="num">R</th></tr>
{trades_html}</table></div></div>

<p class="foot">A week of trades is n≈2 with a standard error of ~0.26R. The weekly line above is a
ledger entry, not a claim. Read it that way. · Bars from api.binance.us, one feed end to end; ⚑ marks a trade that held through a forward-filled bar. · <a href="https://github.com/kunjancollective/troid">journal.csv in the repo</a><br><a href="/faq">faq</a> · <a href="/ledger">ledger</a> · <a href="/dashboard">research</a> · <a href="https://github.com/kunjancollective/troid">source</a> · <a href="https://x.com/tradingdroid">x</a> · <a href="https://www.reddit.com/user/tradingdroid/">reddit</a></p>
</div></body></html>'''
    OUT.write_text(page)
    print(f"ledger.html: {n} trades, net {net:+,.0f}, {len(live)} logged live -> {OUT}")


if __name__ == "__main__":
    main()
