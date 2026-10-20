import sys, json
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import *
L = json.load(open("launcher_logs.json"))
hs = [x["transactionHash"] for x in L]
res = {}
try: res = json.load(open("launcher_txs.json"))
except Exception: pass
todo = [h for h in hs if h not in res]
for i in range(0, len(todo), 50):
    ch = todo[i:i+50]
    r = batch([("eth_getTransactionByHash", [h]) for h in ch])
    for h, t in zip(ch, r):
        if t: res[h] = {"from": t["from"].lower(), "nonce": int(t["nonce"], 16), "to": (t.get("to") or "").lower(), "value": int(t["value"], 16), "input": t["input"], "bn": int(t["blockNumber"], 16),
                        "gas": int(t["gas"], 16), "type": t.get("type"), "tip": t.get("maxPriorityFeePerGas"), "maxfee": t.get("maxFeePerGas"), "gasPrice": t.get("gasPrice")}
    if i % 1000 == 0: print(i, len(res), flush=True); json.dump(res, open("launcher_txs.json", "w"))
json.dump(res, open("launcher_txs.json", "w")); print("done", len(res))
