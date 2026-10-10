import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/protect")
from load_all import *
pools, head = load_all(); cw = annotate(pools)
c = collections.Counter(); o = collections.Counter()
for p in pools:
    for x in p["sw"]:
        if x["a0"] >= 0 and not is_us(x):
            f = x["fp"] or {}
            k = (f.get("type"), f.get("prio"), f.get("gas"), f.get("len"), f.get("dl_max"), (x["to"] or "")[:10], (x["value"] or 0) > 0)
            (c if x["from"] in cw else o)[k] += 1
print("crowd-wallet SELLS fingerprints:"); [print("  ", v, k) for k, v in c.most_common(8)]
print("non-crowd SELLS fingerprints:"); [print("  ", v, k) for k, v in o.most_common(8)]
print("crowd sells total", sum(c.values()), "non-crowd sells", sum(o.values()))
