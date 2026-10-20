"""pack: trades.jsonl -> per-curve lists for the ETH-quoted curves created in the window (pickle), dropping unknown addresses."""
import json, pickle, collections
from kload import *
C = load_creates(); ce = {k: v for k, v in C.items() if v["quote"] == 0}
T = collections.defaultdict(list); n = 0; other = collections.Counter()
with open(os.path.join(DATA, "trades.jsonl")) as f:
    for line in f:
        r = json.loads(line)
        if r[3] in ce: T[r[3]].append(tuple([r[0], r[1], r[2], r[4], tuple(r[5]), tuple(r[6])])); n += 1
        elif r[3] in C: other["nonETH-curve"] += 1
        else: other["unknown-address"] += 1
for k in T: T[k].sort(key=lambda r: (r[0], r[1]))
pickle.dump({"creates": ce, "all_creates": C, "trades": dict(T)}, open(os.path.join(DATA, "packed.pkl"), "wb"))
print("ETH curves", len(ce), "with events", len(T), "rows", n, other)
