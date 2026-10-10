"""results_final.json: the per-family numbers handed to the orchestrator, read from results.json (analyse.py)."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__)); R = json.load(open(os.path.join(HERE, "results.json")))
g1 = "F1 SELECTOR:ec64ddcf|196|0|60|false"; g2 = "F2 CODEHASH:8ce82419|bc9d39fd|*|0|200|false"
keep = ("count", "launches_per_day", "first_buy_any", "first_buy_real", "first_sched_buy", "op_buys_first3000", "pull", "trap", "front", "follow",
        "front_no20cap (sell 1 block after the first scheduled buy, deadline +3000)", "capacity", "eth_tax_buy_sell_ppm", "extras", "gas_usd_median")
out = {"window_days": R["window_days"], "controls": R["controls"], "pricer_check_assigned": R["pricer_check_assigned"],
       "SELECTOR:ec64ddcf|196|0|60|false": {k: R[g1].get(k) for k in keep if k in R[g1]},
       "CODEHASH:8ce82419af8f18d1be64b864a92a7313a543947b187c6c0a1c94a6feac23c407|bc9d39fd|*|0|200|false": {k: R[g2].get(k) for k in keep if k in R[g2]},
       "CONTROL vbot-v2.433": {k: R["CONTROL vbot-v2.433"].get(k) for k in keep + ("bot_buy",) if k in R["CONTROL vbot-v2.433"]},
       "CONTROL operator-A": {k: R["CONTROL operator-A"].get(k) for k in keep if k in R["CONTROL operator-A"]},
       "verdicts": {"SELECTOR:ec64ddcf|196|0|60|false": "no-schedule", "CODEHASH:8ce82419...|bc9d39fd|*|0|200|false": "unprofitable"}}
json.dump(out, open(os.path.join(HERE, "results_final.json"), "w"), indent=1, default=str)
print(json.dumps({k: (v["front"], v["follow"]) for k, v in out.items() if isinstance(v, dict) and "front" in v}, default=str)[:3000])
