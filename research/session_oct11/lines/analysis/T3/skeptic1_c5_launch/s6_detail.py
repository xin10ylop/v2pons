"""Stage 6: the cases behind stage 5 (current regime): the pools with a 1444-byte call at d 0..4 before T, and every trade of the engine
A=18 k=1 (fire on the first 1444-byte call from L+18 until the bot's buy) with its lead and outcome under lag 3 / 5 / 9 / none; a Poisson
check of the hit count against the same pools' own background."""
import pickle, json, math, collections, sys
sys.argv = [sys.argv[0]]
import s5_rule as R
from lib import *
NEWP = [p for p in R.P if R.ts_of(p["L"]) >= R.NEW30]
print("\n\n================ stage 6 details ================")
print("pools (current regime) with a 1444-byte call at d 0..4 before T:")
for p in NEWP:
    if p["Tbn"] is None: continue
    ds = R.dset(p)
    for d in range(0, 5):
        for c in ds.get(d, []):
            print(f"  pool {p['pid'][:10]} L {p['L']} T L+{p['T']} | call at d={d} (L+{c['bn']-p['L']}), value {c['v']/1e18:g} ETH, from {c['frm'][:10]}, tx index {c['ti']} vs bot {p['Tti'] if d == 0 else '-'}")
print("\nengine A=18 k=1, every trade (lead = T - trigger block):")
for p in NEWP:
    if not R.complete(p, 18): continue
    fire = None
    for bn in range(p["L"] + 18, R.armed_end(p) + 1):
        cs = [c for c in (R.calls(bn) or []) if not (p["Tbn"] is not None and bn == p["Tbn"] and c["ti"] > p["Tti"])]
        if cs: fire = (bn, cs[0]); break
    if fire is None: continue
    bn, c = fire
    outs = []
    for lag in (3, 5, 9, None):
        kind, r = R.trade(p, bn + 1, 1, lag, "T+1"); outs.append(f"lag {lag}: {kind} {100*r:+.1f}%")
    print(f"  pool {p['pid'][:10]} L+{bn-p['L']} trigger value {c['v']/1e18:g} from {c['frm'][:10]}; T {('L+'+str(p['T'])) if p['T'] is not None else 'none'}; "
          f"lead {p['Tbn']-bn if p['Tbn'] is not None else '-'}; natural pull {('L+'+str(p['pull'])) if p['pull'] is not None else 'none'} | " + "; ".join(outs))
def pois_ge(k, lam): return 1 - sum(math.exp(-lam) * lam ** i / math.factorial(i) for i in range(k))
full_new = [p for p in R.full if R.ts_of(p["L"]) >= R.NEW30]
r, nb = R.bgrate(full_new)
obs = sum(1 for p in full_new if any(R.dset(p).get(d) for d in range(1, 5)))
lam = len(full_new) * (1 - (1 - r) ** 4)
print(f"\nPoisson: current regime, pools {len(full_new)}, hits in d1..4 {obs}, expected at the pools' own background ({r:.4f}/block) {lam:.2f}, P(X >= obs) = {pois_ge(obs, lam):.3f}")
