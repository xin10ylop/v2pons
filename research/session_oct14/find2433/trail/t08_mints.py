"""Every Transfer from 0x0 (a mint) on the chain from block 86314100 to the head: token, recipient, block, tx, topic count (3 = ERC-20,
4 = ERC-721). Compact rows in t08_mints_cache.jsonl; chunks done in t08_done_cache.jsonl."""
from common import *
A0 = 86314100
h, th = head()
B = int(sys.argv[1]) if len(sys.argv) > 1 else h
done = {r["a"] for r in jl(J("t08_done_cache.jsonl"))}
with open(J("t08_mints_cache.jsonl"), "a") as f, open(J("t08_done_cache.jsonl"), "a") as fd:
    for s in range(A0, B + 1, 30000):
        if s in done: continue
        e = min(B, s + 29999)
        L = rpc.logs({"topics": [T_TRANSFER, pad(ZERO)]}, s, e)
        for l in L:
            f.write(json.dumps({"b": int(l["blockNumber"], 16), "tx": l["transactionHash"], "tok": l["address"].lower(), "to": unpad(l["topics"][2]) if len(l["topics"]) > 2 else None, "nt": len(l["topics"]), "amt": l["data"][:66] if len(l["topics"]) == 3 else None}) + "\n")
        f.flush(); fd.write(json.dumps({"a": s, "b": e}) + "\n"); fd.flush()
        print(s, e, len(L), rpc.STATS, flush=True)
print("head", h, utc(th), rpc.STATS)
