"""every Swap / ModifyLiquidity of the 20 assigned pools + all 35 launches through 0x815542e8 (openlaunch.lol), from launch to the chain head
(beyond the census's 3,000-block window): is the liquidity ever pulled, is there any later trading? (adapted from analyse_19/postwindow.py)
100k-block eth_getLogs chunks, one topic filter with all pool ids; cached to postwindow_logs.json"""
import sys, os, json, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10"); sys.path.insert(0, HERE)
from chain import rpc, logs, PM, T_SWAP, T_ML, W, sgn
from common24 import load_families, load_pools
K = json.load(open(os.path.join(HERE, "keys.json"))); F = load_families(); P = load_pools()
L1 = "0x815542e8b392389a1389e22e588e4b62a67ade72"
pids = sorted(set([x for k in K for x in F[k]["pids"]] + [p["pid"] for p in P.values() if p["launch_to"] == L1]), key=lambda x: P[x]["launch_block"])
cache = os.path.join(HERE, "postwindow_logs.json")
if os.path.exists(cache):
    D = json.load(open(cache))
else:
    head = int(rpc("eth_blockNumber", []), 16); a0 = min(P[x]["launch_block"] for x in pids)
    L = []
    for a in range(a0, head + 1, 100_000):
        for i in range(0, len(pids), 25):
            L += logs({"address": PM, "topics": [[T_SWAP, T_ML], pids[i:i + 25]]}, a, min(a + 99_999, head))
    D = {"head": head, "from": a0, "logs": L}; json.dump(D, open(cache, "w"))
by = collections.defaultdict(list)
for l in D["logs"]: by[l["topics"][1]].append(l)
res = {"head": D["head"], "pools": {}}
for x in pids:
    lb = P[x]["launch_block"]; ev = []
    for l in sorted(by[x], key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16))):
        bn = int(l["blockNumber"], 16) - lb
        if l["topics"][0] == T_SWAP:
            a0 = sgn(W(l["data"], 0)); a0 = a0 - (1 << 256) if a0 >= (1 << 255) else a0
            ev.append(["swap", bn, round(-a0 / 1e18, 9)])
        else:
            ev.append(["ml", bn, sgn(W(l["data"], 2))])
    res["pools"][x] = {"family": P[x]["family"], "launch_to": P[x]["launch_to"], "launch_block": lb, "blocks_to_head": D["head"] - lb, "events": ev,
                       "pulls": sum(1 for e in ev if e[0] == "ml" and e[2] < 0), "swaps": sum(1 for e in ev if e[0] == "swap"),
                       "swaps_after_3000": sum(1 for e in ev if e[0] == "swap" and e[1] > 3000),
                       "buy_eth_after_3000": round(sum(e[2] for e in ev if e[0] == "swap" and e[1] > 3000 and e[2] > 0), 6)}
groups = [(k, F[k]["pids"]) for k in K] + [("F1-LAUNCHER 0x815542e8 (35)", [x for x in pids if P[x]["launch_to"] == L1])]
summ = {}
for k, g in groups:
    ps = [res["pools"][x] for x in g]
    summ[k] = {"pools": len(ps), "blocks_to_head_min_max": [min(p["blocks_to_head"] for p in ps), max(p["blocks_to_head"] for p in ps)],
               "pulls_ever": sum(p["pulls"] for p in ps), "pools_pulled_ever": sum(1 for p in ps if p["pulls"]), "swaps_ever": sum(p["swaps"] for p in ps),
               "swaps_after_3000": sum(p["swaps_after_3000"] for p in ps), "buy_eth_after_3000": round(sum(p["buy_eth_after_3000"] for p in ps), 6)}
    print(k[:70], summ[k])
    for p in ps:
        if p["swaps_after_3000"] or p["pulls"]: print("   ", p["events"][:30])
res["summary"] = summ
json.dump(res, open(os.path.join(HERE, "postwindow.json"), "w"), indent=1)
