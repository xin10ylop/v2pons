import sys, os, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
P = load_pools(); C = json.load(open("cache/fetch2.json")); T = load_txs()
PMA = "0x8366a39cc670b4001a1121b8f6a443a643e40951"; UR = "0x8876789976decbfcbbbe364623c63652db8c0904"; TESTER = "0x4f881c6afe5ced5e4469b15269fd0c1390f089c6"
F4a = [p["pid"] for p in P.values() if p["launch_to"] == PMA and p["selector"] == "6276cbbe" and p["calldata_len"] == 196 and p["fee"] == 500 and p["tick_spacing"] == 1 and p["hooks_zero"]]
E = load_events(set(F4a))
print("pools with an outside-router buy (any size): age of each outside buy (size ETH, sender) | pull age")
nopull_ages = []
for pid in F4a:
    e = E[pid]; lb = e["adds"][0]["bn"]; pb = e["pulls"][0]["bn"] - lb if e["pulls"] else None
    ob = [s for s in e["swaps"] if s["a0"] < 0 and s["sender"] not in (UR, TESTER)]
    if ob:
        print("  %s pull %s | %s" % (pid[:10], pb, [(s["bn"] - lb, round(-s["a0"] / 1e18, 6), s["sender"][:8]) for s in ob[:5]]))
    elif pb is not None:
        nopull_ages.append(pb)
        # what preceded: last 3 swaps with tx info
        prev = [s for s in e["swaps"] if s["bn"] - lb <= pb][-3:]
        info = []
        for s in prev:
            t = C["tx"].get(s["tx"]) or T.get(s["tx"])
            info.append((pb - (s["bn"] - lb), round(abs(s["a0"]) / 1e18, 5), "B" if s["a0"] < 0 else "S", (t["to"][:8] + ":" + t["selector"] + ":" + t["from"][:8]) if t else s["sender"][:8]))
        print("  NO-OUTSIDER pulled at %d, last swaps before (blocks before pull, eth, side, to:sel:from) %s" % (pb, info))
print("pull ages without an outside-router buy:", sorted(nopull_ages))
