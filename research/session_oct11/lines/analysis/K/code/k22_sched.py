"""the surcharge X rate against seconds since the create (exact timestamps, k21 sample), non-listed buyers only."""
import json, collections
from kload import *
D = json.load(open(os.path.join(DATA, "k21_ts.json"))); ts = {int(k): v for k, v in D["ts"].items()}
C = load_creates(); sc = {c: C[c] for c in D["curves"]}
T = load_trades(set(sc))
tab = collections.defaultdict(collections.Counter); blk = collections.defaultdict(list)
for c, ev in T.items():
    cr = sc[c]; Es = {r[5][0] for r in ev if r[4] == "E" and r[2] == cr["tx"]}; xs = {r[2]: r[6][0] for r in ev if r[4] == "X"}
    t0 = ts.get(cr["bn"])
    for r in ev:
        if r[4] != "B" or r[2] == cr["tx"] or r[0] not in ts or t0 is None: continue
        if r[5][1] in Es or r[5][0] in Es: continue
        ds = ts[r[0]] - t0
        rate = round(xs[r[2]] / r[6][0] * 1e4) if r[2] in xs else 0
        tab[ds][rate] += 1; blk[ds].append(r[0] - cr["bn"])
for ds in sorted(tab): print("seconds", ds, dict(tab[ds]), "blocks", min(blk[ds]), "-", max(blk[ds]))
