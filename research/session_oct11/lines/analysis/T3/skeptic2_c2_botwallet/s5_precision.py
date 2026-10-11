"""Stage 5: the candidate seen from the engine's side. Every bot-wallet tx (W0, causal wallet set, other pools) that falls inside an open
3.0 window (block in [L+1, T-1] of some slice pool) is a fire the engine would see. Per fire: is it 1..4 blocks ahead of that pool's T
(precision), what share of fires come before d 5 (fatal: the buy lands >= 3 blocks before T, the minimum pre-T pull lag), and the per-block
odds of a fire against the blocks 1..4 before T. Also the per-pool lead of the first fire after each arm offset (lead-time distribution).
Reads s4_rule.pkl and s2_parsed.pkl."""
import pickle, collections, os, statistics as st
from lib import *
os.chdir(HERE)
R = pickle.load(open("s4_rule.pkl", "rb")); D = pickle.load(open("s2_parsed.pkl", "rb")); P = {p["pid"]: p for p in D["pools"]}
V0 = "W0 any tx from a bot wallet (the candidate)"
for lab in ("SL", "NEW", "OLD"):
    S = [P[x] for x in R[lab]]
    ds = [p["Tbn"] - bn for p in S for bn in R["pre"][V0][p["pid"]] if bn < p["Tbn"]]
    c = collections.Counter(ds); n = len(ds)
    print(f"{lab}: fires (bot-wallet txs, other pools, in L+1..T-1) {n} over {len(S)} pools ({n / len(S):.1f} a pool); "
          f"at d 1..2 {sum(c[d] for d in (1, 2))} ({100 * sum(c[d] for d in (1, 2)) / n:.1f}%), d 1..4 {sum(c[d] for d in range(1, 5))} ({100 * sum(c[d] for d in range(1, 5)) / n:.1f}%), "
          f"d >= 5 {sum(v for d, v in c.items() if d >= 5)} ({100 * sum(v for d, v in c.items() if d >= 5) / n:.1f}%)")
    blocks = sum(p["Tbn"] - p["L"] - 1 for p in S)
    print(f"   share of window blocks that are d 1..4: {100 * 4 * len(S) / blocks:.1f}% (what a lead-free signal would give)")
    # first-fire lead per arm offset
    for a in (4, 10, 20, 30, 40):
        leads = []
        for p in S:
            f = [bn for bn in R["pre"][V0][p["pid"]] if bn >= p["L"] + a]
            if f: leads.append(p["Tbn"] - f[0])
        cc = collections.Counter(min(x, 30) for x in leads)
        print(f"   arm L+{a:<2d}: first fire in {len(leads)}/{len(S)} pools; lead T-b p10/25/50/75/90 {[pct(leads, x) for x in (.1, .25, .5, .75, .9)]}; "
              f"in 0..2 {sum(1 for x in leads if 0 <= x <= 2)}, 3..4 {sum(1 for x in leads if 3 <= x <= 4)}, >= 5 {sum(1 for x in leads if x >= 5)}")
