#!/usr/bin/env python3
"""ethride.py [LINE_JSON]: the Ethereum 1852 B line's front, replayed on each pool's recorded swaps with our trade in the pool: STAKE in at the
head of launch + ENTRY (before that block's swaps), every recorded swap re-run on the changed reserves (buys: the same ETH in; sells: the same
tokens in), our tokens sold at the end of launch + EXIT (-100% if the LP burn came first). Uniswap V2, 0.3% fee. GAS_ETH per trade (buy,
approve, sell). Read-only (reads out/line_eth_full.json, written by the scratch fetch)."""
import sys, json, statistics as st, os
d = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "out/line_eth_full.json"))
GAS = float(os.environ.get("GAS_ETH", "0.0006"))
F = 0.997


def ride(p, entry, exit_, stake):
    ev = p["ev"]
    if not ev:
        return None
    if p["burn"] is not None and p["burn"] <= exit_:
        return -1.0
    first = ev[0]
    x = first[4] - first[2]; y = first[5] + first[3]                  # reserves before the first swap (ETH, token units)
    ours = None
    for e in ev:
        if ours is None and e[0] >= entry:
            s = stake * F; ours = y * s / (x + s); x += stake; y -= ours
        if e[0] > exit_:
            break
        n, t = e[2], e[3]
        if n > 0:                                                    # a buy: the same ETH in
            s = n * F; out = y * s / (x + s); x += n; y -= out
        else:                                                        # a sell: the same tokens in
            tin = -t; out = x * tin * F / (y + tin * F); x -= out; y += tin
    if ours is None:
        s = stake * F; ours = y * s / (x + s); x += stake; y -= ours
    back = x * ours * F / (y + ours * F)
    return (back - stake - GAS) / stake


pools = d["pools"]
print(f"{len(pools)} pools; burn offsets {sorted(p['burn'] for p in pools)}; gas {GAS} ETH a trade")
for stake in (0.05, 0.1, 0.25, 0.5, 1.0):
    print(f"\nstake {stake} ETH")
    for entry in (1, 2, 3, 5):
        row = []
        for exit_ in (30, 60, 100, 145, 200, 300, 400, 470):
            r = [ride(p, entry, exit_, stake) for p in pools]; r = [v for v in r if v is not None]
            row.append(f"x{exit_}: {st.mean(r):+.0%} (min {min(r):+.0%})")
        print(f"  in +{entry}: " + "  ".join(row))
