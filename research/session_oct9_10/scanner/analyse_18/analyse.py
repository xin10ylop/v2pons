"""analyse_18: the four assigned families (+ the wider launcher groups they belong to) and the controls (v2.433, operator A), priced with
common18.Pool (the exact replay of explore/chk/replay.py on the census). Writes stats.json."""
import sys, os, json, statistics as st, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common18 import *  # noqa

K = json.load(open(os.path.join(HERE, "keys.json")))
P = load_pools(); F = load_families(); T = load_txs(); M = load_blocks_meta()
AUD = json.load(open("/home/user/v2pons/research/session_oct9_10/front_audit/full_audit.json"))
groups = {k: F[k]["pids"] for k in K}
groups["WIDER all 7fde822e launches (imortal.buzz launchpad, every launch contract)"] = [p["pid"] for p in P.values() if p["selector"] == "7fde822e"]
groups["WIDER deployer 0x06cb3a68 (all its pools)"] = [p["pid"] for p in P.values() if p["launch_from"] == "0x06cb3a6841c92525e7a1998328e7c9d37e98d937"]
groups["WIDER all 0x815542e8 / 7c33638d launches (openlaunch.lol)"] = [p["pid"] for p in P.values() if p["launch_to"] == "0x815542e8b392389a1389e22e588e4b62a67ade72"]
V = [p["pid"] for p in P.values() if p["known"] == "vbot-v2.433"]
A = [p["pid"] for p in P.values() if p["known"] == "operator-A"]
E = load_events(set(x for v in groups.values() for x in v) | set(V) | set(A))
POOL = {}


def pool(pid):
    if pid not in POOL: POOL[pid] = Pool(P[pid], E.get(pid), T, M)
    return POOL[pid]


def is_bot(x): return x["to"] == VBOT_ROUTER and x["sel"] == "c1120e3d"


def real_buys(pl, after=None):
    return [x for x in pl.buys() if x["eth"] >= MIN_REAL and x["from"] not in DUST_WALLETS and (after is None or x["bn"] > after)]


def sched_generic(pl, B): r = real_buys(pl, B); return r[0] if r else None
def sched_bot(pl, B): return next((x for x in pl.buys() if x["bn"] > B and is_bot(x)), None)


def front(pl, sched_fn, hold=20, stake=STAKE):
    lb = pl.b0; B = lb + 1; sb = sched_fn(pl, B)
    S = sb["bn"] + 1 if (sb and sb["bn"] + 1 <= lb + hold) else lb + hold
    r = pl.trade(B, S, stake); r["sched"] = (sb["bn"] - lb) if sb else None; return r


def follow(pl, hold=4, stake=STAKE):
    lb = pl.b0; rb = real_buys(pl)
    if not rb: return None
    trig = rb[0]; B = trig["bn"] + 1
    nxt = next((x for x in rb if x["bn"] > B), None)
    S = nxt["bn"] + 1 if (nxt and nxt["bn"] + 1 <= B + hold) else B + hold
    r = pl.trade(B, S, stake); r.update({"trig": trig["bn"] - lb, "trig_eth": trig["eth"] / 1e18, "next": (nxt["bn"] - lb) if nxt else None}); return r


def capacity(pl, sb):
    s, L = pl.launch_state(); fee = pl.fee_at(sb["bn"]); Y = sb["eth"]
    quote = v4math.buy_out_int(int(s), L, Y, fee)
    if is_bot(sb) and sb["input"]:
        mo = word(sb["input"], 4); src = "calldata word 4 (bot router c1120e3d)"
    else:
        mo = int(quote * 0.99); src = "ASSUMED minOut = 0.99 x launch-state quote"
    return {"cap_eth": room(s, L, Y, fee, mo), "src": src, "minout_over_quote": mo / quote if quote else None, "Y": Y / 1e18}


def pct(v): return q(v)


out = {}
# ------------------------------------------------------------------ controls
C = {}
rs = [front(pool(x), sched_bot) for x in V]
C["v2433_front_all"] = summarize(rs)
C["v2433_front_exits"] = dict(collections.Counter(r["exit"] for r in rs))
C["v2433_sched_off_p10_50_90"] = pct([r["sched"] for r in rs if r["sched"] is not None])
C["v2433_front_bot_by_20"] = summarize([r for r in rs if r["sched"] is not None and r["sched"] + 1 <= 20])
lw = [r for x, r in zip(V, rs) if 84880000 <= P[x]["launch_block"] <= 84970000]
C["v2433_front_livewindow"] = summarize(lw)
C["v2433_front_generic_sched"] = summarize([front(pool(x), sched_generic) for x in V])
caps = [capacity(pool(x), sb) for x in V for sb in [sched_bot(pool(x), P[x]["launch_block"])] if sb]
C["v2433_capacity_p10_50_90"] = pct([c["cap_eth"] for c in caps])
C["v2433_minout_over_quote_p10_50_90"] = pct([c["minout_over_quote"] for c in caps])
c05 = [c["cap_eth"] for c in caps if abs(c["Y"] - 0.05) < 0.002]
C["v2433_capacity_for_0.05_buys"] = pct(c05)
# live relay trades: realised gross vs the model at the same B, S, stake
diffs = []
for x in V + A:
    pl = pool(x); rel = [y for y in pl.seq if y["relay"]]
    rb = [y for y in rel if y["buy"]]; rsl = [y for y in rel if not y["buy"]]
    if len(rb) != 1 or len(rsl) != 1: continue
    b, s = rb[0], rsl[0]; real = (s["eth"] - b["eth"]) / b["eth"]
    before_in_S = any(y["bn"] == s["bn"] and y["li"] < s["li"] and not y["relay"] for y in pl.seq)
    sim = pl.trade(b["bn"], s["bn"] + (1 if before_in_S else 0), stake=b["eth"])
    if sim.get("gross") is not None: diffs.append((sim["gross"] - real, real, sim["gross"], P[x]["known"]))
d = [z[0] for z in diffs]
C["live_relay_calibration"] = {"n": len(diffs), "real_mean": st.mean(z[1] for z in diffs), "model_mean": st.mean(z[2] for z in diffs),
                               "diff_p10_50_90": q(d, nd=7), "abs_diff_median": st.median(abs(z) for z in d), "within_0.5pt": sum(1 for z in d if abs(z) < 0.005)}
fa = [r for r in (follow(pool(x)) for x in A) if r]
C["opA_follow"] = summarize(fa); C["opA_follow_trig_p10_50_90"] = pct([r["trig"] for r in fa])
C["opA_front_generic"] = summarize([front(pool(x), sched_generic) for x in A])
C["gas_usd_per_trade_v2433_median"] = st.median(pool(x).gas for x in V) / 1e18 * USD_PER_ETH
out["controls"] = C
print("CONTROLS")
for k, v in C.items(): print("  ", k, fmt_rule(v) if isinstance(v, dict) and "n" in v and "exits" in v else v)

# ------------------------------------------------------------------ families
for g, pids in groups.items():
    pls = [pool(x) for x in pids]; ps = [P[x] for x in pids]
    lbs = [p["launch_block"] for p in ps]
    r = {"count": len(ps), "launches_per_day": round(len(ps) / WINDOW_DAYS, 2),
         "first_last_utc_ts": [min(p["launch_ts"] for p in ps), max(p["launch_ts"] for p in ps)],
         "span_hours": round((max(lbs) - min(lbs)) * 0.1026 / 3600, 2),
         "deployers": collections.Counter(p["launch_from"] for p in ps).most_common(5), "n_deployers": len(set(p["launch_from"] for p in ps)),
         "launch_to": collections.Counter(p["launch_to"] for p in ps).most_common(3), "n_launch_to": len(set(p["launch_to"] for p in ps)),
         "values": collections.Counter(p["launch_value_eth"] for p in ps).most_common(3), "fees": collections.Counter(p["fee"] for p in ps).most_common(4),
         "calldata_len": collections.Counter(p["calldata_len"] for p in ps).most_common(4),
         "nonce_range": [min(p["launch_nonce"] for p in ps), max(p["launch_nonce"] for p in ps)],
         "tick0": collections.Counter(p["tick0"] for p in ps).most_common(3), "liq_launch": collections.Counter(p["liq_launch"] for p in ps).most_common(3),
         "launch_ranges": collections.Counter(tuple((a["lo"], a["hi"]) for a in pl.adds if a["tx"] == pl.p["launch_tx"]) for pl in pls).most_common(3),
         "minted_by": collections.Counter(pl.adds[0]["sender"] if pl.adds else None for pl in pls).most_common(3),
         "buy_in_launch_tx": sum(1 for p in ps if p["buy_in_launch_tx"])}
    fb = [(pl, pl.buys()[0]) for pl in pls if pl.buys()]
    r["first_buy_any"] = {"pools_with": len(fb), "off_p10_50_90": pct([x["bn"] - pl.b0 for pl, x in fb]), "eth_p10_50_90": pct([x["eth"] / 1e18 for pl, x in fb]),
                          "to": collections.Counter(x["to"] for pl, x in fb).most_common(3), "from": collections.Counter(x["from"] for pl, x in fb).most_common(3),
                          "n_from": len(set(x["from"] for pl, x in fb))}
    fr = [(pl, real_buys(pl)[0]) for pl in pls if real_buys(pl)]
    r["first_buy_real"] = {"pools_with": len(fr), "off_p10_50_90": pct([x["bn"] - pl.b0 for pl, x in fr]), "eth_p10_50_90": pct([x["eth"] / 1e18 for pl, x in fr]),
                           "to": collections.Counter(x["to"] for pl, x in fr).most_common(4), "from": collections.Counter(x["from"] for pl, x in fr).most_common(4),
                           "n_from": len(set(x["from"] for pl, x in fr)), "by_launch_wallet": sum(1 for pl, x in fr if x["from"] == pl.p["launch_from"]),
                           "list": [(pl.pid[:12], x["bn"] - pl.b0, x["eth"] / 1e18, x["to"], x["from"], x["sel"]) for pl, x in fr][:12]}
    allsw = [x for pl in pls for x in pl.seq]
    r["swaps"] = {"total": len(allsw), "buys": sum(1 for x in allsw if x["buy"]), "sells": sum(1 for x in allsw if not x["buy"]),
                  "eth_in": sum(x["eth"] for x in allsw if x["buy"]) / 1e18, "from": collections.Counter(x["from"] for x in allsw).most_common(5),
                  "pools_with_any": sum(1 for pl in pls if pl.seq), "pools_with_sell": sum(1 for pl in pls if any(not x["buy"] for x in pl.seq))}
    pl_ = [(pl, pl.pulls[0]) for pl in pls if pl.pulls]
    r["pull"] = {"pulled_3000": len(pl_), "frac": round(len(pl_) / len(pls), 3), "off_p10_50_90": pct([x["bn"] - pl.b0 for pl, x in pl_]),
                 "by": collections.Counter(pl.p["first_pull_from"] for pl, x in pl_).most_common(3),
                 "by_launch_wallet": sum(1 for pl, x in pl_ if pl.p["first_pull_from"] == pl.p["launch_from"])}
    # trap test: outsider = a buy (any size) by a non-launch wallet before the first scheduled (real) buy; pull delay with/without
    wo, wi = [], []
    for pl in pls:
        sb = sched_generic(pl, pl.b0)
        outs = [x for x in pl.buys() if (sb is None or (x["bn"], x["li"]) < (sb["bn"], sb["li"])) and x["from"] != pl.p["launch_from"]]
        pb = pl.pull_bn
        if outs: wi.append((pb - outs[0]["bn"]) if pb is not None else None)
        else: wo.append((pb - pl.b0) if pb is not None else None)
    r["trap"] = {"pools_with_outsider_before_sched": len(wi), "pulled_after_outsider": sum(1 for z in wi if z is not None),
                 "delay_after_outsider_p10_50_90": pct([z for z in wi if z is not None]), "pools_without": len(wo),
                 "pulled_without": sum(1 for z in wo if z is not None), "pull_off_without_p10_50_90": pct([z for z in wo if z is not None])}
    frs = [front(pl, sched_generic) for pl in pls]
    r["front"] = summarize(frs); r["front_sched_by_20"] = sum(1 for z in frs if z.get("sched") is not None and z["sched"] + 1 <= 20)
    r["front_gross_p10_50_90"] = pct([z["gross"] for z in frs if z.get("gross") is not None])
    r["front_hold3000"] = summarize([front(pl, sched_generic, hold=3000) for pl in pls])
    fos = [z for z in (follow(pl) for pl in pls) if z]
    r["follow"] = summarize(fos); r["follow_rows"] = [{k: z.get(k) for k in ("trig", "trig_eth", "next", "B", "S", "exit", "ret")} for z in fos][:10]
    caps = [capacity(pl, sb) for pl in pls for sb in [sched_generic(pl, pl.b0)] if sb]
    r["capacity"] = {"n": len(caps), "cap_eth_p10_50_90": pct([c["cap_eth"] for c in caps]), "src": collections.Counter(c["src"] for c in caps).most_common(2)}
    r["gas_usd_median"] = st.median(pl.gas for pl in pls) / 1e18 * USD_PER_ETH
    r["base_fee_gwei_median"] = st.median(pl.base_fee for pl in pls) / 1e9
    out[g] = r
    print("=" * 110); print(g)
    for k, v in r.items():
        if k in ("front", "follow", "front_hold3000"): print("  %-22s %s" % (k, fmt_rule(v)))
        else: print("  %-22s %s" % (k, v))
json.dump(out, open(os.path.join(HERE, "stats.json"), "w"), indent=1, default=str)
