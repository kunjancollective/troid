#!/usr/bin/env python3
"""Extend the frozen bar file with fresh bars, without letting the fresh feed rewrite history.

  python stitch_bars.py data/btc_4h.csv data/fresh_4h.csv data/live_4h.csv

The frozen file is the sample the journal was built on. Its bars never change. Bars from
the fresh feed are appended only after the frozen file's last bar, so the replay's past
is fixed and the only thing a new day can change is the bars it adds.

Why this exists: api.binance.com returns HTTP 451 to GitHub's runners, so the daily fetch
falls back to api.binance.us, and the two feeds differ on every bar (median 0.05%, max
1.8% on the 2026 sample). Replaying the whole history on the other feed produced 78
trades instead of 71 and journaled 15 alternate-history trades as "new". Freezing the
history makes the replay a function of the frozen sample plus the live tail only.

Fails loudly if the fresh feed does not contain the bar right after the frozen end.
"""
import sys, csv, datetime as dt
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import engine as E


def iso(t):
    return dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def read(path):
    """t,o,h,l,c rows, or o,h,l,c rows anchored at engine.T0. Returns (comment, bars)."""
    comment, rows = "", []
    for r in csv.reader(open(path)):
        if not r:
            continue
        if r[0].startswith("#"):
            comment = comment or r[0]
            continue
        rows.append(r)
    if len(rows[0]) == 5:
        bars = [(int(float(r[0])),) + tuple(map(float, r[1:5])) for r in rows]
    else:
        bars = [(E.T0 + i * E.STEP,) + tuple(map(float, r[:4])) for i, r in enumerate(rows)]
    return comment, bars


def main(frozen_path, fresh_path, out_path):
    _, frozen = read(frozen_path)
    fresh_comment, fresh = read(fresh_path)
    end = frozen[-1][0]
    tail = [b for b in fresh if b[0] > end]
    if not tail:
        sys.exit(f"stitch: {fresh_path} has no bars after the frozen end {iso(end)}")
    if tail[0][0] != end + E.STEP:
        sys.exit(f"stitch: {fresh_path} starts at {iso(tail[0][0])}, expected {iso(end + E.STEP)}")
    bars = frozen + tail
    ts = [b[0] for b in bars]
    if any(b - a != E.STEP for a, b in zip(ts, ts[1:])):
        sys.exit("stitch: bars are not regular 4h")
    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([f"# frozen {frozen_path}: {len(frozen)} bars {iso(frozen[0][0])} -> {iso(end)}; "
                    f"then {len(tail)} bars {iso(tail[0][0])} -> {iso(tail[-1][0])} from {fresh_path}"
                    + (f" ({fresh_comment.lstrip('# ')})" if fresh_comment else "") + "; t,o,h,l,c"])
        w.writerows(bars)
    print(f"{out_path}: {len(frozen)} frozen + {len(tail)} live = {len(bars)} bars, "
          f"{iso(bars[0][0])} -> {iso(bars[-1][0])}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:4])
