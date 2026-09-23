#!/usr/bin/env python3
"""Fixed text every generated page shares: the footer and the hypothetical-performance disclaimer.

Imported by gen_compare.py (which also writes the footer into the marked <!-- footer --> regions of the
static pages), gen_ledger.py, gen_tearsheet.py and walkforward.py. Change the wording here, once.
"""
from __future__ import annotations
import html, json
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
            f"{h['exp']:+.3f}R per trade, standard error {h['se']:.3f}R — a MEASURED figure, inside noise, and not a fact "
            f"about the future.") if h else ""
    return "troid's own strategy shows no statistical edge." + tail


def required_sentences():
    """Every listed firm's required verbatim sentence, while the firm is listed (same rule as gen_compare.py)."""
    F = json.loads((ROOT / "firms.json").read_text())
    order = sorted(k for k in F if isinstance(F[k], dict) and "compare_product" in F[k])
    return [F[k]["required_disclaimer"].strip() for k in order if (F[k].get("required_disclaimer") or "").strip()]


def footer_html():
    """Inline HTML (no block elements), so it fits both <footer><div> and <p class="foot"> containers."""
    links = " · ".join(f'<a href="{u}">{html.escape(t)}</a>' for u, t in LINKS)
    extra = " ".join(html.escape(t) for t in required_sentences())
    return f"{links}<br><br>{html.escape(FOOTER_TEXT)}" + (f" {extra}" if extra else "")


def hypo_html(no_edge=None):
    """The disclaimer box: the 4.41 text verbatim, with troid's no-edge sentence beside it. Inline styles with
    fallbacks, so it renders on pages that don't share the site stylesheet (the tearsheet)."""
    ne = html.escape(no_edge or no_edge_sentence())
    return ('<div class="hypo" style="border-left:2px solid var(--warn,#96661a);background:var(--surface2,#eef2f7);'
            'padding:12px 14px;margin:0 0 14px;font-family:var(--mono,ui-monospace,Menlo,monospace);font-size:11.5px;'
            'line-height:1.65;color:var(--dim,#5f6f86)">'
            '<div style="text-transform:uppercase;letter-spacing:.1em;font-size:9.5px;margin-bottom:6px">Hypothetical performance</div>'
            f'<p style="margin:0 0 8px;font:inherit">{html.escape(HYPO)}</p><p style="margin:0;font:inherit">{ne}</p></div>')


def hypo_md(no_edge=None):
    return (f"> **Hypothetical performance.** {HYPO}\n>\n> {no_edge or no_edge_sentence()}\n")
