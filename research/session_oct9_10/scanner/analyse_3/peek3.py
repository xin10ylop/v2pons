import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
F = load_families(); P = load_pools()
KEYS = json.load(open("keys.json"))
allp = set()
for k in KEYS: allp |= set(F[k]["pids"])
E = load_events(allp); T = load_txs()
for k in KEYS[1:2] + KEYS[3:4]:
    print("=====", k)
    ratios = collections.Counter()
    for pid in F[k]["pids"]:
        e = E[pid]
        for s in e["swaps"][:8]:
            t = T.get(s["tx"])
            if not t: continue
            if s["a0"] < 0:
                v = t["value_wei"]
                ratios[(t["to"][:10], round(v / -s["a0"], 4) if s["a0"] else None)] += 1
            else:
                ratios[(t["to"][:10], "sell", t["value_wei"])] += 1
    for kk, n in ratios.most_common(30): print(kk, n)
