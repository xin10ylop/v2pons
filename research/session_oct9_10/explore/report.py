#!/usr/bin/env python3
"""Full survivor test on the rules chosen in rules.json (both selection criteria), with per-trade detail and the exact replay.
Writes report.json."""
import sys, os, pickle, json, collections, warnings, statistics as stt
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fams import *
import sim, detail
warnings.filterwarnings("ignore")
P = pickle.load(open("pools.pkl", "rb")); M = pickle.load(open("meta.pkl", "rb")); pids = M["pids"]
R = json.load(open("rules.json")); F = families(P, pids)
out = {}
for fk, fam in R["families"].items():
    for sk, r in fam["by_stake"].items():
        if "mean" not in r: continue
        for crit in ("mean", "tstat"):
            c = r[crit]; e, s, t, h = c["idx"]
            rows = []
            for i in F[fk]:
                p = P[pids[i]]; d = detail.detail(p, e, s, t, h)
                if d is None: continue
                hh = hours(p["b0"]); d.update(pid=p["pid"], b0=p["b0"], h=hh, half="test" if hh >= MID_H else "train", slice=min(int(hh // 6), 6)); rows.append(d)
            te = [x for x in rows if x["half"] == "test"]; trn = [x for x in rows if x["half"] == "train"]
            def S(v):
                if not v: return None
                a = np.array([x["ret"] for x in v]); ex = np.array([x["exact"] for x in v])
                srt = np.sort(a)[::-1]
                return {"n": len(v), "mean": float(a.mean()), "median": float(np.median(a)), "pos": float((a > 0).mean()), "mean_exact": float(ex.mean()),
                        "median_exact": float(np.median(ex)), "mean_ex_top1": float(srt[1:].mean()) if len(a) > 1 else None, "mean_ex_top3": float(srt[3:].mean()) if len(a) > 3 else None,
                        "top1_share": float(srt[0] / a.sum()) if a.sum() > 0 else None, "why": dict(collections.Counter(x["why"] for x in v)),
                        "pulled": sum(1 for x in v if x["why"] == "pulled"), "max_abs_exact_diff": float(np.max(np.abs(a - ex)))}
            sl = {k: S([x for x in rows if x["slice"] == k]) for k in range(7)}
            slp = [k for k in range(7) if sl[k] and sl[k]["n"] >= 5]
            tsl = [k for k in slp if k >= 3]
            res = {"rule": c["rule"], "train": S(trn), "test": S(te), "slices": {k: (round(v["mean"], 4), v["n"]) if v else None for k, v in sl.items()},
                   "slices_pos": f"{sum(1 for k in slp if sl[k]['mean'] > 0)}/{len(slp)}", "test_slices_pos": f"{sum(1 for k in tsl if sl[k]['mean'] > 0)}/{len(tsl)}",
                   "worst_slice": min((sl[k]["mean"] for k in slp), default=None),
                   "B_offsets": dict(collections.Counter(x["B"] for x in rows).most_common(5)), "T_offsets_p50": float(np.median([x["T"] for x in rows if x["T"] is not None])) if any(x["T"] is not None for x in rows) else None,
                   "send_p50": float(np.median([x["send"] for x in rows])),
                   "examples": [(x["pid"], round(x["ret"], 4), x["why"]) for x in sorted(te, key=lambda x: -x["b0"])[:3]]}
            tst = res["test"]
            res["survivor"] = bool(tst and tst["n"] >= 30 and tst["mean"] > 0 and tst["median"] > 0 and tst["mean_ex_top3"] > 0 and (tst["top1_share"] or 0) < 0.5
                                   and sum(1 for k in slp if sl[k]["mean"] > 0) > len(slp) / 2 and sum(1 for k in tsl if sl[k]["mean"] > 0) > len(tsl) / 2 and tst["mean_exact"] > 0)
            out[f"{fk} || {sk} || {crit}"] = res
            if tst:
                print(f"{'SURV' if res['survivor'] else '    '} {fk[:70]:70s} {sk:6s} {crit:5s} {c['rule']:52s} test n {tst['n']:4d} mean {100*tst['mean']:+6.2f}% exact {100*tst['mean_exact']:+6.2f}% "
                      f"med {100*tst['median']:+6.2f}% pos {tst['pos']:.2f} exTop3 {100*tst['mean_ex_top3']:+6.2f}% top1 {tst['top1_share'] if tst['top1_share'] is None else round(tst['top1_share'], 3)} "
                      f"pulled {tst['pulled']} sl {res['slices_pos']} tsl {res['test_slices_pos']} worst {100*res['worst_slice']:+.2f}% why {tst['why']}")
json.dump(out, open("report.json", "w"), indent=1)
