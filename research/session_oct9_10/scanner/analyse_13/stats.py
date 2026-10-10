"""aggregate rows.json per group -> stats.json"""
import sys, os, json, collections, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common13 import q, summarize, fmt_rule, WINDOW_DAYS, STAKE, USD_PER_ETH

rows = json.load(open(os.path.join(HERE, "rows.json")))
out = {}
for g, rs in rows.items():
    n = len(rs)
    b0s = sorted(r["b0"] for r in rs)
    span_days = (b0s[-1] - b0s[0]) * 0.1026 / 86400 if n > 1 else 0
    gaps = [b - a for a, b in zip(b0s, b0s[1:])]
    o = {"count": n, "launches_per_day_window": round(n / WINDOW_DAYS, 2), "active_span_days": round(span_days, 3),
         "launches_per_day_active": round(n / span_days, 1) if span_days > 0 else None, "gap_blocks_p10_50_90": q(gaps),
         "deployers": collections.Counter(r["launch_from"] for r in rs).most_common(5), "n_deployers": len(set(r["launch_from"] for r in rs)),
         "launch_nonce_p10_50_90": q([r["nonce"] for r in rs]), "values": collections.Counter(r["value"] for r in rs).most_common(4),
         "buy_in_launch_tx": collections.Counter(tuple(r["buy_in_launch_tx"]) for r in rs).most_common(4),
         "start": collections.Counter(r["start"] for r in rs).most_common(), "n_ranges_launch": collections.Counter(r["n_ranges_launch"] for r in rs).most_common(),
         "L0": collections.Counter(r["L0"] for r in rs).most_common(3)}
    fa = [r["first_any"] for r in rs if r["first_any"]]
    o["first_any"] = {"pools_with": len(fa), "rel": q([x["rel"] for x in fa]), "eth": q([x["eth"] for x in fa], nd=9),
                      "to": collections.Counter(x["to"] for x in fa).most_common(4), "from": collections.Counter(x["from"] for x in fa).most_common(4)}
    fr = [r["first_real"] for r in rs if r["first_real"]]
    o["first_real"] = {"pools_with": len(fr), "frac": round(len(fr) / n, 3), "rel": q([x["rel"] for x in fr]), "eth": q([x["eth"] for x in fr]),
                       "to": collections.Counter(x["to"] for x in fr).most_common(4), "n_from": len(set(x["from"] for x in fr)),
                       "from_top": collections.Counter(x["from"] for x in fr).most_common(4), "nonce": q([x["nonce"] for x in fr if x["nonce"] is not None]),
                       "from_launch_wallet": sum(1 for r in rs if r["first_real"] and r["first_real"]["from"] == r["launch_from"])}
    sb = [r["sched"] for r in rs if r["sched"]]
    o["sched"] = {"pools_with": len(sb), "frac": round(len(sb) / n, 3), "rel": q([x["rel"] for x in sb]), "eth": q([x["eth"] for x in sb]),
                  "to": collections.Counter(x["to"] for x in sb).most_common(3), "sel": collections.Counter(x["sel"] for x in sb).most_common(3),
                  "n_from": len(set(x["from"] for x in sb)), "from_top": collections.Counter(x["from"] for x in sb).most_common(3),
                  "nonce": q([x["nonce"] for x in sb if x["nonce"] is not None]), "eth_counts": collections.Counter(round(x["eth"], 6) for x in sb).most_common(8)}
    caps = [r["cap"] for r in rs if r["cap"]]
    o["capacity"] = {"minout_source": collections.Counter(c["minout_source"] for c in caps).most_common(),
                     "minout_over_quote": q([c["minout_over_quote"] for c in caps]),
                     "cap_from_launch_eth": q([c["cap_from_launch"] for c in caps if c["cap_from_launch"] not in (None, float("inf"))]),
                     "room_left_eth": q([c["room_left_at_chain_state"] for c in caps if c["room_left_at_chain_state"] not in (None, float("inf"))]),
                     "actual_over_launch_quote": q([c["actual_over_launch_quote"] for c in caps if c["actual_over_launch_quote"]]),
                     "pred_vs_actual": q([c["pred_vs_actual"] for c in caps if c["pred_vs_actual"]], nd=8)}
    pl = [r["pull"] for r in rs if r["pull"]]
    o["pull"] = {"pulled_3000": len(pl), "frac": round(len(pl) / n, 3), "rel": q([x["rel"] for x in pl]), "from_sched": q([x["from_sched"] for x in pl if x["from_sched"] is not None]),
                 "from_first_real": q([x["from_first_real"] for x in pl if x["from_first_real"] is not None]),
                 "by_launcher": sum(1 for x in pl if x["by_launcher"]), "via": collections.Counter(f"{x['to']}:{x['sel']}" for x in pl).most_common(3)}
    wo = [r for r in rs if r["outsider_real"]]
    wo_any = [r for r in rs if r["outsiders"] and any(not o_[4] for o_ in r["outsiders"])]
    o["outsiders"] = {"pools_with_real_outsider_before_sched": len(wo), "pools_with_nonnoise_outsider_any_size": len(wo_any),
                      "outsider_real_eth": q([x[1] for r in wo for x in r["outsider_real"]]),
                      "outsider_real_rel": q([x[0] for r in wo for x in r["outsider_real"]]),
                      "pull_from_sched_with": q([r["pull"]["from_sched"] for r in wo if r["pull"] and r["pull"]["from_sched"] is not None]),
                      "pull_from_sched_without": q([r["pull"]["from_sched"] for r in rs if not r["outsider_real"] and r["pull"] and r["pull"]["from_sched"] is not None]),
                      "pull_rel_with": q([r["pull"]["rel"] for r in wo if r["pull"]]), "pull_rel_without": q([r["pull"]["rel"] for r in rs if not r["outsider_real"] and r["pull"]]),
                      "pulled_frac_with": round(sum(1 for r in wo if r["pull"]) / len(wo), 3) if wo else None,
                      "pulled_frac_without": round(sum(1 for r in rs if not r["outsider_real"] and r["pull"]) / max(1, sum(1 for r in rs if not r["outsider_real"])), 3),
                      "pull_from_first_outsider": q([r["pull"]["from_first_outsider_real"] for r in wo if r["pull"] and r["pull"]["from_first_outsider_real"] is not None]),
                      "anysize_n_with": len(wo_any), "anysize_outsider_eth": q([o_[1] for r in wo_any for o_ in r["outsiders"] if not o_[4]], nd=8),
                      "anysize_outsider_from": collections.Counter(o_[3] for r in wo_any for o_ in r["outsiders"] if not o_[4]).most_common(4),
                      "anysize_pull_from_sched_with": q([r["pull"]["from_sched"] for r in wo_any if r["pull"] and r["pull"]["from_sched"] is not None]),
                      "anysize_pull_from_sched_without": q([r["pull"]["from_sched"] for r in rs if r not in wo_any and r["pull"] and r["pull"]["from_sched"] is not None]),
                      "anysize_pulled_frac_with": round(sum(1 for r in wo_any if r["pull"]) / len(wo_any), 3) if wo_any else None,
                      "anysize_pulled_frac_without": round(sum(1 for r in rs if r not in wo_any and r["pull"]) / max(1, n - len(wo_any)), 3)}
    for rule in ("front", "front_wait", "follow"):
        rr = [r[rule] for r in rs if r.get(rule)]
        s = summarize(rr)
        if rule.startswith("front"):
            s["trig_rel"] = q([x.get("trig") for x in rr if x.get("trig") is not None]); s["S_rel"] = q([x.get("S") for x in rr if x.get("S") is not None])
        else:
            s["trig_rel"] = q([x.get("trig_rel") for x in rr]); s["next_rel"] = q([x.get("next") for x in rr if x.get("next") is not None])
            s["S_rel"] = q([x.get("S") for x in rr if x.get("S") is not None])
        s["dropped_pools"] = sum(1 for x in rr if x.get("dropped"))
        o[rule] = s
    o["launcher_sells"] = {"pools": sum(1 for r in rs if r["launcher_sells"]), "list": [[r["pid"][:10]] + r["launcher_sells"] for r in rs if r["launcher_sells"]][:10]}
    o["relay_in"] = sum(1 for r in rs if r["relay_in"])
    vals = [v for r in rs for v in r["val"]]
    o["pricer_check_buy_out_vs_actual"] = q(vals, nd=9) if vals else None
    out[g] = o
    print("=" * 110); print(g, n, "launches/day", o["launches_per_day_window"], "active", o["active_span_days"], "d")
    for k in ("first_any", "first_real", "sched", "capacity", "pull", "outsiders", "launcher_sells"):
        print(f"  {k}: {json.dumps(o[k], default=str)[:700]}")
    for rule in ("front", "front_wait", "follow"):
        print(f"  {rule}: {fmt_rule(o[rule])} trig {o[rule].get('trig_rel')} S {o[rule].get('S_rel')} exits {o[rule].get('exits')} p10/50/90 {o[rule].get('p10_50_90')}")
json.dump(out, open(os.path.join(HERE, "stats.json"), "w"), indent=1, default=str)
