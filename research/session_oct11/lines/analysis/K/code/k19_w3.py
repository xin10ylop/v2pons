"""the Buy/Sell 4th word (a variable charge): its rate on buys and sells vs blocks since create, the curve's real ETH, and the price move over the
previous 50/300 blocks (momentum)."""
import json, collections, statistics as st, sys
from kload import *
C = load_creates(); ce = {k: v for k, v in C.items() if v["quote"] == 0}
T = load_trades(set(ce), int(sys.argv[1]) if len(sys.argv) > 1 else None)
R = []
for c, ev in T.items():
    cr = ce[c]; x = VX0; y = Y0; hist = [(cr["bn"], x / y)]
    for r in ev:
        k = r[4]
        if k not in "BS": continue
        p_before = x / y
        def back(nb):
            ps = [p for b, p in hist if b <= r[0] - nb]
            return ps[-1] if ps else hist[0][1]
        if k == "B":
            ethIn, out, fee, w3 = r[6][:4]; net = ethIn - fee - w3; rate = w3 / ethIn if ethIn else 0
            R.append(("B", r[0] - cr["bn"], round(rate * 1e4), (x - VX0) / 1e18, p_before / back(50), p_before / back(300), ethIn / 1e18))
            x += net; y -= out
        else:
            tin, eout, fee, w3 = r[6][:4]; gross = x * tin // (y + tin); rate = w3 / gross if gross else 0
            R.append(("S", r[0] - cr["bn"], round(rate * 1e4), (x - VX0) / 1e18, p_before / back(50), p_before / back(300), gross / 1e18))
            x -= gross; y += tin
        hist.append((r[0], x / y))
for k in "BS":
    v = [z for z in R if z[0] == k]
    print(k, len(v), "rate bps top", collections.Counter(z[2] for z in v).most_common(12))
    for lo, hi in [(0, 1), (1, 25), (25, 100), (100, 1000), (1000, 10**4), (10**4, 10**9)]:
        u = [z for z in v if lo <= z[1] < hi]
        if u: print("   dt", lo, hi, len(u), "rate>0 share", round(sum(1 for z in u if z[2] > 0) / len(u), 3), "median rate", st.median(z[2] for z in u))
    for lo, hi in [(0, 0.98), (0.98, 1.0001), (1.0001, 1.05), (1.05, 1.2), (1.2, 2), (2, 1e9)]:
        u = [z for z in v if lo <= z[5] < hi]
        if u: print("   p/p(-300 blocks)", lo, hi, len(u), "rate>0 share", round(sum(1 for z in u if z[2] > 0) / len(u), 3), "median", st.median(z[2] for z in u), "mean", round(sum(z[2] for z in u) / len(u), 1))
