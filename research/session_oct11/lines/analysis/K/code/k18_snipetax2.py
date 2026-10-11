"""who pays the early surcharge X in blocks 1-30 after a create: by sender (router or direct), creator, size, 4th word."""
import json, collections, statistics as st, sys
from kload import *
C = load_creates(); ce = {k: v for k, v in C.items() if v["quote"] == 0}
T = load_trades(set(ce), int(sys.argv[1]) if len(sys.argv) > 1 else None)
cnt = collections.Counter(); big = []
for c, ev in T.items():
    cr = ce[c]; xs = {r[2]: r[6][0] for r in ev if r[4] == "X"}
    for r in ev:
        if r[4] != "B" or r[2] == cr["tx"]: continue
        dt = r[0] - cr["bn"]
        if not 1 <= dt <= 9: continue
        ethIn, out, fee, w3 = r[6][:4]
        direct = r[5][0] == r[5][1]
        key = ("X" if r[2] in xs else "noX", "direct" if direct else "via:" + r[5][0][:10], "creator" if r[5][1] == cr["creator"] else "other", "w3" if w3 else "")
        cnt[key] += 1
        if r[2] in xs and xs[r[2]] / ethIn > 0.5: big.append((dt, ethIn / 1e18, round(xs[r[2]] / ethIn, 3), r[5][1][:10], r[2][:12]))
for k, v in cnt.most_common(25): print(v, k)
print("96% cases", big[:10])
