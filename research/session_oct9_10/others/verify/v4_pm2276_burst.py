#!/usr/bin/env python3
"""PM2276 with the 0.01 ETH minimum trigger: where does our buy land relative to the burst? The burst = the run of buy blocks from the
trigger with gaps <= 2 blocks. Variants: head of trigger+1 (the census), after the whole trigger+1 block, after the burst. Also: how many
of the trigger txs carry ETH as tx value (the engine sees only those)."""
import sys, os, json, pickle, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
exec(open(os.path.join(HERE, "v2_price.py")).read().split("B0 = 82878144")[0])
TX = pickle.load(open(os.path.join(HERE, "..", "cache_crowdtx.pkl"), "rb"))
pids = [p for p, r in R.items() if r["logs"] and r["hooks"] == Z and FAMS["pm2276"](r)]
res = {"head_t+1": [], "after_t+1_block": [], "after_burst": [], "after_burst_hold30": []}; vis = {"value>0": 0, "value0": 0, "unknown": 0}; bl = []
for p in pids:
    P = prep(p); b0 = P["b0"]
    big = [s for s in P["sw"] if -s[2] >= 10**16 and 6 < s[0] - b0 <= 150]
    if not big: continue
    t = big[0][0]
    # burst extent
    buys = sorted({s[0] for s in P["sw"] if s[2] < 0 and s[0] >= t})
    end = t
    for b in buys:
        if b - end <= 2: end = b
        else: break
    nb = sum(1 for s in P["sw"] if s[2] < 0 and t <= s[0] <= end); bl.append((end - t, nb))
    for k, B, h in (("head_t+1", t + 1, 2), ("after_t+1_block", t + 2, 2), ("after_burst", end + 1, 2), ("after_burst_hold30", end + 1, 30)):
        x = trade(P, B, h, 1)
        if x: res[k].append(x["ret"])
for k, v in res.items():
    print(f"{k:20s} n {len(v)} mean {100*st.mean(v):+.2f}% median {100*st.median(v):+.2f}% pos {sum(1 for a in v if a > 0)}")
print("burst length blocks p10/50/90", [sorted(a for a, b in bl)[int(q*(len(bl)-1))] for q in (.1,.5,.9)], "buys in burst p10/50/90", [sorted(b for a, b in bl)[int(q*(len(bl)-1))] for q in (.1,.5,.9)])
