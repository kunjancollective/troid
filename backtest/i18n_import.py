#!/usr/bin/env python3
"""Import a reviewer's returned sheet and publish the language.

  python i18n_import.py ar returned.csv --by NA --on 2026-10-02
  python i18n_import.py ar returned.csv --by NA --on 2026-10-02 --dry-run

For every row the value is reviewer_edit where the reviewer wrote one, otherwise the draft. The sheet is refused
if any English cell no longer matches en.json (the page changed since the export: export again), if any key is
missing a value, or if any string breaks the contract in i18n.check_pair (same figures, placeholders, tags and
links as the English; troid lowercase in Latin script; no exclamation mark; product names in their fixed form).

On success web/i18n/{lang}.json is written with
  {"_reviewed_by": "<initials>", "_reviewed_on": "<date>", "_status": "live", ...}
and the next build (gen_compare.py in the shadow loop, or site_build.py) publishes /{lang}/.
"""
import argparse
import csv
import datetime as dt
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import i18n  # noqa: E402


def read_sheet(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    need = {"key", "english", "draft", "reviewer_edit", "note"}
    if not rows or not need <= set(rows[0].keys()):
        raise SystemExit(f"{path}: expected columns {sorted(need)}")
    return rows


def build(code, rows):
    en = i18n.english()
    out, data_en, problems, edited = {}, {}, [], 0
    seen = set()
    for r in rows:
        k = (r["key"] or "").strip()
        if not k:
            continue
        if k in seen:
            problems.append(f"{k}: appears twice in the sheet")
        seen.add(k)
        value = r["reviewer_edit"] if (r.get("reviewer_edit") or "").strip() else r["draft"]
        edited += bool((r.get("reviewer_edit") or "").strip())
        if k.startswith("data."):
            if i18n.data_key(r["english"]) != k:
                problems.append(f"{k}: the English cell was changed; export again")
                continue
            data_en[k] = r["english"]
        elif k not in en:
            problems.append(f"{k}: no longer a key in en.json; export again")
            continue
        elif r["english"] != en[k]:
            problems.append(f"{k}: the English has changed since this sheet was exported; export again")
            continue
        out[k] = value
    for k in en:
        if not (out.get(k) or "").strip():
            problems.append(f"{k}: no translation (draft and reviewer_edit both empty)")
    products = {k: out.get(k) for k in i18n.PRODUCTS}
    for k, v in out.items():
        if (v or "").strip():
            problems.extend(i18n.check_pair(k, data_en[k] if k.startswith("data.") else en[k], v, products))
    return out, data_en, problems, edited


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lang")
    ap.add_argument("sheet")
    ap.add_argument("--by", required=True, help="the reviewer's initials")
    ap.add_argument("--on", default=dt.date.today().isoformat(), help="the date the reviewer signed off")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.lang not in i18n.BY_CODE or a.lang == "en":
        raise SystemExit(f"unknown language {a.lang}")
    dt.date.fromisoformat(a.on)
    out, data_en, problems, edited = build(a.lang, read_sheet(a.sheet))
    if problems:
        print(f"{a.lang}: {len(problems)} problem(s); nothing written.")
        for p in problems[:80]:
            print("  ", p)
        sys.exit(1)
    en_order = list(i18n.english())
    doc = {"_reviewed_by": a.by, "_reviewed_on": a.on, "_status": "live", "_data_en": data_en}
    for k in en_order + sorted(k for k in out if k.startswith("data.")):
        if k in out and (out[k] or "").strip():
            doc[k] = out[k]
    print(f"{a.lang}: {len(doc) - 4} strings, {edited} edited by the reviewer, all checks pass.")
    if a.dry_run:
        print("dry run: nothing written.")
        return
    path = i18n.I18N / f"{a.lang}.json"
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
    print(f"wrote {path.relative_to(i18n.ROOT)} with _status live. Next: python backtest/gen_og.py {a.lang}, "
          f"then the build (cd backtest && python gen_compare.py && python gen_ledger.py) and python verify_claims.py.")


if __name__ == "__main__":
    main()
