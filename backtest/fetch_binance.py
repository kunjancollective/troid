#!/usr/bin/env python3
"""Pull 4h klines from Binance's public REST API (no key needed) into t,o,h,l,c CSV.

  python fetch_binance.py BTCUSDT 2021-01-01 data/BTCUSDT_4h.csv

Forward-fills any gaps with flat bars so engine.py's regular-step contract holds,
and prints how many it filled. Tries api.binance.com then api.binance.us.
NOT tested from the sandbox that wrote it (no egress there) — run it in Claude Code.
"""
import sys, json, time, csv, datetime as dt, urllib.request, urllib.error

STEP = 14400
HOSTS = ["https://api.binance.com", "https://api.binance.us"]

def get(host, params):
    q = "&".join(f"{k}={v}" for k, v in params.items())
    with urllib.request.urlopen(f"{host}/api/v3/klines?{q}", timeout=30) as r:
        return json.loads(r.read())

def main(symbol, start, out):
    t = int(dt.datetime.fromisoformat(start).replace(tzinfo=dt.timezone.utc).timestamp()) * 1000
    bars = []
    host = None
    for h in HOSTS:
        try:
            get(h, {"symbol": symbol, "interval": "4h", "limit": 1}); host = h; break
        except Exception as e:
            print(f"{h}: {e}")
    if not host:
        sys.exit("no reachable Binance host")
    while True:
        chunk = get(host, {"symbol": symbol, "interval": "4h", "startTime": t, "limit": 1000})
        if not chunk:
            break
        bars += [(int(k[0]) // 1000, float(k[1]), float(k[2]), float(k[3]), float(k[4])) for k in chunk]
        t = int(chunk[-1][6]) + 1
        if len(chunk) < 1000:
            break
        time.sleep(0.25)
    bars = bars[:-1]                      # drop the still-forming bar
    # regularise
    filled = 0; out_rows = [bars[0]]
    for b in bars[1:]:
        while b[0] - out_rows[-1][0] > STEP:
            p = out_rows[-1]; out_rows.append((p[0] + STEP, p[4], p[4], p[4], p[4])); filled += 1
        if b[0] - out_rows[-1][0] == STEP:
            out_rows.append(b)
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([f"# {symbol} 4h from {host}, t,o,h,l,c, gaps forward-filled: {filled}"])
        w.writerows(out_rows)
    print(f"{symbol}: {len(out_rows)} bars {dt.datetime.utcfromtimestamp(out_rows[0][0]):%Y-%m-%d} -> "
          f"{dt.datetime.utcfromtimestamp(out_rows[-1][0]):%Y-%m-%d}, {filled} gaps filled -> {out}")

if __name__ == "__main__":
    main(*(sys.argv[1:4] if len(sys.argv) >= 4 else ("BTCUSDT", "2021-01-01", "BTCUSDT_4h.csv")))
