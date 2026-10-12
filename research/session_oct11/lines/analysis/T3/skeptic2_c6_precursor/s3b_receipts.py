"""Stage 3b: receipts for the rest of [L-3, T+3] of every slice pool (so log-based keys, e.g. an event in another line pool, have a
background and a first-occurrence time measured on the same footing as the transaction-list keys) -> cache/rcp.jsonl."""
import pickle, os
from lib import *
os.chdir(HERE)
D = pickle.load(open("s2_parsed.pkl", "rb")); P = [p for p in D["pools"] if p["in_slice"] and p["T"] is not None]
kb = KV("blk"); kr = KV("rcp")
class KV0:
    class _All:
        def __contains__(self, k): return True
    def __init__(self, kv): self.d = KV0._All(); self.kv = kv
    def put(self, k, v): self.kv.put(k, v)
    def flush(self): self.kv.flush()
allb = sorted(set(b for p in P for b in range(p["L"] - 3, p["Tbn"] + 4)) - set(int(k) for k in kr.d))
print("receipt blocks to fetch", len(allb), flush=True)
for i in range(0, len(allb), 300):
    get_blocks(allb[i:i + 300], KV0(kb), kr); print(f"  receipts {min(i + 300, len(allb))}/{len(allb)} have {len(kr.d)}", flush=True)
need = sorted(set(b for p in P for b in range(p["L"] - 3, p["Tbn"] + 4)))
print("missing receipts", sum(1 for b in need if str(b) not in kr.d), "of", len(need))
