import sys, json
from tr import *
def funders(x, b, span=3000, want=1):
    """incoming value transfers to x, scanning back from block b in 200-block chunks"""
    x = x.lower(); got = []
    for end in range(b, b - span, -200):
        for n, t in sorted(touching([x], end - 199, end), reverse=True):
            if t[2] == x and t[3] > 0: got.append((n, t))
        if len(got) >= want: break
    return got
def chain(x, b, hops=4, indent=""):
    for _ in range(hops):
        g = funders(x, b)
        if not g: print(indent + f"{x[:12]}: no incoming transfer within 3000 blocks before {b}"); return
        n, t = g[0]
        print(indent + f"{x[:12]} <- {t[1]} {t[3]/1e18:.4f} ETH (its nonce {t[4]}) at blk {n} ({n-b:+d})")
        if t[4] > 50: print(indent + f"   {t[1][:12]} is an old wallet (nonce {t[4]})"); return
        x, b = t[1], n
P = json.load(open("../oct8_pools.json"))["pools"]
for blk in (83647992, 83402323):
    p = next(q for q in P if q["block"] == blk)
    print(f"== launch {blk} ({p['kind']}) deployer {p['from']}")
    chain(p["from"], blk)
save()
