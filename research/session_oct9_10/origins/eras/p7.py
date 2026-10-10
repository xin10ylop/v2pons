"""per component: daily segments; crowd-A / crowd-B wallets' first/last buy and which components; L006 Sep-11 part"""
from L import *
X = launches(); R = json.load(open(D + "p1.json")); Lp = json.load(open(D + "p2_loops.json")); C6 = json.load(open(D + "p6_crowds.json"))
P = json.load(open(S + "money/pots.json"))["pots"]; A = set(P["A_7.01"]["crowd"]); Bc = set(P["B_4.86"]["crowd"])
comp = {}
for l in Lp:
    for h in l["launches"]: comp[h] = "L%03d" % l["i"]
SK = {PM, "0x" + "0" * 40, "0x3194e32622c5d860a0572c74edda99dcfd8fc827", "0x8876789976decbfcbbbe364623c63652db8c0904"}
B = {x["h"]: {t for n, t, h in R[x["h"]]["buys"]} - SK - {x["from"]} for x in X}
XH = {x["h"]: x for x in X}
for l in Lp:
    k = "L%03d" % l["i"]
    if l["n"] < 5: continue
    d = collections.defaultdict(list)
    for h in l["launches"]: d[T(XH[h]["bn"])[:5]].append(XH[h])
    cr = set(C6[k]["crowd"])
    print(k, "crowd", len(cr), " | ".join(f"{dd}:{len(v)}x[{','.join(sorted({str(round(x['value'],2)) for x in v})[:4])}] {T(v[0]['bn'])[6:]}-{T(v[-1]['bn'])[6:]}" for dd, v in sorted(d.items())))
for name, S_ in (("crowdA", A), ("crowdB", Bc)):
    first = collections.Counter(); comps = collections.Counter()
    fl = {}
    for x in X:
        for t in B[x["h"]] & S_:
            comps[comp.get(x["h"], "fresh")] += 1
            fl.setdefault(t, [x["bn"], x["bn"]]); fl[t][1] = x["bn"]
    print(name, len(S_), "wallets seen buying:", len(fl), "launch-buys by component", dict(comps))
    print("   first buy dates:", collections.Counter(T(v[0])[:5] for v in fl.values()).most_common(8))
