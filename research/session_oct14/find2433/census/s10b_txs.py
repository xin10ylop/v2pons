"""Step 10b: transactions of the buys >= 0.002 ETH in (L, L+30] found by s10 (appended to s06_tx_cache.jsonl with full input)."""
from common import *
need = json.load(open(P("s10_need.json")))
have = {r["h"] for r in jl_load("s06_tx_cache.jsonl")}
want = [h for h in need if h not in have]
for i in range(0, len(want), 200):
    ch = want[i:i + 200]
    res = rpc.batch("eth_getTransactionByHash", [[h] for h in ch], n=25)
    rows = []
    for h, t in zip(ch, res):
        if t is None: rows.append(dict(h=h, miss=1)); continue
        rows.append(dict(h=h, f=t["from"].lower(), to=(t.get("to") or "").lower(), n=int(t["nonce"], 16), v=str(int(t["value"], 16)), s=t["input"][:10],
                         il=(len(t["input"]) - 2) // 2, gp=int(t.get("gasPrice", "0x0"), 16), gas=int(t["gas"], 16), bn=int(t["blockNumber"], 16), ti=int(t["transactionIndex"], 16), **{"in": t["input"]}))
    jl_append(rows, "s06_tx_cache.jsonl")
    print(i + len(ch), "/", len(want), rpc.STATS, flush=True)
