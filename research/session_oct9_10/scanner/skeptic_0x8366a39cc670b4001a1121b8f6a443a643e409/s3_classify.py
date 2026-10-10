import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common_s import *
F = load_families(); pids = F[KEY]["pids"]; P = load_pools(); E = load_events(set(pids)); C = load_cache()
cnt = collections.Counter(); ex = {}
for p in pids:
    e = E[p]; a = e["adds"][0]["bn"]
    for s in e["swaps"]:
        t = C.get(s["tx"])
        if not t: continue
        k = (t["to"], t["sel"], t["len"], "buy" if s["a0"] < 0 else "sell")
        cnt[k] += 1; ex.setdefault(k, (t["from"], s["a0"] / 1e18, s["bn"] - a))
for k, n in cnt.most_common(40): print(n, k, ex[k])
