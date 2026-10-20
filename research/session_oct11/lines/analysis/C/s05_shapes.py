"""Liquidity shape per family: V2 initial reserves (ETH side), V3 mint ranges (full range or not, single-sided or not), the
token side, swaps before/after, sells by non-launch wallets."""
import sys, os, pickle
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fams import *
R = load_rows(); FP = fam_pools(R); E = pickle.load(open(os.path.join(OUT, "ev.pkl"), "rb"))
def q(xs, ps=(.1, .5, .9)):
    xs = sorted(x for x in xs if x is not None)
    return "/".join(f"{xs[min(len(xs)-1, int(p*len(xs)))]:.4g}" for p in ps) if xs else "-"
for name0, rs0 in FP.items():
  for kind in ("v2", "v3"):
    rs = [r for r in rs0 if r["n_adds"] and (r["dex"] == "v3") == (kind == "v3")]
    name = f"{name0} [{kind}]"
    if not rs: continue
    print(f"\n## {name} (with liquidity {len(rs)})  quote_side {Counter(r['quote_side'] for r in rs).most_common()}")
    if rs[0]["dex"] in ("v2a", "v2b"):
        eth0, tok0 = [], []
        nmints = []
        for r in rs:
            o = E[r["pool"]]; qs = r["quote_side"]
            mi = [e for e in o["ev"] if e[0] == "mi"]
            nmints.append(len(mi))
            if mi: eth0.append(mi[0][6 + qs] / 1e18); tok0.append(mi[0][7 - qs] / 1e18)
        print("  first mint ETH", q(eth0), " token", q(tok0), " mints/pool", Counter(nmints).most_common(4), " ETH values top", Counter(round(x, 3) for x in eth0).most_common(5))
    else:
        rng = Counter(); single = Counter(); nm = []; eth0 = []; widths = []
        for r in rs:
            o = E[r["pool"]]; qs = r["quote_side"]
            mi = [e for e in o["ev"] if e[0] == "mi"]
            nm.append(len(mi))
            if not mi: continue
            m = mi[0]
            lo, hi = m[6], m[7]
            full = lo <= -887000 and hi >= 887000
            rng["full" if full else "partial"] += 1
            a0, a1 = m[9], m[10]
            aq, at = (a0, a1) if qs == 0 else (a1, a0)
            single["token-only" if aq == 0 else "both" if at > 0 else "eth-only"] += 1
            eth0.append(aq / 1e18); widths.append(hi - lo)
        print("  ranges", rng.most_common(), " sides", single.most_common(), " mints/pool", Counter(nm).most_common(4), " first-mint ETH", q(eth0), " width ticks", q(widths))
        ex = rs[len(rs)//2]; o = E[ex["pool"]]
        print("  example", ex["pool"], ex["launch_utc"], "qs", ex["quote_side"], "fee", ex["fee"], "ts", ex["tick_spacing"])
        for e in o["ev"][:6]: print("   ", [e[0], e[1] - o["lb"]] + e[5:12])
