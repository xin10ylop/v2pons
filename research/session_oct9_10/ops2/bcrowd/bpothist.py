"""B pot history over all cached blocks (bc cache, local only): every address that sends plain ETH to >= 15 B wallets (dispatcher) or
receives from >= 15 B wallets (sweep); for each: its other inputs/outputs in the cache."""
import os, json, collections
from libb import *
b = json.load(open('../../ops/b_list.json')); B = set(b['B']); A = set(b['A'])
D = bc.D; seen = set()
outB = collections.defaultdict(list); inB = collections.defaultdict(list); allp = collections.defaultdict(list)
files = sorted(os.listdir(D))
for fn in files:
    if not fn.endswith(".json"): continue
    try: d = json.load(open(D + fn))
    except Exception: continue
    for k, (ts, tl) in d.items():
        bn = int(k)
        if bn < 82900000 or bn in seen: continue
        seen.add(bn)
        for t in tl:
            if int(t[3]) <= 0 or t[5] not in ("0x", ""): continue
            if t[2] in B and t[1] not in B: outB[t[1]].append((bn, ts, t))
            if t[1] in B and t[2] not in B: inB[t[2]].append((bn, ts, t))
            allp[t[1]].append((bn, ts, t)); allp[t[2]].append((bn, ts, t))
ev = []
for a, l in outB.items():
    if len({x[2][2] for x in l}) >= 15: ev.append(("DISP", a, l))
for a, l in inB.items():
    if len({x[2][1] for x in l}) >= 15: ev.append(("SWEEP", a, l))
ev.sort(key=lambda e: min(x[0] for x in e[2]))
for kind, a, l in ev:
    bn0 = min(x[0] for x in l); ts0 = min(x[1] for x in l)
    other = sorted([x for x in allp[a] if x[2][1] not in B and x[2][2] not in B], key=lambda x: x[0])
    sB = sum(int(x[2][3]) for x in l) / 1e18
    print(time.strftime("%m-%d %H:%M", time.gmtime(ts0)), bn0, kind, a[:10], "B wallets", len({(x[2][1] if kind == "SWEEP" else x[2][2]) for x in l}), "B eth %.4f" % sB,
          "| other:", [(x[0], x[2][1][:10], "->", x[2][2][:10], round(int(x[2][3]) / 1e18, 4), "n%d" % x[2][4]) for x in other][:4])
