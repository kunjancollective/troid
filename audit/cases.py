#!/usr/bin/env python3
"""The calculator audit's cases (HANDOFF-calculator-audit, 29 Sep 2026): the seed's 23 edge cases, a named regression
for each item the handoff fixed, the desk's own grid on every product it offers, and 1,000 random cases seeded by the
ISO week, so each week's sample differs and any week can be run again exactly.

A case is a dict: id, group (edge | regression | grid | random), name, firm, product, x (the desk's inputs, as
audit/model.py reads them) and, for the edge cases and the regressions, pin: the figures the handoff states, worked by
hand. audit/run.py checks the model against every pin before it drives a page, so a model that drifts from the
handoff stops the run instead of passing a desk that drifted with it.

  python3 audit/cases.py            # the model against every pin, and the week's case count
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import model as M  # noqa: E402

BASE = dict(quota=100000, equity=100000, daystart=100000, side=1, entry=60000, stop=59400, targetR=2, riskPct=0.5,
            capPct=35, lev=5, mode="cross")


def _case(cid, group, name, firm, prod, pin=None, **k):
    x = dict(BASE); x.update(k)
    return {"id": cid, "group": group, "name": name, "firm": firm, "product": prod, "x": x, "pin": pin or {}}


def edges():
    """The seed's 23 edge cases, in its order, each pinned to what the handoff says the desk must show."""
    E = []

    def e(name, f, p, pin, **k):
        E.append(_case(f"edge-{len(E) + 1:02d}", "edge", name, f, p, pin, **k))
    e("zero distance and a long's stop at entry", "bitfunded", "1step", {"v": "BLOCK"}, stop=60000)
    e("long, stop above entry", "bitfunded", "1step", {"v": "BLOCK"}, stop=60600)
    e("short, stop below entry", "bitfunded", "1step", {"v": "BLOCK"}, side=-1, stop=59400)
    e("short, sized", "bitfunded", "1step", {"v": "OK", "risk": 500}, side=-1, stop=60600)
    e("equity at the max-loss floor: breached", "bitfunded", "1step", {"v": "BLOCK", "ddB": 0}, equity=94000)
    e("a dollar under the daily floor: breached", "bitfunded", "1step", {"v": "BLOCK", "dB": -1}, equity=95999, daystart=100000)
    e("BrightFunded locks exactly at +6%", "brightfunded", "1step", {"ddF": 100000, "locked": True}, hwm=106000, equity=105000)
    e("BrightFunded a dollar below the lock", "brightfunded", "1step", {"ddF": 99999, "locked": False}, hwm=105999, equity=105000)
    e("high-water mark typed below equity, a firm that trails on equity (F4)", "brightfunded", "1step",
      {"hwm": 103000, "ddF": 97000}, hwm=100000, equity=103000)
    e("high-water mark typed below quota (F4)", "brightfunded", "1step", {"hwm": 100000, "ddF": 94000}, hwm=95000, equity=95500)
    e("CFT $25k: the Student band's 5x", "crypto_fund_trader", "1phase", {"lev_used": 5}, quota=25000, equity=25000,
      daystart=25000, lev=20)
    e("CFT $30k: no band recorded, held to the lowest cap, 5x (D6)", "crypto_fund_trader", "1phase", {"lev_used": 5},
      quota=30000, equity=30000, daystart=30000, lev=200)
    e("CFT $50k: the Advanced band's 100x", "crypto_fund_trader", "1phase", {"lev_used": 100}, quota=50000, equity=50000,
      daystart=50000, lev=150)
    e("CFT Instant: drawdown type pending, the loosest floor (F3), cap 5x", "crypto_fund_trader", "instant",
      {"ddF": 9400, "lev_used": 5}, quota=10000, equity=10000, daystart=10000, lev=20)
    e("CFT 2-Phase, static", "crypto_fund_trader", "2phase", {"ddF": 90000, "lev_used": 10}, lev=10)
    e("isolated at 5x", "bitfunded", "1step", {"liq": 19.5979899, "liq_none": False}, mode="isolated", lev=5)
    e("isolated at 1x, a long: none above zero (F5)", "bitfunded", "1step", {"liq_none": True}, mode="isolated", lev=1)
    e("wide stop, cross, a long: none above zero (F5)", "bitfunded", "1step", {"liq_none": True}, entry=60000, stop=54000)
    e("budget cap 150% (F2)", "bitfunded", "1step", {"v": "BLOCK", "range": ["cap_pct"]}, capPct=150)
    e("risk an exact quarter of the room (F7)", "bitfunded", "1step", {"risk": 1000, "left": 3}, capPct=25, riskPct=5)
    e("risk -1% (F2)", "bitfunded", "1step", {"v": "BLOCK", "range": ["risk_pct"]}, riskPct=-1)
    e("leverage 0 (F2)", "bitfunded", "1step", {"v": "BLOCK", "range": ["leverage"]}, lev=0)
    e("short, tight stop: the fee at the stop (F6)", "bitfunded", "1step", {"loss": 500.0, "risk": 500}, side=-1,
      entry=60000, stop=60120)
    return E


def regressions():
    """One named case for each fix, worked from the handoff's own numbers."""
    R = []

    def r(item, name, f, p, pin, **k):
        R.append(_case(f"reg-{item}-{sum(1 for c in R if c['id'].startswith(f'reg-{item}-')) + 1}", "regression",
                       f"{item}: {name}", f, p, pin, **k))
    # F1: the handoff's case, a 10-point stop at 5x on $100k, and its short twin
    r("F1", "margin above equity is cut to equity x 5x / entry (long)", "bitfunded", "1step",
      {"v": "REDUCE", "cut": True, "qty": 8.3333333, "margin": 100000, "notional": 500000, "margin0": 103455.41, "loss": 483.30},
      stop=59990)
    r("F1", "margin above equity is cut (short)", "bitfunded", "1step",
      {"v": "REDUCE", "cut": True, "margin": 100000, "notional": 500000}, side=-1, stop=60010)
    r("F1", "margin inside equity is not cut", "bitfunded", "1step", {"v": "OK", "cut": False, "margin0": 9262.69}, stop=59400)
    # F2: each field out of range, the edges of each range, and an empty entry
    r("F2", "quota 0", "bitfunded", "1step", {"v": "BLOCK", "range": ["quota"]}, quota=0)
    r("F2", "risk 0%", "bitfunded", "1step", {"v": "BLOCK", "range": ["risk_pct"]}, riskPct=0)
    r("F2", "risk 100.5%", "bitfunded", "1step", {"v": "BLOCK", "range": ["risk_pct"]}, riskPct=100.5)
    r("F2", "budget cap 0%", "bitfunded", "1step", {"v": "BLOCK", "range": ["cap_pct"]}, capPct=0)
    r("F2", "leverage 0.5", "bitfunded", "1step", {"v": "BLOCK", "range": ["leverage"]}, lev=0.5)
    r("F2", "entry below 0", "bitfunded", "1step", {"v": "BLOCK", "range": ["entry"]}, entry=-60000)
    r("F2", "stop 0", "bitfunded", "1step", {"v": "BLOCK", "range": ["stop"]}, stop=0)
    r("F2", "no entry yet, risk -1%: blocked all the same", "bitfunded", "1step", {"v": "BLOCK", "range": ["risk_pct"]},
      entry="", stop="", riskPct=-1)
    r("F2", "risk 0%, cap 0% and leverage 0 together, each named", "bitfunded", "1step",
      {"v": "BLOCK", "range": ["risk_pct", "cap_pct", "leverage"]}, riskPct=0, capPct=0, lev=0)
    r("F2", "the edges are in range: risk 100%, cap 100%, leverage 1", "bitfunded", "1step", {"v": "REDUCE", "lev_used": 1},
      riskPct=100, capPct=100, lev=1)
    # F3: the handoff's case
    r("F3", "CFT Instant $10k at $9,500: the room is at most $100", "crypto_fund_trader", "instant",
      {"v": "REDUCE", "ddF": 9400, "eff": 100, "risk": 100}, quota=10000, equity=9500, daystart=9500, riskPct=2, capPct=100)
    # F4
    r("F4", "BrightFunded: high-water mark $100,000 typed, equity $103,000", "brightfunded", "1step",
      {"hwm": 103000, "ddF": 97000, "hwm_raised": "equity"}, hwm=100000, equity=103000, daystart=103000)
    r("F4", "BrightFunded: high-water mark $95,000, below quota and equity (raised to the quota)", "brightfunded", "1step",
      {"hwm": 100000, "ddF": 94000, "hwm_raised": "quota"}, hwm=95000, equity=95500, daystart=95500)
    r("F4", "BrightFunded: high-water mark $95,000, below quota only", "brightfunded", "1step",
      {"hwm": 100000, "ddF": 94000, "hwm_raised": "quota"}, hwm=95000, equity=94500, daystart=94500)
    r("F4", "CFT 1-Phase trails on balance: a mark below equity stays", "crypto_fund_trader", "1phase",
      {"hwm": 100000, "ddF": 94000}, hwm=100000, equity=103000, daystart=103000)
    r("F4", "BrightFunded: high at rollover $99,000, below the $100,000 day start", "brightfunded", "1step",
      {"hi": 100000, "dF": 97000, "hi_raised": True}, hirollover=99000)
    # F5
    r("F5", "cross long, 1% stop: none above zero", "bitfunded", "1step", {"liq_none": True})
    r("F5", "cross long, 10% stop: none above zero", "bitfunded", "1step", {"liq_none": True}, stop=54000)
    r("F5", "isolated long at 1x: none above zero", "bitfunded", "1step", {"liq_none": True}, mode="isolated", lev=1)
    r("F5", "cross short, 1% stop: shown as computed", "bitfunded", "1step", {"liq_none": False, "liq": 214.5075},
      side=-1, stop=60600)
    # F6: the loss at the stop equals the risk to the cent
    r("F6", "long, 1% stop", "bitfunded", "1step", {"loss": 500.0, "fpu": 47.76}, stop=59400)
    r("F6", "short, 1% stop", "bitfunded", "1step", {"loss": 500.0, "fpu": 48.24}, side=-1, stop=60600)
    r("F6", "long, 0.2% stop", "bitfunded", "1step", {"loss": 500.0, "fpu": 47.952}, stop=59880)
    r("F6", "short, 0.2% stop", "bitfunded", "1step", {"loss": 500.0, "fpu": 48.048}, side=-1, stop=60120)
    # F7
    r("F7", "risk an exact quarter of the room: 3 losses left", "bitfunded", "1step", {"left": 3}, capPct=25, riskPct=5)
    r("F7", "risk 30% of the room: 3 losses left", "bitfunded", "1step", {"left": 3}, capPct=30, riskPct=5)
    r("F7", "risk the whole room: none left", "bitfunded", "1step", {"left": 0}, capPct=100, riskPct=5)
    # D6
    r("D6", "CFT $30k at 200x: held to 5x", "crypto_fund_trader", "1phase", {"lev_used": 5, "lev_held": 5}, quota=30000,
      equity=30000, daystart=30000, lev=200)
    r("D6", "CFT $40k at 10x: held to 5x", "crypto_fund_trader", "2phase", {"lev_used": 5, "lev_held": 5}, quota=40000,
      equity=40000, daystart=40000, lev=10)
    r("D6", "CFT $30k at 3x: below the lowest cap, not held", "crypto_fund_trader", "1phase", {"lev_used": 3}, quota=30000,
      equity=30000, daystart=30000, lev=3)
    return R


# the desk's own grid (backtest/i18n_equiv.DESK_GRID's six rows), on every product the desk offers
GRID = [(100000, 100000, 100000, 1, 77872, 74814, 5, "cross"), (100000, 96000, 96000, -1, 77872, 78105.616, 5, "cross"),
        (100000, 106000, 106000, 1, 77872, 74814, 150, "isolated"), (30000, 30000, 30000, 1, 77872, 74814, 150, "cross"),
        (10000, 10000, 10000, 1, 100, 101, 5, "cross"), (100000, 93000, 94000, 1, 77872, 77600, 20, "isolated")]


def grid(FJ=None):
    out = []
    for i, (q, eq, ds, side, entry, stop, lev, mode) in enumerate(GRID, 1):
        for f, p in M.offered(FJ):
            out.append(_case(f"grid-{i}-{f}-{p}", "grid", f"grid row {i}", f, p, quota=q, equity=eq, daystart=ds, side=side,
                             entry=entry, stop=stop, lev=lev, mode=mode, targetR=2, riskPct=0.5, capPct=35))
    return out


PRICES = [0.08, 0.61, 1.0, 2.35, 24.5, 142.0, 590.0, 2400.0, 3600.0, 61000.0, 118000.0]


def rand(week, n=1000, FJ=None):
    """The seed's random cases, drawn from a generator seeded by the ISO week ("2026-W40")."""
    rng = random.Random(week)
    combos = M.offered(FJ)
    out = []
    for i in range(n):
        f, p = rng.choice(combos)
        q = rng.choice([2500, 5000, 10000, 25000, 30000, 50000, 100000, 200000])
        eq = round(q * rng.uniform(0.9, 1.12), 2)
        ds = round(eq * rng.uniform(0.98, 1.03), 2)
        entry = rng.choice(PRICES) * rng.uniform(0.9, 1.1)
        side = rng.choice([1, -1])
        sp = rng.choice([0.001, 0.003, 0.01, 0.02, 0.05, 0.12])
        stop = entry * (1 - side * sp)
        x = dict(quota=q, equity=eq, daystart=ds, side=side, entry=round(entry, 6), stop=round(stop, 6),
                 targetR=rng.choice([1, 1.5, 2, 3]), riskPct=rng.choice([0.25, 0.5, 1, 2]),
                 capPct=rng.choice([20, 35, 50, 100]), lev=rng.choice([1, 2, 3, 5, 10, 20, 50]),
                 mode=rng.choice(["cross", "isolated"]))
        if rng.random() < 0.4:
            x["hwm"] = round(max(eq, q) * rng.uniform(1.0, 1.09), 2)
        if rng.random() < 0.3:
            x["hirollover"] = round(ds * rng.uniform(1.0, 1.02), 2)
        out.append({"id": f"rand-{i + 1:04d}", "group": "random", "name": f"{week} #{i + 1}", "firm": f, "product": p,
                    "x": x, "pin": {}})
    return out


def all_cases(week, n=1000, FJ=None):
    return edges() + regressions() + grid(FJ) + rand(week, n, FJ)


MONEY = {"loss", "margin0", "margin", "notional", "dF", "ddF", "dB", "ddB", "eff", "risk", "intended", "cap", "hwm", "hi"}


def pin_check(cases, FJ=None):
    """Every pinned figure, from the model. A pin is the handoff's number worked by hand, right to the digits it is
    written with (103455.41 to half a cent, 214.5075 to half of its last place, never finer than 1e-6); a flag, a
    verdict or a list of fields as it is."""
    bad = []
    for c in cases:
        if not c["pin"]:
            continue
        got = M.model(c["firm"], c["product"], c["x"], FJ)
        for k, want in c["pin"].items():
            g = got.get(k)
            if isinstance(want, (bool, str, list)) or want is None:
                ok = g == want
            else:
                places = len(repr(float(want)).split(".")[1]) if "e" not in repr(float(want)) else 0
                tol = max(1e-6, 0.5 * 10 ** -places + 1e-9)
                if k in MONEY:
                    tol = min(tol, 0.0051)                  # a dollar figure to the cent, however it is written
                ok = isinstance(g, (int, float)) and abs(g - want) <= tol
            if not ok:
                bad.append((c["id"], c["name"], k, want, g))
    return bad


if __name__ == "__main__":
    import datetime as dt
    wk = sys.argv[1] if len(sys.argv) > 1 else "%d-W%02d" % dt.datetime.now(dt.timezone.utc).isocalendar()[:2]
    cs = all_cases(wk)
    bad = pin_check(cs)
    for b in bad:
        print("PIN  ", *b)
    print(f"{len(cs)} cases for {wk}: {len(edges())} edge, {len(regressions())} regression, {len(grid())} grid, "
          f"{len(cs) - len(edges()) - len(regressions()) - len(grid())} random; "
          f"{sum(len(c['pin']) for c in cs)} pinned figures, {len(bad)} off")
    sys.exit(1 if bad else 0)
