"""Family 3 (launcher 0x6d9ba28f, aa7ec999, hook 0xd7d01126, PoolKey fee 0): read every swap's receipt (8 txs, cached) and the hook's code
size, to see what the hook / launcher keeps of the ETH in (tx value vs the Swap event's a0) and whether the hook emits anything."""
import sys, json, os, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from load import *
from chain import batch, rpc
HERE = os.path.dirname(os.path.abspath(__file__))
K = json.load(open(os.path.join(HERE, "keys.json")))
P = load_pools(); F = load_families(); T = load_txs()
pids = F[K[2]]["pids"]; E = load_events(set(pids))
HOOK = "0xd7d01126cc5ffe6d232e081636fd03c4f438e0cc"; LAUNCHER = "0x6d9ba28f614168f3241b302704ac478850bcbd43"
want = list(dict.fromkeys(s["tx"] for pid in pids for s in E[pid]["swaps"]))
CACHE = os.path.join(HERE, "hookfee_rcpts.json")
R = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
miss = [h for h in want if h not in R]
if miss:
    R.update(zip(miss, batch([("eth_getTransactionReceipt", [h]) for h in miss])))
    R["_code"] = {a: len(rpc("eth_getCode", [a, "latest"])) // 2 - 1 for a in (HOOK, LAUNCHER, "0x65050a9b7e5075a2ba5ced7b1b64ee66262c40dc", "0x294df973b8db52a3a1bb32fe74d4abc9e35fd727")}
    json.dump(R, open(CACHE, "w"))
print("code sizes", R.get("_code"))
out = []
for pid in pids:
    for s in E[pid]["swaps"]:
        r = R.get(s["tx"]); t = T.get(s["tx"])
        if not r: continue
        logs = r["logs"]
        row = {"pid": pid[:12], "rel": s["bn"] - P[pid]["launch_block"], "side": "buy" if s["a0"] < 0 else "sell", "a0": s["a0"], "tx_value": t["value_wei"] if t else None,
               "to": t["to"] if t else None, "from": t["from"] if t else None, "status": r["status"], "gasUsed": int(r["gasUsed"], 16),
               "pool_in_over_value": (-s["a0"] / t["value_wei"]) if (t and t["value_wei"] and s["a0"] < 0) else None,
               "log_addrs": collections.Counter(l["address"][:10] for l in logs).most_common(8),
               "hook_logs": [(l["topics"][0][:10], l["data"][:200]) for l in logs if l["address"].lower() == HOOK]}
        out.append(row); print(row)
json.dump(out, open(os.path.join(HERE, "hookfee.json"), "w"), indent=1)
