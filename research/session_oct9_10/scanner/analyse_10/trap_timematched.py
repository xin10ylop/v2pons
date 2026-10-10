"""v2.433: the quick pull (sched + 2..5) by hour, pools with and without our relay's buy ahead (is the quick pull a reaction to us, or a regime?)"""
import sys, os, json, collections, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common10 import *  # noqa
rows = json.load(open(os.path.join(HERE, "rows.json")))
R = [r for r in rows["control:vbot-v2.433"] if r["sched"]]
H = collections.defaultdict(lambda: {"relay": [0, 0], "norelay": [0, 0]})
for r in R:
    h = dt.datetime.fromtimestamp(r["ts"], dt.timezone.utc).strftime("%m-%d %H")
    k = "relay" if r["relay_before_sched"] else "norelay"
    H[h][k][0] += 1
    if r["pull"] and r["pull"]["from_sched"] is not None and r["pull"]["from_sched"] <= 5: H[h][k][1] += 1
out = {h: v for h, v in sorted(H.items())}
json.dump(out, open(os.path.join(HERE, "trap_timematched.json"), "w"), indent=1)
for h, v in sorted(H.items()): print(h, "relay pools/quick", v["relay"], "no-relay pools/quick", v["norelay"])
