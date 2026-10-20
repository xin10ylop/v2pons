import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
P = load_pools()
ps = [p for p in P.values() if p["launch_to"] == "0x8366a39cc670b4001a1121b8f6a443a643e40951" and p["selector"] == "6276cbbe" and p["calldata_len"] == 196]
print(len(ps))
g = collections.Counter((p["fee"], p["tick_spacing"], p["hooks_zero"]) for p in ps)
for k, n in g.most_common():
    sub = [p for p in ps if (p["fee"], p["tick_spacing"], p["hooks_zero"]) == k]
    print(k, n, "deployers", len(set(p["launch_from"] for p in sub)), "nonce", sorted(p["launch_nonce"] for p in sub)[:: max(1, n // 6)],
          "hooks", collections.Counter(p["hooks"] for p in sub).most_common(2), "tokens", len(set(p["token"] for p in sub)),
          "swaps>0", sum(1 for p in sub if p["n_swaps"]), "pulls", sum(1 for p in sub if p["n_pulls"]),
          "fb", sorted(p["first_buy_rel"] for p in sub if p["first_buy_rel"] is not None)[:: max(1, n // 8)],
          "fp", sorted(p["first_pull_rel"] for p in sub if p["first_pull_rel"] is not None)[:: max(1, n // 8)],
          "liq", collections.Counter(p["liq_launch"] for p in sub).most_common(2), "adds", collections.Counter(p["n_adds"] for p in sub).most_common(3))
