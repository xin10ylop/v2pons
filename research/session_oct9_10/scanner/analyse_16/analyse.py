"""per-family statistics and the two priced trades for the four analyse_16 families, plus the wider launcher groups they belong to
(the loose 7fde822e family of every launch contract, the ff734f50 launchers)"""
import sys, json, statistics as st, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/analyse_16")
from common16 import *
KEYS = json.load(open(OUT + "/keys.json"))
P0 = load_pools(); F = load_families(); LF = load_loose_families()
groups = {k: F[k]["pids"] for k in KEYS}
loose7 = [p["pid"] for p in P0.values() if p["selector"] == "7fde822e"]
groups["WIDER all 7fde822e launches (every launch contract)"] = loose7
groups["WIDER all ff734f50 launches (3 launch contracts)"] = [p["pid"] for p in P0.values() if p["selector"] == "ff734f50"]
groups["WIDER deployer 0x06cb3a68 (all its pools)"] = [p["pid"] for p in P0.values() if p["launch_from"] == "0x06cb3a6841c92525e7a1998328e7c9d37e98d937"]
groups["WIDER deployer 0x17ad4d45 (all its pools)"] = [p["pid"] for p in P0.values() if p["launch_from"] == "0x17ad4d45f347794ddc38211de615fb90a641ef1c"]
ctx = Ctx(set(x for v in groups.values() for x in v))
P, E, T = ctx.P, ctx.E, ctx.T


def real_sched(ctx, p, B):
    for s in buys(ctx, p):
        if s["bn"] > B and -s["a0"] >= MIN_REAL: return s
    return None


def txinfo(h):
    t = T.get(h)
    return (t["to"], t["from"], t["selector"]) if t else (None, None, None)


res = {}
for g, pids in groups.items():
    ps = [P[x] for x in pids]
    lbs = [p["launch_block"] for p in ps]
    r = {"count": len(ps), "launches_per_day": round(len(ps) / DAYS, 2), "span_blocks": [min(lbs), max(lbs)],
         "span_hours": round((max(lbs) - min(lbs)) * 0.1026 / 3600, 2),
         "deployers": collections.Counter(p["launch_from"] for p in ps).most_common(6),
         "launch_to": collections.Counter(p["launch_to"] for p in ps).most_common(4),
         "values": collections.Counter(p["launch_value_eth"] for p in ps).most_common(6),
         "nonces": sorted(p["launch_nonce"] for p in ps)[:12],
         "fees": collections.Counter(p["fee"] for p in ps).most_common(4),
         "sqrt_p0": collections.Counter(p["sqrt_p0"] for p in ps).most_common(3),
         "liq_launch": collections.Counter(p["liq_launch"] for p in ps).most_common(3),
         "buy_in_launch_tx": sum(1 for p in ps if p["buy_in_launch_tx"]),
         "launch_tx_ti_p10_50_90": pct([p["tx_index"] for p in ps]),
         "n_adds_launch": collections.Counter(len([a for a in (E.get(p["pid"]) or {"adds": []})["adds"] if a["tx"] == p["launch_tx"]]) for p in ps).most_common(3)}
    # first non-launch buy (any size) and first real buy (>= 0.0002)
    fb, fr = [], []
    for p in ps:
        bs = buys(ctx, p)
        if bs:
            s = bs[0]; to, fr_, sel = txinfo(s["tx"])
            fb.append({"pid": p["pid"], "off": s["bn"] - p["launch_block"], "eth": -s["a0"] / 1e18, "to": to, "from": fr_, "sel": sel})
        rb = [s for s in bs if -s["a0"] >= MIN_REAL]
        if rb:
            s = rb[0]; to, fr_, sel = txinfo(s["tx"])
            fr.append({"pid": p["pid"], "off": s["bn"] - p["launch_block"], "eth": -s["a0"] / 1e18, "to": to, "from": fr_, "sel": sel,
                       "launch_from": p["launch_from"]})
    r["first_buy_any"] = {"pools_with": len(fb), "frac": round(len(fb) / len(ps), 3), "off_p10_50_90": pct([x["off"] for x in fb]),
                          "eth_p10_50_90": pct([x["eth"] for x in fb]), "to": collections.Counter(x["to"] for x in fb).most_common(4),
                          "from": collections.Counter(x["from"] for x in fb).most_common(4), "n_from": len(set(x["from"] for x in fb))}
    r["first_buy_real"] = {"pools_with": len(fr), "frac": round(len(fr) / len(ps), 3), "off_p10_50_90": pct([x["off"] for x in fr]),
                           "eth_p10_50_90": pct([x["eth"] for x in fr]), "to": collections.Counter(x["to"] for x in fr).most_common(4),
                           "from": collections.Counter(x["from"] for x in fr).most_common(6), "n_from": len(set(x["from"] for x in fr)),
                           "by_launch_wallet": sum(1 for x in fr if x["from"] == x["launch_from"]), "list": fr[:12]}
    # swaps by everyone
    allsw = [s for p in ps for s in (E.get(p["pid"]) or {"swaps": []})["swaps"]]
    r["swaps_total"] = len(allsw); r["buys_total"] = sum(1 for s in allsw if s["a0"] < 0); r["sells_total"] = sum(1 for s in allsw if s["a0"] > 0)
    r["swap_senders"] = collections.Counter(s["sender"] for s in allsw).most_common(5)
    r["eth_in_buys_total"] = round(sum(-s["a0"] for s in allsw if s["a0"] < 0) / 1e18, 6)
    # pulls
    pl = []
    for p in ps:
        e = E.get(p["pid"])
        if e and e["pulls"]:
            x = e["pulls"][0]; bs = [s for s in buys(ctx, p) if -s["a0"] >= MIN_REAL]
            pl.append({"off": x["bn"] - p["launch_block"], "from_first_real_buy": (x["bn"] - bs[0]["bn"]) if bs else None,
                       "by": p["first_pull_from"], "launch_from": p["launch_from"]})
    r["pull"] = {"pulled": len(pl), "frac": round(len(pl) / len(ps), 3), "off_p10_50_90": pct([x["off"] for x in pl]),
                 "from_buy_p10_50_90": pct([x["from_first_real_buy"] for x in pl if x["from_first_real_buy"] is not None]),
                 "by_launch_wallet": sum(1 for x in pl if x["by"] == x["launch_from"])}
    # outsiders/trap: a real buy (>= 0.0002) by a wallet other than the launch wallet, and the pull delay after it
    with_out, wo_out = [], []
    for p in ps:
        e = E.get(p["pid"]); bs = [s for s in buys(ctx, p) if -s["a0"] >= MIN_REAL]
        pull = e["pulls"][0]["bn"] if e and e["pulls"] else None
        outs = [s for s in bs if txinfo(s["tx"])[1] != p["launch_from"]]
        if outs:
            with_out.append((pull - outs[0]["bn"]) if pull is not None and pull > outs[0]["bn"] else None)
        else:
            wo_out.append((pull - p["launch_block"]) if pull is not None else None)
    r["trap"] = {"pools_with_outsider_real_buy": len(with_out), "pulled_after_outsider": sum(1 for x in with_out if x is not None),
                 "pull_delay_after_outsider_p10_50_90": pct([x for x in with_out if x is not None]),
                 "pools_without": len(wo_out), "pulled_without": sum(1 for x in wo_out if x is not None),
                 "pull_off_without_p10_50_90": pct([x for x in wo_out if x is not None])}
    # the two trades
    fr_rs = [front(ctx, p, real_sched) for p in ps]
    fo_rs = [x for x in (follow(ctx, p) for p in ps) if x]
    r["front"] = summ(fr_rs); r["front_exits"] = dict(collections.Counter(x["exit"] for x in fr_rs))
    r["front_sched_found_by_20"] = sum(1 for x in fr_rs if x["sched"] is not None and x["sched"] < 20)
    r["front_ret_gross_p10_50_90"] = pct([x["ret_gross"] for x in fr_rs if "ret_gross" in x])
    r["follow"] = summ(fo_rs); r["follow_rows"] = [{k: x.get(k) for k in ("trig", "trig_eth", "next", "B", "S", "exit", "ret", "between")} for x in fo_rs][:12]
    # front with a long hold (does any buy come at all within 3,000 blocks?)
    r["front_hold3000"] = summ([front(ctx, p, real_sched, hold=3000) for p in ps])
    # capacity
    caps = []
    for p in ps:
        sb = real_sched(ctx, p, p["launch_block"])
        if sb:
            c = capacity(ctx, p, sb)
            if c: caps.append(c)
    r["capacity"] = {"n": len(caps), "cap_eth_p10_50_90": pct([c["cap_eth"] for c in caps]),
                     "src": collections.Counter(c["minout_src"] for c in caps).most_common(2)}
    res[g] = r
    print("=" * 110); print(g)
    print("  count %d (%.2f/day), span %.2f h, deployers %s, launch_to %s, values %s" % (len(ps), r["launches_per_day"], r["span_hours"], r["deployers"][:3], r["launch_to"][:2], r["values"][:4]))
    print("  nonces", r["nonces"], "fees", r["fees"], "buy_in_launch_tx", r["buy_in_launch_tx"], "adds in launch tx", r["n_adds_launch"])
    print("  first buy (any):", {k: v for k, v in r["first_buy_any"].items()})
    print("  first buy (>=0.0002):", {k: v for k, v in r["first_buy_real"].items() if k != "list"})
    for x in r["first_buy_real"]["list"]: print("     ", x)
    print("  swaps %d (buys %d sells %d), ETH in buys %.6f, senders %s" % (r["swaps_total"], r["buys_total"], r["sells_total"], r["eth_in_buys_total"], r["swap_senders"][:3]))
    print("  pull", r["pull"]); print("  trap", r["trap"])
    print("  FRONT ", fmt(r["front"]), r["front_exits"], "sched<20:", r["front_sched_found_by_20"], "gross", r["front_ret_gross_p10_50_90"])
    print("  FRONT hold 3000", fmt(r["front_hold3000"]))
    print("  FOLLOW", fmt(r["follow"]))
    for x in r["follow_rows"]: print("     ", x)
    print("  capacity", r["capacity"])
json.dump(res, open(OUT + "/stats.json", "w"), indent=1, default=str)
