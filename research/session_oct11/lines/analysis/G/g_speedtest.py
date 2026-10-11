from common import *
import time, gsim
rows = {r["pool"]: r for r in load_rows()}
EV = pickle.load(open(os.path.join(G, "ev.pkl"), "rb"))
kept = json.load(open(os.path.join(G, "families_kept.json")))
fk = [k for k in kept if "2.4333285" in k][0]
pools = kept[fk][:200]
t = time.time()
res = []
for p in pools:
    ps = gsim.PoolSim(rows[p], EV[p]); res.append(ps.grid(0.0058))
print("200 pools", time.time() - t, "s")
import numpy as np
raw = np.array([r[1] for r in res]); sk = np.array([r[0] for r in res])
for ki, K in enumerate(gsim.KS[:4]):
    for i in [0, 3, 6, 11+ 2*11+5, 99+11*1+4]:
        print(K, gsim.rule_name(K, i), np.nanmean(raw[:, ki, i]), (sk[:, ki] == 0).sum())
