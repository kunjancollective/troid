#!/usr/bin/env python3
"""troid-shadow-2's walk-forward (SHADOW2.md), beside shadow-1's (WALKFORWARD.md).

  python walkforward2.py data/BTCUSDT_4h.csv data/ETHUSDT_4h.csv > WALKFORWARD2.md

The design was fixed before any run (SHADOW2.md, shadow2_config.json); nothing here changes it. One continuous run per
asset with challenge accounting off (expectancy per trade is the statistic), trades bucketed by exit time. The holdout
is 2025-01-01 to the frozen end, 2026-09-21; later bars are a live tail. A bucket under 30 trades is insufficient, not a
number. The four lookbacks alone are the neighbourhood, reported beside the ensemble, never chosen from. The states
split the holdout's trades; the confluence matrix is measured at every decision bar. H1 and H2 are decided on the
cross-section, not on one asset.

Also writes results/shadow2_<SYMBOL>.json.
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


def stats(trades):
    rs = [t["r"] for t in trades]
    n = len(rs)
    out = dict(n=n)
    if n < 2:
        return out
    pnl = [t["pnl"] for t in trades]
    gw, gl = math.fsum(x for x in pnl if x > 0), -math.fsum(x for x in pnl if x < 0)
    m, sd = statistics.fmean(rs), statistics.stdev(rs)
    se = sd / math.sqrt(n)
    out.update(exp=m, sd=sd, se=se, lo=m - 1.96 * se, hi=m + 1.96 * se, pf=(gw / gl if gl else float("inf")),
               win=100 * sum(1 for x in pnl if x > 0) / n, net=math.fsum(pnl))
    return out


def diff(a, b):
    """Mean of a minus mean of b, with its standard error (Welch) and 95% interval; None under MIN_N either side."""
    sa, sb = stats(a), stats(b)
    if sa["n"] < MIN_N or sb["n"] < MIN_N:
        return None
    d, se = sa["exp"] - sb["exp"], math.sqrt(sa["se"] ** 2 + sb["se"] ** 2)
    return dict(d=d, se=se, lo=d - 1.96 * se, hi=d + 1.96 * se)


def row(label, st, months):
    tpm = st["n"] / months if months else 0
    if st["n"] < MIN_N:
        return f"| {label} | {st['n']} | {tpm:.1f} | insufficient (n < {MIN_N}) | | | | |"
    return (f"| {label} | {st['n']} | {tpm:.1f} | {st['win']:.0f}% | {st['exp']:+.3f} | {st['se']:.3f} | "
            f"[{st['lo']:+.3f}, {st['hi']:+.3f}] | {st['pf']:.2f} |")


def pearson(x, y):
    mx, my = statistics.fmean(x), statistics.fmean(y)
    sxy = math.fsum((a - mx) * (b - my) for a, b in zip(x, y))
    sxx, syy = math.fsum((a - mx) ** 2 for a in x), math.fsum((b - my) ** 2 for b in y)
    return sxy / math.sqrt(sxx * syy) if sxx and syy else float("nan")


def inputs_at_decisions(bars, t0, cfg):
    """Each input at every decision bar where all exist: shadow-2's vote, volatility and vol-of-vol, Bollinger width,
    and shadow-1's two inputs (its 120-bar EMA trend and its 90-bar range width in ATRs)."""
    o, h, l, c = zip(*bars)
    sig = S2.daily_vol(c, cfg)
    vov = S2.vol_of_vol(sig, cfg)
    bbw = S2.bb_width(c, cfg)
    _, e120, atr = E.indicators(bars)
    _, _, _, width = V.regime(bars, atr)
    nL = {L: S2.lookback_bars(L, cfg) for L in cfg["lookback_months"]}
    first = S2.first_decision(bars, t0, cfg)
    cols = {k: [] for k in ("vote", "sigma", "vov", "bb_width", "s1_trend", "s1_range_width")}
    for i in range(first, len(bars) - 1):
        if not S2.is_decision(i, t0, cfg) or width[i] is None or e120[i - E.TREND_SLOPE_BARS] is None:
            continue
        up = c[i] > e120[i] and e120[i] > e120[i - E.TREND_SLOPE_BARS]
        dn = c[i] < e120[i] and e120[i] < e120[i - E.TREND_SLOPE_BARS]
        cols["vote"].append(sum((c[i] > c[i - n]) - (c[i] < c[i - n]) for n in nL.values()))
        cols["sigma"].append(sig[i]); cols["vov"].append(vov[i]); cols["bb_width"].append(bbw[i])
        cols["s1_trend"].append(1 if up else -1 if dn else 0); cols["s1_range_width"].append(width[i])
    names = list(cols)
    return names, {(a, b): pearson(cols[a], cols[b]) for a in names for b in names}, len(cols["vote"])


def admitted(corr):
    """The gate, in SHADOW2.md's order: an input is admitted only if |corr| < 0.5 with every input already admitted."""
    inn, out = [], {}
    for k in ("vote", "sigma", "vov"):
        worst = max((abs(corr[(k, j)]) for j in inn), default=0.0)
        out[k] = (worst < 0.5, worst)
        if worst < 0.5:
            inn.append(k)
    for k in ("bb_width",):                               # the comparison, measured against what was admitted
        out[k] = (max(abs(corr[(k, j)]) for j in inn) < 0.5, max(abs(corr[(k, j)]) for j in inn))
    return out


def one(path, cfg):
    bars, t0 = S2.load(path)
    sym = Path(path).stem.replace("_4h", "")
    asset = sym.replace("USDT", "").replace("USD", "") if sym.endswith(("USDT", "USD")) else sym
    when = lambda i: dt.datetime.fromtimestamp(t0 + i * E.STEP, dt.timezone.utc)        # noqa: E731
    hold_from = dt.date.fromisoformat(cfg["holdout_from"])
    frozen = dt.date.fromisoformat(cfg["frozen_end"])
    first = S2.first_decision(bars, t0, cfg)
    start = first + 1

    def trades_for(lookbacks=None):
        sigs = S2.signals(bars, t0, cfg, lookbacks=lookbacks)
        r = S2.run(bars, t0, sigs, cfg, asset=asset, challenge=False, start=start)
        tr = [t for t in r.trades if t["reason"] != "eod"]            # a position open at the last bar isn't a closed trade
        for t in tr:
            t["when"] = when(t["bar"])
        return tr, sigs

    ens, sigs = trades_for()
    alone = {L: trades_for((L,))[0] for L in cfg["lookback_months"]}
    flat = {i for i, b in enumerate(bars) if b[0] == b[1] == b[2] == b[3]}
    months = lambda a, b: sum(1 for i in range(start, len(bars)) if a <= when(i).date() <= b) * 4 / 24 / 30.44  # noqa: E731
    first_day, last_day = when(start).date(), when(len(bars) - 1).date()
    hold = lambda tr: [t for t in tr if hold_from <= t["when"].date() <= frozen]        # noqa: E731
    before = [t for t in ens if t["when"].date() < hold_from]
    after = [t for t in ens if t["when"].date() > frozen]
    years = sorted({t["when"].year for t in ens})
    H = hold(ens)
    hs = stats(H)

    # the states, on the holdout's trades and on every holdout decision
    split = {k: {s: [t for t in H if t.get(k) == s] for s in states} for k, states in
             (("vov_state", ("calm", "unsettled")), ("bb_state", ("compressed", "expanded")))}
    dec = [s for s in S2.signals(bars, t0, cfg) if hold_from <= when(s["i"]).date() <= frozen]
    agree = (100 * sum(1 for s in dec if (s["vov_state"] == "calm") == (s["bb_state"] == "compressed")) / len(dec)) if dec else None
    names, corr, n_dec = inputs_at_decisions(bars, t0, cfg)
    gate = admitted(corr)

    s1 = json.loads((HERE / "results" / f"walkforward_{sym}.json").read_text()) if (HERE / "results" / f"walkforward_{sym}.json").exists() else None
    y25 = stats([t for t in ens if t["when"].year == 2025])
    reasons = {}
    for t in H:
        reasons[t["reason"]] = reasons.get(t["reason"], 0) + 1

    L = []
    L.append(f"## {sym}: {len(bars)} bars, {when(0):%Y-%m-%d} -> {when(len(bars) - 1):%Y-%m-%d}\n")
    L.append(f"Data: `{Path(path).resolve().relative_to(HERE).as_posix()}`. Forward-filled bars in the file: {len(flat)}. The first decision "
             f"with every input: {when(first):%Y-%m-%d} (bar {first}). Hold limit: {cfg['hold_bars'][S2.asset_class(asset, cfg)]} "
             f"bars ({S2.asset_class(asset, cfg)}).\n")
    L.append("| bucket | n | trades/mo | win | exp R | SE | 95% CI | PF |")
    L.append("|---|---|---|---|---|---|---|---|")
    for y in years:
        tr = [t for t in ens if t["when"].year == y]
        tag = " (holdout)" if y >= hold_from.year else ""
        L.append(row(f"{y}{tag}", stats(tr), months(max(first_day, dt.date(y, 1, 1)), min(last_day, dt.date(y, 12, 31)))))
    L.append(row(f"before the holdout, {first_day} -> {hold_from - dt.timedelta(days=1)}", stats(before),
                 months(first_day, hold_from - dt.timedelta(days=1))))
    L.append(row(f"**holdout, {hold_from} -> {frozen}**", hs, months(hold_from, frozen)))
    if after:
        L.append(row(f"after {frozen} (live tail)", stats(after), months(frozen + dt.timedelta(days=1), last_day)))
    L.append("")
    L.append(f"Holdout exits: " + ", ".join(f"{k} {v}" for k, v in sorted(reasons.items())) + ".\n")
    L.append("**The neighbourhood, on the holdout.** The ensemble is the strategy; each lookback alone is shown beside it, "
             "not chosen from.\n")
    L.append("| signal | n | exp R | SE | 95% CI |")
    L.append("|---|---|---|---|---|")
    for lab, tr in [("ensemble of 3, 6, 9, 12 months (the strategy)", H)] + [(f"{m} months alone", hold(alone[m])) for m in cfg["lookback_months"]]:
        st = stats(tr)
        L.append(f"| {lab} | {st['n']} | " + ("insufficient | | |" if st["n"] < MIN_N else
                                             f"{st['exp']:+.3f} | {st['se']:.3f} | [{st['lo']:+.3f}, {st['hi']:+.3f}] |"))
    L.append("")
    L.append("**The states, on the holdout's trades** (recorded at entry, never used to filter).\n")
    L.append("| state | n | exp R | 95% CI |")
    L.append("|---|---|---|---|")
    for k, states in (("vov_state", ("calm", "unsettled")), ("bb_state", ("compressed", "expanded"))):
        for s in states:
            st = stats(split[k][s])
            L.append(f"| {'vol-of-vol' if k == 'vov_state' else 'Bollinger width'}: {s} | {st['n']} | " +
                     ("insufficient | |" if st["n"] < MIN_N else f"{st['exp']:+.3f} | [{st['lo']:+.3f}, {st['hi']:+.3f}] |"))
    dv = diff(split["vov_state"]["calm"], split["vov_state"]["unsettled"])
    db = diff(split["bb_state"]["compressed"], split["bb_state"]["expanded"])
    L.append("")
    L.append("- Calm minus unsettled: " + (f"{dv['d']:+.3f}R, SE {dv['se']:.3f}, 95% CI [{dv['lo']:+.3f}, {dv['hi']:+.3f}]."
                                             if dv else "insufficient (a state under 30 trades)."))
    L.append("- Compressed minus expanded: " + (f"{db['d']:+.3f}R, SE {db['se']:.3f}, 95% CI [{db['lo']:+.3f}, {db['hi']:+.3f}]."
                                                  if db else "insufficient (a state under 30 trades)."))
    L.append(f"- The two states agree (calm with compressed, unsettled with expanded) on {agree:.0f}% of the holdout's "
             f"{len(dec)} trading decisions." if agree is not None else "- No holdout decisions.")
    L.append("")
    L.append(f"**The confluence gate**, at {n_dec} decision bars: |corr| between the inputs.\n")
    L.append("| | " + " | ".join(names) + " |")
    L.append("|---|" + "---|" * len(names))
    for a in names:
        L.append(f"| {a} | " + " | ".join(f"{abs(corr[(a, b)]):.2f}" for b in names) + " |")
    L.append("")
    L.append("Admitted in order (|corr| < 0.5 with every input already in): " + "; ".join(
        f"{k} {'in' if okk else 'OUT'} (worst |corr| {w:.2f})" for k, (okk, w) in gate.items() if k != "bb_width")
        + f". Bollinger width against what was admitted: worst |corr| {gate['bb_width'][1]:.2f}"
        + (" (under 0.5)." if gate["bb_width"][0] else " (0.5 or more: it would not be admitted)."))
    L.append("")
    if s1:
        h1 = s1["holdout"]; y1 = s1["years"].get("2025", {})
        L.append("**Beside shadow-1** (WALKFORWARD.md; 2025 is out of sample for both).\n")
        L.append("| | n | exp R | 95% CI |")
        L.append("|---|---|---|---|")
        L.append(f"| shadow-1, its holdout (before 2026-01-08) | {h1['n']} | {h1['exp']:+.3f} | [{h1['lo']:+.3f}, {h1['hi']:+.3f}] |")
        L.append(f"| shadow-1, 2025 | {y1.get('n', 0)} | " + (f"{y1['exp']:+.3f} | [{y1['lo']:+.3f}, {y1['hi']:+.3f}] |"
                                                              if y1.get("n", 0) >= MIN_N else "insufficient | |"))
        L.append(f"| shadow-2, 2025 | {y25['n']} | " + (f"{y25['exp']:+.3f} | [{y25['lo']:+.3f}, {y25['hi']:+.3f}] |"
                                                         if y25["n"] >= MIN_N else "insufficient | |"))
        L.append(f"| shadow-2, its holdout ({hold_from} -> {frozen}) | {hs['n']} | " +
                 (f"{hs['exp']:+.3f} | [{hs['lo']:+.3f}, {hs['hi']:+.3f}] |" if hs["n"] >= MIN_N else "insufficient | |"))
        L.append("")
    verdict = ("insufficient" if hs["n"] < MIN_N else "excludes zero" if hs["lo"] > 0 or hs["hi"] < 0 else "contains zero")
    L.append(f"Reading it: the holdout is n = {hs['n']}" + (f", {hs['exp']:+.3f}R, 95% CI [{hs['lo']:+.3f}R, {hs['hi']:+.3f}R]: {verdict}."
                                                          if hs["n"] >= MIN_N else ": insufficient.")
             + " MEASURED on one asset; H1 and H2 are decided on the cross-section (SHADOW2.md).\n")

    dump = dict(symbol=sym, asset=asset, bars=len(bars), first=when(0).isoformat(), last=when(len(bars) - 1).isoformat(),
                config=cfg["name"], first_decision=when(first).isoformat(), hold_bars=cfg["hold_bars"][S2.asset_class(asset, cfg)],
                forward_filled_bars=len(flat), years={str(y): stats([t for t in ens if t["when"].year == y]) for y in years},
                before=stats(before), holdout=dict(hs, months=months(hold_from, frozen)), after=stats(after),
                alone={str(m): stats(hold(alone[m])) for m in cfg["lookback_months"]},
                states={k: {s: stats(v) for s, v in d.items()} for k, d in split.items()},
                calm_minus_unsettled=dv, compressed_minus_expanded=db, states_agree_pct=agree, holdout_exits=reasons,
                confluence={f"{a}|{b}": corr[(a, b)] for a in names for b in names}, n_decisions=n_dec,
                admitted={k: dict(admitted=a, worst=w) for k, (a, w) in gate.items()},
                holdout_trades=[dict(entry_utc=when(t["entry_bar"]).isoformat(), exit_utc=t["when"].isoformat(), side=t["side"],
                                     r=t["r"], reason=t["reason"], vov_state=t.get("vov_state"), bb_state=t.get("bb_state"))
                                for t in H])
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / f"shadow2_{sym}.json").write_text(json.dumps(dump, indent=1, default=str))
    return "\n".join(L)


def main(paths):
    cfg = S2.load_config()
    print("# Walk-forward — troid-shadow-2\n")
    print("**Generated by `walkforward2.py`. Do not hand-edit — regenerate.**\n")
    print(site_text.hypo_md(no_edge=site_text.NO_EDGE_SHORT + " shadow-2's rows below are MEASURED; none is stated as fact."))
    print(f"Strategy: `{cfg['name']}` from `shadow2_config.json`, fixed before any run (SHADOW2.md): time-series momentum, the "
          f"sign of the vote of the {', '.join(map(str, cfg['lookback_months'][:-1]))} and {cfg['lookback_months'][-1]}-month returns, "
          f"long and short; one decision a day on the {cfg['decide_bar_utc']} UTC bar's close; the stop {cfg['stop_sigmas']:g} daily "
          f"deviations away, {cfg['risk_pct'] * 100:.1f}% risk at that stop; a {cfg['take_profit_r']:g}R take-profit and the asset "
          f"class's hold limit; holding through the reset. One continuous run per asset, challenge accounting off, trades bucketed "
          f"by exit time. Nothing was fitted on any year. Buckets under {MIN_N} trades are insufficient, not numbers.\n")
    for p in paths:
        print(one(p, cfg))
        print("---\n")


if __name__ == "__main__":
    main(sys.argv[1:] or ["data/BTCUSDT_4h.csv", "data/ETHUSDT_4h.csv"])
