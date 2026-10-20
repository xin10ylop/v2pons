"""check the full-range constant-product model of the migration pools against every recorded swap (census events): predicted output from
the previous sqrtPrice and L vs the Swap event's output (pool-level amounts, before the hook's fee)."""
import json, statistics as st
from kv4 import V4, Q96
M = {m["pool"]: m for m in json.load(open("../out/k13_mig_pools.json"))}
E = json.load(open("../data/mig_pool_events.json"))
err = []
for pid, ev in E.items():
    v = V4(M[pid], ev)
    if not v.full_range_only: continue
    sp = M[pid]["sqrt_p0"]; L = v.L
    for e in ev:
        if e[0] != "s": continue
        a0, a1 = e[6], e[7]; X = L * Q96 / sp; Y = L * sp / Q96
        if a0 < 0:   # ETH in, token out
            pred = Y * (-a0) / (X - a0); act = a1
        else:        # token in, ETH out
            pred = X * (-a1) / (Y - a1); act = a0
        if act > 10**9: err.append(abs(pred - act) / act)
        sp = e[8]
print("swaps checked", len(err), "median rel err", st.median(err), "p99", sorted(err)[int(len(err) * .99)])
json.dump({"n": len(err), "median_rel_err": st.median(err), "p99": sorted(err)[int(len(err) * .99)]}, open("../out/k37_v4check.json", "w"))
