"""proper crowd per component: wallets with >=90% of their buys inside the component and present in >=25% of its launches; overlaps"""
from L import *
X = launches(); R = json.load(open(D + "p1.json")); Lp = json.load(open(D + "p2_loops.json"))
P = json.load(open(S + "money/pots.json"))["pots"]; A = set(P["A_7.01"]["crowd"]); Bc = set(P["B_4.86"]["crowd"])
comp = {}
for l in Lp:
    for h in l["launches"]: comp[h] = "L%03d" % l["i"]
SK = {PM, "0x" + "0" * 40, "0x3194e32622c5d860a0572c74edda99dcfd8fc827", "0x8876789976decbfcbbbe364623c63652db8c0904"}
B = {x["h"]: {t for n, t, h in R[x["h"]]["buys"]} - SK - {x["from"]} for x in X}
per = collections.defaultdict(collections.Counter)
for x in X:
    for t in B[x["h"]]: per[t][comp.get(x["h"], "fresh")] += 1
res = {}
for l in Lp:
    k = "L%03d" % l["i"]; n = l["n"]
    crowd = [t for t, c in per.items() if c[k] >= max(2, 0.25 * n) and c[k] >= 0.9 * sum(c.values())]
    shared = [t for t, c in per.items() if c[k] >= max(2, 0.25 * n) and c[k] < 0.9 * sum(c.values())]
    # crowd turnover: how many crowd wallets per launch, and are they the same over time (first/last appearance)
    hs = l["launches"]; per_l = [len(B[h] & set(crowd)) for h in hs]
    res[k] = {"crowd": crowd, "n": n, "per_launch_med": sorted(per_l)[len(per_l) // 2], "shared_frequent": [(t, dict(per[t])) for t in shared][:5]}
    print(f"{k} n={n} crowd wallets={len(crowd)} (median per launch {res[k]['per_launch_med']}) ∩A={len(set(crowd)&A)} ∩B={len(set(crowd)&Bc)}; non-exclusive frequent buyers: {len(shared)}")
ks = sorted(res)
for i, a in enumerate(ks):
    for b in ks[i + 1:]:
        o = set(res[a]["crowd"]) & set(res[b]["crowd"])
        if o: print("  crowd overlap", a, b, len(o))
json.dump(res, open(D + "p6_crowds.json", "w"))
