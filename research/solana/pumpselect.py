#!/usr/bin/env python3
"""pumpselect.py OUTDIR: picks the operators for the deeper sample (stage B) from the screening (stage A) scan, and records which
launches were already seen (offline).

Picked: an op-wallet wave (pumpscan.py's has_wave) in half or more of the screened launches and a dump clock in 4+ of them; or,
with a dump clock in 4+ screened launches, a mean hindsight exit at 0.5 SOL above +0.05 SOL (a lift after slot c+1 worth 10% to
take) and clocks within a factor of 2 (p75 <= 2 x p25); or one of the 40 operators with the most launches. The screening's own paper P&L is not used, so the paper trades
on the launches stage B adds are a clean out-of-sample test of the picked operators.
Writes OUTDIR/stageB_ids.txt and OUTDIR/stageA_mints.json."""
import json, sys, statistics as st

outdir = sys.argv[1]
d = json.load(open(outdir + "/wave.json"))
ops = sorted(d["ops"], key=lambda o: -o["n_window"])
top = {o["id"] for o in ops[:40]}
pick, why = [], {}
for o in ops:
    L = o["launches"]
    if not L:
        continue
    w = sum(l["has_wave"] for l in L) / len(L)
    clk = sorted(l["clock_slot"] for l in L if l["clock_slot"] is not None)
    h = [l["hind"].get("end0.5") for l in L if l["hind"].get("end0.5") is not None]
    reg = len(clk) >= 4 and clk[3 * len(clk) // 4] <= 2 * max(1, clk[len(clk) // 4])
    r = []
    if w >= 0.5 and len(clk) >= 4:
        r.append("wave")
    if reg and h and st.mean(h) > 0.05:
        r.append("lift+clock")
    if o["id"] in top:
        r.append("top40")
    if r:
        pick.append(o["id"]); why[o["id"]] = r
open(outdir + "/stageB_ids.txt", "w").write("\n".join(pick) + "\n")
json.dump(sorted(l["mint"] for o in d["ops"] for l in o["launches"]), open(outdir + "/stageA_mints.json", "w"))
from collections import Counter
print(f"{len(pick)} operators picked: " + str(Counter(tuple(v) for v in why.values()).most_common()))
