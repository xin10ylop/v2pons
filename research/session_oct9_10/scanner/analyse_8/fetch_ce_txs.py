# fetch the transactions of every swap and pull of the ce5494bb family's 11 pools that the census did not fetch (beyond the first 8 swaps)
import sys, json, os
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/analyse_8")
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from common8 import *
from chain import batch
P = load_pools(); T = load_txs(); F = load_families()
k = "0x05d552391067389ee44fec3924157ed33f976000|ce5494bb|36|10000|200|true"
pids = F[k]["pids"]; E = load_events(set(pids))
need = []
for pid in pids:
    for x in E[pid]["swaps"] + E[pid]["pulls"]:
        if x["tx"] not in T: need.append(x["tx"])
need = sorted(set(need))
path = "cache/ce_txs.json"
have = json.load(open(path)) if os.path.exists(path) else {}
need = [h for h in need if h not in have]
print("need", len(need))
for i in range(0, len(need), 50):
    ch = need[i:i + 50]
    r = batch([("eth_getTransactionByHash", [h]) for h in ch])
    for h, t in zip(ch, r):
        if t: have[h] = {"hash": h, "from": t["from"].lower(), "to": (t.get("to") or "").lower(), "nonce": int(t["nonce"], 16), "bn": int(t["blockNumber"], 16),
                         "ti": int(t["transactionIndex"], 16), "selector": t["input"][2:10], "calldata_len": (len(t["input"]) - 2) // 2, "value_wei": int(t["value"], 16),
                         "max_prio": int(t["maxPriorityFeePerGas"], 16) if t.get("maxPriorityFeePerGas") else None, "input": t["input"] if len(t["input"]) < 4200 else t["input"][:1026]}
    json.dump(have, open(path, "w"))
    print(i, len(have))
