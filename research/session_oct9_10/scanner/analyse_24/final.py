"""compose the per-family rows (results.json from analyse.py + postwindow.json) into results_final.json for the orchestrator"""
import os, json
HERE = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(HERE, "results.json"))); PW = json.load(open(os.path.join(HERE, "postwindow.json")))["summary"]
K = json.load(open(os.path.join(HERE, "keys.json")))


def rule(s):
    if not s.get("n"): return "n 0 (no qualifying trigger)"
    return ("n %d, mean %+.2f%%, median %+.2f%%, win %.0f%%, pulled-first %d, $%+.3f a trade, $%+.2f a day" %
            (s["n"], 100 * s["mean"], 100 * s["median"], 100 * s["win"], s["pulled_first"], s["usd_trade"], s["usd_day"]))


rows = []
for i, k in enumerate(K):
    g = "F%d %s" % (i + 1, k); r = R[g]
    rows.append({"key": k, "count": r["count"], "launches_per_day": r["launches_per_day"], "front": rule(r["front"]), "follow": rule(r["follow"]),
                 "front_into_dev_buy": rule(r["front_into_dev_buy (pools with a launch-wallet buy only; sell 1 block after it)"]),
                 "first_buy_any": r["first_buy_any"], "first_buy_real": r["first_buy_real"], "pull": r["pull"], "trap": r["trap"], "capacity": r["capacity"],
                 "postwindow_to_head": PW[k]})
wide = {g: {"count": R[g]["count"], "launches_per_day": R[g]["launches_per_day"], "front": rule(R[g]["front"]), "follow": rule(R[g]["follow"]),
            "pull": R[g]["pull"], "first_buy_real": R[g]["first_buy_real"]} for g in R if g.startswith(("F1-", "F2-", "F34-", "F234-"))}
ctl = {k: (rule(v) if isinstance(v, dict) and "exits" in v else v) for k, v in R["controls"].items()}
json.dump({"families": rows, "wider_groups": wide, "controls": ctl, "postwindow_launcher": PW.get("F1-LAUNCHER 0x815542e8 (35)")},
          open(os.path.join(HERE, "results_final.json"), "w"), indent=1)
for x in rows: print(x["key"], "|", x["front"], "|", x["follow"], "|", x["front_into_dev_buy"])
for g, v in wide.items(): print(g[:40], "|", v["front"], "|", v["follow"])
for k, v in ctl.items(): print(k, v)
