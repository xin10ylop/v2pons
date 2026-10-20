"""control trap test on v2.433: does the pull come sooner after the bot's buy when an outside buyer (our own relay) bought ahead of it?
   confound check: compare within the hours the relay was trading"""
import sys, os, json, collections, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common7 import *  # noqa
rows = json.load(open(os.path.join(HERE, "rows.json")))["control:vbot-v2.433"]
E = load_events(set(r["pid"] for r in rows))
relay = {r["pid"]: any(s["sender"] == RELAY for s in E[r["pid"]]["swaps"]) for r in rows}
first_relay_ts = min(r["ts"] for r in rows if relay[r["pid"]]); last_relay_ts = max(r["ts"] for r in rows if relay[r["pid"]])
def d(rs):
    x = [r["pull"] - r["sb"]["off"] for r in rs if r["sb"] and r["pull"] is not None]
    return {"pools": len(rs), "pulled": len(x), "pull_minus_sched_p10_50_90": q(x), "within_2_4": sum(1 for v in x if 2 <= v <= 4)}
out = {"relay_first_launch_utc": dt.datetime.fromtimestamp(first_relay_ts, dt.timezone.utc).isoformat(), "relay_last_launch_utc": dt.datetime.fromtimestamp(last_relay_ts, dt.timezone.utc).isoformat()}
inwin = [r for r in rows if first_relay_ts <= r["ts"] <= last_relay_ts]
out["in_relay_hours_with_relay"] = d([r for r in inwin if relay[r["pid"]]])
out["in_relay_hours_without_relay"] = d([r for r in inwin if not relay[r["pid"]]])
out["before_relay_hours"] = d([r for r in rows if r["ts"] < first_relay_ts])
by_h = collections.defaultdict(lambda: [[], []])
for r in inwin:
    h = dt.datetime.fromtimestamp(r["ts"], dt.timezone.utc).strftime("%m-%d %H")
    if r["sb"] and r["pull"] is not None: by_h[h][relay[r["pid"]]].append(r["pull"] - r["sb"]["off"])
    else: by_h[h][relay[r["pid"]]].append(None)
out["by_hour_[without,with]_median_pull_minus_sched_and_n"] = {h: [(q(v[0])[1] if q(v[0]) else None, len(v[0])), (q(v[1])[1] if q(v[1]) else None, len(v[1]))] for h, v in sorted(by_h.items())}
json.dump(out, open(os.path.join(HERE, "trap_v2433.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
