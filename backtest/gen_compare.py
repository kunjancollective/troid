#!/usr/bin/env python3
"""Render web/public/compare.html from firms.json, and rewrite the marked regions of index.html and faq.html.

Three columns, alphabetical, PER-CELL verification. Everything firm-specific on the site comes from
firms.json: the firms panel on the landing page (<!-- firms:start/end -->) and every listed firm's
required_disclaimer in the FAQ disclaimer and both footers (<!-- disclaimers:start/end -->). The
generic text around those regions never names a firm.

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
STYLE = BRAND[BRAND.index('<link rel="icon"'):BRAND.index("</style>") + 8]
HEADER = '''<div class="bar">
  <a class="mark" href="/">tr<span class="dot"></span>id</a>
  <nav><a href="/compare">compare</a><a href="/faq">faq</a><a href="/ledger">ledger</a>
    <a href="/dashboard">research</a><a href="https://github.com/kunjancollective/troid">source</a></nav>
</div>'''
ORDER = sorted(k for k in FIRMS if isinstance(FIRMS[k], dict) and "compare_product" in FIRMS[k])
FIELDS = ["daily_pct","max_pct","target_pct","min_days","price","daily_basis","drawdown_type","reset_utc",
          "fee_per_side_pct","max_leverage","hold_cap","max_open","refund","split","us_available",
          "consistency_rule","news_rule","profit_cap"]

INDEX = HERE.parent / "web" / "public" / "index.html"
FAQ = HERE.parent / "web" / "public" / "faq.html"
RANK = {e["firm"]: (i + 1, e) for i, e in enumerate((FIRMS.get("_external_ranking_snapshot") or {}).get("top", []))}


def link_live(f):
    """The contract: a human set link_live, AND daily, max, target and price are verified from the firm's documents."""
    p = f["compare_product"]
    return (bool(f.get("link_live")) and bool(f.get("affiliate_url"))
            and all(p.get(x) is not None for x in ("daily_pct", "max_pct", "target_pct", "price")))


def required_sentences():
    """Every listed firm's required disclaimer, verbatim, while the firm is listed."""
    return [(FIRMS[k]["name"], FIRMS[k]["required_disclaimer"].strip())
            for k in ORDER if (FIRMS[k].get("required_disclaimer") or "").strip()]


def required_html(inline=False):
    items = required_sentences()
    if inline:
        return " ".join(html.escape(t) for _, t in items)
    return "\n".join(f"<p>{html.escape(t)}</p>" for _, t in items)


def panel_cell(k, f):
    p = f["compare_product"]; name = html.escape(f["name"])
    rank = RANK.get(f["name"])
    role = "reference" if f.get("reference") else (f"#{rank[0]} by reviews" if rank else "")
    head = f"{name} · {role}" if role else name
    if f.get("verified"):
        summary = f.get("panel_summary") or (f"{p['label']} {p['daily_pct']}% / {p['max_pct']}%"
                                             + (f" {p['drawdown_type']}" if p.get("drawdown_type") else ""))
        v = f'<div class="v" style="font-size:14px;margin:4px 0">{html.escape(summary)}</div>'
    else:
        v = '<div class="v" style="font-size:14px;margin:4px 0;color:var(--dim)">verification pending</div>'
    notes = []
    if rank: notes.append(f"{rank[1]['reviews']} verified reviews at {rank[1]['rating']} on propfirmmatch.")
    if f.get("panel_note"): notes.append(f["panel_note"])
    note = f'\n      <div class="s">{html.escape(" ".join(notes))}</div>' if notes else ""
    link = ""
    if link_live(f):
        code = (f.get("affiliate_agreement") or {}).get("customer_code")
        link = (f'\n      <div class="s" style="margin-top:8px"><a href="{html.escape(f["affiliate_url"])}" rel="sponsored noopener">'
                f'{name} challenges</a> · our link' + (f" · code {html.escape(code)}" if code else "")
                + (" · their promos apply here" if f.get("_promo_note") else "") + "</div>")
    return f'    <div class="cell">\n      <div class="k">{head}</div>\n      {v}{note}{link}\n    </div>'


def firms_panel_html():
    return ('  <div class="read" style="grid-template-columns:repeat(auto-fit,minmax(220px,1fr))">\n'
            + "\n".join(panel_cell(k, FIRMS[k]) for k in ORDER) + "\n  </div>")


def rewrite_region(path, tag, inner):
    """Replace everything between <!-- tag:start --> and <!-- tag:end --> in a static page. Returns True if it changed."""
    start, end = f"<!-- {tag}:start -->", f"<!-- {tag}:end -->"
    s = path.read_text(); i = s.index(start) + len(start); j = s.index(end)
    body = ("\n" + inner.strip("\n") + "\n") if inner.strip() else "\n"
    new = s[:i] + body + s[j:]
    if new != s:
        path.write_text(new); return True
    return False


def js(k, f):
    p = f["compare_product"]
    ag = f.get("affiliate_agreement") or {}
    link_ok = link_live(f)
    return json.dumps({"name": f["name"], "p": p,
        "verified_n": sum(1 for x in FIELDS if p.get(x) is not None), "total": len(FIELDS),
        "open": f.get("_open_questions", []),
        "url": f.get("affiliate_url") if link_ok else None,
        "code": ag.get("customer_code") if link_ok else None, "promo": f.get("_promo_note") if link_ok else None})

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
<p class="foot">{" ".join(x for x in (html.escape(FIRMS.get("_disclosure","")), required_html(inline=True)) if x)} Not financial advice. Simulated trading. Verify every rule with the firm before purchase.<br><a href="/faq">faq</a> · <a href="/ledger">ledger</a> · <a href="/dashboard">research</a> · <a href="https://github.com/kunjancollective/troid">source</a> · <a href="https://x.com/tradingdroid">x</a> · <a href="https://www.reddit.com/user/tradingdroid/">reddit</a></p>
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
    else foot='<span class="pend">Link appears when '+f.name+"'s affiliate agreement allows it and daily, max, target and price are verified from "+f.name+"'s documents.</span>";
    if(f.open&&f.open.length)foot+='<div style="margin-top:8px;color:var(--dim);font-size:10.5px">open: '+f.open.length+' question'+(f.open.length>1?'s':'')+' — '+f.open[0].split('.')[0]+(f.open.length>1?' …':'')+'</div>';
    document.getElementById("rows-"+k).innerHTML=h;document.getElementById("foot-"+k).innerHTML=foot;
  }});
}}
["quota","risk","stop","lev"].forEach(function(i){{document.getElementById(i).addEventListener("input",render)}});
render();
</script></body></html>'''
OUT.write_text(page)
cov={k:sum(1 for x in FIELDS if FIRMS[k]["compare_product"].get(x) is not None) for k in ORDER}
links=[k for k in ORDER if link_live(FIRMS[k])]
changed = [name for name, hit in (("index.html firms", rewrite_region(INDEX, "firms", firms_panel_html())),
                                  ("index.html disclaimers", rewrite_region(INDEX, "disclaimers", "  " + required_html(inline=True) if required_sentences() else "")),
                                  ("faq.html disclaimers", rewrite_region(FAQ, "disclaimers", required_html()))) if hit]
print(f"compare.html: coverage {cov} of {len(FIELDS)} · links live: {links} · required disclaimers: "
      f"{[n for n, _ in required_sentences()] or 'none'} · regions rewritten: {changed or 'none (already current)'}")
