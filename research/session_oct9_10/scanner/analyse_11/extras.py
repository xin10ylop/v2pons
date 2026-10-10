"""small extras for the write-up: UTC launch ranges, the scheduled buyer's wallet diversity, v2.433 front before/after the competitors
appeared (Oct 10 14:47 UTC), the outsider-buy pull timing on v2.433 at the outsider's own block"""
import sys, os, json, collections, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common11 import *  # noqa
rows = json.load(open(os.path.join(HERE, "rows.json")))
u = lambda t: dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%m-%d %H:%M")
out = {}
for g, R in rows.items():
    ts = sorted(r["ts"] for r in R)
    sc = [r["sched"] for r in R if r["sched"]]
    out[g] = {"first_launch_utc": u(ts[0]), "last_launch_utc": u(ts[-1]),
              "sched_from_distinct": len(set(x["from"] for x in sc)), "sched_from_top": collections.Counter(x["from"] for x in sc).most_common(3),
              "sched_from_is_launch_wallet": sum(1 for r in R if r["sched"] and r["sched"]["from"] == r["launch_from"]),
              "sched_nonce_p10_50_90": q([x["nonce"] for x in sc if x["nonce"] is not None]),
              "sched_to": collections.Counter(f"{x['to']}:{x['sel']}" for x in sc).most_common(3)}
R = rows["control:vbot-v2.433"]
cut = int(dt.datetime(2026, 10, 10, 14, 47, tzinfo=dt.timezone.utc).timestamp())
out["v2433_front_before_1447"] = summarize([r["front"] for r in R if r["ts"] < cut])
out["v2433_front_after_1447"] = summarize([r["front"] for r in R if r["ts"] >= cut])
out["v2433_pools_after_1447_with_real_outsider"] = sum(1 for r in R if r["ts"] >= cut and r["outsider_real"])
out["v2433_pools_after_1447"] = sum(1 for r in R if r["ts"] >= cut)
json.dump(out, open(os.path.join(HERE, "extras.json"), "w"), indent=1)
print(json.dumps(out, indent=1, default=str))
