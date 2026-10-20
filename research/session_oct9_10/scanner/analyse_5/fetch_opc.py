"""fetch the transactions of every swap and pull in the opC pools (fee 100 and 500 families) that the census did not keep (it kept the first
8 swaps and the first 2 pulls): ~5 batched POSTs. Cache: opc_txs.json"""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10"); sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from chain import batch
from load import *
F = load_families(); T = load_txs()
keys = ["0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|100|1|true", "0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|500|10|true"]
pids = [pid for k in keys for pid in F[k]["pids"]]
E = load_events(set(pids))
cache_f = os.path.join(HERE, "opc_txs.json")
cache = json.load(open(cache_f)) if os.path.exists(cache_f) else {}
need = sorted({x["tx"] for pid in pids for x in E[pid]["swaps"] + E[pid]["pulls"] if x["tx"] not in T and x["tx"] not in cache})
print("need", len(need))
res = batch([("eth_getTransactionByHash", [h]) for h in need])
for h, t in zip(need, res):
    if t: cache[h] = {"hash": h, "from": t["from"].lower(), "to": (t["to"] or "").lower() or None, "nonce": int(t["nonce"], 16), "value_wei": int(t["value"], 16),
                      "selector": t["input"][2:10], "calldata_len": (len(t["input"]) - 2) // 2, "input": t["input"] if len(t["input"]) < 4098 else None, "bn": int(t["blockNumber"], 16)}
json.dump(cache, open(cache_f, "w"))
print("cached", len(cache), "missing", sum(1 for h in need if h not in cache))
