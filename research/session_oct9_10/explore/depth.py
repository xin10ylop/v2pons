import pickle, collections, numpy as np, sys
sys.path.insert(0, ".")
from fams import *
P = pickle.load(open("pools.pkl", "rb")); M = pickle.load(open("meta.pkl", "rb")); pids = M["pids"]
F = families(P, pids)
for k, v in sorted(F.items(), key=lambda kv: -len(kv[1])):
    if len(v) < 20: continue
    xv = [M["info"][pids[i]][0][3] for i in v if M["info"][pids[i]][0] and M["info"][pids[i]][0][3] is not None]
    xt = [M["info"][pids[i]][39][3] for i in v if M["info"][pids[i]][39] and M["info"][pids[i]][39][3] is not None]
    q = lambda a: [round(float(np.percentile(a, x)), 3) for x in (5, 50, 95)] if a else None
    h = [hours(P[pids[i]]["b0"]) for i in v]
    print(f"{k[:95]:95s} n {len(v):4d} train {sum(1 for x in h if x < MID_H):4d} xv@K2 {q(xv)} xv@trig {q(xt)}")
