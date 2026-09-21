#!/usr/bin/env python3
"""Render web/public/compare.html from firms.json. Three columns, alphabetical, PER-CELL verification.

Every cell shows its value if verified from the firm's own documents, 'pending' if not.
Derived cells compute only when their inputs exist. The same rule applies to every firm.
A firm's link shows once its affiliate agreement exists and daily/max/target/price are
verified. Nothing is scored. Nothing is ranked.
"""
from __future__ import annotations
import json, html
from pathlib import Path

HERE = Path(__file__).parent
FIRMS = json.loads((HERE.parent / "firms.json").read_text())
OUT = HERE.parent / "web" / "public" / "compare.html"
BRAND = (HERE.parent / "web" / "public" / "index.html").read_text()
STYLE = BRAND[BRAND.index('<link rel="preconnect"'):BRAND.index("</style>") + 8]
HEADER = '''<div class="bar">
  <a class="mark" href="/"><span class="dot"></span>troid</a>
  <nav><a href="/compare">compare</a><a href="/faq">faq</a><a href="/ledger">ledger</a>
    <a href="/dashboard">research</a><a href="https://github.com/kunjancollective/troid">source</a></nav>
</div>'''
ORDER = sorted(k for k in FIRMS if isinstance(FIRMS[k], dict) and "compare_product" in FIRMS[k])
FIELDS = ["daily_pct","max_pct","target_pct","min_days","price","daily_basis","drawdown_type","reset_utc",
          "fee_per_side_pct","max_leverage","hold_cap","max_open","refund","split","us_available",
          "consistency_rule","news_rule","profit_cap"]

def js(k, f):
    p = f["compare_product"]
    ag = f.get("affiliate_agreement") or {}
    link_ok = bool(f.get("affiliate_url")) and all(p.get(x) is not None for x in ("daily_pct","max_pct","target_pct","price"))
    return json.dumps({"name": f["name"], "p": p,
        "verified_n": sum(1 for x in FIELDS if p.get(x) is not None), "total": len(FIELDS),
        "open": f.get("_open_questions", []),
        "url": f.get("affiliate_url") if link_ok else None,
        "code": ag.get("customer_code"), "promo": f.get("_promo_note")})

def column(k, f):
    p = f["compare_product"]; n = sum(1 for x in FIELDS if p.get(x) is not None)
    tag = "good" if n == len(FIELDS) else ("warn" if n >= len(FIELDS)//2 else "bad")
    return f'''<div class="col" id="col-{k}">
  <div class="colhead"><div style="font-family:var(--mono);font-size:15px;font-weight:600">{html.escape(f["name"])}</div>
    <div class="s" style="margin-top:3px">{html.escape(p["label"])}</div>
    <div style="margin-top:7px"><span class="tag {tag}">{n} of {len(FIELDS)} verified</span></div></div>
  <div class="rows" id="rows-{k}"></div><div class="colfoot" id="foot-{k}"></div></div>'''

page = f'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>troid — compare</title>
{STYLE}
<style>
.cols{{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background:var(--line);border:1px solid var(--line);border-radius:4px;margin-top:14px}}
@media(max-width:760px){{.cols{{grid-template-columns:1fr}}}}
.col{{background:var(--surface);display:flex;flex-direction:column}}
.colhead{{padding:16px 16px 12px;border-bottom:1px solid var(--line)}}
.rows{{flex:1}}
.r{{display:flex;justify-content:space-between;gap:10px;padding:8px 16px;border-bottom:1px solid var(--line);font-family:var(--mono);font-size:12px}}
.r .l{{color:var(--dim);flex-shrink:0}}.r .v{{font-variant-numeric:tabular-nums;text-align:right}}
.r.sec{{background:var(--surface2);color:var(--dim);font-size:9.5px;text-transform:uppercase;letter-spacing:.12em;padding:6px 16px}}
.pend{{color:var(--dim);font-style:italic}}
.colfoot{{padding:14px 16px 16px;border-top:1px solid var(--line);font-family:var(--mono);font-size:11.5px;line-height:1.7;background:var(--surface2)}}
.inputs{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}}
@media(max-width:640px){{.inputs{{grid-template-columns:1fr 1fr}}}}
.s{{font-family:var(--mono);font-size:10.5px;color:var(--dim)}}
</style></head><body><div class="wrap">
{HEADER}
<h1>Three firms, your numbers.</h1>
<p class="lede">Enter your sizing once. Each column shows what that sizing costs under that firm's rules. Every cell
is verified from the firm's own documents or says <em>pending</em>. Nothing is scored.</p>
<p class="meta">alphabetical · one reference firm + two by external ranking · reviewed {html.escape(FIRMS.get("_last_review",""))}</p>
<div class="panel"><p class="eyebrow">Your sizing</p><div class="inputs">
  <div><label>Quota</label><input id="quota" type="number" value="100000"></div>
  <div><label>Risk % per trade</label><input id="risk" type="number" step="any" value="0.5"></div>
  <div><label>Stop % of price</label><input id="stop" type="number" step="any" value="1.66"></div>
  <div><label>Leverage you use</label><input id="lev" type="number" step="any" value="5"></div>
</div></div>
<div class="cols">{"".join(column(k, FIRMS[k]) for k in ORDER)}</div>
<p class="s" style="margin:16px 0 0;line-height:1.7">{html.escape(FIRMS.get("_reference_firm",""))} {html.escape(FIRMS.get("_bitfunded_directory_note",""))}</p>
<p class="s" style="margin:10px 0 0;line-height:1.7">{html.escape(FIRMS.get("_criterion",""))}</p>
<p class="s" style="margin:10px 0 0;line-height:1.7">{html.escape(FIRMS.get("_link_rule",""))}</p>
<p class="foot">{html.escape(FIRMS.get("_disclosure",""))} Not financial advice. Simulated trading. Verify every rule with the firm before purchase.</p>
</div>
<script>
var F={{{",".join(f'"{k}":{js(k, FIRMS[k])}' for k in ORDER)}}};var ORDER={json.dumps(ORDER)};
function n(id){{return parseFloat(document.getElementById(id).value)||0}}
function $(x){{return "$"+x.toLocaleString(undefined,{{maximumFractionDigits:0}})}}
var P='<span class="pend">pending</span>';
function v(x,fmt){{return (x===null||x===undefined)?P:(fmt?fmt(x):String(x))}}
function row(l,val){{return '<div class="r"><span class="l">'+l+'</span><span class="v">'+val+'</span></div>'}}
function sec(t){{return '<div class="r sec">'+t+'</div>'}}
function render(){{
  var Q=n("quota"),rp=n("risk")/100,s=n("stop")/100,lev=n("lev");
  ORDER.forEach(function(k){{
    var f=F[k],p=f.p,h="";
    var d=p.daily_pct!=null?p.daily_pct/100:null,m=p.max_pct!=null?p.max_pct/100:null;
    var isStatic=p.drawdown_type!=null&&String(p.drawdown_type).indexOf("static")===0;
    var known=d!=null&&m!=null, derivable=known&&p.drawdown_type!=null;
    h+=sec("rules");
    h+=row("daily loss",v(p.daily_pct,function(x){{return x+"% · "+$(Q*x/100)}}));
    h+=row("daily basis",v(p.daily_basis));
    h+=row("reset (UTC)",v(p.reset_utc));
    h+=row("max loss",v(p.max_pct,function(x){{return x+"% · "+$(Q*x/100)}}));
    h+=row("drawdown type",v(p.drawdown_type));
    h+=row("target",v(p.target_pct,function(x){{return x+"%"}}));
    h+=row("min days",v(p.min_days));
    h+=row("leverage cap",v(p.max_leverage,function(x){{return x+"×"}}));
    h+=row("hold cap",v(p.hold_cap));
    h+=row("open positions",v(p.max_open));
    h+=row("consistency rule",v(p.consistency_rule));
    h+=row("news rule",v(p.news_rule));
    h+=row("profit cap",v(p.profit_cap));
    h+=sec("at your sizing");
    var risk=rp*Q;
    h+=row("risk per trade",$(risk)+" ("+(rp*100).toFixed(2)+"%)");
    if(derivable&&isStatic){{
      var room=Q*(m-d),cross=Q*(1-m+d);
      h+=row("room before max loss binds",$(room)+" ("+((m-d)*100).toFixed(1)+"%)");
      h+=row("ceilings swap at",$(cross));
      h+=row("losses survivable",room>0&&risk>0?Math.floor(room/risk)+" at "+(rp*100).toFixed(2)+"%":"—");
    }}else if(derivable){{
      h+=row("room before max loss binds",'<span class="pend">trailing — moves with your high-water mark</span>');
      h+=row("ceilings swap at",'<span class="pend">not fixed under trailing</span>');
      h+=row("losses survivable",known?Math.floor(Q*m/risk)+" from a fresh start, fewer after any profit":P);
    }}else{{
      h+=row("room before max loss binds",P);h+=row("ceilings swap at",P);h+=row("losses survivable",P);
    }}
    if(p.fee_per_side_pct!=null){{var fee=p.fee_per_side_pct/100,drag=s>0?2*fee/(s+2*fee)*100:0;
      h+=row("fee drag at "+(s*100).toFixed(2)+"% stop",drag.toFixed(1)+"% of risk ("+p.fee_per_side_pct+"%/side)");}}
    else h+=row("fee drag",P);
    if(p.max_leverage!=null){{var L=Math.min(lev,p.max_leverage);h+=row("isolated liq. distance","~"+((1-(1-1/L))*100).toFixed(0)+"% at "+L+"×");}}
    else h+=row("isolated liq. distance",P);
    h+=sec("cost & access");
    h+=row("challenge fee",v(p.price));h+=row("refund",v(p.refund));h+=row("profit split",v(p.split));
    h+=row("US residents",v(p.us_available));
    var foot="";
    if(f.url){{foot='<a href="'+f.url+'" rel="sponsored noopener">'+f.name+' challenges</a> · our link';
      if(f.code)foot+='<br>discount code <b>'+f.code+'</b> — cheaper through this link';
      if(f.promo)foot+='<br><span style="color:var(--dim)">'+f.promo+'</span>';}}
    else foot='<span class="pend">Link appears once daily, max, target and price are verified from '+f.name+"'s documents.</span>";
    if(f.open&&f.open.length)foot+='<div style="margin-top:8px;color:var(--dim);font-size:10.5px">open: '+f.open.length+' question'+(f.open.length>1?'s':'')+' — '+f.open[0].split('.')[0]+(f.open.length>1?' …':'')+'</div>';
    document.getElementById("rows-"+k).innerHTML=h;document.getElementById("foot-"+k).innerHTML=foot;
  }});
}}
["quota","risk","stop","lev"].forEach(function(i){{document.getElementById(i).addEventListener("input",render)}});
render();
</script></body></html>'''
OUT.write_text(page)
cov={k:sum(1 for x in FIELDS if FIRMS[k]["compare_product"].get(x) is not None) for k in ORDER}
links=[k for k in ORDER if FIRMS[k].get("affiliate_url") and all(FIRMS[k]["compare_product"].get(x) is not None for x in ("daily_pct","max_pct","target_pct","price"))]
print(f"compare.html: coverage {cov} of {len(FIELDS)} · links live: {links}")
