import pickle, collections, statistics as st, numpy as np
P = pickle.load(open("pools.pkl","rb"))
PM_POS = "0x58daec3116aae6d93017baaea7749052e8a04fa7"; UR="8876789976decbfcbbbe364623c63652db8c0904"
fam = sorted([p for p in P.values() if p.get("to")==PM_POS and p.get("inlen")==1444 and p.get("fee")==10000 and p.get("ts")==200 and round(p.get("value") or 0,3)==5.0 and "sw" in p], key=lambda p:p["b0"])
dust = collections.Counter(); rows = []
for p in fam:
    b0 = p["b0"]
    pull = next((m[0]-b0 for m in p["mls"] if m[4]<0), None)
    for s in p["sw"]:
        if s[2] < 0 and -s[2] <= 2e13: dust[(s[0]-b0 if s[0]-b0<10 else '10+', s[6][:8])] += 1
    nb = [s for s in p["sw"] if s[6]!=UR and s[2]<0 and -s[2] > 2e13]
    if nb:
        t = nb[0][0]-b0
        if pull is None or pull > t:
            rows.append((t, pull - t if pull is not None else None, round(-nb[0][2]/1e18,5), nb[0][6][:8], p["pid"][:10], 3000 - t))
print("dust buys (<=2e-5 ETH) by offset/sender:", dust.most_common(12))
print("pools with a real non-UR buy (> 2e-5 ETH) before any pull:", len(rows), "of", len(fam))
for W in (5,10,16,20,25,30,60,100,300):
    print(f"  pulled within {W:3d} blocks after it: {sum(1 for r in rows if r[1] is not None and r[1] <= W)}/{len(rows)}")
print("lag, offset, size, sender:", sorted(((r[1] if r[1] is not None else 9999), r[0], r[2], r[3]) for r in rows))
# base hazard: per-block pull probability for pools at the same offsets with no outsider before
haz = collections.Counter(); expo = collections.Counter()
for p in fam:
    b0 = p["b0"]; pull = next((m[0]-b0 for m in p["mls"] if m[4]<0), None)
    nb = [s[0]-b0 for s in p["sw"] if s[6]!=UR and s[2]<0 and -s[2] > 2e13]
    first_out = nb[0] if nb else 10**9
    end = min(pull if pull is not None else 3000, first_out)
    for lo in range(0, 3000, 300):
        a = max(lo, 0); b = min(lo+300, end)
        if b > a: expo[lo] += b - a
    if pull is not None and pull < first_out: haz[(pull//300)*300] += 1
print("base pull hazard per 25 blocks w/o outsider, by offset band:", {k: round(25*haz[k]/expo[k], 4) for k in sorted(expo)})
