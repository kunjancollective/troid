#!/usr/bin/env python3
"""The weekly calculator audit (HANDOFF-calculator-audit, 29 Sep 2026): troid's desk, as built, driven in Chromium
through every case in audit/cases.py, each figure it shows compared with audit/model.py, which reads firms.json and
derives the figure itself. The audit is not written by the thing it audits: nothing here reads or imports the desk's
code; the page is served, its fields are set, its own render() runs, and its "show the working" table is read back.

Pages: the English desk (web/public, as built) and one right-to-left page, /ar, built for the run as a draft preview
(backtest/site_build.py --preview; Arabic is not published yet). A page's row labels are its language's strings
(web/i18n/{lang}.json, English where the draft has none); its numbers are read in its locale's format (languages.json
"num"), bidirectional marks dropped.

A check is one case on one page (its verdict and every figure the case shows), plus each data check: the page's inline
FIRMS equals firms.json for every product (on each page), and on the English page every rule the desk sizes with either
cites its source in the provenance block or is named in "Source not yet recorded for …", as firms.json records it.
The report also lists the rules with no recorded source, the pending rules and read dates older than 45 days.

  python3 audit/run.py                    # this ISO week (UTC): web/public/audit.json and audit/reports/<week>.md
  python3 audit/run.py --week 2026-W40    # any week again, exactly: the random cases are seeded by the week
  python3 audit/run.py --no-write         # print the result, write nothing
  python3 audit/run.py --no-write --revert all   # diagnosis: the seed's derivations, to show the harness is clean

Exit 0 when every check passed, 1 on any mismatch, 2 when the audit itself couldn't run: a bad argument, a pinned
figure the model misses, a page with no desk, a preview that won't build, a browser that won't start, any crash. A 2
writes nothing, so a workflow can tell "the audit found mismatches" from "there is no audit this week".
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import itertools
import json
import math
import re
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import cases as C  # noqa: E402
import model as M  # noqa: E402
import provenance as P  # noqa: E402

sys.path.insert(0, str(ROOT / "backtest"))
from i18n_equiv import serve  # noqa: E402  (a static server with Vercel's cleanUrls; no desk code)

PUB = ROOT / "web" / "public"
I18N = ROOT / "web" / "i18n"
REPO = "https://github.com/kunjancollective/troid/blob/main/"
CHROMIUM = Path("/opt/pw-browsers/chromium")
WEEK = re.compile(r"^\d{4}-W(0[1-9]|[1-4]\d|5[0-3])$")
MAX_LISTED = 50

# ------------------------------------------------------------------------------------------------ a page's language
EN = json.loads((I18N / "en.json").read_text())
LANGS = {l["code"]: l for l in json.loads((I18N / "languages.json").read_text())["languages"]}
PATHS = {"en": "/", "ar": "/ar"}


class Lang:
    """A page's strings (its language, English where a draft has none) and its number format."""

    def __init__(self, code):
        self.code = code
        raw = EN if code == "en" else json.loads((I18N / f"{code}.json").read_text())
        self.s = {k: v for k, v in raw.items() if not k.startswith("_")}
        self.num = LANGS[code]["num"]
        self.missing = set()

    def __call__(self, key):
        v = self.s.get(key)
        if v in (None, ""):
            v = EN.get(key)
        if v is None:
            self.missing.add(key)
        return v

    def plain(self, key):
        v = self(key)
        return None if v is None else norm(html.unescape(re.sub(r"<[^>]+>", "", v)))


def norm(s):
    return " ".join((s or "").split())


BIDI = dict.fromkeys(map(ord, "‎‏؜⁦⁧⁨⁩‪‫‬‭‮"), None)


def parse(s, fmt):
    """A figure as the page writes it, in its locale's format; None when it isn't one number."""
    if s is None:
        return None
    t = s.translate(BIDI).replace("−", "-")
    for tok in ("US$", "$US", "$", "×", "%"):
        t = t.replace(tok, "")
    t = re.sub(r"[\s  ]", "", t)
    if fmt.get("group", ",").strip():
        t = t.replace(fmt["group"], "")
    if fmt.get("decimal", ".") != ".":
        t = t.replace(fmt["decimal"], ".")
    t = t.replace("--", "-")
    if not re.fullmatch(r"-?\d+(?:\.\d+)?(?:e[-+]?\d+)?", t):
        return None
    return float(t)


def half_ulp(s, fmt, places=0):
    """Half a unit in the last place a figure is written to: how far the page's rounding can have moved it. `places`
    is the fewest the page writes such a figure to (it trims trailing zeros: "600" is 600.000000)."""
    t = (s or "").translate(BIDI)
    t = re.sub(r"[\s\u00a0\u202f]", "", t)
    dec = fmt.get("decimal", ".")
    if fmt.get("group", ",").strip() and fmt["group"] != dec:
        t = t.replace(fmt["group"], "")
    m = re.search(re.escape(dec) + r"(\d+)", t)
    return 0.5 * 10 ** -max(places, len(m.group(1)) if m else 0)


def pieces(tpl):
    """A string's literal text around its {placeholders}, tags dropped: what the page must show, in order."""
    t = html.unescape(re.sub(r"<[^>]+>", "", tpl))
    return [norm(p) for p in re.split(r"\{[A-Za-z_]+\}", t) if norm(p)]


def fill(tpl, text):
    """The figures a page wrote into one of its strings: {placeholder: what stands there} when `text` is exactly `tpl`
    with its placeholders filled (tags dropped, bidirectional marks and runs of spaces ignored), else None. Stricter
    than says(): the literal words must be all there is, and each figure can then be read and compared."""
    if tpl is None:
        return None
    t = norm(html.unescape(re.sub(r"<[^>]+>", "", tpl)).translate(BIDI))
    rx, names = "", []
    for i, part in enumerate(re.split(r"\{([A-Za-z_]+)\}", t)):
        if not i % 2:
            rx += re.escape(part)
        elif part in names:
            rx += f"(?P={part})"
        else:
            names.append(part)
            rx += f"(?P<{part}>.+?)"
    m = re.fullmatch(rx, norm((text or "").translate(BIDI)))
    return m.groupdict() if m else None


def says(text, tpl):
    pos = 0
    for p in pieces(tpl):
        i = text.find(p, pos)
        if i < 0:
            return False
        pos = i + len(p)
    return True


# ------------------------------------------------------------------------------------------------ comparing one case
LAB = [("dF", ["index.js.daily_floor"]), ("ddF", ["index.js.dd_floor"]), ("dB", ["index.js.st_daily_budget"]),
       ("ddB", ["index.js.st_dd_budget"]), ("hwm", ["index.js.st_hwm"]), ("hi", ["index.js.st_hi"]),
       ("intended", ["index.js.st_intended"]), ("cap", ["index.js.st_cap"]),
       ("risk", ["index.js.risk"]), ("dist", ["index.js.st_dist"]), ("fpu", ["index.js.st_fpu"]),
       ("qty", ["index.js.st_qty"]), ("notional", ["index.js.st_notional"]), ("lev_used", ["index.js.st_lev_used"]),
       ("margin", ["index.js.margin"]), ("margin0", ["index.js.st_margin_check"]), ("fees", ["index.js.fees"]),
       ("loss", ["index.js.st_loss"]), ("used", ["index.js.budget_used"]), ("left", ["index.js.st_left"]),
       ("target", ["index.js.st_target"]), ("ddist", ["index.js.st_daily_dist"]),
       ("fdist", ["index.js.st_dd_dist", "index.js.st_trailing_dist"])]
ACCOUNT = {"dF", "ddF", "dB", "ddB", "hwm", "hi"}      # the account's rows: in every state past the range check
BEFORE_SIZING = ACCOUNT | {"intended", "cap", "risk"}  # compared, when present, on a trade that isn't sized
RANGE_LABEL = {"quota": "index.calc.quota", "equity": "index.calc.equity", "daystart": "index.calc.daystart",
               "risk_pct": "index.calc.risk_pct", "cap_pct": "index.calc.cap_pct", "leverage": "index.calc.leverage",
               "entry": "index.calc.entry", "stop": "index.calc.stop"}
RANGE_WHY = {"gt0": "index.js.b_gt0", "pct": "index.js.b_pct", "lev": "index.js.b_lev"}
BLOCK_WHY = {"long": "index.js.b_long", "short": "index.js.b_short", "zero": "index.js.b_zero", "breached": "index.js.b_breached",
             "reaches": "index.js.b_reaches"}                # a reason the model names otherwise is index.js.b_<name>

DOLLAR = 0.0051        # a dollar figure is written to the cent: half a cent, and float slack, whatever the account's size
PCT2 = 0.0051          # a percentage written to two decimals
# The places the desk writes a target price to (index.html's st_target row and the readout's "tgt"). Two decimals say
# nothing about a sub-dollar asset's target (0.08016 and the entry, 0.08, both show 0.08), so the review's finding 14
# moves the desk to n4, six decimals; this becomes 6 in the same commit, and the audit then holds the target as it
# holds the entry and the stop. Set lower than the desk writes, the check only loosens; set higher, a right desk fails.
TARGET_PLACES = 2


def tol(key, e):
    """How far a figure the page writes may sit from the model's: dollars and the working table's percentages to half a
    cent (an absolute band: a relative one let a $100k account's floor sit 9 cents off), budget used to 0.05 points
    (one decimal shown), a quantity, a fee per unit or a stop distance to 1e-6 (relative where larger)."""
    if key == "used":
        return 0.051
    if key in ("qty", "fpu", "dist"):
        return max(1e-6, abs(e) * 1e-6)
    return DOLLAR


def tol_target(g, fmt, e):
    """A target price: half a unit in the last place it is written to, never coarser than TARGET_PLACES decimals."""
    return max(half_ulp(g, fmt, TARGET_PLACES), abs(e) * 1e-9) + 1e-9


def fmt_x(v):
    if isinstance(v, float):
        return f"{v:.6f}".rstrip("0").rstrip(".") if math.isfinite(v) else str(v)
    return str(v)


def rawnum(s, fmt):
    """A number the page prints as JavaScript's String() does (a leverage, a typed percentage, a count), or failing
    that, in its locale's format."""
    t = (s or "").translate(BIDI).strip().rstrip("×x%").strip()
    try:
        return float(t)
    except ValueError:
        return parse(s, fmt)


def near(g, e, t, fmt):
    v = parse(g, fmt)
    return v is not None and e is not None and math.isfinite(e) and abs(v - e) <= t


def applies(key, r):
    """Whether the product's rules put this account row in the table: the high-water mark on a trailing drawdown, the
    high at rollover on a daily limit set from it."""
    if key == "hwm":
        return r["dd"] == "trailing"
    if key == "hi":
        return r["basis"] == "max_balance_equity"
    return True


def binding(exp):
    """Which limit binds: the daily one when its budget is at most the drawdown's (SPEC.md: dB ≤ ddB → daily)."""
    dB, ddB = exp.get("dB"), exp.get("ddB")
    return "daily" if dB is not None and (ddB is None or dB <= ddB) else "dd"


def floor_none(exp, key, x, L):
    """The words a floor distance is shown as instead of a number, or None. A long can't fall more than 100%, so a
    floor that far below the entry isn't reached above zero (SPEC.md R6, which extends F5's rule to the floors), once
    the page's language has the words for it (index.js.v_floor_none); before that the desk writes the number."""
    v = exp.get(key)
    if v is None or M.num(x.get("side", 1)) <= 0 or v < 100 - 1e-9:
        return None
    return L.plain("index.js.v_floor_none")


def breakers(exp, entry, r, x, L):
    """[(label, adverse %, words shown instead of the number or None)] in the order the page must list its circuit
    breakers: stop, daily limit, floor and exchange liquidation, least adverse first; one a long can't reach sorts last,
    as infinity, in that order (JavaScript's sort is stable, like Python's)."""
    trl = r["dd"] == "trailing" and not exp.get("locked")
    mode = L.plain("index.js.isolated" if x.get("mode") == "isolated" else "index.js.cross")
    ords = [(L.plain("index.js.br_stop"), exp["dist"] / entry * 100, None)]
    for key, bkey, lab in (("ddist", "dB", L.plain("index.js.br_daily")),
                           ("fdist", "ddB", L.plain("index.js.trailing_floor" if trl else "index.js.dd_floor"))):
        if exp.get(bkey) is not None:
            nw = floor_none(exp, key, x, L)
            ords.append((lab, math.inf if nw else exp[key], nw))
    liq_lab = norm(html.unescape(re.sub(r"<[^>]+>", "", (L("index.js.br_liq") or "")).replace("{mode}", mode or "")))
    liq_none = L.plain("index.js.v_liq_none") if exp.get("liq_none") else None
    ords.append((liq_lab, math.inf if liq_none else max(exp["liq"], 0), liq_none))
    return sorted(ords, key=lambda o: o[1])


def compare(exp, got, L):
    """[(what, expected, got)]: every way the page differs from the model for one case."""
    bad = []
    text = norm(got["text"])
    if got.get("err"):
        bad.append(("script error", "none", got["err"]))
    if got.get("where") and got["where"] != [got["want_firm"], got["want_product"]]:
        bad.append(("product", f"{got['want_firm']} {got['want_product']}", " ".join(got["where"])))
    v = got["v"]
    pend = L("index.js.vs_pending")
    if pend and says(text, pend):
        v = "PENDING"
    if exp["v"] != v:
        bad.append(("verdict", exp["v"], v))
    if exp["v"] == "PENDING":
        return bad
    if exp.get("range"):                                     # F2: each field named
        for fld in exp["range"]:
            why, lab = L(RANGE_WHY[M.RANGE[fld]]), L.plain(RANGE_LABEL.get(fld, f"index.calc.{fld}"))
            if why is None or lab is None:
                bad.append(("string", f"{RANGE_WHY[M.RANGE[fld]]} / {RANGE_LABEL.get(fld, fld)}", "not in en.json"))
                continue
            want = norm(html.unescape(re.sub(r"<[^>]+>", "", why.replace("{field}", lab))))
            if want not in text:
                bad.append((f"reason: {fld}", want, text[:160]))
        return bad

    x = got.get("x") or {}
    entry = M.num(x.get("entry", ""))
    r = M.rules(got["want_firm"], got["want_product"])
    rows = {}
    for row in got["rows"]:
        if len(row) == 3:
            rows.setdefault(norm(row[0]), (norm(row[1]), norm(row[2])))
    sized = exp["v"] in ("OK", "REDUCE")
    if exp["v"] == "BLOCK":
        for b in exp.get("blocks", []):
            k = BLOCK_WHY.get(b, f"index.js.b_{b}")
            if L(k) is None or not says(text, L(k)):
                bad.append((f"reason: {b}", L.plain(k) or k, text[:160]))

    # the binding limit, by name, and the room it leaves: in the table's binding row in every state, and in the verdict
    # line wherever there is one (a wrong name there reads through the verdict, the notes and the explainer)
    want_bind = L.plain("index.js.bind_daily" if binding(exp) == "daily" else "index.js.bind_dd")
    lab_b = L.plain("index.js.st_binding")
    if lab_b not in rows:
        bad.append((f"row: {lab_b}", want_bind, "missing"))
    else:
        g = rows[lab_b][1]
        head, _, fig = g.rpartition(" · ")
        if head != want_bind:
            bad.append((lab_b, want_bind, g))
        if not near(fig, exp["eff"], DOLLAR, L.num):
            bad.append((f"{lab_b} (room)", fmt_x(exp["eff"]), g))
    vt = norm((got.get("vtxt") or "").translate(BIDI))
    if exp["v"] == "BLOCK":
        if vt != want_bind:
            bad.append(("verdict line (binding)", want_bind, vt))
    elif exp["v"] in ("OK", "REDUCE", "SET"):
        f = fill(L("index.js.v_txt"), vt)
        if f is None or norm(f["bind"]) != want_bind or not near(f["room"], exp["eff"], DOLLAR, L.num):
            bad.append(("verdict line", f"{want_bind} · {fmt_x(exp['eff'])}", vt))

    got_v = {}
    for key, keys in LAB:
        e = exp.get(key)
        if e is None or (not sized and key not in BEFORE_SIZING) or not applies(key, r):
            continue
        labs = [L.plain(k) for k in keys]
        if all(l is None for l in labs):
            bad.append(("string", keys[0], "not in en.json"))
            continue
        lab = next((l for l in labs if l in rows), None)
        if lab is None:
            if sized or key in ACCOUNT:
                bad.append((f"row: {labs[0] or keys[0]}", fmt_x(e), "missing"))
            continue
        formula, g = rows[lab]
        nw = floor_none(exp, key, x, L) if key in ("ddist", "fdist") else None
        if nw is not None:                                   # a long's floor it can't reach (R6): words, not a number
            if g != nw:
                bad.append((labs[0], nw, g))
            continue
        if key in ("fees", "dist"):
            g0 = g.split("(")[0]
        else:
            g0 = g
        gv = rawnum(g0, L.num) if key in ("lev_used", "left") else parse(g0, L.num)
        got_v[key] = (gv, half_ulp(g0, L.num, 6 if key in ("qty", "dist", "fpu") else 0))
        t = tol_target(g0, L.num, e) if key == "target" else tol(key, e)
        if gv is None or not math.isfinite(e) or abs(gv - e) > t:
            bad.append((labs[0], fmt_x(e), g))
        if key == "dist":                                    # its share of the entry, in parentheses
            m = re.search(r"\(([^)]*)\)", g)
            want = e / entry * 100 if entry else math.nan
            if not near(m.group(1) if m else None, want, PCT2, L.num):
                bad.append((f"{labs[0]} (% of entry)", fmt_x(want), g))
        if key == "fees" and exp.get("fshare") is not None:
            m = re.search(r"\(([^)]*)\)", g)
            if not near(m.group(1).split()[0] if m else None, exp["fshare"], PCT2, L.num):
                bad.append((f"{labs[0]} (share of risk)", fmt_x(exp["fshare"]), g))
        if key == "margin0":                                 # F1: the row says which way the check went
            want = L("index.js.f_margin_cut" if exp.get("cut") else "index.js.f_margin_fits")
            if want is None:
                bad.append(("string", "index.js.f_margin_cut" if exp.get("cut") else "index.js.f_margin_fits", "not in en.json"))
            elif not (says(formula, want) if exp.get("cut") else formula == L.plain("index.js.f_margin_fits")):
                bad.append((f"{labs[0]} (formula)", norm(html.unescape(want)), formula))
        if key == "qty" and exp.get("cut"):
            want = L.plain("index.js.f_qty_margin")
            if want is None or formula != want:
                bad.append((f"{labs[0]} (formula)", want or "index.js.f_qty_margin", formula))
    if not sized:
        return bad

    # liquidation: a long at or beyond 100% is "none above zero" (F5); at or below 0 it is below maintenance
    liq_pre = (L.plain("index.js.br_liq") or "").split("{mode}")[0].strip()
    liq_rows = [k for k in rows if liq_pre and k.startswith(liq_pre)]
    e = exp["liq"]
    if not liq_rows:
        bad.append((f"row: {liq_pre or 'index.js.br_liq'}", fmt_x(e), "missing"))
    else:
        g = rows[liq_rows[0]][1]
        if e <= 0:
            if not says(g, L("index.js.v_liq_below") or "\x00"):
                bad.append(("liquidation", L.plain("index.js.v_liq_below"), g))
        elif exp.get("liq_none"):
            none = L.plain("index.js.v_liq_none")
            if none is None or g != none:
                bad.append(("liquidation", none or "index.js.v_liq_none", g))
        elif not near(g, e, PCT2, L.num):
            bad.append(("liquidation", fmt_x(e), g))

    loss = exp.get("loss", exp.get("risk"))           # the loss at the stop (the risk, with F6 reverted for diagnosis)
    fee_known = exp.get("fee_known")
    pend_w = L.plain("index.js.pending")

    # the readout: the six cells a trader reads first, each figure and the line under it
    cells = {}
    for k, val, sub in got.get("read") or []:
        cells.setdefault(norm(k), (norm(val), norm(sub)))
    stop_pct = exp["dist"] / entry * 100 if entry else math.nan
    for key, e, t, sub_key, sub_want in (
            ("index.js.size", exp["qty"], tol("qty", exp["qty"]), None, exp["notional"]),
            ("index.js.margin", exp["margin"], DOLLAR,
             "index.js.s_lev_pending" if exp.get("cap_l") is None else "index.js.s_lev", {"lev": exp["lev_used"]}),
            ("index.js.risk", loss, DOLLAR, "index.js.s_incl_fees" if fee_known else "index.js.s_fees_pending",
             {"fees": exp["fees"]} if fee_known else {}),
            ("index.js.fees", exp["fshare"] if fee_known else None, 0.0501, None, None),
            ("index.js.stop", stop_pct, PCT2, "index.js.s_tgt", {"price": exp["target"]}),
            ("index.js.budget_used", exp["used"], 0.5001, "index.js.s_floor", {"floor": exp.get("ddF")})):
        lab = L.plain(key)
        if lab not in cells:
            bad.append((f"readout: {lab or key}", fmt_x(e) if e is not None else pend_w, "missing"))
            continue
        gv, gs = cells[lab]
        if e is None:                                        # a fee troid hasn't recorded: pending, not a number
            if gv != pend_w:
                bad.append((f"readout: {lab}", pend_w, gv))
        elif not near(gv, e, t, L.num):
            bad.append((f"readout: {lab}", fmt_x(e), gv))
        if sub_key is None:
            if sub_want is not None and not near(gs, sub_want, DOLLAR, L.num):
                bad.append((f"readout: {lab} (under it)", fmt_x(sub_want), gs))
            continue
        f = fill(L(sub_key), gs)
        ok = f is not None
        for ph, w in (sub_want or {}).items():
            if not ok:
                break
            if w is None:                                    # a pending floor
                ok = norm(f[ph]) == pend_w
            elif ph == "lev":
                ok = rawnum(f[ph], L.num) == w
            elif ph == "price":
                ok = near(f[ph], w, tol_target(f[ph], L.num, w), L.num)
            else:
                ok = near(f[ph], w, DOLLAR, L.num)
        if not ok:
            bad.append((f"readout: {lab} (under it)", ", ".join(f"{k} {fmt_x(w)}" for k, w in (sub_want or {}).items())
                        or L.plain(sub_key), gs))

    # the verdict sentence, figure by figure: F1's margin cut, the budget cap's cut, or the fit
    rp, cp = M.num(x.get("riskPct")), M.num(x.get("capPct"))
    if exp.get("cut"):
        key, want = "index.js.vs_margin", {"lev": exp["lev_used"], "max": exp["lev_max"], "risk": loss}
    elif exp["v"] == "REDUCE":
        key, want = "index.js.vs_reduce", {"pct": rp, "intended": exp["intended"], "risk": exp["risk"], "cap": cp}
    else:
        key, want = "index.js.vs_ok", {"risk": loss, "cap": cp, "room": exp["eff"], "bind": want_bind}
    vs = norm(got.get("vsent"))
    f = fill(L(key), vs)
    if f is None:
        bad.append(("verdict sentence", L.plain(key) or key, vs[:160]))
    else:
        for ph, w in want.items():
            if isinstance(w, str):
                ok = norm(f[ph]) == w
            elif ph in ("lev", "pct", "cap"):
                ok = rawnum(f[ph], L.num) is not None and abs(rawnum(f[ph], L.num) - w) <= 1e-9
            else:
                ok = near(f[ph], w, DOLLAR, L.num)
            if not ok:
                bad.append((f"verdict sentence {{{ph}}}", fmt_x(w), f[ph]))

    # the circuit breakers, each at its own distance, least adverse first
    order = breakers(exp, entry, r, x, L)
    brk = norm((got.get("brk") or "").translate(BIDI))
    head = L.plain("index.js.breakers") or ""
    segs = [norm(s) for s in (brk[len(head):] if brk.startswith(head) else brk).split("→") if norm(s)]
    seen = []
    for s in segs:
        lab = max((o[0] for o in order if o[0] and s.startswith(o[0])), key=len, default=None)
        if lab is None:
            bad.append(("breakers", " → ".join(o[0] for o in order), brk[:160]))
            break
        val = norm(s[len(lab):])
        want, none = next((o[1], o[2]) for o in order if o[0] == lab)
        if none is not None:
            if val != none:
                bad.append((f"breakers: {lab}", none, val))
            gv = math.inf
        else:
            gv = parse(val, L.num)
            if gv is None or abs(gv - want) > PCT2:
                bad.append((f"breakers: {lab}", f"{want:.2f}%", val))
        seen.append((lab, math.inf if gv is None else gv))
    if sorted(l for l, _ in seen) != sorted(o[0] for o in order):
        bad.append(("breakers (which)", " → ".join(o[0] for o in order), brk[:160]))
    elif any(b[1] < a[1] - 1e-9 for a, b in zip(seen, seen[1:])):
        bad.append(("breakers (order)", " → ".join(o[0] for o in order), brk[:160]))

    # the notes a fix adds, where the case calls for them
    notes = [norm((n or "").translate(BIDI)) for n in got.get("notes") or []]

    def note(key, t=0.0501, **want):
        """The note `key` among the page's notes, with these figures in it (a percentage within `t`)."""
        for n in notes:
            f = fill(L(key), n)
            if f is not None and all((norm(f[k]) == w) if isinstance(w, str) else
                                     (rawnum(f[k], L.num) == w if k in ("n", "lev") else near(f[k], w, t, L.num))
                                     for k, w in want.items()):
                return True
        return False
    for flag, key in (("hwm_raised", None), ("hi_raised", "index.js.n_hi_raised"), ("dd_loosest", "index.js.n_dd_loosest"),
                      ("lev_held", "index.js.n_lev_held")):
        if not exp.get(flag):
            continue
        if flag == "hwm_raised":
            key = "index.js.n_hwm_raised_equity" if exp["hwm_raised"] == "equity" else "index.js.n_hwm_raised"
        if L(key) is None or not says(text, L(key)):
            bad.append((f"note: {key.split('.')[-1]}", L.plain(key) or key, "not shown"))
    # losses left, with the binding limit named (F7)
    if exp.get("left") is not None and not note("index.js.n_left", n=exp["left"], bind=want_bind):
        bad.append(("note: n_left", fmt_x(exp["left"]) + " · " + want_bind, " | ".join(notes)[:160]))
    # the breaker that bites first: DANGER when it isn't the stop; else cross's warning, or isolated's liquidation, which
    # a long at 1x doesn't have (F5). A near tie between the first two is left alone: either reading is the page's to make
    tie = len(order) > 1 and abs(order[0][1] - order[1][1]) < 1e-7
    if not tie:
        first, pct, _ = order[0]
        if first != L.plain("index.js.br_stop"):
            if not note("index.js.n_danger", PCT2, what=first, pct=pct):
                bad.append(("note: n_danger", f"{first} {pct:.2f}%", " | ".join(notes)[:160]))
        elif x.get("mode") == "isolated":
            if exp.get("liq_none"):
                if not note("index.js.n_isolated_none", lev=exp["lev_used"]):
                    bad.append(("note: n_isolated_none", L.plain("index.js.n_isolated_none"), " | ".join(notes)[:160]))
                if any(fill(L("index.js.n_isolated"), n) is not None for n in notes):
                    bad.append(("note: n_isolated", "absent (no liquidation above zero)", "shown"))
            elif not note("index.js.n_isolated", pct=exp["liq"]):
                bad.append(("note: n_isolated", f"{exp['liq']:.1f}%", " | ".join(notes)[:160]))
        elif norm((L.plain("index.js.n_cross") or "").translate(BIDI)) not in notes:
            bad.append(("note: n_cross", L.plain("index.js.n_cross"), " | ".join(notes)[:160]))

    # the page against itself: its quantity × (its stop distance + its fee per unit) is its loss at the stop, to the
    # cent, allowing only for the places each figure is written to (the loss to the cent, the others to six decimals)
    vals = [got_v.get(k) for k in ("qty", "dist", "fpu", "loss")]
    if all(v and v[0] is not None for v in vals):
        (q, hq), (d, hd), (f, hf), (lo, hl) = vals
        slack = max(hl, 0.005) + hq * (d + f) + (q + hq) * (hd + hf) + 1e-9
        if abs(q * (d + f) - lo) > slack:
            bad.append(("quantity × (stop distance + fee per unit) = loss at the stop", f"{q * (d + f):.4f}", fmt_x(lo)))
    return bad


def diagnose(c, got, L):
    """Which handoff item a mismatch is about: the smallest set of items whose seed derivation makes the page match.
    An out-of-range input the page sizes anyway is F2 whatever it shows (the figures of an impossible input mean
    nothing). A label for the report only; it never decides a check."""
    if M.model(c["firm"], c["product"], c["x"]).get("range") and got["v"] != "BLOCK":
        return "F2"
    for k in range(1, len(M.ITEMS)):
        for sub in itertools.combinations(M.ITEMS, k):
            if not compare(M.model(c["firm"], c["product"], c["x"], revert=sub), got, L):
                return "+".join(sub)
    if not compare(M.model(c["firm"], c["product"], c["x"], revert=M.ITEMS), got, L):
        return "+".join(M.ITEMS)
    return "unexplained"


# ------------------------------------------------------------------------------------------------ driving a page
DRIVE = """(cs)=>cs.map(([f,p,x])=>{
  const set=(k,v)=>{const e=document.getElementById(k);if(e)e.value=v};let err=null;
  try{set('firm',f);fillProfiles();set('profile',p);toggleInputs();['hwm','hirollover'].forEach(k=>set(k,''));
    for(const k in x)set(k,String(x[k]));render();}catch(e){err=String(e&&e.message||e)}
  const R=document.getElementById('result'),vd=R.querySelector('.verdict'),tx=(e)=>e?e.textContent:'';
  return {rows:[...R.querySelectorAll('details.work tr')].map(r=>[...r.children].map(td=>td.textContent)),
    v:vd?((vd.className.match(/\\bv(OK|REDUCE|BLOCK|SET)\\b/)||[])[1]||null):(R.querySelector('.d2empty')?'EMPTY':null),
    text:R.textContent,vsent:tx(vd&&vd.querySelector('.vsent')),vtxt:tx(vd&&vd.querySelector('.vtxt')),
    read:[...R.querySelectorAll('.read .cell')].map(c=>['.k','.v','.s'].map(s=>tx(c.querySelector(s)))),
    notes:[...R.querySelectorAll('.notes > div:not(.brk)')].map(tx),
    brk:[...R.querySelectorAll('.brk')].map(e=>e.textContent).join(' '),prov:(R.querySelector('.prov')||{}).textContent||'',
    where:[document.getElementById('firm').value,document.getElementById('profile').value],err}})"""
CHUNK = 25


def launch(pw):
    return pw.chromium.launch(executable_path=str(CHROMIUM)) if CHROMIUM.exists() else pw.chromium.launch()


def drive(browser, url, cases, states):
    """Every case on one page: what the page shows for each, its inline FIRMS, and its provenance block at `states`."""
    ctx = browser.new_context(viewport={"width": 1280, "height": 900}, locale="en-US", timezone_id="UTC")

    def handler(r):
        u = r.request.url.split("?")[0]
        if u.endswith(("/status.json", "/calendar.json", "/audit.json")) or "/api/ticker" in u:
            return r.fulfill(status=404, body="")
        return r.continue_() if u.startswith("http://127.0.0.1") else r.abort()
    ctx.route("**/*", handler)
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(url, wait_until="load")
    pg.wait_for_timeout(600)
    ready = pg.evaluate("()=>['render','fillProfiles','toggleInputs'].every(n=>typeof window[n]==='function')"
                        "&&typeof FIRMS==='object'&&!!document.getElementById('result')")
    if not ready:
        ctx.close()
        cant(f"{url} has no desk to drive (render, fillProfiles, toggleInputs, FIRMS, #result)")
    firms_page = pg.evaluate("()=>JSON.parse(JSON.stringify(FIRMS))")
    out = []
    for i in range(0, len(cases), CHUNK):
        chunk = cases[i:i + CHUNK]
        n0 = len(errs)
        res = pg.evaluate(DRIVE, [[c["firm"], c["product"], c["x"]] for c in chunk])
        for c, r in zip(chunk, res):
            r["want_firm"], r["want_product"], r["x"] = c["firm"], c["product"], c["x"]
            if len(errs) > n0 and not r["err"]:
                r["err"] = "page error while this batch ran: " + errs[-1][:200]
            out.append(r)
    prov = pg.evaluate(DRIVE, [[f, p, x] for f, p, x in states]) if states else []
    ctx.close()
    return out, firms_page, prov, errs


# ------------------------------------------------------------------------------------------------ the data checks
def same(a, b):
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool) and not isinstance(b, bool):
        return float(a) == float(b)
    return a == b


def bands_of(x):
    return sorted(((b.get("min_quota"), b.get("max_quota"), float(b["lev"])) for b in (x or [])), key=str)


def firms_check(page_firms, FJ):
    """[(name, problems)] for every product: the page's inline FIRMS against firms.json, every calc field."""
    offered = M.offered(FJ)
    on_page = [(f, p) for f, F in (page_firms or {}).items() for p in (F.get("products") or {})]
    out = []
    for f, p in offered + [x for x in on_page if x not in offered]:
        probs = []
        if (f, p) not in on_page:
            probs.append("offered in firms.json, missing from the page's FIRMS")
        elif (f, p) not in offered:
            probs.append("in the page's FIRMS, not a product firms.json offers")
        else:
            r, Q = M.rules(f, p, FJ), page_firms[f]["products"][p]
            for k in ("d", "m", "basis", "dd", "locks", "hwm", "fee", "lev"):
                if not same(Q.get(k), r[k]):
                    probs.append(f"{k}: page {Q.get(k)!r}, firms.json {r[k]!r}")
            if bands_of(Q.get("levb")) != bands_of(r["bands"]):
                probs.append(f"leverage bands: page {bands_of(Q.get('levb'))}, firms.json {bands_of(r['bands'])}")
        out.append((f"FIRMS = firms.json: {label(FJ, f, p) if (f, p) in offered else f + ' ' + p}", probs))
    return out


def js_num(v):
    """A rule value as the desk's strings print it (String(x) for the numbers firms.json holds)."""
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return format(float(v), ".15g")
    return str(v)


def rule_label(u):
    """The rule's name in the English provenance block (index.js.u_*)."""
    key = {"d": "u_daily", "m": "u_max", "basis": "u_basis", "dd": "u_dd", "locks": "u_locks", "hwm": "u_hwm",
           "fee": "u_fee", "lev": "u_lev"}[u["rule"]]
    s = EN["index.js." + key]
    for ph in ("d", "m", "locks", "fee", "lev"):
        s = s.replace("{" + ph + "}", js_num(u["value"]))
    return norm(s)


def prov_states(FJ):
    """Where to read each product's provenance block: the desk grid's first row, and a quota inside each leverage band."""
    base = dict(C.BASE, entry=77872, stop=74814)
    states = []
    for f, p in M.offered(FJ):
        qs = [100000] + [b.get("max_quota") or b.get("min_quota") for b in (M.rules(f, p, FJ)["bands"] or [])]
        for q in qs:
            states.append((f, p, dict(base, quota=q, equity=q, daystart=q)))
    return states


def prov_check(FJ, page_firms, states, prov):
    """[(name, problems)] for every product: each rule the desk sizes with, in the page's data (pv) and in its
    provenance block, cited with its source where firms.json records one, named as not yet recorded where it doesn't."""
    texts = {}
    for (f, p, x), r in zip(states, prov):
        texts.setdefault((f, p), []).append((x["quota"], norm(r["prov"])))
    out = []
    for f, p in M.offered(FJ):
        probs = []
        used, _ = P.desk_rules(FJ, f, p)
        Q = ((page_firms.get(f) or {}).get("products") or {}).get(p)
        name = FJ[f]["name"]
        if Q is None:
            out.append((f"provenance: {label(FJ, f, p)}", ["not on the page"]))
            continue
        for u in used:                                            # the page's own record of each rule's source
            if "band" in u:
                pv = next((b.get("pv") for b in Q.get("levb") or [] if same(b.get("lev"), u["value"])
                           and [b.get("min_quota"), b.get("max_quota")] == u["band"]), None)
            else:
                pv = (Q.get("pv") or {}).get(u["rule"])
            if bool(pv) != bool(u["source"]):
                probs.append(f"{u['field']}: the page {'cites a source' if pv else 'has no source'}, firms.json "
                             f"{'records ' + ', '.join(u['source']['src']) if u['source'] else 'records none'}")
            elif pv and sorted(pv.get("o") or []) != u["source"]["dates"]:
                probs.append(f"{u['field']}: read {pv.get('o')} on the page, {u['source']['dates']} in firms.json")
        for q, text in texts.get((f, p), []):                    # what the block says
            m = re.search(re.escape(pieces(EN["index.js.prov_missing"])[0]) + r"(.+?)\.(?:\s|$)", text)
            missing = m.group(1) if m else ""
            for u in used:
                if "band" in u and not ((u["band"][0] is None or q >= u["band"][0]) and (u["band"][1] is None or q <= u["band"][1])):
                    continue
                lab = rule_label(u)
                if u["source"]:
                    sec = u["source"]["section"]
                    secs = {sec, sec[len(name) + 1:] if sec.startswith(name + " ") else sec}
                    secs |= {s.replace(" — ", ": ") for s in secs}
                    cited = any(lab in seg and any(seg.find(" from " + s) > seg.find(lab) >= 0 for s in secs)
                                for seg in text.split(" · "))
                    if not cited:
                        probs.append(f"${q:,}: {lab} is not cited with its source ({sec})")
                    if lab in missing:
                        probs.append(f"${q:,}: {lab} is listed as not yet recorded, but firms.json records {', '.join(u['source']['src'])}")
                elif lab not in missing:
                    probs.append(f"${q:,}: {lab} has no recorded source and the block doesn't say so")
        out.append((f"provenance: {label(FJ, f, p)}", probs))
    return out


# ------------------------------------------------------------------------------------------------ the report
def label(FJ, f, p):
    """A product as the desk names it: "Bitfunded 2-Step · S1"."""
    return f"{FJ[f]['name']} {FJ[f]['calc']['products'][p].get('label', p)}"


def inputs_str(x):
    keys = ["quota", "equity", "daystart", "hwm", "hirollover", "side", "entry", "stop", "targetR", "riskPct", "capPct", "lev", "mode"]
    return ", ".join(f"{k}={x[k]}" for k in keys if k in x and x[k] not in (None,))


def report_md(R):
    L = []
    w = L.append
    w(f"# Calculator audit, {R['week']}")
    w("")
    w(f"Run {R['date']} (UTC) on commit `{R['commit']}`{' (with uncommitted changes)' if R['dirty'] else ''}; "
      f"random cases seeded by `{R['seed']}`." + (f" **Diagnosis run: the model's {', '.join(R['revert'])} reverted to the seed's "
                                                  "derivations. Not an audit result.**" if R["revert"] else ""))
    w("")
    w(f"Totals: {R['checks']:,} checks, {R['passed']:,} passed, {R['failed']:,} failed.")
    w("")
    w("## What was checked, and how")
    w("")
    w("- **The model.** `audit/model.py` reads `firms.json` directly, not the page's `FIRMS`, and derives every figure "
      "from the firm's rules and first principles, as the seed the owner reviewed did, with the changes the handoff's "
      "F1–F7 and D6 require (listed in its docstring). It imports no desk or generator code.")
    w(f"- **The pages.** {', '.join(R['page_notes'])}. Chromium drove each page's own `render()` with the case's inputs "
      "and read back the verdict, the result's text and the \"show the working\" table. Row labels are the page's own "
      "strings; numbers are read in its locale's format.")
    g = R["groups"]
    w(f"- **The cases, on each page ({R['cases']:,}).** {g['edge']} edge cases from the seed; {g['regression']} named "
      f"regressions for F1–F7 and D6; the desk's grid, {len(C.GRID)} rows on each of the {g['grid'] // len(C.GRID)} "
      f"products the desk offers ({g['grid']}); {g['random']:,} random cases seeded by `{R['seed']}`. Before any page "
      f"was driven, the model was held to the {R['pins']} figures the edge cases and regressions pin by hand.")
    w("- **Each case** (one check per page): the verdict; every figure in the working table (floors, budgets, the "
      "high-water mark and the high at rollover where the product has them, the binding limit by name and its room, "
      "intended risk, cap, risk, stop distance and its share of the entry, fee per unit, quantity, notional, leverage "
      "used, margin, the margin check, fees and their share, the loss at the stop, budget used, losses left, target, "
      "the limit distances, liquidation); the readout's six cells and the line under each (size and notional, margin "
      "and leverage, risk and fees, fee share, stop and target, budget used and floor); the verdict sentence and the "
      "verdict line, each figure in them; the circuit breakers, each distance and their order; the notes: losses left "
      "with the binding limit named, the breaker that bites first, and those a fix adds. Dollars to the cent (half a "
      "cent, whatever the account's size), quantities, fees per unit and stop distances to 1e-6, a target to "
      f"{TARGET_PLACES} decimals, percentages to the places shown, budget used to 0.05 points in the table. A "
      "blocked trade's reasons, each out-of-range field named; the formulas a fix adds; and the page against itself: "
      "its quantity × (stop distance + fee per unit) equals its loss at the stop, to the cent.")
    w(f"- **Data checks.** The page's inline `FIRMS` against `firms.json`, every calc field of every product, on each "
      f"page ({R['n_firms_checks']}); on the English page, each product's provenance: every rule the desk sizes with "
      f"cites its source, or is named in \"Source not yet recorded for …\", as `firms.json` records it ({R['n_prov_checks']}).")
    w("")
    w("## Mismatches")
    w("")
    if not R["mismatches"]:
        w("None.")
    else:
        pages = R["pages"]
        w("Each mismatched case is labelled with the handoff items that account for it: the smallest set of items whose "
          "earlier derivation (the seed's) makes the page match. A label for reading the report, never a check; a case "
          "counts once under each of its items.")
        w("")
        w("| item | " + " | ".join(f"cases on `{pg}`" for pg in pages) + " |")
        w("|---|" + "---|" * len(pages))
        for item in [*M.ITEMS, "unexplained"]:
            ns = [sum(n for (pg, cat), n in R["categories"].items() if pg == p and item in cat.split("+")) for p in pages]
            if any(ns):
                w(f"| {item} | " + " | ".join(f"{n:,}" for n in ns) + " |")
        w("")
        w("<details><summary>By combination</summary>")
        w("")
        w("| page | items | cases |")
        w("|---|---|---|")
        for (pg, cat), n in sorted(R["categories"].items(), key=lambda kv: (kv[0][0], -kv[1], kv[0][1])):
            w(f"| `{pg}` | {cat} | {n:,} |")
        w("")
        w("</details>")
        w("")
        shown = R["mismatches"][:MAX_LISTED]
        w(f"The first {len(shown)} of {len(R['mismatches']):,} cases:" if len(R["mismatches"]) > MAX_LISTED else f"All {len(shown)}:")
        w("")
        for m in shown:
            w(f"- **`{m['page']}` {m['id']}**, {m['name']}: {m['label']}; items: {m['diagnosis']}")
            w(f"  - inputs: `{m['inputs']}`")
            for what, e, g2 in m["bad"][:8]:
                w(f"  - {what}: expected `{e}`, got `{str(g2)[:140]}`")
            if len(m["bad"]) > 8:
                w(f"  - and {len(m['bad']) - 8} more")
    w("")
    w("## Data checks")
    w("")
    ok = [d for d in R["data"] if not d[1]]
    w(f"{len(ok)} of {len(R['data'])} passed." + ("" if len(ok) < len(R["data"]) else " "
      "Every product's inline `FIRMS` equals `firms.json` on each page, and every rule the desk sizes with is cited with "
      "its source or named as not yet recorded."))
    w("")
    for name, probs, pg in R["data"]:
        if probs:
            w(f"- **failed**: `{pg}` {name}")
            for pr in probs:
                w(f"  - {pr}")
    w("")
    w("## Rules the desk uses with no recorded source")
    w("")
    w("The desk prints \"Source not yet recorded for …\" beside each of these.")
    w("")
    for u in R["unsourced"] or []:
        w(f"- {label(M.firms(), u['firm'], u['product'])}: `{u['rule']}` = {u['value']}")
    if not R["unsourced"]:
        w("None.")
    w("")
    w("## Pending rules")
    w("")
    w("No value recorded; the desk sizes around them and says so.")
    w("")
    for u in R["pending"] or []:
        w(f"- {label(M.firms(), u['firm'], u['product'])}: `{u['rule']}`: {u['why']}")
    if not R["pending"]:
        w("None.")
    w("")
    w(f"## Read dates older than {P.STALE_DAYS} days")
    w("")
    rr = R["rules_read"]
    w(f"Rules the desk uses were read from {rr['from']} to {rr['to']}." if rr else "No rule has a read date.")
    w("")
    for u in R["stale"]:
        w(f"- {label(M.firms(), u['firm'], u['product'])}: `{u['rule']}`, read {u['read']}")
    if not R["stale"]:
        w(f"None as of {R['date']}.")
    w("")
    w("## Reproduce")
    w("")
    w("```")
    w(f"git checkout {R['commit']}")
    w(f"python3 audit/run.py --week {R['week']} --no-write")
    w("```")
    w("")
    w("The random cases depend only on the week; the edge cases, regressions and grid are fixed in `audit/cases.py`. "
      "`python3 audit/cases.py` holds the model to its pinned figures without a browser.")
    return "\n".join(L) + "\n"


# ------------------------------------------------------------------------------------------------ main
def this_week(now=None):
    y, wk, _ = (now or dt.datetime.now(dt.timezone.utc)).isocalendar()
    return f"{y}-W{wk:02d}"


def git(*a):
    return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True).stdout.strip()


class CantRun(Exception):
    """The audit couldn't run: exit 2, write nothing."""


def cant(msg):
    raise CantRun(msg)


def main():
    """Exit 0, 1 or 2 (the module's docstring). argparse's own errors already exit 2; everything else that stops the
    run before its result is written, whatever raised it, exits 2 as well, never 1, which means mismatches."""
    try:
        code = _main()
    except CantRun as e:
        print(f"audit: couldn't run: {e}", file=sys.stderr)
        sys.exit(2)
    except SystemExit:
        raise
    except BaseException:                                    # a crash, the browser, a preview build, Ctrl-C
        traceback.print_exc()
        print("audit: couldn't run (above); nothing written", file=sys.stderr)
        sys.exit(2)
    sys.exit(code)


def _main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--week", help="ISO week, e.g. 2026-W40 (default: this week, UTC); seeds the random cases")
    ap.add_argument("--n", type=int, default=1000, help="random cases (default 1000)")
    ap.add_argument("--json", default=str(PUB / "audit.json"), help="where to write the result (default web/public/audit.json)")
    ap.add_argument("--report", help="where to write the report (default audit/reports/<week>.md)")
    ap.add_argument("--no-write", action="store_true", help="print the result, write nothing")
    ap.add_argument("--pages", default="en,ar", help="languages to audit (default en,ar)")
    ap.add_argument("--site", default=str(PUB), help="the built English site (default web/public)")
    ap.add_argument("--revert", help="diagnosis only: items whose seed derivation the model uses (F1,F6 or all); writes nothing")
    a = ap.parse_args()

    week = a.week or this_week()
    if not WEEK.match(week):
        cant(f"--week must look like 2026-W40, not {week!r}")
    revert = tuple(M.ITEMS if a.revert == "all" else [x.strip() for x in a.revert.split(",")]) if a.revert else ()
    if any(x not in M.ITEMS for x in revert):
        cant(f"--revert takes {', '.join(M.ITEMS)} or all")
    write = not a.no_write and not revert
    langs = [x.strip() for x in a.pages.split(",") if x.strip()]
    if any(x not in PATHS for x in langs):
        cant(f"--pages takes {', '.join(PATHS)}")
    now = dt.datetime.now(dt.timezone.utc)
    FJ = M.firms()
    cases = C.all_cases(week, a.n, FJ)

    pins = C.pin_check(cases, FJ)
    if pins:
        for p in pins:
            print("PIN  ", *p)
        cant(f"the model misses {len(pins)} pinned figure(s); the model or the case needs the owner's review")

    from playwright.sync_api import sync_playwright
    states = prov_states(FJ)
    results = {}
    with tempfile.TemporaryDirectory() as tmp, sync_playwright() as pw:
        roots = {"en": Path(a.site)}
        if "ar" in langs:           # a draft: rendered for the run, never into web/public
            b = subprocess.run([sys.executable, str(ROOT / "backtest" / "site_build.py"), "--preview", tmp, "--langs", "ar"],
                               cwd=ROOT, capture_output=True, text=True)
            if b.returncode:
                cant(f"the /ar preview didn't build (site_build.py --preview exited {b.returncode}):\n{b.stderr[-2000:]}")
            roots["ar"] = Path(tmp)
        browser = launch(pw)
        for lang in langs:
            srv, url = serve(roots[lang])
            try:
                results[lang] = drive(browser, url + PATHS[lang], cases, states if lang == "en" else [])
            finally:
                srv.shutdown()
        browser.close()

    mismatches, categories, data = [], {}, []
    passed = failed = 0
    for lang in langs:
        got_all, firms_page, prov, errs = results[lang]
        Lg = Lang(lang)
        for c, got in zip(cases, got_all):
            exp = M.model(c["firm"], c["product"], c["x"], FJ, revert=revert)
            bad = compare(exp, got, Lg)
            if bad:
                failed += 1
                diag = diagnose(c, got, Lg) if not revert else "diagnosis run"
                categories[(PATHS[lang], diag)] = categories.get((PATHS[lang], diag), 0) + 1
                mismatches.append({"page": PATHS[lang], "id": c["id"], "name": c["name"], "firm": c["firm"],
                                   "product": c["product"], "label": label(FJ, c["firm"], c["product"]),
                                   "inputs": inputs_str(c["x"]), "bad": bad, "diagnosis": diag})
            else:
                passed += 1
        checks = firms_check(firms_page, FJ) + (prov_check(FJ, firms_page, states, prov) if lang == "en" else [])
        for name, probs in checks:
            data.append((name, probs, PATHS[lang]))
            if probs:
                failed += 1
            else:
                passed += 1

    rr = P.rules_read(FJ)
    commit = git("rev-parse", "HEAD")
    if write and not re.fullmatch(r"[0-9a-f]{40}", commit):
        # audit.js hides a line whose commit isn't one: an audit.json without it would publish nothing, silently
        cant(f"git rev-parse HEAD gave {commit!r}, not a commit; the result would name no tree")
    R = {"date": now.date().isoformat(), "week": week, "seed": week, "commit": commit,
         "dirty": bool(git("status", "--porcelain")), "checks": passed + failed, "passed": passed, "failed": failed,
         "cases": len(cases), "pages": [PATHS[x] for x in langs], "revert": list(revert),
         "groups": {g: sum(1 for c in cases if c["group"] == g) for g in ("edge", "regression", "grid", "random")},
         "pins": sum(len(c["pin"]) for c in cases), "mismatches": mismatches, "categories": categories, "data": data,
         "n_firms_checks": sum(1 for d in data if d[0].startswith("FIRMS")),
         "n_prov_checks": sum(1 for d in data if d[0].startswith("provenance")),
         "rules_read": rr, "stale": P.stale(now.date(), FJ), "unsourced": P.unsourced(FJ), "pending": P.pending_rules(FJ),
         "page_notes": [("`/`, the English desk as built (`" + (str(Path(a.site).resolve().relative_to(ROOT)) if Path(a.site).resolve().is_relative_to(ROOT) else a.site) + "`)")
                        if x == "en" else "`/ar`, right to left: the Arabic draft preview (`backtest/site_build.py --preview`); "
                        "Arabic is not published yet, and its missing strings fall back to English as the preview's do"
                        for x in langs]}
    report_rel = f"audit/reports/{week}.md"
    out = {"date": R["date"], "week": week, "commit": R["commit"], "checks": R["checks"], "passed": passed,
           "failed": failed, "report": report_rel, "pages": R["pages"], "cases": len(cases), "seed": week,
           "rules_read": rr, "stale_rules": R["stale"], "unsourced_rules": R["unsourced"]}

    print(f"audit {week}: {R['checks']:,} checks, {passed:,} passed, {failed:,} failed "
          f"({len(cases):,} cases on {', '.join(R['pages'])}; {len(data)} data checks)" + (f" [revert {', '.join(revert)}]" if revert else ""))
    for pg in R["pages"]:
        tally = {i: sum(n for (p, cat), n in categories.items() if p == pg and i in cat.split("+")) for i in [*M.ITEMS, "unexplained"]}
        if any(tally.values()):
            print(f"  {pg:4} cases by item: " + ", ".join(f"{i} {n:,}" for i, n in tally.items() if n))
    for m in mismatches[:12]:
        print(f"  {m['page']:4} {m['id']:34} {m['diagnosis']:18} {m['bad'][0][0]}: expected {str(m['bad'][0][1])[:40]}, got {str(m['bad'][0][2])[:50]}")
    if len(mismatches) > 12:
        print(f"  … and {len(mismatches) - 12:,} more case(s)")
    for name, probs, pg in data:
        if probs:
            print(f"  data {pg} {name}: " + "; ".join(probs)[:400])
    for lang in langs:
        if results[lang][3]:
            print(f"  page errors on {PATHS[lang]}: {results[lang][3][:3]}")
    if write:
        rp = Path(a.report) if a.report else ROOT / report_rel
        rp.parent.mkdir(parents=True, exist_ok=True)
        rp.write_text(report_md(R))
        jp = Path(a.json)
        jp.parent.mkdir(parents=True, exist_ok=True)
        jp.write_text(json.dumps(out, indent=1) + "\n")
        print(f"wrote {jp} and {rp}")
    return 1 if failed else 0


if __name__ == "__main__":
    main()
