"""calibration on the controls: v2.433 front (all, the live window 09:07-11:40 UTC Oct 10, by 6 h slice, by bot-buy size, kept vs dropped)
and operator A follow; pricer validation on every buy (prediction from the chain's own pre-state over the actual output)"""
import sys, os, json, collections, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common11 import *  # noqa
rows = json.load(open(os.path.join(HERE, "rows.json")))
ts = lambda s: int(dt.datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).timestamp())
live_a, live_b = ts("2026-10-10 09:07"), ts("2026-10-10 11:40")
R = rows["control:vbot-v2.433"]
out = {}
out["v2433_front_all"] = summarize([r["front"] for r in R])
out["v2433_front_live_window_0907_1140"] = summarize([r["front"] for r in R if live_a <= r["ts"] <= live_b])
out["v2433_front_bot_buy_kept"] = summarize([r["front"] for r in R if r["front"].get("exit") == "sold" and not r["front"].get("dropped")])
out["v2433_front_bot_buy_dropped"] = summarize([r["front"] for r in R if r["front"].get("dropped")])
out["v2433_front_exits"] = dict(collections.Counter(r["front"]["exit"] for r in R))
out["v2433_front_trig_rel"] = dict(collections.Counter(r["front"].get("trig") for r in R).most_common(12))
out["v2433_sched_rel_p10_50_90"] = q([r["sched"]["rel"] for r in R if r["sched"]])
out["v2433_sched_eth_p10_50_90"] = q([r["sched"]["eth"] for r in R if r["sched"]])
out["v2433_minout_over_quote_p10_50_90"] = q([r["cap"]["minout_over_quote"] for r in R if r["cap"]], nd=5)
out["v2433_cap_from_launch_p10_50_90"] = q([r["cap"]["cap_from_launch"] for r in R if r["cap"]], nd=5)
out["v2433_pull_from_sched_counts"] = dict(collections.Counter(r["pull"]["from_sched"] for r in R if r["pull"] and r["pull"]["from_sched"] is not None).most_common(8))
# why dropped: who sits ahead of the bot's buy in those pools
dr = [r for r in R if r["front"].get("dropped")]
c = collections.Counter()
ahead_eth = []
for r in dr:
    o = [x for x in r["outsiders"] if x[1] >= 0.0002]
    ahead_eth.append(sum(x[1] for x in r["outsiders"]))
    for x in o: c[(x[2], x[3])] += 1
out["dropped_pools_outsider_real_ahead_top"] = [[f"{k[0]}|{k[1]}", v] for k, v in c.most_common(10)]
out["dropped_pools_eth_ahead_p10_50_90"] = q(ahead_eth, nd=5)
by6 = collections.defaultdict(list)
for r in R:
    h = dt.datetime.fromtimestamp(r["ts"], dt.timezone.utc); by6[h.strftime("%m-%d ") + "%02dh" % (h.hour // 6 * 6)].append(r["front"])
out["v2433_front_by_6h"] = {k: {kk: v.get(kk) for kk in ("n", "mean", "median", "win")} for k, v in ((k, summarize(v)) for k, v in sorted(by6.items()))}
bys = collections.defaultdict(list)
for r in R:
    if r["sched"] and r["front"].get("ret") is not None:
        e = r["sched"]["eth"]; b = "<0.04" if e < 0.04 else ("0.04-0.12" if e < 0.12 else ("0.12-0.22" if e < 0.22 else ">=0.22"))
        bys[b].append(r["front"])
out["v2433_front_by_bot_size"] = {k: {kk: v.get(kk) for kk in ("n", "mean", "median", "win")} for k, v in ((k, summarize(v)) for k, v in sorted(bys.items()))}
out["v2433_follow"] = summarize([r["follow"] for r in R if r["follow"]])
val = [x for g in rows.values() for r in g for x in r["val"]]
out["pricer_validation_buys"] = {"n": len(val), "p01_50_99": q(val, (.01, .5, .99), nd=8), "abs_err_gt_1e-4": sum(1 for x in val if abs(x - 1) > 1e-4)}
RA = rows["control:operator-A"]
out["opA_follow"] = summarize([r["follow"] for r in RA if r["follow"]])
out["opA_front"] = summarize([r["front"] for r in RA])
out["opA_first_real_rel_p10_50_90"] = q([r["first_real"]["rel"] for r in RA if r["first_real"]])
out["opA_pull_rel_p10_50_90"] = q([r["pull"]["rel"] for r in RA if r["pull"]])
json.dump(out, open(os.path.join(HERE, "calib.json"), "w"), indent=1)
for k, v in out.items(): print(k, json.dumps(v)[:700])
