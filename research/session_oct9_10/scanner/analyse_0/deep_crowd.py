"""The two crowd families (fee-100 POSM 2,276-byte launches; PM.initialize fee-500 launches): their crowd routers have minOut = 0, the
first crowd buy is far from the launch and the pull is slow, so the literal rules sell before the crowd arrives. Here: (1) a riding grid
(entry at live + 1 or one block after the first crowd buy; exit at a fixed hold or one block after the k-th crowd buy seen in the first
8 swaps), split by time halves; (2) the crowd's cadence and the pull; (3) the other bots already sniping these pools: their own realised
round trips where both legs are among the first 8 swaps."""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common import *
from analyse import sched_pred, sched_minout
P = load_pools(); T = load_txs(); M = load_blocks_meta(); FF = load_families()
FAMS = [("fee100-2276", "0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|2276|100|1|true", 2),
        ("pm-init-500", "0x8366a39cc670b4001a1121b8f6a443a643e40951|6276cbbe|196|500|1|true", 3)]
out = {}
for name, key, idx in FAMS:
    pids = FF[key]["pids"]; E = load_events(set(pids)); is_s = sched_pred(name); mo = sched_minout(name)
    rows = {json.loads(l)["pid"]: json.loads(l) for l in open(os.path.join(HERE, f"pools_{idx}.jsonl"))}
    pools = [Pool(P[p], E[p], T, M) for p in pids]
    pools.sort(key=lambda pl: pl.b0)
    half = pools[len(pools) // 2].b0
    grid = collections.defaultdict(lambda: {"A": [], "B": []})
    cad = []; crowd_eth_300 = []; nocrowd = []; pull_vs_crowd = []
    for pl in pools:
        r = rows[pl.pid]; part = "A" if pl.b0 < half else "B"
        live = pl.live_block
        fs = r["sched"]
        buys = pl.buys()
        for H in (50, 100, 150, 200, 250, 300, 400, 500, 750, 1000):
            grid[("live+1", H)][part].append(pl.trade(live + 1, live + H, minout_check=mo))
            if fs:
                b = live + fs["off"] + 1
                grid[("crowd1+1", H)][part].append(pl.trade(b, b + H, minout_check=mo))
        # crowd cadence: real buys (>= 0.0002) per 100 blocks after the first crowd buy, ETH in by +300 from the live block
        crowd_eth_300.append(sum(x["eth"] for x in buys if x["bn"] <= live + 300 and x["eth"] >= MIN_REAL) / 1e18)
        if fs:
            offs = [x["bn"] - live for x in buys if x["eth"] >= MIN_REAL and x["bn"] - live >= fs["off"]]
            gaps = [b - a for a, b in zip(offs, offs[1:]) if b > a]
            cad.append(st.median(gaps) if gaps else None)
            if pl.pull_bn:
                last_before = [x["bn"] for x in buys if x["bn"] < pl.pull_bn and x["eth"] >= MIN_REAL]
                pull_vs_crowd.append({"pull_off": pl.pull_bn - live, "since_last_real_buy": (pl.pull_bn - last_before[-1]) if last_before else None,
                                      "real_buys_before": len(last_before), "eth_in_before": round(sum(x["eth"] for x in buys if x["bn"] < pl.pull_bn) / 1e18, 4)})
        else:
            nocrowd.append({"pull_off": (pl.pull_bn - live) if pl.pull_bn else None, "n_buys": len(buys), "nonce": pl.p["launch_nonce"],
                            "eth_in": round(sum(x["eth"] for x in buys) / 1e18, 4), "first_real": r.get("first_real")})
    g = {}
    for (entry, H), d in sorted(grid.items()):
        g[f"{entry}|H{H}"] = {"all": {k: v for k, v in summarize(d["A"] + d["B"]).items() if k in ("n", "mean", "median", "win", "pulled_first", "usd_trade", "usd_day")},
                              "first_half": {k: v for k, v in summarize(d["A"]).items() if k in ("n", "mean", "median", "win", "pulled_first")},
                              "second_half": {k: v for k, v in summarize(d["B"]).items() if k in ("n", "mean", "median", "win", "pulled_first")}}
    # snipers: tx-from wallets with a buy and a later sell among the first 8 swaps of the same pool
    snip = collections.defaultdict(lambda: {"pools": 0, "rt": [], "buy_off": [], "sell_off": [], "eth": [], "to_buy": collections.Counter(), "to_sell": collections.Counter()})
    for pl in pools:
        seen = {}
        for x in pl.seq:
            if x["from"] is None or x["relay"]: continue
            if x["buy"] and x["from"] not in seen and not is_s(x) and x["from"] != DUST:
                seen[x["from"]] = x
            elif not x["buy"] and x["from"] in seen:
                b = seen.pop(x["from"]); s = snip[x["from"]]
                s["pools"] += 1; s["rt"].append(x["eth"] / b["eth"] - 1); s["buy_off"].append(b["bn"] - pl.live_block); s["sell_off"].append(x["bn"] - pl.live_block)
                s["eth"].append(b["eth"] / 1e18); s["to_buy"][b["to"]] += 1; s["to_sell"][x["to"]] += 1
    sn = {w: {"round_trips": s["pools"], "ret_mean": round(st.mean(s["rt"]), 4), "ret_median": round(st.median(s["rt"]), 4), "buy_eth": q(s["eth"], (0, .5, 1), 7),
              "buy_off": q(s["buy_off"], (0, .5, 1)), "sell_off": q(s["sell_off"], (0, .5, 1)), "buy_router": s["to_buy"].most_common(2), "sell_router": s["to_sell"].most_common(2)}
          for w, s in sorted(snip.items(), key=lambda kv: -kv[1]["pools"]) if s["pools"] >= 3}
    out[name] = {"grid": g, "crowd_gap_median_blocks": q([c for c in cad if c is not None], (.1, .5, .9)), "crowd_eth_by_live300": q(crowd_eth_300, (.1, .5, .9)),
                 "no_crowd_pools": {"n": len(nocrowd), "pulled": sum(1 for x in nocrowd if x["pull_off"] is not None), "pull_off": q([x["pull_off"] for x in nocrowd], (.1, .5, .9)),
                                    "nonce": collections.Counter(x["nonce"] for x in nocrowd).most_common(), "eth_in": q([x["eth_in"] for x in nocrowd], (.1, .5, .9))},
                 "pull_vs_crowd": {"n": len(pull_vs_crowd), "since_last_real_buy": q([x["since_last_real_buy"] for x in pull_vs_crowd], (.1, .5, .9)),
                                   "eth_in_before": q([x["eth_in_before"] for x in pull_vs_crowd], (.1, .5, .9))},
                 "snipers": sn, "half_split_block": half}
    print("=====", name)
    for k, v in g.items(): print(k, json.dumps(v))
    for k in ("crowd_gap_median_blocks", "crowd_eth_by_live300", "no_crowd_pools", "pull_vs_crowd"): print(k, json.dumps(out[name][k], default=str))
    for w, s in sn.items(): print("  sniper", w, json.dumps(s, default=str))
json.dump(out, open(os.path.join(HERE, "deep_crowd.json"), "w"), indent=1, default=str)
