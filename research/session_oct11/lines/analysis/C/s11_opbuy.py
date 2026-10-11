"""The first real buy ("operator's buy") per family: offset p10/50/90, size, missing share, its price move (token price in ETH,
before -> after that swap, from the synced simulator state), who (launch wallet / multi-pool wallet / single-use), and the liquidity
present (ETH side for V2; L for V3)."""
import sys, os, pickle, statistics as st
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fams import *
from replay import *
R = load_rows(); FP = fam_pools(R); E = pickle.load(open(os.path.join(OUT, "ev.pkl"), "rb"))
def q(xs, ps=(.1, .5, .9), f="%.4g"):
    xs = sorted(x for x in xs if x is not None)
    return "/".join(f % xs[min(len(xs)-1, int(p*len(xs)))] for p in ps) if xs else "-"
def frb_move(r):
    o = E[r["pool"]]; lb = o["lb"]; sim = make_sim(r); qs = r["quote_side"]
    for e in o["ev"]:
        if e[0] == "s" and e[1] - lb == r["frb"]["off"] and sim.ok():
            if r["dex"] == "v3":
                dq = e[7] if qs == 0 else e[8]
            else:
                dq = (e[6] if qs == 0 else e[7]) if (e[8] if qs == 0 else e[9]) == 0 else 0
            if dq / 1e18 >= 0.005 - 1e-12:
                p0 = sim.price(); sim.apply(e); p1 = sim.price()
                liq = (sim.x / 1e18) if r["dex"] != "v3" else max(sim.pos.values())
                return p1 / p0 - 1, liq
        sim.apply(e)
    return None, None
for name in ["tok:0f34e3b5", "tok:70adce63", "lc:0a493d1a|13ead562", "tok:203caacb*", "tok:fbe37854", "tok:884da06b", "tok:d4e7eae4", "lc:0a493d1a|ac9650d8", "lc:89885b75|d27d1e00", "tok:97c7ba1b", "tok:2be340ff", "lc:b09ef517|e9ae5c53", "tok:c40bd4ef"]:
    if name == "tok:203caacb*":
        rs = [r for r in FP["lc:0a493d1a|13ead562"] if r["fam"]["tok"].startswith("203caacb")]
    else:
        rs = FP[name]
    rs = [r for r in rs if r["dex"] != "v4"]
    fr = [r for r in rs if r["frb"]]
    mv = [frb_move(r) for r in fr]
    who = Counter("launch-wallet" if r["frb"]["eoa_is_launch_wallet"] else "single-use" if (r["frb"]["eoa_npools_seen"] or 0) <= 1 else "multi-pool(>=10)" if r["frb"]["eoa_npools_seen"] >= 10 else "multi-pool(2-9)" for r in fr)
    print(f"{name}: n {len(rs)}  frb missing {1 - len(fr)/len(rs):.3f}  off p10/50/90 {q([r['frb']['off'] for r in fr], f='%d')}  eth p10/50/90 {q([r['frb']['eth'] for r in fr])}  "
          f"price move p10/50/90 {q([m[0]*100 for m in mv if m[0] is not None], f='%+.1f%%')}  liquidity at frb {q([m[1] for m in mv if m[1] is not None])}  who {who.most_common()}  distinct frb wallets {len(set(r['frb']['eoa'] for r in fr))}")
