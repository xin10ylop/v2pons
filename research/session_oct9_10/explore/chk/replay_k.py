"""replay.py's exact feed replay at other fire blocks (K = 3..6, TP 5% and 1%), and the cheap pricer (detail.detail) on the same pools."""
import sys, os, pickle, statistics as st, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
import replay, sim, detail
D = pickle.load(open(os.path.join(HERE, "replay_data.pkl"), "rb"))
pools = sorted([replay.prep(R) for R in D["pools"].values()], key=lambda p: p["b0"])
for tp in (0.05, 0.01):
    replay.TP = tp
    for K in (2, 3, 4, 5, 6):
        for land in (1, 2):
            for stake in (0.0012, 0.012):
                rs = [replay.trade(p, p["b0"] + K, land, 1, stake) for p in pools]
                v = [r["ret"] for r in rs if r["ret"] is not None]
                expo = [r["S"] - r["B"] for r in rs if "S" in r]
                print(f"TP {tp:.2f} K{K} land+{land} {stake:6g}: mean {100*st.mean(v):+6.2f}% median {100*st.median(v):+6.2f}% pos {sum(1 for a in v if a > 0)}/{len(v)} "
                      f"exits {dict(collections.Counter(r['exit'] for r in rs))} exposure S-B {sorted(collections.Counter(expo).items())}")
replay.TP = 0.05
# cheap pricer vs exact replay, same pools, K2 TP5 H19
P = pickle.load(open(os.path.join(os.path.dirname(HERE), "pools.pkl"), "rb")); FP = pickle.load(open(os.path.join(os.path.dirname(HERE), "fwd_pools.pkl"), "rb"))
diffs = []
for p in pools:
    q = P.get(p["pid"]) or FP.get(p["pid"])
    if not q: continue
    for s, stake in enumerate((0.0012, 0.012)):
        d = detail.detail(q, sim.KS.index(2), s, 3, sim.HS.index(19)); r = replay.trade(p, p["b0"] + 2, 1, 1, stake)
        diffs.append((p["pid"][:10], stake, round(d["ret"], 4), round(r["ret"], 4), round(100 * (r["ret"] - d["ret"]), 3)))
print("cheap vs exact-feed (pp):", max(abs(x[4]) for x in diffs), diffs[:6])
