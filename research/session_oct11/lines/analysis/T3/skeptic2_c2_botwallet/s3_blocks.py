"""Stage 3: every whole block (all transactions, failed ones included, as the sequencer feed shows them) from L-3 to T+3 of every 3.0 pool
with a bot buy launched in the last HOURS (default 6) before the stage-1 head -> cache/blk.jsonl. Usage: python3 s3_blocks.py [HOURS]"""
import pickle, sys, os
from lib import *
os.chdir(HERE)
hours = float(sys.argv[1]) if len(sys.argv) > 1 else 6
D = pickle.load(open("s2_parsed.pkl", "rb")); lo = D["head"] - int(hours * 3600 * D["bps"])
P = [p for p in D["pools"] if p["L"] >= lo and p["T"] is not None]
kb = KV("blk"); kr = KV("rcp_unused")
nums = sorted(set(b for p in P for b in range(p["L"] - 3, p["Tbn"] + 4)))
print(f"pools {len(P)} (L >= {lo}), blocks {len(nums)}, cached {sum(1 for n in nums if str(n) in kb.d)}", flush=True)
for i in range(0, len(nums), 500):
    get_blocks(nums[i:i + 500], kb, kr, receipts=False)
    print(f"  {min(i + 500, len(nums))}/{len(nums)} blocks cached {len(kb.d)}", flush=True)
print("missing:", [n for n in nums if str(n) not in kb.d][:20])
