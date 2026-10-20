"""analyse_12: the four assigned families plus the two controls (vbot-v2.433, operator-A), priced with px.py.
Writes rows.json (per pool) and stats.json (per family)."""
import sys, os, json, collections, datetime as dt, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from px import *  # noqa

FAMS = ["0x575b952fd3c079b3e72f4cd45f546edd2486d8fa|7fde822e|804|10000|200|true",
        "0x5bd1fbe78a78fe8236fa00cf48fbeba74ae34661|a80ac0c2|1156|0|200|false",
        "0x8366a39cc670b4001a1121b8f6a443a643e40951|6276cbbe|196|3000|60|true",
        "0xa0ce0291c181f800e7a5096b433685c37cfbf4df|617ac5de|676|8388608|200|false"]
P = load_pools(); F = load_families(); T = load_txs(); M = load_blocks_meta()
groups = {k: F[k]["pids"] for k in FAMS}
groups["control:vbot-v2.433"] = [pid for pid, p in P.items() if p["known"] == "vbot-v2.433"]
groups["control:operator-A"] = [pid for pid, p in P.items() if p["known"] == "operator-A"]
allp = set(x for v in groups.values() for x in v)
E = load_events(allp)
print({k[:40]: len(v) for k, v in groups.items()})


def is_bot(x):
    return x["to"] == VBOT_ROUTER and x["sel"] == "c1120e3d"


def pool_row(pid, ctl):
    p = P[pid]; pl = Pool(p, E.get(pid), T, M); b0 = pl.b0
    buys = pl.buys()
    first_any = buys[0] if buys else None
    reals = [x for x in buys if x["eth"] >= MIN_REAL]
    first_real = reals[0] if reals else None
    # the scheduled buy: the bot's router buy for v2.433, else the first real buy
    if ctl == "vbot":
        sched_all = [x for x in buys if is_bot(x)]
    else:
        sched_all = reals
    sched = sched_all[0] if sched_all else None
    r = {"pid": pid, "b0": b0, "ts": p["launch_ts"], "from": p["launch_from"], "nonce": p["launch_nonce"], "value": p["launch_value_eth"],
         "fee": p["fee"], "hooks": p["hooks"], "n_buys": len(buys), "relay_in": any(x["relay"] for x in pl.seq), "base_fee": pl.base_fee}
    fx = lambda x: None if x is None else {"rel": x["bn"] - b0, "ti": x["ti"], "eth": x["eth"] / 1e18, "to": x["to"], "from": x["from"], "sel": x["sel"],
                                         "sender": x["sender"], "tx": x["tx"], "value": (x["value"] / 1e18 if x["value"] is not None else None)}
    r["first_any"] = fx(first_any); r["first_real"] = fx(first_real); r["sched"] = fx(sched)
    # pull
    if pl.pull:
        pt = T.get(pl.pull["tx"])
        r["pull"] = {"rel": pl.pull_bn - b0, "from_sched": (pl.pull_bn - sched["bn"]) if sched else None,
                     "from_first_real": (pl.pull_bn - first_real["bn"]) if first_real else None,
                     "by": pt["from"] if pt else None, "by_launcher": (pt["from"] == p["launch_from"]) if pt else None,
                     "to": pt["to"] if pt else None, "sel": pt["selector"] if pt else None}
    else:
        r["pull"] = None
    # outsiders: non-launch buys before the scheduled buy that are not the scheduler's (any size; dust bot and decoys flagged)
    lim = (sched["bn"], sched["li"]) if sched else (b0 + 3001, 0)
    outs = [x for x in buys if (x["bn"], x["li"]) < lim and x is not sched]
    r["outsiders"] = [{"rel": x["bn"] - b0, "eth": x["eth"] / 1e18, "to": x["to"], "from": x["from"], "dust": x["from"] == DUST or x["eth"] < 1e13} for x in outs]
    real_outs = [x for x in outs if x["eth"] >= MIN_REAL]
    r["first_real_outsider_rel"] = (real_outs[0]["bn"] - b0) if real_outs else None
    if pl.pull and real_outs:
        r["pull_after_real_outsider"] = pl.pull_bn - real_outs[0]["bn"]
    # FRONT: buy at b0+1 (end of block), sell one block after the first scheduled buy behind ours, else at b0+20
    B = b0 + 1
    nxt = [x for x in sched_all if x["bn"] > B]
    S = min(nxt[0]["bn"] + 1, b0 + 20) if nxt else b0 + 20
    r["front"] = pl.trade(B, S)
    r["front"]["sched_behind_rel"] = (nxt[0]["bn"] - b0) if nxt else None
    # generic front for the controls too (first real buy instead of the bot's router buy)
    if ctl == "vbot":
        nr = [x for x in reals if x["bn"] > B]
        S2 = min(nr[0]["bn"] + 1, b0 + 20) if nr else b0 + 20
        r["front_generic"] = pl.trade(B, S2)
    # FOLLOW: buy one block after the first real buy, sell one block after the next real buy behind ours, else at our buy + 4
    if first_real:
        B = first_real["bn"] + 1
        nb = [x for x in reals if x["bn"] > B]
        S = min(nb[0]["bn"] + 1, B + 4) if nb else B + 4
        r["follow"] = pl.trade(B, S)
        r["follow"]["next_rel"] = (nb[0]["bn"] - b0) if nb else None
    else:
        r["follow"] = None
    # capacity of the scheduled buy
    cap = None
    if sched:
        s0, L0 = pl.launch_state()
        X = sched["eth"]; fee = sched["fee"]
        if L0 > 0:
            q0 = v4math.buy_out_int(int(s0), L0, X, fee)
            mo = pl.vbot_minout(sched)
            # the room left at the chain state just before the scheduled buy, and the room from the launch state
            pre_s = sched["pre_sp"]; Lp = pl.L_at(pre_s, sched["bn"], sched["li"])
            if mo is not None:
                cap = {"minout_source": "calldata word 4", "minout_over_quote": mo / q0 if q0 else None,
                       "cap_from_launch": room(s0, L0, X, fee, mo), "room_left_at_chain_state": room(pre_s, Lp, X, fee, mo)}
            else:
                mo99 = int(q0 * 0.99)
                cap = {"minout_source": "assumed 0.99 x launch-state quote", "cap_from_launch": room(s0, L0, X, fee, mo99),
                       "room_left_at_chain_state": room(pre_s, Lp, X, fee, mo99) if Lp > 0 else None}
    r["cap"] = cap
    r["val"] = pl.validate()
    r["L0"] = pl.launch_state()[1]
    return r


rows = {}
for g, pids in groups.items():
    ctl = "vbot" if g == "control:vbot-v2.433" else ("opA" if g == "control:operator-A" else None)
    rows[g] = [pool_row(pid, ctl) for pid in pids]
json.dump(rows, open(os.path.join(HERE, "rows.json"), "w"), default=str)


def ctr(v, n=6):
    return collections.Counter(v).most_common(n)


stats = {}
for g, R in rows.items():
    n = len(R)
    fa = [r["first_any"] for r in R if r["first_any"]]
    fr = [r["first_real"] for r in R if r["first_real"]]
    sc = [r["sched"] for r in R if r["sched"]]
    pulls = [r["pull"] for r in R if r["pull"]]
    s = {"count": n, "launches_per_day": round(n / WINDOW_DAYS, 2),
         "launch_from_distinct": len(set(r["from"] for r in R)), "launch_from_top": ctr([r["from"] for r in R], 3),
         "values": ctr([r["value"] for r in R], 6), "nonce_range": [min(r["nonce"] for r in R), max(r["nonce"] for r in R)],
         "first_any": {"frac": round(len(fa) / n, 3), "rel": q([x["rel"] for x in fa]), "eth": q([x["eth"] for x in fa], nd=8),
                       "to": ctr([x["to"] for x in fa]), "from_distinct": len(set(x["from"] for x in fa)), "from_top": ctr([x["from"] for x in fa], 4)},
         "first_real": {"frac": round(len(fr) / n, 3), "rel": q([x["rel"] for x in fr]), "eth": q([x["eth"] for x in fr], nd=8),
                        "to": ctr([x["to"] for x in fr]), "from_distinct": len(set(x["from"] for x in fr)), "from_top": ctr([x["from"] for x in fr], 4),
                        "from_is_launcher": sum(1 for r in R if r["first_real"] and r["first_real"]["from"] == r["from"])},
         "sched": {"frac": round(len(sc) / n, 3), "rel": q([x["rel"] for x in sc]), "eth": q([x["eth"] for x in sc], nd=8), "to": ctr([x["to"] for x in sc])},
         "pull": {"frac": round(len(pulls) / n, 3), "rel": q([x["rel"] for x in pulls]), "from_sched": q([x["from_sched"] for x in pulls if x["from_sched"] is not None]),
                  "by_launcher": sum(1 for x in pulls if x["by_launcher"]), "by_other": ctr([x["by"] for x in pulls if not x["by_launcher"]], 3),
                  "to_sel": ctr([f"{x['to']}:{x['sel']}" for x in pulls], 3)},
         "outsiders": {"pools_with_any": sum(1 for r in R if r["outsiders"]), "pools_with_nondust": sum(1 for r in R if any(not o["dust"] for o in r["outsiders"])),
                       "pools_with_real": sum(1 for r in R if r["first_real_outsider_rel"] is not None),
                       "sizes": q([o["eth"] for r in R for o in r["outsiders"]], nd=8),
                       "to": ctr([o["to"] for r in R for o in r["outsiders"]], 4)},
         "front": summarize([r["front"] for r in R]), "follow": summarize([r["follow"] for r in R if r["follow"]]),
         "val": {"n": sum(len(r["val"]) for r in R), "p01_50_99": q([x for r in R for x in r["val"]], (.01, .5, .99), nd=8)}}
    # trap test: the pull delay after the first real outsider vs the pools without one
    w = [r for r in R if r["pull"] and r["first_real_outsider_rel"] is not None]
    wo = [r for r in R if r["pull"] and r["first_real_outsider_rel"] is None]
    s["trap"] = {"pulled_with_real_outsider": len(w), "pull_after_outsider": q([r["pull"]["rel"] - r["first_real_outsider_rel"] for r in w]),
                 "pull_rel_with": q([r["pull"]["rel"] for r in w]), "pull_rel_without": q([r["pull"]["rel"] for r in wo]),
                 "unpulled_with_real_outsider": sum(1 for r in R if not r["pull"] and r["first_real_outsider_rel"] is not None)}
    caps = [r["cap"] for r in R if r["cap"]]
    s["cap"] = {"source": ctr([c["minout_source"] for c in caps], 2), "cap_from_launch": q([c["cap_from_launch"] for c in caps], nd=6),
                "room_left": q([c["room_left_at_chain_state"] for c in caps if c.get("room_left_at_chain_state") is not None], nd=6),
                "minout_over_quote": q([c.get("minout_over_quote") for c in caps if c.get("minout_over_quote")], nd=5)}
    if g == "control:vbot-v2.433":
        s["front_generic"] = summarize([r["front_generic"] for r in R])
        ts = lambda x: int(dt.datetime.strptime(x, "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).timestamp())
        a, b = ts("2026-10-10 09:07"), ts("2026-10-10 11:40")
        s["front_live_window"] = summarize([r["front"] for r in R if a <= r["ts"] <= b])
        s["front_bot_kept"] = summarize([r["front"] for r in R if r["front"].get("exit") == "sold" and not r["front"].get("dropped")])
        s["front_bot_dropped"] = summarize([r["front"] for r in R if r["front"].get("dropped")])
    stats[g] = s
    print("=" * 30, g, n)
    for k2, v2 in s.items():
        if k2 in ("front", "follow", "front_generic", "front_live_window", "front_bot_kept", "front_bot_dropped"):
            print(f"  {k2:18s}", fmt_rule(v2), "exits", v2.get("exits"), "p10/50/90", v2.get("p10_50_90"))
        else:
            print(f"  {k2:18s}", json.dumps(v2, default=str)[:700])
json.dump(stats, open(os.path.join(HERE, "stats.json"), "w"), indent=1, default=str)
