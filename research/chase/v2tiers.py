#!/usr/bin/env python3
"""v2tiers.py rh_v2.json: a v2scan.py file (Robinhood V2 factory 0x8bceaa40) per tier: the repeat buyers in the first 25 swaps and how soon
the pull followed each one (the reaction to a foreign buy); the line is the fresh creator at nonce 2 calling addLiquidityETH on router 0x89e5db8b."""
import json, collections, statistics as st, sys
d = json.load(open(sys.argv[1])); P = d["pairs"]; txs = d["txs"]
R = "89e5db8b5aa49aa85ac63f691524311aeb649eba"
for TIER in (1.0, 30.09, 40.59, 50.09):
    ps = {a: p for a, p in P.items() if p.get("nonce") == 2 and p.get("to") == R and p.get("sel") == "0xf305d719" and p.get("eth_in") and round(p["eth_in"], 2) == TIER}
    by = collections.defaultdict(list); fresh_only = 0; fresh_pull = []
    for a, p in ps.items():
        burn = p["burns"][0][0] if p["burns"] else None; seen = set()
        for s in p["swaps"][:25]:
            t = txs.get(s[6]); ein = s[2] if p["weth_is0"] else s[3]
            if not t or not ein or t[0] in seen: continue
            seen.add(t[0])
            if t[2] > 0 or t[1] != R: by[t[0]].append((s[0] - p["bn"], (burn - s[0]) if burn else None, ein / 1e18))
        multi = [w for w in seen if w in by]
        if not any(len(by[w]) >= 1 and (txs and True) for w in multi): fresh_only += 1; fresh_pull.append((burn - p["bn"]) if burn else None)
    print(f"== tier {TIER}: {len(ps)} pairs; pairs with no non-fresh buyer in the first 25 swaps: {fresh_only}, their pull offsets median "
          f"{st.median([x for x in fresh_pull if x is not None]) if any(x is not None for x in fresh_pull) else None}")
    for w, ev in sorted(by.items(), key=lambda kv: -len(kv[1]))[:6]:
        gaps = [g for _, g, _ in ev if g is not None]
        print(f"   {w[:10]} bought on {len(ev)} pairs at +{st.median([o for o, _, _ in ev]):.0f} median, {st.median([e for _, _, e in ev]):.5f} ETH; "
              f"pulled after it on {len(gaps)} (blocks after its buy: median {st.median(gaps) if gaps else None}, within 200: {sum(0 <= g <= 200 for g in gaps)})")
