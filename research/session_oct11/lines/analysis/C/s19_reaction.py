"""Does the operator pull after a stranger's buy? Unbiased version: only the first 12 swaps of each pool (fetched for every pool).
Crowd fingerprints = (to, selector, calldata length) carrying >= 5% of the family's buys >= 0.005 ETH among those swaps; a stranger buy =
a buy >= 0.001 ETH among the first 12 swaps, not by the launch wallet, with another fingerprint. Compare the share of pools pulled within
D blocks after the stranger's buy with the share pulled within D blocks after the first crowd buy in pools without a stranger."""
import sys, os, pickle
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fams import *
R = load_rows(); FP = fam_pools(R)
for name in ["tok:0f34e3b5", "tok:70adce63", "tok:d4e7eae4", "lc:0a493d1a|13ead562", "lc:89885b75|d27d1e00"]:
    rs = [r for r in FP[name] if r["dex"] != "v4"]
    fp = Counter()
    for r in rs:
        for s in r["swaps12"]:
            if s[1] == "B" and s[2] >= 0.005: fp[(s[4], s[5], s[6])] += 1
    tot = sum(fp.values()); crowd = {k for k, v in fp.items() if v >= 0.05 * tot}
    ws, wo = [], []
    for r in rs:
        lw = r["launch"]["from"]; st = None; cr = None
        for s in r["swaps12"]:
            if s[1] != "B": continue
            if (s[4], s[5], s[6]) in crowd and s[2] >= 0.005 and cr is None: cr = s[0]
            if s[2] >= 0.001 and s[3] != lw and (s[4], s[5], s[6]) not in crowd and st is None: st = s
        if st: ws.append((r, st[0], st))
        elif cr is not None: wo.append((r, cr, None))
    print(f"\n{name}: crowd fingerprints {[(k[0][:10], k[1], k[2], v) for k, v in fp.most_common(4) if k in crowd]}")
    for D_ in (50, 100, 150, 300):
        a = sum(1 for r, off, s in ws if r["first_pull_off"] is not None and off <= r["first_pull_off"] <= off + D_)
        b = sum(1 for r, off, s in wo if r["first_pull_off"] is not None and off <= r["first_pull_off"] <= off + D_)
        print(f"  pulled within {D_} blocks: after a stranger's buy {a}/{len(ws)} ({a/max(1,len(ws)):.2f})  | after the first crowd buy, no stranger {b}/{len(wo)} ({b/max(1,len(wo)):.2f})")
    dl = sorted(r["first_pull_off"] - off for r, off, s in ws if r["first_pull_off"] is not None and r["first_pull_off"] >= off)
    print("  pull delay after the stranger (blocks), first 25:", dl[:25])
    print("  strangers:", Counter((s[4][:10], s[5]) for r, off, s in ws).most_common(5))

# 70adce63 and 0f34e3b5: where was the stranger relative to the operator's first buy, and did the operator still buy after a stranger?
print("\nstranger position vs the first real buy (frb), first 12 swaps")
for name in ["tok:70adce63", "tok:0f34e3b5"]:
    rs = FP[name]; rows = []
    for r in rs:
        lw = r["launch"]["from"]
        for s in r["swaps12"]:
            if s[1] == "B" and s[2] >= 0.001 and s[3] != lw and not (s[4].startswith("0x89e5db8b") and s[5] == "7ff36ab5" and s[6] == 228):
                rows.append((s[0], r["frb"]["off"] if r["frb"] else None, r["first_pull_off"])); break
    before = [x for x in rows if x[1] is not None and x[0] < x[1]]
    print(f"  {name}: strangers {len(rows)}; before the frb {len(before)}: " + str([(a, f, p) for a, f, p in before][:12]))
