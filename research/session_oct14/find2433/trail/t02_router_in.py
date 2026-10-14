"""Every ERC-20 Transfer INTO the bot router 0x1cbaf24d since the 2.433 stop (block 86314100, Oct 12 02:13 UTC) to the head:
from 0x0 = a token minted to the router (a 7422a284 deploy), from the PoolManager = a bot buy. Compact rows in t02_in_cache.jsonl
(b, tx, token, from, amount); chunks done in t02_done_cache.jsonl so the scan resumes."""
from common import *
A0 = 86314100
h, th = head()
B = int(sys.argv[1]) if len(sys.argv) > 1 else h
done = {r["a"] for r in jl(J("t02_done_cache.jsonl"))}
n = 0
with open(J("t02_in_cache.jsonl"), "a") as f, open(J("t02_done_cache.jsonl"), "a") as fd:
    for s in range(A0, B + 1, 30000):
        if s in done: continue
        e = min(B, s + 29999)
        L = rpc.logs({"topics": [T_TRANSFER, None, pad(BOT)]}, s, e)
        for l in L:
            if len(l["topics"]) != 3: continue
            f.write(json.dumps({"b": int(l["blockNumber"], 16), "tx": l["transactionHash"], "tok": l["address"].lower(), "fr": unpad(l["topics"][1]), "amt": str(int(l["data"], 16) if l["data"] != "0x" else 0)}) + "\n")
            n += 1
        f.flush(); fd.write(json.dumps({"a": s, "b": e}) + "\n"); fd.flush()
        print(s, e, len(L), rpc.STATS, flush=True)
print("rows", n, "head", h, utc(th), rpc.STATS)
