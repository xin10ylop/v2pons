"""Stage 3: full blocks [T-12, T+3] of every pool (all transactions), block receipts [T-12, T+1] (status, logs), and the launch block L
(its timestamp). Cached in cache/blk.jsonl, cache/rcp.jsonl."""
import pickle
from lib import *
D = pickle.load(open("parsed.pkl", "rb")); P = [p for p in D["pools"] if p["T"] is not None]
kb = KV("blk"); kr = KV("rcp")
nb = sorted({b for p in P for b in list(range(p["Tbn"] - 12, p["Tbn"] + 4)) + [p["L"]]})
nr = sorted({b for p in P for b in range(p["Tbn"] - 12, p["Tbn"] + 2)})
print(f"pools {len(P)}; blocks {len(nb)}; receipts {len(nr)}", flush=True)
get_blocks(nb, kb, kr, receipts=False)
need = [n for n in nr if str(n) not in kr.d]
for i in range(0, len(need), 100):
    ch = need[i:i + 100]; res = batch([("eth_getBlockReceipts", [hex(n)]) for n in ch], 10)
    for n, r in zip(ch, res):
        if r is not None: kr.put(str(n), slim_receipts(r))
    kr.flush(); print(f"   receipts {i+len(ch)}/{len(need)}", flush=True)
print("missing blocks", sum(1 for n in nb if str(n) not in kb.d), "missing receipts", sum(1 for n in nr if str(n) not in kr.d))
