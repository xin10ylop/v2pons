"""C-1 ETH: the buy wave after the first real buy (events), returns of follow d2/H60 by frb offset bucket, ours-in-pool check, one worked example."""
from cands import *
from replay import *
rows = rows_nonvbot(); E = load_ev()
rs = [r for r in rows if CANDS["C1_eth"](r)]
print("pools with our own engine's trades (ours):", sum(1 for r in rs if r.get("ours")))
Ps = {r["pool"]: prep(r, E[r["pool"]]) for r in rs}
fr = [r for r in rs if r.get("frb")]
nb, eth, nsell, selleth, rise = [], [], [], [], []
for r in fr:
    P = Ps[r["pool"]]; f0 = P["lb"] + r["frb"]["off"]
    w60 = [w for w in P["sw"] if f0 < w["bn"] <= f0 + 62]
    b = [w for w in w60 if w["buy"]]; s = [w for w in w60 if not w["buy"]]
    nb.append(len(b)); eth.append(sum(w["q"] for w in b) / 1e18); nsell.append(len(s)); selleth.append(sum(w["q"] for w in s) / 1e18)
print("after the first real buy, blocks (frb, frb+62]: buys p10/50/90", p1050(nb), " buy ETH", p1050(eth), " sells", p1050(nsell), " sell ETH", p1050(selleth))
# returns by frb offset bucket (follow d2 H60)
bk = C.defaultdict(list)
for r in fr:
    o = r["frb"]["off"]; a = o + 2; x = replay(r, Ps[r["pool"]], a, a + 60)
    if x: bk[min(o // 50 * 50, 300)].append(x)
for k in sorted(bk): print(f"  frb offset {k}-{k+49}: {stats(bk[k])}")
# worked example: the first pool on day 6 with a frb
r = [x for x in fr if day_of(x) == 6][0]; P = Ps[r["pool"]]
print("\nexample", r["pool"], r["launch_utc"], "launch tx", r["launch_tx"], "frb", r["frb"]["off"], r["frb"]["eth"], r["frb"]["eoa"])
for w in P["sw"][:14]:
    print("   +%d %s q=%.6f sqrt=%d L=%d" % (w["bn"] - P["lb"], "B" if w["buy"] else "S", w["q"] / 1e18, w["sqrt"], w["L"]))
a = r["frb"]["off"] + 2; x = replay(r, P, a, a + 60); print("   follow a=%d b=%d ->" % (a, a + 60), x)
print("   pulls:", [p - P["lb"] for p in P["pulls"]][:3])
