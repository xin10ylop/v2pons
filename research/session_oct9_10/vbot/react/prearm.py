#!/usr/bin/env python3
"""LEAD ONLY (cheap pricer, census pools): buy BEFORE the bot's first buy (land at launch + K) and sell into that first buy (the sell lands
L blocks after it). Same pricing as others/variants.py (paper()). Reaction model from the data: a pre-arm outsider buy >= 3e-5 drew a pull
3-10 blocks after the bot's first buy (9/9 v3.0 cases, one probe episode), so a sell landing 1-2 blocks after it escapes; pull = -100% if
the actual pull lands first."""
import os, sys, statistics as st
O = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/others"
src = open(os.path.join(O, "variants.py")).read().split("FAMS = {")[0]
g = {"__file__": os.path.join(O, "variants.py")}; exec(compile(src, "variants_head", "exec"), g)
R, plogs, inits, paper, W, sgn, s128, T_SWAP, RELAY = (g[k] for k in ("R", "plogs", "inits", "paper", "W", "sgn", "s128", "T_SWAP", "RELAY"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load, classifier, COV
P, TX, M = load(); BOTW, cls = classifier(TX)
def run(pid, K, L):
    r = R[pid]; d = inits[pid]["data"]; b0 = r["b0"]; v = P[pid]
    bb = []
    for s in v["sw"]:
        if s["rel"] > 60: break
        k, t = cls(v, s)
        if k == "bot" and s["eth"] > 0: bb.append(s); break
    if not bb or bb[0]["rel"] <= K: return None
    sw = []; mls = []; rem = []
    for bn, li, t0, snd, dd, th in sorted(plogs[pid], key=lambda x: (x[0], x[1])):
        if t0 == T_SWAP:
            if snd[-40:] != RELAY: sw.append((bn, li, s128(W(dd, 0)), s128(W(dd, 1)), W(dd, 2), W(dd, 3)))
        else:
            mls.append((bn, sgn(W(dd, 0)), sgn(W(dd, 1)), sgn(W(dd, 2))))
            if sgn(W(dd, 2)) < 0: rem.append(bn)
    hold = bb[0]["rel"] - K
    return paper(sw, mls, W(d, 3), sgn(W(d, 4)), W(d, 0), b0 + K - 1, 1, L, min(rem) if rem else None, hold)
for fam in ("v3.0", "v5.0", "v2.433"):
    pids = [p for p, v in P.items() if v["fam"] == fam and v["src"] == "census" and p in R]
    for K in (4, 6):
        for L in (1, 2):
            res = [x for x in (run(p, K, L) for p in pids) if x]; v = [x["ret"] for x in res]
            print(f"{fam:6s} buy lands +{K}, sell lands bot-buy1 + {L}: n {len(v)} mean {100*st.mean(v):+.2f}% median {100*st.median(v):+.2f}% pos {sum(1 for a in v if a > 0)} "
                  f"tp {sum(1 for x in res if x['why']=='tp')} pulled {sum(1 for x in res if x['why']=='pulled')}")
