import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
P = load_pools(); T = load_txs()
ps = [p for p in P.values() if p["launch_to"] == "0x8366a39cc670b4001a1121b8f6a443a643e40951" and p["selector"] == "6276cbbe" and p["fee"] == 500 and p["tick_spacing"] == 1 and p["hooks_zero"]]
E = load_events(set(p["pid"] for p in ps))
for p in ps[:6]:
    e = E[p["pid"]]; b0 = p["launch_block"]
    print("==", p["pid"][:12], "b0", b0, "from", p["launch_from"], "nonce", p["launch_nonce"], "token", p["token"], "tick0", p["tick0"], "sp0", p["sqrt_p0"])
    print("  launch tx", {k: T[p["launch_tx"]][k] for k in ("from", "to", "nonce", "value_eth", "selector", "calldata_len", "max_prio", "gas_price")})
    for a in e["adds"]: print("  add", a["bn"] - b0, a["ti"], a["lo"], a["hi"], a["dl"], a["sender"], a["tx"][:12], a["tx"] in T)
    for s in e["swaps"][:10]:
        t = T.get(s["tx"])
        print("  swap", s["bn"] - b0, s["ti"], "buy" if s["a0"] < 0 else "sell", abs(s["a0"]) / 1e18, s["sender"][:10], s["fee"], (t["from"][:10], t["to"][:10], t["selector"], t["calldata_len"], t["nonce"]) if t else None)
    for s in e["pulls"]: print("  pull", s["bn"] - b0, s["dl"], s["sender"][:10], s["tx"][:12], (T[s["tx"]]["from"][:10], T[s["tx"]]["to"][:10], T[s["tx"]]["selector"]) if s["tx"] in T else None)
    print("  n swaps", len(e["swaps"]), "buys", sum(1 for s in e["swaps"] if s["a0"] < 0))
