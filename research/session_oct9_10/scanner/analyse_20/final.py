"""analyse_20: assemble results.json (the per-family rows for the orchestrator) from stats.json (analyse.py), controls_extra.json,
fam2_cap.json, fam4_cap.json, hookfee.json."""
import os, json
HERE = os.path.dirname(os.path.abspath(__file__))
S = json.load(open(os.path.join(HERE, "stats.json"))); CX = json.load(open(os.path.join(HERE, "controls_extra.json")))
C2 = json.load(open(os.path.join(HERE, "fam2_cap.json"))); C4 = json.load(open(os.path.join(HERE, "fam4_cap.json")))
K = json.load(open(os.path.join(HERE, "keys.json")))


def rule(x):
    if not x or not x.get("n"): return "n 0 (no trigger in any pool)"
    return (f"n {x['n']}, mean {100*x['mean']:+.2f}%, median {100*x['median']:+.2f}%, win {100*x['win']:.0f}%, pulled-first {x['pulled_first']}, "
            f"${x['usd_trade']:+.3f} a trade, ${x['usd_day']:+.2f} a day ({x['trades_day']}/day)")


C = S["controls"]; out = {"controls": C, "controls_extra": CX, "families": []}
fams = out["families"]
for k in K:
    r = S[k]
    fams.append({"key": k, "known": "none", "count": r["count"], "launches_per_day": r["launches_per_day"], "stats": r,
                 "front_rule": rule(r["front"]), "follow_rule": rule(r["follow"])})
out["wider"] = {k: {"count": v["count"], "per_day": v["launches_per_day"], "front": rule(v["front"]), "follow": rule(v["follow"]),
                    "first_buy_real": {a: v["first_buy_real"][a] for a in ("pools_with", "frac", "off_p10_50_90", "eth_p10_50_90")}, "pull": v["pull"]["frac"]}
                for k, v in S.items() if k.startswith("WIDER")}
out["fam2_capacity_decoded"] = C2; out["fam4_capacity_decoded"] = C4
json.dump(out, open(os.path.join(HERE, "results.json"), "w"), indent=1, default=str)
for f in fams: print(f["key"], "|", f["front_rule"], "|", f["follow_rule"])
for k, v in out["wider"].items(): print(k, v)
print("controls:", rule(C["v2433_front_all"]), "| live window", rule(C["v2433_front_livewindow_oct10_0907_1139"]), "| opA follow", rule(C["opA_follow"]))
