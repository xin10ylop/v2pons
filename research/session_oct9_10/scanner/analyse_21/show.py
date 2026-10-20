import json, sys
S = json.load(open("stats.json"))
gs = [g for g in S if g != "controls"]
g = gs[int(sys.argv[1])]; r = S[g]
print(g)
for k in ("count", "launches_per_day", "span_hours", "n_deployers", "values", "fees", "nonce_range", "launch_ranges", "start", "buy_in_launch_tx", "later_adds_pools"):
    print("  ", k, json.dumps(r[k])[:300])
for k in ("first_buy_any", "first_buy_real", "swaps_non_launch", "pull", "trap"):
    v = dict(r[k]); v.pop("list", None); print("  ", k, json.dumps(v)[:700])
print("   first_buy_real list", r["first_buy_real"]["list"][:8])
for k in ("front", "front_hold3000", "follow"):
    s = r[k]; print("  ", k, {kk: s.get(kk) for kk in ("n", "mean", "median", "win", "pulled_first", "pulled_before_buy", "exits", "usd_trade", "usd_day", "trades_day", "min", "max")})
print("   front_sched_by_20", r["front_sched_by_20"], "front_fees", r["front_fees"], "adds_in_window", r["front_adds_in_window"])
print("   front_rows", [(z["pid"][:10], z["sched"], z["S"], z["exit"], z["ret"] and round(z["ret"], 4)) for z in r["front_rows"]][:6])
print("   follow_rows", [(z["pid"][:10], z["trig"], round(z["trig_eth"], 5), z["next"], z["S"], z["exit"], z["ret"] and round(z["ret"], 4)) for z in r["follow_rows"]][:6])
print("   capacity", r["capacity"]["n"], r["capacity"]["cap_eth_p10_50_90"], r["capacity"]["src"], [(c["Y"], c["cap_eth"], round(c["minout_over_quote"] or 0, 4)) for c in r["capacity"]["rows"][:6]])
