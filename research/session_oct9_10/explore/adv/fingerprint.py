"""Launch fingerprint: decode the multicall of the sampled launch txs (PoolKey from calldata alone), token bytecode hash, and how many
blocks before the launch the token's code exists (getCode at b0 - d)."""
import sys, pickle, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import batch
from eth_abi import decode
from eth_utils import keccak
D = pickle.load(open("adv/cache.pkl", "rb"))
hashes = collections.Counter(); rows = []
for pid, P in D.items():
    m = P["meta"]; b0 = m["b0"]
    t = next(t for b in P["blocks"] if b for t in b["transactions"] if t["hash"] == m["tx"])
    data = bytes.fromhex(t["input"][2:])
    (calls,) = decode(["bytes[]"], data[4:])
    sels = [c[:4].hex() for c in calls]
    key = None
    for c in calls:
        if c[:4].hex() == "f7020405":   # initializePool((address,address,uint24,int24,address),uint160)
            (k, sp), = [decode(["(address,address,uint24,int24,address)", "uint160"], c[4:])]
            key = (k[0], k[1], k[2], k[3], k[4], sp)
    rows.append((pid, b0, m["token"], sels, key, int(t["value"], 16), len(data), t["to"]))
codes = batch([("eth_getCode", [r[2], "latest"]) for r in rows])
for r, c in zip(rows, codes):
    hashes[(len(c) - 2) // 2, keccak(bytes.fromhex(c[2:])).hex()[:16]] += 1
# token code existence before the launch
dd = (1, 2, 3, 5, 10, 20, 50)
ex = batch([("eth_getCode", [r[2], hex(r[1] - d)]) for r in rows for d in dd])
first = collections.Counter()
for i, r in enumerate(rows):
    e = ex[i * len(dd):(i + 1) * len(dd)]
    have = [d for d, c in zip(dd, e) if c and len(c) > 2]
    first[max(have) if have else 0] += 1
print("multicall inner selectors:", collections.Counter(tuple(r[3]) for r in rows).most_common(3))
print("PoolKey from calldata (example):", rows[0][4])
print("keys consistent with token:", sum(1 for r in rows if r[4] and r[4][1].lower() == r[2].lower() and r[4][2] == 2500 and r[4][3] == 50 and int(r[4][4], 16) == 0 and int(r[4][0], 16) == 0))
print("launch value wei:", collections.Counter(r[5] for r in rows), "calldata len:", collections.Counter(r[6] for r in rows), "to:", collections.Counter(r[7] for r in rows))
print("token code (size, hash):", hashes.most_common(4))
print("token code present at least d blocks before the launch (max d of", dd, "):", sorted(first.items()))
