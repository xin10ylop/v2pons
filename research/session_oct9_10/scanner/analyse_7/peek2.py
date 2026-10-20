import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
P = load_pools(); F = load_families(); T = load_txs()
keys = json.load(open("families_in.json"))
pids = [pid for k in keys for pid in F[k]["pids"]]
E = load_events(set(pids))
p = P[F[keys[0]]["pids"][0]]
t = T[p["launch_tx"]]
inp = t["input"]
print(t["selector"], t["calldata_len"], t["gas"], t["gas_price"], t["max_prio"], t["type"])
for i in range(0, (len(inp) - 10) // 64):
    w = inp[10 + 64 * i: 10 + 64 * (i + 1)]
    try: s = bytes.fromhex(w).rstrip(b"\0").decode("ascii") if all(32 <= c < 127 for c in bytes.fromhex(w).rstrip(b"\0")) and bytes.fromhex(w).rstrip(b"\0") else ""
    except Exception: s = ""
    print(i, w, int(w, 16) if not s else "", s)
e = E[p["pid"]]
print(json.dumps(e["adds"], default=str)[:600])
print(json.dumps(e["swaps"], default=str)[:600])
# first swap txs
c = collections.Counter(); froms = collections.Counter(); sel = collections.Counter()
for pid in pids:
    for s in E[pid]["swaps"]:
        tx = T.get(s["tx"])
        c[(tx["to"], tx["selector"], tx["calldata_len"]) if tx else None] += 1; froms[tx["from"] if tx else None] += 1
print(c.most_common(10)); print(froms.most_common(10))
