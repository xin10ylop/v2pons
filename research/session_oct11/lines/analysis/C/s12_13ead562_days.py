"""lc:0a493d1a|13ead562: per day, the liquidity tier (L of the single mint), the launch wallet's first buy size, frb presence, pulls."""
import sys, os, pickle
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fams import *
R = load_rows(); FP = fam_pools(R); E = pickle.load(open(os.path.join(OUT, "ev.pkl"), "rb"))
T0 = 1791121962
rs = FP["lc:0a493d1a|13ead562"]
for d in range(7):
    xs = [r for r in rs if int((r["launch_ts"] - T0) // 86400) == d]
    tiers = Counter(); fb = Counter(); hasfrb = 0; nolaunchbuy = 0
    for r in xs:
        o = E[r["pool"]]
        mi = [e for e in o["ev"] if e[0] == "mi"]
        tiers["%.3g" % mi[0][8] if mi else "none"] += 1
        sw = [e for e in o["ev"] if e[0] == "s"]
        fb[round((sw[0][7] if r["quote_side"] == 0 else sw[0][8]) / 1e18, 4) if sw else None] += 1
        hasfrb += bool(r["frb"])
    print(f"d{d}: n {len(xs)}  frb {hasfrb}  L tiers {tiers.most_common(5)}  first swap ETH {fb.most_common(5)}  launch wallets {len(set(r['launch']['from'] for r in xs))}")
