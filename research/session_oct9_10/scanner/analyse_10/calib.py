"""calibration on the controls: v2.433 front (all, live window, relay-traded pools, by bot-buy drop) and operator A follow; pricer validation"""
import sys, os, json, collections, statistics as st, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common10 import *  # noqa
rows = json.load(open(os.path.join(HERE, "rows.json")))
ts = lambda s: int(dt.datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).timestamp())
live_a, live_b = ts("2026-10-10 09:07"), ts("2026-10-10 11:40")
R = rows["control:vbot-v2.433"]
out = {}
out["v2433_front_all"] = summarize([r["front"] for r in R])
out["v2433_front_live_window_0907_1140"] = summarize([r["front"] for r in R if live_a <= r["ts"] <= live_b])
out["v2433_front_relay_traded_pools"] = summarize([r["front"] for r in R if r["relay_in"]])
out["v2433_front_bot_buy_kept"] = summarize([r["front"] for r in R if r["front"].get("exit") == "sold" and not r["front"].get("dropped")])
out["v2433_front_bot_buy_dropped"] = summarize([r["front"] for r in R if r["front"].get("dropped")])
out["v2433_front_exits"] = dict(collections.Counter(r["front"]["exit"] for r in R))
out["v2433_sched_rel_p10_50_90"] = q([r["sched"]["rel"] for r in R if r["sched"]])
out["v2433_sched_eth_p10_50_90"] = q([r["sched"]["eth"] for r in R if r["sched"]])
out["v2433_minout_over_quote_p10_50_90"] = q([r["cap"]["minout_over_quote"] for r in R if r["cap"]], nd=5)
out["v2433_cap_from_launch_p10_50_90"] = q([r["cap"]["cap_from_launch"] for r in R if r["cap"]], nd=5)
out["v2433_room_left_p10_50_90"] = q([r["cap"]["room_left_at_chain_state"] for r in R if r["cap"]], nd=5)
out["v2433_pull_from_sched_counts"] = dict(collections.Counter(r["pull"]["from_sched"] for r in R if r["pull"] and r["pull"]["from_sched"] is not None).most_common(8))
# by 6-hour slice
by6 = collections.defaultdict(list)
for r in R:
    h = dt.datetime.fromtimestamp(r["ts"], dt.timezone.utc); by6[h.strftime("%m-%d ") + "%02dh" % (h.hour // 6 * 6)].append(r["front"])
out["v2433_front_by_6h"] = {k: {kk: v.get(kk) for kk in ("n", "mean", "median", "win")} for k, v in ((k, summarize(v)) for k, v in sorted(by6.items()))}
# by bot buy size (our return is a function of it)
bys = collections.defaultdict(list)
for r in R:
    if r["sched"] and r["front"].get("ret") is not None:
        e = r["sched"]["eth"]; b = "<0.04" if e < 0.04 else ("0.04-0.12" if e < 0.12 else ("0.12-0.22" if e < 0.22 else ">=0.22"))
        bys[b].append(r["front"])
out["v2433_front_by_bot_size"] = {k: {kk: v.get(kk) for kk in ("n", "mean", "median", "win")} for k, v in ((k, summarize(v)) for k, v in sorted(bys.items()))}
# pricer validation: predicted output of every buy from the chain's own pre-state over its actual output
val = [x for g in rows.values() for r in g for x in r["val"]]
out["pricer_validation_buys"] = {"n": len(val), "p01_50_99": q(val, (.01, .5, .99), nd=8), "abs_err_gt_1e-4": sum(1 for x in val if abs(x - 1) > 1e-4)}
# operator A
RA = rows["control:operator-A"]
out["opA_follow"] = summarize([r["follow"] for r in RA if r["follow"]])
out["opA_front"] = summarize([r["front"] for r in RA])
out["opA_first_real_rel_p10_50_90"] = q([r["first_real"]["rel"] for r in RA if r["first_real"]])
json.dump(out, open(os.path.join(HERE, "calib.json"), "w"), indent=1)
for k, v in out.items(): print(k, json.dumps(v)[:600])
