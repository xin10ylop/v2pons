"""Can a non-operator wallet sell, and does the token take a transfer tax? From the fetched swap transactions (EOA known): per pool and
wallet, tokens the pool sent on its buys vs tokens the pool received on its sells. A wallet that sold its whole bag with no transfer
tax shows sold/bought = 1.000; a tax shows up as a ratio capped below 1. Also: sells by wallets other than the launch wallet that
returned ETH, and the token code size."""
import sys, os, pickle
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fams import *
R = load_rows(); FP = fam_pools(R); T = pickle.load(open(os.path.join(OUT, "tx.pkl"), "rb")); E = pickle.load(open(os.path.join(OUT, "ev.pkl"), "rb"))
def q(xs, ps=(.1, .5, .9)):
    xs = sorted(xs); return "/".join(f"{xs[min(len(xs)-1, int(p*len(xs)))]:.4f}" for p in ps) if xs else "-"
for name in ["tok:0f34e3b5", "tok:70adce63", "lc:0a493d1a|13ead562", "tok:d4e7eae4", "lc:0a493d1a|ac9650d8", "lc:89885b75|d27d1e00", "lc:b09ef517|e9ae5c53"]:
    rs = [r for r in FP[name] if r["dex"] != "v4"]
    ratios = []; pools_with_outside_sell = 0; outside_sell_eth = 0.0; n_outside_sells = 0
    for r in rs:
        o = E[r["pool"]]; qs = r["quote_side"]; lw = r["launch"]["from"]
        bought = defaultdict(int); sold = defaultdict(int); any_out = False
        for e in o["ev"]:
            if e[0] != "s": continue
            t = T.get(e[-1]);
            if not t: continue
            w = t["from"]
            if r["dex"] == "v3":
                dq, dt = (e[7], e[8]) if qs == 0 else (e[8], e[7])
                if dq > 0: bought[w] += -dt
                else:
                    sold[w] += dt
                    if w != lw and -dq > 0: any_out = True; outside_sell_eth += -dq / 1e18; n_outside_sells += 1
            else:
                qin, tin, qout, tout = (e[6], e[7], e[8], e[9]) if qs == 0 else (e[7], e[6], e[9], e[8])
                if qin > 0 and tout > 0: bought[w] += tout
                elif tin > 0:
                    sold[w] += tin
                    if w != lw and qout > 0: any_out = True; outside_sell_eth += qout / 1e18; n_outside_sells += 1
        pools_with_outside_sell += any_out
        for w in sold:
            if bought.get(w): ratios.append(sold[w] / bought[w])
    full = [x for x in ratios if x > 0.98]
    print(f"{name}: pools {len(rs)}  token code size {Counter(r['token_code']['size'] for r in rs).most_common(3)}")
    print(f"   pools with a sell by a non-launch wallet that returned ETH: {pools_with_outside_sell} ({n_outside_sells} sells, {outside_sell_eth:.3f} ETH)")
    print(f"   wallets with buy+sell seen: {len(ratios)}  sold/bought p10/50/90 {q(ratios)}  ratio in [0.999,1.001]: {sum(1 for x in ratios if abs(x-1) < 1e-3)}  max {max(ratios) if ratios else None}")
