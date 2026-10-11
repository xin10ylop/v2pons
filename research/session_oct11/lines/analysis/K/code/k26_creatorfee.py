"""the 4th word of Buy/Sell = a per-curve creator fee: is its rate constant within a curve, or does it change with time? distribution across curves."""
import json, pickle, collections, statistics as st
from kload import *
P = pickle.load(open(os.path.join(DATA, "packed.pkl"), "rb")); CE = P["creates"]; TR = P["trades"]
const = 0; varying = []; dist = collections.Counter(); first = collections.Counter(); n = 0
for c, ev in TR.items():
    rates = []
    for r in ev:
        if r[3] == "B" and r[5][0] > 10**12: rates.append((r[0] - CE[c]["bn"], round(r[5][3] / r[5][0] * 1e4)))
        elif r[3] == "S" and r[5][1] > 10**12: g = r[5][1] + r[5][2] + r[5][3]; rates.append((r[0] - CE[c]["bn"], round(r[5][3] / g * 1e4)))
    if len(rates) < 2: continue
    n += 1; s = {x[1] for x in rates}; first[rates[0][1]] += 1
    if len(s) == 1: const += 1; dist[rates[0][1]] += 1
    else: varying.append(rates)
print("curves with >= 2 trades", n, "constant rate", const, "varying", len(varying))
print("constant-rate distribution (bps)", dist.most_common(15))
for v in varying[:8]: print("  ", v[:3], "...", v[-3:])
# varying: monotone decreasing over time?
dec = sum(1 for v in varying if all(a[1] >= b[1] for a, b in zip(v, v[1:])))
print("varying and non-increasing", dec)
# share of trades by rate class
