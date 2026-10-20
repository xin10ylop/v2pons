"""Stage 3: whole blocks (every transaction) [L-3, T+3] of every slice pool, and the receipts (every log) of [T-12, T+3]
-> cache/blk.jsonl, cache/rcp.jsonl."""
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
allb = sorted(set(b for p in P for b in range(p["L"] - 3, p["Tbn"] + 4)))
near = sorted(set(b for p in P for b in range(p["Tbn"] - 12, p["Tbn"] + 4)))
print("pools", len(P), "blocks", len(allb), "receipt blocks", len(near), flush=True)
for i in range(0, len(allb), 500):
    get_blocks(allb[i:i + 500], kb, kr, receipts=False); print(f"  blocks {min(i + 500, len(allb))}/{len(allb)} have {len(kb.d)}", flush=True)
for i in range(0, len(near), 300):
    get_blocks(near[i:i + 300], KV0(kb), kr); print(f"  receipts {min(i + 300, len(near))}/{len(near)} have {len(kr.d)}", flush=True)
print("missing blocks", sum(1 for b in allb if str(b) not in kb.d), "missing receipts", sum(1 for b in near if str(b) not in kr.d))
