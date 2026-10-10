import sys, json, datetime
sys.path.insert(0, "."); from common9 import *
F = load_families(); P = load_pools(); T = load_txs(); M = load_blocks_meta()
raw = json.load(open("results_raw.json")); calib = json.load(open("calib.json")); post = json.load(open("postwindow.json"))
f4l = json.load(open("fam4_long.json")); f4c = json.load(open("fam4_crowd.json")); f4f = json.load(open("fam4_flow.json"))
k4 = "create|60808060|3740|2500|25|true"
crowd = set(f4c["where"].keys()) - {"0x0b410a5f0594fd4500acccd4b97b91da8987c40c"}
E = load_events(set(F[k4]["pids"]))
pools = [Pool(P[p], E.get(p), T, M) for p in F[k4]["pids"]]
fr_crowd = [pl.front(lambda x: x["from"] in crowd) for pl in pools]
extra = {"fam4_front_first_crowd_buy": summarize(fr_crowd), "fam4_front_crowd_detail": [(pl.pid[:12], r["sched_rel"], round(r["ret"], 5)) for pl, r in zip(pools, fr_crowd)]}
for k, r in raw.items():
    ts = [P[p]["launch_ts"] for p in F[k]["pids"]]
    r["utc_span"] = [datetime.datetime.utcfromtimestamp(min(ts)).strftime("%Y-%m-%d %H:%M:%S"), datetime.datetime.utcfromtimestamp(max(ts)).strftime("%Y-%m-%d %H:%M:%S")]
    r["post_window_to_head"] = {"head": post["head"], "logs": post[k]["logs"], "pools_with_activity": post[k]["pools_with_activity"]}
out = {"method": "common9.py (exact v4 replay as explore/chk/replay.py; buy at the end of block B, sell at the head of S, pull <= S = stake lost; gas 2 x 104,000 x launch-block base fee; stake 0.0058 ETH = $15)",
       "calibration": calib, "families": raw, "extra": extra, "fam4_hold_within_window": f4f["hold_summary"], "fam4_long_hold": f4l, "fam4_crowd": f4c}
json.dump(out, open("results.json", "w"), indent=1, default=str)
print(json.dumps(extra, indent=0)[:1500])
for k, r in raw.items(): print(k, r["utc_span"], r["post_window_to_head"])
