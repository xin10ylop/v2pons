"""calibration of the pricer: v2.433 front in the live window (HANDOFF 16.2: Oct 10 09:08-11:40 UTC, $15 trades +14.1% mean), the whole family
by 6-hour slice, and the pools where the bot's buy is dropped (someone else's ETH ahead + ours > its 0.99 minOut slack); operator A follow."""
import sys, os, datetime, json, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from pricer import summarize, q
rows = [json.loads(l) for l in open(os.path.join(HERE, "pools_control-v2433.jsonl"))]
ts = lambda *a: datetime.datetime(*a, tzinfo=datetime.timezone.utc).timestamp()
out = {}
sel = [r for r in rows if ts(2026, 10, 10, 9, 8) <= r["ts"] <= ts(2026, 10, 10, 11, 40)]
out["live_window"] = summarize([r["front"] for r in sel])
out["live_window_with_relay"] = summarize([r["front"] for r in sel if r.get("relay_buy_off") is not None])
out["whole_no_drop"] = summarize([r["front"] for r in rows if not r["front"].get("dropped")])
out["whole_dropped"] = summarize([r["front"] for r in rows if r["front"].get("dropped")])
# who is ahead in the dropped pools
c = collections.Counter(); sz = []
for r in rows:
    if r["front"].get("dropped"):
        for o in r["before_sched"]:
            if o["eth"] >= 0.001: c[(o["cls"], o["to"])] += 1; sz.append(o["eth"])
out["dropped_ahead_buyers"] = [[f"{a}|{b}", n] for (a, b), n in c.most_common(8)]
out["dropped_ahead_eth"] = q(sz, (0, .5, 1), 6)
by = collections.defaultdict(list)
for r in rows:
    d = datetime.datetime.fromtimestamp(r["ts"], datetime.timezone.utc); by[f"{d:%m-%d} {d.hour // 6 * 6:02d}h"].append(r["front"])
out["by_6h"] = {k: {kk: summarize(v)[kk] for kk in ("n", "mean", "median", "win")} for k, v in sorted(by.items())}
A = [json.loads(l) for l in open(os.path.join(HERE, "pools_control-opA.jsonl"))]
out["opA_follow"] = summarize([r.get("follow") for r in A])
for k, v in out.items(): print(k, json.dumps(v)[:600])
json.dump(out, open(os.path.join(HERE, "calib.json"), "w"), indent=1)
# trap-test calibration on v2.433: pools where our real relay bought 0.0058 ETH at launch + 1 (an outsider of our size) vs pools without it
w = [r for r in rows if r.get("relay_buy_off") is not None]; wo = [r for r in rows if r.get("relay_buy_off") is None]
def ps(rs):
    a = [r["pull"]["after_sched"] for r in rs if r.get("pull") and r["pull"]["after_sched"] is not None]
    return {"n": len(rs), "pulled_3000": sum(1 for r in rs if r.get("pull")), "pull_after_sched_p10_50_90": q(a), "pull_off_launch_p10_50_90": q([r["pull"]["off"] for r in rs if r.get("pull")]),
            "pull_2_4_after_sched": sum(1 for x in a if 2 <= x <= 4)}
out["trap_calib_relay"] = {"with_our_relay": ps(w), "without": ps(wo)}
print("trap_calib_relay", json.dumps(out["trap_calib_relay"]))
json.dump(out, open(os.path.join(HERE, "calib.json"), "w"), indent=1)
