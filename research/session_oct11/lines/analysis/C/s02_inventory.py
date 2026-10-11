"""Inventory of V2/V3 families (tok and lc keys) with >= 10 launches: liquidity, real buys, frb offset, pulls."""
import pickle, os, statistics as st
from collections import Counter, defaultdict
OUT = os.path.dirname(os.path.abspath(__file__))
R = pickle.load(open(os.path.join(OUT, "v23.pkl"), "rb"))
V = {k: r for k, r in R.items() if r["dex"] != "v4" and not r["quote_pair"]}
def q(xs, p):
    xs = sorted(xs); return xs[min(len(xs) - 1, int(p * len(xs)))] if xs else None
for g in ("tok", "lc"):
    fam = defaultdict(list)
    for r in V.values(): fam[r["fam"][g]].append(r)
    print(f"=== grouping {g}")
    print("key       n  dex  liq  frb  frb_off p10/50/90  frb_eth_med  pulled pull_off_med  liq_off_med  launchwallets  value_top")
    for k, rs in sorted(fam.items(), key=lambda x: -len(x[1])):
        if len(rs) < 10: continue
        frb = [r for r in rs if r["frb"]]
        if not frb and len(rs) < 200: continue
        liq = [r for r in rs if r["n_adds"]]
        offs = [r["frb"]["off"] for r in frb]
        pl = [r for r in rs if r["n_pulls"]]
        dexc = Counter(r["dex"] for r in rs).most_common(3)
        vals = Counter(round(r["launch"]["value_eth"], 4) for r in rs).most_common(3)
        lo = [r["liq_off"] for r in liq if r["liq_off"] is not None]
        print(f"{(k or 'None')[:8]}|{(k or '').split('|')[-1] if g=='lc' else ''} {len(rs)} {dexc} liq {len(liq)} frb {len(frb)} off {q(offs,.1)}/{q(offs,.5)}/{q(offs,.9)} eth {q([r['frb']['eth'] for r in frb],.5)} pulled {len(pl)} pulloff {q([r['first_pull_off'] for r in pl],.5)} liqoff {q(lo,.5)} wallets {len(set(r['launch']['from'] for r in rs))} vals {vals}")
