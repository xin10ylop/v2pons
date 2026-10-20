"""cluster launches into loops by shared repeat buyers (crowd wallets)"""
from L import *
X = launches(); R = json.load(open(D + "p1.json"))
X = [x for x in X if x["h"] in R and "buys" in R[x["h"]]]
SKIP = {PM, "0x" + "0" * 40, "0x3194e32622c5d860a0572c74edda99dcfd8fc827", "0x8876789976decbfcbbbe364623c63652db8c0904"}
buyers = {}
cnt = collections.Counter()
for x in X:
    b = {t for n, t, h in R[x["h"]]["buys"]} - SKIP - {x["from"]}
    buyers[x["h"]] = b
    for t in b: cnt[t] += 1
print("launches", len(X), "distinct buyers", len(cnt), "buyers in >=3 launches", sum(1 for v in cnt.values() if v >= 3))
# repeat-buyer signature per launch
sig = {h: {t for t in b if cnt[t] >= 3} for h, b in buyers.items()}
# union-find launches sharing >= 5 signature wallets (and >=30% of the smaller signature)
par = {x["h"]: x["h"] for x in X}
def f(a):
    while par[a] != a: par[a] = par[par[a]]; a = par[a]
    return a
inv = collections.defaultdict(list)
for h, s in sig.items():
    for t in s: inv[t].append(h)
# wallets that buy in very many launches across long spans (snipers) are excluded from linking: compute span
bn = {x["h"]: x["bn"] for x in X}
pairs = collections.Counter()
for t, hs in inv.items():
    if len(hs) > 400: continue
    hs = sorted(hs, key=lambda h: bn[h])
    for i in range(len(hs)):
        for j in range(i + 1, min(len(hs), i + 6)):  # link to the next few launches this wallet bought (loops are sequential)
            pairs[(hs[i], hs[j])] += 1
for (a, b), c in pairs.items():
    if c >= 5 and c >= 0.3 * min(len(sig[a]), len(sig[b])): par[f(a)] = f(b)
comp = collections.defaultdict(list)
for x in X: comp[f(x["h"])].append(x)
big = sorted([c for c in comp.values() if len(c) >= 3], key=lambda c: c[0]["bn"])
print("components with >=3 launches:", len(big), "covering", sum(len(c) for c in big), "launches; singletons/small:", sum(len(c) for c in comp.values() if len(c) < 3))
out = []
for i, c in enumerate(big):
    cw = collections.Counter(t for x in c for t in sig[x["h"]])
    core = [t for t, k in cw.items() if k >= max(3, 0.3 * len(c))]
    vals = collections.Counter(round(x["value"], 2) for x in c)
    newwal = sum(1 for x in c if x["nonce"] == 0)
    nsend = len({x["from"] for x in c})
    pulled = sum(1 for x in c if R[x["h"]]["pull"])
    out.append({"i": i, "n": len(c), "bn0": c[0]["bn"], "bn1": c[-1]["bn"], "core": core, "vals": vals.most_common(5), "senders": nsend, "nonce0": newwal, "pulled": pulled,
                "launches": [x["h"] for x in c]})
    print(f"L{i:03d} n={len(c):4d} blocks {c[0]['bn']}-{c[-1]['bn']} core={len(core):3d} senders={nsend} nonce0={newwal} pulled={pulled} vals={vals.most_common(4)}")
json.dump(out, open(D + "p2_loops.json", "w"))
json.dump({"cnt": cnt.most_common(3000)}, open(D + "p2_buyercnt.json", "w"))
