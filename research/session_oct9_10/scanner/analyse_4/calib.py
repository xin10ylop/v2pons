#!/usr/bin/env python3
"""v2.433 control: the front rule by time slice (the live audit window Oct 10 09:08-11:40 UTC should price near +14%), by bot-buy size,
and the pull timing in pools with our relay ahead vs without, within the same hours (reaction vs time-of-day)."""
import sys, os, json, statistics as st, collections, datetime
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from ana import *   # noqa
rows = [json.loads(l) for l in open(os.path.join(HERE, "pools_0.jsonl"))]
def ts(s): return int(datetime.datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=datetime.timezone.utc).timestamp())
out = {}
w = [r for r in rows if ts("2026-10-10 09:07") <= r["ts"] <= ts("2026-10-10 11:40")]
out["live_audit_window"] = summarize([r["front"] for r in w])
print("front, Oct 10 09:07-11:40 UTC (live audit: mean +13.97%, median +16.25%):", out["live_audit_window"])
# by 6 h slice
sl = collections.defaultdict(list)
for r in rows:
    d = datetime.datetime.fromtimestamp(r["ts"], datetime.timezone.utc); sl[f"{d:%m-%d} {d.hour // 6 * 6:02d}h"].append(r)
out["by_6h"] = {}
for k in sorted(sl):
    rs = sl[k]; s = summarize([r["front"] for r in rs])
    relay = sum(1 for r in rs if r["relay_buy_off"] is not None)
    pq = pct([r["pull"]["after_sched"] for r in rs if r["pull"] and r["pull"]["after_sched"] is not None])
    pf = round(sum(1 for r in rs if r["pull"]) / len(rs), 3)
    se = pct([r["sched"]["eth"] for r in rs if r["sched"]], nd=4)
    out["by_6h"][k] = {"n": len(rs), "relay": relay, "front_mean": s.get("mean"), "front_median": s.get("median"), "win": s.get("win"), "pulled_first": s.get("pulled_first"),
                       "pull_frac": pf, "pull_after_bot_p10_50_90": pq, "bot_eth_p10_50_90": se}
    print(k, out["by_6h"][k])
# by bot buy size
out["by_bot_eth"] = {}
for lo, hi in ((0, 0.03), (0.03, 0.08), (0.08, 0.15), (0.15, 0.22), (0.22, 1)):
    rs = [r for r in rows if r["sched"] and lo <= r["sched"]["eth"] < hi]
    s = summarize([r["front"] for r in rs]); out["by_bot_eth"][f"{lo}-{hi}"] = {"n": s["n"], "mean": s.get("mean"), "median": s.get("median")}
print("by bot eth", out["by_bot_eth"])
# reaction test within hours: for each UTC hour with both relay and non-relay pools, pull after the bot's buy
hrs = collections.defaultdict(lambda: {"relay": [], "none": []})
for r in rows:
    if not r["sched"]: continue
    h = datetime.datetime.fromtimestamp(r["ts"], datetime.timezone.utc).strftime("%m-%d %H")
    d = r["pull"]["after_sched"] if r["pull"] else 9999
    hrs[h]["relay" if r["relay_buy_off"] is not None else "none"].append(d)
both = {h: v for h, v in hrs.items() if v["relay"] and v["none"]}
out["same_hour"] = {}
for h in sorted(both):
    v = both[h]
    out["same_hour"][h] = {"relay_n": len(v["relay"]), "relay_pull_after_bot_med": st.median(v["relay"]), "relay_le4": sum(1 for d in v["relay"] if d <= 4),
                           "none_n": len(v["none"]), "none_pull_after_bot_med": st.median(v["none"]), "none_le4": sum(1 for d in v["none"] if d <= 4)}
    print(h, out["same_hour"][h])
R = [d for v in both.values() for d in v["relay"]]; N = [d for v in both.values() for d in v["none"]]
out["same_hour_total"] = {"relay": {"n": len(R), "pull_le4_after_bot": sum(1 for d in R if d <= 4), "median": st.median(R)},
                          "none": {"n": len(N), "pull_le4_after_bot": sum(1 for d in N if d <= 4), "median": st.median(N)}}
print("same hours total", out["same_hour_total"])
json.dump(out, open(os.path.join(HERE, "calib.json"), "w"), indent=1)
