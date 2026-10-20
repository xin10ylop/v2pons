"""Every PoolManager Initialize from block 86314100 (Oct 12 02:13 UTC) to the head, compact rows in t04_inits_cache.jsonl
(pid, c0, c1, fee, ts, hooks, sqrtP, tick, b, tx); chunks done in t04_done_cache.jsonl."""
from common import *
A0 = 86314100
h, th = head()
done = {r["a"] for r in jl(J("t04_done_cache.jsonl"))}
with open(J("t04_inits_cache.jsonl"), "a") as f, open(J("t04_done_cache.jsonl"), "a") as fd:
    for s in range(A0, h + 1, 50000):
        if s in done: continue
        e = min(h, s + 49999)
        L = rpc.logs({"address": PM, "topics": [T_INIT]}, s, e)
        for l in L:
            d = l["data"]
            f.write(json.dumps({"pid": l["topics"][1], "c0": unpad(l["topics"][2]), "c1": unpad(l["topics"][3]), "fee": W(d, 0), "ts": sgn(W(d, 1)),
                                "hooks": "0x" + d[2 + 64 * 2 + 24: 2 + 64 * 3], "sqrtP": W(d, 3), "tick": sgn(W(d, 4)), "b": int(l["blockNumber"], 16), "tx": l["transactionHash"]}) + "\n")
        f.flush(); fd.write(json.dumps({"a": s, "b": e}) + "\n"); fd.flush()
        print(s, e, len(L), rpc.STATS, flush=True)
print("head", h, utc(th), rpc.STATS)
