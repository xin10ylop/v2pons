"""after the census' 3,000-block window: every Swap and ModifyLiquidity of the 26 pools of families 1-3 and every ModifyLiquidity of
family 4's 8 pools, from the first launch to the head (eth_getLogs in 100k-block chunks, cached to postwindow_logs.json)"""
import sys, os, json, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from load import *
from chain import rpc, logs, PM, T_SWAP, T_ML, W, sgn
P = load_pools(); F = load_families()
KEYS = json.load(open(os.path.join(HERE, "keys.json")))
CACHE = os.path.join(HERE, "postwindow_logs.json")
pids13 = [p for k in KEYS[:3] for p in F[k]["pids"]]
pids4 = list(F[KEYS[3]]["pids"])
if os.path.exists(CACHE):
    C = json.load(open(CACHE))
else:
    head = int(rpc("eth_blockNumber", []), 16)
    C = {"head": head, "l13": [], "ml4": [], "calls": 0}
    a = min(P[p]["launch_block"] for p in pids13 + pids4)
    for lo in range(a, head + 1, 100_000):
        hi = min(lo + 99_999, head)
        C["l13"] += logs({"address": PM, "topics": [[T_SWAP, T_ML], pids13]}, lo, hi)
        C["ml4"] += logs({"address": PM, "topics": [T_ML, pids4]}, lo, hi)
        C["calls"] += 2; time.sleep(0.2)
    json.dump(C, open(CACHE, "w"))
s128 = lambda x: x - (1 << 128) if x >= (1 << 127) else x
out = {"head": C["head"], "calls": C["calls"], "per_family": {}}
for i, k in enumerate(KEYS):
    pids = set(F[k]["pids"])
    src = C["l13"] if i < 3 else C["ml4"]
    L = [l for l in src if l["topics"][1] in pids]
    ml = [l for l in L if l["topics"][0] == T_ML]
    neg = [l for l in ml if sgn(W(l["data"], 2)) < 0]
    sw = [l for l in L if l["topics"][0] == T_SWAP]
    late = [l for l in sw if int(l["blockNumber"], 16) > P[l["topics"][1]]["launch_block"] + 3000]
    late_buys = sorted(-s128(W(l["data"], 0)) / 1e18 for l in late if s128(W(l["data"], 0)) < 0)
    out["per_family"][k] = {"blocks_after_last_launch_to_head": C["head"] - max(P[p]["launch_block"] for p in pids),
                            "modify_liquidity": len(ml), "pulls_ever": len(neg), "pulled_pools_ever": len(set(l["topics"][1] for l in neg)),
                            "pull_rel": sorted(int(l["blockNumber"], 16) - P[l["topics"][1]]["launch_block"] for l in neg),
                            "swaps_logged": len(sw) if i < 3 else "not fetched (active market)", "swaps_after_window": len(late) if i < 3 else None,
                            "late_buys_eth_top": late_buys[-8:] if i < 3 else None, "late_real_buys": sum(1 for x in late_buys if x >= 0.0002) if i < 3 else None}
json.dump(out, open(os.path.join(HERE, "postwindow.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
