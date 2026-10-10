import sys, os, pickle, json, warnings, numpy as np
sys.path.insert(0, "."); from fams import *
warnings.filterwarnings("ignore")
P = pickle.load(open("pools.pkl", "rb")); M = pickle.load(open("meta.pkl", "rb")); pids = M["pids"]
G = np.load("grid.npy", mmap_mode="r"); F = families(P, pids)
H_ = np.array([hours(P[q]["b0"]) for q in pids])
names = sys.argv[1:]
for fk in names:
    idx = np.array(sorted(F[fk])); A = np.asarray(G[idx])[:, :, 0]   # stake 0.0012
    print("==", fk, len(idx))
    for t in range(4):
        row = []
        for e in [0, 1, 2, 4, 6, 8, 10, 14, 20, 30, 38]:
            v = A[:, e, t, 58]; row.append(f"K{M['KS'][e]}:{100*np.nanmean(v):+.1f}({(~np.isnan(v)).sum()})")
        print(f"  TP{M['TPS'][t]*100:g} H60 ", " ".join(row))
    row = []
    for h in (0, 3, 8, 18, 28, 38, 48, 58):
        v = A[:, 0, 3, h]; row.append(f"H{M['HS'][h]}:{100*np.nanmean(v):+.1f}")
    print("  K2 TP5 by H", " ".join(row))
    # trigger entries
    for ti in range(3):
        row = []
        for d in (0, 2, 5, 10):
            e = 39 + ti * 11 + d; v = A[:, e, 3, 58]; row.append(f"d{d}:{100*np.nanmean(v):+.1f}({(~np.isnan(v)).sum()})")
        print(f"  firstbuy>={M['THRS'][ti]/1e18:g} TP5 H60", " ".join(row))
    trig = [M["pinfo"][pids[i]]["trig"][2] for i in idx]
    tt = [x for x in trig if x is not None]
    print("  first >=0.01 buy offset p10/50/90", np.percentile(tt, [10, 50, 90]) if tt else None, "none", sum(1 for x in trig if x is None))
