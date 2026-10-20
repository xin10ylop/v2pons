"""descriptive statistics per group from rows.json (+ the census): launcher, first buys, pulls, outsiders + trap test, capacity"""
import sys, os, json, collections, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common7 import *  # noqa
rows = json.load(open(os.path.join(HERE, "rows.json")))
P = load_pools(); T = load_txs()
res = {}
for g, R in rows.items():
    n = len(R); o = {"n": n}
    lf = collections.Counter(r["from"] for r in R)
    o["launches_per_day"] = round(n / WINDOW_DAYS, 2)
    bl = sorted(r["b0"] for r in R)
    o["span_blocks"] = [bl[0], bl[-1]]; o["active_hours"] = round((bl[-1] - bl[0]) * 0.1026 / 3600, 2)
    o["gap_blocks_p10_50_90"] = q([b - a for a, b in zip(bl, bl[1:])])
    o["launch_from_top"] = lf.most_common(3); o["n_launch_wallets"] = len(lf)
    o["launch_nonce_p10_50_90"] = q([r["nonce"] for r in R])
    o["start"] = collections.Counter(r["start"] for r in R)
    ve = [r["val_err"] for r in R if r["val_err"] is not None]
    o["validate_first_swap_rel_err_max"] = max(ve) if ve else None; o["validate_n"] = len(ve)
    for key in ("fb", "fr", "sb"):
        xs = [r[key] for r in R if r[key]]
        o[key] = {"pools": len(xs), "frac": round(len(xs) / n, 4), "off_p10_50_90": q([x["off"] for x in xs]), "eth_p10_50_90": q([x["eth"] for x in xs], nd=7),
                  "to_top": collections.Counter(x["to"] for x in xs).most_common(4), "from_top": collections.Counter(x["from"] for x in xs).most_common(4),
                  "n_from": len(set(x["from"] for x in xs)), "fresh_nonce_le2": sum(1 for x in xs if x["nonce"] is not None and x["nonce"] <= 2),
                  "sel_top": collections.Counter(x.get("sel") for x in xs).most_common(3)} if xs else {"pools": 0}
    pl = [r for r in R if r["pull"] is not None]
    o["pull"] = {"pulled": len(pl), "frac": round(len(pl) / n, 4), "off_launch_p10_50_90": q([r["pull"] for r in pl]),
                 "off_sched_p10_50_90": q([r["pull"] - r["sb"]["off"] for r in pl if r["sb"]]),
                 "by_launch_wallet": sum(1 for r in pl if r["pull_from"] == r["from"]), "pull_from_top": collections.Counter(r["pull_from"] for r in pl).most_common(3),
                 "pull_to_top": collections.Counter(r["pull_to"] for r in pl).most_common(3),
                 "pulled_before_sched": sum(1 for r in pl if r["sb"] and r["pull"] <= r["sb"]["off"]), "pulled_no_sched": sum(1 for r in pl if not r["sb"])}
    # outsiders before the scheduled buy + trap test
    wo = [r for r in R if r["outsiders"]]
    o["outsiders"] = {"pools": len(wo), "frac": round(len(wo) / n, 4), "eth_p10_50_90": q([x[1] for r in wo for x in r["outsiders"]], nd=7),
                      "off_p10_50_90": q([x[0] for r in wo for x in r["outsiders"]]),
                      "real_ge_0.0002_pools": sum(1 for r in wo if any(x[1] >= 0.0002 for x in r["outsiders"])),
                      "to_top": collections.Counter(x[2] for r in wo for x in r["outsiders"]).most_common(4),
                      "from_top": collections.Counter(x[3] for r in wo for x in r["outsiders"]).most_common(4),
                      "dust_bot_pools": sum(1 for r in R if r["dust_before"])}
    def delay(rs):
        d = [r["pull"] - r["sb"]["off"] for r in rs if r["sb"] and r["pull"] is not None]
        return {"pools": len(rs), "with_sched": sum(1 for r in rs if r["sb"]), "pulled": sum(1 for r in rs if r["pull"] is not None),
                "pull_minus_sched_p10_50_90": q(d), "pull_le_sched_plus4": sum(1 for x in d if x <= 4)}
    real_out = [r for r in R if any(x[1] >= 0.0001 for x in r["outsiders"])]
    no_out = [r for r in R if not any(x[1] >= 0.0001 for x in r["outsiders"])]
    o["trap_test"] = {"with_outsider_ge_0.0001": delay(real_out), "without": delay(no_out)}
    # capacity
    cp = [r["cap"] for r in R if r.get("cap")]
    if cp:
        o["capacity"] = {"pools": len(cp), "real_minout": sum(1 for c in cp if c["real_minout"]), "minout_vs_quote_p10_50_90": q([c["minout_vs_quote"] for c in cp], nd=5),
                         "room_from_launch_p10_50_90": q([c["room_from_launch"] for c in cp if c["room_from_launch"] not in (None, float("inf"))], nd=5),
                         "room_after_prebuys_p10_50_90": q([c["room_after_preburys"] for c in cp if c["room_after_preburys"] not in (None, float("inf"))], nd=5),
                         "eth_ahead_actual_p10_50_90": q([c["eth_ahead_actual"] for c in cp], nd=6),
                         "room_lt_stake": sum(1 for c in cp if c["room_after_preburys"] is not None and c["room_after_preburys"] < 0.0058),
                         "sched_eth_p10_50_90": q([c["sched_eth"] for c in cp], nd=5)}
    o["front"] = summarize([r["front"] for r in R]); o["front"]["late"] = sum(1 for r in R if r["front"]["exit"] == "late")
    o["front"]["sell_off_p10_50_90"] = q([r["front"].get("S") for r in R if r["front"].get("S") is not None])
    o["front"]["bot_dropped_pools"] = sum(1 for r in R if r["front"].get("dropped"))
    o["follow"] = summarize([r["follow"] for r in R if r["follow"]])
    o["follow"]["no_trigger"] = sum(1 for r in R if not r["follow"])
    res[g] = o
    print("=" * 20, g); print(json.dumps(o, default=str)[:3500])
json.dump(res, open(os.path.join(HERE, "stats.json"), "w"), indent=1, default=str)
