import sys, json
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
F = load_families(); P = load_pools(); T = load_txs()
K3 = "0x8366a39cc670b4001a1121b8f6a443a643e40951|6276cbbe|196|3000|60|true"
pids = F[K3]["pids"]
E = load_events(set(pids))
for pid in pids:
    e = E[pid]
    for s in e["swaps"][:1]:
        t = T[s["tx"]]
        inp = t.get("input") or t["input512"]
        print(pid[:10], t["from"][:10], t["to"][:10], t["selector"], t["value_eth"], -s["a0"], s["a1"])
        for i in range((len(inp)-10)//64): print("    w%d" % i, inp[10+64*i:10+64*(i+1)], int(inp[10+64*i:10+64*(i+1)],16))
    print("  launch input", T[P[pid]["launch_tx"]]["input"])
    print("  token", P[pid]["token"])
