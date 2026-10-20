import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
P = load_pools(); T = load_txs(); ids = json.load(open("pids.json")); E = load_events(set(ids["F2"]))
n = 0
for pid in ids["F2"]:
    p = P[pid]; e = E[pid]
    for s in e["swaps"]:
        t = T.get(s["tx"])
        if not t: continue
        inp = t.get("input") or t["input512"]
        ws = [inp[10 + 64*i: 10 + 64*(i+1)] for i in range((len(inp) - 10) // 64)]
        print(pid[:10], "+%d" % (s["bn"] - p["launch_block"]), t["selector"], "a0 %d a1 %d" % (s["a0"], s["a1"]), " ".join((w.lstrip("0") or "0") for w in ws[:12]))
        n += 1
    if n > 60: break
