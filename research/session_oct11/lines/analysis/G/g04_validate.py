"""check that the replay reproduces each kept family's real price path (no buy of ours): cumulative relative sqrtP error per swap"""
from common import *
import random, gsim
rows = {r["pool"]: r for r in load_rows()}
EV = pickle.load(open(os.path.join(G, "ev.pkl"), "rb"))
kept = json.load(open(os.path.join(G, "families_kept.json")))
random.seed(1)
allerr = []; out = []
for fk, pools in sorted(kept.items(), key=lambda kv: -len(kv[1])):
    sample = random.sample(pools, min(25, len(pools)))
    errs = []; jumps = 0; nsw = 0
    for p in sample:
        ps = gsim.PoolSim(rows[p], EV[p]); e, j = ps.validate(EV[p]); errs += e; jumps += j; nsw += len(e)
    allerr += errs
    md = pct(errs, 0.5); p90 = pct(errs, 0.9); mx = max(errs) if errs else None
    out.append(f"{fk[:110]:110s} swaps {nsw:6d} err med {md if md is None else f'{md:.1e}'} p90 {p90 if p90 is None else f'{p90:.1e}'} max {mx if mx is None else f'{mx:.1e}'} liq jumps {jumps}")
print("all sampled swaps", len(allerr), "median", f"{pct(allerr,0.5):.2e}", "p90", f"{pct(allerr,0.9):.2e}", "p99", f"{pct(allerr,0.99):.2e}",
      "share > 1e-6:", f"{sum(e > 1e-6 for e in allerr)/len(allerr):.4f}")
print("\n".join(out))
