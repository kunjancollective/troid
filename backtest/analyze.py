import engine as E, statistics, itertools, json
bars = E.load_bars("data/btc_4h.csv")
e20, e120, atr = E.indicators(bars)
warm = E.EMA_TREND + E.TREND_SLOPE_BARS + 1

def strength_at(i):   # trend strength at signal bar, in ATRs
    return abs(e20[i]-e120[i]) / atr[i]

# --- 1. regime breakdown for the SWING variant at default params
sigs = E.signals(bars, e20, e120, atr)
r = E.run(bars, sigs, "swing", warm, challenge=False)
# map trades back to their signal bar: entry bar = signal bar + 1
sig_by_entry = {i+1: i for i,_,_ in sigs}
buckets = {"weak <1 ATR":[], "mid 1-2 ATR":[], "strong >2 ATR":[]}
for t in r.trades:
    sb = sig_by_entry.get(t["bar"] - t["bars"])
    if sb is None: continue
    s = strength_at(sb)
    k = "weak <1 ATR" if s < 1 else ("mid 1-2 ATR" if s < 2 else "strong >2 ATR")
    buckets[k].append(t["r"])
print("SWING default — expectancy by trend strength at entry (|EMA20-EMA120| in ATRs)")
for k,v in buckets.items():
    if v: print(f"  {k:14s} n={len(v):3d}  win {sum(1 for x in v if x>0)/len(v)*100:4.0f}%  exp {statistics.mean(v):+.2f}R")

# --- 2. small grid, swing + swing_safe, looking for a ROBUST region not a spike
print("\nGRID (swing_safe): rows=target R, cols=trend EMA; cell = exp R / n trades")
grid = {}
for tgt, trend, smin in itertools.product([1.5,2.0,3.0],[60,120,200],[1.0,2.0]):
    E.TARGET_R, E.EMA_TREND = tgt, trend
    e20b, e120b, atrb = E.indicators(bars)
    sg = E.signals(bars, e20b, e120b, atrb)
    # strength filter applied here
    sg = [(i,s,d) for i,s,d in sg if abs(e20b[i]-e120b[i])/atrb[i] >= smin]
    w = trend + E.TREND_SLOPE_BARS + 1
    for variant in ("swing","swing_safe"):
        rr = E.run(bars, sg, variant, w, challenge=False)
        st = E.trade_stats(rr.trades)
        grid[(variant,tgt,trend,smin)] = (st.get("exp_r",0), st.get("n",0), st.get("profit_factor",0), st.get("win_rate",0))
E.TARGET_R, E.EMA_TREND = 2.0, 120
for variant in ("swing","swing_safe"):
    for smin in (1.0,2.0):
        print(f"\n {variant}, min strength {smin} ATR")
        print("        EMA60          EMA120         EMA200")
        for tgt in (1.5,2.0,3.0):
            row = f"  {tgt}R  "
            for trend in (60,120,200):
                e,n,pf,wr = grid[(variant,tgt,trend,smin)]
                row += f"{e:+.2f}R/{n:3d}     "
            print(row)
