#!/usr/bin/env python3
"""Every pull inside the tx-covered window (census <= +300, recent <= +600): what preceded it within 25 blocks (outsider buys by wallet,
bot buys/sells), and the pools' per-age pull hazard with and without a preceding outsider buy."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
P, TX, M = load(); BOTW, cls = classifier(TX)
res = collections.defaultdict(collections.Counter); ex = collections.defaultdict(list)
for v in P.values():
    covd = COV[v["src"]]
    if v["pull"] is None or v["pull"] > covd: continue
    pre = []
    miss = 0
    for s in v["sw"]:
        if s["rel"] > v["pull"]: break
        if v["pull"] - 25 <= s["rel"] <= v["pull"]:
            k, t = cls(v, s)
            if k is None: miss += 1; continue
            pre.append((s["rel"], k, "buy" if s["eth"] > 0 else "sell", s["eth"], t["from"]))
    ob = [x for x in pre if x[1] == "out" and x[2] == "buy"]
    key = "incomplete-tx" if miss else ("outsider buy within 25" if ob else "no outsider buy within 25")
    res[v["fam"]][key] += 1
    ex[(v["fam"], key)].append((v["b0"], v["pull"], [(x[0], x[1], x[2], round(x[3], 5), x[4][:10]) for x in pre]))
for f in res: print(f, dict(res[f]))
for k in (("v3.0", "no outsider buy within 25"), ("v5.0", "no outsider buy within 25"), ("v2.433", "no outsider buy within 25")):
    print(k, len(ex[k]))
    for e in ex[k][:60]: print("   ", e[0], "pull +%d" % e[1], e[2][-6:])
