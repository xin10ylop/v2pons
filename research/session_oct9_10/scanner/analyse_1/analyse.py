#!/usr/bin/env python3
"""Per-family analysis of launch / scheduled buy / pull structure and exact pricing of the front and follow rules.

Data: the census (scanner/census, 48 h to Oct 10 18:20 UTC). Pricing follows research/session_oct9_10/explore/chk/replay.py:
  * the chain's own path is rebuilt WITHOUT our relay's swaps (sender 0x2abb5653): every swap is replayed by its own price
    shift (exact-in buys add x/L to 1/sqrtP, sells add t/L to sqrtP), shifts measured on the actual chain sequence;
  * our buy (0.0058 ETH) is inserted at the END of block B (after every other tx of that block), tokens from the clean state;
  * every later swap (B < bn < S) is replayed by its own shift on top of our buy; a scheduled buy whose minOut is decodable
    (volume bot c1120e3d word 4; launchpad router 39ecce49 word 1) and whose output with us ahead falls under it is dropped;
  * our sell lands at the HEAD of block S; a pull at or before S = the whole stake lost (pull at or before B: our buy reverts,
    gas only); hook fees (family 0xae4c0cf7: h% of ETH in before the swap, h% of ETH out after) are charged on both legs;
  * gas = 2 x 104,000 x the base fee of the launch block (about 0.02 gwei); $ at 0.0058 ETH = $15.
Usage: python3 -I analyse.py  -> results.json, results.txt
"""
import sys, os, json, collections, statistics as st, math
HERE = os.path.dirname(os.path.abspath(__file__))
CENSUS = os.path.join(os.path.dirname(HERE), "census")
sys.path.insert(0, CENSUS); sys.path.insert(0, "/home/user/v2pons/src")
from load import load_pools, load_events, load_txs, load_families, load_blocks_meta
import v4math

Q96 = 1 << 96
X_STAKE = 5_800_000_000_000_000          # 0.0058 ETH
USD = 15.0 / 0.0058                       # $ per ETH implied by the $15 stake
GAS_UNITS = 104_000
MIN_REAL = 200_000_000_000_000            # 0.0002 ETH
RELAY = "0x2abb5653352f6b2f3b4f4261877cd02d9e05a957"
VBOT_ROUTER = "0x1cbaf24d53fe930fce8eff149fa797d2611da149"
LP_ROUTER = "0xf0b7eaaf868191adc00065ca13391ef436ce8faf"   # family 0xc763b179's launchpad router (39ecce49)
HOOK_TAX = "0xae4c0cf7c3feb79e0c244edbc6a3f8a3290940cc"
WINDOW_DAYS = (1791656447 - 1791483648) / 86400.0

ASSIGNED = [
    "0xc763b1795dabe2d2336eba214d16969ebc5db27f|f0e9eabf|1796|10000|200|false",
    "0xfcd182416ca91a9e88e9fe44e4f78ea3cb2c15c7|6fe958d8|68|3000|60|false",
    "0xfcd182416ca91a9e88e9fe44e4f78ea3cb2c15c7|6fe958d8|68|10000|100|false",
    "0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|883131|200|true",
]
CONTROLS = ["0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|2500|50|true", "operator-A"]

P = load_pools(); F = load_families(); T = load_txs(); BM = load_blocks_meta()


def pct(v, qs=(10, 50, 90)):
    v = sorted(v)
    if not v: return None
    return [v[min(len(v) - 1, max(0, int(round(q / 100 * (len(v) - 1)))))] for q in qs]


def word(inp, i):
    if not inp or len(inp) < 10 + 64 * (i + 1): return None
    return int(inp[10 + 64 * i: 10 + 64 * (i + 1)], 16)


def fam_pids(key):
    if key == "operator-A": return [pid for pid, p in P.items() if p["known"] == "operator-A"]
    return F[key]["pids"]


def hook_fee(p, swaps):
    """(h_buy, h_sell) fraction charged by the pool's hook outside the LP fee. Family 0xae4c0cf7: per pool from the ratio of the
    pool's ETH in to the tx value (router 0xf0b7eaaf takes 1% first, the Universal Router nothing); default 4% (receipts: 4% on
    most pools, 3% and 2% on a few, symmetric on sells)."""
    if p["hooks"] != HOOK_TAX: return 0.0, 0.0
    for s in swaps:
        t = s["txr"]
        if s["a0"] < 0 and t and t["value_wei"]:
            r = -s["a0"] / t["value_wei"]
            if t["to"] == LP_ROUTER: r /= 0.99
            elif t["to"] != "0x8876789976decbfcbbbe364623c63652db8c0904": continue
            h = round(1 - r, 2)
            if 0 <= h < 0.5: return h, h
    return 0.04, 0.04


def build(pid, ev):
    p = P[pid]; e = ev.get(pid) or {"swaps": [], "pulls": [], "adds": []}
    b0 = p["launch_block"]; ltx = p["launch_tx"]
    fee = p["fee"]
    allsw = [dict(s) for s in e["swaps"]]
    for s in allsw: s["txr"] = T.get(s["tx"])
    # clean path: shifts from the actual sequence, our relay's swaps removed
    sp_act = p["sqrt_p0"]; sp_cl = p["sqrt_p0"]; clean = []
    for s in allsw:
        if s["a0"] == 0 and s["a1"] == 0:                 # zero swaps (price pokes with no amount): no shift
            sp_act = s["sqrt_p"]; continue
        if s["a0"] < 0:
            d = Q96 / s["sqrt_p"] - Q96 / sp_act
            new = Q96 / (Q96 / sp_cl + d)
        else:
            d = s["sqrt_p"] - sp_act
            new = sp_cl + d
        sp_act = s["sqrt_p"]
        if s["sender"] == RELAY: continue
        sp_cl = new
        c = dict(s); c["sp_clean"] = new; c["d"] = d; c["in_launch"] = (s["tx"] == ltx)
        clean.append(c)
    if allsw and allsw[0]["fee"] is not None: fee = allsw[0]["fee"]
    pulls = e["pulls"]
    pull_bn = pulls[0]["bn"] if pulls else None
    pull_tx = T.get(pulls[0]["tx"]) if pulls else None
    hb, hs = hook_fee(p, clean)
    bf = BM.get(b0, (0, 20_000_000, 0))[1]
    return {"pid": pid, "p": p, "b0": b0, "fee": fee, "liq": p["liq_launch"] or 0, "sp0": p["sqrt_p0"],
            "swaps": clean, "n_relay": sum(1 for s in allsw if s["sender"] == RELAY), "pull": pull_bn, "pull_tx": pull_tx,
            "hb": hb, "hs": hs, "basefee": bf}


def state_end_of(v, B):
    """clean (sqrtP, L) at the end of block B"""
    prev = [s for s in v["swaps"] if s["bn"] <= B]
    if prev: return prev[-1]["sp_clean"], prev[-1]["liq"]
    return v["p"]["sqrt_p0"], v["liq"]


def min_out_of(s):
    t = s["txr"]
    if not t: return None, "no tx"
    inp = t.get("input") or t.get("input512")
    if t["to"] == VBOT_ROUTER and t["selector"] == "c1120e3d": return word(inp, 4), "c1120e3d word 4"
    if t["to"] == LP_ROUTER and t["selector"] == "39ecce49": return word(inp, 1), "39ecce49 word 1"
    return None, "not decodable (%s %s)" % (t["to"][:10] if t["to"] else None, t["selector"])


def trade(v, B, S, sched=None):
    """our buy at the end of block B, our sell at the head of block S. Returns a dict with ret (fraction of the stake)."""
    X = X_STAKE; fee = v["fee"]; gas = 2 * GAS_UNITS * v["basefee"]
    pull = v["pull"]
    if pull is not None and pull <= B:
        return {"exit": "pulled_before_buy", "ret": -gas / X, "B": B - v["b0"], "S": S - v["b0"]}
    spB, LB = state_end_of(v, B)
    if not LB:
        return {"exit": "no_liquidity", "ret": None}
    xin = int(X * (1 - v["hb"]))
    tokens = v4math.buy_out_int(int(spB), LB, xin, fee)
    if tokens <= 0: return {"exit": "no_output", "ret": None}
    if pull is not None and pull <= S:
        return {"exit": "pull_first", "ret": (-X - gas) / X, "B": B - v["b0"], "S": S - v["b0"], "pull": pull - v["b0"]}
    xn = xin - (xin * fee + 999_999) // 1_000_000
    s = Q96 / (Q96 / spB + xn / LB); L = LB; dropped = []
    for x in v["swaps"]:
        if x["bn"] <= B: continue
        if x["bn"] >= S: break
        L = x["liq"] or L
        if x["a0"] < 0:
            if sched is not None and x is sched:
                mo, _ = min_out_of(x)
                if mo:
                    out_with_us = v4math.buy_out_int(int(s), L, -x["a0"], fee)
                    if out_with_us < mo: dropped.append(x["bn"] - v["b0"]); continue
            s = Q96 / (Q96 / s + x["d"])
        else:
            s = s + x["d"]
    eth_out = v4math.sell_out_int(int(s), L, tokens, fee)
    eth_out = int(eth_out * (1 - v["hs"]))
    return {"exit": "sold", "ret": (eth_out - X - gas) / X, "ret_gross": (eth_out - X) / X, "B": B - v["b0"], "S": S - v["b0"], "dropped": dropped}


def capacity(v, sched):
    """ETH (tx-side, before hook fee) that can sit ahead of the scheduled buy: (a) with its real minOut on the clean pre-state
    when decodable; (b) assuming minOut = 0.99 x its launch-state quote, measured from the launch state."""
    fee = v["fee"]; Y = -sched["a0"]
    out = {}
    def ahead_out(sp, L, Z):
        zn = Z - (Z * fee + 999_999) // 1_000_000
        s1 = int(Q96 / (Q96 / sp + zn / L)) if Z > 0 else sp
        return v4math.buy_out_int(s1, L, Y, fee)
    def solve(sp, L, target):
        if ahead_out(sp, L, 0) < target: return 0
        lo, hi = 0, 10 ** 15
        while ahead_out(sp, L, hi) >= target and hi < 10 ** 22: hi *= 2
        for _ in range(80):
            mid = (lo + hi) // 2
            if ahead_out(sp, L, mid) >= target: lo = mid
            else: hi = mid
        return lo
    L0 = v["liq"]; sp0 = v["p"]["sqrt_p0"]
    if L0:
        q = v4math.buy_out_int(sp0, L0, Y, fee)
        z = solve(sp0, L0, int(q * 0.99))
        out["assumed_99"] = z / (1 - v["hb"]) / 1e18
    mo, how = min_out_of(sched)
    out["minout_src"] = how
    if mo is not None:
        if mo <= 1: out["real"] = float("inf")          # minOut 0 or 1 wei: no slippage limit at all
        else:
            pre = [s for s in v["swaps"] if (s["bn"], s["li"]) < (sched["bn"], sched["li"])]
            sp, L = (pre[-1]["sp_clean"], pre[-1]["liq"]) if pre else (sp0, L0)
            if L:
                z = solve(int(sp), L, mo)
                ahead_now = sum(-s["a0"] for s in pre if s["a0"] < 0 and not s["in_launch"])
                out["real"] = z / (1 - v["hb"]) / 1e18; out["ahead_already"] = ahead_now / 1e18
                out["slack_vs_minout"] = v4math.buy_out_int(int(sp), L, Y, fee) / mo
    return out


def summarize(rs, launches_per_day, count):
    v = [r["ret"] for r in rs if r.get("ret") is not None]
    ex = collections.Counter(r["exit"] for r in rs)
    if not v: return {"n": 0, "exits": dict(ex)}
    pf = sum(1 for r in rs if r["exit"] == "pull_first")
    m = st.mean(v)
    tpd = launches_per_day * len(v) / count
    return {"n": len(v), "mean": m, "median": st.median(v), "win": sum(1 for a in v if a > 0) / len(v), "pulled_first": pf,
            "usd_trade": m * 15.0, "trades_day": tpd, "usd_day": m * 15.0 * tpd, "min": min(v), "max": max(v), "exits": dict(ex)}


def analyse(key, sched_pred=None, label=None):
    pids = fam_pids(key); ev = load_events(set(pids))
    V = [build(pid, ev) for pid in pids]
    count = len(V)
    lbs = sorted(v["b0"] for v in V)
    lpd = count / WINDOW_DAYS
    res = {"key": key, "label": label, "count": count, "launches_per_day": lpd,
           "active_blocks": [lbs[0], lbs[-1]], "active_days": (lbs[-1] - lbs[0]) * 0.1026 / 86400}
    # launcher
    lf = collections.Counter(v["p"]["launch_from"] for v in V)
    res["launcher"] = {"n_senders": len(lf), "top_senders": lf.most_common(3), "nonce_p10_50_90": pct([v["p"]["launch_nonce"] for v in V]),
                       "values_eth": sorted(set(v["p"]["launch_value_eth"] for v in V))[:5], "to": V[0]["p"]["launch_to"], "selector": V[0]["p"]["selector"],
                       "calldata_len": V[0]["p"]["calldata_len"], "hooks": collections.Counter(v["p"]["hooks"] for v in V).most_common(2),
                       "liq_launch_p10_50_90": pct([v["liq"] for v in V]), "sqrt_p0_distinct": len(set(v["p"]["sqrt_p0"] for v in V)),
                       "buy_in_launch_tx": sum(1 for v in V if any(s["in_launch"] and s["a0"] < 0 for s in v["swaps"]))}
    # first non-launch buy (any size), and first real (>= 0.0002)
    fb_rows = []; fr_rows = []
    for v in V:
        buys = [s for s in v["swaps"] if s["a0"] < 0 and not s["in_launch"]]
        v["buys"] = buys
        if buys: fb_rows.append((v, buys[0]))
        real = [s for s in buys if -s["a0"] >= MIN_REAL]
        v["first_real"] = real[0] if real else None
        if real: fr_rows.append((v, real[0]))
    def desc(rows):
        if not rows: return None
        to = collections.Counter((s["txr"]["to"] if s["txr"] else "?", s["txr"]["selector"] if s["txr"] else "?") for _, s in rows)
        fr = collections.Counter(s["txr"]["from"] if s["txr"] else "?" for _, s in rows)
        nonces = [s["txr"]["nonce"] for _, s in rows if s["txr"]]
        return {"pools": len(rows), "frac_pools": len(rows) / count, "offset_p10_50_90": pct([s["bn"] - v["b0"] for v, s in rows]),
                "eth_p10_50_90": [round(x / 1e18, 6) for x in pct([-s["a0"] for _, s in rows])], "to_selector_top": to.most_common(4),
                "n_from": len(fr), "from_top": fr.most_common(4), "from_nonce_p10_50_90": pct(nonces)}
    res["first_buy_any"] = desc(fb_rows); res["first_buy_real"] = desc(fr_rows)
    # the scheduled buy: the dominant (to, selector) of the first real buys unless given
    if sched_pred is None:
        dom = res["first_buy_real"]["to_selector_top"][0][0] if fr_rows else None
        sched_pred = (lambda s, dom=dom: s["txr"] is not None and (s["txr"]["to"], s["txr"]["selector"]) == dom and -s["a0"] >= MIN_REAL)
        res["sched_def"] = "first buy >= 0.0002 ETH through the dominant first-real-buy (to, selector) %s" % (dom,)
    sc_rows = []
    for v in V:
        v["sched"] = next((s for s in v["buys"] if sched_pred(s)), None)
        if v["sched"]: sc_rows.append((v, v["sched"]))
    res["sched_buy"] = desc(sc_rows)
    # pulls
    pulled = [v for v in V if v["pull"] is not None]
    who = collections.Counter()
    for v in pulled:
        t = v["pull_tx"]
        who[("launch wallet" if t and t["from"] == v["p"]["launch_from"] else (t["from"] if t else "?"), t["to"] if t else "?", t["selector"] if t else "?")] += 1
    res["pull"] = {"frac_pulled_3000": len(pulled) / count, "n_pulled": len(pulled), "from_launch_p10_50_90": pct([v["pull"] - v["b0"] for v in pulled]),
                   "from_sched_p10_50_90": pct([v["pull"] - v["sched"]["bn"] for v in pulled if v["sched"]]),
                   "from_first_real_p10_50_90": pct([v["pull"] - v["first_real"]["bn"] for v in pulled if v["first_real"]]),
                   "who_top": [[list(k), n] for k, n in who.most_common(4)]}
    # outsiders before the scheduled buy (non-launch, non-relay buys not matching the scheduled predicate, before it)
    with_out = []; without = []; sizes = []
    for v in V:
        lim = (v["sched"]["bn"], v["sched"]["li"]) if v["sched"] else (v["b0"] + 3001, 0)
        outs = [s for s in v["buys"] if (s["bn"], s["li"]) < lim and not sched_pred(s)]
        real_outs = [s for s in outs if -s["a0"] >= MIN_REAL]
        v["outs"] = outs; v["real_outs"] = real_outs
        sizes += [-s["a0"] for s in outs]
        (with_out if real_outs else without).append(v)
    def pull_after(vs, ref):
        d = [v["pull"] - ref(v) for v in vs if v["pull"] is not None and ref(v) is not None]
        return {"pools": len(vs), "pulled": sum(1 for v in vs if v["pull"] is not None), "delay_p10_50_90": pct(d)}
    oc = collections.Counter((s["txr"]["to"] if s["txr"] else "?", s["txr"]["from"] if s["txr"] else "?") for v in V for s in v["outs"])
    res["outsiders"] = {"pools_any": sum(1 for v in V if v["outs"]), "pools_real_ge_0.0002": len(with_out),
                        "size_eth_p10_50_90_max": ([round(x / 1e18, 7) for x in pct(sizes)] + [round(max(sizes) / 1e18, 6)]) if sizes else None,
                        "top_to_from": oc.most_common(5),
                        "trap_with_real_outsider_pull_after_outsider": pull_after(with_out, lambda v: v["real_outs"][0]["bn"]),
                        "trap_with_real_outsider_pull_from_launch": pull_after(with_out, lambda v: v["b0"]),
                        "trap_without_pull_from_launch": pull_after(without, lambda v: v["b0"]),
                        "trap_without_pull_after_sched": pull_after(without, lambda v: v["sched"]["bn"] if v["sched"] else None)}
    # front: buy at launch+1 (end of block), sell at the head of sched+1, or launch+20 without a scheduled buy
    fr = []; late = 0
    for v in V:
        B = v["b0"] + 1
        if v["sched"] and v["sched"]["bn"] <= B: late += 1; fr.append({"exit": "late_sched_at_or_before_B", "ret": None}); continue
        S = v["sched"]["bn"] + 1 if v["sched"] and v["sched"]["bn"] + 1 <= v["b0"] + 3000 else v["b0"] + 20
        r = trade(v, B, S, sched=v["sched"]); r["pid"] = v["pid"]; fr.append(r)
    res["front"] = summarize(fr, lpd, count); res["front"]["late"] = late
    res["front_with_sched"] = summarize([r for r, v in zip(fr, V) if v["sched"]], lpd, count)
    res["front_without_sched"] = summarize([r for r, v in zip(fr, V) if not v["sched"]], lpd, count)
    res["front"]["dropped_sched"] = sum(1 for r in fr if r.get("dropped"))
    # follow: buy one block after the first real buy, sell one block after the next real buy behind ours or at our buy + 4
    fo = []
    for v in V:
        if not v["first_real"]: fo.append({"exit": "no_trigger", "ret": None}); continue
        B = v["first_real"]["bn"] + 1
        nb = next((s for s in v["buys"] if s["bn"] > B and -s["a0"] >= MIN_REAL), None)
        S = min(nb["bn"] + 1, B + 4) if nb else B + 4
        r = trade(v, B, S, sched=v["sched"]); r["pid"] = v["pid"]; fo.append(r)
    res["follow"] = summarize(fo, lpd, count)
    # capacity
    caps = [capacity(v, v["sched"]) for v in V if v["sched"]]
    a99 = [c["assumed_99"] for c in caps if "assumed_99" in c]
    real = [c["real"] for c in caps if "real" in c]
    res["capacity"] = {"pools": len(caps), "assumed_99_eth_p10_50_90": [round(x, 5) for x in pct(a99)] if a99 else None,
                       "real_minout_eth_p10_50_90": [round(x, 5) if x != float("inf") else "unlimited" for x in pct(real)] if real else None,
                       "real_minout_unlimited": sum(1 for x in real if x == float("inf")), "real_minout_pools": len(real),
                       "slack_vs_minout_p10_50_90": [round(x, 4) for x in pct([c["slack_vs_minout"] for c in caps if "slack_vs_minout" in c])] if any("slack_vs_minout" in c for c in caps) else None,
                       "minout_src": collections.Counter(c["minout_src"] for c in caps).most_common(3)}
    res["hook_fee"] = collections.Counter((v["hb"], v["hs"]) for v in V).most_common(4)
    res["relay_swaps_removed"] = sum(v["n_relay"] for v in V)
    res["_front_rows"] = fr; res["_follow_rows"] = fo
    return res


def fmt(s):
    if not s or not s.get("n"): return "n 0 %s" % (s.get("exits") if s else "")
    return ("n %d mean %+.2f%% median %+.2f%% win %.0f%% pulled-first %d  $%.3f/trade  %.1f trades/day  $%.1f/day  exits %s" %
            (s["n"], 100 * s["mean"], 100 * s["median"], 100 * s["win"], s["pulled_first"], s["usd_trade"], s["trades_day"], s["usd_day"], s["exits"]))


def main():
    out = []
    vbot_sched = lambda s: s["txr"] is not None and s["txr"]["to"] == VBOT_ROUTER and s["txr"]["selector"] == "c1120e3d"
    jobs = [(k, None, "assigned") for k in ASSIGNED] + [(CONTROLS[0], vbot_sched, "control vbot-v2.433"), (CONTROLS[1], None, "control operator-A")]
    lines = []
    for key, pred, label in jobs:
        r = analyse(key, pred, label)
        out.append(r)
        lines.append("=" * 100); lines.append("%s  [%s]  count %d  launches/day %.1f" % (key, label, r["count"], r["launches_per_day"]))
        for k in ("launcher", "first_buy_any", "first_buy_real", "sched_def", "sched_buy", "pull", "outsiders", "capacity", "hook_fee", "relay_swaps_removed"):
            if k in r: lines.append("  %s: %s" % (k, json.dumps(r[k], default=str)))
        lines.append("  FRONT : " + fmt(r["front"]) + "  late %d dropped %d" % (r["front"].get("late", 0), r["front"].get("dropped_sched", 0)))
        lines.append("    front, pools with a scheduled buy   : " + fmt(r["front_with_sched"]))
        lines.append("    front, pools without (sell at +20)  : " + fmt(r["front_without_sched"]))
        lines.append("  FOLLOW: " + fmt(r["follow"]))
    txt = "\n".join(lines); print(txt)
    open(os.path.join(HERE, "results.txt"), "w").write(txt + "\n")
    json.dump(out, open(os.path.join(HERE, "results.json"), "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
