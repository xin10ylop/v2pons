"""per-family statistics from rows.json -> stats.json"""
import sys, os, json, collections, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common11 import *  # noqa
rows = json.load(open(os.path.join(HERE, "rows.json")))


def fam_stats(R):
    n = len(R)
    out = {"count": n}
    tsl = sorted(r["ts"] for r in R)
    out["launches_per_day_window"] = round(n / WINDOW_DAYS, 2)
    span = (tsl[-1] - tsl[0]) / 86400 if n > 1 else 0
    out["active_span_days"] = round(span, 2)
    out["launch_gap_blocks_p10_50_90"] = q([b - a for a, b in zip(sorted(r["b0"] for r in R), sorted(r["b0"] for r in R)[1:])])
    out["deployers"] = collections.Counter(r["launch_from"] for r in R).most_common(6)
    out["launch_values"] = collections.Counter(r["value"] for r in R).most_common(6)
    out["launch_nonce_p10_50_90"] = q([r["nonce"] for r in R])
    out["buy_in_launch_tx_pools"] = sum(1 for r in R if r["buy_in_launch_tx"])
    out["buy_in_launch_tx_eth_p10_50_90"] = q([sum(r["buy_in_launch_tx"]) for r in R if r["buy_in_launch_tx"]])
    fa = [r["first_any"] for r in R if r["first_any"]]
    out["first_any_buy"] = {"pools": len(fa), "rel_p10_50_90": q([x["rel"] for x in fa]), "eth_p10_50_90": q([x["eth"] for x in fa], nd=9),
                            "from_top": collections.Counter(x["from"] for x in fa).most_common(4), "to_top": collections.Counter(x["to"] for x in fa).most_common(4)}
    fr = [r["first_real"] for r in R if r["first_real"]]
    out["first_real_buy"] = {"pools": len(fr), "frac": round(len(fr) / n, 3), "rel_p10_50_90": q([x["rel"] for x in fr]), "eth_p10_50_90": q([x["eth"] for x in fr]),
                             "to_top": collections.Counter(f"{x['to']}:{x['sel']}" for x in fr).most_common(5),
                             "from_top": collections.Counter(x["from"] for x in fr).most_common(5), "n_distinct_from": len(set(x["from"] for x in fr)),
                             "from_launch_wallet": sum(1 for r in R if r["first_real"] and r["first_real"]["from"] == r["launch_from"]),
                             "nonce_p10_50_90": q([x["nonce"] for x in fr if x["nonce"] is not None])}
    out["real_buys_per_pool_p10_50_90"] = q([r["n_real_buys"] for r in R])
    out["sells_per_pool_p10_50_90"] = q([r["n_sells"] for r in R])
    pl = [r["pull"] for r in R if r["pull"]]
    out["pull"] = {"pools_pulled_3000": len(pl), "frac": round(len(pl) / n, 3), "rel_p10_50_90": q([x["rel"] for x in pl]),
                   "from_sched_p10_50_90": q([x["from_sched"] for x in pl if x["from_sched"] is not None]),
                   "from_first_real_p10_50_90": q([x["from_first_real"] for x in pl if x["from_first_real"] is not None]),
                   "by_launch_wallet": sum(1 for x in pl if x["by_launcher"]), "full": sum(1 for x in pl if x["full"]),
                   "via": collections.Counter(f"{x['to']}:{x['sel']}" for x in pl).most_common(4), "who": collections.Counter(x["from"] for x in pl).most_common(4)}
    # trap test: pools with a real outsider buy before the scheduled buy vs without
    w = [r for r in R if r["sched"] and r["outsider_real"]]; wo = [r for r in R if r["sched"] and not r["outsider_real"]]
    out["outsiders"] = {"pools_with_any_buy_before_sched": sum(1 for r in R if r["sched"] and r["outsiders"]),
                        "pools_with_real_outsider_before_sched": len(w),
                        "outsider_real_eth_p10_50_90": q([o[1] for r in w for o in r["outsider_real"]]),
                        "pulled_with": sum(1 for r in w if r["pull"]), "pulled_without": sum(1 for r in wo if r["pull"]),
                        "pull_after_sched_with_p10_50_90": q([r["pull"]["from_sched"] for r in w if r["pull"]]),
                        "pull_after_sched_without_p10_50_90": q([r["pull"]["from_sched"] for r in wo if r["pull"]]),
                        "pull_after_first_outsider_p10_50_90": q([r["pull"]["from_first_outsider_real"] for r in w if r["pull"]]),
                        "n_with": len(w), "n_without": len(wo)}
    caps = [r["cap"] for r in R if r["cap"]]
    out["capacity"] = {"n": len(caps), "minout_source": collections.Counter(c["minout_source"] for c in caps).most_common(3),
                       "cap_from_launch_eth_p10_50_90": q([c["cap_from_launch"] for c in caps], nd=5),
                       "room_left_at_chain_state_p10_50_90": q([c["room_left_at_chain_state"] for c in caps], nd=5),
                       "sched_eth_p10_50_90": q([c["eth"] for c in caps], nd=5)}
    out["front"] = summarize([r["front"] for r in R])
    out["front"]["trig_rel_counts"] = collections.Counter(r["front"].get("trig") for r in R).most_common(8)
    out["follow"] = summarize([r["follow"] for r in R if r["follow"]])
    out["follow"]["pools_without_real_buy"] = sum(1 for r in R if not r["follow"])
    return out


if __name__ == "__main__":
    S = {g: fam_stats(R) for g, R in rows.items()}
    json.dump(S, open(os.path.join(HERE, "stats.json"), "w"), indent=1, default=str)
    for g, s in S.items():
        print("=" * 90); print(g)
        for k, v in s.items(): print("  ", k, json.dumps(v, default=str)[:400])
