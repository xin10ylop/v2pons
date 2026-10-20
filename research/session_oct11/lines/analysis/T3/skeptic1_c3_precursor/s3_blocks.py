"""Stage 3: whole blocks (every transaction) and their block receipts (every log) for
  cur  - the current-regime 3.0 pools of the mid slice (first one L 85,553,521 = 10-11 04:22 UTC .. 85,734,702 = 09:38 UTC; the precursor
         finder's pools start at 85,734,703): every block L-3 .. T+3 (so the precursor window T-12..T and the background L+4..T-13 are both whole);
  old  - the old-regime pools (T at L+8..+10) of the slice 85,170,000..85,452,461 (10-10 17:22 .. 10-11 01:27 UTC): blocks T-12 .. T+3.
-> cache/blk.jsonl, cache/rcp.jsonl"""
import pickle, sys
from lib import *
CUR0 = 85553521
mid = pickle.load(open("parsed_mid.pkl", "rb"))["pools"]; old = pickle.load(open("parsed_old.pkl", "rb"))["pools"]
cur = [p for p in mid if p["L"] >= CUR0 and p["T"] is not None]
oldp = [p for p in old if p["T"] is not None]
kb = KV("blk"); kr = KV("rcp")
nums_cur = sorted(set(b for p in cur for b in range(p["L"] - 3, p["Tbn"] + 4)))
near_cur = sorted(set(b for p in cur for b in range(p["Tbn"] - 12, p["Tbn"] + 4)))
nums_old = sorted(set(b for p in oldp for b in range(p["Tbn"] - 12, p["Tbn"] + 4)))
print(f"cur pools {len(cur)} blocks {len(nums_cur)} (near T {len(near_cur)}); old pools {len(oldp)} blocks {len(nums_old)}", flush=True)
order = near_cur + [b for b in nums_cur if b not in set(near_cur)] + nums_old
for i in range(0, len(order), 400):
    get_blocks(order[i:i + 400], kb, kr, receipts=True)
    print(f"  {min(i + 400, len(order))}/{len(order)} blocks {len(kb.d)} receipts {len(kr.d)}", flush=True)
print("done", flush=True)
