"""Forward test: the rules chosen on the first half (rules.json, 'mean' and 'tstat'), frozen, on launches after the census window. -> fwd.json"""
import sys, os, pickle, json, collections
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sim, detail
FP = pickle.load(open("fwd_pools.pkl", "rb")); R = json.load(open("rules.json"))
out = {}
for fk in sorted({p["fam"] for p in FP.values()}):
    ps = sorted([p for p in FP.values() if p["fam"] == fk], key=lambda p: p["b0"])
    for sk, r in R["families"][fk]["by_stake"].items():
        if "mean" not in r: continue
        for crit in ("mean", "tstat"):
            e, s, t, h = r[crit]["idx"]
            rows = [(p["pid"], d) for p in ps for d in [detail.detail(p, e, s, t, h)] if d]
            if not rows: continue
            a = np.array([d["ret"] for _, d in rows]); ex = np.array([d["exact"] for _, d in rows]); srt = np.sort(a)[::-1]
            res = {"rule": r[crit]["rule"], "n_launches": len(ps), "n": len(a), "mean": float(a.mean()), "median": float(np.median(a)), "pos": float((a > 0).mean()),
                   "mean_exact": float(ex.mean()), "mean_ex_top3": float(srt[3:].mean()) if len(a) > 3 else None, "why": dict(collections.Counter(d["why"] for _, d in rows)),
                   "examples": [(pid, round(d["ret"], 4), d["why"]) for pid, d in rows[-3:]]}
            out[f"{fk} || {sk} || {crit}"] = res
            print(f"{fk[:62]:62s} {sk:6s} {crit:5s} {res['rule']:50s} fwd n {res['n']:3d}/{len(ps):3d} mean {100*res['mean']:+6.2f}% exact {100*res['mean_exact']:+6.2f}% "
                  f"med {100*res['median']:+6.2f}% pos {res['pos']:.2f} exTop3 {100*(res['mean_ex_top3'] or 0):+6.2f}% {res['why']}")
json.dump(out, open("fwd.json", "w"), indent=1)
