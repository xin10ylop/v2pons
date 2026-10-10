import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
P = load_pools(); T = load_txs(); ids = json.load(open("pids.json"))
for pid in ids["F1"][:69]:
    p = P[pid]; t = T[p["launch_tx"]]; inp = t["input"]
    ws = [inp[10 + 64*i: 10 + 64*(i+1)] for i in range((len(inp) - 10) // 64)]
    print(pid[:10], p["n_swaps"], p["tick0"], " ".join(w.lstrip("0") or "0" for w in ws))
