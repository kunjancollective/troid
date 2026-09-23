#!/usr/bin/env python3
"""Render web/public/compare.html from firms.json, and rewrite the marked regions of index.html and faq.html.

Three columns, alphabetical, PER-CELL verification. Everything firm-specific on the site comes from
firms.json: the firms panel on the landing page (<!-- firms:start/end -->), the calculator's data
(<!-- profiles -->), the landing page's crossover stat with its provenance line (<!-- crossover -->), and the
shared footer (<!-- footer -->, from site_text.py) on every static page, which carries every listed firm's
required_disclaimer. The generic text around those regions never names a firm.

Every cell shows its value with its source and read date, 'source not yet recorded' where troid has a value
but no source, or 'pending' where it has no value. Derived cells compute only when their inputs exist. The
same rule applies to every firm. A firm's link shows once its affiliate agreement exists and daily, max,
target and price each have a recorded source (firms.json _link_rule); until then it is held. Nothing is
scored. Nothing is ranked.

The page renders once per published language (render_compare; site_build.py). Its words come from
web/i18n (compare.*, and the script's compare.js.*); text from firms.json (labels, rule values, the
criterion, link rule and disclosure, promo notes, open questions) goes through T.data, so a reviewed
translation of it shows and anything unreviewed stays in English. Rule-source names stay in English.
"""
from __future__ import annotations
import json, html, re, sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import i18n
import site_build
import site_text
FIRMS = json.loads((HERE.parent / "firms.json").read_text())
BRAND = (HERE.parent / "web" / "public" / "index.html").read_text()
STYLE = BRAND[BRAND.index('<link rel="icon"'):BRAND.index("</style>") + 8]
ORDER = sorted(k for k in FIRMS if isinstance(FIRMS[k], dict) and "compare_product" in FIRMS[k])
FIELDS = ["daily_pct","max_pct","target_pct","min_days","price","daily_basis","drawdown_type","reset_utc",
          "fee_per_side_pct","max_leverage","hold_cap","max_open","refund","split","us_available",
          "consistency_rule","news_rule","profit_cap"]

INDEX = HERE.parent / "web" / "public" / "index.html"
FAQ = HERE.parent / "web" / "public" / "faq.html"
PUB = HERE.parent / "web" / "public"
RANK = {e["firm"]: (i + 1, e) for i, e in enumerate((FIRMS.get("_external_ranking_snapshot") or {}).get("top", []))}


def cite(f, field, product=None, fallback=True):
    """Where a rule was read: {'c': section, 'o': [read dates]} from firms.json provenance, or None when no source
    is recorded. A product's own limits never fall back to the firm-level cite (that would credit one product's
    source to another); firm-wide rules do."""
    P = f.get("provenance") or {}
    ent = ((P.get("products") or {}).get(product) or {}).get(field) if product else None
    if product and field in (P.get("product_only") or []):
        fallback = False                                  # the firm-level cite covers one product only
    if ent is None and fallback:
        ent = (P.get("fields") or {}).get(field)
    if not ent:
        return None
    S = P.get("sources") or {}
    unknown = [i for i in ent["src"] if i not in S]
    assert not unknown, f"{f['name']}: provenance for {field} cites unknown source(s) {unknown}"
    sec = ent["section"]
    if sec.startswith(f["name"] + " "):
        sec = sec[len(f["name"]) + 1:]                    # the block already names the firm
    return {"c": sec.replace(" — ", ": "), "o": sorted({S[i]["read_on"] for i in ent["src"] if S[i].get("read_on")})}


PROV_TAIL = "Rules change without notice. Verify with the firm before trading."


def sourced(f, x, p):
    """A compare cell with a value and a recorded source — looked up the way the cell's provenance block is."""
    return p.get(x) is not None and cite(f, x, p.get("key")) is not None


def link_live(f):
    """The contract (firms.json _link_rule): a human set link_live, AND daily, max, target and price each have a
    recorded source. Until then the link is held."""
    p = f["compare_product"]
    return (bool(f.get("link_live")) and bool(f.get("affiliate_url"))
            and all(sourced(f, x, p) for x in ("daily_pct", "max_pct", "target_pct", "price")))


def required_sentences():
    """Every listed firm's required disclaimer, verbatim, while the firm is listed."""
    return [(FIRMS[k]["name"], FIRMS[k]["required_disclaimer"].strip())
            for k in ORDER if (FIRMS[k].get("required_disclaimer") or "").strip()]


def required_html(inline=False):
    items = required_sentences()
    if inline:
        return " ".join(html.escape(t) for _, t in items)
    return "\n".join(f"<p>{html.escape(t)}</p>" for _, t in items)


def rewrite_region(path, tag, inner):
    """Replace everything between <!-- tag:start --> and <!-- tag:end --> in a static page. Returns True if it changed."""
    start, end = f"<!-- {tag}:start -->", f"<!-- {tag}:end -->"
    s = path.read_text(); i = s.index(start) + len(start); j = s.index(end)
    body = ("\n" + inner.strip("\n") + "\n") if inner.strip() else "\n"
    new = s[:i] + body + s[j:]
    if new != s:
        path.write_text(new); return True
    return False


def _mark(T, s):
    """In the pseudo-locale (i18n_pseudo.py), mark text that reaches the page through T.data the way a keyed string
    is marked: it is translatable (by content), and the scan's data list does not carry firms.json's underscore-keyed
    prose (_criterion, _link_rule, _disclosure, _reference_firm, _promo_note, _open_questions). Otherwise unchanged."""
    return i18n.mark(s) if getattr(T, "pseudo", False) and isinstance(s, str) and s.strip() else s


def _data(T, s):
    """Text from firms.json in T's language: its reviewed translation, or the English as it is."""
    return _mark(T, T.data(s))


def _style(T):
    """index.html's icon, og and font links and its stylesheet. English: exactly as index.html has them; another
    language gets its own og title, description and image."""
    if T.code == "en":
        return STYLE
    og = site_build.og(T)
    s = STYLE
    for prop, val in (("og:image", og["image"]), ("og:title", og["title"]), ("og:description", og["description"])):
        s = re.sub(rf'(<meta property="{prop}" content=")[^"]*(">)', lambda m, v=val: m.group(1) + v + m.group(2), s, count=1)
    return s


def header(T, live):
    """The compare page's bar (it has no <header> block, so not partials/_header.html): links inside T's language,
    the language switcher at the end of the nav."""
    return f'''<div class="bar">
  <a class="mark" href="{T.H}">tr<span class="dot"></span>id</a>
  <nav><a href="{T.H}">{T("product.desk")}</a><a href="{T.L}/compare">{T("product.compare")}</a><a href="{T.L}/ledger">{T("product.ledger")}</a><a href="{T.L}/dashboard">{T("product.research")}</a><a href="{T.L}/chat">{T("product.ask")}</a><a href="{T.L}/faq">{T("common.nav.faq")}</a>
    <a href="https://github.com/kunjancollective/troid">{T("common.nav.source")}</a>{site_build.switcher(T, "compare", live)}</nav>
</div>'''


def js(k, f, T):
    """One firm's column data for the page's script. p holds the rule values as firms.json has them (the script's
    logic reads them); pt holds the ones whose text differs in T's language, which the script shows instead."""
    p = f["compare_product"]
    ag = f.get("affiliate_agreement") or {}
    link_ok = link_live(f)
    c = f.get("calc") or {}; pc = (c.get("products") or {}).get(p.get("key")) or {}
    pt = {}
    for x in FIELDS:
        if isinstance(p.get(x), str):
            t = _data(T, p[x])
            if t != p[x]:
                pt[x] = t
    qs = f.get("_open_questions") or []
    return json.dumps({"name": f["name"], "p": p, "pt": pt, "label": _data(T, p["label"]),
        "basis": pc.get("daily_basis", c.get("daily_basis")),
        "prov": dict({x: cite(f, x, p.get("key")) for x in FIELDS if p.get(x) is not None},
                     **{b["cite"]: cite(f, b["cite"]) for b in (c.get("lev_bands") or []) if "max_leverage" not in pc}),
        "levb": None if "max_leverage" in pc else c.get("lev_bands"),
        "verified_n": sum(1 for x in FIELDS if p.get(x) is not None), "total": len(FIELDS),
        "open_n": len(qs), "open1": _mark(T, T.data(qs[0]).split(".")[0]) if qs else None,
        "url": f.get("affiliate_url") if link_ok else None,
        "code": ag.get("customer_code") if link_ok else None,
        "promo": _data(T, f.get("_promo_note")) if link_ok else None})


def column(k, f, T):
    p = f["compare_product"]; n = sum(1 for x in FIELDS if p.get(x) is not None); m = sum(1 for x in FIELDS if sourced(f, x, p))
    tag = "good" if m == len(FIELDS) else ("warn" if m >= len(FIELDS)//2 else "bad")
    return f'''<div class="col" id="col-{k}">
  <div class="colhead"><div style="font-family:var(--mono);font-size:15px;font-weight:600">{html.escape(f["name"])}</div>
    <div class="s" style="margin-top:3px">{html.escape(_data(T, p["label"]))}</div>
    <div style="margin-top:7px"><span class="tag {tag}">{T("compare.col.tag", n=n, total=len(FIELDS), m=m)}</span></div></div>
  <div class="rows" id="rows-{k}"></div><div class="colfoot" id="foot-{k}"></div></div>'''


def render_compare(T, live):
    """troid's compare in T's language, as HTML (site_build.GENERATED). T is an i18n.Strings, live the published
    language codes. English renders exactly as the page did before it was keyed."""
    gov = site_build.governs_html(T, "legal.summary.citations")
    D = lambda key: html.escape(_data(T, FIRMS.get(key, "")))   # noqa: E731
    return f'''<!DOCTYPE html><html{site_build.html_attrs(T)}><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{T("compare.meta.title")}</title>
{_style(T)}
<style>
.cols{{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background:var(--line);border:1px solid var(--line);border-radius:4px;margin-top:14px}}
@media(max-width:760px){{.cols{{grid-template-columns:1fr}}}}
.col{{background:var(--surface);display:flex;flex-direction:column}}
.colhead{{padding:16px 16px 12px;border-bottom:1px solid var(--line)}}
.rows{{flex:1}}
.r{{padding:8px 16px;border-bottom:1px solid var(--line);font-family:var(--mono);font-size:12px}}
.r .rt{{display:flex;justify-content:space-between;gap:10px}}.r .pv{{font-size:9.5px;line-height:1.5;color:var(--dim);margin-top:4px}}
.r .pv code{{font-size:9.5px;padding:0 3px}}.r .l{{color:var(--dim);flex-shrink:0}}.r .v{{font-variant-numeric:tabular-nums;text-align:right}}
.r.sec{{background:var(--surface2);color:var(--dim);font-size:9.5px;text-transform:uppercase;letter-spacing:.12em;padding:6px 16px}}
.pend{{color:var(--dim);font-style:italic}}
.colfoot{{padding:14px 16px 16px;border-top:1px solid var(--line);font-family:var(--mono);font-size:11.5px;line-height:1.7;background:var(--surface2)}}
.inputs{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}}
@media(max-width:640px){{.inputs{{grid-template-columns:1fr 1fr}}}}
.s{{font-family:var(--mono);font-size:10.5px;color:var(--dim)}}
.foot{{font-family:var(--mono);font-size:11px;color:var(--dim);border-top:1px solid var(--line);margin-top:36px;padding-top:20px;line-height:1.8}}
</style>{site_build.head_extra(T, "compare", live)}</head><body><div class="wrap">
{header(T, live)}
<p class="eyebrow" style="margin-top:28px;text-transform:none">{T("product.compare")}</p>
<h1>{T("compare.hero.h1")}</h1>
<p class="lede">{T("compare.hero.lede")}</p>
<p class="meta">{T("compare.hero.meta", date=html.escape(FIRMS.get("_last_review","")))}</p>
{gov + chr(10) if gov else ""}<div class="panel"><p class="eyebrow">{T("compare.sizing.h")}</p><div class="inputs">
  <div><label>{T("compare.sizing.quota")}</label><input id="quota" type="number" value="100000"></div>
  <div><label>{T("compare.sizing.risk")}</label><input id="risk" type="number" step="any" value="0.5"></div>
  <div><label>{T("compare.sizing.stop")}</label><input id="stop" type="number" step="any" value="1.66"></div>
  <div><label>{T("compare.sizing.lev")}</label><input id="lev" type="number" step="any" value="5"></div>
</div></div>
<div class="cols">{"".join(column(k, FIRMS[k], T) for k in ORDER)}</div>
<p class="s" style="margin:16px 0 0;line-height:1.7">{D("_reference_firm")} {D("_bitfunded_directory_note")}</p>
<p class="s" style="margin:10px 0 0;line-height:1.7">{D("_criterion")}</p>
<p class="s" style="margin:10px 0 0;line-height:1.7">{D("_link_rule")}</p>
<p class="s" style="margin:10px 0 0;line-height:1.7">{D("_disclosure")}</p>
<p class="foot">{site_text.footer_html(T)}</p>
</div>
<script>
var FIRMS={{{",".join(f'"{k}":{js(k, FIRMS[k], T)}' for k in ORDER)}}};var ORDER={json.dumps(ORDER)};
var T={T.js("compare.js.")},LANG="{T.code}";
function F(s,o){{return s.replace(/\\{{(\\w+)\\}}/g,function(m,k){{return k in o?o[k]:m}})}}
function n(id){{return parseFloat(document.getElementById(id).value)||0}}
function $(x){{return "$"+x.toLocaleString(undefined,{{maximumFractionDigits:0}})}}
var P='<span class="pend">'+T.pending+'</span>';
function v(x,fmt){{return (x===null||x===undefined)?P:(fmt?fmt(x):String(x))}}
function esc(x){{return String(x).replace(/[&<>"]/g,function(c){{return{{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}}[c]}})}}
var LAB={{}};for(var lk in T)if(lk.indexOf("lab_")===0)LAB[lk.slice(4)]=T[lk];
/* The provenance block under every number: firm, product, the date troid read each rule, the section, the formula.
   Section names stay in English, as each firm publishes them. */
var PROV_TAIL={json.dumps(T("prov.tail"), ensure_ascii=False)};
function andj(a){{return a.length<2?a.join(""):F(T.list_and,{{a:a.slice(0,-1).join(", "),b:a[a.length-1]}})}}
function pv(f,keys,formula){{
  var by={{}},order=[],dates=[],miss=[];
  keys.forEach(function(x){{var c=f.prov[x];if((x in f.p)&&(f.p[x]===null||f.p[x]===undefined))return;
    if(!c){{miss.push(LAB[x]||x);return}}
    if(!by[c.c]){{by[c.c]={{labs:[],o:c.o}};order.push(c.c)}}by[c.c].labs.push(LAB[x]||x);
    c.o.forEach(function(d){{if(dates.indexOf(d)<0)dates.push(d)}})}});
  dates.sort();
  var t,o={{firm:esc(f.name),product:esc(f.label),missing:miss.join(", "),tail:PROV_TAIL}};
  if(order.length){{
    o.dates=andj(dates);
    o.sources=(order.length===1&&keys.length===1)?esc(order[0]):order.map(function(c){{
      return F(dates.length>1&&by[c].o.length?T.pv_src_read:T.pv_src,{{labels:by[c].labs.join(", "),source:esc(c),dates:andj(by[c].o)}})}}).join(" · ");
    t=F(miss.length?T.pv_dated_miss:T.pv_dated,o);
  }}else t=F(miss.length?T.pv_miss:T.pv_plain,o);
  if(formula)t+=" <code>"+formula+"</code>";
  return '<div class="pv">'+t+'</div>';
}}
function row(l,val,prov){{return '<div class="r"><div class="rt"><span class="l">'+l+'</span><span class="v">'+val+'</span></div>'+(prov||"")+'</div>'}}
function rr(f,l,x,fmt,formula){{var val=f.p[x];return row(l,v(x in f.pt?f.pt[x]:val,fmt),val===null||val===undefined?"":pv(f,[x],formula))}}
function sec(t){{return '<div class="r sec">'+t+'</div>'}}
function render(){{
  var Q=n("quota"),rp=n("risk")/100,s=n("stop")/100,lev=n("lev");
  ORDER.forEach(function(k){{
    var f=FIRMS[k],p=f.p,h="";
    var d=p.daily_pct!=null?p.daily_pct/100:null,m=p.max_pct!=null?p.max_pct/100:null;
    var isStatic=p.drawdown_type!=null&&String(p.drawdown_type).indexOf("static")===0;
    var known=d!=null&&m!=null, derivable=known&&p.drawdown_type!=null&&p.daily_basis!=null;
    h+=sec(T.sec_rules);
    h+=row(T.row_daily_loss,v(p.daily_pct,function(x){{return x+"% · "+$(Q*x/100)}}),p.daily_pct==null?"":pv(f,["daily_pct","daily_basis"],
      f.basis==="day_start"?T.f_daily_day_start:T.f_daily));
    h+=rr(f,T.row_daily_basis,"daily_basis");
    h+=rr(f,T.row_reset,"reset_utc");
    h+=row(T.row_max_loss,v(p.max_pct,function(x){{return x+"% · "+$(Q*x/100)}}),p.max_pct==null?"":pv(f,["max_pct","drawdown_type"],
      isStatic?T.f_max:T.f_max_trailing));
    h+=rr(f,T.row_drawdown_type,"drawdown_type");
    h+=rr(f,T.row_target,"target_pct",function(x){{return x+"%"}});
    h+=rr(f,T.row_min_days,"min_days");
    h+=rr(f,T.row_leverage_cap,"max_leverage",function(x){{return x+"×"}});
    h+=rr(f,T.row_hold_cap,"hold_cap");
    h+=rr(f,T.row_open_positions,"max_open");
    h+=rr(f,T.row_consistency_rule,"consistency_rule");
    h+=rr(f,T.row_news_rule,"news_rule");
    h+=rr(f,T.row_profit_cap,"profit_cap");
    h+=sec(T.sec_sizing);
    var risk=rp*Q;
    h+=row(T.row_risk,$(risk)+" ("+(rp*100).toFixed(2)+"%)",'<div class="pv">'+T.pv_inputs+' <code>'+T.f_risk+'</code></div>');
    var K=["daily_pct","max_pct","daily_basis","drawdown_type"];
    var cross=null,cf="";
    if(derivable&&isStatic){{
      if(f.basis==="initial"||f.basis==="max_balance_equity"){{cross=Q*(1-m+d);cf=T.f_cf_initial;}}
      else if(f.basis==="day_start"){{cross=Q*(1-m)/(1-d);cf=T.f_cf_day_start;}}
    }}
    if(cross!==null){{
      var room=Q-cross;
      h+=row(T.row_room,$(room)+" ("+(room/Q*100).toFixed(1)+"%)",pv(f,K,F(T.f_room,{{cf:cf}})));
      h+=row(T.row_cross,$(cross),pv(f,K,F(T.f_cross,{{cf:cf}})));
      h+=row(T.row_losses,room>0&&risk>0?F(T.v_losses,{{n:Math.floor(room/risk),pct:(rp*100).toFixed(2)}}):"—",pv(f,K,T.f_losses));
      h+=row(T.row_survive,risk>0?F(T.v_survive,{{n:Math.floor(Q*m/risk)}}):"—",pv(f,["max_pct","drawdown_type"],T.f_survive));
    }}else if(derivable&&!isStatic){{
      h+=row(T.row_room,'<span class="pend">'+T.v_room_trail+'</span>',pv(f,["drawdown_type"]));
      h+=row(T.row_cross,'<span class="pend">'+T.v_cross_trail+'</span>',pv(f,["drawdown_type"]));
      h+=row(T.row_losses,'<span class="pend">'+T.v_losses_trail+'</span>',pv(f,["drawdown_type"]));
      h+=row(T.row_survive,risk>0?F(T.v_survive_trail,{{n:Math.floor(Q*m/risk)}}):"—",pv(f,["max_pct","drawdown_type"],T.f_survive));
    }}else{{
      h+=row(T.row_room,P);h+=row(T.row_cross,P);h+=row(T.row_losses,P);h+=row(T.row_survive,P);
    }}
    if(p.fee_per_side_pct!=null){{var fee=p.fee_per_side_pct/100,drag=s>0?2*fee/(s+2*fee)*100:0;
      h+=row(F(T.row_fee_at,{{stop:(s*100).toFixed(2)}}),F(T.v_fee,{{drag:drag.toFixed(1),fee:p.fee_per_side_pct}}),pv(f,["fee_per_side_pct"],T.f_fee));}}
    else h+=row(T.row_fee,P);
    var cap=p.max_leverage,ck="max_leverage";
    if(f.levb){{cap=null;f.levb.forEach(function(b){{if((b.max_quota==null||Q<=b.max_quota)&&(b.min_quota==null||Q>=b.min_quota)){{cap=b.lev;ck=b.cite}}}})}}
    if(cap!=null){{var L=Math.min(lev,cap);h+=row(T.row_liq,F(T.v_liq,{{pct:((1-(1-1/L))*100).toFixed(0),lev:L}}),pv(f,[ck],F(T.f_liq,{{cap:cap,quota:$(Q)}})));}}
    else h+=row(T.row_liq,P);
    h+=sec(T.sec_cost);
    h+=rr(f,T.row_price,"price");h+=rr(f,T.row_refund,"refund");h+=rr(f,T.row_split,"split");
    h+=rr(f,T.row_us,"us_available");
    var foot="";
    if(f.url){{foot=F(T.foot_link,{{url:f.url,name:f.name}});
      if(f.code)foot+='<br>'+F(T.foot_code,{{code:f.code}});
      if(f.promo)foot+='<br><span style="color:var(--dim)">'+f.promo+'</span>';}}
    else foot='<span class="pend">'+F(T.foot_held,{{name:f.name}})+'</span>';
    if(f.open_n)foot+='<div style="margin-top:8px;color:var(--dim);font-size:10.5px">'+F(f.open_n>1?T.foot_open_n:T.foot_open_1,{{n:f.open_n,first:f.open1}})+'</div>';
    document.getElementById("rows-"+k).innerHTML=h;document.getElementById("foot-"+k).innerHTML=foot;
  }});
}}
["quota","risk","stop","lev"].forEach(function(i){{document.getElementById(i).addEventListener("input",render)}});
render();
</script></body></html>'''


def main():
    live = site_build.targets()
    for code in live:
        out = site_build.out_path(code, "compare")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render_compare(i18n.Strings(code), live))
    cov={k:sum(1 for x in FIELDS if FIRMS[k]["compare_product"].get(x) is not None) for k in ORDER}
    links=[k for k in ORDER if link_live(FIRMS[k])]
    import regions
    templated = {pg for pg in site_build.STATIC if (site_build.TEMPLATES / f"{pg}.html").exists()}
    changed = [name for name, hit in (("index.html firms", "index" not in templated and rewrite_region(INDEX, "firms", regions.firms_panel_html())),
                                      ("index.html profiles", "index" not in templated and rewrite_region(INDEX, "profiles", regions.profiles_js())),
                                      ("index.html crossover", "index" not in templated and rewrite_region(INDEX, "crossover", regions.crossover_html())),
                                      ("dashboard.html hypo", "dashboard" not in templated and rewrite_region(PUB / "dashboard.html", "hypo", site_text.hypo_html())),
                                      *((f"{pg}.html footer", rewrite_region(PUB / f"{pg}.html", "footer", site_text.footer_html()))
                                        for pg in ("index", "faq", "dashboard", "chat", "terms")
                                        if (PUB / f"{pg}.html").exists() and pg not in templated)) if hit]
    changed += site_build.render_static(site_build.targets())
    changed += [f"removed {c}/" for c in site_build.prune()]
    # Context bundle for the assistant function (web/api/troid.js): a copy of firms.json outside
    # public/, packaged into the function by vercel.json includeFiles. Not served as a page.
    CONTEXT = HERE.parent / "web" / "context" / "firms.json"
    CONTEXT.parent.mkdir(exist_ok=True)
    if not CONTEXT.exists() or CONTEXT.read_bytes() != (HERE.parent / "firms.json").read_bytes():
        CONTEXT.write_bytes((HERE.parent / "firms.json").read_bytes()); changed.append("context/firms.json")
    print(f"compare.html: coverage {cov} of {len(FIELDS)} · links live: {links} · required disclaimers: "
          f"{[n for n, _ in required_sentences()] or 'none'} · regions rewritten: {changed or 'none (already current)'}")


if __name__ == "__main__":
    main()
