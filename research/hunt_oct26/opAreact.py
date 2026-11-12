#!/usr/bin/env python3
"""opAreact.py [LINE_JSON]: does operator A pull on a TRUE outsider? Its crowd is large and rotating (dozens of wallets, many in under 10%
of pools), so a fixed crew threshold misfiles crowd wallets as outsiders. Here: crowd = any wallet that buys in 3+ of the line's pools;
true outsider = a wallet that buys (0.001 ETH+) in only 1-2 of them, not the launcher, not the 2e-6 dust bot. For each pool with a true
outsider: blocks from its first buy to the pull, whether it ever sold, and the crowd ETH that came after it; against the pull time of clean
pools. Read-only (the lineprobe line file)."""
import sys, json, collections, statistics as st
D = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "out/line_rh_0x3194e326_644.json"))
P = D["pools"]; DUST = {"0xe71a69f434a719cd5afa411568b69716aab3b84a"}
cnt = collections.Counter()
for p in P:
    for w in {e[2] for e in p["ev"] if e[1] > 0 and e[2]}:
        cnt[w] += 1
crowd = {w for w, n in cnt.items() if n >= 3}
print(f"{len(P)} pools; wallets that buy in 3+ pools (the crowd): {len(crowd)}")
fr = []; clean = []
for p in P:
    ev = sorted(p["ev"]); pull = min((o for o, _ in p["pulls"]), default=None)
    outs = [e for e in ev if e[1] >= 0.001 and e[2] not in crowd and e[2] != p["launcher"] and e[2] not in DUST]
    if outs:
        o = outs[0]; w = o[2]
        sold = any(e[2] == w and e[1] < 0 for e in ev)
        after = sum(e[1] for e in ev if e[2] in crowd and e[1] >= 0.005 and e[0] > o[0])
        fr.append({"id": p["id"], "off": o[0], "eth": o[1], "pull": pull, "lag": (pull - o[0]) if pull is not None else None, "sold": sold, "crowd_after": after})
    else:
        clean.append(pull)
lags = [r["lag"] for r in fr if r["lag"] is not None]
print(f"pools with a true outsider: {len(fr)}; clean pools: {len(clean)}")
if lags:
    sl = sorted(lags)
    print(f"  blocks from the outsider's buy to the pull: median {st.median(sl):g}, p25 {sl[len(sl)//4]}, p75 {sl[3*len(sl)//4]}; within 10 blocks: {sum(l<=10 for l in sl)}/{len(sl)}, within 50: {sum(l<=50 for l in sl)}/{len(sl)}")
print(f"  outsiders that sold before the pull: {sum(1 for r in fr if r['sold'])}/{len(fr)}")
print(f"  crowd ETH arriving after the outsider: median {st.median([r['crowd_after'] for r in fr]):.3f}" if fr else "")
cp = sorted(x for x in clean if x is not None)
if cp:
    print(f"clean pools: pull at median +{st.median(cp):g} (p10 +{cp[len(cp)//10]})")
print("\nfirst 25 pools with a true outsider (outsider offset, ETH -> pull offset, lag, sold?, crowd ETH after):")
for r in sorted(fr, key=lambda r: r["off"])[:25]:
    print(f"  {r['id'][:14]}  +{r['off']:<5} {r['eth']:.4f} -> pull +{r['pull']}  lag {r['lag']}  sold {r['sold']}  crowd after {r['crowd_after']:.3f}")
