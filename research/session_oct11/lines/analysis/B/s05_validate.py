"""Check the replay's swap model against the real price path: per family, the median / p90 relative error of the modelled sqrtP after
each real swap (from the previous swap's sqrtP and this swap's liquidity), and the share of pools whose liquidity changes between swaps."""
import pickle
from common import *
from replay import Pool
X = pickle.load(open(os.path.join(D, "events.pkl"), "rb")); E, fam = X["ev"], X["fam"]
rows = {r["pool"]: r for r in load_rows() if r["pool"] in fam}
res = C.defaultdict(lambda: {"err": [], "jump_pools": 0, "n": 0, "nsw": 0})
for pid, k in fam.items():
    P = Pool(rows[pid], E[pid]); errs, j = P.validate()
    x = res[k]; x["err"] += errs; x["n"] += 1; x["nsw"] += len(P.sw); x["jump_pools"] += (j > 0)
for k, x in sorted(res.items(), key=lambda kv: -kv[1]["n"]):
    print(f"{short(k):40s} pools {x['n']:4d} swaps {x['nsw']:6d} err p50 {pct(x['err'],.5) or 0:.1e} p90 {pct(x['err'],.9) or 0:.1e} p99 {pct(x['err'],.99) or 0:.1e} | pools with liquidity change between swaps {x['jump_pools']}")
