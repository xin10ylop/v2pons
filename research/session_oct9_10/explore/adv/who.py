import pickle, collections, sys
sys.path.insert(0, ".")
P = pickle.load(open("pools.pkl", "rb")); FP = pickle.load(open("fwd_pools.pkl", "rb"))
PM_POS = "0x58daec3116aae6d93017baaea7749052e8a04fa7"; UR = "8876789976decbfcbbbe364623c63652db8c0904"
isf = lambda p: p.get("to") == PM_POS and p.get("inlen") == 1444 and p.get("fee") == 2500 and p.get("ts") == 50 and abs((p.get("value") or 0) - 2.4333285) < 1e-9 and "sw" in p
ps = [p for p in P.values() if isf(p)] + [p for p in FP.values() if isf(p)]
quick = collections.Counter(); first_sell = []
for p in ps:
    b0 = p["b0"]; bot = next((x for x in p["sw"] if x[2] < 0 and -x[2] >= 0.01e18), None)
    if not bot: continue
    s = [x for x in p["sw"] if x[2] > 0 and bot[0] <= x[0] <= bot[0] + 3]
    for x in s: quick[(x[6][:8], round(x[2] / 1e18, 5))] += 1
    fs = next((x for x in p["sw"] if x[2] > 0), None)
    if fs: first_sell.append(fs[0] - b0)
import numpy as np
print("sells within the bot's first-buy block .. +3 (sender, ETH out):", sum(quick.values()), quick.most_common(6))
print("first sell offset p5/25/50:", np.percentile(first_sell, [5, 25, 50]))
# feed view on the 24 fetched pools: every tx touching the token in +0..+45, by (to, sel, from-class)
D = pickle.load(open("adv/cache.pkl", "rb")); who = collections.Counter(); froms = collections.defaultdict(set)
for pid, Pp in D.items():
    m = Pp["meta"]; b0 = m["b0"]; tb = bytes.fromhex(m["token"][2:])
    for b in Pp["blocks"]:
        if not b: continue
        for t in b["transactions"]:
            data = bytes.fromhex(t["input"][2:])
            if tb in data and t["hash"] != m["tx"]:
                k = ((t["to"] or "")[:10], t["input"][:10], "val>0" if int(t["value"], 16) else "val0")
                who[k] += 1; froms[k].add(t["from"][:10])
print("txs carrying the token, +1..+45, 24 pools: (to, sel, value) count, distinct senders")
for k, v in who.most_common(12): print("  ", k, v, len(froms[k]), sorted(froms[k])[:5])
