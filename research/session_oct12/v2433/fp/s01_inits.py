"""Every PoolManager Initialize log from Oct 11 18:00 UTC to the head; block timestamps sampled every 2,000 blocks (for hourly buckets).
Outputs: s01_inits_cache.jsonl (raw logs), s01_meta.json (start/head blocks), s01_blocks_cache.jsonl (block -> timestamp samples)."""
import json, time, calendar
from common import R, PM, T_INIT, p, load_jsonl, append_jsonl
T0 = calendar.timegm((2026, 10, 11, 18, 0, 0))
def bts(b): return int(R.call("eth_getBlockByNumber", [hex(b), False])["timestamp"], 16)
head = int(R.call("eth_blockNumber", []), 16); th = bts(head)
try: meta = json.load(open(p("s01_meta.json")))
except Exception: meta = {}
if "start" not in meta:
    lo, hi = 1, head
    while lo < hi:
        mid = (lo + hi) // 2
        if bts(mid) < T0: lo = mid + 1
        else: hi = mid
    meta["start"] = lo
start = meta["start"]; prev_head = meta.get("head", start - 1)
print("start", start, time.strftime("%H:%M:%S", time.gmtime(bts(start))), "head", head, time.strftime("%m-%d %H:%M:%S", time.gmtime(th)), "prev head", prev_head)
n = 0
for a in range(prev_head + 1, head + 1, 20000):
    b = min(a + 19999, head)
    ls = R.logs({"address": PM, "topics": [T_INIT]}, a, b)
    append_jsonl("s01_inits_cache.jsonl", ls); n += len(ls)
print("new Initialize logs", n)
have = {r["b"] for r in load_jsonl("s01_blocks_cache.jsonl")}
want = [b for b in list(range(start, head + 1, 2000)) + [head] if b not in have]
res = R.batch("eth_getBlockByNumber", [[hex(b), False] for b in want])
append_jsonl("s01_blocks_cache.jsonl", [{"b": b, "t": int(x["timestamp"], 16)} for b, x in zip(want, res) if x])
meta["head"] = head; meta["head_t"] = th
json.dump(meta, open(p("s01_meta.json"), "w"))
print("total Initialize logs", len(load_jsonl("s01_inits_cache.jsonl")), "rpc", R.STATS)
