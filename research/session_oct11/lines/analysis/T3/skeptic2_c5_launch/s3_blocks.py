"""Stage 3: the whole blocks L..T+4 of every 3.0 pool of the slice (every tx, so a 1,444-byte PositionManager call that reverted or did not
initialise a pool is seen too, as the sequencer feed would show it); receipts for the blocks holding a 1,444-byte PositionManager call that is
not one of the slice's Initialize txs (to read its status) -> cache/blocks.jsonl, cache/rcpts.jsonl; summary in s3_blocks.out."""
import json, collections
from lib import *
P = json.load(open("s2_parsed.json"))["pools"]; S = json.load(open("s1_slice.json"))
init_tx = {r["tx"] for r in S["launches"]}
kv_b = KV("blocks"); kv_r = KV("rcpts")
nums = sorted({b for p in P for b in range(p["L"], p["Tbn"] + 5)})
print("blocks to cover:", len(nums), "cached:", sum(1 for n in nums if str(n) in kv_b.d), flush=True)
get_blocks(nums, kv_b, kv_r, receipts=False)
odd = []
for n in nums:
    b = kv_b.d.get(str(n))
    if b is None: print("missing block", n); continue
    for t in b["txs"]:
        if (t["to"] or "").lower() == POSM and (len(t["input"]) - 2) // 2 == 1444 and t["hash"] not in init_tx: odd.append((n, t["hash"]))
print("1444-byte PositionManager calls in the windows that are not slice Initialize txs:", len(odd), flush=True)
get_blocks(sorted({n for n, _ in odd}), kv_b, kv_r, receipts=True)
for n, h in odd:
    r = next((x for x in kv_r.d.get(str(n), []) if x["tx"] == h), None)
    print("  ", n, h[:12], "status", r and r["status"], "logs", r and len(r["logs"]))
ntx = [len(kv_b.d[str(n)]["txs"]) for n in nums if str(n) in kv_b.d]
print("txs per block in the windows: mean %.2f, p50 %s, p90 %s, max %s" % (sum(ntx) / len(ntx), pct(ntx, .5), pct(ntx, .9), max(ntx)))
