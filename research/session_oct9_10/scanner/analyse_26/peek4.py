import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
P = load_pools(); T = load_txs()
fam = [p for p in P.values() if p["launch_to"] == "0x8366a39cc670b4001a1121b8f6a443a643e40951" and p["selector"] == "6276cbbe" and p["calldata_len"] == 196]
E = load_events(set(p["pid"] for p in fam))
def show(p, n=10):
    e = E[p["pid"]]; b0 = p["launch_block"]
    print("==", p["pid"][:12], "b0", b0, "fee", p["fee"], "ts", p["tick_spacing"], "hooks", p["hooks"][:10], "from", p["launch_from"][:12], "nonce", p["launch_nonce"], "tick0", p["tick0"])
    for a in e["adds"][:3]: print("  add", a["bn"] - b0, a["ti"], a["lo"], a["hi"], a["dl"], a["sender"][:10], a["tx"][:12])
    for s in e["swaps"][:n]:
        t = T.get(s["tx"])
        print("  swap", s["bn"] - b0, s["ti"], "buy" if s["a0"] < 0 else "sell", abs(s["a0"]) / 1e18, s["sender"][:10], s["fee"], (t["from"][:10], t["to"][:10], t["selector"], t["calldata_len"], t["nonce"]) if t else None)
    for s in e["pulls"][:2]: print("  pull", s["bn"] - b0, s["dl"], s["sender"][:10], (T[s["tx"]]["from"][:10], T[s["tx"]]["to"][:10], T[s["tx"]]["selector"]) if s["tx"] in T else None)
    print("  n swaps", len(e["swaps"]), "buys", sum(1 for s in e["swaps"] if s["a0"] < 0), "eth in", sum(-s["a0"] for s in e["swaps"] if s["a0"] < 0) / 1e18)
for k in [(500, 1, False), (3000, 60, True), (836798, 9303, True), (200000, 2000, True), (0, 40, True)]:
    sub = [p for p in fam if (p["fee"], p["tick_spacing"], p["hooks_zero"]) == k]
    print("#########", k, len(sub))
    for p in sub[:3]: show(p)
