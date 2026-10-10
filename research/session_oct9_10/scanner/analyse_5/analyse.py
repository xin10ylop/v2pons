"""analyse_5: the four assigned families (PM1444 fee-100 1.5-2 ETH; three 7fde822e launch contracts of deployer 0x06cb3a68) plus the
fee-500 sibling of the first and the two controls (vbot-v2.433, operator A), each through the same code: launcher, first buys, the
scheduled buy, pulls, outsiders and the trap test, the exact replay of front and follow (plus family variants), and the scheduled buy's room.
Writes pools_<name>.jsonl and results.json. Run: python3 -I analyse.py"""
import sys, os, datetime
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from pricer import *

K_C100 = "0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|100|1|true"
K_C500 = "0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|500|10|true"
K_9F = "0x9f81695f2d705e81f8fb7a4f8831afe92c4e6b35|7fde822e|804|10000|200|true"
K_B7 = "0xb7758ae7102037e3db22fe472689e6598a78f639|7fde822e|804|10000|200|true"
K_F6 = "0xf6b59a71e1a3169bd418169ee20e37e6a7152b5c|7fde822e|804|10000|200|true"
K_V = "0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|2500|50|true"


def ur_minout(x):
    """Universal Router execute -> V4_SWAP SWAP_EXACT_IN: the amountIn word equals the tx value, the next word is amountOutMinimum"""
    inp = x.get("input"); v = x.get("value")
    if not inp or not v or x.get("to") != UR or x.get("sel") != "3593564c" or len(inp) < 10 + 64 * 30: return None
    d = inp[10:]; n = len(d) // 64
    for i in range(8, n - 1):
        if int(d[64 * i: 64 * i + 64], 16) == v:
            return int(d[64 * (i + 1): 64 * (i + 2)], 16)
    return None


def vbot_minout(x):
    if x.get("to") == VBOT_ROUTER and x.get("sel") == "c1120e3d" and x.get("input"):
        return int(x["input"][10 + 64 * 4: 10 + 64 * 5], 16)
    return None


def any_minout(x):
    mo = vbot_minout(x)
    return mo if mo is not None else ur_minout(x)


SCHED = {
    "opC": lambda x: x["to"] == UR and x["sel"] == "3593564c" and x["clen"] == 1284 and x["nonce"] == 0,
    "vbot": lambda x: x["to"] == VBOT_ROUTER and x["sel"] == "c1120e3d",
    "opA": lambda x: x["eth"] >= MIN_REAL and x["to"] is not None and x["from"] != DUST,   # the crowd's first real buy
    "none": lambda x: False,
}

FAMS = [  # name, keys (or "operator-A"), sched kind, family wait W for the front variant, role
    ("opC-fee100", [K_C100], "opC", 600, "assigned"),
    ("06cb-9f81", [K_9F], "none", 20, "assigned"),
    ("06cb-b775", [K_B7], "none", 20, "assigned"),
    ("06cb-f6b5", [K_F6], "none", 20, "assigned"),
    ("opC-fee500", [K_C500], "opC", 600, "sibling"),
    ("opC-hist-oct7", "hist", "opC", 600, "history (pre-window, fee 100 and 500)"),
    ("control-v2433", [K_V], "vbot", 150, "control"),
    ("control-opA", "operator-A", "opA", 150, "control"),
]


def classify(x, is_sched):
    if x["relay"]: return "relay"
    if x["to"] is None: return "unknown"          # beyond the first 8 swaps: no tx
    if is_sched(x): return "sched"
    if x["from"] == DUST: return "dust"
    if x["to"] in VBOT_DECOY_ROUTERS: return "vbot_decoy"
    return "other"


def analyse_pool(pl, kind, W):
    p = pl.p; b0 = pl.b0; is_sched = SCHED[kind]
    r = {"pid": pl.pid, "b0": b0, "ts": p["launch_ts"], "from": p["launch_from"], "nonce": p["launch_nonce"], "value": p["launch_value_eth"],
         "L0": pl.L0, "fee": pl.fee_pool, "tick0": p["tick0"], "ranges": pl.ranges, "n_swaps": len(pl.seq), "live_off": (pl.live_block - b0) if pl.live_block is not None else None}
    if pl.live_block is None or pl.L0 <= 0:
        r["dead"] = True; return r
    buys = pl.buys()
    for x in buys: x["cls"] = classify(x, is_sched)
    r["n_buys"] = len(buys); r["eth_in"] = sum(x["eth"] for x in buys) / 1e18
    fb = buys[0] if buys else None
    r["first_buy"] = {"off": fb["bn"] - b0, "eth": fb["eth"] / 1e18, "to": fb["to"], "from": fb["from"], "cls": fb["cls"]} if fb else None
    fr = next((x for x in buys if x["eth"] >= MIN_REAL), None)
    r["first_real"] = {"off": fr["bn"] - b0, "eth": fr["eth"] / 1e18, "to": fr["to"], "from": fr["from"], "sel": fr["sel"], "nonce": fr["nonce"], "clen": fr["clen"], "cls": fr["cls"]} if fr else None
    fs = next((x for x in buys if x["cls"] == "sched"), None)
    scheds = [x for x in buys if x["cls"] == "sched"]
    if fs:
        mo = any_minout(fs)
        r["sched"] = {"off": fs["bn"] - b0, "eth": fs["eth"] / 1e18, "to": fs["to"], "from": fs["from"], "sel": fs["sel"], "nonce": fs["nonce"], "clen": fs["clen"],
                      "minout": mo, "minout_over_fill": (mo / fs["a1"]) if mo else None, "n_known": len(scheds),
                      "same_block": sum(1 for x in scheds if x["bn"] == fs["bn"])}
    else:
        r["sched"] = None
    lim = (fs["bn"], fs["li"]) if fs else (b0 + W, 10 ** 9)
    outs = [x for x in buys if (x["bn"], x["li"]) < lim and x["cls"] != "sched"]
    r["before_sched"] = [{"off": x["bn"] - b0, "eth": x["eth"] / 1e18, "cls": x["cls"], "to": x["to"], "from": x["from"]} for x in outs]
    rel = [x for x in pl.seq if x["relay"] and x["buy"]]
    r["relay_buy_off"] = (rel[0]["bn"] - b0) if rel else None
    if pl.pull:
        r["pull"] = {"off": pl.pull_bn - b0, "from": p["first_pull_from"], "to": p["first_pull_to"], "sel": p["first_pull_selector"],
                     "by_launcher": p["first_pull_from"] == p["launch_from"], "full": -pl.pull["dl"] >= pl.L0 * 0.99,
                     "after_sched": (pl.pull_bn - fs["bn"]) if fs else None, "after_first_real": (pl.pull_bn - fr["bn"]) if fr else None}
    else:
        r["pull"] = None
    # ---------------- front: buy lands at launch + 1 (end of block); sell one block after the first scheduled buy, else at launch + W
    B = b0 + 1
    def front(Wd):
        if fs is None or fs["bn"] > b0 + Wd: S = b0 + Wd; why = "deadline"
        else: S = max(fs["bn"] + 1, B + 1); why = "sched" if fs["bn"] > B else "sched_not_ahead"
        t = pl.trade(B, S, minout_check=any_minout); t["why"] = why; return t
    r["front"] = front(20)
    r["front_wait"] = front(W)
    r["front_hold"] = {H: pl.trade(B, b0 + H, minout_check=any_minout) for H in (20, 100, 300, 600, 900, 1200, 1500)}
    # front, sell one block after the k-th crowd buy (opC: the scheduled fingerprint in the first 8 swaps, else any buy >= 0.005 ETH after it)
    if kind == "opC":
        crowd = []
        for x in buys:
            if x["cls"] == "sched" or (fs and (x["bn"], x["li"]) > (fs["bn"], fs["li"]) and x["cls"] == "unknown" and x["eth"] >= int(0.005e18)):
                crowd.append(x)
        r["crowd_offs"] = [x["bn"] - b0 for x in crowd]; r["crowd_eth"] = [round(x["eth"] / 1e18, 6) for x in crowd]
        r["front_kth"] = {}
        for k in range(1, 11):
            if len(crowd) >= k: S = crowd[k - 1]["bn"] + 1; why = "kth"
            else: S = b0 + 1500; why = "deadline1500"
            t = pl.trade(B, S, minout_check=any_minout); t["why"] = why; r["front_kth"][k] = t
        # the family rule: buy at launch + 1; sell one block after the 10th crowd buy; no crowd buy by launch + 640: sell at + 640;
        # fewer than 10 by + 2400: sell at + 2400. And the follow-entry version (buy one block after the first crowd buy, same exit).
        def c10_exit():
            if not crowd or crowd[0]["bn"] > b0 + 640: return b0 + 640, "no_crowd_640"
            if len(crowd) >= 10 and crowd[9]["bn"] + 1 <= b0 + 2400: return crowd[9]["bn"] + 1, "crowd10"
            return b0 + 2400, "deadline2400"
        S, why = c10_exit()
        r["front_c10"] = {}
        for stake in (0.0058, 0.02, 0.05, 0.1):
            t = pl.trade(B, S, stake=int(stake * 1e18), minout_check=any_minout); t["why"] = why; r["front_c10"][stake] = t
        if crowd:
            Bf = crowd[0]["bn"] + 1
            Sf = crowd[9]["bn"] + 1 if len(crowd) >= 10 else b0 + 2400
            t = pl.trade(Bf, Sf, minout_check=any_minout); t["why"] = "crowd10" if len(crowd) >= 10 else "deadline2400"; r["follow_c10"] = t
        else:
            r["follow_c10"] = None
        r["pull_after_10th"] = (pl.pull_bn - crowd[9]["bn"]) if (pl.pull_bn and len(crowd) >= 10) else None
    # ---------------- follow: buy lands one block after the first real buy (>= 0.0002); sell one block after the next real buy, or at our buy + 4
    def follow(trig, hold=4):
        Bf = trig["bn"] + 1
        nx = next((x for x in buys if x["bn"] > Bf and x["eth"] >= MIN_REAL), None)
        Sf = min(nx["bn"] + 1, Bf + hold) if nx else Bf + hold
        t = pl.trade(Bf, Sf, minout_check=any_minout); t["why"] = "next_buy" if nx and nx["bn"] + 1 <= Bf + hold else f"hold{hold}"
        t["trig_off"] = trig["bn"] - b0; t["trig_cls"] = trig["cls"]; return t
    r["follow"] = follow(fr) if fr else None
    r["follow_sched"] = follow(fs) if fs else None
    # ---------------- capacity of the first scheduled buy
    if fs:
        X = fs["eth"]; f = fs["fee"]
        quote = v4math.buy_out_int(int(pl.s_eff), pl.L0, X, f)
        mo = any_minout(fs)
        s_pre, L_pre = pl.state_through(None, upto=(fs["bn"], fs["li"]))
        r["cap"] = {"X": X / 1e18, "quote_launch": quote, "fill": fs["a1"], "minout": mo, "minout_over_launch_quote": (mo / quote) if (mo and quote) else None,
                    "room_99_launch": room(int(pl.s_eff), pl.L0, X, f, int(quote * 0.99)),
                    "room_minout_total": room(int(pl.s_eff), pl.L0, X, f, mo) if mo is not None else None,
                    "room_minout_left": room(int(s_pre), L_pre, X, f, mo) if mo is not None else None,
                    "ahead_others_eth": sum(x["eth"] for x in buys if (x["bn"], x["li"]) < (fs["bn"], fs["li"])) / 1e18}
    return r


def bucket(ts):
    d = datetime.datetime.fromtimestamp(ts, datetime.timezone.utc); return f"{d:%m-%d} {d.hour // 6 * 6:02d}h"


def fam_summary(name, rows, W, kind):
    live = [r for r in rows if not r.get("dead")]
    out = {"name": name, "count": len(rows), "n_live": len(live), "launches_per_day": round(len(rows) / WINDOW_DAYS, 2),
           "by_6h": dict(sorted(collections.Counter(bucket(r["ts"]) for r in rows).items())),
           "deployers": len({r["from"] for r in rows}), "nonce": collections.Counter(r["nonce"] for r in rows).most_common(4),
           "values": collections.Counter(r["value"] for r in rows).most_common(5),
           "eth_in_per_pool": q([r.get("eth_in") for r in live], (0, .5, 1), 5)}
    fb = [r["first_buy"] for r in live if r.get("first_buy")]
    out["first_buy_any"] = {"n": len(fb), "off": q([x["off"] for x in fb]), "eth": q([x["eth"] for x in fb], nd=7), "cls": collections.Counter(x["cls"] for x in fb).most_common()}
    fr = [r["first_real"] for r in live if r.get("first_real")]
    out["first_real"] = {"n": len(fr), "frac": round(len(fr) / max(1, len(live)), 3), "off": q([x["off"] for x in fr], (.1, .5, .9)), "eth": q([x["eth"] for x in fr], nd=6),
                         "cls": collections.Counter(x["cls"] for x in fr).most_common(), "to_sel_len": collections.Counter(f"{x['to']}:{x['sel']}:{x['clen']}" for x in fr).most_common(5),
                         "n_from": len({x["from"] for x in fr if x["from"]}), "from_top": collections.Counter(x["from"] for x in fr).most_common(4),
                         "nonce0": sum(1 for x in fr if x["nonce"] == 0)}
    sc = [r["sched"] for r in live if r.get("sched")]
    out["sched"] = {"n": len(sc), "frac": round(len(sc) / max(1, len(live)), 3), "off": q([x["off"] for x in sc], (0, .1, .5, .9, 1)), "eth": q([x["eth"] for x in sc], (0, .1, .5, .9, 1), 6),
                    "routers": collections.Counter(f"{x['to']}:{x['sel']}:{x['clen']}" for x in sc).most_common(4), "n_from": len({x["from"] for x in sc}),
                    "nonce0": sum(1 for x in sc if x["nonce"] == 0), "minout_over_fill": q([x["minout_over_fill"] for x in sc if x["minout_over_fill"]], (0, .5, 1), 5)}
    pu = [r for r in live if r.get("pull")]
    out["pull"] = {"frac_3000": round(len(pu) / max(1, len(live)), 3), "n": len(pu), "off_launch": q([r["pull"]["off"] for r in pu], (0, .1, .5, .9, 1)),
                   "after_sched": q([r["pull"]["after_sched"] for r in pu if r["pull"]["after_sched"] is not None], (0, .1, .5, .9, 1)),
                   "after_sched_hist": collections.Counter(min(r["pull"]["after_sched"], 99) for r in pu if r["pull"]["after_sched"] is not None).most_common(6),
                   "pulled_with_no_sched": sum(1 for r in pu if r["sched"] is None),
                   "by_launcher": sum(1 for r in pu if r["pull"]["by_launcher"]), "full": sum(1 for r in pu if r["pull"]["full"]),
                   "to_sel": collections.Counter(f"{r['pull']['to']}:{r['pull']['sel']}" for r in pu).most_common(3)}
    # outsiders before the first scheduled buy, trap test
    def outs(r, mn=MIN_REAL / 1e18, classes=("other", "relay", "unknown", "vbot_decoy")):
        return [o for o in r["before_sched"] if o["cls"] in classes and o["eth"] >= mn]
    cls_c = collections.Counter(); sz = collections.defaultdict(list)
    for r in live:
        for o in r["before_sched"]: cls_c[o["cls"]] += 1; sz[o["cls"]].append(o["eth"])
    out["before_sched"] = {"by_class": {c: {"n": n, "pools": sum(1 for r in live if any(o["cls"] == c for o in r["before_sched"])), "eth": q(sz[c], (0, .5, 1), 7)} for c, n in cls_c.most_common()},
                           "other_from": collections.Counter(o["from"] for r in live for o in r["before_sched"] if o["cls"] == "other").most_common(6),
                           "pools_with_real_outsider": sum(1 for r in live if outs(r))}
    def tstats(rs, ref_classes):
        if not rs: return {"n": 0}
        d_o = []
        for r in rs:
            if not r.get("pull"): continue
            o = next(iter(outs(r, classes=ref_classes)), None) if ref_classes else None
            if o: d_o.append(r["pull"]["off"] - o["off"])
        ps = [r["pull"]["after_sched"] for r in rs if r.get("pull") and r["pull"]["after_sched"] is not None]
        return {"n": len(rs), "with_sched": sum(1 for r in rs if r["sched"]), "pulled_3000": sum(1 for r in rs if r.get("pull")),
                "pull_off_launch": q([r["pull"]["off"] for r in rs if r.get("pull")]), "pull_after_sched": q(ps), "pull_after_outsider": q(d_o) if ref_classes else None,
                "pulled_before_sched_or_none": sum(1 for r in rs if r.get("pull") and (r["sched"] is None or r["pull"]["after_sched"] < 0))}
    out["trap"] = {}
    for label, classes in (("other_real", ("other",)), ("relay", ("relay",)), ("any_real", ("other", "relay", "unknown", "vbot_decoy"))):
        w = [r for r in live if outs(r, classes=classes)]; wo = [r for r in live if not outs(r)]
        out["trap"][label] = {"with": tstats(w, classes), "without": tstats(wo, None)}
    out["front"] = summarize([r["front"] for r in live]); out["front_why"] = collections.Counter(r["front"].get("why") for r in live).most_common()
    out["front_dropped"] = sum(1 for r in live if r["front"].get("dropped"))
    out["front_wait"] = summarize([r["front_wait"] for r in live]); out["front_wait_W"] = W
    out["front_wait_why"] = collections.Counter(r["front_wait"].get("why") for r in live).most_common()
    out["front_hold"] = {H: summarize([r["front_hold"][H] for r in live]) for H in (20, 100, 300, 600, 900, 1200, 1500)}
    if kind == "opC":
        out["front_kth"] = {k: summarize([r["front_kth"][k] for r in live]) for k in range(1, 11)}
        out["crowd_n"] = q([len(r["crowd_offs"]) for r in live], (0, .5, 1))
        out["crowd_n_hist"] = collections.Counter(len(r["crowd_offs"]) for r in live).most_common()
        out["crowd_gaps"] = q([b - a for r in live for a, b in zip(r["crowd_offs"], r["crowd_offs"][1:])], (0, .1, .5, .9, 1))
        out["crowd_10th_off"] = q([r["crowd_offs"][9] for r in live if len(r["crowd_offs"]) >= 10], (0, .1, .5, .9, 1))
        out["crowd_eth_total"] = q([sum(r["crowd_eth"]) for r in live if r["crowd_offs"]], (0, .5, 1), 5)
        out["pull_after_10th"] = q([r["pull_after_10th"] for r in live if r.get("pull_after_10th") is not None], (0, .1, .5, .9, 1))
        out["front_c10"] = {st_: summarize([r["front_c10"][st_] for r in live]) for st_ in (0.0058, 0.02, 0.05, 0.1)}
        for st_ in (0.02, 0.05, 0.1):      # dollars scale with the stake
            d = out["front_c10"][st_]
            if d.get("n"): d["usd_trade_at_stake"] = round(d["mean"] * st_ * ETH_USD, 3)
        out["front_c10_why"] = collections.Counter(r["front_c10"][0.0058]["why"] for r in live).most_common()
        out["follow_c10"] = summarize([r.get("follow_c10") for r in live])
    out["follow"] = summarize([r.get("follow") for r in live])
    out["follow_trig_cls"] = collections.Counter(r["follow"]["trig_cls"] for r in live if r.get("follow")).most_common()
    out["follow_why"] = collections.Counter(r["follow"]["why"] for r in live if r.get("follow")).most_common()
    out["follow_sched"] = summarize([r.get("follow_sched") for r in live])
    cp = [r["cap"] for r in live if r.get("cap")]
    out["cap"] = {"n": len(cp), "minout_decoded": sum(1 for c in cp if c["minout"] is not None), "minout_over_launch_quote": q([c["minout_over_launch_quote"] for c in cp if c["minout_over_launch_quote"]], (0, .1, .5, .9, 1), 5),
                  "room_99_launch": q([c["room_99_launch"] for c in cp], (0, .1, .5, .9, 1), 5),
                  "room_minout_total": q([c["room_minout_total"] for c in cp if c["room_minout_total"] not in (None, float("inf"))], (0, .1, .5, .9, 1), 5),
                  "room_minout_left": q([c["room_minout_left"] for c in cp if c["room_minout_left"] not in (None, float("inf"))], (0, .1, .5, .9, 1), 5),
                  "ahead_others": q([c["ahead_others_eth"] for c in cp], (.5, .9, 1), 6)}
    return out


def main():
    P = load_pools(); T = load_txs(); M = load_blocks_meta(); FF = load_families()
    HP = json.load(open(os.path.join(HERE, "hist_pools.json"))); HE = json.load(open(os.path.join(HERE, "hist_events.json"))); HT = json.load(open(os.path.join(HERE, "hist_txs.json")))
    XT = json.load(open(os.path.join(HERE, "opc_txs.json")))          # the opC pools' swaps beyond the census's first 8
    T2 = dict(T); T2.update({h: dict(t, input=t.get("input")) for h, t in XT.items()})
    res = {}; allrows = {}
    for name, keys, kind, W, role in FAMS:
        if keys == "hist":
            rows = [analyse_pool(Pool(HP[pid], HE[pid], HT, M), kind, W) for pid in sorted(HP, key=lambda x: HP[x]["launch_block"])]
        else:
            pids = [p["pid"] for p in P.values() if p["known"] == "operator-A"] if keys == "operator-A" else [pid for k in keys for pid in FF[k]["pids"]]
            E = load_events(set(pids))
            rows = [analyse_pool(Pool(P[pid], E.get(pid), T2 if kind == "opC" else T, M), kind, W) for pid in pids]
        allrows[name] = rows
        with open(os.path.join(HERE, f"pools_{name}.jsonl"), "w") as fo:
            for r in rows: fo.write(json.dumps(r, default=str) + "\n")
        res[name] = fam_summary(name, rows, W, kind); res[name]["keys"] = keys; res[name]["role"] = role
    # the operator as a whole: fee 100 + fee 500 in the window, and with the Oct 7 history (per-day figures use the census window only)
    res["opC-window-all"] = fam_summary("opC-window-all", allrows["opC-fee100"] + allrows["opC-fee500"], 600, "opC"); res["opC-window-all"]["role"] = "union"
    res["opC-with-hist"] = fam_summary("opC-with-hist", allrows["opC-fee100"] + allrows["opC-fee500"] + allrows["opC-hist-oct7"], 600, "opC"); res["opC-with-hist"]["role"] = "union (per-day figures not meaningful)"
    for name, s in res.items():
        print(f"{name:16s} n {s['count']:4d} front {s['front'].get('mean')} {s['front'].get('n')} pf {s['front'].get('pulled_first')} | wait {s['front_wait'].get('mean')} pf {s['front_wait'].get('pulled_first')} | follow {s['follow'].get('mean')} n {s['follow'].get('n')} pf {s['follow'].get('pulled_first')}", flush=True)
    json.dump(res, open(os.path.join(HERE, "results.json"), "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
