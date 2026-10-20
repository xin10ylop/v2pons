#!/usr/bin/env python3
"""analyse_4 main: per family (controls first), structure + front/follow pricing + capacity + trap test -> results.json
Usage: python3 -I analyse.py
"""
import sys, os, json, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from ana import *   # noqa

FAMS = [
    {"name": "vbot-v2.433 (control)", "sel": {"known": "vbot-v2.433"}, "sched": "vbot"},
    {"name": "operator-A (control)", "sel": {"known": "operator-A"}, "sched": "real"},
    {"name": "hook-launcher 0xfcd18241 fee 10%", "key": "0xfcd182416ca91a9e88e9fe44e4f78ea3cb2c15c7|6fe958d8|68|100000|200|false", "sched": "real"},
    {"name": "PM-direct init fee 838974", "key": "0x8366a39cc670b4001a1121b8f6a443a643e40951|6276cbbe|196|838974|9303|true", "sched": "real"},
    {"name": "POSM1444 fee 0.3% ts60", "key": "0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|3000|60|true", "sched": "real"},
    {"name": "launchpad 0x815542e8 fee 3%", "key": "0x815542e8b392389a1389e22e588e4b62a67ade72|7c33638d|769|30000|200|true", "sched": "real"},
]
DECOY_ROUTERS = {"0x65050a9b7e5075a2ba5ced7b1b64ee66262c40dc", "0xfd1b271f235e5230eaee9d914ccb1af495bfb758"}


def classify(x, is_sched):
    if is_sched(x): return "sched"
    if x["from"] == DUST: return "dust_bot"
    if x["to"] in DECOY_ROUTERS: return "vbot_decoy"
    if not x["known_tx"]: return "unknown_tx"
    return "other"


def analyse_pool(pl, mode):
    p = pl.p; b0 = pl.b0
    r = {"pid": pl.pid, "b0": b0, "ts": p["launch_ts"], "from": p["launch_from"], "nonce": p["launch_nonce"], "value": p["launch_value_eth"],
         "start": pl.start, "L0": pl.L0, "fee": pl.fee, "n_swaps": len(pl.seq), "rebalances": pl.n_rebalance}
    buys = pl.buys()
    if mode == "vbot":
        is_sched = lambda x: x["to"] == VBOT_ROUTER
    else:
        is_sched = lambda x: x["eth"] >= MIN_REAL
    for x in buys: x["cls"] = classify(x, is_sched)
    fb = buys[0] if buys else None
    r["first_buy"] = {"off": fb["bn"] - b0, "eth": fb["eth"] / 1e18, "to": fb["to"], "from": fb["from"], "sel": fb["sel"], "cls": fb["cls"]} if fb else None
    fr = next((x for x in buys if x["eth"] >= MIN_REAL), None)
    r["first_real"] = {"off": fr["bn"] - b0, "eth": fr["eth"] / 1e18, "to": fr["to"], "from": fr["from"], "sel": fr["sel"], "cdl": fr["cdl"], "cls": fr["cls"]} if fr else None
    fs = next((x for x in buys if x["cls"] == "sched"), None)
    # v2.433: a bot buy beyond the first 8 swaps has no tx row; flag pools where it may hide
    r["sched_hidden"] = fs is None and any(not x["known_tx"] for x in buys)
    r["sched"] = {"off": fs["bn"] - b0, "eth": fs["eth"] / 1e18, "to": fs["to"], "from": fs["from"], "sel": fs["sel"], "cdl": fs["cdl"],
                  "minout": vbot_minout(fs)} if fs else None
    lim = (fs["bn"], fs["li"]) if fs else (b0 + 20, 10**9)
    outs = [x for x in buys if (x["bn"], x["li"]) < lim and x["cls"] != "sched"]
    r["before_sched"] = [{"off": x["bn"] - b0, "eth": x["eth"] / 1e18, "cls": x["cls"], "to": x["to"], "from": x["from"]} for x in outs]
    rel = [x for x in pl.seq if x["relay"] and x["buy"]]
    r["relay_buy_off"] = (rel[0]["bn"] - b0) if rel else None
    if pl.pull_bn is not None:
        t = pl.T.get(pl.pull_tx) if hasattr(pl, "T") else None
        r["pull"] = {"off": pl.pull_bn - b0, "after_sched": (pl.pull_bn - fs["bn"]) if fs else None,
                     "from": t["from"] if t else None, "to": t["to"] if t else None, "sel": t["selector"] if t else None,
                     "by_launcher": (t["from"] == p["launch_from"]) if t else None}
    else:
        r["pull"] = None
    # ---- front: buy at launch + 1 (end of block), sell one block after the first scheduled buy behind ours, or at launch + 20
    B = b0 + 1
    nxt = next((x for x in buys if x["cls"] == "sched" and x["bn"] > B), None)
    if nxt is None or nxt["bn"] + 1 > b0 + 20:
        S = b0 + 20; why = "deadline"
    else:
        S = nxt["bn"] + 1; why = "sched"
    t = pl.trade(B, S, minout_check=vbot_minout); t["why"] = why
    t["late"] = bool(fs and fs["bn"] <= B)
    r["front"] = t
    r["live_off"] = (pl.live_block - b0) if pl.live_block is not None else None
    # the same rule counted from the block the liquidity goes live (pools whose mint is a separate, later transaction)
    if pl.live_block is not None and pl.live_block != b0:
        Bl = pl.live_block + 1
        nl = next((x for x in buys if x["cls"] == "sched" and x["bn"] > Bl), None)
        Sl = pl.live_block + 20 if (nl is None or nl["bn"] + 1 > pl.live_block + 20) else nl["bn"] + 1
        r["front_live"] = pl.trade(Bl, Sl, minout_check=vbot_minout)
    else:
        r["front_live"] = t
    # front with the generic trigger on v2.433 (first real buy, whatever router) for comparison
    if mode == "vbot":
        g = next((x for x in buys if x["eth"] >= MIN_REAL and x["bn"] > B), None)
        S2 = b0 + 20 if (g is None or g["bn"] + 1 > b0 + 20) else g["bn"] + 1
        r["front_generic"] = pl.trade(B, S2, minout_check=vbot_minout)
    # ---- follow: buy one block after the first real buy; sell one block after the next real buy, or at our buy + 4
    if fr:
        Bf = fr["bn"] + 1
        nx = next((x for x in buys if x["bn"] > Bf and x["eth"] >= MIN_REAL), None)
        Sf = min(nx["bn"] + 1, Bf + 4) if nx else Bf + 4
        tf = pl.trade(Bf, Sf, minout_check=vbot_minout); tf["why"] = "next_buy" if (nx and nx["bn"] + 1 <= Bf + 4) else "hold4"
        tf["trig_off"] = fr["bn"] - b0; r["follow"] = tf
    else:
        r["follow"] = None
    # ---- capacity of the first scheduled buy
    if fs and pl.L0 > 0:
        X = fs["eth"]; f = fs["fee"]
        quote = v4math.buy_out_int(int(pl.s_eff), pl.L0, X, f)
        mo = vbot_minout(fs)
        mo_used = mo if mo is not None else int(quote * 0.99)
        s_pre, L_pre = pl.state_before(fs["bn"], fs["li"])
        r["cap"] = {"X": X / 1e18, "minout_decoded": mo is not None, "minout_over_quote": (mo / quote) if (mo and quote) else None,
                    "room_total": room(int(pl.s_eff), pl.L0, X, f, mo_used), "room_left": room(int(s_pre), L_pre, X, f, mo_used),
                    "ahead_others": sum(x["eth"] for x in buys if (x["bn"], x["li"]) < (fs["bn"], fs["li"])) / 1e18}
    return r


def fam_summary(name, rows, mode):
    live = [r for r in rows]
    out = {"name": name, "count": len(rows), "launches_per_day": round(len(rows) / WINDOW_DAYS, 1)}
    out["start_state"] = dict(collections.Counter(r["start"] for r in rows))
    out["deployers"] = len({r["from"] for r in rows}); out["top_deployers"] = collections.Counter(r["from"] for r in rows).most_common(4)
    out["values"] = collections.Counter(r["value"] for r in rows).most_common(5)
    out["n_with_swaps"] = sum(1 for r in rows if r["n_swaps"])
    fb = [r["first_buy"] for r in rows if r["first_buy"]]
    out["first_buy_any"] = {"n": len(fb), "frac": round(len(fb) / len(rows), 3), "off": pct([x["off"] for x in fb]), "eth": pct([x["eth"] for x in fb], nd=7),
                            "cls": collections.Counter(x["cls"] for x in fb).most_common(), "to": collections.Counter(x["to"] for x in fb).most_common(5),
                            "n_from": len({x["from"] for x in fb if x["from"]})}
    fr = [r["first_real"] for r in rows if r["first_real"]]
    out["first_real"] = {"n": len(fr), "frac": round(len(fr) / len(rows), 3), "off": pct([x["off"] for x in fr]), "eth": pct([x["eth"] for x in fr], nd=6),
                         "to_sel_cdl": collections.Counter(f"{x['to']}:{x['sel']}:{x['cdl']}" for x in fr).most_common(5),
                         "n_from": len({x["from"] for x in fr if x["from"]}), "top_from": collections.Counter(x["from"] for x in fr).most_common(3)}
    sc = [r["sched"] for r in rows if r["sched"]]
    out["sched"] = {"n": len(sc), "frac": round(len(sc) / len(rows), 3), "hidden_beyond_8": sum(1 for r in rows if r["sched_hidden"]),
                    "off": pct([x["off"] for x in sc], (.1, .5, .9)), "off_minmax": pct([x["off"] for x in sc], (0, 1)),
                    "eth": pct([x["eth"] for x in sc], nd=6), "routers": collections.Counter(x["to"] for x in sc).most_common(4),
                    "n_from": len({x["from"] for x in sc}), "top_from": collections.Counter(x["from"] for x in sc).most_common(3)}
    pu = [r for r in rows if r["pull"]]
    out["pull"] = {"frac_3000": round(len(pu) / len(rows), 3), "off": pct([r["pull"]["off"] for r in pu]),
                   "after_sched": pct([r["pull"]["after_sched"] for r in pu if r["pull"]["after_sched"] is not None]),
                   "after_sched_hist": collections.Counter(r["pull"]["after_sched"] for r in pu if r["pull"]["after_sched"] is not None).most_common(6),
                   "before_sched": sum(1 for r in pu if r["pull"]["after_sched"] is not None and r["pull"]["after_sched"] < 0),
                   "no_sched": sum(1 for r in pu if r["sched"] is None),
                   "by_launcher": sum(1 for r in pu if r["pull"]["by_launcher"]), "pull_tx_known": sum(1 for r in pu if r["pull"]["from"]),
                   "to_sel": collections.Counter(f"{r['pull']['to']}:{r['pull']['sel']}" for r in pu).most_common(3),
                   "rebalance_pools": sum(1 for r in rows if r["rebalances"])}
    cls_c = collections.Counter(); sz = collections.defaultdict(list)
    for r in rows:
        for o in r["before_sched"]:
            cls_c[o["cls"]] += 1; sz[o["cls"]].append(o["eth"])
    out["before_sched"] = {c: {"n": n, "pools": sum(1 for r in rows if any(o["cls"] == c for o in r["before_sched"])), "eth": pct(sz[c], (0, .5, 1), 7)}
                           for c, n in cls_c.most_common()}
    out["relay_pools"] = sum(1 for r in rows if r["relay_buy_off"] is not None)
    # trap test: real-size outsider (>= 0.0002, not the scheduled buyer, not the dust bot / decoys) before the scheduled buy, vs none
    def real_out(r, classes=("other", "unknown_tx")):
        return next((o for o in r["before_sched"] if o["cls"] in classes and o["eth"] >= 0.0002), None)
    def st_(rs, with_out):
        if not rs: return {"n": 0}
        d_o = []
        for r in rs:
            o = real_out(r)
            if with_out and o and r["pull"]: d_o.append(r["pull"]["off"] - o["off"])
        return {"n": len(rs), "pulled_3000": round(sum(1 for r in rs if r["pull"]) / len(rs), 3),
                "pulled_before_sched": sum(1 for r in rs if r["pull"] and r["sched"] and r["pull"]["after_sched"] < 0),
                "pull_off": pct([r["pull"]["off"] for r in rs if r["pull"]]),
                "pull_after_sched": pct([r["pull"]["after_sched"] for r in rs if r["pull"] and r["pull"]["after_sched"] is not None]),
                "pull_after_outsider": pct(d_o) if with_out else None}
    w = [r for r in rows if real_out(r)]; wo = [r for r in rows if not real_out(r)]
    out["trap"] = {"with_outsider": st_(w, True), "without": st_(wo, False)}
    if mode == "vbot":
        # our own relay's real buys ahead of the bot (Oct 10 09:07 onwards): the live outsider test
        wr = [r for r in rows if r["relay_buy_off"] is not None and r["sched"] and r["relay_buy_off"] < r["sched"]["off"]]
        wn = [r for r in rows if r["relay_buy_off"] is None]
        out["trap"]["relay_ahead"] = st_(wr, False); out["trap"]["no_relay"] = st_(wn, False)
    out["front"] = summarize([r["front"] for r in rows]); out["front_from_live"] = summarize([r["front_live"] for r in rows])
    out["live_off"] = pct([r["live_off"] for r in rows], (0, .5, 1)); out["front_why"] = collections.Counter(r["front"].get("why") for r in rows).most_common()
    out["front_late"] = sum(1 for r in rows if r["front"].get("late")); out["front_dropped"] = sum(1 for r in rows if r["front"].get("dropped"))
    if mode == "vbot":
        out["front_generic_trigger"] = summarize([r["front_generic"] for r in rows])
    out["follow"] = summarize([r["follow"] for r in rows if r["follow"]])
    out["follow_why"] = collections.Counter(r["follow"]["why"] for r in rows if r["follow"]).most_common()
    cp = [r["cap"] for r in rows if r.get("cap")]
    out["cap"] = {"n": len(cp), "minout_decoded": sum(1 for c in cp if c["minout_decoded"]),
                  "minout_over_quote": pct([c["minout_over_quote"] for c in cp if c["minout_over_quote"]], (0, .1, .5, .9, 1), 6),
                  "room_total": pct([c["room_total"] for c in cp if c["room_total"] not in (None, float("inf"))], (0, .1, .5, .9, 1), 5),
                  "room_left": pct([c["room_left"] for c in cp if c["room_left"] not in (None, float("inf"))], (0, .1, .5, .9, 1), 5),
                  "room_inf": sum(1 for c in cp if c["room_total"] == float("inf")),
                  "room_left_under_stake": sum(1 for c in cp if c["room_left"] is not None and c["room_left"] < 0.0058),
                  "ahead_others": pct([c["ahead_others"] for c in cp], (.5, .9, 1), 6)}
    return out


def main():
    P = load_pools(); T = load_txs(); M = load_blocks_meta(); FF = load_families()
    res = {}
    for f in FAMS:
        if "key" in f: pids = FF[f["key"]]["pids"]
        else: pids = [pid for pid, p in P.items() if p["known"] == f["sel"]["known"]]
        E = load_events(set(pids))
        rows = []
        for pid in pids:
            pl = Pool(P[pid], E.get(pid), T, M); pl.T = T
            rows.append(analyse_pool(pl, f["sched"]))
        tag = f.get("key") or f["sel"]["known"]
        with open(os.path.join(HERE, f"pools_{len(res)}.jsonl"), "w") as fo:
            for r in rows: fo.write(json.dumps(r, default=str) + "\n")
        res[tag] = fam_summary(f["name"], rows, f["sched"])
        s = res[tag]
        print("=" * 110); print(f["name"], tag, "n", s["count"], "per day", s["launches_per_day"])
        for k in ("live_off", "front_from_live", "start_state", "first_buy_any", "first_real", "sched", "pull", "before_sched", "trap", "front", "front_why", "follow", "follow_why", "cap"):
            print(f"  {k}: {json.dumps(s[k], default=str)}")
        if "front_generic_trigger" in s: print("  front_generic_trigger:", json.dumps(s["front_generic_trigger"]))
    json.dump(res, open(os.path.join(HERE, "results_raw.json"), "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
