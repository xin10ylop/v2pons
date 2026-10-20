"""analyse_22: the per-family answer (the structured output) assembled from results.json, slowpump.json, validate.json, crowd_minout.json."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(HERE, "results.json"))); S = json.load(open(os.path.join(HERE, "slowpump.json")))
V = json.load(open(os.path.join(HERE, "validate.json"))); C = json.load(open(os.path.join(HERE, "crowd_minout.json")))
K = json.load(open(os.path.join(HERE, "keys.json")))
fam = lambda pre: next(v for k, v in R.items() if k.startswith(pre + " "))
out = {"controls": R["controls"], "F1_operator_rule": {k: S[k] for k in S if k not in ("pools",)}, "F1_pools": S["pools"],
       "pricer_validation_on_F1_operator": {k: V[k] for k in V if k != "outsider_round_trips"}, "outsider_round_trips": V["outsider_round_trips"],
       "crowd_minout": {"minout_over_actual_output": C["minout_over_actual_output"]},
       "families": {K[0]: fam("F1"), K[1]: fam("F2"), K[2]: fam("F3"), K[3]: fam("F4")},
       "wider": {"F1-WIDE": fam("F1-WIDE"), "F2-WIDE": fam("F2-WIDE"), "F4-WIDE": fam("F4-WIDE")}}
json.dump(out, open(os.path.join(HERE, "results_final.json"), "w"), indent=1, default=str)
print("ok", os.path.getsize(os.path.join(HERE, "results_final.json")))
