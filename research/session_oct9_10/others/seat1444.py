#!/usr/bin/env python3
"""PM1444 family (PositionManager multicall, 1,444-byte calldata): a fixed-time entry (our buy at the head of launch + K, no trigger needed)
and the sell on the first buy that prices us >= +1% after gas within H blocks (else at the deadline), landing one block later; pull = -100%."""
import os, statistics as st
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "variants.py")).read().split("FAMS = {")[0]
g = {"__file__": os.path.join(os.path.dirname(os.path.abspath(__file__)), "variants.py")}; exec(compile(src, "variants_head", "exec"), g)
R = g["R"]; plogs = g["plogs"]; inits = g["inits"]; paper = g["paper"]; W = g["W"]; sgn = g["sgn"]; s128 = g["s128"]; T_SWAP = g["T_SWAP"]; RELAY = g["RELAY"]
def run(pid, K, H):
    r = R[pid]; d = inits[pid]["data"]; b0 = r["b0"]; sw = []; mls = []; rem = []
    for bn, li, t0, snd, dd, th in sorted(plogs[pid], key=lambda x: (x[0], x[1])):
        if t0 == T_SWAP:
            if snd[-40:] != RELAY: sw.append((bn, li, s128(W(dd, 0)), s128(W(dd, 1)), W(dd, 2), W(dd, 3)))
        else:
            mls.append((bn, sgn(W(dd, 0)), sgn(W(dd, 1)), sgn(W(dd, 2))))
            if sgn(W(dd, 2)) < 0: rem.append(bn)
    return paper(sw, mls, W(d, 3), sgn(W(d, 4)), W(d, 0), b0 + K - 1, 1, 1, min(rem) if rem else None, H)
for name, f in (("v3.0 fee1%", lambda r: r["fee"] == 10000 and round(r["value"] or 0, 3) == 3.0), ("v5.0 fee1%", lambda r: r["fee"] == 10000 and round(r["value"] or 0, 3) == 5.0),
                ("v2.433 fee0.25%", lambda r: r["fee"] == 2500 and r["ts"] == 50)):
    pids = [p for p, r in R.items() if r["logs"] and r["sel"] == "0xac9650d8" and r["inlen"] == 1444 and r["ts"] in (50, 200) and f(r)]
    for K in (12, 16, 20, 25):
        for H in (15, 25, 40):
            res = [x for x in (run(p, K, H) for p in pids) if x]; v = [x["ret"] for x in res]
            print(name, "buy at +%d hold %d" % (K, H), "n", len(v), "mean %+.2f%%" % (100 * st.mean(v)), "med %+.2f%%" % (100 * st.median(v)), "pos", sum(1 for a in v if a > 0), "pulled", sum(1 for x in res if x["why"] == "pulled"))
