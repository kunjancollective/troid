#!/usr/bin/env python3
"""The cross-section (HANDOFF.md "Asset coverage"; SHADOW2.md "The cross-section" and "What counts as surviving"):
troid-shadow-1 and troid-shadow-2 on every asset that qualifies, side by side.

  python cross_section.py > CROSSSECTION.md          every data/<ASSET>USDT_4h.csv or <ASSET>USD_4h.csv

- The universe and its order are SHADOW2.md's. An asset qualifies when its file is api.binance.us's, starts before
  2023-01-01, forward-fills at most 1% of its bars and no gap longer than a day (a delisting would otherwise read as a
  flat market). Every asset that qualifies is reported; one that doesn't is listed with the reason. PAXG is apart.
- shadow-1 runs from its own config unchanged but for the hold limit of the asset's class, with two ablations the
  handoff asks the cross-section to settle: without the regime filter (and so without the breakout), and a single
  entry instead of the strength ladder.
- shadow-2 runs from its config, as fixed before any run.
- The window both are compared on is shadow-2's holdout, 2025-01-01 to 2026-09-21 (for shadow-1 on BTC, 2026 is its
  fit sample, and the table says so). Pooled across assets, the standard error is clustered by entry day, as fixed;
  by entry week beside it, for information only.
- H1 and H2 are judged exactly as SHADOW2.md fixed them. A bucket under 30 trades is insufficient, not a number.

Also writes results/cross_section.json.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import engine as E  # noqa: E402
import engine_s2 as S2  # noqa: E402
import engine_v2 as V  # noqa: E402
import site_text  # noqa: E402

MIN_N = 30
START_BY = dt.date(2023, 1, 1)
MAX_FILLED_SHARE = 0.01
MAX_GAP_BARS = 6                        # a day
S1_KEYS_V = ("REGIME", "BREAKOUT", "LADDER", "COMPRESS_K", "MIN_COMP", "LADDER_DIR", "LADDER_N", "BREAKEVEN_AFTER_TP1", "TPS",
             "REVERSE_AFTER_TP3", "REVERSE_TRIGGER", "HOLDING", "MAX_HOLD_BARS", "MIN_TRADING_DAYS")
S1_KEYS_E = ("INITIAL", "RISK_PCT", "BUDGET_CAP", "FEE", "MAX_LEV", "TARGET_R", "T0")


def universe(cfg):
    base = cfg["majors"] + ["LTC", "LINK", "BCH", "DOT", "AVAX", "XLM", "ATOM", "UNI", "ETC", "ALGO"]
    return base, "PAXG"


def find(asset):
    for q in ("USDT", "USD"):
        p = HERE / "data" / f"{asset}{q}_4h.csv"
        if p.exists():
            return p
    return None


def qualify(path, bars, t0):
    import csv
    head = next((r[0] for r in csv.reader(open(path)) if r and r[0].startswith("#")), "")
    if "api.binance.us" not in head:
        return f"not api.binance.us's ({head[:60]})"
    first = dt.datetime.fromtimestamp(t0, dt.timezone.utc).date()
    if first >= START_BY:
        return f"history starts {first}, after {START_BY}"
    flat = [b[0] == b[1] == b[2] == b[3] for b in bars]
    share = sum(flat) / len(bars)
    run = longest = 0
    for f in flat:
        run = run + 1 if f else 0
        longest = max(longest, run)
    if share > MAX_FILLED_SHARE:
        return f"{100 * share:.1f}% of bars forward-filled (at most {100 * MAX_FILLED_SHARE:g}%)"
    if longest > MAX_GAP_BARS:
        return f"a forward-filled gap of {longest} bars (at most {MAX_GAP_BARS}, a day)"
    return None


# ---------------------------------------------------------------------- statistics
def stats(rs):
    n = len(rs)
    if n < 2:
        return dict(n=n)
    m, sd = statistics.fmean(rs), statistics.stdev(rs)
    se = sd / math.sqrt(n)
    return dict(n=n, exp=m, se=se, lo=m - 1.96 * se, hi=m + 1.96 * se)


def clustered(trades, key):
    """The pooled mean R and its standard error clustered by key(trade) (entry day, or week)."""
    n = len(trades)
    if n < 2:
        return dict(n=n)
    m = statistics.fmean(t["r"] for t in trades)
    groups = {}
    for t in trades:
        groups.setdefault(key(t), []).append(t["r"] - m)
    C = len(groups)
    var = math.fsum(math.fsum(g) ** 2 for g in groups.values()) / n ** 2 * (C / (C - 1) if C > 1 else 1)
    se = math.sqrt(var)
    return dict(n=n, clusters=C, exp=m, se=se, lo=m - 1.96 * se, hi=m + 1.96 * se)


def clustered_diff(a, b, key):
    """mean(a) - mean(b) with a cluster-robust standard error (each trade's influence summed by cluster)."""
    if len(a) < MIN_N or len(b) < MIN_N:
        return None
    ma, mb = statistics.fmean(t["r"] for t in a), statistics.fmean(t["r"] for t in b)
    u = {}
    for t in a:
        u[key(t)] = u.get(key(t), 0.0) + (t["r"] - ma) / len(a)
    for t in b:
        u[key(t)] = u.get(key(t), 0.0) - (t["r"] - mb) / len(b)
    C = len(u)
    se = math.sqrt(math.fsum(x * x for x in u.values()) * (C / (C - 1) if C > 1 else 1))
    d = ma - mb
    return dict(d=d, se=se, lo=d - 1.96 * se, hi=d + 1.96 * se, clusters=C)


def fmt(st):
    if st is None or st.get("n", 0) < MIN_N:
        return f"{(st or {}).get('n', 0)} · insufficient"
    return f"{st['n']} · {st['exp']:+.3f} [{st['lo']:+.3f}, {st['hi']:+.3f}]"


# ---------------------------------------------------------------------- the two strategies on one asset
def shadow1(bars, t0, asset, cfg2, variant="as configured"):
    import forward
    keep_v, keep_e = {k: getattr(V, k) for k in S1_KEYS_V}, {k: getattr(E, k) for k in S1_KEYS_E}
    try:
        forward.apply_config()
        V.MAX_HOLD_BARS = cfg2["hold_bars"][S2.asset_class(asset, cfg2)]      # its _hold_note: set per asset
        if variant == "no regime filter":
            V.REGIME, V.BREAKOUT = False, False
        elif variant == "single entry":
            V.LADDER_DIR, V.LADDER_N = "none", 1     # one entry for the pullback, the breakout and the reverse alike
        E.T0 = t0
        e20, e120, atr = E.indicators(bars)
        sigs = V.build_signals(bars, e20, e120, atr)
        warm = max(E.EMA_TREND + E.TREND_SLOPE_BARS, V.RANGE_BARS) + 1
        r = V.run(bars, sigs, warm, challenge=False, risk_pct=forward.CFG["risk_pct"], atr=atr)
    finally:
        for k, x in keep_v.items():
            setattr(V, k, x)
        for k, x in keep_e.items():
            setattr(E, k, x)
    return [t for t in r.trades if t["reason"] != "eod"]


def shadow2(bars, t0, asset, cfg):
    first = S2.first_decision(bars, t0, cfg)
    if first is None:
        return []
    r = S2.run(bars, t0, S2.signals(bars, t0, cfg), cfg, asset=asset, challenge=False, start=first + 1)
    return [t for t in r.trades if t["reason"] != "eod"]


def main():
    cfg = S2.load_config()
    hold_from, frozen = dt.date.fromisoformat(cfg["holdout_from"]), dt.date.fromisoformat(cfg["frozen_end"])
    names, proxy = universe(cfg)
    rows, skipped, pooled = [], [], {k: [] for k in ("s2", "s1", "s1_noregime", "s1_single")}
    proxy_row = None
    for asset in names + [proxy]:
        path = find(asset)
        if not path:
            skipped.append((asset, "no file: api.binance.us has no 4h history for it, or it hasn't been fetched"))
            continue
        bars, t0 = S2.load(path)
        why = qualify(path, bars, t0)
        if why:
            skipped.append((asset, why))
            continue
        day = lambda i, t0=t0: dt.datetime.fromtimestamp(t0 + i * E.STEP, dt.timezone.utc).date()    # noqa: E731

        def window(tr, day=day, asset=asset):
            out = []
            for t in tr:
                d = day(t["bar"])
                if hold_from <= d <= frozen:
                    out.append(dict(t, asset=asset, exit_day=d, entry_day=day(t["entry_bar"])))
            return out
        s2 = window(shadow2(bars, t0, asset, cfg))
        s1 = {v: window(shadow1(bars, t0, asset, cfg, v)) for v in ("as configured", "no regime filter", "single entry")}
        row = dict(asset=asset, pair=path.stem.replace("_4h", ""), cls=S2.asset_class(asset, cfg),
                   hold=cfg["hold_bars"][S2.asset_class(asset, cfg)],
                   first=str(dt.datetime.fromtimestamp(t0, dt.timezone.utc).date()),
                   s2=stats([t["r"] for t in s2]), s1=stats([t["r"] for t in s1["as configured"]]),
                   s1_noregime=stats([t["r"] for t in s1["no regime filter"]]), s1_single=stats([t["r"] for t in s1["single entry"]]),
                   calm=stats([t["r"] for t in s2 if t.get("vov_state") == "calm"]),
                   unsettled=stats([t["r"] for t in s2 if t.get("vov_state") == "unsettled"]),
                   compressed=stats([t["r"] for t in s2 if t.get("bb_state") == "compressed"]),
                   expanded=stats([t["r"] for t in s2 if t.get("bb_state") == "expanded"]))
        if asset == proxy:
            proxy_row = row
            continue
        rows.append(row)
        pooled["s2"] += s2
        pooled["s1"] += s1["as configured"]; pooled["s1_noregime"] += s1["no regime filter"]; pooled["s1_single"] += s1["single entry"]

    by_day = lambda t: t["entry_day"]                                                  # noqa: E731
    by_week = lambda t: tuple(t["entry_day"].isocalendar())[:2]                        # noqa: E731
    P = {k: dict(day=clustered(v, by_day), week=clustered(v, by_week)) for k, v in pooled.items()}
    calm = [t for t in pooled["s2"] if t.get("vov_state") == "calm"]
    uns = [t for t in pooled["s2"] if t.get("vov_state") == "unsettled"]
    comp = [t for t in pooled["s2"] if t.get("bb_state") == "compressed"]
    expd = [t for t in pooled["s2"] if t.get("bb_state") == "expanded"]
    h2 = clustered_diff(calm, uns, by_day)
    bb = clustered_diff(comp, expd, by_day)

    enough = [r for r in rows if r["s2"].get("n", 0) >= MIN_N]
    pos = [r for r in enough if r["s2"]["exp"] > 0]
    both = [r for r in rows if r["calm"].get("n", 0) >= MIN_N and r["unsettled"].get("n", 0) >= MIN_N]
    same = [r for r in both if (r["calm"]["exp"] - r["unsettled"]["exp"]) > 0]
    pd = P["s2"]["day"]
    decided = len(rows) >= 10
    h1_ok = (pd.get("n", 0) >= MIN_N and pd["exp"] > 0 and pd["lo"] > 0 and enough and len(pos) >= 2 / 3 * len(enough))
    h2_ok = (h2 is not None and h2["d"] > 0 and h2["lo"] > 0 and both and len(same) >= 2 / 3 * len(both))

    print("# The cross-section — troid-shadow-1 and troid-shadow-2\n")
    print("**Generated by `cross_section.py`. Do not hand-edit — regenerate.**\n")
    print(site_text.hypo_md(no_edge=site_text.NO_EDGE_SHORT + " Every row below is MEASURED; none is stated as fact."))
    print(f"The window: {hold_from} -> {frozen}, shadow-2's holdout (SHADOW2.md), trades bucketed by exit day, one continuous run "
          f"per asset with challenge accounting off. Each cell: n · mean R [95% CI]. A bucket under {MIN_N} trades is "
          f"insufficient, not a number. For shadow-1 on BTC, 2026 is its fit sample; every other asset and year is new to it.\n")
    print(f"**{len(rows)} assets qualify** (SHADOW2.md: at least 10 are needed to decide H1 and H2)"
          + ("." if decided else f": **fewer than 10, so neither is decided**; the rows are the machinery's dry run.") + "\n")
    print("| asset | class, hold | from | shadow-2 | shadow-1 | shadow-1, no regime filter | shadow-1, single entry |")
    print("|---|---|---|---|---|---|---|")
    for r in rows:
        print(f"| {r['pair']} | {r['cls']}, {r['hold']} bars | {r['first']} | {fmt(r['s2'])} | {fmt(r['s1'])} | "
              f"{fmt(r['s1_noregime'])} | {fmt(r['s1_single'])} |")
    print()
    print("**Pooled**, standard error clustered by entry day (the fixed method); by entry week beside it, for information.\n")
    print("| | n | days | mean R | 95% CI (by day) | 95% CI (by week) |")
    print("|---|---|---|---|---|---|")
    for k, lab in (("s2", "shadow-2"), ("s1", "shadow-1"), ("s1_noregime", "shadow-1, no regime filter"), ("s1_single", "shadow-1, single entry")):
        d, w = P[k]["day"], P[k]["week"]
        if d.get("n", 0) < MIN_N:
            print(f"| {lab} | {d.get('n', 0)} | | insufficient | | |")
        else:
            print(f"| {lab} | {d['n']} | {d['clusters']} | {d['exp']:+.3f} | [{d['lo']:+.3f}, {d['hi']:+.3f}] | [{w['lo']:+.3f}, {w['hi']:+.3f}] |")
    print()
    if enough:
        qs = sorted(r["s2"]["exp"] for r in enough)
        print(f"shadow-2's per-asset means (n ≥ {MIN_N}), lowest to highest: " + ", ".join(f"{x:+.3f}" for x in qs)
              + f". Positive on {len(pos)} of {len(enough)}.\n")
    print("**The states** (shadow-2, pooled over the window).\n")
    print("| split | difference in mean R | 95% CI (by day) | assets with 30+ in each state, same sign |")
    print("|---|---|---|---|")
    print(f"| vol-of-vol: calm minus unsettled (H2) | " + (f"{h2['d']:+.3f} | [{h2['lo']:+.3f}, {h2['hi']:+.3f}] | {len(same)} of {len(both)} |"
                                                         if h2 else "insufficient | | |"))
    bb_both = [r for r in rows if r["compressed"].get("n", 0) >= MIN_N and r["expanded"].get("n", 0) >= MIN_N]
    bb_same = [r for r in bb_both if r["compressed"]["exp"] - r["expanded"]["exp"] > 0]
    print(f"| Bollinger width: compressed minus expanded | " + (f"{bb['d']:+.3f} | [{bb['lo']:+.3f}, {bb['hi']:+.3f}] | {len(bb_same)} of {len(bb_both)} |"
                                                             if bb else "insufficient | | |"))
    print()
    if proxy_row:
        print(f"**Apart: {proxy_row['pair']}**, tokenised gold, a proxy only (troid's firms' XAU is another feed), TradFi's "
              f"{proxy_row['hold']}-bar hold: shadow-2 {fmt(proxy_row['s2'])}; shadow-1 {fmt(proxy_row['s1'])}.\n")
    if skipped:
        print("**Not in the cross-section:** " + "; ".join(f"{a}: {w}" for a, w in skipped) + ".\n")
    print("## Verdicts, as SHADOW2.md fixed them\n")
    if not decided:
        print(f"- Undecided: {len(rows)} assets qualify, and the design needs at least 10. TradFi stays open (no binance.us feed).")
    else:
        print(f"- **H1, shadow-2's expectancy: {'survived' if h1_ok else 'did not survive'}.** Pooled {pd['exp']:+.3f}R, 95% CI "
              f"[{pd['lo']:+.3f}, {pd['hi']:+.3f}] (by day); positive on {len(pos)} of {len(enough)} assets with {MIN_N}+ trades.")
        print(f"- **H2, the vol-of-vol state: {'survived' if h2_ok else 'did not survive'}.** " +
              (f"Calm minus unsettled {h2['d']:+.3f}R, 95% CI [{h2['lo']:+.3f}, {h2['hi']:+.3f}]; same sign on {len(same)} of {len(both)}."
               if h2 else "Insufficient trades in a state."))
        print("- shadow-1's regime filter and strength ladder, the components HANDOFF.md asks the cross-section about: the "
              "ablation columns above, read as a neighbourhood across assets, never as the best asset.")
    print("- Every figure here is MEASURED. If neither survives, that is the finding.")

    out = dict(window=[str(hold_from), str(frozen)], assets=rows, skipped=skipped, proxy=proxy_row,
               pooled={k: v for k, v in P.items()}, h2=h2, bb=bb, decided=decided,
               h1=dict(survived=bool(h1_ok) if decided else None, positive=len(pos), of=len(enough)),
               h2_verdict=dict(survived=bool(h2_ok) if decided else None, same_sign=len(same), of=len(both)))
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / "cross_section.json").write_text(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
