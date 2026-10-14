"""Step 1: every PoolManager Initialize log and every V3 factory PoolCreated log from Oct 12 00:00 UTC to the head (resumable).
Outputs: s01_v4init_cache.jsonl, s01_v3pc_cache.jsonl (raw logs), s01_meta.json (start/head), s01_blocks_cache.jsonl (block->time every 5,000 blocks)."""
import calendar
from common import *
T0 = calendar.timegm((2026, 10, 12, 0, 0, 0))
def bts(b): return int(rpc.call("eth_getBlockByNumber", [hex(b), False])["timestamp"], 16)
head = int(rpc.call("eth_blockNumber", []), 16); th = bts(head)
try: meta = jload("s01_meta.json")
except Exception: meta = {}
if "start" not in meta:
    lo, hi = 86000000, 86400000
    while lo < hi:
        mid = (lo + hi) // 2
        if bts(mid) < T0: lo = mid + 1
        else: hi = mid
    meta["start"] = lo
start = meta["start"]; prev = meta.get("head", start - 1)
print("start", start, hm(bts(start)), "head", head, hm(th), "prev", prev, flush=True)
n4 = n3 = 0
for a in range(prev + 1, head + 1, 25000):
    b = min(a + 24999, head)
    l4 = rpc.logs({"address": PM, "topics": [T_INIT]}, a, b)
    l3 = rpc.logs({"address": V3F, "topics": [T_V3POOL]}, a, b)
    jl_append([dict(b=int(l["blockNumber"], 16), li=int(l["logIndex"], 16), h=l["transactionHash"], t=l["topics"], d=l["data"]) for l in l4], "s01_v4init_cache.jsonl")
    jl_append([dict(b=int(l["blockNumber"], 16), li=int(l["logIndex"], 16), h=l["transactionHash"], t=l["topics"], d=l["data"]) for l in l3], "s01_v3pc_cache.jsonl")
    n4 += len(l4); n3 += len(l3)
    meta["head"] = b; meta["head_t"] = th; jdump(meta, "s01_meta.json")
    print(b, n4, n3, rpc.STATS, flush=True)
have = {r["b"] for r in jl_load("s01_blocks_cache.jsonl")}
want = [b for b in list(range(start, head + 1, 5000)) + [head] if b not in have]
res = rpc.batch("eth_getBlockByNumber", [[hex(b), False] for b in want])
jl_append([{"b": b, "t": int(x["timestamp"], 16)} for b, x in zip(want, res) if x], "s01_blocks_cache.jsonl")
print("v4 inits", len(jl_load("s01_v4init_cache.jsonl")), "v3 pools", len(jl_load("s01_v3pc_cache.jsonl")), rpc.STATS)
