"""Step 12b: transactions of the swaps in (L+80, L+400] of the 2020 B hooked family (to name the buyer swarm). Appends to s06_tx_cache.jsonl."""
from common import *
import s07_traits as S
fam = "K1 v4 0x58daec31 0xac9650d8 2020B f3000 ts60 v0 ETH hooked"
pids = [t["pid"] for t in jload("s05_targets.json") if t["fam"] == fam]
want = []
for pid in pids:
    p = S.EV[pid]; L = S.rows[pid]["b"]
    want += [s[3] for s in p["sw"] if L + 80 < s[0] <= L + 400]
want = sorted(set(want) - set(S.TX))
print("need", len(want), flush=True)
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
