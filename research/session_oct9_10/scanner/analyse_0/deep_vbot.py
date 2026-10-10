"""Deeper checks on the two volume-bot families: (A) v2.433 trap test with our own relay as the outsider; (B) vbot-other (v3.0 / v5.0):
the front rule by 6-hour slice, by stake (the bot's minOut is 0.95 x its launch-state quote, so the room is ~0.08 ETH), the pools where
someone else bought before the bot (who, what they got, when the pull came), and the deadline/late-bot cases."""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common import *
from analyse import sched_minout, time_bucket
P = load_pools(); T = load_txs(); M = load_blocks_meta(); FF = load_families()
out = {}
# ---------------- A: v2.433, our relay as the outsider
K1 = "0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|2500|50|true"
rows = [json.loads(l) for l in open(os.path.join(HERE, "pools_0.jsonl"))]
def pstat(rs):
    d = [r["pull"]["after_sched"] for r in rs if r.get("pull") and r["pull"].get("after_sched") is not None]
    return {"n": len(rs), "pulled_3000": round(sum(1 for r in rs if r.get("pull")) / max(1, len(rs)), 3),
            "pull_after_bot": q(d, (.1, .5, .9)), "pull_2_4_after_bot": round(sum(1 for x in d if 2 <= x <= 4) / max(1, len(rs)), 3),
            "pulled_before_bot": sum(1 for r in rs if r.get("pull") and (r["sched"] is None or r["pull"]["after_sched"] < 0)),
            "pull_after_relay_buy": q([r["pull"]["off"] - r["relay_buy_off"] for r in rs if r.get("pull") and r.get("relay_buy_off") is not None], (.1, .5, .9))}
late = [r for r in rows if r["sub"] == "while-we-traded"]
out["v2433_relay_trap"] = {"while_we_traded_with_relay": pstat([r for r in late if r.get("relay_buy_off") is not None]),
                           "while_we_traded_without_relay": pstat([r for r in late if r.get("relay_buy_off") is None]),
                           "before_us": pstat([r for r in rows if r["sub"] == "before-us"])}
# ---------------- B: vbot-other
K2 = "0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|10000|200|true"
pids = FF[K2]["pids"]; E = load_events(set(pids))
mo_of = sched_minout("vbot-other")
pools = {pid: Pool(P[pid], E[pid], T, M) for pid in pids}
rows2 = {json.loads(l)["pid"]: json.loads(l) for l in open(os.path.join(HERE, "pools_1.jsonl"))}
by = collections.defaultdict(list); by_sub_stake = collections.defaultdict(list); hist = collections.defaultdict(list)
for pid, pl in pools.items():
    r = rows2[pid]; sub = r["sub"]
    if sub == "v0": continue
    by[(sub, time_bucket(r["ts"]))].append(r["front"])
    fs = r["sched"]
    B = pl.live_block + 1
    S = (pl.live_block + fs["off"] + 1) if fs and fs["off"] <= 20 else pl.live_block + 20
    S = max(S, B + 1)
    for stake in (0.0029, 0.0058, 0.012, 0.025, 0.05, 0.075, 0.1):
        t = pl.trade(B, S, stake=int(stake * 1e18), minout_check=mo_of)
        by_sub_stake[(sub, stake)].append(t)
    if fs: hist[sub].append(fs["off"])
out["vbot_other_front_by_slice"] = {f"{a}|{b}": {k: v for k, v in summarize(rs).items() if k in ("n", "mean", "median", "win", "pulled_first")} for (a, b), rs in sorted(by.items())}
out["vbot_other_front_by_stake"] = {}
for (sub, stake), rs in sorted(by_sub_stake.items()):
    v = [x["ret"] for x in rs if x.get("ret") is not None]
    m = st.mean(v)
    out["vbot_other_front_by_stake"][f"{sub}|{stake}"] = {"n": len(v), "mean": round(m, 5), "median": round(st.median(v), 5), "win": round(sum(1 for a in v if a > 0) / len(v), 3),
                                                          "bot_buy_dropped": sum(1 for x in rs if x.get("dropped")), "usd_trade": round(m * stake * ETH_USD, 3),
                                                          "usd_day": round(m * stake * ETH_USD * len(v) / WINDOW_DAYS, 1)}
out["vbot_other_bot_offset_hist"] = {s: sorted(collections.Counter(v).items()) for s, v in hist.items()}
# who else bought before the bot (all classes but dust/sched), what they made: their buy and their sell (first 8 swaps carry tx from)
comp = collections.defaultdict(lambda: {"pools": 0, "eth": [], "offs": [], "pull_after_bot": [], "sells": 0, "sell_offs": []})
for pid, pl in pools.items():
    r = rows2[pid]
    for o in r["before_sched"]:
        if o["cls"] in ("other", "unknown"):
            c = comp[o["from"]]; c["pools"] += 1; c["eth"].append(o["eth"]); c["offs"].append(o["off"])
            if r.get("pull") and r["sched"]: c["pull_after_bot"].append(r["pull"]["after_sched"])
            for x in pl.seq:
                if not x["buy"] and x["from"] == o["from"]:
                    c["sells"] += 1; c["sell_offs"].append(x["bn"] - pl.live_block); break
out["vbot_other_outsiders"] = {w: {"pools": c["pools"], "eth": q(c["eth"], (0, .5, 1), 7), "offs": q(c["offs"], (0, .5, 1)), "pull_after_bot": c["pull_after_bot"],
                                   "sells_seen_in_first8": c["sells"], "sell_offs": c["sell_offs"]} for w, c in comp.items()}
json.dump(out, open(os.path.join(HERE, "deep_vbot.json"), "w"), indent=1, default=str)
for k, v in out.items():
    print(k); print(json.dumps(v, default=str)[:3000])
