"""Attribution sample: 80 random C-1 core pools with a bot trigger (seed 2026). Fetch from the chain every swap tx the census did not
fetch in [trigger, trigger + 162) and every sell tx in [trigger + 162, min(pull, trigger + 400)] -> sample_txs.json (trimmed)."""
import pickle, random
from sim import *
import rpc
rows = {r["pool"]: r for r in jl(os.path.join(V, "c1_rows.jsonl")) if r["quote"] == "ETH"}
E = pickle.load(open(os.path.join(V, "ev.pkl"), "rb")); T = json.load(open(os.path.join(V, "c1_txs.json"))); R = pickle.load(open(os.path.join(V, "replay.pkl"), "rb"))
random.seed(2026)
pids = sorted(R["trig"]); samp = random.sample(pids, 80)
need = []
for pid in samp:
    P = Pool(rows[pid], E[pid]); tb = R["trig"][pid]
    end = P.first_pull if P.first_pull else P.lb + 3000
    for x in P.sw:
        if x[8] in T: continue
        if tb[0] <= x[0] < tb[0] + 162 or (not x[3] and tb[0] + 162 <= x[0] <= min(end, tb[0] + 400)): need.append(x[8])
need = sorted(set(need))
outp = os.path.join(V, "sample_txs.json")
have = json.load(open(outp)) if os.path.exists(outp) else {}
todo = [h for h in need if h not in have]
print("sample pools", len(samp), "txs needed", len(need), "to fetch", len(todo))
res = rpc.batch("eth_getTransactionByHash", [[h] for h in todo])
for h, t in zip(todo, res):
    if t is None: continue
    inp = t["input"]
    have[h] = {"hash": h, "from": t["from"].lower(), "to": (t.get("to") or "").lower(), "value_wei": int(t["value"], 16), "gas": int(t["gas"], 16),
               "gas_price": int(t["gasPrice"], 16), "max_prio": int(t["maxPriorityFeePerGas"], 16) if t.get("maxPriorityFeePerGas") else None,
               "selector": inp[2:10], "calldata_len": (len(inp) - 2) // 2, "input_head": inp[:2 + 8 + 64 * 16]}
json.dump(have, open(outp, "w"))
json.dump(samp, open(os.path.join(V, "sample_pools.json"), "w"))
print("fetched", len(have), "null", sum(1 for t in res if t is None), rpc.STATS)
