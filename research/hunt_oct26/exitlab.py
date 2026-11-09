#!/usr/bin/env python3
"""exitlab.py DUMP.json [MIN_POOLS]: find 2.433-type lines — a scheduled buyer AND a real exit for outsiders — from a buyerlab DUMP.

buyerlab groups every pool into a line (its token-code template) and resolves every swap to the EOA behind it. This reads that dump and,
for each line (5+ pools), measures the two things that made the 2.433 seat tradeable and that every defended line fails:

  scheduled   a buyer in most of the line's pools at a tight offset and one size (the bot we would front). Reported: the tightest such
              buyer's median offset, size, and the share of its buys within +-2 blocks of its median.
  real exit   does a NON-crew, non-launcher wallet that buys actually get out? For every such outsider in every pool, its token balance is
              tracked across its own buys and sells; a round trip = it sold 80%+ of what it bought before the pool's pull. Reported per
              line: how many outsiders bought, what share completed a round trip, their median round-trip return (native out / native in - 1),
              and the share whose pull came before they could sell (the honeypot / rug signature).

crew = a wallet buying in 10%+ of the line's pools (3+); it is the operator's own fleet, never counted as an outsider. A line is
2.433-type when a scheduled buyer is present AND most outsiders round-trip at a profit with few cut off by the pull. Read-only (the dump)."""
import sys, json, collections, statistics as st

D = json.load(open(sys.argv[1])); MIN_POOLS = int(sys.argv[2]) if len(sys.argv) > 2 else 5
pools = D["pools"]
by_line = collections.defaultdict(list)
for pid, p in pools.items():
    by_line[tuple(p["grp"])].append(pid)

# crew per line: a wallet that buys in 10%+ of the line's pools (>=3)
crew = {}
for line, pids in by_line.items():
    c = collections.Counter()
    for pid in pids:
        firsts = {w for _, _, _, w in pools[pid]["swaps"] if w not in ("?", None)}  # distinct buyers/sellers in the pool
        bought = {w for _, nat, _, w in pools[pid]["swaps"] if nat > 0 and w not in ("?", None)}
        for w in bought:
            c[w] += 1
    crew[line] = {w for w, n in c.items() if n >= max(3, 0.1 * len(pids))}

rows = []
for line, pids in by_line.items():
    if len(pids) < MIN_POOLS:
        continue
    cr = crew[line]
    # scheduled buyers: crew wallets, their first-buy offset and size across pools
    offs = collections.defaultdict(list); szs = collections.defaultdict(list)
    for pid in pids:
        p = pools[pid]; bn = p["bn"]; seen = set()
        for blk, nat, tok, w in sorted(p["swaps"]):
            if nat > 0 and w in cr and w not in seen and w != p["launcher"]:
                offs[w].append(blk - bn); szs[w].append(nat); seen.add(w)
    sched = None
    for w, ol in offs.items():
        if len(ol) < max(3, 0.3 * len(pids)):
            continue
        med = st.median(ol); tight = sum(1 for o in ol if abs(o - med) <= 2) / len(ol)
        cand = (tight, len(ol), w, med, st.median(szs[w]))
        if sched is None or cand > sched:
            sched = cand
    # real exit: every non-crew, non-launcher buyer's round trip
    trips = []            # (return, cut_off_by_pull)
    n_out_buyers = 0
    for pid in pids:
        p = pools[pid]; pull = p["pull"]
        bal = collections.defaultdict(float); nat_in = collections.defaultdict(float); nat_out = collections.defaultdict(float); sold = collections.defaultdict(float); bought = collections.defaultdict(float)
        for blk, nat, tok, w in sorted(p["swaps"]):
            if w in ("?", None) or w in cr or w == p["launcher"]:
                continue
            if nat > 0:                       # a buy
                bal[w] += tok; nat_in[w] += nat; bought[w] += tok
            else:                              # a sell
                bal[w] += tok; nat_out[w] += -nat; sold[w] += -tok
        for w in bought:
            if bought[w] <= 0:
                continue
            n_out_buyers += 1
            got_out = sold[w] >= 0.8 * bought[w]
            cut = (pull is not None) and not got_out      # a pull and they never sold 80%+
            if got_out:
                trips.append((nat_out[w] / nat_in[w] - 1 if nat_in[w] > 0 else 0.0, False))
            elif cut:
                trips.append((-1.0, True))
    done = [r for r, _ in trips]
    rt_rate = (sum(1 for r, c in trips if not c and r > -0.999) / n_out_buyers) if n_out_buyers else 0.0
    pull_rate = (sum(1 for r, c in trips if c) / n_out_buyers) if n_out_buyers else 0.0
    rows.append({"line": line, "pools": len(pids), "sched": sched, "out_buyers": n_out_buyers,
                 "roundtrip_rate": rt_rate, "median_rt": st.median([r for r, c in trips if not c]) if any(not c for _, c in trips) else None,
                 "pull_before_sell_rate": pull_rate, "crew": len(cr)})

# a 2.433-type line: a scheduled buyer present, outsiders round-trip, few cut off
rows.sort(key=lambda r: (-(r["sched"] is not None), -r["roundtrip_rate"], -(r["out_buyers"])))
print(f"{len(rows)} lines with {MIN_POOLS}+ pools. A 2.433-type line = scheduled buyer + outsiders exit (high round-trip, low pull-before-sell).\n")
print(f"{'line':34s} pools  sched(off/size/tight/n)         out  rt%   medRT   pull%  crew")
for r in rows:
    s = r["sched"]
    sched = f"+{s[3]:g}/{s[4]/1e18 if s[4]>1e6 else s[4]:.4g}/{s[0]:.0%}/{s[1]}" if s else "-- none --"
    med = f"{r['median_rt']:+.0%}" if r["median_rt"] is not None else "  -"
    name = str(r["line"][1])[:32]
    print(f"{name:34s} {r['pools']:4d}  {sched:30s}  {r['out_buyers']:4d}  {r['roundtrip_rate']:.0%}  {med:>6}  {r['pull_before_sell_rate']:.0%}  {r['crew']}")
