"""daily view: launches, component membership, overlap (max simultaneous open launch->pull intervals)"""
from L import *
X = launches(); R = json.load(open(D + "p1.json")); Lp = json.load(open(D + "p2_loops.json"))
comp = {}
for l in Lp:
    for h in l["launches"]: comp[h] = "L%03d" % l["i"]
SK = {PM, "0x" + "0" * 40, "0x3194e32622c5d860a0572c74edda99dcfd8fc827", "0x8876789976decbfcbbbe364623c63652db8c0904"}
cnt = collections.Counter()
for x in X:
    for t in {t for n, t, h in R[x["h"]]["buys"]} - SK - {x["from"]}: cnt[t] += 1
day = collections.defaultdict(list)
for x in X: day[T(x["bn"])[:5]].append(x)
rows_ = []
for d in sorted(day):
    xs = day[d]
    ev = []
    for x in xs:
        p = R[x["h"]]["pull"] or x["bn"] + 3000
        ev += [(x["bn"], 1), (p, -1)]
    ev.sort(); cur = mx = 0
    for b, e in ev: cur += e; mx = max(mx, cur)
    cc = collections.Counter(comp.get(x["h"], "fresh") for x in xs)
    nb = sorted(len({t for n, t, h in R[x["h"]]["buys"]} - SK - {x["from"]}) for x in xs)
    fr = [x for x in xs if x["h"] not in comp]
    vals = collections.Counter(round(x["value"], 2) for x in fr).most_common(3)
    pdel = sorted((R[x["h"]]["pull"] or 0) - x["bn"] for x in xs)
    print(f"{d} n={len(xs):3d} maxOpen={mx:2d} medBuyers={nb[len(nb)//2]:3d} medPullDelay={pdel[len(pdel)//2]:6d} comps={dict(cc)} freshVals={vals}")
