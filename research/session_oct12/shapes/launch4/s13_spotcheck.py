"""Spot check of the grouped log queries: 6 pools (S1 x2, S2, S3, S4, the S2 runner) re-queried one at a time, every Swap/ModifyLiquidity from the
launch to +600; the counts must equal those in s04_pools.json. Prints s13_spotcheck.out."""
from common import *
import rpc, random
D = json.load(open(J("s04_pools.json"))); P = D["pools"]
random.seed(12)
core = lambda p: p["shape"] != "S1" or p["n"] == 4324
pick = random.sample([p for p in P if p["shape"] == "S1" and core(p)], 2) + [random.choice([p for p in P if p["shape"] == s]) for s in ("S2", "S3", "S4")]
pick += [p for p in P if p["pid"].startswith("0xc1ffeb85")]
for p in pick:
    ev = rpc.logs({"address": PM, "topics": [[T_SWAP, T_ML], p["pid"]]}, p["lb"], p["lb"] + 600)
    ns = sum(1 for l in ev if l["topics"][0] == T_SWAP); nm = len(ev) - ns
    print(f"{p['shape']} {p['pid'][:12]}: single query swaps {ns} ML {nm}; grouped swaps {sum(1 for w in p['sw'] if w['off'] <= 600)} ML {sum(1 for m in p['ml'] if m['off'] <= 600)}")
print(rpc.STATS)
