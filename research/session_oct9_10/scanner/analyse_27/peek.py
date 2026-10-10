import sys, collections, json
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
P = load_pools()
POSM = "0x58daec3116aae6d93017baaea7749052e8a04fa7"
g1 = [p for p in P.values() if p["launch_to"] == POSM and p["selector"] == "ac9650d8" and p["calldata_len"] == 2020]
g2 = [p for p in P.values() if p["launch_to"] == POSM and p["selector"] == "ac9650d8" and p["calldata_len"] == 1444 and 10001 <= p["fee"] <= 10300]
g3 = [p for p in P.values() if (p["to_code_hash"] or "").replace("0x","").startswith("f07d1c53")]
g4 = [p for p in P.values() if p["selector"] == "7fde822e"]
for name, g in (("g1", g1), ("g2", g2), ("g3", g3), ("g4", g4)):
    print("==", name, len(g))
    C = collections.Counter
    print(" hooks", C(p["hooks"] for p in g).most_common(5))
    print(" fee", C(p["fee"] for p in g).most_common(8), "ts", C(p["tick_spacing"] for p in g).most_common(5))
    print(" values", C(p["launch_value_eth"] for p in g).most_common(8))
    print(" from", len(set(p["launch_from"] for p in g)), C(p["launch_from"] for p in g).most_common(5))
    print(" to", len(set(p["launch_to"] for p in g)), C(p["launch_to"] for p in g).most_common(4))
    print(" known", C(p["known"] for p in g), C(p["known_by_rule"] for p in g))
    print(" families", len(set(p["family"] for p in g)), C(p["family"] for p in g).most_common(3))
    print(" n_swaps>0", sum(1 for p in g if p["n_swaps"]), "n_pulls>0", sum(1 for p in g if p["n_pulls"]))
    print(" first_buy_rel", sorted(x["first_buy_rel"] for x in g if x["first_buy_rel"] is not None)[::max(1,len(g)//15)])
    print(" first_pull_rel", sorted(x["first_pull_rel"] for x in g if x["first_pull_rel"] is not None)[::max(1,len(g)//15)])
    print(" ts span", min(p["launch_ts"] for p in g), max(p["launch_ts"] for p in g), " multi-pool txs", sum(1 for p in g if sum(1 for q in g if q["launch_tx"]==p["launch_tx"])>1))
    print(" calldata_len", C(p["calldata_len"] for p in g).most_common(8))
