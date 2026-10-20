"""RPC check (cached): every Swap / ModifyLiquidity of the 56 pools of the four families from launch to the head, beyond the census's
3,000-block window. ~15 eth_getLogs calls of <= 100k blocks."""
import sys, os, json, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from chain import rpc, logs, PM, T_SWAP, T_ML, W, sgn
from pricer6 import load_pools, load_families
KEYS = ["0x404700be6b535e6aa7fd744f242d8cf78135817c|7fde822e|804|10000|200|true",
        "0xe696daf67fe25c5936187fc1edf38404353d5f72|7fde822e|804|10000|200|true",
        "0xb40382548413c559ad7f0bb6e24410401238eded|7fde822e|804|10000|200|true",
        "0x0000ffffbe8efe702c8703ae3477ff5de3d319c0|ac9650d8|1316|2500|25|true"]
F = load_families(); P = load_pools()
pids = [pid for k in KEYS for pid in F[k]["pids"]]
cache = os.path.join(HERE, "postwindow_logs.json")
if os.path.exists(cache):
    L = json.load(open(cache))
else:
    head = int(rpc("eth_blockNumber", []), 16)
    a = min(P[p]["launch_block"] for p in pids)
    L = {"head": head, "from": a, "logs": []}
    for lo in range(a, head + 1, 100_000):
        hi = min(head, lo + 99_999)
        L["logs"] += logs({"address": PM, "topics": [[T_SWAP, T_ML], pids]}, lo, hi)
        time.sleep(0.3)
    json.dump(L, open(cache, "w"))
out = {"head": L["head"], "from": L["from"], "n_logs": len(L["logs"]), "per_family": {}}
for k in KEYS:
    rows = []
    for pid in F[k]["pids"]:
        b0 = P[pid]["launch_block"]
        ev = [l for l in L["logs"] if l["topics"][1] == pid]
        sw = [(int(l["blockNumber"], 16) - b0, sgn(W(l["data"], 0))) for l in ev if l["topics"][0] == T_SWAP]
        ml = [(int(l["blockNumber"], 16) - b0, sgn(W(l["data"], 2))) for l in ev if l["topics"][0] == T_ML]
        rows.append({"pid": pid, "age_blocks": L["head"] - b0, "swaps": len(sw), "buys": sum(1 for _, a0 in sw if a0 < 0), "buys_ge_0.0002": sum(1 for _, a0 in sw if a0 <= -int(0.0002e18)),
                     "eth_in": sum(-a0 for _, a0 in sw if a0 < 0) / 1e18, "after_3000_swaps": sum(1 for r, _ in sw if r > 3000), "pulls": [r for r, d in ml if d < 0],
                     "adds": [r for r, d in ml if d > 0], "first_swaps": sw[:4]})
    out["per_family"][k] = {"pools": len(rows), "pools_with_pull_ever": sum(1 for r in rows if r["pulls"]), "pools_with_buy_ge_0.0002_ever": sum(1 for r in rows if r["buys_ge_0.0002"]),
                            "pools_with_swaps_after_3000": sum(1 for r in rows if r["after_3000_swaps"]), "total_eth_in": round(sum(r["eth_in"] for r in rows), 6),
                            "age_blocks_min": min(r["age_blocks"] for r in rows), "rows": rows}
json.dump(out, open(os.path.join(HERE, "postwindow.json"), "w"), indent=1)
for k, v in out["per_family"].items():
    print(k, {a: b for a, b in v.items() if a != "rows"})
    for r in v["rows"]:
        if r["swaps"] > 1 or r["pulls"] or len(r["adds"]) > 1: print("   ", r)
