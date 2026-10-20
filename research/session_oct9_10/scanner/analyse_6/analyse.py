"""analyse_6: the four assigned families + the two controls, one method.
Per family: launches a day, launcher, the first non-launch buy, the first real (>= 0.0002 ETH) buy, the scheduled buy, the pull, outsiders
before the scheduled buy and the trap test, the front and follow rules priced exactly (pricer6), and the scheduled buy's room.
Writes results.json and pools.jsonl. Run: python3 -I analyse.py"""
import sys, os, json, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from pricer6 import *

KEYS = ["0x404700be6b535e6aa7fd744f242d8cf78135817c|7fde822e|804|10000|200|true",
        "0xe696daf67fe25c5936187fc1edf38404353d5f72|7fde822e|804|10000|200|true",
        "0xb40382548413c559ad7f0bb6e24410401238eded|7fde822e|804|10000|200|true",
        "0x0000ffffbe8efe702c8703ae3477ff5de3d319c0|ac9650d8|1316|2500|25|true"]
V2KEY = "0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|2500|50|true"
DECOY_ROUTERS = {"0x65050a9b7e5075a2ba5ced7b1b64ee66262c40dc", "0xfd1b271f235e5230eaee9d914ccb1af495bfb758"}
P = load_pools(); F = load_families()
groups = {k: F[k]["pids"] for k in KEYS}
groups["control:vbot-v2.433"] = [pid for pid, p in P.items() if p["known"] == "vbot-v2.433"]
groups["control:operator-A"] = [pid for pid, p in P.items() if p["known"] == "operator-A"]
allp = set(x for v in groups.values() for x in v)
E = load_events(allp); T = load_txs(); M = load_blocks_meta()
is_bot = lambda x: x["to"] == VBOT_ROUTER and x["sel"] == "c1120e3d"
is_real = lambda x: x["eth"] >= MIN_REAL and x["from"] != DUST
SCHED = {"control:vbot-v2.433": is_bot}
MINOUT = {"control:vbot-v2.433": vbot_minout}


def own(x, pl):
    """the operator's own non-scheduled wallets we know of: the volume bot's decoys, the dust bot (chain-wide)"""
    return x["from"] == DUST or x["to"] in DECOY_ROUTERS


def analyse(name, pids):
    is_sched = SCHED.get(name, is_real); mo_of = MINOUT.get(name)
    rows = []; fr = []; fo = []
    for pid in pids:
        p = P[pid]; pl = Pool(p, E.get(pid), T, M)
        bs = pl.buys()
        fb = bs[0] if bs else None
        rb = next((x for x in bs if is_real(x)), None)
        sb = next((x for x in bs if is_sched(x)), None)
        pull = pl.pulls[0] if pl.pulls else None
        pull_tx = T.get(pull["tx"]) if pull else None
        outs = [x for x in bs if sb and (x["bn"], x["li"]) < (sb["bn"], sb["li"]) and not is_sched(x) and not own(x, pl)] if sb else \
               [x for x in bs if not own(x, pl)]
        cap = None; cap_left = None; mo = None
        if sb is not None:
            mo = mo_of(sb) if mo_of else None
            assumed = mo is None
            s_pre, L_pre = pl.state_before(sb)
            if assumed:
                mo = int(0.99 * v4math.buy_out_int(int(pl.s_eff), pl.L0, sb["eth"], sb["fee"]))
            cap = room(pl.s_eff, pl.L0, sb["eth"], sb["fee"], mo)
            cap_left = room(s_pre, L_pre, sb["eth"], sb["fee"], mo)
        f1 = front(pl, is_sched, minout=mo_of) if pl.L0 > 0 else None
        f2 = follow(pl) if pl.L0 > 0 else None
        fr.append(f1); fo.append(f2)
        rows.append({"fam": name, "pid": pid, "b0": pl.b0, "ts": p["launch_ts"], "from": p["launch_from"], "nonce": p["launch_nonce"], "L0": pl.L0, "fee": pl.fee,
                     "base_fee": pl.base_fee, "n_swaps": len(pl.seq), "n_buys": len(bs),
                     "first_buy": fb and {"rel": fb["rel"], "eth": fb["eth"] / 1e18, "to": fb["to"], "from": fb["from"], "sel": fb["sel"]},
                     "first_real_buy": rb and {"rel": rb["rel"], "eth": rb["eth"] / 1e18, "to": rb["to"], "from": rb["from"], "sel": rb["sel"]},
                     "sched": sb and {"rel": sb["rel"], "eth": sb["eth"] / 1e18, "to": sb["to"], "from": sb["from"], "minout": mo, "minout_assumed": mo_of is None or mo_of(sb) is None,
                                      "room_from_launch_eth": cap, "room_left_eth": cap_left},
                     "pull": pull and {"rel": pull["bn"] - pl.b0, "from": pull_tx and pull_tx["from"], "to": pull_tx and pull_tx["to"], "sel": pull_tx and pull_tx["selector"],
                                       "by_launch_wallet": bool(pull_tx and pull_tx["from"] == p["launch_from"]), "after_sched": (pull["bn"] - sb["bn"]) if sb else None},
                     "outsiders": [{"rel": x["rel"], "eth": x["eth"] / 1e18, "from": x["from"], "to": x["to"]} for x in outs][:10],
                     "front": f1, "follow": f2})
    # ---- aggregate
    n = len(rows)
    blocks = sorted(r["b0"] for r in rows)
    span_days = (max(r["ts"] for r in rows) - min(r["ts"] for r in rows)) / 86400 if n > 1 else None
    fbs = [r["first_buy"] for r in rows if r["first_buy"]]
    rbs = [r["first_real_buy"] for r in rows if r["first_real_buy"]]
    sbs = [r["sched"] for r in rows if r["sched"]]
    pulls = [r for r in rows if r["pull"]]
    w_out = [r for r in rows if r["sched"] and r["outsiders"] and r["pull"]]
    wo_out = [r for r in rows if r["sched"] and not r["outsiders"] and r["pull"]]
    agg = {"count": n, "launches_per_day_window": round(n / WINDOW_DAYS, 2), "active_span_days": span_days and round(span_days, 3),
           "launches_per_day_active": round(n / span_days, 1) if span_days else None,
           "launch_gap_blocks_p10_50_90": pct([b - a for a, b in zip(blocks, blocks[1:])]),
           "deployers": collections.Counter(r["from"] for r in rows).most_common(5), "n_deployers": len(set(r["from"] for r in rows)),
           "first_buy": {"pools_with": len(fbs), "frac": round(len(fbs) / n, 3), "rel_p10_50_90": pct([x["rel"] for x in fbs]), "eth_p10_50_90": pct([x["eth"] for x in fbs]),
                         "via": collections.Counter(x["to"] for x in fbs).most_common(4), "from": collections.Counter(x["from"] for x in fbs).most_common(4),
                         "n_distinct_from": len(set(x["from"] for x in fbs))},
           "first_real_buy": {"pools_with": len(rbs), "frac": round(len(rbs) / n, 3), "rel_p10_50_90": pct([x["rel"] for x in rbs]), "eth_p10_50_90": pct([x["eth"] for x in rbs]),
                              "via": collections.Counter(x["to"] for x in rbs).most_common(4), "n_distinct_from": len(set(x["from"] for x in rbs)),
                              "from_launch_wallet": sum(1 for r in rows if r["first_real_buy"] and r["first_real_buy"]["from"] == r["from"])},
           "sched": {"pools_with": len(sbs), "rel_p10_50_90": pct([x["rel"] for x in sbs]), "eth_p10_50_90": pct([x["eth"] for x in sbs]),
                     "room_from_launch_eth_p10_50_90": pct([x["room_from_launch_eth"] for x in sbs]), "room_left_eth_p10_50_90": pct([x["room_left_eth"] for x in sbs]),
                     "minout_assumed": sum(1 for x in sbs if x["minout_assumed"])},
           "pull": {"pools_pulled_3000": len(pulls), "frac": round(len(pulls) / n, 3), "rel_p10_50_90": pct([r["pull"]["rel"] for r in pulls]),
                    "after_sched_p10_50_90": pct([r["pull"]["after_sched"] for r in pulls if r["pull"]["after_sched"] is not None]),
                    "by_launch_wallet": sum(1 for r in pulls if r["pull"]["by_launch_wallet"]), "via": collections.Counter((r["pull"]["to"], r["pull"]["sel"]) for r in pulls).most_common(3)},
           "outsiders": {"pools_with_outsider_before_sched": sum(1 for r in rows if r["sched"] and r["outsiders"]),
                         "eth_p10_50_90": pct([o["eth"] for r in rows if r["sched"] for o in r["outsiders"]]),
                         "pull_after_sched_with_outsider_p10_50_90": pct([r["pull"]["after_sched"] for r in w_out]),
                         "pull_after_sched_without_outsider_p10_50_90": pct([r["pull"]["after_sched"] for r in wo_out]),
                         "n_with": len(w_out), "n_without": len(wo_out),
                         "pools_without_sched_with_nonown_buy": sum(1 for r in rows if not r["sched"] and r["outsiders"])},
           "front": summarize(fr), "follow": summarize(fo),
           "front_sched_rel_p10_50_90": pct([r["front"]["sched_rel"] for r in rows if r["front"]]),
           "front_exit_S_p10_50_90": pct([r["front"]["S"] for r in rows if r["front"]])}
    return agg, rows


res = {}; allrows = []
for name, pids in groups.items():
    agg, rows = analyse(name, pids); res[name] = agg; allrows += rows
    print("=====", name)
    for a, b in agg.items(): print(" ", a, json.dumps(b, default=str)[:700])
json.dump(res, open(os.path.join(HERE, "results.json"), "w"), indent=1, default=str)
with open(os.path.join(HERE, "pools.jsonl"), "w") as f:
    for r in allrows: f.write(json.dumps(r, default=str) + "\n")
