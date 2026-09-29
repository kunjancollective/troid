#!/usr/bin/env python3
"""The independent model of troid's desk, for the weekly calculator audit (HANDOFF-calculator-audit, 29 Sep 2026).

The audit is not written by the thing it audits. This model reads firms.json itself, never the page's FIRMS, and
derives every figure the desk shows from the firm's rules and first principles. Nothing here imports, copies or reads
the desk's code (render() in web/templates/index.html, web/public/desk2.js, backtest/regions.py) or any generator.

Its derivations are those of the seed the owner reviewed (calc_audit_seed.py, 29 Sep 2026). A change to them needs the
owner's review; don't change the model to make a mismatch go away. The changes from the seed, each one required by an
item of the handoff as SPEC.md (the contract the desk and this model were both written from) states it:

  F2  Input bounds, checked first: quota, entry and stop above 0 (an empty entry or stop is not out of range), risk %
      and budget cap % above 0 and at most 100, leverage at least 1. Out of range is BLOCK in every state, naming each
      field. (The seed sized whatever it was given.)
  F4  The high-water mark is never below the quota, and on a firm that trails on equity never below equity; the high
      at rollover is never below the day start. (The seed took a typed value as it was.)
  F3  A pending drawdown type with the max loss known is bounded by quota × (1 − max%), the loosest reading of the
      rule: a trailing floor is never lower than the static one. (The seed left that floor unknown.)
  F6  Fee per unit is fee × (entry + stop): the exit fee priced at the stop, the way an exchange charges it. (The seed
      used the desk's convention then, both sides priced at entry.)
  D6  A quota no leverage band covers is held to the lowest cap the firm records. (The seed held it to the highest.)
  F1  A size whose margin would exceed equity is cut to equity × leverage used ÷ entry, and the verdict is REDUCE.
      With the cut, fee share and budget used are taken on the loss at the stop, not on the risk before the cut.
  F7  Losses left is ceil(room ÷ loss − 1e-9) − 1, the losses that leave equity above the floor: firms word a breach
      as reaching the limit. (The seed's `survivable`; its `left` was floor(room ÷ risk).)
  F5  A long's liquidation at or beyond 100% of the entry is "none above zero"; a short is shown as computed.
  F6  The loss at the stop, qty·dist + qty·entry·fee + qty·stop·fee (the seed's true_loss), is a figure the desk
      now shows, so it is compared.

`revert` is for diagnosis only: it names handoff items whose seed derivation to use instead, so audit/run.py can say
which item a mismatch is about (a page that matches the model with F6 reverted still uses the pre-F6 fee). It never
decides whether a check passes.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MMR = 0.005          # exchange maintenance margin: troid's assumption, no firm source (SPEC.md)
ITEMS = ("F1", "F2", "F3", "F4", "F5", "F6", "F7", "D6")
_FJ = None


def firms(path=None):
    """firms.json, read once."""
    global _FJ
    if path is not None:
        return json.loads(Path(path).read_text())
    if _FJ is None:
        _FJ = json.loads((ROOT / "firms.json").read_text())
    return _FJ


def offered(FJ=None):
    """Every (firm, product) the desk can size: a firm with calc rules, a product with both its daily and max loss."""
    FJ = FJ or firms()
    out = []
    for fk, f in FJ.items():
        if not isinstance(f, dict) or "calc" not in f:
            continue
        for pk in f["calc"].get("products") or {}:
            pr = (f.get("products") or {}).get(pk) or {}
            if pr.get("daily_pct") is not None and pr.get("max_pct") is not None:
                out.append((fk, pk))
    return out


def rules(firm, prod, FJ=None):
    """A product's rules from firms.json: a calc.products override wins over the firm-level calc value; the daily and
    max loss are the product's own. Leverage is the product's own cap if it has one, else the firm's cap or its bands."""
    FJ = FJ or firms()
    f = FJ[firm]; c = f["calc"]; pc = c["products"][prod]; pr = f["products"][prod]

    def pick(k):
        return pc[k] if k in pc else c.get(k)
    r = dict(d=pr.get("daily_pct"), m=pr.get("max_pct"), basis=pick("daily_basis"), dd=pick("drawdown"),
             locks=pick("locks_at_initial_after_pct"), hwm=pick("hwm_basis"), fee=pick("fee_per_side_pct"))
    if "max_leverage" in pc:
        r["lev"], r["bands"] = pc["max_leverage"], None
    else:
        r["lev"], r["bands"] = c.get("max_leverage"), c.get("lev_bands")
    return r


def lev_cap(r, quota):
    """The leverage cap for this quota: the product's cap, or the band that covers the quota (None when none does)."""
    if not r["bands"]:
        return r["lev"]
    for b in r["bands"]:
        if (b.get("max_quota") is None or quota <= b["max_quota"]) and (b.get("min_quota") is None or quota >= b["min_quota"]):
            return b["lev"]
    return None


def num(v):
    """A field's value as the desk reads it: blank or unparseable is 0."""
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return float(v) if math.isfinite(v) else 0.0
    try:
        x = float(str(v).strip())
        return x if math.isfinite(x) else 0.0
    except ValueError:
        return 0.0


def given(v):
    """Whether a field has anything in it."""
    return str(v).strip() != "" if v is not None else False


def _div(a, b):
    """a ÷ b, and what the arithmetic gives at b = 0 (inputs F2 blocks, reached only with F2 reverted)."""
    if b:
        return a / b
    return float("nan") if not a else math.copysign(float("inf"), a)


RANGE = {"quota": "gt0", "risk_pct": "pct", "cap_pct": "pct", "leverage": "lev", "entry": "gt0", "stop": "gt0"}


def model(firm, prod, x, FJ=None, revert=()):
    """Every figure the desk shows for these inputs. x: quota, equity, daystart, hwm, hirollover (blank or 0: none),
    side (+1 / -1), entry, stop, targetR, riskPct, capPct, lev, mode ('cross' | 'isolated')."""
    revert = set(revert)
    r = rules(firm, prod, FJ)
    q, eq, ds = num(x["quota"]), num(x["equity"]), num(x["daystart"])
    H, R = num(x.get("hwm", "")), num(x.get("hirollover", ""))
    side = 1 if num(x["side"]) > 0 else -1
    entry, stop = num(x.get("entry", "")), num(x.get("stop", ""))
    rp, cp, L = num(x["riskPct"]), num(x["capPct"]), num(x["lev"])
    out = {}

    # F2: out of range is BLOCK before anything is derived, naming each field
    if "F2" not in revert:
        bad = []
        if q <= 0:
            bad.append("quota")
        if not 0 < rp <= 100:
            bad.append("risk_pct")
        if not 0 < cp <= 100:
            bad.append("cap_pct")
        if L < 1:
            bad.append("leverage")
        if given(x.get("entry")) and entry <= 0:
            bad.append("entry")
        if given(x.get("stop")) and stop <= 0:
            bad.append("stop")
        if bad:
            return {"v": "BLOCK", "range": bad}

    # F4: the high-water mark and the high at rollover can't be below what the account has already been
    hwm = H if H > 0 else max(eq, q)
    hi = R if R > 0 else ds
    if "F4" not in revert:
        hwm = max(hwm, q)
        if r["hwm"] == "equity":
            hwm = max(hwm, eq)
        hi = max(hi, ds)
        if H > 0 and hwm > H:
            out["hwm_raised"] = "equity" if r["hwm"] == "equity" and H < eq else "quota"
        if R > 0 and hi > R:
            out["hi_raised"] = True
    out.update(hwm=hwm, hi=hi)

    d = r["d"] / 100 if r["d"] is not None else None
    m = r["m"] / 100 if r["m"] is not None else None
    # daily floor: an independent reading of each basis
    dF = None
    if r["basis"] == "initial":
        dF = ds - d * q                 # a fixed dollar allowance off the day's start
    elif r["basis"] == "day_start":
        dF = ds - d * ds                # a percentage of the day's start
    elif r["basis"] == "max_balance_equity":
        dF = hi - d * q
    # max-loss floor
    ddF = None; locked = False
    if r["dd"] == "static":
        ddF = q - m * q
    elif r["dd"] == "trailing":
        locked = r["locks"] is not None and hwm >= q * (1 + r["locks"] / 100)
        ddF = q if locked else hwm - m * q
    elif r["dd"] is None and m is not None and "F3" not in revert:
        ddF = q - m * q                 # F3: the loosest reading of a pending drawdown type
        out["dd_loosest"] = True
    out.update(dF=dF, ddF=ddF, locked=locked)
    dB = None if dF is None else eq - dF
    ddB = None if ddF is None else eq - ddF
    out.update(dB=dB, ddB=ddB)
    if dB is None and ddB is None:
        out["v"] = "PENDING"
        return out
    eff = min(v for v in (dB, ddB) if v is not None)
    out["eff"] = eff

    dist = abs(entry - stop)
    blocks = []
    if side > 0 and stop >= entry:
        blocks.append("long")
    if side < 0 and stop <= entry:
        blocks.append("short")
    if dist <= 0:
        blocks.append("zero")
    if eff <= 0:
        blocks.append("breached")
    intended = rp / 100 * eq
    cap = cp / 100 * max(eff, 0)
    risk = min(intended, cap)
    out.update(intended=intended, cap=cap, risk=risk)
    if blocks:
        out["v"] = "BLOCK"; out["blocks"] = blocks
        return out

    fee_known = r["fee"] is not None
    f = (r["fee"] or 0) / 100
    fpu = f * (entry + stop) if "F6" not in revert else 2 * f * entry
    qty0 = _div(risk, dist + fpu)
    cap_l = lev_cap(r, q)
    lev_used = L
    if cap_l is not None:
        lev_used = min(L, cap_l)
    elif r["bands"]:
        held = (max if "D6" in revert else min)(b["lev"] for b in r["bands"])
        lev_used = min(L, held)
        if L > held:
            out["lev_held"] = held
    margin0 = _div(qty0 * entry, lev_used)
    cut = "F1" not in revert and margin0 > eq + 1e-9
    qty = _div(eq * lev_used, entry) if cut else qty0
    notional = qty * entry
    margin = _div(notional, lev_used)
    fees = qty * fpu
    # the loss at the stop, each side's fee on its own price, as an exchange charges it
    true_loss = qty * dist + qty * entry * f + qty * stop * f
    denom = true_loss if "F6" not in revert else risk
    if "F7" in revert:
        left = math.floor(eff / risk + 1e-9) if risk > 0 else None
    else:
        left = math.ceil(eff / denom - 1e-9) - 1 if denom > 0 else None
    target = entry + side * num(x["targetR"]) * dist
    mB = _div(1, lev_used) if x["mode"] == "isolated" else _div(eq, notional)
    liq = (mB - MMR) / (1 - side * MMR) * 100 if math.isfinite(mB) else mB
    out.update(v="REDUCE" if risk < intended - 1e-9 or cut else "OK", dist=dist, fpu=fpu, qty=qty, notional=notional,
               lev_used=lev_used, margin=margin, fee_known=fee_known,
               fees=fees if fee_known else None,
               fshare=_div(fees, denom) * 100 if fee_known else None,
               used=denom / eff * 100, left=left, target=target, liq=liq,
               liq_none="F5" not in revert and side > 0 and liq >= 100 - 1e-9,
               ddist=None if dB is None else _div(dB, notional) * 100, fdist=None if ddB is None else _div(ddB, notional) * 100,
               trailing=r["dd"] == "trailing", cap_l=cap_l, true_loss=true_loss)
    if "F1" not in revert:
        out.update(margin0=margin0, cut=cut, lev_max=eq * lev_used)
    if "F6" not in revert:
        out["loss"] = true_loss
    return out
