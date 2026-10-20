"""Fetch every swap tx the census lacks in [trigger, trigger + 100] of all 573 triggered C-1 core pools -> appended to sample_txs.json."""
import pickle
from sim import *
import rpc
rows = {r["pool"]: r for r in jl(os.path.join(V, "c1_rows.jsonl")) if r["quote"] == "ETH"}
E = pickle.load(open(os.path.join(V, "ev.pkl"), "rb")); R = pickle.load(open(os.path.join(V, "replay.pkl"), "rb"))
T = json.load(open(os.path.join(V, "c1_txs.json"))); outp = os.path.join(V, "sample_txs.json"); have = json.load(open(outp))
need = set()
for pid, tb in R["trig"].items():
    P = Pool(rows[pid], E[pid])
    for x in P.sw:
        if tb[0] <= x[0] <= tb[0] + 100 and x[8] not in T and x[8] not in have: need.add(x[8])
todo = sorted(need); print("to fetch", len(todo))
res = rpc.batch("eth_getTransactionByHash", [[h] for h in todo])
for h, t in zip(todo, res):
    if t is None: continue
    inp = t["input"]
    have[h] = {"hash": h, "from": t["from"].lower(), "to": (t.get("to") or "").lower(), "value_wei": int(t["value"], 16), "gas": int(t["gas"], 16),
               "gas_price": int(t["gasPrice"], 16), "max_prio": int(t["maxPriorityFeePerGas"], 16) if t.get("maxPriorityFeePerGas") else None,
               "selector": inp[2:10], "calldata_len": (len(inp) - 2) // 2, "input_head": inp[:2 + 8 + 64 * 16]}
json.dump(have, open(outp, "w"))
print("now", len(have), "null", sum(1 for t in res if t is None), rpc.STATS)
