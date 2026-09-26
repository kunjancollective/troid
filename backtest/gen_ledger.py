#!/usr/bin/env python3
"""Render the shadow account as a public page. Runs after forward.py in the daily loop.

  python gen_ledger.py   ->   ../web/public/ledger.html, and ../web/public/{lang}/ledger.html for every
                              published language (site_build.targets())

Every closed trade, the equity curve, the current state. Losers included, nothing
edited. The page carries the strategy's own verdict on itself: inside noise.

The page's words are keyed in web/i18n (ledger.*; the shared product.*, common.*, hypo.* and footer keys);
render_ledger(T, live) renders it in T's language. What the journal, state and config record stays data: the
figures, the timestamps, the instrument, the strategy's name and the engine's exit-reason codes. Recorded
values that the page shows as English words (side, entry kind, position, status, binding, exit label) have a
keyed label each; a value without one is shown as recorded.
"""
from __future__ import annotations
import csv, json, html, math, re, statistics, datetime as dt
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import i18n
import site_build
import site_text
from noise_math import expected_max_normal
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


def _english(T):
    """The English page, exactly as before. The pseudo-locale (i18n_pseudo.py) takes the translated path."""
    return T.code == "en" and not getattr(T, "pseudo", False)


def _style(T):
    """index.html's icon, og and font links and its stylesheet, with the ledger's own og title and description (a
    shared /ledger link previews as itself) and the language's og image."""
    og = site_build.og(T, "ledger")
    s = STYLE
    for prop, val in (("og:image", og["image"]), ("og:title", og["title"]), ("og:description", og["description"])):
        s = re.sub(rf'(<meta property="{prop}" content=")[^"]*(">)', lambda m, v=val: m.group(1) + v + m.group(2), s, count=1)
    return s


def header(T, live):
    """The ledger's bar (it has no <header> block, so not partials/_header.html): links inside T's language,
    the language switcher at the end of the nav. The mark is site_build.mark: the same on every page."""
    return f'''<div class="bar">
  {site_build.mark(T)}
  {site_build.nav(T, "ledger", live)}
</div>'''


def code(T, s):
    """A name or code the page shows as recorded (the instrument, the strategy's name, an engine exit-reason code):
    never translated. On a translated page it is isolated left to right and marked translate="no"."""
    s = html.escape(str(s), quote=False)
    return s if _english(T) else f'<bdi translate="no">{s}</bdi>'


def utc(T, iso):
    """A UTC time as the page shows it (YYYY-MM-DD HH:MM). On a translated page i18n.js puts the reader's local time
    before it, the UTC time staying beside it."""
    txt = iso[:16].replace("T", " ")
    if not iso or not site_build.features_on(T):
        return txt
    return f'<bdi data-utc="{html.escape(iso[:16], quote=True)}Z">{txt}</bdi>'


def word(T, section, value, markup=True):
    """A recorded value the page shows as an English word (ledger.{section}.{value}: side, kind, pos, status,
    binding, exit): its keyed label. A value with no key is shown as recorded, as data."""
    k = f"ledger.{section}.{value}"
    if k in T.en:
        return T(k)
    return code(T, value) if markup else str(value)


def flag(T):
    return f' <span title="{T.attr("ledger.flag.title")}">⚑</span>'


def equity_svg(T, rows, w=760, h=180):
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
  <span>${lo:,.0f}</span><span>{T("ledger.equity.start", quota=f"${QUOTA:,.0f}")}</span><span>${hi:,.0f}</span></div>'''


def heartbeat(T, st):
    """Last bar, balance, room, binding, position. No direction, no price, no stop."""
    if not st: return ""
    bar = utc(T, st.get("as_of_bar_utc", ""))
    pos = st.get("position")
    ptxt = (T("ledger.hb.open_since", since=utc(T, pos['open_since_utc']),
              filled=pos['tranches_filled'], total=pos['tranches'])
            if pos else T("ledger.pos.flat"))
    b = st.get("binding", "")
    binding = T(f"ledger.binding.{b}") if b and f"ledger.binding.{b}" in T.en else "—"
    return f'''<div class="cells">
<div class="c"><div class="k">{T("ledger.hb.last_bar")}</div><div class="v">{bar}</div><div class="hs">{T("ledger.hb.last_bar_note", close=f'{st.get("last_close", 0):,.0f}')}</div></div>
<div class="c"><div class="k">{T("ledger.cell.balance")}</div><div class="v">${st.get("balance", QUOTA):,.0f}</div><div class="hs">{T("ledger.hb.realized")}</div></div>
<div class="c"><div class="k">{T("ledger.hb.room")}</div><div class="v">${min(st.get("daily_room", 0), st.get("distance_to_floor", 0)):,.0f}</div><div class="hs">{T("ledger.hb.binding", binding=binding)}</div></div>
<div class="c"><div class="k">{T("ledger.cell.to_floor")}</div><div class="v">${st.get("distance_to_floor", 0):,.0f}</div><div class="hs">{T("ledger.hb.daily", amount=f'${st.get("daily_room", 0):,.0f}')}</div></div>
<div class="c" style="grid-column:span 2"><div class="k">{T("ledger.hb.position")}</div><div class="v" style="font-size:14px;margin-top:4px">{ptxt}</div><div class="hs">{T("ledger.hb.position_note")}</div></div>
</div>'''


def runs_table(T):
    """One row per shadow run in the last 7 days, from runs.csv."""
    if not RUNS.exists(): return f'<p class="hs" style="margin:0 0 14px">{T("ledger.runs.none_yet")}</p>'
    now = dt.datetime.now(dt.timezone.utc)
    rows = [r for r in csv.DictReader(RUNS.open()) if dt.datetime.fromisoformat(r["run_utc"]) >= now - dt.timedelta(days=7)]
    if not rows: return f'<p class="hs" style="margin:0 0 14px">{T("ledger.runs.none_7d")}</p>'
    body = "".join(f'<tr><td>{utc(T, r["run_utc"])}</td><td>{utc(T, r["as_of_bar_utc"])}</td>'
                   f'<td class="num">{float(r["balance"]):,.0f}</td><td class="num">{r["trades_new"]}</td><td>{word(T, "pos", r["position"])}</td></tr>'
                   for r in reversed(rows[-42:]))
    return (f'<div class="panel"><p class="eyebrow">{T("ledger.runs.eyebrow", n=len(rows))}</p><div class="scroll"><table>'
            f'<tr><th>{T("ledger.runs.th.run")}</th><th>{T("ledger.runs.th.bar")}</th><th class="num">{T("ledger.runs.th.balance")}</th>'
            f'<th class="num">{T("ledger.runs.th.closed")}</th><th>{T("ledger.runs.th.position")}</th></tr>{body}</table></div>'
            f'<p class="hs">{T("ledger.src.runs")}</p></div>')


def load_bars():
    """t,o,h,l,c rows; comment lines skipped. Returns (times, bars) with times in unix seconds."""
    if not BARS.exists(): return [], []
    rows = [r for r in csv.reader(BARS.open()) if r and not r[0].startswith("#")]
    if len(rows[0]) != 5: return [], []
    return [int(float(r[0])) for r in rows], [tuple(round(float(x), 2) for x in r[1:5]) for r in rows]


def when(iso):
    d = dt.datetime.fromisoformat(iso)
    return f"{d.month}/{d.day} {d:%H:%M}"


def trade_charts(T, rows):
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
                          entry_t=times[ei], exit_t=times[xi], exit_label=word(T, "exit", r["reason"], markup=False),
                          bars=[dict(time=times[i], open=bars[i][0], high=bars[i][1], low=bars[i][2], close=bars[i][3])
                                for i in range(lo, hi)]))
        sk = f"ledger.side_cap.{r['side']}"
        cap = T("ledger.charts.caption",
                side=T(sk) if sk in T.en else code(T, r["side"].capitalize()), kind=word(T, "kind", r["kind"]),
                entry_time=when(r["entry_utc"]), exit_time=when(r["exit_utc"]),
                entry=f"{entry:,.0f}", stop=f"{stop:,.0f}", stop_pct=f"{abs(entry - stop) / entry * 100:.2f}%",
                risk=f"${risk:,.0f}", risk_pct=f"{risk / bal_at[k] * 100:.1f}%",
                binding=word(T, "binding", r["binding_at_entry"]), room=f"${room:,.0f}",
                fills=html.escape(r["fills"]), tranches=html.escape(r["tranches"]), exit=word(T, "exit", r["reason"]),
                bars=html.escape(r["bars_held"]), r=f'{float(r["r"]):+.2f}R', fees=f'{float(r["fee_share_pct"]):.1f}%')
        fl = flag(T) if int(r.get("filled_bars") or 0) else ""
        caps.append(f'<div class="tc"><div class="tchart" id="tc{k}"></div><p class="tcap">{cap}{fl}</p></div>')
    if not items: return ""
    return (f'<div class="panel"><p class="eyebrow">{T("ledger.charts.eyebrow", n=len(items))}</p>'
            f'<p class="hs" style="margin:-8px 0 14px">{T("ledger.charts.note")}</p>'
            + "".join(caps) + f'<p class="hs">{T("ledger.src.charts")}</p></div>'
            + f'<script src="{LWC}"></script>\n<script>var TRADES=' + json.dumps(items, separators=(",", ":"), ensure_ascii=_english(T)) + ";\n"
            + "var T=" + T.js("ledger.js.") + ";\n" + F_JS + "\n" + CHART_JS + "</script>")


F_JS = r"function F(s,o){return s.replace(/\{(\w+)\}/g,function(m,k){return k in o?o[k]:m})}"

CHART_JS = r"""(function(){
  var cs=getComputedStyle(document.documentElement),C={};
  ["bg","surface","line","ink","dim","signal","bad"].forEach(function(k){C[k]=cs.getPropertyValue("--"+k).trim()});
  var mono=cs.getPropertyValue("--mono").trim()||"monospace";
  if(!window.LightweightCharts){document.querySelectorAll(".tchart").forEach(function(e){e.innerHTML='<p class="hs" style="padding:12px">'+T.nolib+'</p>'});return}
  var L=LightweightCharts;
  TRADES.forEach(function(t){
    var el=document.getElementById(t.id); if(!el)return;
    var chart=L.createChart(el,{autoSize:true,height:300,
      layout:{background:{type:"solid",color:C.surface},textColor:C.dim,fontFamily:mono,fontSize:10},
      grid:{vertLines:{color:C.line},horzLines:{color:C.line}},
      rightPriceScale:{borderColor:C.line},timeScale:{borderColor:C.line,timeVisible:true,secondsVisible:false},
      crosshair:{mode:L.CrosshairMode.Normal},handleScroll:false,handleScale:false});
    var s=chart.addCandlestickSeries({upColor:"transparent",downColor:C.dim,borderUpColor:C.ink,borderDownColor:C.dim,
      wickUpColor:C.ink,wickDownColor:C.dim,priceLineVisible:false,lastValueVisible:false});
    s.setData(t.bars);
    s.createPriceLine({price:t.entry,color:C.signal,lineWidth:1,lineStyle:L.LineStyle.Dotted,axisLabelVisible:true,title:T.entry});
    s.createPriceLine({price:t.stop,color:C.bad,lineWidth:1,lineStyle:L.LineStyle.Solid,axisLabelVisible:true,title:T.stop});
    t.tps.forEach(function(p,i){s.createPriceLine({price:p,color:C.dim,lineWidth:1,lineStyle:L.LineStyle.Dashed,axisLabelVisible:false,title:F(T.tp,{n:i+1})})});
    s.setMarkers([{time:t.entry_t,position:t.side>0?"belowBar":"aboveBar",color:C.signal,shape:t.side>0?"arrowUp":"arrowDown",text:T.entry},
                  {time:t.exit_t,position:t.side>0?"aboveBar":"belowBar",color:C.ink,shape:"circle",text:t.exit_label}]);
    chart.timeScale().fitContent();
  });
})();"""


def ledger_data():
    """What the page shows, from the journal, the state, the runs and the config."""
    rows = list(csv.DictReader(JOURNAL.open())) if JOURNAL.exists() else []
    st = json.loads(STATE.read_text()) if STATE.exists() else {}
    cfg = json.loads(CFG.read_text())
    n = len(rows); wins = sum(1 for r in rows if float(r["pnl"])>0)
    net = sum(float(r["pnl"]) for r in rows)
    rs = [float(r["r"]) for r in rows]
    exp = sum(rs)/n if n else 0
    se = statistics.stdev(rs)/math.sqrt(n) if n > 1 else 0.0
    noise30 = se*expected_max_normal(30)            # expected best of ~30 independent configs under a true zero edge
    flagged = sum(1 for r in rows if int(r.get("filled_bars") or 0) > 0)
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
    logged_live = [r for r in rows if r["logged_utc"] != rows[0]["logged_utc"]] if rows else []
    return dict(rows=rows, st=st, cfg=cfg, n=n, wins=wins, net=net, exp=exp, se=se, noise30=noise30,
                flagged=flagged, pf=pf, wk=wk, mo=mo, logged_live=logged_live)


def render_ledger(T, live):
    """troid's ledger in T's language, as HTML (site_build.GENERATED). T is an i18n.Strings, live the published
    language codes. English renders exactly as the page always has."""
    d = ledger_data()
    rows, st, cfg, n, exp, se, noise30 = d["rows"], d["st"], d["cfg"], d["n"], d["exp"], d["se"], d["noise30"]
    net, wk, mo = d["net"], d["wk"], d["mo"]

    trades_html = "".join(f'''<tr><td>{r["exit_utc"][:10]}</td><td>{word(T, "kind", r["kind"])}</td><td>{word(T, "side", r["side"])}</td>
<td class="num">{r["fills"]}</td><td class="num">{r["bars_held"]}</td><td>{code(T, r["reason"])}{flag(T) if int(r.get("filled_bars") or 0) else ''}</td>
<td class="num" style="color:{'var(--signal)' if float(r['pnl'])>0 else 'var(--bad)'}">{float(r["pnl"]):+,.2f}</td>
<td class="num">{float(r["r"]):+.2f}</td></tr>''' for r in reversed(rows[-40:]))

    # one sentence per outcome of the two tests, so each translates whole
    ci = "contains" if abs(exp) < 1.96*se else "excludes"
    chance = "below" if exp < noise30 else "above"
    warn = (T(f"ledger.warn.measure_{ci}_{chance}", exp=f"{exp:+.3f}R", n=n, se=f"{se:.3f}R", noise=f"{noise30:+.3f}R")
            + " " + T("ledger.warn.published") + "\n"
            + T("ledger.warn.logged", live=len(d["logged_live"]), date=rows[0]["logged_utc"][:10] if rows else "—")
            + (" " + T("ledger.warn.flagged", n=d["flagged"]) if d["flagged"] else ""))
    status = word(T, "status", st["outcome"]) if st.get("outcome") else "—"
    wk_r, mo_r = f'{sum(float(r["r"]) for r in wk):+.2f}R', f'{sum(float(r["r"]) for r in mo):+.2f}R'
    asof = T("ledger.hero.asof", asof=utc(T, st.get("as_of_bar_utc", "")) or "—",
             market=code(T, f'{cfg["instrument"]} {cfg["timeframe"]}'), profile=code(T, cfg["profile"]))

    return f'''<!DOCTYPE html><html{site_build.html_attrs(T)}><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{T("ledger.meta.title")}</title>
{_style(T)}
<style>.k{{font-family:var(--mono);font-size:9.5px;text-transform:uppercase;letter-spacing:.1em;color:var(--dim)}}
.v{{font-family:var(--mono);font-size:19px;font-weight:500;letter-spacing:-.02em}}
.cells{{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:1px;background:var(--line);border:1px solid var(--line);border-radius:3px;margin-bottom:14px}}
.c{{background:var(--surface);padding:12px}}
.hs{{font-family:var(--mono);font-size:10.5px;color:var(--dim);margin-top:3px}}
.warnbox{{border-inline-start:2px solid var(--warn);background:var(--surface2);padding:12px 14px;font-family:var(--mono);font-size:12px;color:var(--dim);margin-bottom:14px;line-height:1.6}}
.meta{{font-family:var(--mono);font-size:11px;color:var(--dim);margin:0 0 30px;letter-spacing:.02em}}table{{border-collapse:collapse;width:100%;font-size:13.5px;min-width:520px;font-family:var(--mono)}}th{{text-align:start;font-weight:500;color:var(--dim);font-size:10px;text-transform:uppercase;
  letter-spacing:.1em;padding:0 0 8px;padding-inline:0 10px;border-bottom:1px solid var(--line)}}td{{padding-block:9px;padding-inline:0 10px;border-bottom:1px solid var(--line);font-variant-numeric:tabular-nums}}tr:last-child td{{border-bottom:none}}.num{{text-align:end}}.foot{{font-family:var(--mono);font-size:11px;color:var(--dim);border-top:1px solid var(--line);
  margin-top:36px;padding-top:20px;line-height:1.8;text-align:start}}
.scroll{{overflow-x:auto;-webkit-overflow-scrolling:touch}}
.tc{{margin-bottom:18px}}.tchart{{height:300px;border:1px solid var(--line);border-radius:3px;overflow:hidden}}
.tcap{{font-family:var(--mono);font-size:11px;color:var(--dim);margin:6px 0 0;line-height:1.6}}</style>
{site_build.head_extra(T, "ledger", live)}</head><body><div class="wrap">
{header(T, live)}
{site_build.ticker(T)}
<p class="eyebrow" style="margin-top:28px;text-transform:none">{T("product.ledger")}</p>
<h1>{code(T, cfg["name"])}</h1>
<p class="lede">{T("ledger.hero.lede")}</p>
<p class="meta">{asof}</p>
<p class="meta" style="margin-top:-24px">{T("ledger.src.page")}</p>

{heartbeat(T, st)}
{runs_table(T)}
<div class="warnbox">{warn}</div>
{site_text.hypo_html(T=T)}

<div class="panel"><p class="eyebrow">{T("ledger.equity.eyebrow")}</p>{equity_svg(T, rows)}<p class="hs">{T("ledger.src.journal")}</p></div>

<div class="cells">
<div class="c"><div class="k">{T("ledger.cell.balance")}</div><div class="v">${st.get("balance",QUOTA):,.0f}</div></div>
<div class="c"><div class="k">{T("ledger.cell.net")}</div><div class="v" style="color:{'var(--signal)' if net>=0 else 'var(--bad)'}">{net:+,.0f}</div></div>
<div class="c"><div class="k">{T("ledger.cell.trades")}</div><div class="v">{n}</div></div>
<div class="c"><div class="k">{T("ledger.cell.win")}</div><div class="v">{(d["wins"]/n*100 if n else 0):.0f}%</div></div>
<div class="c"><div class="k">{T("ledger.cell.exp")}</div><div class="v">{exp:+.3f}R</div></div>
<div class="c"><div class="k">{T("ledger.cell.pf")}</div><div class="v">{d["pf"]:.2f}</div></div>
<div class="c"><div class="k">{T("ledger.cell.max_dd")}</div><div class="v">${st.get("max_drawdown",0):,.0f}</div></div>
<div class="c"><div class="k">{T("ledger.cell.to_floor")}</div><div class="v">${st.get("distance_to_floor",0):,.0f}</div></div>
</div>

<div class="cells">
<div class="c"><div class="k">{T("ledger.cell.week")}</div><div class="v">{T("ledger.cell.trades_r", n=len(wk), r=wk_r)}</div></div>
<div class="c"><div class="k">{T("ledger.cell.month")}</div><div class="v">{T("ledger.cell.trades_r", n=len(mo), r=mo_r)}</div></div>
<div class="c"><div class="k">{T("ledger.cell.status")}</div><div class="v">{status}</div></div>
</div>

<div class="panel"><p class="eyebrow">{T("ledger.trades.eyebrow", n=min(n,40))}</p><div class="scroll"><table>
<tr><th>{T("ledger.trades.th.closed")}</th><th>{T("ledger.trades.th.kind")}</th><th>{T("ledger.trades.th.side")}</th><th class="num">{T("ledger.trades.th.fills")}</th><th class="num">{T("ledger.trades.th.bars")}</th><th>{T("ledger.trades.th.exit")}</th><th class="num">{T("ledger.trades.th.pnl")}</th><th class="num">{T("ledger.trades.th.r")}</th></tr>
{trades_html}</table></div><p class="hs">{T("ledger.src.journal")}</p></div>

{trade_charts(T, rows)}

<p class="foot">{T("ledger.foot.week")} · {T("ledger.foot.feed")} · {T("ledger.foot.journal")}<br>{site_text.footer_html(T)}</p>
</div></body></html>'''


# The shadow loop runs every 4 hours (.github/workflows/shadow.yml, 20 minutes after each 4-hour bar closes). GitHub
# starts scheduled runs late and sometimes skips one: in the first nine runs the widest gap was 531 minutes and a run
# started up to 238 minutes after its bar closed. So the status light counts the ledger live while the last run is
# under three cadences and an hour old (780 minutes: one skipped run and a late next one), and the last bar it
# processed closed under 1,020 minutes ago (the same, plus a cadence of lag). A feed that stops delivering new bars
# stills the dot even while the runs go on.
CADENCE_MIN, BAR_MIN = 240, 240
STALE_AFTER_MIN = 3 * CADENCE_MIN + 60
BAR_STALE_AFTER_MIN = STALE_AFTER_MIN + CADENCE_MIN


def write_status(out=None):
    """web/public/status.json: when the shadow loop last ran, for the status light in every page's wordmark
    (web/public/live.js). Built from runs.csv and state.json only, so it changes only when a run does."""
    runs = list(csv.DictReader(RUNS.open())) if RUNS.exists() else []
    st = json.loads(STATE.read_text()) if STATE.exists() else {}
    status = {"what": "troid's ledger: when the shadow loop last ran and the last bar it processed. The wordmark's dot "
                      "ripples while the run is under stale_after_minutes old and the bar closed under "
                      "bar_stale_after_minutes ago, and holds still otherwise.",
              "last_run_utc": runs[-1]["run_utc"] if runs else None, "as_of_bar_utc": st.get("as_of_bar_utc"),
              "bar_minutes": BAR_MIN, "cadence_minutes": CADENCE_MIN, "stale_after_minutes": STALE_AFTER_MIN,
              "bar_stale_after_minutes": BAR_STALE_AFTER_MIN, "ledger": "/ledger"}
    path = (Path(out) if out else site_build.PUB) / "status.json"
    path.write_text(json.dumps(status, indent=1) + "\n")
    return path


def main(out=None):
    """Write the ledger for every published language (site_build.targets()); English to web/public/ledger.html.
    Also web/public/status.json, the status light's source."""
    live = site_build.targets()
    write_status(out)
    for c in live:
        p = site_build.out_path(c, "ledger", out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(render_ledger(i18n.Strings(c), live))
    d = ledger_data()
    print(f"ledger.html: {d['n']} trades, net {d['net']:+,.0f}, {len(d['logged_live'])} logged live -> "
          f"{site_build.out_path('en', 'ledger', out)}" + (f" (+ {', '.join(c for c in live if c != 'en')})" if len(live) > 1 else ""))


if __name__ == "__main__":
    main()
