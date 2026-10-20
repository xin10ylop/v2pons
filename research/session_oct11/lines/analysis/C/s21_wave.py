"""The V3 crowd line (0x73991a25 multicall 836 B, fee 100, value 0): the wave after the first real buy: real buys and ETH in
[frb, frb+20] and [frb, frb+60], the token price move from just before the frb to frb+20, the share of launches whose first real buy lands
by +60 (sold at frb+20 under the cap-80 rule), the crowd wallets and contracts, and the pull timing."""
import sys, os, pickle
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s15_honest as H
from replay import *
E = H.E; T = H.T
def q(xs, ps=(.1, .5, .9), f="%.4g"):
    xs = sorted(xs); return "/".join(f % xs[min(len(xs)-1, int(p*len(xs)))] for p in ps) if xs else "-"
L = [r for r in H.R.values() if r["dex"] == "v3" and (r["fam"]["lc"] or "").startswith("0a493d1a") and r["launch"]["selector"] == "ac9650d8"
     and r["launch"]["calldata_len"] == 836 and r["fee"] == 100 and r["launch"]["value_eth"] == 0]
n20, e20, n60, e60, mv = [], [], [], [], []
crowd_to = Counter(); crowd_w = Counter()
for r in L:
    if not r["frb"]: continue
    f = r["frb"]["off"]; o = E[r["pool"]]; lb = o["lb"]; sim = make_sim(r); p0 = None; p20 = None
    b20 = [(off, dq) for off, dq, e in H.buys(r) if f <= off <= f + 20 and dq >= 5e15]
    b60 = [(off, dq) for off, dq, e in H.buys(r) if f <= off <= f + 60 and dq >= 5e15]
    n20.append(len(b20)); e20.append(sum(d for _, d in b20) / 1e18); n60.append(len(b60)); e60.append(sum(d for _, d in b60) / 1e18)
    for e in o["ev"]:
        if e[1] - lb >= f and p0 is None and sim.ok(): p0 = sim.price()
        if e[1] - lb > f + 20: break
        sim.apply(e)
    p20 = sim.price()
    if p0: mv.append(p20 / p0 - 1)
    for off, dq, e in H.buys(r):
        if f <= off <= f + 20 and dq >= 5e15:
            t = T.get(e[-1])
            if t: crowd_to[(t["to"][:10], t["selector"], t["calldata_len"])] += 1; crowd_w[t["from"]] += 1
print(f"launches {len(L)} ({len(L)/7:.1f}/day); with a real buy {sum(1 for r in L if r['frb'])}; real buy by +60: {sum(1 for r in L if r['frb'] and r['frb']['off'] <= 60)}; by +80: {sum(1 for r in L if r['frb'] and r['frb']['off'] <= 80)}")
print(f"frb off p10/50/90 {q([r['frb']['off'] for r in L if r['frb']], f='%d')}  eth {q([r['frb']['eth'] for r in L if r['frb']])}")
print(f"real buys in [frb, frb+20] p10/50/90 {q(n20, f='%d')}, ETH {q(e20)}; in [frb, frb+60] {q(n60, f='%d')}, ETH {q(e60)}")
print(f"token price move from before the frb to frb+20: p10/50/90 {q([m*100 for m in mv], f='%+.1f%%')}")
print(f"wave txs: contracts {crowd_to.most_common(5)}; distinct wallets {len(crowd_w)}; buys per wallet p50 {sorted(crowd_w.values())[len(crowd_w)//2]}")
pl = [r for r in L if r["n_pulls"]]
print(f"pulled {len(pl)}/{len(L)} at p10/50/90 {q([r['first_pull_off'] for r in pl], f='%d')}; min first pull {min(r['first_pull_off'] for r in pl)}; pull before frb {sum(1 for r in pl if r['pull_before_frb'])}; by launch wallet {sum(1 for r in pl if r['pull_by_launch_wallet'])}")
print(f"launch wallets {len(set(r['launch']['from'] for r in L))} nonce {Counter(r['launch']['nonce'] for r in L).most_common(3)}; mint L p10/50/90 {q([max(v for v in [e[8] for e in E[r['pool']]['ev'] if e[0]=='mi']) for r in L])}")
