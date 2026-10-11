"""the migration pools' v4 events in [migration, +3,000] from the census's ev.jsonl (offline)"""
import json
from krpc import *
M = json.load(open(os.path.join(OUT, "k13_mig_pools.json"))); ids = {m["pool"]: m for m in M}
out = {i: {} for i in ids}
with open(os.path.join(CEN, "cache", "ev.jsonl")) as f:
    for line in f:
        if not any(i[2:12] in line for i in ids): continue
        g = json.loads(line)
        for e in g["ev"]:
            i = e[4]
            if i in ids and ids[i]["launch_block"] <= e[1] <= ids[i]["launch_block"] + 3000: out[i][(e[1], e[3])] = e
res = {i: [v[k] for k in sorted(v)] for i, v in out.items()}
json.dump(res, open(os.path.join(DATA, "mig_pool_events.json"), "w"))
print("pools with events", sum(1 for v in res.values() if v), "events", sum(len(v) for v in res.values()))
