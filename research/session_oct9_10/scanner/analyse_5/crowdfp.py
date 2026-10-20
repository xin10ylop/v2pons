# where else does the fee-100 family's crowd fingerprint (UR execute, 1284-byte calldata, sender nonce 0) appear?
import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
P = load_pools(); T = load_txs()
UR = "0x8876789976decbfcbbbe364623c63652db8c0904"
hit = collections.Counter(); fams = collections.Counter(); per_pool = collections.defaultdict(int)
for h, t in T.items():
    if t["to"] == UR and t["selector"] == "3593564c" and t["calldata_len"] == 1284 and t["nonce"] == 0 and "swap" in t.get("kind", []):
        for pid, kind, rank in t["refs"]:
            if kind == "swap": per_pool[pid] += 1
for pid, n in per_pool.items():
    fams[P[pid]["family"]] += 1
print(len(per_pool), "pools with a nonce-0 1284-byte UR buy among the first 8 swaps")
for k, n in fams.most_common(30): print(n, k)
# by calldata length, any nonce: UR 1284 buys
c2 = collections.Counter()
for h, t in T.items():
    if t["to"] == UR and t["calldata_len"] == 1284:
        c2[t["nonce"] == 0] += 1
print("UR 1284 by nonce0", c2)
