"""Step 3: every token minted to the volume-bot router 0x1cbaf24d (Transfer from 0 to the router, any token) from Oct 12 00:00 to the s01 head.
These are the operator's token deploys (7422a284). Output s03_botmints_cache.jsonl."""
from common import *
meta = jload("s01_meta.json"); start, head = meta["start"], meta["head"]
rows = jl_load("s03_botmints_cache.jsonl"); last = max([r["_to"] for r in rows if "_to" in r] or [start - 1])
BOTT = "0x" + "0" * 24 + BOT[2:]
for a in range(last + 1, head + 1, 50000):
    b = min(a + 49999, head)
    ls = rpc.logs({"topics": [T_TRANSFER, ZERO32, BOTT]}, a, b)
    jl_append([dict(b=int(l["blockNumber"], 16), tok=l["address"].lower(), h=l["transactionHash"], amt=str(int(l["data"], 16) if l["data"] != "0x" else 0)) for l in ls] + [{"_to": b}], "s03_botmints_cache.jsonl")
    print(b, len(ls), rpc.STATS, flush=True)
