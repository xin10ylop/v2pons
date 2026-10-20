"""Per-group summaries of rows.json -> stats.json (and a printout)."""
import sys, os, json, collections, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common15 import q, summarize, fmt_rule, WINDOW_DAYS, STAKE, USD_PER_ETH
D = json.load(open(os.path.join(HERE, "rows.json"))); R = D["rows"]
out = {}
for g, rows in R.items():
    n = len(rows); o = {"count": n}
    bs = sorted(r["b0"] for r in rows)
    o["launches_per_day_window"] = round(n / WINDOW_DAYS, 2)
    o["active_span_days"] = round((bs[-1] - bs[0]) * 0.1026 / 86400, 3)
    o["gap_blocks_p10_50_90"] = q([b - a for a, b in zip(bs, bs[1:])])
    o["first_ts"] = min(r["ts"] for r in rows); o["last_ts"] = max(r["ts"] for r in rows)
    o["launchers"] = collections.Counter(r["launch_from"] for r in rows).most_common(8)
    o["n_launchers"] = len(set(r["launch_from"] for r in rows))
    o["nonces"] = q([r["nonce"] for r in rows])
    o["values"] = collections.Counter(r["value"] for r in rows).most_common(8)
    o["start"] = collections.Counter(r["start"] for r in rows)
    o["etax"] = collections.Counter(tuple(r["etax"]) for r in rows).most_common(6)
    for k in ("first_any", "first_real", "sched"):
        xs = [r[k] for r in rows if r[k]]
        o[k] = {"pools": len(xs), "frac": round(len(xs) / n, 4), "rel": q([x["rel"] for x in xs]), "eth": q([x["eth"] for x in xs]),
                "to_sel": collections.Counter(f"{x['to']}:{x['sel']}" for x in xs).most_common(4),
                "from_top": collections.Counter(x["from"] for x in xs).most_common(5), "n_from": len(set(x["from"] for x in xs)),
                "from_nonce": q([x["nonce"] for x in xs if x["nonce"] is not None])}
    pl = [r["pull"] for r in rows if r["pull"]]
    o["pull"] = {"pulled": len(pl), "frac": round(len(pl) / n, 4), "rel": q([x["rel"] for x in pl]), "from_sched": q([x["from_sched"] for x in pl if x["from_sched"] is not None]),
                 "from_first_real": q([x["from_first_real"] for x in pl if x["from_first_real"] is not None]),
                 "by_launcher": sum(1 for x in pl if x["by_launcher"]), "full": sum(1 for x in pl if x["full"]),
                 "who": collections.Counter(f"{x['to']}:{x['sel']}" for x in pl).most_common(3)}
    # trap test
    w = [r for r in rows if r["sched"] and r["outsider_real"]]; wo = [r for r in rows if r["sched"] and not r["outsider_real"]]
    o["trap"] = {"pools_with_real_outsider_before_sched": len(w), "pools_without": len(wo),
                 "outsider_sizes": q([x[1] for r in w for x in r["outsider_real"]]),
                 "with_pulled": sum(1 for r in w if r["pull"]), "with_pull_from_outsider": q([r["pull"]["from_first_outsider_real"] for r in w if r["pull"]]),
                 "with_pull_from_launch": q([r["pull"]["rel"] for r in w if r["pull"]]),
                 "without_pulled": sum(1 for r in wo if r["pull"]), "without_pull_from_launch": q([r["pull"]["rel"] for r in wo if r["pull"]]),
                 "without_pull_from_sched": q([r["pull"]["from_sched"] for r in wo if r["pull"] and r["pull"]["from_sched"] is not None]),
                 "any_outsider_pools": sum(1 for r in rows if r["sched"] and r["outsiders"])}
    o["front"] = summarize([r["front"] for r in rows])
    o["front_with_sched"] = summarize([r["front"] for r in rows if r["front"].get("trig") is not None and r["front"]["trig"] <= 19])
    o["front_without_sched"] = summarize([r["front"] for r in rows if r["front"].get("ret") is not None and (r["front"].get("trig") is None or r["front"]["trig"] > 19)])
    if any(r.get("front_nohook") for r in rows):
        o["front_nohook"] = summarize([r["front_nohook"] for r in rows if r.get("front_nohook")])
    o["follow"] = summarize([r["follow"] for r in rows])
    if any(r.get("follow_nohook") for r in rows):
        o["follow_nohook"] = summarize([r["follow_nohook"] for r in rows if r.get("follow_nohook")])
    caps = [r["cap"] for r in rows if r["cap"]]
    o["cap"] = {"pools": len(caps), "src": collections.Counter(c["minout_source"] for c in caps).most_common(3),
                "cap_from_launch": q([c["cap_from_launch"] for c in caps if c["cap_from_launch"] not in (None, float("inf"))], nd=5),
                "inf": sum(1 for c in caps if c["cap_from_launch"] == float("inf")),
                "room_left": q([c["room_left_at_chain_state"] for c in caps if c["room_left_at_chain_state"] not in (None, float("inf"))], nd=5),
                "minout_over_quote": q([c["minout_over_quote"] for c in caps if c["minout_over_quote"] is not None], nd=5),
                "actual_over_launch_quote": q([c["actual_over_launch_quote"] for c in caps if c["actual_over_launch_quote"] is not None], nd=5)}
    out[g] = o
    print("=" * 100); print(g, "count", n, "per day", o["launches_per_day_window"], "span d", o["active_span_days"], "launchers", o["n_launchers"], o["launchers"][:4])
    for k in ("first_any", "first_real", "sched"): print("  ", k, json.dumps(o[k]))
    print("   pull", json.dumps(o["pull"])); print("   trap", json.dumps(o["trap"]))
    print("   FRONT", fmt_rule(o["front"]), o["front"]["exits"] if o["front"].get("exits") else "")
    print("     with sched by +19:", fmt_rule(o["front_with_sched"])); print("     without:", fmt_rule(o["front_without_sched"]))
    if "front_nohook" in o: print("     front, hook tax 0:", fmt_rule(o["front_nohook"]))
    print("   FOLLOW", fmt_rule(o["follow"]), o["follow"].get("exits"))
    if "follow_nohook" in o: print("     follow, hook tax 0:", fmt_rule(o["follow_nohook"]))
    print("   cap", json.dumps(o["cap"], default=str))
json.dump(out, open(os.path.join(HERE, "stats.json"), "w"), indent=1, default=str)
