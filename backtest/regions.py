#!/usr/bin/env python3
"""The generated fragments troid's desk (index) embeds, built from firms.json: the firms panel, the calculator's
data, the crossover stat. Each takes the page's strings (i18n.Strings) so it renders in the reader's language;
with no strings (gen_compare.py's own calls) it renders English, exactly as before. site_build.py asks for them
through template_context(); gen_compare.py owns the rules they share (cite, sourced, link_live).

Words come from web/i18n (keys index.firms.*, index.crossover.*, index.js.*, prov.tail). Firm prose and rule values
from firms.json go through T.data(); firm names and rule-source names stay as the firm publishes them."""
from __future__ import annotations
import html
import json

import i18n
import site_build
import site_text
from gen_compare import FIRMS, ORDER, FIELDS, RANK, cite, sourced, link_live, required_span   # noqa: F401


def _strings(T):
    """The page's strings, or English when a caller passes none."""
    return T if T is not None else i18n.Strings("en")


def _join(T, key, items):
    """Items joined one pair at a time through a language's own pattern: index.js.list_comma ('{a}, {b}') gives
    'a, b, c'; index.js.list_and ('{a} and {b}') gives 'a and b and c', as the English always read."""
    items = list(items)
    out = items[0] if items else ""
    for x in items[1:]:
        out = T(key, a=out, b=x)
    return out


def reference_firm():
    """The firm the desk and the crossover stat are computed against (firms.json 'reference')."""
    return FIRMS[next(k for k in ORDER if FIRMS[k].get("reference"))]


def panel_cell(k, f, T=None):
    T = _strings(T)
    p = f["compare_product"]; name = html.escape(f["name"])
    rank = RANK.get(f["name"])
    role = T("index.firms.reference") if f.get("reference") else (T("index.firms.rank", n=rank[0]) if rank else "")
    head = f"{name} · {role}" if role else name
    # One rule for every firm, the reference firm included: how many of the compare's rules are filled and how many
    # have a recorded source; a firm's own one-line summary (panel_summary), where it has one, sits above the count.
    n = sum(1 for x in FIELDS if p.get(x) is not None); m = sum(1 for x in FIELDS if sourced(f, x, p))
    count = T("index.firms.filled", n=n, total=len(FIELDS), m=m) if n else T("index.firms.pending")
    v = f'<div class="v" style="font-size:14px;margin:4px 0;color:var(--dim)">{count}</div>'
    if f.get("panel_summary"):
        v = f'<div class="v" style="font-size:14px;margin:4px 0">{html.escape(T.data(f["panel_summary"]))}</div>\n      ' + v
    notes = []
    if rank: notes.append(T("index.firms.reviews", n=rank[1]["reviews"], rating=rank[1]["rating"]))
    if f.get("panel_note"): notes.append(html.escape(T.data(f["panel_note"])))
    note = f'\n      <div class="s">{" ".join(notes)}</div>' if notes else ""
    link = ""
    if link_live(f):
        code = f.get("affiliate_code") or (f.get("affiliate_agreement") or {}).get("customer_code")
        bits = [f'<a href="{html.escape(f["affiliate_url"])}" rel="sponsored noopener">{T("index.firms.challenges", firm=name)}</a>',
                T("index.firms.affiliate")]
        if code: bits.append(T("index.firms.code", code=html.escape(code)))
        if f.get("_promo_note"): bits.append(T("index.firms.promos"))
        hold = " data-avail-link" if site_build.features_on(T) else ""       # i18n.js hides it where the terms exclude
        link = f'\n      <div class="s" style="margin-top:8px"{hold}>{" · ".join(bits)}</div>'
        if (f.get("required_disclaimer") or "").strip():                # the firm's own wording, beside its link (2d)
            link += f'\n      <div class="s req"{hold}>{required_span(T, f)}</div>'
    return f'    <div class="cell"{site_build.avail_attr(T)(k)}>\n      <div class="k">{head}</div>\n      {v}{note}{link}\n    </div>'


def firms_panel_html(T=None):
    T = _strings(T)
    return ('  <div class="read" style="grid-template-columns:repeat(auto-fit,minmax(220px,1fr))">\n'
            + "\n".join(panel_cell(k, FIRMS[k], T) for k in ORDER) + "\n  </div>")


def profiles_js(T=None):
    """The calculator's data: every listed firm's products with basis, drawdown, lock, hwm, fee, leverage. null = pending.
    Product labels are shown as text, so they pass through T.data(); rule-source names ('c') stay as recorded."""
    T = _strings(T)
    out = {}
    for k in ORDER:
        f = FIRMS[k]; c = f.get("calc") or {}; prods = f.get("products") or {}
        products = {}
        for pk, pc in (c.get("products") or {}).items():
            src = prods.get(pk) or {}
            dp = pc.get("daily_pct", src.get("daily_pct")); mp = pc.get("max_pct", src.get("max_pct"))
            if dp is None or mp is None:
                continue                                   # a product without both limits is not offered
            products[pk] = {"label": T.data(pc["label"]) if "label" in pc else pk, "d": dp, "m": mp,
                            "basis": pc.get("daily_basis", c.get("daily_basis")),
                            "dd": pc["drawdown"] if "drawdown" in pc else c.get("drawdown"),
                            "locks": pc.get("locks_at_initial_after_pct", c.get("locks_at_initial_after_pct")),
                            "hwm": pc.get("hwm_basis", c.get("hwm_basis")),
                            "fee": pc.get("fee_per_side_pct", c.get("fee_per_side_pct")),
                            "lev": pc.get("max_leverage", c.get("max_leverage")),
                            "levb": None if "max_leverage" in pc else [dict({k: v for k, v in b.items() if k != "cite"}, pv=cite(f, b["cite"]))
                                                                        for b in (c.get("lev_bands") or [])] or None,
                            "pv": {"d": cite(f, "daily_pct", pk, fallback=False), "m": cite(f, "max_pct", pk, fallback=False),
                                   "basis": cite(f, "daily_basis", pk, fallback="daily_basis" not in pc),
                                   "dd": cite(f, "drawdown", pk, fallback="drawdown" not in pc),
                                   "locks": cite(f, "locks_at_initial_after_pct", pk, fallback="locks_at_initial_after_pct" not in pc),
                                   "hwm": cite(f, "hwm_basis", pk, fallback="hwm_basis" not in pc),
                                   "fee": cite(f, "fee_per_side_pct", pk, fallback="fee_per_side_pct" not in pc),
                                   "lev": cite(f, "max_leverage", pk, fallback="max_leverage" not in pc)}}
        if products:
            out[k] = {"name": f["name"], "products": products}
    ascii_ = site_text._english(T)                  # English exactly as before; other scripts written as themselves
    return ("<script>var FIRMS=" + json.dumps(out, separators=(",", ":"), ensure_ascii=ascii_) + ";var PROV_TAIL="
            + json.dumps(T("prov.tail"), ensure_ascii=ascii_)
            + ";</script>")


def crossover_html(T=None):
    """The landing page's crossover stat, DERIVED from the reference firm's compare product, with its provenance
    line. Only the initial-balance basis has this closed form: Q(1 − max% + daily%)."""
    T = _strings(T)
    f = reference_firm(); p = f["compare_product"]; pk = p["key"]; c = f.get("calc") or {}
    basis = ((c.get("products") or {}).get(pk) or {}).get("daily_basis", c.get("daily_basis"))
    assert basis == "initial", f"{f['name']} {pk}: the crossover stat's formula needs an initial-balance daily basis, got {basis}"
    q, d, m = 100_000, p["daily_pct"], p["max_pct"]
    x = round(q * (1 - m / 100 + d / 100))
    gap, day = q - x, q * d / 100
    by, order, dates = {}, [], set()
    for field, lab in (("daily_pct", "index.crossover.lab_daily"), ("max_pct", "index.crossover.lab_max"),
                       ("drawdown_type", "index.crossover.lab_static"), ("daily_basis", "index.crossover.lab_basis")):
        ct = cite(f, field, pk)
        assert ct, f"{f['name']} {pk}: the crossover stat uses {field}, which has no recorded source"
        if ct["c"] not in by:
            by[ct["c"]] = {"labs": [], "o": ct["o"]}; order.append(ct["c"])
        by[ct["c"]]["labs"].append(T(lab)); dates.update(ct["o"])
    srcs = " · ".join(T("index.js.prov_src_read", rules=_join(T, "index.js.list_comma", by[s]["labs"]), source=s,
                        dates=_join(T, "index.js.list_and", by[s]["o"])) if by[s]["o"] else
                      T("index.js.prov_src", rules=_join(T, "index.js.list_comma", by[s]["labs"]), source=s)
                      for s in order)
    label = T.data(p["label"])
    pv = T("index.crossover.prov", firm=f["name"], product=label, dates=_join(T, "index.js.list_and", sorted(dates)), sources=srcs,
           tail=T("prov.tail"), formula=T("index.crossover.formula", quota=f"${q:,}", max=m, daily=d))
    para = T("index.crossover.p_half" if gap * 2 == day else "index.crossover.p_share", quota=f"${q // 1000}k",
             product=html.escape(label), max=m, daily=d, gap=f"${gap:,}", share=f"{gap / day:.0%}")
    return (f'  <div class="stat"><div class="n">${x:,}</div>\n'
            f'    <p>{para}</p>\n'
            f'    <div class="prov">{pv}</div></div>')


def affiliate_notices_html(T=None):
    """/terms, "Affiliate notices": each listed firm's required sentence with the firm's name, generated so that a firm
    leaving the list takes its notice with it."""
    T = _strings(T)
    return "\n".join(f'<p><b>{html.escape(FIRMS[k]["name"])}</b>: {required_span(T, FIRMS[k])}</p>'
                     for k in ORDER if (FIRMS[k].get("required_disclaimer") or "").strip())


def why_these(T=None):
    """The desk's "why these 3?" note (2a): how many firms troid compares and which is the reference, from firms.json."""
    T = _strings(T)
    return T("index.why3.p", n=len(ORDER), firm=html.escape(reference_firm()["name"]), others=len(ORDER) - 1)


def _lev_caps(f, T):
    """(product label, cap) for each product the desk offers: the product's own cap, or the highest of the firm's
    bands; None where no cap, or no source for it, is recorded."""
    c = f.get("calc") or {}; prods = f.get("products") or {}; caps = []
    for pk, pc in (c.get("products") or {}).items():
        src = prods.get(pk) or {}
        if pc.get("daily_pct", src.get("daily_pct")) is None or pc.get("max_pct", src.get("max_pct")) is None:
            continue                                   # not offered on the desk (profiles_js)
        label = T.data(pc["label"]) if "label" in pc else pk
        bands = c.get("lev_bands") or []
        if "max_leverage" in pc or not bands:
            lev = pc.get("max_leverage", c.get("max_leverage"))
            caps.append((label, lev if lev is not None and cite(f, "max_leverage", pk, fallback="max_leverage" not in pc) else None))
        else:
            caps.append((label, max(b["lev"] for b in bands) if all(cite(f, b["cite"]) for b in bands) else None))
    return caps


def lev_first(T=None):
    """The leverage note's first sentence (2c): the firms whose every recorded cap is 5×, which is why 5× is the default
    (min(5, the product's cap)); then each firm, or product, with no recorded cap. Only caps firms.json records with a
    source, never one from memory: a firm with some products unrecorded is named with them."""
    T = _strings(T)
    five, pend = [], []
    for k in ORDER:
        name = html.escape(FIRMS[k]["name"]); caps = _lev_caps(FIRMS[k], T)
        known = [c for _, c in caps if c is not None]
        missing = [html.escape(lab) for lab, c in caps if c is None]
        if known and max(known) == 5:
            five.append(name)
        if missing:
            pend.append(name if not known else T("index.lev.firm_product", firm=name, product=_join(T, "index.js.list_and", missing)))
    out = [T("index.lev.first_one" if len(five) == 1 else "index.lev.first_many", firms=_join(T, "index.js.list_and", five))] if five else []
    if pend:
        out.append(T("index.lev.pending", firms=_join(T, "index.js.list_and", pend)))
    return " ".join(out)


def template_context(T):
    """The generated fragments the static page templates embed, in T's language (site_build.py), and the reference
    firm's name for the sentence under the firms panel (a firm's name comes from firms.json, never from en.json)."""
    return {"firms_panel": firms_panel_html(T), "profiles_js": profiles_js(T), "crossover": crossover_html(T),
            "reference_firm": html.escape(reference_firm()["name"]), "why_these": why_these(T), "lev_first": lev_first(T),
            "affiliate_notices": affiliate_notices_html(T), "n_firms": len(ORDER)}
