"""Stage 1b: the txs of every swap of the slice's 3.0 pools to L+400 (stage 1 took them to L+150), so outside buys after T are classified too."""
import json
from lib import *
S = json.load(open("s1_slice.json")); kv_tx = KV("tx")
need = [e["tx"] for p in S["pools"] for e in p["ev"] if e["tx"] not in kv_tx.d]
need = list(dict.fromkeys(need)); print("txs to fetch:", len(need), flush=True)
for i in range(0, len(need), 400):
    ch = need[i:i + 400]; res = batch([("eth_getTransactionByHash", [h]) for h in ch], 20)
    for h, t in zip(ch, res):
        if t: kv_tx.put(h, {k: t.get(k) for k in SLIM_TX})
    kv_tx.flush(); print(f"  txs {i + len(ch)}/{len(need)}", flush=True)
for p in S["pools"]:
    for e in p["ev"]:
        if e["tx"] in kv_tx.d: S["txs"][e["tx"]] = kv_tx.d[e["tx"]]
print("missing after:", sum(1 for p in S["pools"] for e in p["ev"] if e["tx"] not in S["txs"]))
json.dump(S, open("s1_slice.json", "w"))
