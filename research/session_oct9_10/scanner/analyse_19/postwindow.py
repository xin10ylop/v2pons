"""every Swap / ModifyLiquidity of the 22 assigned pools (analyse_19; adapted from analyse_18/postwindow.py) from launch to the chain head (beyond the census's 3,000-block window): are they
# analyse_19 copy: same logic, keys.json of analyse_19
ever pulled or traded later? 100k-block eth_getLogs chunks, one topic filter with all 24 pool ids; cached to postwindow_logs.json"""
import sys, os, json, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10"); sys.path.insert(0, HERE)
from chain import rpc, logs, PM, T_SWAP, T_ML, W, sgn
from common19 import load_families, load_pools
K = json.load(open(os.path.join(HERE, "keys.json"))); F = load_families(); P = load_pools()
pids = [x for k in K for x in F[k]["pids"]]
cache = os.path.join(HERE, "postwindow_logs.json")
if os.path.exists(cache):
    D = json.load(open(cache))
else:
    head = int(rpc("eth_blockNumber", []), 16); a0 = min(P[x]["launch_block"] for x in pids)
    L = []
    for a in range(a0, head + 1, 100_000):
        L += logs({"address": PM, "topics": [[T_SWAP, T_ML], pids]}, a, min(a + 99_999, head))
    D = {"head": head, "from": a0, "logs": L}; json.dump(D, open(cache, "w"))
by = collections.defaultdict(list)
for l in D["logs"]: by[l["topics"][1]].append(l)
res = {"head": D["head"], "pools": {}}
for k in K:
    for x in F[k]["pids"]:
        lb = P[x]["launch_block"]; ev = []
        for l in sorted(by[x], key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16))):
            bn = int(l["blockNumber"], 16) - lb
            if l["topics"][0] == T_SWAP:
                a0 = sgn(W(l["data"], 0)); a0 = a0 - (1 << 256) if a0 >= (1 << 255) else a0
                ev.append(["swap", bn, round(-a0 / 1e18, 9)])
            else:
                ev.append(["ml", bn, sgn(W(l["data"], 2))])
        res["pools"][x] = {"family": k, "launch_block": lb, "blocks_to_head": D["head"] - lb, "events": ev,
                           "pulls": sum(1 for e in ev if e[0] == "ml" and e[2] < 0), "swaps": sum(1 for e in ev if e[0] == "swap"),
                           "swaps_after_3000": sum(1 for e in ev if e[0] == "swap" and e[1] > 3000)}
for k in K:
    ps = [res["pools"][x] for x in F[k]["pids"]]
    print(k[:60], "pools", len(ps), "blocks to head", min(p["blocks_to_head"] for p in ps), "-", max(p["blocks_to_head"] for p in ps),
          "pulls ever", sum(p["pulls"] for p in ps), "swaps ever", sum(p["swaps"] for p in ps), "after +3000", sum(p["swaps_after_3000"] for p in ps))
    for p in ps:
        if p["swaps_after_3000"] or p["pulls"]: print("   ", p["events"])
json.dump(res, open(os.path.join(HERE, "postwindow.json"), "w"), indent=1)
