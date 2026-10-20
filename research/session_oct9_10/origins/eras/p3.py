from L import *
import time as _t
X = {x["h"]: x for x in launches()}; R = json.load(open(D + "p1.json")); Lp = json.load(open(D + "p2_loops.json"))
P = json.load(open(S + "money/pots.json"))["pots"]
A = set(P["A_7.01"]["crowd"]); Bc = set(P["B_4.86"]["crowd"])
SK = {PM, "0x" + "0" * 40, "0x3194e32622c5d860a0572c74edda99dcfd8fc827", "0x8876789976decbfcbbbe364623c63652db8c0904"}
TS0 = (84127430, 1760010000)  # approx anchor: block 84127430 ~ Oct 9 11:39 UTC
def bt(bn): return T(bn)
for l in Lp:
    hs = l["launches"]; core = set(l["core"])
    allb = collections.Counter(t for h in hs for t in {t for n, t, _ in R[h]["buys"]} - SK - {X[h]["from"]})
    gaps = [X[hs[i + 1]]["bn"] - X[hs[i]]["bn"] for i in range(len(hs) - 1)]
    print(f"L{l['i']:03d} n={l['n']} {bt(l['bn0'])} -> {bt(l['bn1'])} core {len(core)} crowdA∩{len(core & A)} crowdB∩{len(core & Bc)} median gap {sorted(gaps)[len(gaps)//2] if gaps else 0} blocks; vals {l['vals'][:3]}")
    # sub-periods: list launches with dates where gap > 200k blocks
    seg = [hs[0]]
    for i, g in enumerate(gaps):
        if g > 300000: print(f"      gap {g} blocks ({g*0.1035/3600:.1f} h) after {bt(X[hs[i]]['bn'])}")
