#!/usr/bin/env python3
"""Reaction detail. Outsider buys AFTER the bot's first buy ('armed'), by size class; for each: pulled within 25 blocks?, lag, the bot's
buys/sells between the outsider buy and the pull; the special case of an outsider buy between the bot's 1st and 2nd buys (our entry slot).
Baseline: P(pull within the next 25 blocks) at a random block of a pool with no outsider buy around it. Pools with full tx coverage only."""
import sys, os, json, random, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
P, TX, M = load(); BOTW, cls = classifier(TX); random.seed(1)
SRC = sys.argv[1] if len(sys.argv) > 1 else "census"
R = []; BASE = collections.defaultdict(lambda: [0, 0])
for v in P.values():
    if v["src"] != SRC and SRC != "all": continue
    lim = min(COV[v["src"]], v["pull"] if v["pull"] is not None else 10**9)
    seq = []; ok = True
    for s in v["sw"]:
        if s["rel"] > lim: break
        k, t = cls(v, s)
        if k is None: ok = False; break
        seq.append((s, k, t))
    if not ok: continue
    bb = [s["rel"] for s, k, t in seq if k == "bot" and s["eth"] > 0]
    if not bb: continue
    arm = bb[0]
    outs = [(s, t) for s, k, t in seq if k == "out" and s["eth"] > 0]
    for s, t in outs:
        if s["rel"] <= arm: continue
        later = [(x, k) for x, k, tt in seq if x["rel"] >= s["rel"] and x["li"] != s["li"] and (v["pull"] is None or x["rel"] <= v["pull"])]
        bbuys = [x["rel"] for x, k in later if k == "bot" and x["eth"] > 0 and x["rel"] > s["rel"] - 0]
        bsells = [(x["rel"], x["eth"]) for x, k in later if k == "bot" and x["eth"] < 0]
        slot = len([b for b in bb if b <= s["rel"]])
        R.append({"fam": v["fam"], "pid": v["pid"], "b0": v["b0"], "rel": s["rel"], "eth": s["eth"], "wallet": t["from"], "lag": (v["pull"] - s["rel"]) if v["pull"] is not None else None,
                  "slot": slot, "bot_buys_before_pull": [b - s["rel"] for b in bbuys], "bot_sells_before_pull": [(a - s["rel"], round(e, 4)) for a, e in bsells],
                  "cov_end": lim})
    # baseline: random ages after arm, windows clean of outsider buys > 3e-5 within [a-25, a+25]
    oa = [s["rel"] for s, t in outs if s["eth"] >= 3e-5]
    for _ in range(5):
        a = random.randint(arm + 1, 275)
        if v["pull"] is not None and v["pull"] <= a: continue
        if any(a - 25 <= x <= a + 25 for x in oa): continue
        BASE[v["fam"]][0] += 1; BASE[v["fam"]][1] += v["pull"] is not None and v["pull"] <= a + 25
json.dump(R, open(os.path.join(HERE, f"react2_{SRC}.json"), "w"))
WL = {"0xb002e8a0e5d5e4b4d0f0e5c9": 0}
for fam in ("v3.0", "v5.0", "v2.433"):
    print(f"=== {fam} ({SRC})  baseline P(pull within 25 | random armed block, no outsider buy >= 3e-5 within 25): {BASE[fam][1]}/{BASE[fam][0]} = {BASE[fam][1] / max(1, BASE[fam][0]):.3%}")
    for name, f in (("< 3e-5 ETH", lambda x: x["eth"] < 3e-5), (">= 3e-5, not 0xb002e8a0", lambda x: x["eth"] >= 3e-5 and not x["wallet"].startswith("0xb002e8a0")),
                    (">= 3e-5, 0xb002e8a0", lambda x: x["eth"] >= 3e-5 and x["wallet"].startswith("0xb002e8a0"))):
        xs = [x for x in R if x["fam"] == fam and f(x)]
        # first such buy per pool only
        seen = set(); fx = []
        for x in sorted(xs, key=lambda x: (x["pid"], x["rel"])):
            if x["pid"] not in seen: seen.add(x["pid"]); fx.append(x)
        if not fx: continue
        lag = [x["lag"] for x in fx if x["lag"] is not None]
        w25 = [x for x in fx if x["lag"] is not None and x["lag"] <= 25]
        nob = [x for x in w25 if not x["bot_buys_before_pull"]]
        print(f"  {name:26s}: first per pool {len(fx):4d}; pulled <=25 blocks later {len(w25):4d} ({len(w25) / len(fx):.0%}); lag hist " +
              str(sorted(collections.Counter(min(l, 99) for l in lag if l <= 25).items())) +
              f"; of the pulled: bot bought again before the pull in {len(w25) - len(nob)}, bot sold before the pull in {sum(1 for x in w25 if x['bot_sells_before_pull'])}")
        sl = [x for x in fx if x["slot"] == 1]
        if sl:
            print(f"      in the entry slot (after bot buy 1, before bot buy 2): {len(sl)}; pulled <=25: {sum(1 for x in sl if x['lag'] is not None and x['lag'] <= 25)}; "
                  f"2nd bot buy still came before the pull: {sum(1 for x in sl if x['bot_buys_before_pull'])}; examples " +
                  str([(x['b0'], x['rel'], round(x['eth'], 5), x['wallet'][:10], x['lag'], x['bot_buys_before_pull'][:2], x['bot_sells_before_pull'][:2]) for x in sl[:12]]))
