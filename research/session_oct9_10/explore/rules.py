#!/usr/bin/env python3
"""Per family x stake: pick the best rule on the first half (by launch time), report it on the second half and per 6-hour slice.
rule = (entry e: launch+K or first-buy(THR)+d, TP, H). Writes rules.json."""
import sys, os, pickle, json, collections, warnings
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fams import *
warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
P = pickle.load(open(os.path.join(HERE, "pools.pkl"), "rb")); M = pickle.load(open(os.path.join(HERE, "meta.pkl"), "rb")); pids = M["pids"]
G = np.load(os.path.join(HERE, "grid.npy"), mmap_mode="r")
TPS, HS, KS, THRS, DS, STAKES = M["TPS"], M["HS"], M["KS"], M["THRS"], M["DS"], M["STAKES"]
NE = len(KS) + len(THRS) * len(DS)
def ename(e):
    if e < len(KS): return f"launch+{KS[e]}"
    t, d = divmod(e - len(KS), len(DS)); return f"firstbuy>={THRS[t]/1e18:g}+{d}"
def rname(e, s, t, h): return f"{ename(e)} | stake {STAKES[s]/1e18:g} | TP {TPS[t]*100:g}% | H {HS[h]}"
H_ = np.array([hours(P[q]["b0"]) for q in pids])
SL = np.minimum((H_ // 6).astype(int), 6)
MIN_TRAIN = int(sys.argv[1]) if len(sys.argv) > 1 else 20
F = families(P, pids)
F = {k: v for k, v in F.items() if len(v) >= 30}
out = {"n_families": len(F), "rules_per_family": NE * len(STAKES) * len(TPS) * len(HS), "families": {}}
out["rules_tested_total"] = out["n_families"] * out["rules_per_family"]

def stats(v):
    v = v[~np.isnan(v)]
    if len(v) == 0: return None
    return {"n": int(len(v)), "mean": float(v.mean()), "median": float(np.median(v)), "pos": float((v > 0).mean()), "sd": float(v.std())}

for fk, idx in sorted(F.items(), key=lambda kv: -len(kv[1])):
    idx = np.array(sorted(idx)); sub = np.asarray(G[idx])          # (n, NE, 2, 4, 59)
    tr = H_[idx] < MID_H; te = ~tr
    fam = {"n_pools": int(len(idx)), "n_train_pools": int(tr.sum()), "n_test_pools": int(te.sum()),
           "launches_per_day": round(len(idx) / (WINDOW_H / 24), 1), "by_stake": {}}
    for s in range(len(STAKES)):
        A = sub[:, :, s]                                             # (n, NE, 4, 59)
        ntr = (~np.isnan(A[tr])).sum(0); mtr = np.nanmean(A[tr], 0) if tr.any() else np.full(A.shape[1:], np.nan)
        sdtr = np.nanstd(A[tr], 0) if tr.any() else np.full(A.shape[1:], np.nan)
        ok = ntr >= MIN_TRAIN
        if not ok.any(): fam["by_stake"][str(STAKES[s] / 1e18)] = {"note": f"no rule with >= {MIN_TRAIN} train trades"}; continue
        res = {}
        for crit in ("mean", "tstat"):
            score = np.where(ok, mtr if crit == "mean" else mtr / (sdtr / np.sqrt(np.maximum(ntr, 1)) + 1e-9), -np.inf)
            e, t, h = np.unravel_index(np.argmax(score), score.shape)
            col = A[:, e, t, h]
            trs = stats(col[tr]); tes = stats(col[te])
            sl = {}
            for k in range(7):
                m = SL[idx] == k; st_ = stats(col[m]); sl[k] = st_
            tv = col[te]; tvv = tv[~np.isnan(tv)]
            ex = {}
            if len(tvv) >= 3:
                srt = np.sort(tvv)[::-1]
                ex = {"mean_ex_top1": float(srt[1:].mean()), "mean_ex_top3": float(srt[3:].mean()),
                      "top1_share_of_sum": float(srt[0] / tvv.sum()) if tvv.sum() > 0 else None, "max": float(srt[0]), "min": float(srt[-1]),
                      "pulled": int((tvv <= -0.99).sum())}
            test_slices = [k for k in range(7) if sl[k] and sl[k]["n"] >= 5 and k >= 3]
            all_slices = [k for k in range(7) if sl[k] and sl[k]["n"] >= 5]
            res[crit] = {"rule": rname(e, s, t, h), "idx": [int(e), int(s), int(t), int(h)], "train": trs, "test": tes, "slices": sl, "test_extra": ex,
                         "slices_pos_all": f"{sum(1 for k in all_slices if sl[k]['mean'] > 0)}/{len(all_slices)}",
                         "slices_pos_test": f"{sum(1 for k in test_slices if sl[k]['mean'] > 0)}/{len(test_slices)}",
                         "worst_slice": min((sl[k]["mean"] for k in all_slices), default=None)}
        # the rule's test-optimum (in-sample on test: NOT a valid result, only to see whether anything there was ever positive)
        nte = (~np.isnan(A[te])).sum(0); mte = np.where(nte >= 30, np.nanmean(A[te], 0), -np.inf)
        e, t, h = np.unravel_index(np.argmax(mte), mte.shape)
        res["test_oracle"] = {"rule": rname(e, s, t, h), "mean": float(mte[e, t, h]), "n": int(nte[e, t, h]), "train_mean": float(mtr[e, t, h]), "train_n": int(ntr[e, t, h])}
        # fraction of rules positive on train and on test (with >= 30 trades)
        res["frac_rules_pos_train"] = float(((mtr > 0) & ok).sum() / max(1, ok.sum()))
        res["frac_rules_pos_test"] = float(((mte > 0) & (nte >= 30)).sum() / max(1, (nte >= 30).sum()))
        res["n_rules_pos_both"] = int(((mtr > 0) & ok & (mte > 0) & (nte >= 30)).sum())
        fam["by_stake"][str(STAKES[s] / 1e18)] = res
    out["families"][fk] = fam
    b = fam["by_stake"]
    for sk, r in b.items():
        if "mean" not in r: print(f"{fk[:80]:80s} {sk:6s} {r['note']}"); continue
        m = r["mean"]
        print(f"{fk[:80]:80s} {sk:6s} n{fam['n_pools']:4d} | {m['rule']:55s} train {100*m['train']['mean']:+6.2f}% ({m['train']['n']}) "
              f"test {100*m['test']['mean'] if m['test'] else float('nan'):+6.2f}% ({m['test']['n'] if m['test'] else 0}) med {100*m['test']['median'] if m['test'] else float('nan'):+6.2f}% "
              f"sl {m['slices_pos_all']} | oracle {100*r['test_oracle']['mean']:+.2f}% posboth {r['n_rules_pos_both']}")
json.dump(out, open(os.path.join(HERE, "rules.json"), "w"), indent=1)
print("families", out["n_families"], "rules/family", out["rules_per_family"], "total", out["rules_tested_total"])
