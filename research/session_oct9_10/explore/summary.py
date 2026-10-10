#!/usr/bin/env python3
"""Robustness of the chosen rules: neighbourhood on the test half, slices, sub-families, canonical rules per family, negative results. -> summary.json"""
import sys, os, pickle, json, warnings, collections
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fams import *
warnings.filterwarnings("ignore")
P = pickle.load(open("pools.pkl", "rb")); M = pickle.load(open("meta.pkl", "rb")); pids = M["pids"]
G = np.load("grid.npy", mmap_mode="r"); R = json.load(open("rules.json")); F = families(P, pids)
KS, TPS, HS, DS, THRS = M["KS"], M["TPS"], M["HS"], M["DS"], M["THRS"]
Hh = np.array([hours(P[q]["b0"]) for q in pids]); SL = np.minimum((Hh // 6).astype(int), 6)
def eidx(kind, a, d=0):
    return KS.index(a) if kind == "K" else len(KS) + list(THRS).index(a) * len(DS) + d
def m(v):
    v = v[~np.isnan(v)]; return (round(100 * float(v.mean()), 2), int(len(v)), round(100 * float(np.median(v)), 2)) if len(v) else None
out = {}
CAND = ["L:0x58daec31|0xac9650d8|len1444|fee2500|ts50|v2.433", "L:0x58daec31|0xac9650d8|len1444|fee10000|ts200|v5.0", "L:0x8366a39c|0x6276cbbe|len196|fee500|ts1|v0",
        "L:OURS-orig", "L:0x58daec31|0xac9650d8|len2276|fee100|ts1|v0", "L:0x58daec31|0xac9650d8|len1444|fee10000|ts200|v3.0"]
for fk in R["families"]:
    idx = np.array(sorted(F[fk])); A = np.asarray(G[idx]); te = Hh[idx] >= MID_H; tr = ~te
    o = {}
    # canonical rules on the test half, stake 0.0012
    can = {"ours-like: firstbuy>=0.0002+0 TP1 H2": (eidx("T", 0.0002e18, 0), 0, 0), "firstbuy>=0.01+0 TP5 H60": (eidx("T", 0.01e18, 0), 3, 58),
           "launch+2 TP5 H20": (eidx("K", 2), 3, 18), "launch+6 TP5 H20": (eidx("K", 6), 3, 18), "launch+10 TP5 H20": (eidx("K", 10), 3, 18), "launch+2 TP1 H2": (eidx("K", 2), 0, 0)}
    o["canonical_test_0.0012"] = {k: m(A[te, e, 0, t, h]) for k, (e, t, h) in can.items()}
    # distribution of all rules on test (>= 30 trades)
    for s in (0, 1):
        n = (~np.isnan(A[te][:, :, s])).sum(0); mu = np.nanmean(A[te][:, :, s], 0)
        ok = n >= 30
        if ok.any():
            v = mu[ok]; o[f"test_rule_dist_stake{s}"] = {"n_rules": int(ok.sum()), "frac_pos": round(float((v > 0).mean()), 3), "p10": round(100 * float(np.percentile(v, 10)), 2),
                                                        "p50": round(100 * float(np.percentile(v, 50)), 2), "p90": round(100 * float(np.percentile(v, 90)), 2), "min": round(100 * float(v.min()), 2)}
            e, t, h = np.unravel_index(np.argmin(np.where(ok, mu, np.inf)), mu.shape)
            o[f"worst_rule_test_stake{s}"] = (f"e{e} TP{TPS[t]} H{HS[h]}", round(100 * float(mu[e, t, h]), 2), int(n[e, t, h]))
    if fk in CAND:
        b = R["families"][fk]["by_stake"]
        for sk, r in b.items():
            if "mean" not in r: continue
            e, s, t, h = r["mean"]["idx"]
            nb_ = {}
            nb_["by_entry"] = {}
            for ee in list(range(0, 10)) + [12, 18, 24, 30, 38] + list(range(39, NE := len(KS) + len(THRS) * len(DS), 3)):
                nb_["by_entry"][ee] = m(A[te, ee, s, t, h])
            nb_["by_TP"] = {TPS[tt]: m(A[te, e, s, tt, h]) for tt in range(4)}
            nb_["by_H"] = {HS[hh]: m(A[te, e, s, t, hh]) for hh in (0, 3, 8, 13, 18, 28, 38, 48, 58) if 0 <= hh < len(HS)}
            nb_["slices_all"] = {k: m(A[SL[idx] == k, e, s, t, h]) for k in range(7)}
            subs = collections.defaultdict(list)
            for j, i in enumerate(idx): subs[nb(P[pids[i]]["nonce"])].append(j)
            nb_["test_by_nonce_band"] = {k: m(A[np.array(v)[te[np.array(v)]], e, s, t, h]) for k, v in subs.items() if te[np.array(v)].any()}
            nb_["train_by_nonce_band"] = {k: m(A[np.array(v)[tr[np.array(v)]], e, s, t, h]) for k, v in subs.items() if tr[np.array(v)].any()}
            o[f"chosen_{sk}"] = {"rule": r["mean"]["rule"], **nb_}
    out[fk] = o
json.dump(out, open("summary.json", "w"), indent=1, default=str)
for fk in CAND:
    o = out[fk]; print("=====", fk)
    print("  canonical (test, 0.0012):", o["canonical_test_0.0012"])
    print("  all-rules test dist s0:", o.get("test_rule_dist_stake0"), "worst", o.get("worst_rule_test_stake0"))
    for k in o:
        if k.startswith("chosen"):
            c = o[k]; print("  ", k, c["rule"]); print("     by_TP", c["by_TP"]); print("     by_H", c["by_H"]); print("     slices", c["slices_all"])
            print("     by_entry", {(f"K{KS[e]}" if e < len(KS) else f"T{(e-len(KS))//len(DS)}+{(e-len(KS))%len(DS)}"): v for e, v in c["by_entry"].items()})
            print("     test by nonce band", c["test_by_nonce_band"], "train", c["train_by_nonce_band"])
print("\nother families: canonical + rule distribution")
for fk, o in out.items():
    if fk in CAND: continue
    print(fk[:80], o.get("test_rule_dist_stake0"), o["canonical_test_0.0012"].get("ours-like: firstbuy>=0.0002+0 TP1 H2"), o["canonical_test_0.0012"].get("launch+2 TP5 H20"))
