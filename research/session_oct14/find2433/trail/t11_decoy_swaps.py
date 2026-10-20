"""Every v4 Swap since the stop (block 86314100) whose sender (the contract that called the PoolManager) is one of the decoy/fronter
routers (0x65050a9b, 0xfd1b271f) or our relay 0x2abb5653: compact rows in t11_swaps_cache.jsonl (b, tx, pid, sender, amount0, amount1)."""
from common import *
A0 = 86314100
h, th = head()
S = [DECOY_R, FRONT_R2, RELAY]
done = {r["a"] for r in jl(J("t11_done_cache.jsonl"))}
with open(J("t11_swaps_cache.jsonl"), "a") as f, open(J("t11_done_cache.jsonl"), "a") as fd:
    for s in range(A0, h + 1, 50000):
        if s in done: continue
        e = min(h, s + 49999)
        L = rpc.logs({"address": PM, "topics": [T_SWAP, None, [pad(x) for x in S]]}, s, e)
        for l in L:
            f.write(json.dumps({"b": int(l["blockNumber"], 16), "tx": l["transactionHash"], "pid": l["topics"][1], "s": unpad(l["topics"][2]), "a0": str(sgn(W(l["data"], 0))), "a1": str(sgn(W(l["data"], 1)))}) + "\n")
        f.flush(); fd.write(json.dumps({"a": s, "b": e}) + "\n"); fd.flush()
        print(s, e, len(L), rpc.STATS, flush=True)
print("head", h, utc(th), rpc.STATS)
