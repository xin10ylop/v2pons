"""Step 9: the price path from the launch to +600: token price in ETH relative to the launch price (for the concentrated pools, the
price at the position's upper edge, which the first buy jumps to), at fixed offsets and around the fleet's first buy."""
from common import *
from v4sim import sqrt_at_tick
pools = load_pools()
def price(sq): return (2 ** 96 / sq) ** 2           # ETH per token (raw units)
def at(p, o):
    """sqrt at the head of block L+o (after every swap before that block)"""
    s0 = p["sqrt0"] if p["tu"] == 887272 else min(p["sqrt0"], sqrt_at_tick(p["tu"]))
    cur = s0
    for s in p["swaps"]:
        if s["o"] >= o: break
        cur = s["sqrt"]
    return cur, s0
offs = [100, 150, 200, 300, 400, 500, 600]
res = {o: [] for o in offs}; resT = {k: [] for k in ("T", "T+1", "T+10", "T+50", "T+100", "T+200", "T+300", "T+450")}; mx = []
for p in pools:
    if p["T"] is None: continue
    pull = p.get("pull_off", 10**9)
    for o in offs:
        if o < pull: c, s0 = at(p, o); res[o].append(price(c) / price(s0) - 1)
    for k in resT:
        o = p["T"] + (int(k[2:]) if "+" in k else 0)
        if o < pull: c, s0 = at(p, o); resT[k].append(price(c) / price(s0) - 1)
    ss = [s["sqrt"] for s in p["swaps"] if s["o"] <= 600]
    if ss: mx.append(price(min(ss)) / price(at(p, 0)[1]) - 1)
def q(xs, a): xs = sorted(xs); return xs[int(a * (len(xs) - 1))]
print("price vs the launch price, at the head of block L+o (pools not yet pulled):")
for o in offs: xs = res[o]; print(f"  +{o}: n {len(xs)} p10/50/90 {q(xs,.1):+.1%} {q(xs,.5):+.1%} {q(xs,.9):+.1%}")
print("relative to the fleet's first buy T (head of the block):")
for k, xs in resT.items(): print(f"  {k}: n {len(xs)} p10/50/90 {q(xs,.1):+.1%} {q(xs,.5):+.1%} {q(xs,.9):+.1%}")
print(f"max by +600: p10/50/90 {q(mx,.1):+.1%} {q(mx,.5):+.1%} {q(mx,.9):+.1%}")
