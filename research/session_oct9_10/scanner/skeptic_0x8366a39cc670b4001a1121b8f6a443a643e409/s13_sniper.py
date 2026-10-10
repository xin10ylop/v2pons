import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common_s import *
P = load_pools(); T = load_txs()
fams = collections.defaultdict(set)
for h, t in T.items():
    if t["from"] == SNIPER:
        for pid, kind, rank in t["refs"]: fams[P[pid]["family"]].add(pid)
E = load_events({p for s in fams.values() for p in s})
for f, ps in fams.items():
    sz = []
    for p in ps:
        for s in E[p]["swaps"]:
            t = T.get(s["tx"])
            if t and t["from"] == SNIPER and s["a0"] < 0: sz.append(-s["a0"] / 1e18)
    print(f[:60], "pools", len(ps), "sniper buys", len(sz), "eth min/max", (min(sz), max(sz)) if sz else None)
