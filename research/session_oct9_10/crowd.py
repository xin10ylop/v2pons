import json, gzip, collections, statistics as st
D = json.load(gzip.open("/home/user/v2pons/research/data/slowrug_op.json.gz"))
P, S, L, T = D["pools"], D["swaps"], D["liquidity"], D["txs"]
OP = "3194e32622c5d860a0572c74edda99dcfd8fc827"
low = [p for p in P if P[p]["fee"] < 10000 and T.get(P[p]["tx"], ["",""])[1] == OP]
print(len(low), "sub-1% operator launches")
gaps = collections.Counter(); n2 = collections.Counter(); seq = []
for p in low:
    b0 = P[p]["bn"]; sw = sorted(S.get(p, []), key=lambda x: (x[0], x[1]))
    real = [x for x in sw if x[3] < 0 and -x[3] >= 2e14 and x[0] > b0]
    if not real: continue
    f = real[0][0]
    rel = [x[0] - f for x in real[1:]]
    # buys (real) in first+1 .. first+10, by offset
    for r in rel:
        if r <= 10: gaps[r] += 1
    nxt = [r for r in rel if r >= 1]
    n2[nxt[0] if nxt and nxt[0] <= 10 else ">10"] += 1
    seq.append((p, f, [(x[0]-f, round(-x[3]/1e18, 4)) for x in real[:8]]))
print("real buys after the first, by offset (blocks after first buy):", sorted(gaps.items()))
print("offset of the crowd's 2nd real buy:", sorted(n2.items(), key=lambda x: (isinstance(x[0], str), x[0])))
for p, f, s in seq[-15:]: print(p[:10], f, s)
