import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
P = load_pools()
v = [p for p, r in P.items() if r["known"] == "vbot-v2.433"]
A = [p for p, r in P.items() if r["known"] == "operator-A"]
E = load_events(set(v) | set(A))
for name, g in (("v2433", v), ("opA", A)):
    c = collections.Counter(); byblk = []
    for pid in g:
        e = E.get(pid)
        if not e: continue
        fs = set(s["fee"] for s in e["swaps"])
        c[(P[pid]["fee"], tuple(sorted(fs)))] += 1
        if e["swaps"]: byblk.append((P[pid]["launch_block"], e["swaps"][0]["fee"]))
    print(name, c.most_common(10))
    byblk.sort()
    # transition block
    prev = None
    for b, f in byblk:
        if f != prev: print("  ", b, f); prev = f
