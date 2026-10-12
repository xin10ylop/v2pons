"""Stage 3: full blocks [T-12, T+3] and block receipts [T-6, T] of every pool with a bot buy (both slices). usage: s3_blocks.py <slice>"""
import sys, pickle
from lib import *
name = sys.argv[1]; D = pickle.load(open(f"parsed_{name}.pkl", "rb")); P = [p for p in D["pools"] if p["T"] is not None]
kb, kr = KV("blk"), KV("rcp")
nums = sorted(set(n for p in P for n in range(p["Tbn"] - 12, p["Tbn"] + 4)))
rn = sorted(set(n for p in P for n in range(p["Tbn"] - 6, p["Tbn"] + 1)))
print(f"{name}: pools {len(P)}; full blocks {len(nums)}; receipts {len(rn)}", flush=True)
get_blocks(nums, kb); get_receipts(rn, kr)
print("missing blocks", sum(1 for n in nums if str(n) not in kb.d), "missing receipts", sum(1 for n in rn if str(n) not in kr.d))
