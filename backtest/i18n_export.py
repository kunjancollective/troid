#!/usr/bin/env python3
"""Write one review sheet per language: web/i18n/review/{lang}.csv, columns key, english, draft, reviewer_edit, note.

Reviewers are friends, not developers: the sheet opens in Google Sheets and is the whole interface. They fill
reviewer_edit where the draft is wrong, leave it empty where it is right, and use note for anything else.
Rows come in this order: troid's product names first (fixed once per language, used everywhere), then the
shared lines, then each page, then text that comes from firm data (firms.json).

  python i18n_export.py            # every language with a file
  python i18n_export.py ar zh
"""
import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import i18n  # noqa: E402
import site_build  # noqa: E402

REVIEW = i18n.I18N / "review"
ORDER = ["product.", "og.", "share.", "common.", "footer.", "legal.", "hypo.", "prov.", "index.", "compare.", "ledger.",
         "dashboard.", "tearsheet.", "chat.", "faq.", "terms.", "data."]


def data_strings():
    """Every firms.json string a page passes through T.data(), found by rendering each page in English."""
    i18n.DATA_SEEN.clear()
    T = i18n.Strings("en")
    ctx = site_build.extra_context(T)
    for page in site_build.PAGES:
        site_build.render_page(page, T, ["en"], ctx=ctx if page in site_build.STATIC else None)
    Tp = i18n.Strings("zh", fallback=True)          # the translated path renders a few more (stubs, governing lines)
    for page in site_build.PAGES:
        site_build.render_page(page, Tp, ["en", "zh"], ctx=site_build.extra_context(Tp) if page in site_build.STATIC else None)
    return dict(i18n.DATA_SEEN)


def note_for(key, en):
    tips = []
    if key.startswith("product."):
        tips.append("troid's product name: choose one form here; it is used the same way everywhere")
    if key.startswith("data."):
        tips.append("text from a firm's rules (firms.json)")
    if i18n.PH.search(en):
        tips.append("keep " + " ".join(sorted(set(i18n.PH.findall(en)))) + " exactly as written")
    if i18n.TAG.search(en):
        tips.append("keep the <…> tags and links as they are; translate only the words")
    if i18n.figures(en):
        tips.append("keep every number exactly")
    if "troid" in en:
        tips.append("troid stays lowercase, in Latin letters")
    return "; ".join(tips)


def rank(key, pos):
    """The sheet's order: the prefix groups above, and inside a group the order the page shows the strings in."""
    for i, p in enumerate(ORDER):
        if key.startswith(p):
            return (i, pos.get(key, 0), key)
    return (len(ORDER), pos.get(key, 0), key)


def export(code, data):
    en = i18n.english()
    header, s = i18n.load(code)
    pos = {k: i for i, k in enumerate(en)}
    rows = [(k, en[k]) for k in sorted(en, key=lambda k: rank(k, pos))] + [(k, v) for k, v in sorted(data.items())]
    check = header.get("_review_notes") or {}      # the drafter's questions for the reviewer, by key ('*': general)
    stale = set(i18n.stale(code)) if header.get("_drafted_from") else set()
    REVIEW.mkdir(parents=True, exist_ok=True)
    path = REVIEW / f"{code}.csv"
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["key", "english", "draft", "reviewer_edit", "note"])
        for q in check.get("*", []):
            w.writerow(["", "", "", "", "CHECK FIRST: " + q])
        for k, v in rows:
            note = note_for(k, v)
            if check.get(k):
                note = " | ".join(["CHECK FIRST: " + q for q in check[k]] + ([note] if note else []))
            draft = s.get(k, "")
            if k in stale and draft:        # the English changed after this draft: never offer the old translation
                draft, note = "", "ENGLISH CHANGED after the draft: translate it in reviewer_edit | " + note
            w.writerow([k, v, draft, "", note])
    return path, len(rows), sum(1 for k, _ in rows if s.get(k))


def main():
    codes = sys.argv[1:] or [l["code"] for l in i18n.LANGS if l["code"] != "en" and i18n.load(l["code"])[0].get("_status") != "absent"]
    data = data_strings()
    for c in codes:
        p, n, d = export(c, data)
        print(f"{c}: {p.relative_to(i18n.ROOT)} · {n} rows · {d} drafted")


if __name__ == "__main__":
    main()
