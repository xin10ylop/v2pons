# check the UR V4_SWAP (SWAP_EXACT_IN 0x07) minOut layout on the fee-100/500 crowd's 1284-byte buys: amountIn word == tx value, next word = amountOutMinimum
import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
P = load_pools(); T = load_txs(); F = load_families()
keys = ["0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|100|1|true", "0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|500|10|true"]
pids = [pid for k in keys for pid in F[k]["pids"]]
E = load_events(set(pids))

def ur_minout(inp, value):
    d = inp[10:]; n = len(d) // 64
    w = [int(d[64 * i: 64 * i + 64], 16) for i in range(n)]
    for i in range(8, n - 1):
        if w[i] == value and value > 0:
            return w[i + 1], i
    return None, None

rat = []; idx = collections.Counter(); other = collections.Counter()
for pid in pids:
    for s in E[pid]["swaps"]:
        t = T.get(s["tx"])
        if not t or s["a0"] >= 0: continue
        if t["to"] == "0x8876789976decbfcbbbe364623c63652db8c0904" and t.get("input"):
            mo, i = ur_minout(t["input"], t["value_wei"])
            key = (t["calldata_len"], t["nonce"] == 0)
            if mo is None: other[key] += 1; continue
            idx[(key, i)] += 1
            rat.append((key, round(mo / s["a1"], 4)))
print(idx); print("undecoded", other)
c = collections.defaultdict(list)
for k, r in rat: c[k].append(r)
for k, v in c.items(): print(k, len(v), sorted(v)[:3], sorted(v)[len(v)//2], sorted(v)[-3:])
