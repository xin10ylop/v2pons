import pickle, collections, sys, numpy as np
sys.path.insert(0, ".")
from fams import hours
P = pickle.load(open("pools.pkl", "rb")); FP = pickle.load(open("fwd_pools.pkl", "rb"))
PM_POS = "0x58daec3116aae6d93017baaea7749052e8a04fa7"; UR = "8876789976decbfcbbbe364623c63652db8c0904"
isf = lambda p: p.get("to") == PM_POS and p.get("inlen") == 1444 and p.get("fee") == 2500 and p.get("ts") == 50 and abs((p.get("value") or 0) - 2.4333285) < 1e-9 and "sw" in p
ps = sorted([(p, "inwin") for p in P.values() if isf(p)] + [(p, "fwd") for p in FP.values() if isf(p)], key=lambda q: q[0]["b0"])
lags = collections.Counter(); per = collections.defaultdict(lambda: [0, 0]); first_out = collections.defaultdict(lambda: [0, 0]); pre_only = [0, 0]
for p, src in ps:
    b0 = p["b0"]; sw = p["sw"]; pl = [m[0] for m in p["mls"] if m[4] < 0]; pull = pl[0] if pl else None
    bot = next((x for x in sw if x[2] < 0 and -x[2] >= 0.01e18), None)
    if not bot: continue
    seg = "fwd" if src == "fwd" else f"h{int(hours(b0)//6)*6:02d}"
    outs = [x for x in sw if x[2] < 0 and -x[2] >= 1e13 and (x[0], x[1]) > (bot[0], bot[1]) and x[6] != UR and (pull is None or x[0] < pull)]
    for x in outs:
        per[seg][0] += 1
        if pull is not None and 1 <= pull - x[0] <= 16: per[seg][1] += 1; lags[pull - x[0]] += 1
    if outs:
        x = outs[0]; first_out[seg][0] += 1
        if pull is not None and 0 <= pull - x[0] <= 30: first_out[seg][1] += 1
    else:
        pre = [x for x in sw if x[2] < 0 and x[6] != UR and (x[0], x[1]) < (bot[0], bot[1])]
        if pre:
            pre_only[0] += 1
            if pull is not None and pull - b0 <= 60: pre_only[1] += 1
print("pull lag after a post-bot outsider buy (blocks: count):", sorted(lags.items()))
print("per segment: post-bot outsider buys, followed by pull <=16 | pools with a post-bot outsider: first one followed by pull <=30")
for k in sorted(per): print(f"  {k}: {per[k][0]:4d} {per[k][1]:4d} ({per[k][1]/max(1,per[k][0]):.2f}) | pools {first_out[k][0]:3d} pulled<=30 after {first_out[k][1]:3d}")
print("pools with ONLY pre-bot outsider buys (no post-bot outsider before the pull):", pre_only[0], "pulled by +60:", pre_only[1])
