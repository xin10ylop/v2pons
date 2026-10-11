"""Stage 3b: receipts (every log) of blocks [T-4, T] of every 3.0 pool, the window a usable precursor must sit in (the full [T-12, T+3]
receipt pass was too slow on the shared public RPC). -> cache/rcp.jsonl"""
import pickle
from lib import *
D = pickle.load(open("parsed.pkl", "rb"))
P = [p for p in D["pools"] if p["line"] == "3.0" and p["T"] is not None]
kr = KV("rcp")
nums = sorted(set(b for p in P for b in range(p["Tbn"] - 4, p["Tbn"] + 1)) - set(int(k) for k in kr.d))
print("receipts to fetch", len(nums), flush=True)
for i in range(0, len(nums), 50):
    ch = nums[i:i + 50]
    for n, r in zip(ch, batch([("eth_getBlockReceipts", [hex(n)]) for n in ch], 10)):
        if r is not None: kr.put(str(n), slim_receipts(r))
    kr.flush(); print(f"  {min(i + 50, len(nums))}/{len(nums)}", flush=True)
