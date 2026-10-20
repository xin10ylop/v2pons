import pickle, collections, sys, numpy as np
sys.path.insert(0, ".")
from fams import hours
P = pickle.load(open("pools.pkl", "rb")); FP = pickle.load(open("fwd_pools.pkl", "rb"))
PM_POS = "0x58daec3116aae6d93017baaea7749052e8a04fa7"; UR = "8876789976decbfcbbbe364623c63652db8c0904"
isf = lambda p: p.get("to") == PM_POS and p.get("inlen") == 1444 and p.get("fee") == 2500 and p.get("ts") == 50 and abs((p.get("value") or 0) - 2.4333285) < 1e-9 and "sw" in p
ps = sorted([p for p in P.values() if isf(p)] + [p for p in FP.values() if isf(p)], key=lambda p: p["b0"])
n = 0
for p in ps:
    b0 = p["b0"]; pl = [m for m in p["mls"] if m[4] < 0]
    if not pl or pl[0][0] - b0 > 30: continue
    n += 1
    if n > 40: break
    pb = pl[0][0]
    s = " ".join(f"+{x[0]-b0}{'B' if x[2]<0 else 'S'}{abs(x[2])/1e18:.4f}{'' if x[6]==UR else '@'+x[6][:4]}" for x in p["sw"] if x[0] <= pb + 2)
    print(f"h{hours(b0):5.1f} n{p['nonce']:2d} {p['pid'][:10]} pull +{pb-b0} frac {-pl[0][4]/p['liq']:.2f} | {s[:260]}")
