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
    r("F2", "entry typed, no stop yet, risk -1%: blocked all the same", "bitfunded", "1step",
      {"v": "BLOCK", "range": ["risk_pct"]}, stop="", riskPct=-1)
    r("F2", "risk 0%, cap 0% and leverage 0 together, each named", "bitfunded", "1step",
      {"v": "BLOCK", "range": ["risk_pct", "cap_pct", "leverage"]}, riskPct=0, capPct=0, lev=0)
    # the edges one at a time: risk 100% with cap 100% is a loss that takes the whole room, which SPEC.md's R5 refuses
    # for its own reason, so each edge is shown in range on a trade that can still be sized
    r("F2", "the edges are in range: risk 100%, leverage 1", "bitfunded", "1step", {"v": "REDUCE", "range": None, "lev_used": 1},
      riskPct=100, lev=1)
    r("F2", "the edges are in range: cap 100%", "bitfunded", "1step", {"v": "OK", "range": None}, capPct=100)
    # F3: the handoff's case. At a 100% cap the loss takes the whole room, which SPEC.md's R5 refuses (BLOCK) where the
    # handoff sized it (REDUCE); the floor and the room are F3's, the same under both
    r("F3", "CFT Instant $10k at $9,500: the room is at most $100", "crypto_fund_trader", "instant",
      {"ddF": 9400, "eff": 100, "risk": 100, "v": "BLOCK", "blocks": ["reaches"], "link": True},
      quota=10000, equity=9500, daystart=9500, riskPct=2, capPct=100)
    r("F3", "CFT Instant $10k at $9,500, a 50% cap: sized against the loosest floor", "crypto_fund_trader", "instant",
      {"v": "REDUCE", "ddF": 9400, "eff": 100, "risk": 50}, quota=10000, equity=9500, daystart=9500, riskPct=2, capPct=50)
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
    # the whole room: F7 leaves none, and SPEC.md's R5 then refuses the trade
    r("F7", "risk the whole room", "bitfunded", "1step", {"risk": 4000, "left": 0, "v": "BLOCK", "blocks": ["reaches"]},
      capPct=100, riskPct=5)
    # D6
    r("D6", "CFT $30k at 200x: held to 5x", "crypto_fund_trader", "1phase", {"lev_used": 5, "lev_held": 5}, quota=30000,
      equity=30000, daystart=30000, lev=200)
    r("D6", "CFT $40k at 10x: held to 5x", "crypto_fund_trader", "2phase", {"lev_used": 5, "lev_held": 5}, quota=40000,
      equity=40000, daystart=40000, lev=10)
    r("D6", "CFT $30k at 3x: below the lowest cap, not held", "crypto_fund_trader", "1phase", {"lev_used": 3}, quota=30000,
      equity=30000, daystart=30000, lev=3)
    # the binding limit (SPEC.md: daily when dB <= ddB): a tie, each side of it, and the notes that name it. On
    # Bitfunded's 1-Step, $100k, the floors are day start - $4,000 and $94,000 (exact in floating point, both sides)
    r("bind", "a tie: day start $98,000, both budgets $5,000, the daily limit binds", "bitfunded", "1step",
      {"dB": 5000, "ddB": 5000, "eff": 5000}, equity=99000, daystart=98000)
    r("bind", "day start $97,000: the daily budget $6,000 is wider, the max drawdown binds", "bitfunded", "1step",
      {"dB": 6000, "ddB": 5000, "eff": 5000}, equity=99000, daystart=97000)
    r("bind", "day start $99,000: the daily budget $4,000 is narrower, the daily limit binds", "bitfunded", "1step",
      {"dB": 4000, "ddB": 5000, "eff": 4000}, equity=99000, daystart=99000)
    r("bind", "a tie, blocked: the reasons and the binding limit named", "bitfunded", "1step",
      {"v": "BLOCK", "dB": 5000, "ddB": 5000}, equity=99000, daystart=98000, stop=60600)
    # the isolated note (F5): a 1x long has no liquidation above zero, so it gets n_isolated_none and not n_isolated;
    # a 3x short has one, and gets n_isolated
    r("F5", "isolated long at 1x, cross-checked against the notes", "bitfunded", "1step", {"liq_none": True},
      mode="isolated", lev=1, stop=59700)
    r("F5", "isolated short at 3x: liquidation shown, n_isolated", "bitfunded", "1step", {"liq_none": False},
      mode="isolated", lev=3, side=-1, stop=60300)
    # SPEC.md's changes after the review (2026-09-30)
    # R1/R2: equity and day start bounded; an account out of range computes nothing and gives no link (R4)
    r("R1", "equity 0", "bitfunded", "1step", {"v": "BLOCK", "range": ["equity"], "dF": None, "link": False}, equity=0)
    r("R1", "day start blank: refused, not a daily floor of -$4,000", "bitfunded", "1step",
      {"v": "BLOCK", "range": ["daystart"], "dF": None, "account_range": True}, daystart="")
    r("R1", "every account field and the risk out of range, in SPEC.md's order", "bitfunded", "1step",
      {"v": "BLOCK", "range": ["quota", "equity", "daystart", "risk_pct"], "blocks": None}, quota=0, equity=-1,
      daystart=0, riskPct=0, stop=60600)
    r("R1", "equity 0 on a breached-looking account: the range, never b_breached", "bitfunded", "1step",
      {"v": "BLOCK", "range": ["equity"], "blocks": None}, equity=0, daystart=90000)
    r("R1", "a high-water mark of 0 is still none", "brightfunded", "1step", {"v": "OK", "range": None, "hwm": 100000}, hwm=0)
    # R4: a range BLOCK has no link row; a trade's own BLOCK keeps it
    r("R4", "risk out of range: no link row", "bitfunded", "1step", {"v": "BLOCK", "link": False, "account_range": False},
      riskPct=101)
    r("R4", "stop on the wrong side: the link row kept", "bitfunded", "1step", {"v": "BLOCK", "blocks": ["long"], "link": True},
      stop=60600)
    # R5: a 100% cap with the intended risk under the room is sized; at or over it, refused
    r("R5", "a 100% cap, intended $500 under the $4,000 room: sized", "bitfunded", "1step", {"v": "OK", "left": 7}, capPct=100)
    r("R5", "a 100% cap, intended $5,000 over the $4,000 room: refused", "bitfunded", "1step",
      {"v": "BLOCK", "blocks": ["reaches"], "risk": 4000, "eff": 4000}, capPct=100, riskPct=5)
    # R6: a long whose budgets exceed the notional: $100 at risk on a 50% stop is a $200 position
    r("R6", "a long, a 50% stop: neither floor reached above zero", "bitfunded", "1step",
      {"v": "OK", "ddist_none": True, "fdist_none": True}, stop=30000, riskPct=0.1, capPct=2.5)
    r("R6", "the short twin: shown as computed", "bitfunded", "1step",
      {"ddist_none": False, "fdist_none": False}, side=-1, stop=90000, riskPct=0.1, capPct=2.5)
    # R7: a pending drawdown type (CFT Instant) has no crossover; a recorded one (Bitfunded) does
    r("R7", "CFT Instant: drawdown type pending", "crypto_fund_trader", "instant", {"dd_pending": True, "dd_loosest": True},
      quota=10000, equity=10000, daystart=10000)
    r("R7", "Bitfunded 1-Step: drawdown type recorded", "bitfunded", "1step", {"dd_pending": False})
    # R8: the handoff's 10-point stop at 2%, a 35% cap: the cap cuts $2,000 to $1,400 (35% of the $4,000 room), then the margin cuts the size
    r("R8", "cut by the cap, then the margin: n_cut_margin", "bitfunded", "1step",
      {"v": "REDUCE", "cut": True, "cut_note": "n_cut_margin", "intended": 2000, "risk": 1400, "qty": 8.3333333,
       "loss": 483.30}, stop=59990, riskPct=2)
    r("R8", "cut by the margin alone: no cap note", "bitfunded", "1step", {"v": "REDUCE", "cut": True, "cut_note": None},
      stop=59990)
    r("R8", "cut by the cap alone: n_cut", "bitfunded", "1step", {"v": "REDUCE", "cut": False, "cut_note": "n_cut"},
      riskPct=2)
    return R


def states(FJ=None):
    """The desk's two states with no verdict (review finding 15): no entry yet (EMPTY, the account only) and an entry
    with no stop (SET, "Set your stop"), and a breached account with no entry, which is EMPTY, not BLOCK. They join the
    run once the model derives those states; until then the model gives them a verdict the desk rightly doesn't, and
    the audit would report a correct desk. The model's change is the owner's review (README, "Changing the model"), so
    these wait for it rather than a rule written here."""
    S = [_case("state-1", "regression", "states: entry typed, no stop, valid inputs: SET", "bitfunded", "1step",
               {"v": "SET"}, stop=""),
         _case("state-2", "regression", "states: no entry, no stop, valid inputs: EMPTY", "bitfunded", "1step",
               {"v": "EMPTY"}, entry="", stop=""),
         _case("state-3", "regression", "states: a breached account, no entry: EMPTY, not BLOCK", "bitfunded", "1step",
               {"v": "EMPTY"}, entry="", stop="", equity=94000)]
    return S if all(M.model(c["firm"], c["product"], c["x"], FJ).get("v") == c["pin"]["v"] for c in S) else []


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
    return edges() + regressions() + states(FJ) + grid(FJ) + rand(week, n, FJ)


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
    ns = len(states())
    print(f"{len(cs)} cases for {wk}: {len(edges())} edge, {len(regressions()) + ns} regression, {len(grid())} grid, "
          f"{len(cs) - len(edges()) - len(regressions()) - ns - len(grid())} random; "
          f"{sum(len(c['pin']) for c in cs)} pinned figures, {len(bad)} off"
          + ("" if ns else "; the EMPTY and SET regressions wait for the model to derive those states"))
    sys.exit(1 if bad else 0)
