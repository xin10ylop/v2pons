from L import *
X = launches(); R = json.load(open(D + "p1.json")); Lp = json.load(open(D + "p2_loops.json"))
P = json.load(open(S + "money/pots.json"))["pots"]; A = set(P["A_7.01"]["crowd"]); Bc = set(P["B_4.86"]["crowd"])
comp = {}
for l in Lp:
    for h in l["launches"]: comp[h] = "L%03d" % l["i"]
SK = {PM, "0x" + "0" * 40, "0x3194e32622c5d860a0572c74edda99dcfd8fc827", "0x8876789976decbfcbbbe364623c63652db8c0904"}
B = {x["h"]: {t for n, t, h in R[x["h"]]["buys"]} - SK - {x["from"]} for x in X}
cnt = collections.Counter(t for b in B.values() for t in b)
# 1) core overlaps between components
cores = {"L%03d" % l["i"]: set(l["core"]) for l in Lp}
cores["A"] = A; cores["B"] = Bc
ks = sorted(cores)
print("core overlaps (nonzero):")
for i, a in enumerate(ks):
    for b in ks[i + 1:]:
        o = cores[a] & cores[b]
        if o: print("  ", a, b, len(o))
# 2) where do each component's core wallets buy outside the component
print("core wallets buying outside their component:")
for l in Lp:
    c = set(l["core"]); hs = set(l["launches"])
    outside = collections.Counter()
    for x in X:
        if x["h"] in hs: continue
        k = len(B[x["h"]] & c)
        if k: outside[comp.get(x["h"], "fresh")] += 1
    print("   L%03d core %d -> launches outside with any core buyer: %s" % (l["i"], len(c), dict(outside)))
# 3) frequent buyers: where
print("frequent buyers (>=40 launches): components/eras")
for t, c in cnt.most_common(12):
    hs = [x for x in X if t in B[x["h"]]]
    cc = collections.Counter(comp.get(x["h"], "fresh") for x in hs)
    print("  ", t, c, T(hs[0]["bn"]), "->", T(hs[-1]["bn"]), dict(cc.most_common(6)))
# 4) fresh launches: share of buyers seen in only that launch
fr = [x for x in X if x["h"] not in comp]
one = sum(1 for x in fr for t in B[x["h"]] if cnt[t] == 1); tot = sum(len(B[x["h"]]) for x in fr)
print("fresh launches", len(fr), "buyer slots", tot, "single-launch buyers", one)
