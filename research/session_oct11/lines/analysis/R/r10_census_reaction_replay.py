"""Census ride replay priced with the observed reaction: the operator pulls `lag` blocks after a stranger's buy after T (r09: p10 4,
p50 7, p90 13 blocks); our buy at T+2 is that stranger buy. Untouched pools, the regimes without the pull-at-T+3 phase."""
import pickle, collections
from common import *
from ride import *
P = pickle.load(open("cpools.pkl", "rb"))
U = [p for p in P if not p["ours"] and p["T"] is not None]
def grp(p):
    if p["line"] == "3.0": return "3.0 old" if p["ts"] < NEW30 else "3.0 new"
    return "2.433 d0-5" if p["day"] <= 5 else "2.433 d6"
for lagr in (None, 4, 7, 13, 30):
    RES = collections.defaultdict(list)
    for p in U:
        fo = 5000 if p["line"] == "2.433" else 10000
        pp = dict(p)
        if lagr is not None:
            fake = p["T"] + 2 + lagr
            pp["pull"] = fake if p["pull"] is None else min(p["pull"], fake)
        for name, r in run_pool(pp, 0.0058, 2, fo).items(): RES[(grp(p), name)].append(r)
    print(f"--- reaction pull at our buy + {lagr}" if lagr else "--- no reaction (as the census pools were)")
    for k in sorted(RES):
        s = summ(RES[k], 0.0058)
        print(f"{k[0]:11s} {k[1]:12s} n {s['n']:4d} mean {s['mean%']:+7.2f}% med {s['med%']:+7.2f}% win {s['win']:.3f} pulled {s['pulled%']:5.1f}%")
