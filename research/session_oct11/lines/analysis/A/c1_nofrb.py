"""C-1: the pools without a first real buy: when are they pulled; the first buy via the operator router (any size) vs pulls; per day."""
from cands import *
OPR = "0xd6d35b56237a05afd4cd7e441226fefc3f78c4e6"
rows = rows_nonvbot()
for name in ("C1_eth", "C1_weth"):
    rs = [r for r in rows if CANDS[name](r)]
    nf = [r for r in rs if not r.get("frb")]
    print(f"{name}: {len(rs)} pools, no frb {len(nf)} ({len(nf)/len(rs):.3f}); no-frb pulled {sum(1 for r in nf if r.get('n_pulls'))}, pull off p10/50/90 {p1050([r['first_pull_off'] for r in nf if r.get('n_pulls')])}")
    print("   no-frb share by day:", [round(sum(1 for r in nf if day_of(r) == d) / max(1, sum(1 for r in rs if day_of(r) == d)), 2) for d in range(7)])
    print("   no-frb pools: n_buys p10/50/90", p1050([r["n_buys"] for r in nf]), " buy_eth_total p50", pct([r["buy_eth_total"] for r in nf], .5), " any OPR buy in first 12:", sum(1 for r in nf if any(s[4] == OPR for s in r["swaps12"] or [])))
    fr = [r for r in rs if r.get("frb")]
    print("   frb pools pulled:", sum(1 for r in fr if r.get("n_pulls")), " pull - frb p10/50/90:", p1050([r["first_pull_off"] - r["frb"]["off"] for r in fr if r.get("n_pulls")]))
    # among all pools: share with a pull before offset X, and share with frb before X
    for X in (100, 150, 200, 250, 300):
        print(f"   by +{X}: frb seen {sum(1 for r in rs if r.get('frb') and r['frb']['off'] < X)/len(rs):.3f}  pulled {sum(1 for r in rs if r.get('n_pulls') and r['first_pull_off'] <= X)/len(rs):.3f}  pulled with no frb before it {sum(1 for r in rs if r.get('n_pulls') and r['first_pull_off'] <= X and not (r.get('frb') and r['frb']['off'] < r['first_pull_off']))/len(rs):.3f}")
