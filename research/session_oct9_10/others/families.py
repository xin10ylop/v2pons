#!/usr/bin/env python3
"""Families from census.jsonl: launch contract (address, or the code-size class for per-launch contracts) + selector + calldata length +
fee tier + tick spacing + launch value; per family the gates, the crowd, the pull and the paper FOLLOW. Writes families.json."""
import json, os, statistics as st, collections, math
HERE = os.path.dirname(os.path.abspath(__file__))
R = [json.loads(l) for l in open(os.path.join(HERE, "census.jsonl"))]
PM_POS = "0x58daec3116aae6d93017baaea7749052e8a04fa7"

def tier(f): return "sub1%" if f < 10000 else ("1%" if f == 10000 else ">1%")
def fam(r):
    if r["ours"]: return f"OURS-{r['ours']}"
    to = r["to"] or "none"
    many = cnt_to[to] >= 3
    c = to if many else f"percontract:{(r['codesize'] or 0) // 100 * 100}"
    return f"{c}|{r['sel']}|len{r['inlen']}|{tier(r['fee'])}|ts{r['ts']}|v{round(r['value'] or 0, 3)}"
cnt_to = collections.Counter(r["to"] or "none" for r in R)
G = collections.defaultdict(list)
for r in R: G[fam(r)].append(r)

def pct(v, qs=(.1, .5, .9)):
    v = sorted(v); return [v[int(q * (len(v) - 1))] for q in qs] if v else None
out = []
for k, v in G.items():
    lv = [r for r in v if r["logs"]]
    tr = [r for r in lv if r.get("tradable")]
    trig = [r for r in lv if r.get("trig") is not None and 6 < r["trig"] <= 150]
    def ps(key, rows, sub="paper"):
        p = [r[sub][key] for r in rows if r.get(sub) and r[sub].get(key)]
        if not p: return None
        x = [a["ret"] for a in p]
        return {"n": len(p), "mean": round(st.mean(x), 4), "median": round(st.median(x), 4), "pos": sum(1 for a in x if a > 0), "pulled": sum(1 for a in p if a["why"] == "pulled"),
                "tp": sum(1 for a in p if a["why"] == "tp"), "worst": round(min(x), 4), "best": round(max(x), 4)}
    f = {"family": k, "n": len(v), "n_logs": len(lv), "deployers": len({r["from"] for r in v}), "nonce0": sum(1 for r in v if r["nonce"] == 0),
         "nonce_med": st.median(r["nonce"] for r in v if r["nonce"] is not None), "fees": collections.Counter(r["fee"] for r in v).most_common(4),
         "hooks_nonzero": sum(1 for r in v if r["hooks"] != "0x" + "0" * 40), "liq_log10": collections.Counter(int(math.log10(r["liq"])) if r.get("liq") else 0 for r in lv).most_common(3),
         "gates": collections.Counter(x for r in lv for x in r["gates"]).most_common(), "n_tradable": len(tr), "n_trig_7_150": len(trig),
         "trig_p10_50_90": pct([r["trig"] for r in lv if r.get("trig") is not None]), "first_any_buy_med": st.median([r["first_any_buy"] for r in lv if r.get("first_any_buy") is not None] or [-1]),
         "n_real300_p10_50_90": pct([r["n_real300"] for r in lv]), "gap_med300_p10_50_90": pct([r["gap_med300"] for r in lv if r.get("gap_med300") is not None]),
         "pull_p10_50_90": pct([r["pull"] for r in lv if r.get("pull") is not None]), "no_pull_3000": sum(1 for r in lv if r.get("pull") is None),
         "pull_after_trig_p10_50": pct([r["pull_after_trig"] for r in lv if r.get("pull_after_trig") is not None], (.1, .5)),
         "eth_in_before_pull_med": round(st.median([r["eth_in_before_pull"] for r in lv] or [0]), 4),
         "behind10_med": st.median([r["behind10"] for r in lv if r.get("behind10") is not None] or [-1]),
         "paper_tradable": {kk: ps(kk, tr) for kk in ("land1_fast", "land2_fast", "land2_slow", "hold30")},
         "paper_fee_gate_only": ps("land1_fast", [r for r in lv if r["gates"] == ["fee"]]),
         "paper_liq_gate_only": ps("land1_fast", [r for r in lv if r["gates"] == ["liq"]]),
         "paper_alt_after_arm": {kk: ps(kk, [r for r in lv if r.get("paper_alt")], "paper_alt") for kk in ("land1_fast", "hold30")},
         "first": min(r["b0"] for r in v), "last": max(r["b0"] for r in v),
         "examples": [r["pid"] for r in sorted(tr or lv or v, key=lambda r: -r["b0"])[:5]]}
    out.append(f)
out.sort(key=lambda f: -f["n"])
json.dump(out, open(os.path.join(HERE, "families.json"), "w"), indent=1)
print("families", len(out))
for f in out:
    pt = f["paper_tradable"]["land1_fast"]
    if f["n"] < 8 and not pt: continue
    print(f"{f['family'][:110]:110s} n {f['n']:4d} dep {f['deployers']:4d} n0 {f['nonce0']:3d} trad {f['n_tradable']:3d} trig {f['n_trig_7_150']:4d} "
          f"paper {('%+.2f%% (%d, pos %d, pulled %d)' % (100 * pt['mean'], pt['n'], pt['pos'], pt['pulled'])) if pt else '-'} "
          f"| gates {dict(f['gates'])}")
