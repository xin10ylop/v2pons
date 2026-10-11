"""Stage 3: whole blocks (every transaction) and block receipts (every log) of [L-3, T+3] for every pool launched in the last 2 hours
(the test slice plus the finder's overlap), precursor window [T-12, T+3] first -> cache/blk.jsonl, cache/rcp.jsonl."""
import pickle, os
from lib import *
os.chdir(HERE)
D = pickle.load(open("u2_parsed.pkl", "rb"))
P = [p for p in D["pools"] if p["recent2h"] and p["T"] is not None]
kb = KV("blk"); kr = KV("rcp")
near = sorted(set(b for p in P for b in range(max(p["L"] - 3, p["Tbn"] - 12), p["Tbn"] + 4)))
rest = sorted(set(b for p in P for b in range(p["L"] - 3, p["Tbn"] + 4)) - set(near))
print("pools", len(P), "blocks near T", len(near), "rest", len(rest), flush=True)
for name, nums in (("near", near), ("rest", rest)):
    for i in range(0, len(nums), 400):
        get_blocks(nums[i:i + 400], kb, kr)
        print(f"  {name} {min(i + 400, len(nums))}/{len(nums)} blocks {len(kb.d)} receipts {len(kr.d)}", flush=True)
miss = [b for b in near + rest if str(b) not in kb.d or str(b) not in kr.d]
print("missing blocks or receipts:", len(miss), miss[:10])
