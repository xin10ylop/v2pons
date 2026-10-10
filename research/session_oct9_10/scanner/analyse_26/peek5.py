import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
P = load_pools(); T = load_txs(); A = json.load(open("cache/add_txs.json"))
fam = [p for p in P.values() if p["launch_to"] == "0x8366a39cc670b4001a1121b8f6a443a643e40951" and p["selector"] == "6276cbbe" and p["calldata_len"] == 196]
E = load_events(set(p["pid"] for p in fam))
for k in [(500, 1, True), (500, 1, False)]:
    sub = [p for p in fam if (p["fee"], p["tick_spacing"], p["hooks_zero"]) == k]
    rows = []
    for p in sub:
        e = E[p["pid"]]
        if not e["adds"]: continue
        a = e["adds"][0]; t = A.get(a["tx"]) or T.get(a["tx"])
        rows.append((a["bn"] - p["launch_block"], t["from"] == p["launch_from"], t["to"], t["selector"], t["calldata_len"], t["value_wei"] / 1e18, t["nonce"], a["lo"], a["hi"], p["tick0"]))
    print(k, len(rows))
    print(" add offset", collections.Counter(r[0] for r in rows).most_common(10))
    print(" add by launch wallet", collections.Counter(r[1] for r in rows), "to/sel/len", collections.Counter((r[2], r[3], r[4]) for r in rows).most_common(4))
    print(" add value", collections.Counter(round(r[5], 6) for r in rows).most_common(8), "nonce", collections.Counter(r[6] for r in rows).most_common(5))
    print(" ranges", collections.Counter((r[7], r[8], r[9]) for r in rows).most_common(6))
    print(" tick0", collections.Counter(r[9] for r in rows).most_common(6))
    print(" liq", collections.Counter(E[p["pid"]]["adds"][0]["dl"] for p in sub if E[p["pid"]]["adds"]).most_common(6))
    print(" launch nonce", collections.Counter(p["launch_nonce"] for p in sub).most_common(4))
    # how was the wallet funded? first tx nonce 0?
    print(" deployers distinct", len(set(p["launch_from"] for p in sub)))
