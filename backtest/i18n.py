#!/usr/bin/env python3
"""troid's strings, in every language (HANDOFF-global-launch).

web/i18n/en.json holds every UI string, keyed. web/i18n/{lang}.json holds a translation: a draft
(_status 'draft', machine-drafted, unreviewed) or a live file (_status 'live', written by
i18n_import.py from the reviewer's sheet). Only live languages are published.

Values may carry HTML and two kinds of placeholder:
  {name}        filled by the caller: t("key", name=...)
  {L} and {H}   the language's path prefix ("" or "/zh") and its home link ("/" or "/zh"), filled for
                every string so internal links stay inside the reader's language.

check_pair() is the contract a translation must meet against its English string: the same figures,
the same placeholders, the same tags and link targets, troid lowercase in Latin script, no
exclamation mark, and each product name in the language's fixed form. i18n_import.py refuses a sheet
that breaks it, and verify_claims.py re-runs it over every live language.
"""
import hashlib
import html
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
I18N = ROOT / "web" / "i18n"
LANGS = json.loads((I18N / "languages.json").read_text())["languages"]
BY_CODE = {l["code"]: l for l in LANGS}
HEADER_KEYS = ("_reviewed_by", "_reviewed_on", "_status", "_note", "_drafted_by", "_drafted_on", "_data_en", "_review_notes",
               "_drafted_from")

# troid's product names, fixed once per language under these keys (the brand rule in BRAND.md)
PRODUCTS = {"product.desk": "troid's desk", "product.compare": "troid's compare", "product.ledger": "troid's ledger",
            "product.research": "troid's research", "product.ask": "ask troid"}


class MissingKey(KeyError):
    pass


# Text that reaches a page from data (firms.json: panel notes, rule values, open questions), not from en.json.
# Translated by content: the key is a hash of the English, so when firms.json changes the page falls back to
# the new English instead of showing a stale translation. Every string a render passes through T.data() is
# recorded here, so i18n_export.py can put it on the review sheet.
DATA_SEEN = {}


def data_key(s):
    return "data." + hashlib.sha1(s.encode("utf-8")).hexdigest()[:12]


def _read(path):
    return json.loads(path.read_text()) if path.exists() else None


_EN = None


def english():
    """en.json: every UI string, keyed (read once per process)."""
    global _EN
    if _EN is None:
        _EN = {k: v for k, v in json.loads((I18N / "en.json").read_text()).items() if not k.startswith("_")}
    return dict(_EN)


def en_hash(s):
    """A draft records the English each string was translated from (_drafted_from: key -> this hash), so a later
    change to en.json marks that string stale instead of leaving an outdated translation beside new English."""
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:10]


def stale(code):
    """Keys whose English changed after the draft was written, or that the draft never had."""
    h, s = load(code)
    was = h.get("_drafted_from") or {}
    return [k for k, v in english().items() if not s.get(k) or (was and was.get(k) != en_hash(v))]


def load(code):
    """(header, strings) for a language. English has no header and is always live."""
    if code == "en":
        return {"_status": "live"}, english()
    raw = _read(I18N / f"{code}.json")
    if raw is None:
        return {"_status": "absent"}, {}
    return {k: raw[k] for k in HEADER_KEYS if k in raw}, {k: v for k, v in raw.items() if not k.startswith("_")}


def live_codes():
    """English, then every language whose file says _status 'live', in registry order."""
    return [l["code"] for l in LANGS if l["code"] == "en" or load(l["code"])[0].get("_status") == "live"]


class Strings:
    """t(key, **kw) for one language. English is the fallback only when fallback=True (draft previews);
    a live language must carry every key, and English must carry every key a template asks for."""

    def __init__(self, code, fallback=False, pseudo=False):
        self.code, self.lang = code, BY_CODE[code]
        self.pseudo = pseudo          # i18n_pseudo.py: mark every keyed text segment ⟦…⟧ to find hard-coded text
        self.header, self.s = load(code)
        self.en = english()
        self.fallback = fallback
        self.L = "" if code == "en" else f"/{code}"
        self.H = "/" if code == "en" else f"/{code}"
        self.missing = set()

    def raw(self, key):
        if key not in self.en:
            raise MissingKey(f"key '{key}' is not in web/i18n/en.json")
        if key in self.s and self.s[key] not in (None, ""):
            return self.s[key]
        if self.code == "en":
            return self.en[key]
        if not self.fallback:
            raise MissingKey(f"key '{key}' is missing from web/i18n/{self.code}.json")
        self.missing.add(key)
        return self.en[key]

    def __call__(self, key, **kw):
        v = self.raw(key).replace("{L}", self.L).replace("{H}", self.H)
        if self.pseudo:
            v = mark(v)
        for k, x in kw.items():
            v = v.replace("{" + k + "}", str(x))
        return v

    def attr(self, key, **kw):
        """For an attribute value: only what would break the attribute is escaped (English stays byte-identical)."""
        return self(key, **kw).replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")

    def data(self, s):
        """A string from firms.json in this language: its reviewed translation if the language file has one,
        otherwise the English as it is. English is returned untouched."""
        if not isinstance(s, str) or not s.strip():
            return s
        k = data_key(s)
        DATA_SEEN[k] = s
        if self.code != "en" and self.s.get(k):
            return self.s[k]
        return mark(s) if self.pseudo else s       # translatable by content, so the pseudo scan counts it as keyed

    def js(self, prefix):
        """Every key under prefix, as a JSON object literal for the page's script (T.name)."""
        keys = sorted(k for k in self.en if k.startswith(prefix))
        return json.dumps({k[len(prefix):]: self(k) for k in keys}, ensure_ascii=False, separators=(",", ":"))


def mark(v):
    """Pseudo-locale: wrap each run of text between tags and placeholders in ⟦ ⟧ (never inside a tag)."""
    out, i = [], 0
    for m in re.finditer(r"<[^>]*>|\{[A-Za-z_][A-Za-z0-9_]*\}|&[a-zA-Z#0-9]+;", v):
        seg = v[i:m.start()]
        out.append(f"⟦{seg}⟧" if seg.strip() else seg)
        out.append(m.group(0)); i = m.end()
    seg = v[i:]
    out.append(f"⟦{seg}⟧" if seg.strip() else seg)
    return "".join(out)


# ---------------------------------------------------------------- the contract a translation meets
TAG = re.compile(r"<\s*(/?)\s*([a-zA-Z0-9]+)([^>]*)>")
HREF = re.compile(r'''\b(?:href|src)\s*=\s*"([^"]*)"''')
PH = re.compile(r"\{[A-Za-z_][A-Za-z0-9_]*\}")
NATIVE_DIGITS = re.compile(r"[٠-٩۰-۹०-९০-৯０-９]")
# A figure: digits joined by . or , (decimals, grouping) or by a space that groups thousands ("96 000", "1 539"),
# never by a space before anything else ("Sep 21 2026" is two figures, "1,539 4h" is two).
NUM = re.compile(r"\d+(?:(?:[.,]|[    ](?=\d{3}(?!\d)))\d+)*")
MONTHS = {m: i % 12 + 1 for i, m in enumerate(
    "January February March April May June July August September October November December "
    "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split())}
MONTHS["Sept"] = 9
MONTH = re.compile(r"\b(" + "|".join(sorted(MONTHS, key=len, reverse=True)) + r")\b")


def _text(s):
    s = PH.sub(" ", s)
    s = TAG.sub(" ", s)
    return html.unescape(s)


def figures(s):
    """The figures in a string, separators removed, as a sorted list: '96,000' and '96 000' are the same figure."""
    return sorted(re.sub(r"[.,\u00a0\u202f\u2009 ]", "", m.group(0)) for m in NUM.finditer(_text(s)))


def month_figures(s):
    """A month the English names may be written as its number in a translation (2021 年 1 月 1 日): each named
    month allows one extra figure, the month's number, with or without a leading zero."""
    out = Counter()
    for m in MONTH.finditer(_text(s)):
        n = MONTHS[m.group(1)]
        out[str(n)] += 1
        if n < 10:
            out[f"0{n}"] += 1
    return out


def figures_match(en, tr):
    """The same figures, except that a translation may write a month the English names as its number."""
    fe, ft = Counter(figures(en)), Counter(figures(tr))
    if fe == ft:
        return True
    if fe - ft:
        return False
    extra, allowed = ft - fe, month_figures(en)
    return (all(allowed[k] >= v for k, v in extra.items())
            and sum(extra.values()) <= sum(1 for _ in MONTH.finditer(_text(en))))


def tags(s):
    return sorted((m.group(1) + m.group(2).lower()) for m in TAG.finditer(s))


def check_pair(key, en, tr, products=None):
    """Problems with one translated string against its English. Empty list: it meets the contract."""
    out = []
    if not isinstance(tr, str) or not tr.strip():
        return [f"{key}: empty"]
    if NATIVE_DIGITS.search(tr):
        out.append(f"{key}: uses non-Latin digits; troid shows Latin digits in every language")
    if not figures_match(en, tr):
        out.append(f"{key}: figures differ — English {figures(en)} vs {figures(tr)}")
    if sorted(PH.findall(en)) != sorted(PH.findall(tr)):
        out.append(f"{key}: placeholders differ — {sorted(PH.findall(en))} vs {sorted(PH.findall(tr))}")
    if tags(en) != tags(tr):
        out.append(f"{key}: HTML tags differ — {tags(en)} vs {tags(tr)}")
    if sorted(HREF.findall(en)) != sorted(HREF.findall(tr)):
        out.append(f"{key}: link targets differ — {sorted(HREF.findall(en))} vs {sorted(HREF.findall(tr))}")
    ttext = _text(tr)
    if re.search(r"(?i)troid", _text(en)):
        if "troid" not in ttext:
            out.append(f"{key}: 'troid' missing — it stays lowercase, in Latin script")
    if re.search(r"Troid|TROID|[Тт]роид|トロイド|特洛伊德", ttext.replace("TROID.md", "")):   # the file name TROID.md stays
        out.append(f"{key}: troid must stay lowercase and in Latin script")
    if re.search(r"[!！¡]", ttext):
        out.append(f"{key}: exclamation mark (troid never uses one)")
    if products and not key.startswith("product."):
        for pk, pen in PRODUCTS.items():
            if pen in _text(en) and products.get(pk) and products[pk] not in ttext:
                out.append(f"{key}: product name '{pen}' should read '{products[pk]}' (the fixed form in this language)")
    return out


def check_language(code, strings=None, require_all=True):
    """Every problem in one language file against en.json."""
    en = english()
    h, s = load(code) if strings is None else ({}, strings)
    products = {k: s.get(k) for k in PRODUCTS}
    out = []
    for k, v in en.items():
        if k not in s or s[k] in (None, ""):
            if require_all:
                out.append(f"{k}: missing")
            continue
        out.extend(check_pair(k, v, s[k], products))
    for k in s:
        if k not in en and not k.startswith("data."):
            out.append(f"{k}: not a key in en.json")
    return out + check_data(s, h.get("_data_en") or {}, products)


def check_data(s, src, products=None):
    """Translated data strings (data.<hash>) against the English they were made from (the file's _data_en)."""
    out = []
    for k, v in s.items():
        if k.startswith("data.") and k in src:
            out.extend(check_pair(k, src[k], v, products))
    return out


if __name__ == "__main__":
    import sys
    codes = sys.argv[1:] or [l["code"] for l in LANGS if l["code"] != "en"]
    for c in codes:
        h, s = load(c)
        st = stale(c) if h.get("_status") != "absent" else []
        probs = [x for x in check_language(c, require_all=h.get("_status") == "live")
                 if h.get("_status") == "live" or x.split(":")[0] not in st]     # a stale draft is re-translated, not checked
        print(f"{c}: {h.get('_status')} · {len(s)} strings · {len(probs)} problem(s)"
              + (f" · {len(st)} stale (English changed or missing): {st[:6]}" if st else ""))
        for p in probs[:40]:
            print("   ", p)
