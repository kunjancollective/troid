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
target and price each have a recorded source (firms.json _link_rule, the page's words; _link_rule_impl, the check);
until then it is held. Nothing is
scored. Nothing is ranked.

The columns are in the page as served, sized at the page's default inputs (DEFAULTS; static_column, numbers written by
jsnum.py as the browser writes them), so a reader without the script and a search or AI crawler read every value with
its provenance line (launch handoff 2026-09-26, 5.1 item 4). The script's render() redraws them on load and on every
input; at the defaults it writes the same HTML, which web/test_compare_static.py holds in Chromium for every language.
A change to render() is a change to static_column(), and the test says so.

The page renders once per published language (render_compare; site_build.py). Its words come from
web/i18n (compare.*, and the script's compare.js.*); text from firms.json (labels, rule values, the
criterion, link rule and disclosure, promo notes, open questions) goes through T.data, so a reviewed
translation of it shows and anything unreviewed stays in English. Rule-source names stay in English.
"""
from __future__ import annotations
import json, html, math, re, sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import i18n
import jsnum
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
    """The contract (firms.json _link_rule_impl): a human set link_live, AND daily, max, target and price each have a
    recorded source. Until then the link is held."""
    p = f["compare_product"]
    return (bool(f.get("link_live")) and bool(f.get("affiliate_url"))
            and all(sourced(f, x, p) for x in ("daily_pct", "max_pct", "target_pct", "price")))


def last_read():
    """The most recent date troid read any firm document: every read_on in firms.json. troid's compare shows it as
    'reviewed', so the date moves when a read is recorded and never by hand."""
    dates = []
    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if k == "read_on" and isinstance(v, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
                    dates.append(v)
                else:
                    walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(FIRMS)
    return max(dates)


def reference():
    """The reference firm's entry (firms.json 'reference')."""
    return FIRMS[next(k for k in ORDER if FIRMS[k].get("reference"))]


def conflicts_html(T, f):
    """A firm's logged conflicts between its own documents (_conflicts_found), each side with its document, linked, and
    the date troid read it, then what troid shows. Document labels and wording go through T.data."""
    S = (f.get("provenance") or {}).get("sources") or {}
    items = []
    for c in f.get("_conflicts_found") or []:
        sides = []
        for s in c["sides"]:
            src = S.get(s.get("src")) or {}
            doc = html.escape(T.data(s["doc"]))
            if src.get("url"):
                doc = f'<a href="{html.escape(src["url"])}">{doc}</a>'
            read = src.get("read_on") or s.get("read_on")
            when = T("compare.conflicts.read", date=read) if read else T("compare.conflicts.unread")
            sides.append(f'{doc} ({when}): {html.escape(T.data(s["says"]))}')
        items.append(f'<li><strong>{html.escape(T.data(c["topic"]))}</strong>. {" · ".join(sides)}. '
                     f'{T("compare.conflicts.troid", what=html.escape(T.data(c["troid"])))}</li>')
    if not items:
        return ""
    return (f'<div class="s" style="margin:10px 0 0;line-height:1.7"><p style="margin:0">'
            f'{T("compare.conflicts.h", firm=html.escape(f["name"]), n=len(items))}</p>\n'
            f'<ul style="margin:4px 0 0;padding-inline-start:18px">{"".join(items)}</ul></div>\n')


def required_sentences():
    """Every listed firm's required disclaimer, verbatim, while the firm is listed."""
    return [(FIRMS[k]["name"], FIRMS[k]["required_disclaimer"].strip())
            for k in ORDER if (FIRMS[k].get("required_disclaimer") or "").strip()]


def required_span(T, f):
    """A firm's required sentence (firms.json required_disclaimer), verbatim: the firm's own words, so in English on
    every page. It sits beside the firm's link wherever troid shows one (this page's column foot, the desk's firms
    panel) and in the terms' affiliate notices; the site-wide footer names no firm (design handoff 2026-09-24, 2d)."""
    lang = "" if site_text._english(T) else ' lang="en"'
    return f'<span{lang}>{html.escape(f["required_disclaimer"].strip())}</span>'


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


# Translated pages only (site_build.features_on): the daily reset gets the reader's local time beside it, the
# firm's link sits in a block i18n.js can replace with "not available in <country> per the firm's terms".
RESET_FMT = ',function(x){return /^\\d\\d?:\\d\\d([–-]\\d\\d?:\\d\\d)?$/.test(x)?\'<bdi data-utc-hm="\'+x+\'">\'+x+\' UTC</bdi>\':x}'
AVAIL_WRAP = "\n      foot='<div data-avail-link>'+foot+'</div>';"
AFTER_RENDER = "\n  TROID.avail_apply(document);TROID.times(document);"


def _numbers(T):
    """The page's number helpers: English exactly as before; a translated page formats in its locale (i18n.js)."""
    if site_build.features_on(T):
        return ("function fx(x,d){return TROID.fixed(x,d)}function tl(x,o){return TROID.num(x,o)}"
                "function $(x){return TROID.usd(x,0)}")
    return ("function fx(x,d){return x.toFixed(d)}function tl(x,o){return x.toLocaleString(undefined,o)}"
            'function $(x){return "$"+tl(x,{maximumFractionDigits:0})}')


def _style(T):
    """index.html's icon, og and font links and its stylesheet, with the compare page's own og title and description
    (a shared /compare link previews as itself) and the language's og image."""
    og = site_build.og(T, "compare")
    s = re.sub(r'<meta name="twitter:card"[^>]*>\n?', "", STYLE)     # head_extra writes the card, on every page
    for prop, val in (("og:image", og["image"]), ("og:title", og["title"]), ("og:description", og["description"])):
        s = re.sub(rf'(<meta property="{prop}" content=")[^"]*(">)', lambda m, v=val: m.group(1) + v + m.group(2), s, count=1)
    return s


def header(T, live):
    """The compare page's bar (it has no <header> block, so not partials/_header.html): links inside T's language,
    the language switcher at the end of the nav."""
    return f'''<div class="bar">
  {site_build.mark(T)}
  {site_build.nav(T, "compare", live)}
</div>'''


def js_data(k, f, T):
    """One firm's column data for the page's script. p holds the rule values as firms.json has them (the script's
    logic reads them); pt holds the ones whose text differs in T's language, which the script shows instead."""
    p = f["compare_product"]
    code = f.get("affiliate_code") or (f.get("affiliate_agreement") or {}).get("customer_code")   # public: it is in the link
    link_ok = link_live(f)
    c = f.get("calc") or {}; pc = (c.get("products") or {}).get(p.get("key")) or {}
    pt = {}
    for x in FIELDS:
        if isinstance(p.get(x), str):
            t = T.data(p[x])
            if t != p[x]:
                pt[x] = t
    qs = f.get("_open_questions") or []
    return {"name": f["name"], "p": p, "pt": pt, "label": T.data(p["label"]),
        "basis": pc.get("daily_basis", c.get("daily_basis")),
        "prov": dict({x: cite(f, x, p.get("key")) for x in FIELDS if p.get(x) is not None},
                     **{b["cite"]: cite(f, b["cite"]) for b in (c.get("lev_bands") or []) if "max_leverage" not in pc}),
        "levb": None if "max_leverage" in pc else c.get("lev_bands"),
        "verified_n": sum(1 for x in FIELDS if p.get(x) is not None), "total": len(FIELDS),
        "open_n": len(qs), "open1": T.data(qs[0]).split(".")[0] if qs else None,
        "url": f.get("affiliate_url") if link_ok else None,
        "code": code if link_ok else None,
        "promo": T.data(f.get("_promo_note")) if link_ok else None,
        "req": required_span(T, f) if link_ok and (f.get("required_disclaimer") or "").strip() else None}


def js(k, f, T):
    return json.dumps(js_data(k, f, T), ensure_ascii=site_text._english(T))


# The page's inputs as it opens. Its script sizes every column at these, and the page carries the columns already
# sized at them, so a reader without the script, and a search or AI crawler, reads each firm's rules with their sources
# (launch handoff 2026-09-26, 5.1 item 4: until then the columns were empty until the script ran).
DEFAULTS = {"quota": 100000, "risk": 0.5, "stop": 1.66, "lev": 5}
RESET_HM = re.compile(r"[0-9][0-9]?:[0-9][0-9]([–-][0-9][0-9]?:[0-9][0-9])?")      # the script's reset test, ASCII digits


def _fmt(T):
    """The page's $ and fx, as _numbers(T) defines them in its script: Intl in the page's locale where the reading
    aids are on, otherwise toLocaleString and toFixed as an en-US browser writes them."""
    if site_build.features_on(T):
        I = jsnum.Intl(T.lang)
        return (lambda x: I.usd(x, 0)), I.fixed
    en = jsnum.Intl(i18n.BY_CODE["en"])
    return (lambda x: "$" + en.num(x, 0)), jsnum.to_fixed


def static_column(d, T, inputs=DEFAULTS):
    """One firm's rows and column foot as the page's render() writes them at inputs: the same HTML, in the page before
    the script runs. d is the firm's js_data(). Each step mirrors render() line for line (render() stays the page's
    only logic once it runs); web/test_compare_static.py holds the two equal in Chromium, every language."""
    J = json.loads(T.js("compare.js."))
    usd, fx = _fmt(T)
    features = site_build.features_on(T)
    LAB = {k[4:]: v for k, v in J.items() if k.startswith("lab_")}
    tail, lc = T("prov.tail"), T("index.js.list_comma")
    P = '<span class="pend">' + J["pending"] + '</span>'
    f, p = d, d["p"]
    S = jsnum.js_str

    def F(s, o):
        return re.sub(r"\{([A-Za-z0-9_]+)\}", lambda m: S(o[m.group(1)]) if m.group(1) in o else m.group(0), s)

    def esc(x):
        return S(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

    def v(x, fmt=None):
        return P if x is None else (fmt(x) if fmt else S(x))

    def lst(a):
        if not a:
            return ""
        acc = a[0]
        for y in a[1:]:
            acc = F(lc, {"a": acc, "b": y})
        return acc

    def andj(a):
        return "".join(a) if len(a) < 2 else F(J["list_and"], {"a": lst(a[:-1]), "b": a[-1]})

    def pv(keys, formula=None):
        by, order, dates, miss = {}, [], [], []
        for x in keys:
            c = f["prov"].get(x)
            if x in p and p[x] is None:
                continue
            if not c:
                miss.append(LAB.get(x) or x)
                continue
            if c["c"] not in by:
                by[c["c"]] = {"labs": [], "o": c["o"]}
                order.append(c["c"])
            by[c["c"]]["labs"].append(LAB.get(x) or x)
            for dt in c["o"]:
                if dt not in dates:
                    dates.append(dt)
        dates.sort()
        o = {"firm": esc(f["name"]), "product": esc(f["label"]), "missing": lst(miss), "tail": tail}
        if order:
            o["dates"] = andj(dates)
            o["sources"] = esc(order[0]) if len(order) == 1 and len(keys) == 1 else " · ".join(
                F(J["pv_src_read"] if len(dates) > 1 and by[c]["o"] else J["pv_src"],
                  {"labels": lst(by[c]["labs"]), "source": esc(c), "dates": andj(by[c]["o"])}) for c in order)
            t = F(J["pv_dated_miss"] if miss else J["pv_dated"], o)
        else:
            t = F(J["pv_miss"] if miss else J["pv_plain"], o)
        if formula:
            t += " <code>" + formula + "</code>"
        return '<div class="pv">' + t + '</div>'

    def row(l, val, prov=""):
        return '<div class="r"><div class="rt"><span class="l">' + l + '</span><span class="v">' + val + '</span></div>' + (prov or "") + '</div>'

    def rr(l, x, fmt=None, formula=None):
        val = p.get(x)
        return row(l, v(f["pt"][x] if x in f["pt"] else val, fmt), "" if val is None else pv([x], formula))

    def sec(t):
        return '<div class="r sec">' + t + '</div>'

    def reset(x):
        return '<bdi data-utc-hm="' + S(x) + '">' + S(x) + ' UTC</bdi>' if RESET_HM.fullmatch(S(x)) else S(x)

    Q, rp, s, lev = (float(inputs["quota"]), float(inputs["risk"]) / 100, float(inputs["stop"]) / 100,
                     float(inputs["lev"]))
    dly = p["daily_pct"] / 100 if p.get("daily_pct") is not None else None
    m = p["max_pct"] / 100 if p.get("max_pct") is not None else None
    is_static = p.get("drawdown_type") is not None and S(p["drawdown_type"]).startswith("static")
    known = dly is not None and m is not None
    derivable = known and p.get("drawdown_type") is not None and p.get("daily_basis") is not None
    h = sec(J["sec_rules"])
    h += row(J["row_daily_loss"], v(p.get("daily_pct"), lambda x: S(x) + "% · " + usd(Q * x / 100)),
             "" if p.get("daily_pct") is None else pv(["daily_pct", "daily_basis"],
                                                     J["f_daily_day_start"] if f["basis"] == "day_start" else J["f_daily"]))
    h += rr(J["row_daily_basis"], "daily_basis")
    h += rr(J["row_reset"], "reset_utc", reset if features else None)
    h += row(J["row_max_loss"], v(p.get("max_pct"), lambda x: S(x) + "% · " + usd(Q * x / 100)),
             "" if p.get("max_pct") is None else pv(["max_pct", "drawdown_type"], J["f_max"] if is_static else J["f_max_trailing"]))
    h += rr(J["row_drawdown_type"], "drawdown_type")
    h += rr(J["row_target"], "target_pct", lambda x: S(x) + "%")
    h += rr(J["row_min_days"], "min_days")
    h += rr(J["row_leverage_cap"], "max_leverage", lambda x: S(x) + "×")
    h += rr(J["row_hold_cap"], "hold_cap")
    h += rr(J["row_open_positions"], "max_open")
    h += rr(J["row_consistency_rule"], "consistency_rule")
    h += rr(J["row_news_rule"], "news_rule")
    h += rr(J["row_profit_cap"], "profit_cap")
    h += sec(J["sec_sizing"])
    risk = rp * Q
    h += row(J["row_risk"], usd(risk) + " (" + fx(rp * 100, 2) + "%)",
             '<div class="pv">' + J["pv_inputs"] + ' <code>' + J["f_risk"] + '</code></div>')
    K = ["daily_pct", "max_pct", "daily_basis", "drawdown_type"]
    cross, cf = None, ""
    if derivable and is_static:
        if f["basis"] in ("initial", "max_balance_equity"):
            cross, cf = Q * (1 - m + dly), J["f_cf_initial"]
        elif f["basis"] == "day_start":
            cross, cf = Q * (1 - m) / (1 - dly), J["f_cf_day_start"]
    if cross is not None:
        room = Q - cross
        h += row(J["row_room"], usd(room) + " (" + fx(room / Q * 100, 1) + "%)", pv(K, F(J["f_room"], {"cf": cf})))
        h += row(J["row_cross"], usd(cross), pv(K, F(J["f_cross"], {"cf": cf})))
        h += row(J["row_losses"], F(J["v_losses"], {"n": math.floor(room / risk), "pct": fx(rp * 100, 2)})
                 if room > 0 and risk > 0 else "—", pv(K, J["f_losses"]))
        h += row(J["row_survive"], F(J["v_survive"], {"n": math.floor(Q * m / risk)}) if risk > 0 else "—",
                 pv(["max_pct", "drawdown_type"], J["f_survive"]))
    elif derivable and not is_static:
        h += row(J["row_room"], '<span class="pend">' + J["v_room_trail"] + '</span>', pv(["drawdown_type"]))
        h += row(J["row_cross"], '<span class="pend">' + J["v_cross_trail"] + '</span>', pv(["drawdown_type"]))
        h += row(J["row_losses"], '<span class="pend">' + J["v_losses_trail"] + '</span>', pv(["drawdown_type"]))
        h += row(J["row_survive"], F(J["v_survive_trail"], {"n": math.floor(Q * m / risk)}) if risk > 0 else "—",
                 pv(["max_pct", "drawdown_type"], J["f_survive"]))
    else:
        h += row(J["row_room"], P) + row(J["row_cross"], P) + row(J["row_losses"], P) + row(J["row_survive"], P)
    if p.get("fee_per_side_pct") is not None:
        fee = p["fee_per_side_pct"] / 100
        drag = 2 * fee / (s + 2 * fee) * 100 if s > 0 else 0
        h += row(F(J["row_fee_at"], {"stop": fx(s * 100, 2)}), F(J["v_fee"], {"drag": fx(drag, 1), "fee": p["fee_per_side_pct"]}),
                 pv(["fee_per_side_pct"], J["f_fee"]))
    else:
        h += row(J["row_fee"], P)
    cap, ck = p.get("max_leverage"), "max_leverage"
    if f["levb"] is not None:                              # an empty list is truthy in the script
        cap = None
        for b in f["levb"]:
            if (b.get("max_quota") is None or Q <= b["max_quota"]) and (b.get("min_quota") is None or Q >= b["min_quota"]):
                cap, ck = b["lev"], b["cite"]
    if cap is not None:
        L = min(lev, cap)
        h += row(J["row_liq"], F(J["v_liq"], {"pct": fx((1 - (1 - 1 / L)) * 100, 0), "lev": L}),
                 pv([ck], F(J["f_liq"], {"cap": cap, "quota": usd(Q)})))
    else:
        h += row(J["row_liq"], P)
    h += sec(J["sec_cost"])
    h += rr(J["row_price"], "price") + rr(J["row_refund"], "refund") + rr(J["row_split"], "split")
    h += rr(J["row_us"], "us_available")
    if f["url"]:
        foot = F(J["foot_link"], {"url": f["url"], "name": f["name"]})
        if f["code"]:
            foot += "<br>" + F(J["foot_code"], {"code": f["code"]})
        if f["promo"]:
            foot += '<br><span style="color:var(--dim)">' + f["promo"] + '</span>'
        if f["req"]:
            foot += '<div class="req">' + f["req"] + '</div>'
        if features:
            foot = '<div data-avail-link>' + foot + '</div>'
    else:
        foot = '<span class="pend">' + F(J["foot_held"], {"name": f["name"]}) + '</span>'
    if f["open_n"]:
        foot += ('<div style="margin-top:8px;color:var(--dim);font-size:10.5px">'
                 + F(J["foot_open_n"] if f["open_n"] > 1 else J["foot_open_1"], {"n": f["open_n"], "first": f["open1"]}) + '</div>')
    return h, foot


def column(k, f, T):
    p = f["compare_product"]; n = sum(1 for x in FIELDS if p.get(x) is not None); m = sum(1 for x in FIELDS if sourced(f, x, p))
    tag = "good" if m == len(FIELDS) else ("warn" if m >= len(FIELDS)//2 else "bad")
    rows, foot = static_column(js_data(k, f, T), T)
    return f'''<div class="col" id="col-{k}">
  <div class="colhead"><div style="font-family:var(--mono);font-size:15px;font-weight:600">{html.escape(f["name"])}</div>
    <div class="s" style="margin-top:3px">{html.escape(T.data(p["label"]))}</div>
    <div style="margin-top:7px"><span class="tag {tag}">{T("compare.col.tag", n=n, total=len(FIELDS), m=m)}</span></div></div>
  <div class="rows" id="rows-{k}">{rows}</div><div class="colfoot" id="foot-{k}"{site_build.avail_attr(T)(k)}>{foot}</div></div>'''


def render_compare(T, live):
    """troid's compare in T's language, as HTML (site_build.GENERATED). T is an i18n.Strings, live the published
    language codes. English renders exactly as the page did before it was keyed."""
    gov = site_build.governs_html(T, "legal.summary.citations")
    D = lambda key: html.escape(T.data(FIRMS.get(key, "")))   # noqa: E731
    ref_text = D("_reference_firm").replace("{conflicts}", str(len(reference().get("_conflicts_found") or [])))
    return site_build.finish(T, "compare", f'''<!DOCTYPE html><html{site_build.html_attrs(T)}><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{T("compare.meta.title")}</title>
{_style(T)}
<style>
.cols{{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background:var(--line);border:1px solid var(--line);border-radius:4px;margin-top:14px}}
@media(max-width:760px){{.cols{{grid-template-columns:1fr}}}}
.col{{background:var(--surface);display:flex;flex-direction:column}}
.colhead{{padding:16px 16px 12px;border-bottom:1px solid var(--line)}}
.rows{{flex:1}}
.r{{padding:8px 16px;border-bottom:1px solid var(--line);font-family:var(--mono);font-size:12px}}
.r .rt{{display:flex;flex-wrap:wrap;justify-content:space-between;gap:0 10px}}.r .pv{{font-size:9.5px;line-height:1.5;color:var(--dim);margin-top:4px}}
.r .pv code{{font-size:9.5px;padding:0 3px}}.r .l{{color:var(--dim)}}.r .v{{font-variant-numeric:tabular-nums;text-align:end;margin-inline-start:auto;min-width:0;overflow-wrap:break-word}}
.r.sec{{background:var(--surface2);color:var(--dim);font-size:9.5px;text-transform:uppercase;letter-spacing:.12em;padding:6px 16px}}
.pend{{color:var(--dim);font-style:italic}}
.colfoot{{padding:14px 16px 16px;border-top:1px solid var(--line);font-family:var(--mono);font-size:11.5px;line-height:1.7;background:var(--surface2)}}
.colfoot .req{{margin-top:8px;color:var(--dim);font-size:10.5px;line-height:1.6}}
.inputs{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}}
@media(max-width:640px){{.inputs{{grid-template-columns:1fr 1fr}}}}
/* a value that doesn't fit beside its label takes the next line, and nothing is wider than a phone (design handoff
   2026-09-24, 1a) */
.inputs>*{{min-width:0}}
.s{{font-family:var(--mono);font-size:10.5px;color:var(--dim)}}
.foot{{font-family:var(--mono);font-size:11px;color:var(--dim);border-top:1px solid var(--line);margin-top:36px;padding-top:20px;line-height:1.8}}
</style>{site_build.head_extra(T, "compare", live)}</head><body><div class="wrap">
{header(T, live)}
{site_build.ticker(T)}
<p class="eyebrow" style="margin-top:28px;text-transform:none">{T("product.compare")}</p>
<h1>{T("compare.hero.h1")}</h1>
<p class="lede">{T("compare.hero.lede")}</p>
<p class="meta">{T("compare.hero.meta", date=html.escape(last_read()))}</p>
{gov + chr(10) if gov else ""}<div class="panel"><p class="eyebrow">{T("compare.sizing.h")}</p><div class="inputs">
  <div><label>{T("compare.sizing.quota")}</label><input id="quota" type="number" value="{jsnum.js_str(DEFAULTS["quota"])}"></div>
  <div><label>{T("compare.sizing.risk")}</label><input id="risk" type="number" step="any" value="{jsnum.js_str(DEFAULTS["risk"])}"></div>
  <div><label>{T("compare.sizing.stop")}</label><input id="stop" type="number" step="any" value="{jsnum.js_str(DEFAULTS["stop"])}"></div>
  <div><label>{T("compare.sizing.lev")}</label><input id="lev" type="number" step="any" value="{jsnum.js_str(DEFAULTS["lev"])}"></div>
</div></div>
{site_build.country_box(T)}<div class="cols">{"".join(column(k, FIRMS[k], T) for k in ORDER)}</div>
<p class="s" id="chosen" style="margin:16px 0 0;line-height:1.7">{ref_text} {D("_bitfunded_directory_note")}</p>
{conflicts_html(T, reference())}<p class="s" style="margin:10px 0 0;line-height:1.7">{D("_criterion")}</p>
<p class="s" style="margin:10px 0 0;line-height:1.7">{D("_link_rule")}</p>
<p class="s" style="margin:10px 0 0;line-height:1.7">{D("_disclosure")}</p>
<p class="foot">{site_text.footer_html(T)}</p>
</div>
<script>
var FIRMS={{{",".join(f'"{k}":{js(k, FIRMS[k], T)}' for k in ORDER)}}};var ORDER={json.dumps(ORDER)};
var T={T.js("compare.js.")},LANG="{T.code}";
function F(s,o){{return s.replace(/\\{{(\\w+)\\}}/g,function(m,k){{return k in o?o[k]:m}})}}
function n(id){{return parseFloat(document.getElementById(id).value)||0}}
{_numbers(T)}
var P='<span class="pend">'+T.pending+'</span>';
function v(x,fmt){{return (x===null||x===undefined)?P:(fmt?fmt(x):String(x))}}
function esc(x){{return String(x).replace(/[&<>"]/g,function(c){{return{{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}}[c]}})}}
var LAB={{}};for(var lk in T)if(lk.indexOf("lab_")===0)LAB[lk.slice(4)]=T[lk];
/* The provenance block under every number: firm, product, the date troid read each rule, the section, the formula.
   Section names stay in English, as each firm publishes them. */
var PROV_TAIL={json.dumps(T("prov.tail"), ensure_ascii=False)};
var LC={json.dumps(T("index.js.list_comma"), ensure_ascii=False)};
function list(a){{return a.length?a.reduce(function(x,y){{return F(LC,{{a:x,b:y}})}}):""}}
function andj(a){{return a.length<2?a.join(""):F(T.list_and,{{a:list(a.slice(0,-1)),b:a[a.length-1]}})}}
function pv(f,keys,formula){{
  var by={{}},order=[],dates=[],miss=[];
  keys.forEach(function(x){{var c=f.prov[x];if((x in f.p)&&(f.p[x]===null||f.p[x]===undefined))return;
    if(!c){{miss.push(LAB[x]||x);return}}
    if(!by[c.c]){{by[c.c]={{labs:[],o:c.o}};order.push(c.c)}}by[c.c].labs.push(LAB[x]||x);
    c.o.forEach(function(d){{if(dates.indexOf(d)<0)dates.push(d)}})}});
  dates.sort();
  var t,o={{firm:esc(f.name),product:esc(f.label),missing:list(miss),tail:PROV_TAIL}};
  if(order.length){{
    o.dates=andj(dates);
    o.sources=(order.length===1&&keys.length===1)?esc(order[0]):order.map(function(c){{
      return F(dates.length>1&&by[c].o.length?T.pv_src_read:T.pv_src,{{labels:list(by[c].labs),source:esc(c),dates:andj(by[c].o)}})}}).join(" · ");
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
    h+=rr(f,T.row_reset,"reset_utc"{RESET_FMT if site_build.features_on(T) else ""});
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
    h+=row(T.row_risk,$(risk)+" ("+fx((rp*100),2)+"%)",'<div class="pv">'+T.pv_inputs+' <code>'+T.f_risk+'</code></div>');
    var K=["daily_pct","max_pct","daily_basis","drawdown_type"];
    var cross=null,cf="";
    if(derivable&&isStatic){{
      if(f.basis==="initial"||f.basis==="max_balance_equity"){{cross=Q*(1-m+d);cf=T.f_cf_initial;}}
      else if(f.basis==="day_start"){{cross=Q*(1-m)/(1-d);cf=T.f_cf_day_start;}}
    }}
    if(cross!==null){{
      var room=Q-cross;
      h+=row(T.row_room,$(room)+" ("+fx((room/Q*100),1)+"%)",pv(f,K,F(T.f_room,{{cf:cf}})));
      h+=row(T.row_cross,$(cross),pv(f,K,F(T.f_cross,{{cf:cf}})));
      h+=row(T.row_losses,room>0&&risk>0?F(T.v_losses,{{n:Math.floor(room/risk),pct:fx((rp*100),2)}}):"—",pv(f,K,T.f_losses));
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
      h+=row(F(T.row_fee_at,{{stop:fx((s*100),2)}}),F(T.v_fee,{{drag:fx(drag,1),fee:p.fee_per_side_pct}}),pv(f,["fee_per_side_pct"],T.f_fee));}}
    else h+=row(T.row_fee,P);
    var cap=p.max_leverage,ck="max_leverage";
    if(f.levb){{cap=null;f.levb.forEach(function(b){{if((b.max_quota==null||Q<=b.max_quota)&&(b.min_quota==null||Q>=b.min_quota)){{cap=b.lev;ck=b.cite}}}})}}
    if(cap!=null){{var L=Math.min(lev,cap);h+=row(T.row_liq,F(T.v_liq,{{pct:fx(((1-(1-1/L))*100),0),lev:L}}),pv(f,[ck],F(T.f_liq,{{cap:cap,quota:$(Q)}})));}}
    else h+=row(T.row_liq,P);
    h+=sec(T.sec_cost);
    h+=rr(f,T.row_price,"price");h+=rr(f,T.row_refund,"refund");h+=rr(f,T.row_split,"split");
    h+=rr(f,T.row_us,"us_available");
    var foot="";
    if(f.url){{foot=F(T.foot_link,{{url:f.url,name:f.name}});
      if(f.code)foot+='<br>'+F(T.foot_code,{{code:f.code}});
      if(f.promo)foot+='<br><span style="color:var(--dim)">'+f.promo+'</span>';
      if(f.req)foot+='<div class="req">'+f.req+'</div>';{AVAIL_WRAP if site_build.features_on(T) else ""}}}
    else foot='<span class="pend">'+F(T.foot_held,{{name:f.name}})+'</span>';
    if(f.open_n)foot+='<div style="margin-top:8px;color:var(--dim);font-size:10.5px">'+F(f.open_n>1?T.foot_open_n:T.foot_open_1,{{n:f.open_n,first:f.open1}})+'</div>';
    document.getElementById("rows-"+k).innerHTML=h;document.getElementById("foot-"+k).innerHTML=foot;
  }});{AFTER_RENDER if site_build.features_on(T) else ""}
}}
["quota","risk","stop","lev"].forEach(function(i){{document.getElementById(i).addEventListener("input",render)}});
render();
</script></body></html>''')


def unsourced():
    """Every compare cell that shows a value without a recorded source: troid's rule is that a cell shows a value only
    from the firm's own document, so the build refuses one (challenge-proof audit, 2026-09-26, C). Source it with a read
    date in firms.json provenance, or return it to pending (null)."""
    return [(FIRMS[k]["name"], x) for k in ORDER for x in FIELDS
            if FIRMS[k]["compare_product"].get(x) is not None and not sourced(FIRMS[k], x, FIRMS[k]["compare_product"])]


def main():
    bad = unsourced()
    if bad:
        sys.exit("compare: filled but unsourced — source each from the firm's document or return it to pending: "
                 + "; ".join(f"{n} {x}" for n, x in bad))
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
    changed += site_build.write_seo()
    # Context bundle for the assistant function (web/api/troid.js): a copy of firms.json outside
    # public/, packaged into the function by vercel.json includeFiles. Not served as a page.
    CONTEXT = HERE.parent / "web" / "context" / "firms.json"
    CONTEXT.parent.mkdir(exist_ok=True)
    if not CONTEXT.exists() or CONTEXT.read_bytes() != (HERE.parent / "firms.json").read_bytes():
        CONTEXT.write_bytes((HERE.parent / "firms.json").read_bytes()); changed.append("context/firms.json")
    print(f"compare.html: coverage {cov} of {len(FIELDS)}, every filled cell sourced · links live: {links} · required disclaimers: "
          f"{[n for n, _ in required_sentences()] or 'none'} · regions rewritten: {changed or 'none (already current)'}")


if __name__ == "__main__":
    main()
