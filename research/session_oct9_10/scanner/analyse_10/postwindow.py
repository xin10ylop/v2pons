"""after the census' 3,000-block window: every ModifyLiquidity of the 36 pools, and every Swap of the 27 pools outside family 2,
from each family's first launch to the head (eth_getLogs in 100k-block chunks, cached)"""
import sys, os, json
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from load import *
from chain import rpc, logs, PM, T_SWAP, T_ML, W, sgn
P = load_pools(); F = load_families()
KEYS = json.load(open("keys.json"))
CACHE = "postwindow_logs.json"
if os.path.exists(CACHE):
    C = json.load(open(CACHE))
else:
    head = int(rpc("eth_blockNumber", []), 16)
    C = {"head": head, "ml": [], "swap": []}
    pids_all = [p for k in KEYS for p in F[k]["pids"]]
    pids_sw = [p for k in KEYS if not k.startswith("0x2a53386d") for p in F[k]["pids"]]
    a = min(P[p]["launch_block"] for p in pids_all)
    for lo in range(a, head + 1, 100_000):
        hi = min(lo + 99_999, head)
        C["ml"] += logs({"address": PM, "topics": [T_ML, pids_all]}, lo, hi)
        C["swap"] += logs({"address": PM, "topics": [T_SWAP, pids_sw]}, lo, hi)
    json.dump(C, open(CACHE, "w"))
out = {"head": C["head"], "per_family": {}}
for k in KEYS:
    pids = set(F[k]["pids"])
    ml = [l for l in C["ml"] if l["topics"][1] in pids]
    neg = [l for l in ml if sgn(W(l["data"], 2)) < 0]
    sw = [l for l in C["swap"] if l["topics"][1] in pids]
    late_sw = [l for l in sw if int(l["blockNumber"], 16) > P[l["topics"][1]]["launch_block"] + 3000]
    buys = [l for l in late_sw if sgn(W(l["data"], 0)) >= (1 << 127) or (W(l["data"], 0) >> 127) & 1]
    def s128(x): return x - (1 << 128) if x >= (1 << 127) else x
    late_buys_eth = sorted(-s128(W(l["data"], 0) & ((1 << 128) - 1)) / 1e18 for l in late_sw if s128(W(l["data"], 0) & ((1 << 128) - 1)) < 0)
    out["per_family"][k] = {"modify_liquidity": len(ml), "pulls_ever": len(neg), "pulled_pools_ever": len(set(l["topics"][1] for l in neg)),
                            "pull_rel": sorted(int(l["blockNumber"], 16) - P[l["topics"][1]]["launch_block"] for l in neg),
                            "swaps_logged": len(sw) if not k.startswith("0x2a53386d") else "not fetched (active market)",
                            "swaps_after_window": len(late_sw), "late_buys_eth": late_buys_eth[-10:], "late_real_buys": sum(1 for x in late_buys_eth if x >= 0.0002)}
json.dump(out, open("postwindow.json", "w"), indent=1)
print(json.dumps(out, indent=1))
