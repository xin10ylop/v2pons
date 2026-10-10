import pickle, collections, statistics as st, numpy as np
P = pickle.load(open("pools.pkl","rb"))
PM_POS = "0x58daec3116aae6d93017baaea7749052e8a04fa7"; UR="8876789976decbfcbbbe364623c63652db8c0904"
fam = sorted([p for p in P.values() if p.get("to")==PM_POS and p.get("inlen")==1444 and p.get("fee")==10000 and p.get("ts")==200 and round(p.get("value") or 0,3)==5.0 and "sw" in p], key=lambda p:p["b0"])
ROUND = {0.12375,0.099,0.1485,0.125,0.07425,0.1,0.0495,0.075,0.15,0.05,0.17325,0.175,1e-05,2e-05}
sc = collections.Counter(); first_nonur = []
for p in fam:
    b0=p["b0"]
    pull = next((m[0]-b0 for m in p["mls"] if m[4]<0), None)
    for s in p["sw"]:
        if s[6] != UR:
            sc[(s[6][:8], "buy" if s[2]<0 else "sell")] += 1
    nb = [s for s in p["sw"] if s[6]!=UR and s[2]<0]
    odd = [s for s in p["sw"] if s[2]<0 and round(-s[2]/1e18,5) not in ROUND]
    first_nonur.append((p["pid"][:10], nb[0][0]-b0 if nb else None, round(-nb[0][2]/1e18,5) if nb else None, nb[0][6][:8] if nb else None, odd[0][0]-b0 if odd else None, round(-odd[0][2]/1e18,5) if odd else None, pull, len([s for s in p["sw"] if s[2]<0])))
print(sc.most_common(20))
# pools with a non-UR buy or odd-size buy before block 70
early = [x for x in first_nonur if (x[1] is not None and x[1] <= 70) or (x[4] is not None and x[4] <= 70)]
print("pools with nonUR/odd buy <= +70:", len(early))
for x in early[:40]: print(x)
# relation pull vs first odd buy
c = collections.Counter()
for x in first_nonur:
    o = min([v for v in (x[1], x[4]) if v is not None], default=None)
    c[("odd" if o is not None else "none", "pulled" if x[6] is not None else "alive")] += 1
print(c)
d = [x[6]-min(v for v in (x[1],x[4]) if v is not None) for x in first_nonur if x[6] is not None and min([v for v in (x[1],x[4]) if v is not None], default=10**9) < x[6]]
print("pull - first odd buy (blocks)", sorted(d)[:60])
