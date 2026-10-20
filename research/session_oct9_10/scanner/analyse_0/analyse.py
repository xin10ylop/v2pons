"""Per-family analysis of four launch families (census of Oct 8 18:20 - Oct 10 18:20 UTC): launcher, first buys, the scheduled buy,
pulls, outsiders and the trap test, and the exact replay of the front and follow rules (plus variants), and the scheduled buy's room.
Writes pools_<n>.jsonl (one row per pool) and results.json. Run: python3 -I analyse.py"""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common import *

FAMS = json.load(open(os.path.join(HERE, "families_in.json")))
CROWD3 = "0xd6d35b56237a05afd4cd7e441226fefc3f78c4e6"


def sched_pred(name):
    if name in ("vbot-v2.433", "vbot-other"):
        return lambda x: x["to"] == VBOT_ROUTER and x["sel"] == "c1120e3d"
    if name == "fee100-2276":
        return lambda x: x["to"] == CROWD3 and x["sel"] == "e6cb474f"
    if name == "pm-init-500":
        return lambda x: x["sel"] == "7169b574"
    raise ValueError(name)


def sched_minout(name):
    """the scheduled buy's own minOut when its calldata says it (None = unknown)"""
    def f(x):
        if x["to"] == VBOT_ROUTER and x["sel"] == "c1120e3d" and x["input"]:
            return int(x["input"][10 + 64 * 4: 10 + 64 * 5], 16)
        if x["to"] == CROWD3 and x["sel"] == "e6cb474f" and x["input"]:
            return int(x["input"][10 + 64 * 3: 10 + 64 * 4], 16)            # word 3 (0 on all 717 seen)
        if x["sel"] == "7169b574" and x["input"] and len(x["input"]) >= 10 + 64 * 8 and int(x["input"][10 + 64 * 8: 10 + 64 * 9], 16) == 1:
            return int(x["input"][10 + 64 * 7: 10 + 64 * 8], 16)            # word 7 (0 on all 1,092 772-byte calls seen)
        return None
    return f


def subfam(name, pl):
    p = pl.p
    if name == "vbot-other":
        return {3.0: "v3.0", 5.0: "v5.0"}.get(round(p["launch_value_eth"], 6), "v0")
    if name == "pm-init-500":
        return "one-sided" if pl.e["adds"] and pl.e["adds"][0]["lo"] != -887272 else "full-range"
    if name == "vbot-v2.433":
        return "before-us" if p["launch_ts"] < 1791624420 else "while-we-traded"     # Oct 10 09:07 UTC = 1791624420
    return "all"


def classify(x, is_sched, vbot):
    if x["relay"]: return "relay"
    if x["to"] is None: return "unknown"
    if is_sched(x): return "sched"
    if x["from"] == DUST: return "dust"
    if x["to"] in VBOT_DECOY_ROUTERS: return "vbot_decoy"
    return "other"


def s_after_int(s, L, eth, fee):
    x = net_in(eth, fee)
    num = L * s; den = L + (x * s) // Q96
    return (num + den - 1) // den


def room(s, L, X, fee, mo):
    """the ETH that can be bought ahead (from price s) before the X-wei buy's output falls under mo"""
    if mo is None: return None
    if mo == 0: return float("inf")
    if v4math.buy_out_int(s, L, X, fee) < mo: return 0.0
    lo, hi = 0, int(50e18)
    while hi - lo > int(1e12):
        m = (lo + hi) // 2
        if v4math.buy_out_int(s_after_int(s, L, m, fee), L, X, fee) >= mo: lo = m
        else: hi = m
    return lo / 1e18


def analyse_pool(pl, name, is_sched, mo_of):
    p = pl.p; live = pl.live_block; b0 = pl.b0
    r = {"pid": pl.pid, "b0": b0, "ts": p["launch_ts"], "live": live, "live_off": (live - b0) if live is not None else None, "sub": subfam(name, pl),
         "from": p["launch_from"], "nonce": p["launch_nonce"], "L0": pl.L0, "fee": pl.fee, "n_swaps": len(pl.seq)}
    if live is None or pl.L0 <= 0:
        r["dead"] = True; return r
    buys = pl.buys()
    for x in buys: x["cls"] = classify(x, is_sched, False)
    fb = buys[0] if buys else None
    r["first_buy"] = ({"off": fb["bn"] - live, "eth": fb["eth"] / 1e18, "to": fb["to"], "from": fb["from"], "sel": fb["sel"], "cls": fb["cls"]} if fb else None)
    fr = next((x for x in buys if x["eth"] >= MIN_REAL), None)
    r["first_real"] = ({"off": fr["bn"] - live, "eth": fr["eth"] / 1e18, "to": fr["to"], "from": fr["from"], "sel": fr["sel"], "cls": fr["cls"]} if fr else None)
    fs = next((x for x in buys if x["cls"] == "sched"), None)
    unknown_before = any(x["cls"] == "unknown" for x in buys if fs is None or (x["bn"], x["li"]) < (fs["bn"], fs["li"]))
    r["sched_unknown"] = fs is None and unknown_before
    scheds = [x for x in buys if x["cls"] == "sched"]
    if fs:
        mo = mo_of(fs)
        r["sched"] = {"off": fs["bn"] - live, "eth": fs["eth"] / 1e18, "to": fs["to"], "from": fs["from"], "minout": mo, "n_known": len(scheds),
                      "same_block": sum(1 for x in scheds if x["bn"] == fs["bn"]), "eth_same_block": sum(x["eth"] for x in scheds if x["bn"] == fs["bn"]) / 1e18,
                      "offs_known": [x["bn"] - live for x in scheds][:8]}
    else:
        r["sched"] = None
    # outsiders before the first scheduled buy (or before the deadline +20 when there is none)
    lim = (fs["bn"], fs["li"]) if fs else (live + 20, 10**9)
    outs = [x for x in buys if (x["bn"], x["li"]) < lim and x["cls"] != "sched"]
    r["before_sched"] = [{"off": x["bn"] - live, "eth": x["eth"] / 1e18, "cls": x["cls"], "to": x["to"], "from": x["from"]} for x in outs]
    # relay (our real buys)
    rel = [x for x in pl.seq if x["relay"] and x["buy"]]
    r["relay_buy_off"] = (rel[0]["bn"] - live) if rel else None
    # pull
    if pl.pull:
        r["pull"] = {"off": pl.pull_bn - live, "off_b0": pl.pull_bn - b0, "from": p["first_pull_from"], "to": p["first_pull_to"], "sel": p["first_pull_selector"],
                     "by_launcher": p["first_pull_from"] == p["launch_from"], "full": -pl.pull["dl"] >= pl.L0 * 0.99,
                     "after_sched": (pl.pull_bn - fs["bn"]) if fs else None}
    else:
        r["pull"] = None
    # ---- rules
    B = live + 1
    if fs is None or fs["bn"] > live + 20:
        S = live + 20; why = "deadline"
    else:
        S = max(fs["bn"] + 1, B + 1); why = "sched" if fs["bn"] > B else "sched_not_ahead"
    t = pl.trade(B, S, minout_check=mo_of); t["why"] = why; r["front"] = t
    # front, waiting for the scheduled buy up to the family's horizon (set by main via FRONT_WAIT)
    W = FRONT_WAIT[name]
    if fs is None or fs["bn"] > live + W:
        S2 = live + W; why2 = "deadline"
    else:
        S2 = max(fs["bn"] + 1, B + 1); why2 = "sched" if fs["bn"] > B else "sched_not_ahead"
    t2 = pl.trade(B, S2, minout_check=mo_of); t2["why"] = why2; r["front_wait"] = t2
    # front, fixed holds
    r["front_hold"] = {H: pl.trade(B, live + H, minout_check=mo_of) for H in (10, 20, 50, 100, 150, 200, 300)}
    # follow: first real buy -> buy at +1; sell one block after the next real buy, or at our buy + 4
    if fr:
        Bf = fr["bn"] + 1
        nx = next((x for x in buys if x["bn"] > Bf and x["eth"] >= MIN_REAL), None)
        Sf = min(nx["bn"] + 1, Bf + 4) if nx else Bf + 4
        tf = pl.trade(Bf, Sf, minout_check=mo_of); tf["why"] = "next_buy" if nx and nx["bn"] + 1 <= Bf + 4 else "hold4"; tf["trig_off"] = fr["bn"] - live
        tf["trig_cls"] = fr["cls"]; r["follow"] = tf
    else:
        r["follow"] = None
    # follow variants on the scheduled buy: hold 4 and hold 40 (sell one block after the next real buy)
    if fs:
        Bf = fs["bn"] + 1
        nx = next((x for x in buys if x["bn"] > Bf and x["eth"] >= MIN_REAL), None)
        r["follow_sched"] = pl.trade(Bf, min(nx["bn"] + 1, Bf + 4) if nx else Bf + 4, minout_check=mo_of)
        r["follow_sched_h40"] = pl.trade(Bf, min(nx["bn"] + 1, Bf + 40) if nx else Bf + 40, minout_check=mo_of)
    # ---- capacity of the first scheduled buy
    if fs:
        X = fs["eth"]; f = fs["fee"]
        quote = v4math.buy_out_int(int(pl.s_eff), pl.L0, X, f)
        mo = mo_of(fs)
        mo_used = mo if mo is not None else int(quote * 0.99)
        s_pre, L_pre = pl.state_through(fs["bn"] - 1)
        # swaps in fs's own block before it (not relay)
        for x in pl.seq:
            if x["bn"] == fs["bn"] and x["li"] < fs["li"] and not x["relay"]:
                s_pre = Pool._apply(s_pre, x); L_pre = x["liq"]
        r["cap"] = {"X": X / 1e18, "quote": quote, "minout": mo, "minout_assumed": mo is None, "minout_over_quote": (mo / quote) if (mo and quote) else None,
                    "room_total": room(int(pl.s_eff), pl.L0, X, f, mo_used), "room_left": room(int(s_pre), L_pre, X, f, mo_used),
                    "ahead_others_eth": sum(x["eth"] for x in buys if (x["bn"], x["li"]) < (fs["bn"], fs["li"])) / 1e18}
    return r


FRONT_WAIT = {}


def pct_str(v, qs=(.1, .5, .9), nd=4):
    a = q([round(x, nd) if isinstance(x, float) else x for x in v if x is not None], qs)
    return a


def fam_summary(name, key, rows, fam_row):
    out = {"key": key, "name": name, "count": len(rows)}
    live = [r for r in rows if not r.get("dead")]
    out["n_live"] = len(live); out["n_dead"] = len(rows) - len(live)
    out["launches_per_day"] = round(len(rows) / WINDOW_DAYS, 1)
    days = collections.Counter(time_bucket(r["ts"]) for r in rows); out["by_6h"] = dict(sorted(days.items()))
    out["live_off"] = pct_str([r["live_off"] for r in live], (0, .1, .5, .9, 1))
    out["deployers"] = len({r["from"] for r in rows}); out["nonce"] = collections.Counter(r["nonce"] for r in rows).most_common(5)
    # first buys
    fb = [r["first_buy"] for r in live if r.get("first_buy")]
    out["first_buy"] = {"n": len(fb), "frac": round(len(fb) / max(1, len(live)), 3), "off": pct_str([x["off"] for x in fb]), "eth": pct_str([x["eth"] for x in fb], nd=7),
                        "cls": collections.Counter(x["cls"] for x in fb).most_common(), "to": collections.Counter(x["to"] for x in fb).most_common(5),
                        "n_from": len({x["from"] for x in fb if x["from"]})}
    fr = [r["first_real"] for r in live if r.get("first_real")]
    out["first_real"] = {"n": len(fr), "frac": round(len(fr) / max(1, len(live)), 3), "off": pct_str([x["off"] for x in fr]), "eth": pct_str([x["eth"] for x in fr], nd=7),
                         "cls": collections.Counter(x["cls"] for x in fr).most_common(), "to_sel": collections.Counter(f"{x['to']}:{x['sel']}" for x in fr).most_common(6),
                         "n_from": len({x["from"] for x in fr if x["from"]})}
    sc = [r["sched"] for r in live if r.get("sched")]
    out["sched"] = {"n": len(sc), "frac": round(len(sc) / max(1, len(live)), 3), "unknown_beyond_8": sum(1 for r in live if r.get("sched_unknown")),
                    "off": pct_str([x["off"] for x in sc], (0, .05, .1, .25, .5, .75, .9, .95, 1)), "eth": pct_str([x["eth"] for x in sc], (0, .1, .5, .9, 1), 6),
                    "eth_same_block": pct_str([x["eth_same_block"] for x in sc], (.1, .5, .9), 6), "n_same_block": pct_str([x["same_block"] for x in sc]),
                    "routers": collections.Counter(x["to"] for x in sc).most_common(6), "n_from": len({x["from"] for x in sc}), "n": len(sc),
                    "top_from": collections.Counter(x["from"] for x in sc).most_common(3)}
    # pulls
    pu = [r for r in live if r.get("pull")]
    out["pull"] = {"frac_3000": round(len(pu) / max(1, len(live)), 3), "off_live": pct_str([r["pull"]["off"] for r in pu], (0, .1, .5, .9, 1)),
                   "after_sched": pct_str([r["pull"]["after_sched"] for r in pu if r["pull"]["after_sched"] is not None], (0, .05, .1, .5, .9, 1)),
                   "after_sched_hist": collections.Counter(min(r["pull"]["after_sched"], 99) for r in pu if r["pull"]["after_sched"] is not None).most_common(8),
                   "before_sched": sum(1 for r in pu if r["pull"]["after_sched"] is not None and r["pull"]["after_sched"] < 0) + sum(1 for r in pu if r["sched"] is None),
                   "by_launcher": sum(1 for r in pu if r["pull"]["by_launcher"]), "full": sum(1 for r in pu if r["pull"]["full"]),
                   "to_sel": collections.Counter(f"{r['pull']['to']}:{r['pull']['sel']}" for r in pu).most_common(3)}
    # outsiders before the first scheduled buy
    def has_out(r, classes, mn=0):
        return any(o["cls"] in classes and o["eth"] >= mn for o in r["before_sched"])
    cls_c = collections.Counter(); sz = collections.defaultdict(list)
    for r in live:
        for o in r["before_sched"]:
            cls_c[o["cls"]] += 1; sz[o["cls"]].append(o["eth"])
    out["before_sched"] = {"by_class": {c: {"n": n, "pools": sum(1 for r in live if any(o["cls"] == c for o in r["before_sched"])),
                                            "eth": pct_str(sz[c], (0, .5, .9, 1), 7)} for c, n in cls_c.most_common()},
                           "other_routers": collections.Counter(o["to"] for r in live for o in r["before_sched"] if o["cls"] == "other").most_common(6),
                           "other_from": collections.Counter(o["from"] for r in live for o in r["before_sched"] if o["cls"] == "other").most_common(6)}
    # trap test: pools with a real-size outsider (other/relay/unknown, >= 0.0002) before the scheduled buy vs pools without
    tt = {}
    for label, classes in (("other_real", {"other"}), ("relay", {"relay"}), ("any_real", {"other", "relay", "vbot_decoy", "unknown"})):
        w = [r for r in live if has_out(r, classes, 0.0002)]
        wo = [r for r in live if not has_out(r, {"other", "relay", "vbot_decoy", "unknown"}, 0.0002)]
        def stats(rs, ref):
            n = len(rs)
            if not n: return {"n": 0}
            pb = [r for r in rs if r.get("pull") and (r["sched"] is None or r["pull"]["after_sched"] is None or r["pull"]["after_sched"] < 0)]
            d_s = [r["pull"]["after_sched"] for r in rs if r.get("pull") and r["pull"]["after_sched"] is not None]
            d_o = []
            for r in rs:
                if not r.get("pull"): continue
                o = next((o for o in r["before_sched"] if o["cls"] in classes and o["eth"] >= 0.0002), None) if ref else None
                if o: d_o.append(r["pull"]["off"] - o["off"])
            return {"n": n, "pulled_3000": round(sum(1 for r in rs if r.get("pull")) / n, 3), "pulled_before_sched": len(pb),
                    "pull_off_live": pct_str([r["pull"]["off"] for r in rs if r.get("pull")]), "pull_after_sched": pct_str(d_s, (.1, .5, .9)),
                    "pull_within_20_of_sched": round(sum(1 for d in d_s if 0 <= d <= 20) / n, 3), "pull_after_outsider": pct_str(d_o, (.1, .5, .9)) if ref else None}
        tt[label] = {"with": stats(w, True), "without": stats(wo, False)}
    out["trap"] = tt
    # rules
    def ss(sel):
        return summarize([sel(r) for r in live if sel(r) is not None])
    out["front"] = ss(lambda r: r["front"])
    out["front_why"] = collections.Counter(r["front"].get("why") for r in live).most_common()
    out["front_dropped"] = sum(1 for r in live if r["front"].get("dropped"))
    out["front_wait"] = ss(lambda r: r["front_wait"]); out["front_wait_W"] = FRONT_WAIT[name]
    out["front_wait_why"] = collections.Counter(r["front_wait"].get("why") for r in live).most_common()
    out["front_hold"] = {H: ss(lambda r, H=H: r["front_hold"][H]) for H in (10, 20, 50, 100, 150, 200, 300)}
    out["follow"] = ss(lambda r: r.get("follow"))
    out["follow_trig_cls"] = collections.Counter(r["follow"]["trig_cls"] for r in live if r.get("follow")).most_common()
    out["follow_why"] = collections.Counter(r["follow"]["why"] for r in live if r.get("follow")).most_common()
    out["follow_sched"] = ss(lambda r: r.get("follow_sched"))
    out["follow_sched_h40"] = ss(lambda r: r.get("follow_sched_h40"))
    # by sub-family
    subs = collections.Counter(r["sub"] for r in live)
    if len(subs) > 1:
        out["by_sub"] = {}
        for sname in subs:
            rs = [r for r in live if r["sub"] == sname]
            out["by_sub"][sname] = {"n": len(rs), "front": summarize([r["front"] for r in rs]), "front_wait": summarize([r["front_wait"] for r in rs]),
                                    "follow": summarize([r["follow"] for r in rs if r.get("follow")]),
                                    "sched_off": pct_str([r["sched"]["off"] for r in rs if r.get("sched")]),
                                    "sched_eth": pct_str([r["sched"]["eth"] for r in rs if r.get("sched")], nd=6),
                                    "pull_frac": round(sum(1 for r in rs if r.get("pull")) / len(rs), 3),
                                    "pull_after_sched": pct_str([r["pull"]["after_sched"] for r in rs if r.get("pull") and r["pull"]["after_sched"] is not None], (0, .1, .5, .9)),
                                    "front_hold": {H: summarize([r["front_hold"][H] for r in rs]) for H in (20, 50, 100, 200)}}
            for k2 in ("front", "front_wait", "follow"):
                out["by_sub"][sname][k2] = {kk: out["by_sub"][sname][k2].get(kk) for kk in ("n", "mean", "median", "win", "pulled_first", "usd_trade", "usd_day", "exits")}
    # capacity
    cp = [r["cap"] for r in live if r.get("cap")]
    rt = [c["room_total"] for c in cp if c["room_total"] is not None]; rl = [c["room_left"] for c in cp if c["room_left"] is not None]
    out["cap"] = {"n": len(cp), "minout_assumed": sum(1 for c in cp if c["minout_assumed"]), "minout_zero": sum(1 for c in cp if c["minout"] == 0),
                  "minout_over_quote": pct_str([c["minout_over_quote"] for c in cp if c["minout_over_quote"]], (0, .1, .5, .9, 1), 6),
                  "room_total": pct_str([x for x in rt if x != float("inf")], (0, .1, .5, .9, 1), 5), "room_left": pct_str([x for x in rl if x != float("inf")], (0, .1, .5, .9, 1), 5),
                  "room_inf": sum(1 for x in rt if x == float("inf")), "room_left_under_stake": sum(1 for x in rl if x < 0.0058),
                  "ahead_others": pct_str([c["ahead_others_eth"] for c in cp], (.5, .9, 1), 6)}
    return out


def time_bucket(ts):
    import datetime
    d = datetime.datetime.utcfromtimestamp(ts)
    return f"{d:%m-%d} {d.hour // 6 * 6:02d}h"


def main():
    P = load_pools(); T = load_txs(); M = load_blocks_meta(); FF = load_families()
    names = {"vbot-v2.433": "vbot-v2.433", "vbot-other": "vbot-other"}
    res = {}
    for i, f in enumerate(FAMS):
        key = f["key"]; name = f.get("name") or names.get(f["known"])
        FRONT_WAIT[name] = f.get("wait", 20)
        pids = FF[key]["pids"]; E = load_events(set(pids))
        is_sched = sched_pred(name); mo_of = sched_minout(name)
        rows = []
        for pid in pids:
            pl = Pool(P[pid], E.get(pid), T, M)
            rows.append(analyse_pool(pl, name, is_sched, mo_of))
        with open(os.path.join(HERE, f"pools_{i}.jsonl"), "w") as fo:
            for r in rows: fo.write(json.dumps(r, default=str) + "\n")
        res[key] = fam_summary(name, key, rows, FF[key])
        print(name, json.dumps({k: res[key][k] for k in ("count", "front", "front_wait", "follow")}, default=str)[:1500], flush=True)
    json.dump(res, open(os.path.join(HERE, "results.json"), "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
