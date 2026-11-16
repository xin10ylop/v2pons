#!/usr/bin/env python3
"""wave1380.py DUMP.json[,DUMP.json...] DAYS: operator A's 1,380 B line (PositionManager modifyLiquidities, 1,380 B; 4,655 B clean ERC-20
tokens; fee 0, no hook) -- does buying early and selling later pay, with the crowd buying AND selling?

For every pool of the line in the dumps: our STAKE in at launch + ENTRY (head of that block), every recorded swap replayed on the pool's
virtual reserves with our trade in it (buys: the same native in; sells: the same tokens in), our tokens sold at the end of launch + EXIT;
a pull at or before the exit = -100%. Also: the share of pools where the price at EXIT is above the price at ENTRY, and the pull time.
Read-only (the dumps, the census files, the launch and token-code caches)."""
import sys, json, os, statistics as st, collections

HERE = os.path.dirname(os.path.abspath(__file__))
DUMPS = sys.argv[1].split(","); DAYS = sys.argv[2].split(",")
lc = json.load(open(os.path.join(HERE, "out/struct_launch_rh.json"))); cc = json.load(open(os.path.join(HERE, "out/token_code_rh.json")))
created = {}
for d in DAYS:
    for k, tok, bn, tx, nin in json.load(open(os.path.join(HERE, f"out/rh_{d}_00.json")))["chains"]["rh"]["created"]:
        created[k] = tx
pools = []
for f in DUMPS:
    for k, p in json.load(open(f))["pools"].items():
        t = lc.get(created.get(k))
        if t and t[1].startswith("0x58daec31") and t[2] == "0xdd46508f" and t[3] == 1380 and cc.get(p["tok"], ["?", 0])[1] == 4655:
            pools.append(p)
print(f"{len(pools)} pools of the 1,380 B line with 4,655 B tokens in {len(DUMPS)} dump(s)")


def ride(p, entry, exit_, stake):
    ev = [e for e in p["ev"] if e[4] and e[5]]
    if not ev:
        return None
    if p["pull"] is not None and p["pull"] - p["bn"] <= exit_:
        return -1.0
    F = 1 - (p["f"] or 0)
    first = ev[0]; x = first[4] - first[2] * F; y = first[5] + first[3]          # reserves before the first swap (native, token)
    ours = None
    for e in ev:
        off = e[0] - p["bn"]
        if ours is None and off >= entry:
            s = stake * F; ours = y * s / (x + s); x += stake; y -= ours
        if off > exit_:
            break
        n, t = e[2], e[3]
        if n > 0:
            s = n * F; out = y * s / (x + s); x += n; y -= out
        elif t < 0:
            tin = -t; out = x * tin * F / (y + tin * F); x -= out; y += tin
    if ours is None:
        return None                                                                 # nothing traded after our entry: no test
    return (x * ours * F / (y + ours * F) - stake) / stake


for stake in (0.05, 0.2):
    print(f"\nstake {stake} ETH (fee as recorded, mostly 0; no gas)")
    for entry in (5, 50, 200):
        cells = []
        for exit_ in (600, 1200, 2400, 4800, 5900):
            r = [ride(p, entry, exit_, stake) for p in pools]; r = [v for v in r if v is not None]
            if r:
                cells.append(f"x{exit_}: {st.mean(r):+.0%} med {st.median(r):+.0%} won {sum(v > 0 for v in r)}/{len(r)} pulled {sum(v <= -1 for v in r)}")
        print(f"  in +{entry}: " + " | ".join(cells))
pulls = sorted(p["pull"] - p["bn"] for p in pools if p["pull"] is not None)
print(f"\npulled within 2 h: {len(pulls)}/{len(pools)}; pull offsets: median {st.median(pulls) if pulls else '-'}, p10 {pulls[len(pulls)//10] if pulls else '-'}")
print("crowd buys vs sells per pool (native, first 6,000 blocks): median buys {:.2f}, sells {:.2f}".format(
    st.median([sum(e[2] for e in p["ev"] if e[2] > 0) for p in pools]), st.median([sum(-e[2] for e in p["ev"] if e[2] < 0) for p in pools])))
