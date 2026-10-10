#!/usr/bin/env python3
"""All PM1444 pools (logs only): an outsider buy = a swap paying 0.0002-0.02 ETH (every bot buy in the 181-pool tx sample was >= 0.0247 ETH,
every non-bot buy <= 0.0041). Pull timing after the first outsider buy vs the base rate; then the hold-30 / fixed-entry paper with the
pull our own buy would cause, drawn from the observed reaction delays."""
import sys, os, json, pickle, statistics as st, collections, random
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
exec(open(os.path.join(HERE, "v2_price.py")).read().split("B0 = 82878144")[0])
LO, HI = 2 * 10**14, 2 * 10**16
delays_all = {}
for name in ("v3", "v5", "v2433"):
    pids = [p for p, r in R.items() if r["logs"] and r["hooks"] == Z and FAMS[name](r)]
    d = []; base_hits = 0; base_n = 0; ex = []
    for p in pids:
        P = prep(p); b0 = P["b0"]; pull = P["pull"]
        outs = [s for s in P["sw"] if LO <= -s[2] < HI and (pull is None or s[0] < pull)]
        if outs:
            o = outs[0][0]
            d.append((pull - o) if pull is not None else None); ex.append((p[:10], o - b0, (pull - b0) if pull else None))
    v = [x for x in d if x is not None]
    print(f"{name}: pools {len(pids)}; with an outsider buy (0.0002-0.02 ETH) before the pull: {len(d)}; pulled after it: {len(v)}; "
          f"within 20 blocks: {sum(1 for x in v if x <= 20)}; within 30: {sum(1 for x in v if x <= 30)}; delay p10/50/90 {[sorted(v)[int(q*(len(v)-1))] for q in (.1,.5,.9)] if v else None}; never pulled in window: {sum(1 for x in d if x is None)}")
    print("   delay histogram", sorted(collections.Counter(min(x, 99) for x in v).items())[:30])
    # base rate: pools with no outsider: probability of a pull inside a 20-block window starting at +10..+40
    no = [prep(p) for p in pids if not any(LO <= -s[2] < HI for s in prep(p)["sw"])]
    for a in (10, 25):
        print(f"   base rate (no outsider buy at all): pulled in [+{a}, +{a+20}]: {sum(1 for P in no if P['pull'] is not None and a <= P['pull'] - P['b0'] <= a + 20)} of {len(no)}")
    delays_all[name] = v
json.dump(delays_all, open(os.path.join(HERE, "v5_delays.json"), "w"))
# reaction-adjusted paper: our buy at B is an outsider buy; the pull comes at B + delay (delay drawn from the family's observed delays,
# 200 draws per pool), or the logged pull if earlier.
random.seed(1)
for name in ("v3", "v5", "v2433"):
    dl = [x for x in delays_all[name] if x <= 60]
    pids = [p for p, r in R.items() if r["logs"] and r["hooks"] == Z and FAMS[name](r)]
    PP = {p: prep(p) for p in pids}
    for K, H in ((10, 30), (16, 40), (20, 40), (25, 25), (25, 40), (30, 15)):
        rets = []
        for p in pids:
            P = PP[p]; B = P["b0"] + K
            for _ in range(50):
                dd = random.choice(dl); pull = B + dd
                if P["pull"] is not None: pull = min(pull, P["pull"])
                x = vprice.follow(P["sw"], P["sp0"], P["L0"], P["fee"], B, H, 1, pull)
                if x: rets.append(x["ret"])
        print(f"   {name} reaction-adjusted: buy at +{K} hold {H}: mean {100*st.mean(rets):+.2f}% median {100*st.median(rets):+.2f}% P(pulled) {sum(1 for a in rets if a < -0.99)/len(rets):.2f}")
