#!/usr/bin/env python3
"""The generated fragments troid's desk (index) embeds, built from firms.json: the firms panel, the calculator's
data, the crossover stat. Each takes the page's strings (i18n.Strings) so it renders in the reader's language.
site_build.py asks for them through template_context(); gen_compare.py owns the rules they share
(cite, sourced, link_live)."""
from __future__ import annotations
import html
import json

from gen_compare import FIRMS, ORDER, FIELDS, RANK, PROV_TAIL, cite, sourced, link_live   # noqa: F401


def panel_cell(k, f):
    p = f["compare_product"]; name = html.escape(f["name"])
    rank = RANK.get(f["name"])
    role = "reference" if f.get("reference") else (f"#{rank[0]} by reviews" if rank else "")
    head = f"{name} · {role}" if role else name
    if f.get("verified"):
        summary = f.get("panel_summary") or (f"{p['label']} {p['daily_pct']}% / {p['max_pct']}%"
                                             + (f" {p['drawdown_type']}" if p.get("drawdown_type") else ""))
        v = f'<div class="v" style="font-size:14px;margin:4px 0">{html.escape(summary)}</div>'
    elif link_live(f):
        n = sum(1 for x in FIELDS if p.get(x) is not None); m = sum(1 for x in FIELDS if sourced(f, x, p))
        v = f'<div class="v" style="font-size:14px;margin:4px 0;color:var(--dim)">{n} of {len(FIELDS)} rules filled · {m} sourced</div>'
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
                f'{name} challenges</a> · affiliate link' + (f" · code {html.escape(code)}" if code else "")
                + (" · their promos apply here" if f.get("_promo_note") else "") + "</div>")
    return f'    <div class="cell">\n      <div class="k">{head}</div>\n      {v}{note}{link}\n    </div>'


def firms_panel_html():
    return ('  <div class="read" style="grid-template-columns:repeat(auto-fit,minmax(220px,1fr))">\n'
            + "\n".join(panel_cell(k, FIRMS[k]) for k in ORDER) + "\n  </div>")


def profiles_js():
    """The calculator's data: every listed firm's products with basis, drawdown, lock, hwm, fee, leverage. null = pending."""
    out = {}
    for k in ORDER:
        f = FIRMS[k]; c = f.get("calc") or {}; prods = f.get("products") or {}
        products = {}
        for pk, pc in (c.get("products") or {}).items():
            src = prods.get(pk) or {}
            dp = pc.get("daily_pct", src.get("daily_pct")); mp = pc.get("max_pct", src.get("max_pct"))
            if dp is None or mp is None:
                continue                                   # a product without both limits is not offered
            products[pk] = {"label": pc.get("label", pk), "d": dp, "m": mp,
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
    return ("<script>var FIRMS=" + json.dumps(out, separators=(",", ":")) + ";var PROV_TAIL=" + json.dumps(PROV_TAIL)
            + ";</script>")


def crossover_html():
    """The landing page's crossover stat, DERIVED from the reference firm's compare product, with its provenance
    line. Only the initial-balance basis has this closed form: Q(1 − max% + daily%)."""
    k = next(k for k in ORDER if FIRMS[k].get("reference"))
    f = FIRMS[k]; p = f["compare_product"]; pk = p["key"]; c = f.get("calc") or {}
    basis = ((c.get("products") or {}).get(pk) or {}).get("daily_basis", c.get("daily_basis"))
    assert basis == "initial", f"{f['name']} {pk}: the crossover stat's formula needs an initial-balance daily basis, got {basis}"
    q, d, m = 100_000, p["daily_pct"], p["max_pct"]
    x = round(q * (1 - m / 100 + d / 100))
    gap, day = q - x, q * d / 100
    part = "half of one bad day" if gap * 2 == day else f"{gap / day:.0%} of one bad day"
    by, order, dates = {}, [], set()
    for field, lab in (("daily_pct", "daily %"), ("max_pct", "max %"), ("drawdown_type", "static floor"),
                       ("daily_basis", "initial-balance daily limit")):
        ct = cite(f, field, pk)
        assert ct, f"{f['name']} {pk}: the crossover stat uses {field}, which has no recorded source"
        if ct["c"] not in by:
            by[ct["c"]] = {"labs": [], "o": ct["o"]}; order.append(ct["c"])
        by[ct["c"]]["labs"].append(lab); dates.update(ct["o"])
    srcs = " · ".join(", ".join(by[s]["labs"]) + " from " + s + (f" (read {' and '.join(by[s]['o'])})" if by[s]["o"] else "")
                      for s in order)
    pv = (f"DERIVED. Computed from {f['name']} {p['label']} rules as published on {' and '.join(sorted(dates))} — {srcs}. "
          f"{PROV_TAIL} <code>quota × (1 − max% + daily%) = ${q:,} × (1 − {m}% + {d}%)</code>")
    return (f'  <div class="stat"><div class="n">${x:,}</div>\n'
            f'    <p>On a ${q // 1000}k {html.escape(p["label"])}, below this equity the {m}% static floor binds instead of the {d}%\n'
            f'    daily. That is ${gap:,} from the start — {part}.</p>\n'
            f'    <div class="prov">{pv}</div></div>')


def template_context(T):
    """The generated fragments the static page templates embed, in T's language (site_build.py)."""
    import site_text
    return {}
