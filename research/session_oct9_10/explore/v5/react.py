import pickle, collections, statistics as st, numpy as np
P = pickle.load(open("pools.pkl","rb"))
PM_POS = "0x58daec3116aae6d93017baaea7749052e8a04fa7"; UR="8876789976decbfcbbbe364623c63652db8c0904"
fam = sorted([p for p in P.values() if p.get("to")==PM_POS and p.get("inlen")==1444 and p.get("fee")==10000 and p.get("ts")==200 and round(p.get("value") or 0,3)==5.0 and "sw" in p], key=lambda p:p["b0"])
rows = []; base_blocks = 0; base_pulls_30 = 0
for p in fam:
    b0 = p["b0"]; end = 3000
    pull = next((m[0]-b0 for m in p["mls"] if m[4]<0), None)
    nb = [s for s in p["sw"] if s[6]!=UR and s[2]<0]
    if nb:
        t = nb[0][0]-b0
        if pull is None or pull > t:
            rows.append((t, pull - t if pull is not None else None, round(-nb[0][2]/1e18,5), nb[0][6][:8], p["pid"][:10]))
print("pools with a non-UR buy before any pull:", len(rows))
lags = [r[1] for r in rows]
for W in (5,10,16,20,25,30,60,100):
    print(f"  pulled within {W:3d} blocks after the first non-UR buy: {sum(1 for x in lags if x is not None and x <= W)}/{len(rows)}")
print(sorted((r[1] if r[1] is not None else 9999, r[0], r[2], r[3]) for r in rows)[:80])
# base: for pools without non-UR buys, pull hazard in a random 30-block window at similar offsets
# per-offset: does an early (<=70) non-UR buy exist?
print("non-UR buys at offset <= 70:", sorted((r[0], r[1], r[2], r[3]) for r in rows if r[0] <= 70))
# the 'pull at ~130' cluster: what precedes it
c130 = [p for p in fam if any(120 <= m[0]-p["b0"] <= 165 and m[4] < 0 for m in p["mls"])]
print("pools pulled at 120-165:", len(c130))
for p in c130[:8]:
    b0=p["b0"]; pull = next(m[0]-b0 for m in p["mls"] if m[4]<0)
    print(p["pid"][:10], "pull", pull, [(s[0]-b0, round(-s[2]/1e18,5) if s[2]<0 else -round(s[2]/1e18,4), s[6][:4]) for s in p["sw"] if s[0]-b0 <= pull][:30])
