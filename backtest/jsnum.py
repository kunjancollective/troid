#!/usr/bin/env python3
"""Numbers written as a page's script writes them, for HTML rendered ahead of the script.

troid's compare fills its rule columns in the browser; gen_compare.py also writes them into the page at the default
inputs, so a reader without the script, and a search or AI crawler, sees every value with its source (launch handoff
2026-09-26, 5.1 item 4). The script re-renders on load, and at the default inputs it writes the same HTML
(web/test_compare_static.py, in Chromium, every language). Three writers:

  js_str(x)        String(x), and what "+" and a template's {n} make of a number
  to_fixed(x, d)   x.toFixed(d): the double's exact value, a tie rounded up (1.005 → "1.00": its double is below 1.005)
  Intl(lang)       Intl.NumberFormat in a language's locale, as web/public/i18n.js calls it (TROID.num, .fixed, .usd),
                   from the format languages.json records for the locale ("num"). ICU rounds the shortest decimal that
                   reads back as the double, a tie away from zero (1.005 → "1.01").
"""
from __future__ import annotations

import math
from decimal import ROUND_HALF_UP, Decimal, localcontext

MARKS = "‎‏؜"          # LRM, RLM, ALM: i18n.js ltr() drops them and isolates the amount instead


def js_str(x):
    """ECMAScript Number::toString(x) (and String(x) for the other JSON values a template meets)."""
    if x is None:
        return "null"
    if isinstance(x, bool):
        return "true" if x else "false"
    if isinstance(x, str):
        return x
    if isinstance(x, int):
        return str(x)
    x = float(x)
    if math.isnan(x):
        return "NaN"
    if math.isinf(x):
        return "Infinity" if x > 0 else "-Infinity"
    if x == 0:
        return "0"
    sign, digits, exp = Decimal(repr(abs(x))).normalize().as_tuple()     # the shortest decimal, as JS picks it
    s = "".join(map(str, digits))
    k, n = len(s), exp + len(s)
    if k <= n <= 21:
        out = s + "0" * (n - k)
    elif 0 < n <= 21:
        out = s[:n] + "." + s[n:]
    elif -6 < n <= 0:
        out = "0." + "0" * (-n) + s
    else:
        e = n - 1
        out = (s if k == 1 else s[0] + "." + s[1:]) + "e" + ("+" if e >= 0 else "-") + str(abs(e))
    return ("-" if x < 0 else "") + out


def _quantize(d, places):
    with localcontext() as c:
        c.prec = 200
        return d.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)


def to_fixed(x, d):
    """Number.prototype.toFixed(d): the exact value of the double, the tie to the larger n; -0 prints unsigned."""
    x = float(x)
    if math.isnan(x) or math.isinf(x) or abs(x) >= 1e21:
        return js_str(x)
    return format(_quantize(Decimal(x if x != 0 else 0.0), d), "f")


def _negative(x):
    return x < 0 or (x == 0 and math.copysign(1.0, x) < 0)


class Intl:
    """Intl.NumberFormat for one languages.json entry: its "num" record says how the locale writes a number
    (group and decimal separators, group sizes, the digits a number needs before it is grouped, the minus sign, and
    the USD pattern with # for the number). Recorded from the browser; web/test_compare_static.py re-reads each
    locale in Chromium and fails when a record no longer matches."""

    def __init__(self, lang):
        n = lang.get("num")
        if not n:
            raise KeyError(f"web/i18n/languages.json: {lang['code']} has no \"num\" record (how {lang['intl']} writes a number)")
        self.group, self.decimal = n["group"], n["decimal"]
        self.sizes = tuple(n.get("grouping") or (3, 3))
        self.min_grouping = n.get("min_grouping", 1)
        self.minus = n.get("minus", "-")
        self.usd_pos, self.usd_neg = n["usd"], n["usd_neg"]
        self.rtl = lang.get("dir") == "rtl"

    def _group(self, i):
        p, s = self.sizes
        if len(i) < p + self.min_grouping:
            return i
        head, parts = i[:-p], [i[-p:]]
        while len(head) > s:
            parts.insert(0, head[-s:]); head = head[:-s]
        return self.group.join(([head] if head else []) + parts)

    def _digits(self, x, lo, hi, grouping=True):
        """|x| rounded to at most hi and at least lo fraction digits, grouped or not."""
        q = _quantize(Decimal(repr(abs(float(x)))), hi)
        i, _, f = format(q, "f").partition(".")
        f = f.rstrip("0")
        f = f + "0" * (lo - len(f)) if len(f) < lo else f
        i = self._group(i) if grouping else i
        return i + (self.decimal + f if f else "")

    def num(self, x, max_frac=3, min_frac=0):
        """TROID.num(x, {maximumFractionDigits, minimumFractionDigits}); the default is Intl's 0 to 3."""
        return (self.minus if _negative(x) else "") + self._digits(x, min_frac, max_frac)

    def fixed(self, x, d):
        """TROID.fixed(x, d): d fraction digits, no grouping."""
        return (self.minus if _negative(x) else "") + self._digits(x, d, d, grouping=False)

    def usd(self, x, d=2):
        """TROID.usd(x, d): the locale's USD pattern; on a right-to-left page isolated left to right (i18n.js ltr())."""
        s = (self.usd_neg if _negative(x) else self.usd_pos).replace("#", self._digits(x, d, d))
        if self.rtl:
            s = "⁦" + "".join(c for c in s if c not in MARKS) + "⁩"
        return s
