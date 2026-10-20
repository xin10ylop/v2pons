import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
P = load_pools(); T = load_txs()
fam = [p for p in P.values() if p["launch_to"] == "0x8366a39cc670b4001a1121b8f6a443a643e40951" and p["selector"] == "6276cbbe" and p["fee"] == 500 and p["tick_spacing"] == 1]
E = load_events(set(p["pid"] for p in fam))
n = 0
for p in fam[:200]:
    e = E[p["pid"]]
    for s in e["swaps"][:8]:
        t = T.get(s["tx"])
        if t and t["selector"] == "7169b574":
            inp = t["input"]; ws = [inp[10 + 64 * i: 10 + 64 * (i + 1)] for i in range((len(inp) - 10) // 64)]
            print(p["pid"][:10], p["hooks"][:8], "a0", s["a0"], "a1", s["a1"], "value", t["value_wei"], "to", t["to"])
            for i, w in enumerate(ws): print("   ", i, w, int(w, 16) if int(w, 16) < 10**40 else "")
            n += 1; break
    if n >= 2: break
