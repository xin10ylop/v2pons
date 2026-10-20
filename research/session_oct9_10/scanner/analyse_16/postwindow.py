"""every Swap / ModifyLiquidity of the 26 pools of my four families from their launch to the chain head (beyond the census's 3,000-block
window): did anyone ever trade them, did anyone ever pull? eth_getLogs on the PoolManager, 100k-block ranges, cached to postwindow_logs.json"""
import sys, json, os, collections
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from chain import rpc, logs, PM, T_SWAP, T_ML, W, sgn
from load import load_families, load_pools
OUT = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/analyse_16"
K = json.load(open(OUT + "/keys.json")); F = load_families(); P = load_pools()
pids = [x for k in K for x in F[k]["pids"]]
cache = OUT + "/postwindow_logs.json"
if os.path.exists(cache):
    D = json.load(open(cache))
else:
    head = int(rpc("eth_blockNumber", []), 16)
    a = min(P[x]["launch_block"] for x in pids)
    L = []
    for lo in range(a, head + 1, 100_000):
        hi = min(head, lo + 99_999)
        L += logs({"address": PM, "topics": [[T_SWAP, T_ML], pids]}, lo, hi)
    D = {"head": head, "from": a, "logs": L}
    json.dump(D, open(cache, "w"))
by = collections.defaultdict(lambda: {"swaps": [], "ml": []})
for l in D["logs"]:
    pid = l["topics"][1]; bn = int(l["blockNumber"], 16)
    if l["topics"][0] == T_SWAP:
        a0 = sgn(W(l["data"], 0)); a0 = a0 - (1 << 128) if a0 >= (1 << 127) else a0
        a0 = sgn(W(l["data"], 0))
        by[pid]["swaps"].append((bn - P[pid]["launch_block"], -a0 / 1e18, l["transactionHash"]))
    else:
        by[pid]["ml"].append((bn - P[pid]["launch_block"], sgn(W(l["data"], 2)), l["transactionHash"]))
res = {"head": D["head"], "n_logs": len(D["logs"]), "pools": {}}
tot_pull = 0; tot_late_swaps = 0
for k in K:
    print(k)
    for pid in F[k]["pids"]:
        b = by[pid]; pulls = [m for m in b["ml"] if m[1] < 0]; late = [s for s in b["swaps"] if s[0] > 3000]
        tot_pull += len(pulls); tot_late_swaps += len(late)
        res["pools"][pid] = {"swaps": b["swaps"], "pulls": pulls, "adds": [m for m in b["ml"] if m[1] > 0], "blocks_to_head": D["head"] - P[pid]["launch_block"]}
        print("  %s swaps %d (after +3000: %d %s) adds %d pulls %d  blocks to head %d" % (pid[:12], len(b["swaps"]), len(late), [(s[0], round(s[1], 6)) for s in late][:4],
              len([m for m in b["ml"] if m[1] > 0]), len(pulls), D["head"] - P[pid]["launch_block"]))
res["total_pulls_ever"] = tot_pull; res["total_swaps_after_window"] = tot_late_swaps
print("head", D["head"], "logs", len(D["logs"]), "pulls ever", tot_pull, "swaps after +3000", tot_late_swaps)
json.dump(res, open(OUT + "/postwindow.json", "w"), indent=1)
