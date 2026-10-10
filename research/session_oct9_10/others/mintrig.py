#!/usr/bin/env python3
"""Variant: a larger minimum trigger (the first buy >= MIN after +6, within 150 blocks); hold 2 (engine) or 30; land 1/2."""
import os, statistics as st
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "variants.py")).read().split("FAMS = {")[0]
g = {"__file__": os.path.join(os.path.dirname(os.path.abspath(__file__)), "variants.py")}; exec(compile(src, "variants_head", "exec"), g)
R = g["R"]; plogs = g["plogs"]; inits = g["inits"]; paper = g["paper"]; W = g["W"]; sgn = g["sgn"]; s128 = g["s128"]; T_SWAP = g["T_SWAP"]; RELAY = g["RELAY"]
def run(pid, hold, minw, land=1, lag=1):
    r = R[pid]; l = inits[pid]; d = l["data"]; b0 = r["b0"]
    ev = sorted(plogs[pid], key=lambda x: (x[0], x[1])); sw = []; mls = []; rem = []
    for bn, li, t0, snd, dd, th in ev:
        if t0 == T_SWAP:
            if snd[-40:] != RELAY: sw.append((bn, li, s128(W(dd, 0)), s128(W(dd, 1)), W(dd, 2), W(dd, 3)))
        else:
            mls.append((bn, sgn(W(dd, 0)), sgn(W(dd, 1)), sgn(W(dd, 2))))
            if sgn(W(dd, 2)) < 0: rem.append(bn)
    big = [x for x in sw if -x[2] >= minw and 6 < x[0] - b0 <= 150]
    if not big: return None
    return paper(sw, mls, W(d, 3), sgn(W(d, 4)), W(d, 0), big[0][0], land, lag, min(rem) if rem else None, hold)
fams = {"PM2276": lambda r: r["sel"] == "0xac9650d8" and r["inlen"] == 2276, "OURS-orig": lambda r: r["ours"] == "orig",
        "PMdirect500": lambda r: r["sel"] == "0x6276cbbe" and r["fee"] == 500 and r["ts"] == 1}
for name, f in fams.items():
    pids = [p for p, r in R.items() if r["logs"] and r["hooks"] == "0x" + "0" * 40 and f(r) and r["fee"] < 10000]
    for minw in (2e14, 1e16, 5e16):
        for hold in (2, 30):
            for land, lag in ((1, 1), (2, 1), (2, 2)):
                if hold == 30 and (land, lag) != (1, 1): continue
                res = [x for x in (run(p, hold, int(minw), land, lag) for p in pids) if x]
                v = [x["ret"] for x in res]
                if v: print(name, "min %.4f" % (minw / 1e18), "hold", hold, "land", land, "lag", lag, "n", len(v), "mean %+.2f%%" % (100 * st.mean(v)), "med %+.2f%%" % (100 * st.median(v)), "pos", sum(1 for a in v if a > 0), "pulled", sum(1 for x in res if x["why"] == "pulled"))

# PM2276 detail at MIN 0.01 ETH
import collections, json, pickle
pids = [p for p, r in R.items() if r["logs"] and r["sel"] == "0xac9650d8" and r["inlen"] == 2276]
rows = [(p, run(p, 2, int(1e16), 1, 1), run(p, 2, int(1e16), 2, 1)) for p in pids]
rows = [(p, a, b) for p, a, b in rows if a]
v = sorted((a["ret"] for p, a, b in rows), reverse=True)
print("PM2276 min0.01 land1 fast: n", len(v), "top5", [round(x, 3) for x in v[:5]], "mean w/o top3 %+.2f%%" % (100 * st.mean(v[3:])), "w/o top5 %+.2f%%" % (100 * st.mean(v[5:])))
B0 = 82878144; bk = collections.defaultdict(list)
for p, a, b in rows: bk[int((R[p]["b0"] - B0) * 0.103 / 3600 // 6) * 6].append(a["ret"])
print("  by 6h:", {k: (len(x), "%+.1f%%" % (100 * st.mean(x)), sum(1 for y in x if y > 0)) for k, x in sorted(bk.items())})
Ls = collections.Counter()
for p in pids:
    ev = plogs[p]; L = {W(d, 3) for bn, li, t0, snd, d, th in ev if t0 == T_SWAP and bn - R[p]["b0"] <= 400}
    Ls[len(L) <= 1] += 1
print("  single-L pools:", dict(Ls))
crowd = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "crowd.json")))
for k, c in crowd.items():
    if "len2276" in k: print("  crowd", c)
pos = [p for p, a, b in sorted(rows, key=lambda x: -x[1]["ret"])][:8]
print("  best pools", [(p, round(R[p]["b0"]), R[p]["trig"]) for p in pos])
