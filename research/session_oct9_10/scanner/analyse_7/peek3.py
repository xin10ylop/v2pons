import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
P = load_pools(); F = load_families(); T = load_txs()
keys = json.load(open("families_in.json"))
pids = [pid for k in keys for pid in F[k]["pids"]]
E = load_events(set(pids))
def words(inp): return [inp[10 + 64 * i: 10 + 64 * (i + 1)] for i in range((len(inp) - 10) // 64)]
def strs(inp):
    w = words(inp); out = []
    for i in range(len(w)):
        b = bytes.fromhex(w[i]).rstrip(b"\0")
        if b and all(32 <= c < 127 for c in b): out.append(b.decode())
    return out
w7 = collections.Counter(); w8 = collections.Counter(); w10 = collections.Counter(); gp = collections.Counter()
for pid in pids:
    p = P[pid]; t = T[p["launch_tx"]]; w = words(t["input"])
    w7["0x" + w[7][24:]] += 1; w8[int(w[8], 16)] += 1; w10[int(w[10], 16)] += 1; gp[(t["max_prio"], t["gas"])] += 1
    print(pid[:10], p["launch_block"], p["token"][:10], "0x" + w[7][24:34], int(w[8], 16), int(w[10], 16) / 1e18, strs(t["input"])[:3], p["tx_index"], p["launch_to"][:10])
print(w7.most_common(8)); print(w8); print(w10); print(gp.most_common(5))
pid = [x for x in pids if x.startswith("0xcdbee622")][0]
e = E[pid]
for s in e["swaps"]:
    t = T.get(s["tx"]); print(s["bn"] - P[pid]["launch_block"], s["a0"] / 1e18, s["a1"] / 1e18, s["fee"], t and t["from"], t and t["to"], t and t["selector"], t and t["value_eth"])
print(e["pulls"], e["zero_mods"], len(e["adds"]))
