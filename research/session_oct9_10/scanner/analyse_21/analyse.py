"""analyse_21: four assigned families + their wider groups (same deployers) + controls (vbot-v2.433, operator A), priced with
common21.Pool (analyse_20/common20.py copied verbatim: the exact replay of research/session_oct9_10/explore/chk/replay.py on the census:
our buy at the END of block B after every other tx, every later swap replayed by its own price shift, our sell at the HEAD of block S,
a pull at or before S = the stake lost, the pool's own fee each way, gas 2 x 104,000 x the launch block's base fee).
Writes stats.json."""
import sys, os, json, statistics as st, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common21 import *  # noqa
from pricer21 import Pool21

K = json.load(open(os.path.join(HERE, "keys.json")))
P = load_pools(); F = load_families(); T = load_txs(); M = load_blocks_meta()
groups = {k: F[k]["pids"] for k in K}
D1 = "0x841ac064763c75a6b6b916ef676420d6ffdd281f"
groups["WIDER deployer 0x841ac064 (all 10: launch contracts 0x458cdbed/0xc7c72f08/0x404422f1, d181e93a, fee 0 and 1%)"] = [p["pid"] for p in P.values() if p["launch_from"] == D1]
deps234 = set(P[x]["launch_from"] for k in K[1:] for x in F[k]["pids"])
groups["WIDER deployers of families 2-4 (%d wallets, every POSM launch of theirs)" % len(deps234)] = [p["pid"] for p in P.values() if p["launch_from"] in deps234]
groups["WIDER every POSM ac9650d8 launch with fee >= 5% (known none)"] = [p["pid"] for p in P.values() if p["launch_to"] == "0x58daec3116aae6d93017baaea7749052e8a04fa7"
                                                                           and p["selector"] == "ac9650d8" and p["fee"] != 8388608 and p["fee"] >= 50000 and p["known"] == "none"]
V = [p["pid"] for p in P.values() if p["known"] == "vbot-v2.433"]
A = [p["pid"] for p in P.values() if p["known"] == "operator-A"]
groups["CONTROL vbot-v2.433"] = V
groups["CONTROL operator-A"] = A
E = load_events(set(x for v in groups.values() for x in v) | set(V) | set(A))
POOL = {}


def pool(pid):
    if pid not in POOL: POOL[pid] = Pool21(P[pid], E.get(pid), T, M)
    return POOL[pid]


def is_bot(x): return x["to"] == VBOT_ROUTER and x["sel"] == "c1120e3d"


def real_buys(pl, after=None):
    """non-launch, non-relay buys of >= 0.0002 ETH, the chain-wide dust wallets excluded"""
    return [x for x in pl.buys() if x["eth"] >= MIN_REAL and x["from"] not in DUST_WALLETS and (after is None or x["bn"] > after)]


def sched_generic(pl, B): r = real_buys(pl, B); return r[0] if r else None
def sched_bot(pl, B): return next((x for x in pl.buys() if x["bn"] > B and is_bot(x)), None)


def front(pl, sched_fn, hold=20, stake=STAKE):
    """buy landing at launch + 1 (after every tx of that block); sell landing one block after the first scheduled buy, or at launch + hold"""
    lb = pl.b0; B = lb + 1; sb = sched_fn(pl, B)
    S = sb["bn"] + 1 if (sb and sb["bn"] + 1 <= lb + hold) else lb + hold
    r = pl.trade(B, S, stake); r["sched"] = (sb["bn"] - lb) if sb else None; r["pid"] = pl.pid; return r


def follow(pl, hold=4, stake=STAKE):
    """buy landing one block after the first real buy (>= 0.0002 ETH); sell one block after the next real buy behind ours, or at our buy + hold"""
    lb = pl.b0; rb = real_buys(pl)
    if not rb: return None
    trig = rb[0]; B = trig["bn"] + 1
    nxt = next((x for x in rb if x["bn"] > B), None)
    S = nxt["bn"] + 1 if (nxt and nxt["bn"] + 1 <= B + hold) else B + hold
    r = pl.trade(B, S, stake); r.update({"pid": pl.pid, "trig": trig["bn"] - lb, "trig_eth": trig["eth"] / 1e18, "next": (nxt["bn"] - lb) if nxt else None}); return r


def minout_08c1284c(inp):
    """router 0xf2251d75 selector 08c1284c (packed calldata): returns (amountIn, minOut) if the layout <01><len><amountIn><len><minOut> is found"""
    try:
        h = inp[10:]
        i = h.find("0000010", 128)
        if i < 0: return None
        j = i + 6; ln = int(h[j:j + 2], 16); amt = int(h[j + 2:j + 2 + 2 * ln], 16); k = j + 2 + 2 * ln
        ln2 = int(h[k:k + 2], 16); mo = int(h[k + 2:k + 2 + 2 * ln2], 16) if ln2 else 0
        return amt, mo
    except Exception:
        return None


def capacity(pl, sb):
    s, L = pl.launch_state(); fee = pl.fee_at(sb["bn"]); Y = sb["eth"]
    quote = v4math.buy_out_int(int(s), L, Y, fee)
    if is_bot(sb) and sb["input"]:
        mo = word(sb["input"], 4); src = "calldata word 4 (bot router c1120e3d)"
    elif sb["sel"] == "08c1284c" and sb["input"] and minout_08c1284c(sb["input"]):
        amt, mo = minout_08c1284c(sb["input"]); src = "router 0xf2251d75 08c1284c packed: amountIn %.6g ETH, minOut field %d (effectively none)" % (amt / 1e18, mo)
    elif sb["to"] == UR or sb["sel"] == "3593564c":
        mo = int(quote * 0.99); src = "Universal Router-style execute (nested, not decoded): ASSUMED minOut = 0.99 x launch-state quote"
    else:
        mo = int(quote * 0.99); src = "router %s sel %s not decoded: ASSUMED minOut = 0.99 x launch-state quote" % ((sb["to"] or "?")[:10], sb["sel"])
    return {"cap_eth": room(s, L, Y, fee, mo), "src": src, "minout_over_quote": (mo / quote) if quote else None, "Y": Y / 1e18}


def adds_in_window(pl, B, S):
    return sum(1 for a in pl.adds[1:] if B < a["bn"] <= S)


out = {}
# ------------------------------------------------------------------ controls (calibrate the method)
C = {}
rs = [front(pool(x), sched_bot) for x in V]
C["v2433_front_bot_sched_all"] = summarize(rs)
C["v2433_sched_off_p10_50_90"] = q([r["sched"] for r in rs if r["sched"] is not None])
lw = [r for x, r in zip(V, rs) if 84880000 <= P[x]["launch_block"] <= 84970000]
C["v2433_front_livewindow_oct10_0907_1139"] = summarize(lw)
C["v2433_front_generic_sched"] = summarize([front(pool(x), sched_generic) for x in V])
caps = [capacity(pool(x), sb) for x in V for sb in [sched_bot(pool(x), P[x]["launch_block"])] if sb]
C["v2433_capacity_p10_50_90"] = q([c["cap_eth"] for c in caps])
C["v2433_minout_over_quote_p10_50_90"] = q([c["minout_over_quote"] for c in caps])
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
C["opA_follow"] = summarize(fa); C["opA_follow_trig_p10_50_90"] = q([r["trig"] for r in fa])
C["opA_front_generic"] = summarize([front(pool(x), sched_generic) for x in A])
C["gas_usd_per_trade_v2433_median"] = st.median(pool(x).gas for x in V) / 1e18 * USD_PER_ETH
out["controls"] = C
print("CONTROLS")
for k, v in C.items(): print("  ", k, fmt_rule(v) if isinstance(v, dict) and "exits" in v else v)

# ------------------------------------------------------------------ families
for g, pids in groups.items():
    pls = [pool(x) for x in pids]; ps = [P[x] for x in pids]
    lbs = [p["launch_block"] for p in ps]
    span_h = (max(lbs) - min(lbs)) * 0.1026 / 3600
    r = {"count": len(ps), "launches_per_day": round(len(ps) / WINDOW_DAYS, 2),
         "first_last_block": [min(lbs), max(lbs)], "first_last_ts": [min(p["launch_ts"] for p in ps), max(p["launch_ts"] for p in ps)], "span_hours": round(span_h, 2),
         "deployers": collections.Counter(p["launch_from"] for p in ps).most_common(6), "n_deployers": len(set(p["launch_from"] for p in ps)),
         "launch_to": collections.Counter(p["launch_to"] for p in ps).most_common(3), "values": collections.Counter(p["launch_value_eth"] for p in ps).most_common(5),
         "fees": collections.Counter(p["fee"] for p in ps).most_common(8), "hooks": collections.Counter(p["hooks"] for p in ps).most_common(2),
         "calldata_len": collections.Counter(p["calldata_len"] for p in ps).most_common(3),
         "nonce_range": [min(p["launch_nonce"] for p in ps), max(p["launch_nonce"] for p in ps)],
         "launch_ranges": collections.Counter(str([(a["lo"], a["hi"]) for a in pool(p["pid"]).adds if a["tx"] == p["launch_tx"]]) for p in ps).most_common(3),
         "start": collections.Counter(pl.start for pl in pls).most_common(), "buy_in_launch_tx": sum(1 for p in ps if p["buy_in_launch_tx"]),
         "later_adds_pools": sum(1 for pl in pls if len(pl.adds) > 1)}
    fb = [(pl, pl.buys()[0]) for pl in pls if pl.buys()]
    r["first_buy_any"] = {"pools_with": len(fb), "off_p10_50_90": q([x["bn"] - pl.b0 for pl, x in fb]), "eth_p10_50_90": q([x["eth"] / 1e18 for pl, x in fb], nd=8),
                          "to": collections.Counter(x["to"] for pl, x in fb).most_common(4), "sel": collections.Counter(x["sel"] for pl, x in fb).most_common(4),
                          "from": collections.Counter(x["from"] for pl, x in fb).most_common(4), "n_from": len(set(x["from"] for pl, x in fb)),
                          "from_eq_to (EIP-7702 self-call)": sum(1 for pl, x in fb if x["from"] and x["from"] == x["to"]),
                          "by_launch_wallet": sum(1 for pl, x in fb if x["from"] == pl.p["launch_from"])}
    fr = [(pl, real_buys(pl)[0]) for pl in pls if real_buys(pl)]
    r["first_buy_real"] = {"pools_with": len(fr), "frac": round(len(fr) / len(pls), 3), "off_p10_50_90": q([x["bn"] - pl.b0 for pl, x in fr]),
                           "eth_p10_50_90": q([x["eth"] / 1e18 for pl, x in fr]),
                           "to": collections.Counter(x["to"] for pl, x in fr).most_common(4), "sel": collections.Counter(x["sel"] for pl, x in fr).most_common(4),
                           "from": collections.Counter(x["from"] for pl, x in fr).most_common(4), "n_from": len(set(x["from"] for pl, x in fr)),
                           "by_launch_wallet": sum(1 for pl, x in fr if x["from"] == pl.p["launch_from"]),
                           "fresh_nonce_le3": sum(1 for pl, x in fr if x["nonce"] is not None and x["nonce"] <= 3),
                           "list": [(pl.pid[:12], x["bn"] - pl.b0, round(x["eth"] / 1e18, 6), x["to"], x["from"], x["sel"], x["nonce"]) for pl, x in fr][:12]}
    allsw = [x for pl in pls for x in pl.seq if not x["in_launch"]]
    r["swaps_non_launch"] = {"total": len(allsw), "buys": sum(1 for x in allsw if x["buy"]), "sells": sum(1 for x in allsw if not x["buy"]),
                             "eth_in": round(sum(x["eth"] for x in allsw if x["buy"]) / 1e18, 6), "from": collections.Counter(x["from"] for x in allsw).most_common(6),
                             "pools_with_any": sum(1 for pl in pls if any(not x["in_launch"] for x in pl.seq)),
                             "sells_by_launch_wallet": sum(1 for pl in pls for x in pl.seq if not x["buy"] and x["from"] == pl.p["launch_from"])}
    pl_ = [(pl, pl.pulls[0]) for pl in pls if pl.pulls]
    r["pull"] = {"pulled_3000": len(pl_), "frac": round(len(pl_) / len(pls), 3), "off_launch_p10_50_90": q([x["bn"] - pl.b0 for pl, x in pl_]),
                 "off_from_first_real_buy_p10_50_90": q([x["bn"] - real_buys(pl)[0]["bn"] for pl, x in pl_ if real_buys(pl)]),
                 "by": collections.Counter(pl.p["first_pull_from"] for pl, x in pl_).most_common(3),
                 "by_launch_wallet": sum(1 for pl, x in pl_ if pl.p["first_pull_from"] == pl.p["launch_from"]),
                 "via": collections.Counter("%s:%s" % (pl.p["first_pull_to"], pl.p["first_pull_selector"]) for pl, x in pl_).most_common(2)}
    # trap test: outsider = a non-launch buy by a wallet other than the launch wallet, before the first scheduled (real) buy; dust wallets apart
    wo, wi, dust_only, out_sizes, out_from = [], [], 0, [], collections.Counter()
    for pl in pls:
        sb = sched_generic(pl, pl.b0)
        pre = [x for x in pl.buys() if (sb is None or (x["bn"], x["li"]) < (sb["bn"], sb["li"])) and x["from"] != pl.p["launch_from"]]
        outs = [x for x in pre if x["from"] not in DUST_WALLETS]
        if pre and not outs: dust_only += 1
        pb = pl.pull_bn
        if outs:
            wi.append((pb - outs[0]["bn"]) if pb is not None else None); out_sizes += [x["eth"] / 1e18 for x in outs]; out_from.update(x["from"] for x in outs)
        else: wo.append((pb - pl.b0) if pb is not None else None)
    r["trap"] = {"pools_with_outsider_before_sched": len(wi), "frac": round(len(wi) / len(pls), 3), "pools_with_only_dust_wallet_before_sched": dust_only,
                 "outsider_eth_p10_50_90": q(out_sizes, nd=8), "outsider_wallets": out_from.most_common(5),
                 "pulled_after_outsider": sum(1 for z in wi if z is not None), "delay_after_outsider_p10_50_90": q([z for z in wi if z is not None]),
                 "pools_without": len(wo), "pulled_without": sum(1 for z in wo if z is not None), "pull_off_without_p10_50_90": q([z for z in wo if z is not None])}
    frs = [front(pl, sched_generic) for pl in pls]
    r["front"] = summarize(frs); r["front_sched_by_20"] = sum(1 for z in frs if z.get("sched") is not None and z["sched"] + 1 <= 20)
    r["front_gross_p10_50_90"] = q([z["gross"] for z in frs if z.get("gross") is not None])
    r["front_fees"] = collections.Counter((z.get("fee_b"), z.get("fee_s")) for z in frs if z.get("ret") is not None).most_common(4)
    r["front_adds_in_window"] = sum(adds_in_window(pool(z["pid"]), pool(z["pid"]).b0 + 1, pool(z["pid"]).b0 + z["S"]) for z in frs if z.get("S") is not None)
    r["front_rows"] = [{k: z.get(k) for k in ("pid", "sched", "B", "S", "exit", "ret", "gross", "fee_b", "fee_s")} for z in frs][:12]
    r["front_hold3000"] = summarize([front(pl, sched_generic, hold=3000) for pl in pls])
    fos = [z for z in (follow(pl) for pl in pls) if z]
    r["follow"] = summarize(fos)
    r["follow_rows"] = [{k: z.get(k) for k in ("pid", "trig", "trig_eth", "next", "B", "S", "exit", "ret", "gross", "fee_b", "fee_s")} for z in fos][:12]
    caps = [capacity(pl, sb) for pl in pls for sb in [sched_generic(pl, pl.b0)] if sb]
    r["capacity"] = {"n": len(caps), "cap_eth_p10_50_90": q([c["cap_eth"] for c in caps]), "rows": caps[:8], "src": collections.Counter(c["src"].split(":")[0] for c in caps).most_common(3)}
    r["gas_usd_median"] = st.median(pl.gas for pl in pls) / 1e18 * USD_PER_ETH
    out[g] = r
    print("=" * 110); print(g)
    for k, v in r.items():
        if k in ("front", "follow", "front_hold3000"): print("  %-22s %s" % (k, fmt_rule(v)))
        else: print("  %-22s %s" % (k, v))
json.dump(out, open(os.path.join(HERE, "stats.json"), "w"), indent=1, default=str)
