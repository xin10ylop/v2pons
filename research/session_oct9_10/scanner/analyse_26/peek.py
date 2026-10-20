import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
P = load_pools(); TF = load_to_families()
for k in ["0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|54500", "0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|46788", "0x3194e32622c5d860a0572c74edda99dcfd8fc827|2fcb9108|644", "0x8366a39cc670b4001a1121b8f6a443a643e40951|6276cbbe|196"]:
    r = TF.get(k)
    print("==", k, None if r is None else {a: (b if not isinstance(b, list) or len(b) < 15 else b[:15]) for a, b in r.items() if a != "pids"})
    ps = [p for p in P.values() if p["launch_to"] == k.split("|")[0] and p["selector"] == k.split("|")[1] and p["calldata_len"] == int(k.split("|")[2])]
    print(len(ps), "hooks_zero", collections.Counter(p["hooks_zero"] for p in ps))
    ps = [p for p in ps if not (k.startswith("0x8366") and p["hooks_zero"])]
    print(" n", len(ps), "txs", len(set(p["launch_tx"] for p in ps)), "from", collections.Counter(p["launch_from"] for p in ps).most_common(6))
    print(" fees", collections.Counter(p["fee"] for p in ps).most_common(8), "ts", collections.Counter(p["tick_spacing"] for p in ps).most_common(6))
    print(" hooks", collections.Counter(p["hooks"] for p in ps).most_common(8))
    print(" n_swaps>0", sum(1 for p in ps if p["n_swaps"]), "n_buys", sum(p["n_buys"] for p in ps), "pulls", sum(1 for p in ps if p["n_pulls"]), "adds>1", sum(1 for p in ps if p["n_adds"] > 1))
    print(" first_buy_rel", collections.Counter(p["first_buy_rel"] for p in ps).most_common(8))
    print(" first_pull_rel", sorted(p["first_pull_rel"] for p in ps if p["first_pull_rel"] is not None)[:30])
    print(" known", collections.Counter(p["known"] for p in ps), "liq0", collections.Counter(p["liq_launch"] > 0 for p in ps))
    print(" ts range", min(p["launch_ts"] for p in ps), max(p["launch_ts"] for p in ps))
    print(" example", {a: b for a, b in ps[0].items() if a not in ("first8_swap_to",)})
