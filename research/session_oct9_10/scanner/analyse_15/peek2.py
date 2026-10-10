import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
P = load_pools()
H = "0xae4c0cf7c3feb79e0c244edbc6a3f8a3290940cc"
for lab, cond in (("hook", lambda r: r["hooks"] == H), ("to c763", lambda r: r["launch_to"] == "0xc763b1795dabe2d2336eba214d16969ebc5db27f"),
                  ("posm fee9000", lambda r: r["launch_to"] == "0x58daec3116aae6d93017baaea7749052e8a04fa7" and r["fee"] == 9000),
                  ("posm 2020", lambda r: r["launch_to"] == "0x58daec3116aae6d93017baaea7749052e8a04fa7" and r["calldata_len"] == 2020)):
    rows = [r for r in P.values() if cond(r)]
    print("==", lab, len(rows))
    print("  families", collections.Counter(r["family"] for r in rows).most_common(10))
    print("  to", collections.Counter(r["launch_to"] for r in rows).most_common(5))
    print("  from", collections.Counter(r["launch_from"] for r in rows).most_common(8))
    print("  fee/ts", collections.Counter((r["fee"], r["tick_spacing"]) for r in rows).most_common(8))
    print("  known", collections.Counter(r["known"] for r in rows))
    print("  first_buy_rel", sorted([r["first_buy_rel"] for r in rows if r["first_buy_rel"] is not None])[:60])
    print("  first_buy_eth>=2e-4", sum(1 for r in rows if (r["first_buy_eth"] or 0) >= 2e-4), "pulled", sum(1 for r in rows if r["first_pull_rel"] is not None))
    print("  n_buys", collections.Counter(r["n_buys"] for r in rows).most_common(10))
