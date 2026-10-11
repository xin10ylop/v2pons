"""Skeptic 1, stage 3: every transaction of the whole blocks [L+1, T+3] of every current-regime 3.0 pool (launched from 04:22:19 UTC) in the
two slices the finder did not use (oldest: L < 85,728,798, the finder's first pool; newest: L > 86,150,251, its last), full transaction
objects (what the sequencer feed carries), no receipts -> cache/blk.jsonl. With --old also the pre-04:22 regime's pools (T at L+8..+10)."""
import pickle, sys
from lib import *
NEW30 = 1791692539; FIRST_FINDER = 85728798
P = [p for p in pickle.load(open("parsed.pkl", "rb"))["pools"] if p["L"] < FIRST_FINDER] + pickle.load(open("parsed_late.pkl", "rb"))["pools"]
P = [p for p in P if p["T"] is not None and (p["ts"] >= NEW30 or "--old" in sys.argv)]
kb = KV("blk"); kr = None
nums = sorted(set(b for p in P for b in range(p["L"] + 1, p["Tbn"] + 4)))
print("pools", len(P), "blocks", len(nums), "cached", sum(1 for n in nums if str(n) in kb.d), flush=True)
for i in range(0, len(nums), 400):
    get_blocks(nums[i:i + 400], kb, kr, receipts=False)
    print(f"  {min(i + 400, len(nums))}/{len(nums)}", flush=True)
print("missing", sum(1 for n in nums if str(n) not in kb.d))
