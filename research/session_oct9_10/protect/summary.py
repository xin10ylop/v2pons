"""Summaries over measure.json: reaction lags (first non-crowd buy per launch, all non-crowd buys), by day / hour, the engine's
triggers, margins of the current exit (buy lands trigger + 1 or + 2, sell lands buy + 3). Writes summary.json."""
import json, collections, statistics as st
HERE = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/protect/"
M = json.load(open(HERE + "measure.json"))
R = M["noncrowd_buys"]; T = M["engine_triggers"]
react = [r for r in R if r["lag_blocks"] is not None and r["lag_blocks"] <= 60]
def chance0(r): return r["chance_same_family_clean"] and r["chance_same_family_clean"].startswith("0/")
S = {}
S["noncrowd_real_buys"] = {"total": len(R), "us": sum(1 for r in R if r["who"] == "us"), "outsider": sum(1 for r in R if r["who"] == "outsider"),
                           "launches_with_one": len({r["pid"] for r in R}),
                           "pulled_within_60_blocks": len(react), "of_which_first_noncrowd_on_launch": sum(1 for r in react if r["first_noncrowd_on_launch"]),
                           "not_pulled_within_60": [(r["time_utc"], r["who"], r["family"], r["offset"], r["size_eth"], r["lag_blocks"]) for r in R if r not in react]}
S["reaction_lags_blocks_all"] = sorted(r["lag_blocks"] for r in react)
S["reaction_lags_ms_all"] = sorted(r["lag_ms"] for r in react)
S["min_lag"] = min(react, key=lambda r: r["lag_blocks"])
for d in ("Oct 8", "Oct 9"):
    v = [r["lag_blocks"] for r in react if r["day"] == d]
    S[f"lags_{d}"] = {"n": len(v), "lags": sorted(v), "median": st.median(v) if v else None, "min": min(v) if v else None,
                      "us": sorted(r["lag_blocks"] for r in react if r["day"] == d and r["who"] == "us"),
                      "outsider": sorted(r["lag_blocks"] for r in react if r["day"] == d and r["who"] == "outsider")}
byh = collections.defaultdict(list)
for r in react: byh[r["time_utc"][:8].replace("10-0", "Oct ") + "h"].append((r["lag_blocks"], r["who"]))
S["lags_by_hour"] = {k: sorted(v) for k, v in sorted(byh.items())}
# idle-phase (no crowd swap in the 20 blocks before) vs crowd-phase reactions
S["lags_idle_phase"] = sorted(r["lag_blocks"] for r in react if r["crowd_swaps_prev20"] == 0)
S["lags_crowd_phase"] = sorted(r["lag_blocks"] for r in react if r["crowd_swaps_prev20"] > 0)
# engine triggers
trg = [e for e in T if e.get("trigger")]
S["engine"] = {"orig_launches": len(T), "with_trigger": len(trg), "no_trigger": collections.Counter(e["why_no_trigger"].split(" at ")[0] for e in T if not e.get("trigger")),
               "trigger_family": dict(collections.Counter(e["trigger"]["who"] for e in trg)),
               "trigger_not_crowd": sum(1 for e in trg if e["trigger"]["who"] in ("outsider", "?")),
               "outsider_real_buy_before_first_crowd_buy_on_any_orig": None}
nous = [e for e in trg if not e["traded_by_us"]]
pt = sorted(e["pull_after_trigger"] for e in nous if e["pull_after_trigger"] is not None)
S["engine"]["pull_after_trigger_without_us"] = {"n": len(pt), "min": pt[0], "lowest10": pt[:10], "median": st.median(pt),
                                               "pulled_at_or_before_sell_T+4_or_T+5": sum(1 for x in pt if x <= 5), "within_T+8": sum(1 for x in pt if x <= 8)}
S["engine"]["with_us"] = [(e["launch_utc"], e["pid"], e["family"], e["trigger"]["who"], e["trigger"]["wallet"][:10], e["trigger"]["offset"], e.get("actual_buy_after_trigger"), e["pull_after_trigger"]) for e in trg if e["traded_by_us"]]
# margins of the current exit on every follow trade (live) and on every reaction: sell lands buy + 3
us_follow = [r for r in R if r["who"] == "us" and r["offset"] > 20]
S["margins_current_exit_on_our_follow_buys"] = sorted([(r["lag_blocks"] - 3, r["time_utc"], r["pid"], r["lag_blocks"]) for r in us_follow if r["lag_blocks"] is not None])
S["closest_calls_pull_within_3_of_sell"] = [(r["time_utc"], r["who"], r["pid"], "pull = buy +%d, sell lands buy +3: margin %d blocks (%d ms)" % (r["lag_blocks"], r["lag_blocks"] - 3, round((r["lag_blocks"] - 3) * r["ms_per_block"]))) for r in sorted(react, key=lambda r: r["lag_blocks"]) if r["lag_blocks"] - 3 <= 3]
S["ms_per_block"] = {"min": min(r["ms_per_block"] for r in R), "max": max(r["ms_per_block"] for r in R)}
json.dump(S, open(HERE + "summary.json", "w"), indent=1, default=str)
print(json.dumps(S, indent=1, default=str))
