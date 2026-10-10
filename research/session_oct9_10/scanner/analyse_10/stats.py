"""per-family statistics from rows.json -> stats.json"""
import sys, os, json, collections, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common10 import *  # noqa
rows = json.load(open(os.path.join(HERE, "rows.json")))
out = {}
for g, R in rows.items():
    n = len(R); b = sorted(r["b0"] for r in R)
    span_days = (b[-1] - b[0]) * 0.1026 / 86400 if n > 1 else None
    gaps = [y - x for x, y in zip(b, b[1:])]
    s = {"count": n, "launches_per_day_window": round(n / WINDOW_DAYS, 2), "active_span_h": round(span_days * 24, 2) if span_days else None,
         "launch_gap_blocks_p10_50_90": q(gaps), "launch_from": collections.Counter(r["launch_from"] for r in R).most_common(4),
         "n_deployers": len(set(r["launch_from"] for r in R)), "values": collections.Counter(r["value"] for r in R).most_common(4),
         "start": dict(collections.Counter(r["start"] for r in R)), "tax_ppm": dict(collections.Counter(r["tax"] for r in R))}
    fa = [r["first_any"] for r in R if r["first_any"]]
    s["first_any"] = {"pools": len(fa), "rel_p10_50_90": q([x["rel"] for x in fa]), "eth_p10_50_90": q([x["eth"] for x in fa], nd=7),
                      "to": collections.Counter(x["to"] for x in fa).most_common(4), "from": collections.Counter(x["from"] for x in fa).most_common(4)}
    fr = [r["first_real"] for r in R if r["first_real"]]
    s["first_real"] = {"pools": len(fr), "frac": round(len(fr) / n, 3), "rel_p10_50_90": q([x["rel"] for x in fr]), "eth_p10_50_90": q([x["eth"] for x in fr], nd=6),
                       "to_sel": collections.Counter(f"{x['to']}:{x['sel']}" for x in fr).most_common(5),
                       "from": collections.Counter(x["from"] for x in fr).most_common(5), "n_distinct_from": len(set(x["from"] for x in fr)),
                       "nonce_p10_50_90": q([x["nonce"] for x in fr if x["nonce"] is not None]), "unknown_tx": sum(1 for x in fr if x["to"] is None)}
    sb = [r for r in R if r["sched"]]
    s["sched"] = {"pools": len(sb), "rel_p10_50_90": q([r["sched"]["rel"] for r in sb]), "eth_p10_50_90": q([r["sched"]["eth"] for r in sb], nd=6)}
    pl = [r for r in R if r["pull"]]
    s["pull"] = {"pulled": len(pl), "frac": round(len(pl) / n, 3), "rel_p10_50_90": q([r["pull"]["rel"] for r in pl]),
                 "from_sched_p10_50_90": q([r["pull"]["from_sched"] for r in pl if r["pull"]["from_sched"] is not None]),
                 "by_launcher": sum(1 for r in pl if r["pull"]["by_launcher"]), "puller_to_sel": collections.Counter(f"{r['pull']['to']}:{r['pull']['sel']}" for r in pl).most_common(3)}
    # outsiders and the trap test
    wo = [r for r in sb if r["outsider_real"]]; woo = [r for r in sb if not r["outsider_real"]]
    s["outsiders"] = {"pools_with_any_before_sched": sum(1 for r in sb if r["outsiders"]), "pools_with_real_before_sched": len(wo),
                      "eth_real_p10_50_90": q([o[1] for r in wo for o in r["outsider_real"]], nd=6),
                      "any_eth_p10_50_90": q([o[1] for r in sb for o in r["outsiders"]], nd=7),
                      "who": collections.Counter((o[2], o[3]) for r in sb for o in r["outsiders"]).most_common(5),
                      "pull_from_sched_with_real_outsider": q([r["pull"]["from_sched"] for r in wo if r["pull"]]),
                      "pull_from_sched_without": q([r["pull"]["from_sched"] for r in woo if r["pull"]]),
                      "pulled_with": sum(1 for r in wo if r["pull"]), "pulled_without": sum(1 for r in woo if r["pull"]),
                      "pull_from_first_real_outsider": q([r["pull"]["from_first_outsider_real"] for r in wo if r["pull"]])}
    s["front"] = summarize([r["front"] for r in R])
    s["front_trig_rel_p10_50_90"] = q([r["front"].get("trig") for r in R])
    s["follow"] = summarize([r["follow"] for r in R if r["follow"]])
    s["follow_next_rel_minus_first"] = q([r["follow"]["next"] - r["first_real"]["rel"] for r in R if r["follow"] and r["follow"].get("next") is not None])
    caps = [r["cap"] for r in R if r["cap"]]
    s["cap"] = {"n": len(caps), "src": collections.Counter(c["minout_source"] for c in caps).most_common(3),
                "cap_from_launch_p10_50_90": q([c["cap_from_launch"] for c in caps], nd=5), "room_left_p10_50_90": q([c["room_left_at_chain_state"] for c in caps], nd=5)}
    out[g] = s
json.dump(out, open(os.path.join(HERE, "stats.json"), "w"), indent=1, default=str)
for g, s in out.items():
    if g.startswith("control"): continue
    print("=" * 20, g); print(json.dumps(s, indent=1, default=str))
