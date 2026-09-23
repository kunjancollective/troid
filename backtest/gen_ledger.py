#!/usr/bin/env python3
"""Render the shadow account as a public page. Runs after forward.py in the daily loop.

  python gen_ledger.py   ->   ../web/public/ledger.html

Every closed trade, the equity curve, the current state. Losers included, nothing
edited. The page carries the strategy's own verdict on itself: inside noise.
"""
from __future__ import annotations
import csv, json, html, math, statistics, datetime as dt
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import site_text
JOURNAL, STATE, CFG = HERE/"journal.csv", HERE/"state.json", HERE/"strategy_config.json"
RUNS = HERE/"runs.csv"
OUT = HERE.parent/"web"/"public"/"ledger.html"
QUOTA = 100_000.0
# the bar file the journal was replayed on: the frozen sample plus the live tail when present
BARS = HERE/"data"/("live_4h.csv" if (HERE/"data"/"live_4h.csv").exists() else "btc_4h.csv")
CHARTS_N = 20                      # closed trades drawn, newest first
LWC = "https://cdn.jsdelivr.net/npm/lightweight-charts@4.2.3/dist/lightweight-charts.standalone.production.js"

BRAND = (HERE.parent/"web"/"public"/"index.html").read_text()
STYLE = BRAND[BRAND.index("<link rel=\"icon\""):BRAND.index("</style>")+8]
HEADER = '''<div class="bar">
  <a class="mark" href="/">tr<span class="dot"></span>id</a>
  <nav><a href="/">troid's desk</a><a href="/compare">troid's compare</a><a href="/ledger">troid's ledger</a><a href="/dashboard">troid's research</a><a href="/chat">ask troid</a><a href="/faq">faq</a>
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


def heartbeat(st):
    """Last bar, balance, room, binding, position. No direction, no price, no stop."""
    if not st: return ""
    bar = st.get("as_of_bar_utc", "")[:16].replace("T", " ")
    pos = st.get("position")
    ptxt = (f"open since {pos['open_since_utc'][:16].replace('T', ' ')} UTC · {pos['tranches_filled']} of {pos['tranches']} tranche(s)"
            if pos else "flat")
    binding = {"daily": "daily limit", "floor": "max-loss floor"}.get(st.get("binding", ""), "—")
    return f'''<div class="cells">
<div class="c"><div class="k">last bar</div><div class="v">{bar}</div><div class="hs">UTC · close {st.get("last_close", 0):,.0f}</div></div>
<div class="c"><div class="k">balance</div><div class="v">${st.get("balance", QUOTA):,.0f}</div><div class="hs">realized</div></div>
<div class="c"><div class="k">room</div><div class="v">${min(st.get("daily_room", 0), st.get("distance_to_floor", 0)):,.0f}</div><div class="hs">binding · {binding}</div></div>
<div class="c"><div class="k">to floor</div><div class="v">${st.get("distance_to_floor", 0):,.0f}</div><div class="hs">daily ${st.get("daily_room", 0):,.0f}</div></div>
<div class="c" style="grid-column:span 2"><div class="k">position</div><div class="v" style="font-size:14px;margin-top:4px">{ptxt}</div><div class="hs">no direction, price or stop is published</div></div>
</div>'''


def runs_table():
    """One row per shadow run in the last 7 days, from runs.csv."""
    if not RUNS.exists(): return '<p class="hs" style="margin:0 0 14px">runs: none recorded yet</p>'
    now = dt.datetime.now(dt.timezone.utc)
    rows = [r for r in csv.DictReader(RUNS.open()) if dt.datetime.fromisoformat(r["run_utc"]) >= now - dt.timedelta(days=7)]
    if not rows: return '<p class="hs" style="margin:0 0 14px">runs: none in the last 7 days</p>'
    body = "".join(f'<tr><td>{r["run_utc"][:16].replace("T", " ")}</td><td>{r["as_of_bar_utc"][:16].replace("T", " ")}</td>'
                   f'<td class="num">{float(r["balance"]):,.0f}</td><td class="num">{r["trades_new"]}</td><td>{r["position"]}</td></tr>'
                   for r in reversed(rows[-42:]))
    return (f'<div class="panel"><p class="eyebrow">Runs · last 7 days · {len(rows)}</p><div class="scroll"><table>'
            f'<tr><th>run (UTC)</th><th>bar</th><th class="num">balance</th><th class="num">closed</th><th>position</th></tr>{body}</table></div></div>')


def load_bars():
    """t,o,h,l,c rows; comment lines skipped. Returns (times, bars) with times in unix seconds."""
    if not BARS.exists(): return [], []
    rows = [r for r in csv.reader(BARS.open()) if r and not r[0].startswith("#")]
    if len(rows[0]) != 5: return [], []
    return [int(float(r[0])) for r in rows], [tuple(round(float(x), 2) for x in r[1:5]) for r in rows]


EXIT_LABEL = {"tp1": "TP1", "tp2": "TP2", "tp3": "TP3", "stop": "stop", "max_hold_10d": "max hold",
              "reset_flat": "reset flatten", "reset_flat_loser": "reset flatten"}


def when(iso):
    d = dt.datetime.fromisoformat(iso)
    return f"{d.month}/{d.day} {d:%H:%M}"


def trade_charts(rows):
    """One candlestick panel per closed trade, last CHARTS_N, newest first: bars from 10 before
    entry to 5 after exit, entry / stop / TPs / exit marked. The caption is the risk-why only:
    no thesis, no reason the price moved. Open positions are not drawn — they are not closed."""
    times, bars = load_bars()
    if not times or not rows or "entry_utc" not in rows[0]: return ""
    at = {t: i for i, t in enumerate(times)}
    bal = QUOTA; bal_at = []                    # balance when each trade was entered (one position at a time)
    for r in rows: bal_at.append(bal); bal += float(r["pnl"])
    items, caps = [], []
    for k in range(len(rows) - 1, max(-1, len(rows) - 1 - CHARTS_N), -1):
        r = rows[k]
        if not r.get("entry_utc"): continue
        ei = at.get(int(dt.datetime.fromisoformat(r["entry_utc"]).timestamp()))
        xi = at.get(int(dt.datetime.fromisoformat(r["exit_utc"]).timestamp()))
        if ei is None or xi is None: continue
        lo, hi = max(0, ei - 10), min(len(bars), xi + 6)
        side = 1 if r["side"] == "long" else -1
        entry, stop, exit_px = float(r["entry_price"]), float(r["stop_price"]), float(r["exit_price"])
        risk, room = float(r["risk_usd"]), float(r["room_at_entry"])
        tps = json.loads(r["tp_prices"])
        items.append(dict(id=f"tc{k}", side=side, entry=entry, stop=stop, tps=tps, exit=exit_px,
                          entry_t=times[ei], exit_t=times[xi], exit_label=EXIT_LABEL.get(r["reason"], r["reason"]),
                          bars=[dict(time=times[i], open=bars[i][0], high=bars[i][1], low=bars[i][2], close=bars[i][3])
                                for i in range(lo, hi)]))
        binding = {"daily": "daily limit", "floor": "max-loss floor"}.get(r["binding_at_entry"], r["binding_at_entry"])
        flag = ' <span title="held through a forward-filled bar">⚑</span>' if int(r.get("filled_bars") or 0) else ""
        cap = (f'{r["side"].capitalize()} · {r["kind"]} · {when(r["entry_utc"])} → {when(r["exit_utc"])} UTC · '
               f'entry {entry:,.0f} · stop {stop:,.0f} ({abs(entry - stop) / entry * 100:.2f}%) · '
               f'sized ${risk:,.0f} = {risk / bal_at[k] * 100:.1f}% · {binding} binding, ${room:,.0f} room · '
               f'{r["fills"]} of {r["tranches"]} tranches · exit {EXIT_LABEL.get(r["reason"], r["reason"])} '
               f'after {r["bars_held"]} bars · {float(r["r"]):+.2f}R · fees {float(r["fee_share_pct"]):.1f}% of risk')
        caps.append(f'<div class="tc"><div class="tchart" id="tc{k}"></div><p class="tcap">{html.escape(cap)}{flag}</p></div>')
    if not items: return ""
    return (f'<div class="panel"><p class="eyebrow">Last {len(items)} closed trades · drawn</p>'
            f'<p class="hs" style="margin:-8px 0 14px">Bars from 10 before entry to 5 after exit. Entry, initial stop and take-profits '
            f'as the engine set them; the stop moves to average entry after TP1 and is not redrawn. Open position: not drawn.</p>'
            + "".join(caps) + "</div>"
            + f'<script src="{LWC}"></script>\n<script>var TRADES=' + json.dumps(items, separators=(",", ":")) + ";\n"
            + CHART_JS + "</script>")


CHART_JS = r"""(function(){
  var cs=getComputedStyle(document.documentElement),T={};
  ["bg","surface","line","ink","dim","signal","bad"].forEach(function(k){T[k]=cs.getPropertyValue("--"+k).trim()});
  var mono=cs.getPropertyValue("--mono").trim()||"monospace";
  if(!window.LightweightCharts){document.querySelectorAll(".tchart").forEach(function(e){e.innerHTML='<p class="hs" style="padding:12px">chart library did not load (cdn.jsdelivr.net) — the caption is the record</p>'});return}
  var L=LightweightCharts;
  TRADES.forEach(function(t){
    var el=document.getElementById(t.id); if(!el)return;
    var chart=L.createChart(el,{autoSize:true,height:300,
      layout:{background:{type:"solid",color:T.surface},textColor:T.dim,fontFamily:mono,fontSize:10},
      grid:{vertLines:{color:T.line},horzLines:{color:T.line}},
      rightPriceScale:{borderColor:T.line},timeScale:{borderColor:T.line,timeVisible:true,secondsVisible:false},
      crosshair:{mode:L.CrosshairMode.Normal},handleScroll:false,handleScale:false});
    var s=chart.addCandlestickSeries({upColor:"transparent",downColor:T.dim,borderUpColor:T.ink,borderDownColor:T.dim,
      wickUpColor:T.ink,wickDownColor:T.dim,priceLineVisible:false,lastValueVisible:false});
    s.setData(t.bars);
    s.createPriceLine({price:t.entry,color:T.signal,lineWidth:1,lineStyle:L.LineStyle.Dotted,axisLabelVisible:true,title:"entry"});
    s.createPriceLine({price:t.stop,color:T.bad,lineWidth:1,lineStyle:L.LineStyle.Solid,axisLabelVisible:true,title:"stop"});
    t.tps.forEach(function(p,i){s.createPriceLine({price:p,color:T.dim,lineWidth:1,lineStyle:L.LineStyle.Dashed,axisLabelVisible:false,title:"TP"+(i+1)})});
    s.setMarkers([{time:t.entry_t,position:t.side>0?"belowBar":"aboveBar",color:T.signal,shape:t.side>0?"arrowUp":"arrowDown",text:"entry"},
                  {time:t.exit_t,position:t.side>0?"aboveBar":"belowBar",color:T.ink,shape:"circle",text:t.exit_label}]);
    chart.timeScale().fitContent();
  });
})();"""


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
<meta name="viewport" content="width=device-width, initial-scale=1"><title>troid's ledger</title>
{STYLE}
<style>.k{{font-family:var(--mono);font-size:9.5px;text-transform:uppercase;letter-spacing:.1em;color:var(--dim)}}
.v{{font-family:var(--mono);font-size:19px;font-weight:500;letter-spacing:-.02em}}
.cells{{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:1px;background:var(--line);border:1px solid var(--line);border-radius:3px;margin-bottom:14px}}
.c{{background:var(--surface);padding:12px}}
.hs{{font-family:var(--mono);font-size:10.5px;color:var(--dim);margin-top:3px}}
.warnbox{{border-left:2px solid var(--warn);background:var(--surface2);padding:12px 14px;font-family:var(--mono);font-size:12px;color:var(--dim);margin-bottom:14px;line-height:1.6}}
.meta{{font-family:var(--mono);font-size:11px;color:var(--dim);margin:0 0 30px;letter-spacing:.02em}}table{{border-collapse:collapse;width:100%;font-size:13.5px;min-width:520px;font-family:var(--mono)}}th{{text-align:left;font-weight:500;color:var(--dim);font-size:10px;text-transform:uppercase;
  letter-spacing:.1em;padding:0 10px 8px 0;border-bottom:1px solid var(--line)}}td{{padding:9px 10px 9px 0;border-bottom:1px solid var(--line);font-variant-numeric:tabular-nums}}tr:last-child td{{border-bottom:none}}.num{{text-align:right}}.foot{{font-family:var(--mono);font-size:11px;color:var(--dim);border-top:1px solid var(--line);
  margin-top:36px;padding-top:20px;line-height:1.8;text-align:left}}
.scroll{{overflow-x:auto;-webkit-overflow-scrolling:touch}}
.tc{{margin-bottom:18px}}.tchart{{height:300px;border:1px solid var(--line);border-radius:3px;overflow:hidden}}
.tcap{{font-family:var(--mono);font-size:11px;color:var(--dim);margin:6px 0 0;line-height:1.6}}</style>
</head><body><div class="wrap">
{HEADER}
<p class="eyebrow" style="margin-top:28px;text-transform:none">troid's ledger</p>
<h1>{html.escape(cfg["name"])}</h1>
<p class="lede">The shadow account. Every closed trade, unedited, losers included. It places nothing — a human would.</p>
<p class="meta">as of {st.get("as_of_bar_utc","—")[:16].replace("T"," ")} UTC · {cfg["instrument"]} {cfg["timeframe"]} · {cfg["profile"]} rules · cross 5x · replayed every 4h, 20 min after the bar</p>

{heartbeat(st)}
{runs_table()}
<div class="warnbox">This strategy measures {exp:+.3f}R per trade over {n} trades — a standard error of ~{se:.3f}R, a
confidence interval that {"contains" if abs(exp) < 1.96*se else "excludes"} zero, and a result {"below" if exp < noise30 else "above"} what chance produces across the
~30 configurations searched (~{noise30:+.3f}R).{
f' Out of sample, on the {hold["n"]} trades from 2021–2025 the parameters never saw: {hold["exp"]:+.3f}R, SE {hold["se"]:.3f}R. No edge, confirmed.' if hold else ''} It is published so you can watch a null result run forward, not because it works. The <a href="/tearsheet">full tearsheet</a> shows what noise looks like when all of it is shown.
{len(live)} of these trades were logged live; the rest were backfilled on {rows[0]["logged_utc"][:10] if rows else "—"}.{
f" {flagged} held through a forward-filled bar (a flat bar substituted for a feed gap), marked ⚑ below — flagged, not excluded." if flagged else ""}</div>
{site_text.hypo_html()}

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

{trade_charts(rows)}

<p class="foot">A week of trades is n≈2 with a standard error of ~0.26R. The weekly line above is a
ledger entry, not a claim. Read it that way. · Bars from api.binance.us, one feed end to end; ⚑ marks a trade that held through a forward-filled bar. · <a href="https://github.com/kunjancollective/troid">journal.csv in the repo</a><br>{site_text.footer_html()}</p>
</div></body></html>'''
    OUT.write_text(page)
    print(f"ledger.html: {n} trades, net {net:+,.0f}, {len(live)} logged live -> {OUT}")


if __name__ == "__main__":
    main()
