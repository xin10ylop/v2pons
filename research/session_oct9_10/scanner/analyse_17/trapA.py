"""Operator A trap test: does the pull come sooner after an outside buy? The only real outside buys in its pools are our own relay's live
follow buys (35 of 77 pools; nobody else buys before or between the crowd). Compare the pull delay from the crowd's first buy in pools with and
without our relay buy, and the delay from our relay buy; the assigned fee-1500 family separately. Also: pulls within 20 blocks of launch."""
import sys, os, json, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common17 import q
D = json.load(open(os.path.join(HERE, "rows.json"))); R = D["rows"]
KEYS = json.load(open(os.path.join(HERE, "keys.json")))
out = {}
for g in ("control:operator-A", KEYS[0]):
    rows = R[g]
    rel = [r for r in rows if r["relay_buy_rel"]]; nrel = [r for r in rows if not r["relay_buy_rel"]]
    def pf(rs, k): return [r["pull"][k] for r in rs if r["pull"] and r["pull"][k] is not None]
    o = {"pools_with_relay_buy": len(rel), "pools_without": len(nrel),
         "relay_buy_rel_from_launch": q([r["relay_buy_rel"][0] for r in rel]),
         "relay_buy_from_first_crowd": q([r["relay_buy_rel"][0] - r["sched"]["rel"] for r in rel if r["sched"]]),
         "with_relay_pulled": sum(1 for r in rel if r["pull"]), "with_relay_pull_from_relay_buy": q(pf(rel, "from_first_relay_buy")),
         "with_relay_pull_from_first_crowd": q(pf(rel, "from_sched")), "with_relay_pull_from_launch": q(pf(rel, "rel")),
         "with_relay_pull_within_6_of_relay": sum(1 for x in pf(rel, "from_first_relay_buy") if x <= 6),
         "without_relay_pulled": sum(1 for r in nrel if r["pull"]), "without_relay_pull_from_first_crowd": q(pf(nrel, "from_sched")),
         "without_relay_pull_from_launch": q(pf(nrel, "rel")),
         "without_relay_pull_within_12_of_first_crowd": sum(1 for x in pf(nrel, "from_sched") if x <= 12),
         "with_relay_pull_within_12_of_first_crowd": sum(1 for x in pf(rel, "from_sched") if x <= 12),
         "crowd_buys_before_pull_without_relay": q([sum(1 for b in r["buys20"] if b[1] >= 0.0002 and (r["pull"] is None or b[0] < r["pull"]["rel"])) for r in nrel]),
         "front_wait_trig_rel": q([r["front_wait"].get("trig") for r in rows if r["front_wait"].get("trig") is not None])}
    out[g] = o
    print(g); [print("  ", k, v) for k, v in o.items()]
json.dump(out, open(os.path.join(HERE, "trapA.json"), "w"), indent=1)
