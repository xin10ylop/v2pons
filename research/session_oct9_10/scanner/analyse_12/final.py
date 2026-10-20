"""results.json: per family (the four assigned + the two controls) the numbers of the structured output"""
import sys, os, json, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from px import *  # noqa
S = json.load(open(os.path.join(HERE, "stats.json"))); R = json.load(open(os.path.join(HERE, "rows.json")))
X = json.load(open(os.path.join(HERE, "extra.json"))); L7 = json.load(open(os.path.join(HERE, "loose7f.json")))
REL = json.load(open(os.path.join(HERE, "related.json")))
utc = lambda t: dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%m-%d %H:%M")
res = {"method": {"pricer": "px.py (replay.py model on the census)", "stake_eth": 0.0058, "usd_per_eth": round(USD_PER_ETH, 2), "gas_units": 2 * GAS_UNITS,
                  "window_days": round(WINDOW_DAYS, 4), "min_real_eth": 0.0002,
                  "front": "buy lands at the end of launch+1; sell lands at the head of (first scheduled buy behind ours)+1, capped at launch+20",
                  "follow": "buy lands at the end of (first real buy >= 0.0002)+1; sell lands at the head of (next real buy behind ours)+1, capped at our buy+4",
                  "scheduled_buy": "v2.433: the bot router's (0x1cbaf24d c1120e3d) first buy; others: the first non-launch buy >= 0.0002 ETH"},
       "families": {}}
for g, s in S.items():
    rows = R[g]
    ts = [r["ts"] for r in rows]
    s["launch_utc_first_last"] = [utc(min(ts)), utc(max(ts))]
    s["front_fmt"] = fmt_rule(s["front"]); s["follow_fmt"] = fmt_rule(s["follow"])
    res["families"][g] = s
res["families"]["0x8366a39cc670b4001a1121b8f6a443a643e40951|6276cbbe|196|3000|60|true"]["front_from_add"] = X["family3_front_from_add"]
res["families"]["0x8366a39cc670b4001a1121b8f6a443a643e40951|6276cbbe|196|3000|60|true"]["add_detail"] = X["family3"]
res["extra_buyers_reach"] = {k: v for k, v in X.items() if not k.startswith("family3")}
res["loose_7fde822e"] = L7; res["related"] = REL
json.dump(res, open(os.path.join(HERE, "results.json"), "w"), indent=1, default=str)
for g, s in res["families"].items():
    print(g, s["launch_utc_first_last"]); print("  front ", s["front_fmt"]); print("  follow", s["follow_fmt"])
