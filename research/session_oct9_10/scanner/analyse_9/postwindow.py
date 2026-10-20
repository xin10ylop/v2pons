import sys, json, os, collections
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10"); sys.path.insert(0, ".")
from chain import rpc, logs, T_SWAP, T_ML, PM, W, sgn
from common9 import load_families, load_pools
FK = json.load(open("families_in.json"))
F = load_families(); P = load_pools()
cf = "cache/postwindow_logs.json"
cache = json.load(open(cf)) if os.path.exists(cf) else {}
head = int(rpc("eth_blockNumber", []), 16)
out = {"head": head}
for k in FK:
    pids = F[k]["pids"]
    if k not in cache:
        a = min(P[p]["launch_block"] for p in pids) + 3001; L = []
        for s in range(a, head + 1, 100_000):
            L += logs({"address": PM, "topics": [[T_SWAP, T_ML], pids]}, s, min(s + 99_999, head))
        cache[k] = L; json.dump(cache, open(cf, "w"))
    L = [l for l in cache[k] if int(l["blockNumber"], 16) > P[l["topics"][1]]["launch_block"] + 3000]
    per = collections.defaultdict(lambda: {"swaps": 0, "buys": 0, "buy_eth": 0, "pulls": 0, "first_rel": None})
    for l in L:
        pid = l["topics"][1]; r = per[pid]; rel = int(l["blockNumber"], 16) - P[pid]["launch_block"]
        if r["first_rel"] is None: r["first_rel"] = rel
        if l["topics"][0] == T_SWAP:
            a0 = sgn(W(l["data"], 0)); a0 = a0 - (1 << 128) if a0 >= (1 << 127) else a0
            r["swaps"] += 1
            if a0 < 0: r["buys"] += 1; r["buy_eth"] += -a0 / 1e18
        elif sgn(W(l["data"], 2)) < 0: r["pulls"] += 1
    out[k] = {"logs": len(L), "pools_with_activity": len(per), "per_pool": dict(per)}
    print(k, len(L), dict(per))
json.dump(out, open("postwindow.json", "w"), indent=1)
