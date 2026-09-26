#!/usr/bin/env python3
"""Fixed text every generated page shares: the footer and the hypothetical-performance disclaimer.

Imported by gen_compare.py (which also writes the footer into the marked <!-- footer --> regions of the
static pages), gen_ledger.py, gen_tearsheet.py and walkforward.py. Change the wording here, once.
"""
from __future__ import annotations
import html, json, re
from pathlib import Path

ROOT = Path(__file__).parent.parent

# 17 CFR 4.41(b)(1)(i), verbatim. Do not paraphrase, re-case or "fix" the hyphenation ("under-or over-compensated").
HYPO = ("These results are based on simulated or hypothetical performance results that have certain inherent "
        "limitations. Unlike the results shown in an actual performance record, these results do not represent actual "
        "trading. Also, because these trades have not actually been executed, these results may have under-or "
        "over-compensated for the impact, if any, of certain market factors, such as lack of liquidity. Simulated or "
        "hypothetical trading programs in general are also subject to the fact that they are designed with the benefit "
        "of hindsight. No representation is being made that any account will or is likely to achieve profits or losses "
        "similar to these being shown.")

# The owner's footer line (audit handoff 3a, second sentence replaced by the owner on 2026-09-23), on every page.
FOOTER_TEXT = ("troid is a free informational tool, not financial or investment advice. troid does not place trades "
               "or publish trade signals. Its shadow account is a simulated strategy, shown only after trades close. Prop-firm rules "
               "change without notice — verify every number with the firm before trading. troid is an independent affiliate of the firms it compares and earns a commission on purchases "
               "through its links; this does not affect the calculations or comparisons.")

# The operator (owner decision, 24 Sep 2026): Kunjan Patel, an individual. Terms section 1 names him "the Operator".
# A name, not prose: shown as it is on every page, in every language.
COPYRIGHT = "© 2026 Kunjan Patel"

LINKS = [("/", "troid's desk"), ("/compare", "troid's compare"), ("/ledger", "troid's ledger"),
         ("/dashboard", "troid's research"), ("/tearsheet", "tearsheet"), ("/chat", "ask troid"), ("/faq", "faq"), ("/terms", "terms"),
         ("https://github.com/kunjancollective/troid", "source"), ("https://x.com/tradingdroid", "x"),
         ("https://www.reddit.com/user/tradingdroid/", "reddit")]


def holdout():
    """The out-of-sample result the no-edge sentence quotes, from the walk-forward output (MEASURED)."""
    p = Path(__file__).parent / "results" / "walkforward_BTCUSDT.json"
    return json.loads(p.read_text())["holdout"] if p.exists() else None


NO_EDGE_SHORT = "troid's own strategy shows no statistical edge."


def no_edge_sentence():
    h = holdout()
    tail = (f" Out of sample, on {h['n']} BTC trades from 1 January 2021 to 7 January 2026, which the parameters never saw, it measures "
            f"{h['exp']:+.3f}R per trade, standard error {h['se']:.3f}R — a MEASURED figure (backtest/WALKFORWARD.md), inside noise, "
            f"and not a fact about the future.") if h else ""
    return "troid's own strategy shows no statistical edge." + tail


def required_sentences():
    """Every listed firm's required verbatim sentence, while the firm is listed (same rule as gen_compare.py)."""
    F = json.loads((ROOT / "firms.json").read_text())
    order = sorted(k for k in F if isinstance(F[k], dict) and "compare_product" in F[k])
    return [F[k]["required_disclaimer"].strip() for k in order if (F[k].get("required_disclaimer") or "").strip()]


# The footer's link labels, keyed for translation (web/i18n/en.json); the English labels are LINKS above.
LINK_KEYS = {"/": "product.desk", "/compare": "product.compare", "/ledger": "product.ledger", "/dashboard": "product.research",
             "/tearsheet": "common.link.tearsheet", "/chat": "product.ask", "/faq": "common.link.faq", "/terms": "common.link.terms",
             "https://github.com/kunjancollective/troid": "common.link.source", "https://x.com/tradingdroid": "common.link.x",
             "https://www.reddit.com/user/tradingdroid/": "common.link.reddit"}


# The line's hidden word (the owner, 2026-09-26): "tr" from "trade" and "oid" from "droid" spell troid. Those letters
# take the dot's blue, and the rest of the two words the wordmark's letters' ink, as the wordmark has them; the rest of
# the line stays dim. One rule for the home page, the share image and the banners (site_build, gen_og, brand/tagline.py).
TAGLINE_MARKS = {"droid": (("dr", "ink"), ("oid", "signal")), "trade": (("tr", "signal"), ("ade", "ink"))}


def tagline_parts(line):
    """The line as (text, role) pieces, role None (dim), "ink" or "signal". A line without the two words (a translation)
    is one dim piece."""
    out = []
    for piece in re.split(r"\b(droid|trade)\b", line):
        if piece in TAGLINE_MARKS:
            out += list(TAGLINE_MARKS[piece])
        elif piece:
            out.append((piece, None))
    return out


def _english(T):
    """The English output, byte for byte as before. The pseudo-locale (i18n_pseudo.py) takes the translated path."""
    return T is None or (T.code == "en" and not getattr(T, "pseudo", False))


def footer_html(T=None):
    """Inline HTML (no block elements), so it fits both <footer><div> and <p class="foot"> containers.
    English is the owner's line verbatim; a translated page carries the line in its language. The footer names no
    firm: a firm's required sentence sits beside that firm's link and in the terms' affiliate notices
    (regions.required_span; design handoff 2026-09-24, 2d)."""
    if _english(T):
        links = " · ".join(f'<a href="{u}">{html.escape(t)}</a>' for u, t in LINKS)
        return f"{links}<br><br>{html.escape(FOOTER_TEXT)}<br><br>{COPYRIGHT}"
    links = " · ".join(f'<a href="{(T.H if u == "/" else T.L + u) if u.startswith("/") else u}">{html.escape(T(LINK_KEYS[u]))}</a>'
                       for u, _ in LINKS)
    return f"{links}<br><br>{T('footer.text')}" + f'<br><br><span translate="no">{COPYRIGHT}</span>'


def no_edge_html(T=None):
    """troid's no-edge sentence in the page's language (MEASURED figures from the walk-forward output)."""
    if _english(T):
        return html.escape(no_edge_sentence())
    h = holdout()
    return T("hypo.no_edge_short") + ((" " + T("hypo.no_edge_tail", n=h["n"], exp=f"{h['exp']:+.3f}R", se=f"{h['se']:.3f}R")) if h else "")


def hypo_html(no_edge=None, T=None):
    """The disclaimer box: the 4.41 text verbatim, with troid's no-edge sentence beside it. Inline styles with
    fallbacks, so it renders on pages that don't share the site stylesheet (the tearsheet). On a translated page
    the 4.41 text stays in English (it is regulatory text), after a one-line summary and the governing line."""
    box = ('<div class="hypo" style="border-inline-start:2px solid var(--warn,#96661a);background:var(--surface2,#eef2f7);'
           'padding:12px 14px;margin:0 0 14px;font-family:var(--mono,ui-monospace,Menlo,monospace);font-size:11.5px;'
           'line-height:1.65;color:var(--dim,#5f6f86)">')
    if _english(T):
        ne = html.escape(no_edge or no_edge_sentence())
        return (box + '<div style="text-transform:uppercase;letter-spacing:.1em;font-size:9.5px;margin-bottom:6px">Hypothetical performance</div>'
                f'<p style="margin:0 0 8px;font:inherit">{html.escape(HYPO)}</p><p style="margin:0;font:inherit">{ne}</p></div>')
    ne = T("hypo.no_edge_short") if no_edge == NO_EDGE_SHORT else no_edge_html(T)
    return (box + f'<div style="letter-spacing:.1em;font-size:9.5px;margin-bottom:6px">{T("hypo.label")}</div>'
            f'<p style="margin:0 0 6px;font:inherit"><span class="gov-sum">{T("legal.summary.hypo")}</span> <span class="gov-line">{T("legal.governs")}</span></p>'
            f'<p lang="en" dir="ltr" style="margin:0 0 8px;font:inherit">{html.escape(HYPO)}</p><p style="margin:0;font:inherit">{ne}</p></div>')


def hypo_md(no_edge=None):
    return (f"> **Hypothetical performance.** {HYPO}\n>\n> {no_edge or no_edge_sentence()}\n")
