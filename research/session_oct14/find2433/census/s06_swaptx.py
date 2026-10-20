"""Step 6: the transaction behind every swap in [L, L+EARLY] and every ModifyLiquidity (any time) of the s05 pools, plus the swaps
up to the first pull if it comes later (resumable). Keeps from, to, nonce, value, selector, calldata length, gas price, and the full input for
early swaps (minOut decoding). Output s06_tx_cache.jsonl."""
import sys
from common import *
EARLY = int(sys.argv[1]) if len(sys.argv) > 1 else 80
ev = jl_load("s05_events_cache.jsonl")
early, other = set(), set()
for p in ev:
    for s in p["sw"]:
        if s[0] <= p["L"] + EARLY: early.add(s[3])
    for m in p["ml"]: other.add(m[3])
have = {r["h"] for r in jl_load("s06_tx_cache.jsonl")}
want = sorted((early | other) - have, key=lambda h: (h not in early, h))
print("early", len(early), "ml", len(other), "need", len(want), flush=True)
for i in range(0, len(want), 200):
    ch = want[i:i + 200]
    res = rpc.batch("eth_getTransactionByHash", [[h] for h in ch], n=25)
    rows = []
    for h, t in zip(ch, res):
        if t is None: rows.append(dict(h=h, miss=1)); continue
        r = dict(h=h, f=t["from"].lower(), to=(t.get("to") or "").lower(), n=int(t["nonce"], 16), v=str(int(t["value"], 16)), s=t["input"][:10],
                 il=(len(t["input"]) - 2) // 2, gp=int(t.get("gasPrice", "0x0"), 16), gas=int(t["gas"], 16), bn=int(t["blockNumber"], 16), ti=int(t["transactionIndex"], 16))
        if h in early: r["in"] = t["input"]
        rows.append(r)
    jl_append(rows, "s06_tx_cache.jsonl")
    print(i + len(ch), "/", len(want), rpc.STATS, flush=True)
