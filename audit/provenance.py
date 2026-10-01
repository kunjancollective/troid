#!/usr/bin/env python3
"""Which rules troid's desk sizes with, and where troid read each one: firms.json's provenance, resolved here by rules
of the audit's own, never from the page or the generators (HANDOFF-calculator-audit, 29 Sep 2026).

A rule's source is the product's own entry (provenance.products.<product>.<field>). The firm-level entry
(provenance.fields.<field>) stands in only for a firm-wide value: never for a product's own daily or max loss, never
for a value the product sets itself (a calc.products override), and never for a field firms.json lists as
product_only (a cite that covers one product only). A band of leverage caps is cited by its own `cite` field.

A rule the desk uses has a value; one with no value is pending (the desk sizes around it and says so), which is not
the same as a value with no recorded source. The date a rule was read is the latest read of its sources.

  python3 audit/provenance.py        # every rule the desk uses, its source and read date
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import model as M  # noqa: E402

FIELD = {"d": "daily_pct", "m": "max_pct", "basis": "daily_basis", "dd": "drawdown", "locks": "locks_at_initial_after_pct",
         "hwm": "hwm_basis", "fee": "fee_per_side_pct", "lev": "max_leverage"}
STALE_DAYS = 45


def source(FJ, firm, prod, field, own):
    """{'section', 'src', 'dates'} for a rule, or None when no source is recorded. own: the product's own value."""
    P = FJ[firm].get("provenance") or {}
    ent = ((P.get("products") or {}).get(prod) or {}).get(field)
    if ent is None and not own and field not in (P.get("product_only") or []):
        ent = (P.get("fields") or {}).get(field)
    if not ent:
        return None
    S = P.get("sources") or {}
    unknown = [i for i in ent.get("src") or [] if i not in S]
    if unknown:
        raise ValueError(f"{firm} {prod} {field}: provenance cites unknown source(s) {unknown}")
    return {"section": ent.get("section", ""), "src": list(ent.get("src") or []),
            "dates": sorted({S[i]["read_on"] for i in ent.get("src") or [] if S[i].get("read_on")})}


def _gaps(bands):
    """Quota ranges no band covers, between one band's max_quota and the next band's min_quota."""
    tops = sorted(b["max_quota"] for b in bands if b.get("max_quota") is not None and b.get("min_quota") is None)
    lows = sorted(b["min_quota"] for b in bands if b.get("min_quota") is not None and b.get("max_quota") is None)
    return [(t, min(l for l in lows if l > t)) for t in tops if any(l > t for l in lows)]


def desk_rules(FJ, firm, prod):
    """(used, pending) for one product. used: dicts {rule, field, value, source} for every rule the desk sizes with;
    a leverage band carries its quota range. pending: dicts {rule, field, why} for the rules it has no value for."""
    r = M.rules(firm, prod, FJ)
    pc = FJ[firm]["calc"]["products"][prod]
    used, pending = [], []

    def use(rule, value, own=None, field=None, **extra):
        field = field or FIELD[rule]
        own = (field in pc) if own is None else own
        used.append({"rule": rule, "field": field, "value": value, "source": source(FJ, firm, prod, field, own), **extra})
    use("d", r["d"], own=True)
    use("m", r["m"], own=True)          # used even when the drawdown type is pending: it bounds the room (F3)
    if r["basis"] is not None:
        use("basis", r["basis"])
    else:
        pending.append({"rule": "basis", "field": FIELD["basis"], "why": "daily basis not recorded"})
    if r["dd"] is not None:
        use("dd", r["dd"])
        if r["dd"] == "trailing":
            if r["locks"] is not None:
                use("locks", r["locks"])
            if r["hwm"] is not None:
                use("hwm", r["hwm"])
            else:
                pending.append({"rule": "hwm", "field": FIELD["hwm"], "why": "high-water-mark basis not recorded"})
    else:
        pending.append({"rule": "dd", "field": FIELD["dd"], "why": "drawdown type not recorded (sized against the loosest reading of the max loss)"})
    if r["fee"] is not None:
        use("fee", r["fee"])
    else:
        pending.append({"rule": "fee", "field": FIELD["fee"], "why": "fee per side not recorded (sized before fees)"})
    if r["bands"]:
        for b in r["bands"]:
            use("lev", b["lev"], own=False, field=b.get("cite") or FIELD["lev"], band=[b.get("min_quota"), b.get("max_quota")])
        for lo, hi in _gaps(r["bands"]):
            pending.append({"rule": "lev", "field": FIELD["lev"],
                            "why": f"no leverage class between ${lo:,.0f} and ${hi:,.0f} (held to the lowest cap recorded)"})
    elif r["lev"] is not None:
        use("lev", r["lev"])
    else:
        pending.append({"rule": "lev", "field": FIELD["lev"], "why": "leverage cap not recorded"})
    return used, pending


def every(FJ=None):
    """[(firm, product, used, pending)] for every product the desk offers."""
    FJ = FJ or M.firms()
    return [(f, p, *desk_rules(FJ, f, p)) for f, p in M.offered(FJ)]


def read(u):
    """The date a used rule was last read, or None when it has no recorded source."""
    return max(u["source"]["dates"]) if u["source"] and u["source"]["dates"] else None


def rules_read(FJ=None):
    """{'from', 'to'}: the earliest and latest date troid last read a rule the desk sizes with."""
    ds = [read(u) for _, _, used, _ in every(FJ) for u in used if read(u)]
    return {"from": min(ds), "to": max(ds)} if ds else None


def stale(today, FJ=None, days=STALE_DAYS):
    """Rules the desk uses whose last read is more than `days` days before today."""
    cut = (today - dt.timedelta(days=days)).isoformat()
    return [{"firm": f, "product": p, "rule": u["field"], "read": read(u)}
            for f, p, used, _ in every(FJ) for u in used if read(u) and read(u) < cut]


def unsourced(FJ=None):
    """Rules the desk uses with no recorded source (the desk prints "Source not yet recorded for …")."""
    return [{"firm": f, "product": p, "rule": u["field"], "value": u["value"]}
            for f, p, used, _ in every(FJ) for u in used if not u["source"]]


def pending_rules(FJ=None):
    return [{"firm": f, "product": p, "rule": x["field"], "why": x["why"]} for f, p, _, pend in every(FJ) for x in pend]


if __name__ == "__main__":
    for f, p, used, pend in every():
        for u in used:
            s = u["source"]
            print(f"{f:20} {p:15} {u['field']:30} {str(u['value']):10} "
                  + (f"read {read(u) or '-':10} {s['section'][:70]}" if s else "NO SOURCE RECORDED"))
        for x in pend:
            print(f"{f:20} {p:15} {x['field']:30} {'pending':10} {x['why']}")
    print("rules read:", rules_read())
