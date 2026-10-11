"""Stage 3: whole blocks (every transaction) and their receipts (every log) of every 3.0 pool with a bot buy: first [T-12, T+3] for every pool
(the precursor window), then the rest of [L-3, T+3] -> cache/blk.jsonl, cache/rcp.jsonl."""
import pickle, sys, collections
from lib import *
D = pickle.load(open("parsed.pkl", "rb"))
P = [p for p in D["pools"] if p["line"] == "3.0" and p["T"] is not None]
kb = KV("blk"); kr = KV("rcp")
class KV0:            # a view of the block cache that reports every block as present (receipts-only pass)
    class _All:
        def __contains__(self, k): return True
    def __init__(self, kv): self.d = KV0._All(); self.kv = kv
    def put(self, k, v): self.kv.put(k, v)
    def flush(self): self.kv.flush()
near = sorted(set(b for p in P for b in range(max(p["L"] - 3, p["Tbn"] - 12), p["Tbn"] + 4)))
rest = sorted(set(b for p in P for b in range(p["L"] - 3, p["Tbn"] + 4)) - set(near))
print("pools", len(P), "blocks near T", len(near), "rest", len(rest), flush=True)
for name, nums, rc in (("near blocks", near, False), ("near receipts", near, True), ("rest blocks", rest, False), ("rest receipts", rest, True)):
    for i in range(0, len(nums), 500):
        if rc: get_blocks(nums[i:i + 500], KV0(kb), kr)
        else: get_blocks(nums[i:i + 500], kb, kr, receipts=False)
        print(f"  {name} {min(i + 500, len(nums))}/{len(nums)} blocks {len(kb.d)} receipts {len(kr.d)}", flush=True)
