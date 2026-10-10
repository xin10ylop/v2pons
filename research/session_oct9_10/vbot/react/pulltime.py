#!/usr/bin/env python3
"""Pull timing: per family, lifetime (launch -> pull) split into REACTIVE (an outsider buy >= 3e-5 ETH, by tx or by a non-Universal-Router
swap sender, within the 25 blocks before the pull) and OTHER; UTC hour-of-day of launches and pulls; minutes between consecutive pulls."""
import sys, os, json, datetime, statistics as st; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
P, TX, M = load(); BOTW, cls = classifier(TX)
RC = json.load(open(os.path.join(HERE, "recent.json")))
pts = sorted((x["b0"], x["ts"]) for x in RC["launches"])
(b1, t1), (b2, t2) = pts[0], pts[-1]; rate = (t2 - t1) / (b2 - b1)
ts = lambda b: t1 + (b - b1) * rate
print(f"block time {rate:.4f} s (fit on {len(pts)} launch blocks)")
def q(xs, qs=(0, .05, .1, .25, .5, .75, .9, 1)):
    xs = sorted(xs); return [xs[int(a * (len(xs) - 1))] for a in qs] if xs else None
OUT = {}
for fam in ("v3.0", "v5.0", "v2.433"):
    react, other = [], []; hrs_l = collections.Counter(); hrs_p = collections.Counter(); hrs_r = collections.Counter(); pull_blocks = []
    for v in P.values():
        if v["fam"] != fam: continue
        hrs_l[datetime.datetime.utcfromtimestamp(ts(v["b0"])).hour] += 1
        if v["pull"] is None: continue
        pb = v["b0"] + v["pull"]; pull_blocks.append(pb)
        trig = False
        for s in v["sw"]:
            if s["rel"] > v["pull"]: break
            if s["rel"] < v["pull"] - 25 or s["eth"] < 3e-5: continue
            k, t = cls(v, s)
            if k == "out" or (k is None and s["snd"] != UR): trig = True
        (react if trig else other).append(v["pull"])
        h = datetime.datetime.utcfromtimestamp(ts(pb)).hour; hrs_p[h] += 1
        if trig: hrs_r[h] += 1
    pull_blocks.sort(); gaps = [(b - a) * rate / 60 for a, b in zip(pull_blocks, pull_blocks[1:])]
    OUT[fam] = {"pulled": len(react) + len(other), "reactive": len(react), "reactive_lifetime_q": q(react), "other_lifetime_q": q(other),
                "other_by": {k: sum(1 for x in other if x <= k) for k in (30, 45, 60, 100, 300, 1000, 3000)},
                "launch_hour_utc": dict(sorted(hrs_l.items())), "pull_hour_utc": dict(sorted(hrs_p.items())), "reactive_pull_hour_utc": dict(sorted(hrs_r.items())),
                "minutes_between_pulls_q": [round(x, 2) for x in q(gaps)]}
    print(fam, json.dumps(OUT[fam]))
json.dump(OUT, open(os.path.join(HERE, "pulltime.json"), "w"), indent=1)
