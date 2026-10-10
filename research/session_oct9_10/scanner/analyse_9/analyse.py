import sys, json, collections, statistics as st
sys.path.insert(0, "."); from common9 import *
FK = json.load(open("families_in.json"))
F = load_families(); P = load_pools(); T = load_txs(); M = load_blocks_meta()
pids = set(pid for k in FK for pid in F[k]["pids"])
E = load_events(pids)
KNOWN_DUST = {DUST}
res = {}
for k in FK:
    f = F[k]; pools = [Pool(P[pid], E.get(pid), T, M) for pid in f["pids"]]
    r = {"key": k, "count": f["count"], "known": f["known"]}
    bl = [pl.b0 for pl in pools]
    r["launches_per_day"] = round(len(pools) / WINDOW_DAYS, 2)
    r["launch_span_blocks"] = [min(bl), max(bl), max(bl) - min(bl)]
    r["launch_gaps_blocks"] = sorted(b - a for a, b in zip(bl, bl[1:]))
    lf = collections.Counter(pl.p["launch_from"] for pl in pools)
    r["launcher"] = {"to": f["launch_to"], "selector": f["selector"], "calldata_len": f["calldata_len"], "values_eth": f["values_eth"], "senders": lf.most_common(),
                     "nonces": [pl.p["launch_nonce"] for pl in pools], "created": [pl.p["created_contract"] for pl in pools if pl.p["created_contract"]],
                     "tick0": sorted(set(pl.p["tick0"] for pl in pools)), "liq_launch": sorted(set(pl.p["liq_launch"] for pl in pools)),
                     "buy_in_launch_tx_eth": [round(sum(x["eth"] for x in pl.seq if x["in_launch"] and x["buy"]) / 1e18, 6) for pl in pools]}
    # first non-launch buy (any size), first real buy (>= 0.0002)
    fa = [(pl, (pl.buys() or [None])[0]) for pl in pools]
    fr = [(pl, (pl.buys(MIN_REAL) or [None])[0]) for pl in pools]
    def desc(lst):
        have = [(pl, x) for pl, x in lst if x]
        return {"frac_pools": round(len(have) / len(lst), 3), "offset_p10_50_90": q([x["bn"] - pl.b0 for pl, x in have]),
                "eth_p10_50_90": q([x["eth"] / 1e18 for pl, x in have], nd=8), "to": collections.Counter(x["to"] for pl, x in have).most_common(),
                "from": collections.Counter(x["from"] for pl, x in have).most_common(6), "n_distinct_from": len(set(x["from"] for pl, x in have)),
                "selector": collections.Counter(x["sel"] for pl, x in have).most_common(3)}
    r["first_any_buy"] = desc(fa); r["first_real_buy"] = desc(fr)
    # pulls
    pulled = [pl for pl in pools if pl.pull_bn is not None]
    r["pull"] = {"frac_pulled_3000": round(len(pulled) / len(pools), 3), "offset_launch_p10_50_90": q([pl.pull_bn - pl.b0 for pl in pulled]),
                 "offset_first_real_buy_p10_50_90": q([pl.pull_bn - x["bn"] for pl, x in fr if x and pl.pull_bn is not None]),
                 "who": collections.Counter((T.get(pl.pulls[0]["tx"]) or {}).get("from") for pl in pulled).most_common(3)}
    # outsiders before the first scheduled (real) buy: buys by anyone not in the launch tx, before it
    outs = []
    for pl, x in fr:
        lim = (x["bn"], x["li"]) if x else (pl.b0 + 3001, 0)
        o = [y for y in pl.buys() if (y["bn"], y["li"]) < lim]
        outs.append((pl, o))
    r["outsiders_before_first_real_buy"] = {"frac_pools": round(sum(1 for _, o in outs if o) / len(outs), 3),
        "from": collections.Counter(y["from"] for _, o in outs for y in o).most_common(5), "eth_p10_50_90": q([y["eth"] / 1e18 for _, o in outs for y in o], nd=8)}
    # the two rules
    sched = lambda x: x["eth"] >= MIN_REAL
    front = [pl.front(sched) for pl in pools]
    follow = [pl.follow() for pl in pools]
    r["front"] = summarize(front); r["follow"] = summarize(follow)
    r["front_detail"] = [(pl.pid[:12], x["sched_rel"], x["S"], round(x["ret"], 5)) for pl, x in zip(pools, front)]
    r["follow_detail"] = [(pl.pid[:12], x["trig_rel"], x["B"], x["S"], round(x["ret"], 5)) for pl, x in zip(pools, follow) if x]
    # capacity of the first real buy
    caps = []
    for pl, x in fr:
        if x: caps.append(capacity(pl, x, vbot_minout(x)))
    r["capacity"] = {"n": len(caps), "total_eth_p10_50_90": q([c["total_eth"] for c in caps]), "extra_eth_p10_50_90": q([c["extra_eth"] for c in caps]),
                     "assumed": all(c["minout_assumed"] for c in caps) if caps else None}
    res[k] = r
json.dump(res, open("results_raw.json", "w"), indent=1, default=str)
for k, r in res.items():
    print("=" * 30, k); print(json.dumps({a: b for a, b in r.items() if a not in ("front_detail", "follow_detail")}, default=str)[:4000])
    print("front_detail", r["front_detail"]); print("follow_detail", r["follow_detail"])
