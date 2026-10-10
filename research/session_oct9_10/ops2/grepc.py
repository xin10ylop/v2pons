"""cache-wide (no RPC): every cached tx from/to the given addresses"""
import os, json, sys
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops2")
from labels import lab
D = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops/lch/bc/"
X = {a.lower() for a in sys.argv[1:]}
seen = set(); out = []
for f in sorted(os.listdir(D)):
    if not f.endswith(".json"): continue
    try: d = json.load(open(D + f))
    except Exception: continue
    for k, (ts, tl) in d.items():
        bn = int(k)
        if bn in seen: continue
        seen.add(bn)
        for t in tl:
            if t[1] in X or t[2] in X: out.append((bn, ts, t))
out.sort()
import time
for bn, ts, t in out: print(bn, time.strftime("%m-%d %H:%M:%S", time.gmtime(ts)), t[1], lab(t[1]), "->", t[2], lab(t[2]), int(t[3]) / 1e18, "n", t[4], t[5])
print(len(out), "txs;", len(seen), "blocks searched")
