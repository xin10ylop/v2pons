"""the early-buy surcharge (event X): its rate by blocks and seconds since the create, and for which buyers; also buys without X in the same window."""
import json, collections, statistics as st, sys
from kload import *
C = load_creates(); ce = {k: v for k, v in C.items() if v["quote"] == 0}
T = load_trades(set(ce), int(sys.argv[1]) if len(sys.argv) > 1 else None)
rows = []
for c, ev in T.items():
    cr = ce[c]; xs = {r[2]: r[6][0] for r in ev if r[4] == "X"}; t0 = bts(cr["bn"])
    for r in ev:
        if r[4] != "B": continue
        dt = r[0] - cr["bn"]
        if dt > 60: continue
        ethIn, out, fee, w3 = r[6][:4]
        rows.append({"dt": dt, "ds": bts(r[0]) - t0, "rate": (fee - ethIn // 100) / ethIn, "x": xs.get(r[2], 0) / ethIn if r[2] in xs else None,
                     "creator": r[5][1] == cr["creator"] or r[5][0] == cr["creator"], "same_tx": r[2] == cr["tx"], "eth": ethIn / 1e18})
by = collections.defaultdict(list)
for z in rows:
    if z["same_tx"]: continue
    by[z["dt"]].append(z)
print("dt  n  with_X  X-rate quantiles (bps)")
for k in sorted(by):
    v = by[k]; xr = sorted(round(z["x"] * 1e4) for z in v if z["x"] is not None)
    print(k, len(v), len(xr), collections.Counter(xr).most_common(4))
cr_tx = [z for z in rows if z["same_tx"]]
print("buys in the create tx", len(cr_tx), "with X", sum(1 for z in cr_tx if z["x"] is not None))
