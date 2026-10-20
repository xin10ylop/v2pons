"""Stage 3: whole blocks (every transaction, as the sequencer feed shows them; no receipts needed: the feed carries reverted txs too) of
every 3.0 pool, blocks [L+1, T+3] (pools with no bot buy: [L+1, L+70]) -> cache/blk.jsonl. Used (a) to find every 1,444-byte PositionManager call near T,
Initialize-bearing or not, and (b) for the engine replay's armed window."""
import pickle
from lib import *
D = pickle.load(open("parsed.pkl", "rb"))
P = D["pools"]
kb = KV("blk"); kr = None
nums = sorted(set(b for p in P for b in range(p["L"] + 1, (p["Tbn"] + 4) if p["Tbn"] is not None else p["L"] + 71)))
print("pools", len(P), "blocks", len(nums), "cached", sum(1 for n in nums if str(n) in kb.d), flush=True)
for i in range(0, len(nums), 500):
    get_blocks(nums[i:i + 500], kb, kr, receipts=False)
    print(f"  blocks {min(i + 500, len(nums))}/{len(nums)} cached {len(kb.d)}", flush=True)
