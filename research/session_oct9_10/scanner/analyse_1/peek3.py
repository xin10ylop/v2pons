import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
P = load_pools(); F = load_families()
key = "0xc763b1795dabe2d2336eba214d16969ebc5db27f|f0e9eabf|1796|10000|200|false"
pids = F[key]["pids"]
E = load_events(set(pids)); T = load_txs()
ratios = collections.Counter(); ex = {}
for pid in pids:
    for s in E[pid]["swaps"]:
        t = T.get(s["tx"])
        if not t: continue
        if s["a0"] < 0 and t["value_wei"]:
            r = round(-s["a0"] / t["value_wei"], 5)
            k = (t["to"][:10], t["selector"], r); ratios[k] += 1; ex.setdefault(k, s["tx"])
        elif s["a0"] > 0:
            k = (t["to"][:10], t["selector"], "sell"); ratios[k] += 1; ex.setdefault(k, s["tx"])
for k, v in ratios.most_common(30): print(k, v, ex[k])
