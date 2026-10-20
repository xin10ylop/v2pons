"""trap test on the controls: the pull's delay after the scheduled buy with / without an outsider ahead of it (v2.433: our relay's
0.0058 ETH buy at launch+1 is a natural real-size outsider; the 0x65050a9b-router 0.00495 buys are the operator's own decoys)"""
import sys, os, json, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common10 import *  # noqa
rows = json.load(open(os.path.join(HERE, "rows.json")))
out = {}
for g in ("control:vbot-v2.433", "control:operator-A"):
    R = [r for r in rows[g] if r["sched"]]
    def grp(f):
        a = [r for r in R if f(r)]; pl = [r for r in a if r["pull"]]
        return {"pools": len(a), "pulled": len(pl), "pull_from_sched_p10_50_90": q([r["pull"]["from_sched"] for r in pl]),
                "pull_within_5_of_sched": sum(1 for r in pl if r["pull"]["from_sched"] <= 5)}
    out[g] = {"relay_before_sched": grp(lambda r: r["relay_before_sched"]), "no_relay_before_sched": grp(lambda r: not r["relay_before_sched"]),
              "real_outsider_before": grp(lambda r: bool(r["outsider_real"])), "no_real_outsider_before": grp(lambda r: not r["outsider_real"]),
              "real_outsider_non_65050a9b": grp(lambda r: any(o[2] != "0x65050a9b7e5075a2ba5ced7b1b64ee66262c40dc" for o in r["outsider_real"]))}
json.dump(out, open(os.path.join(HERE, "trap_controls.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
