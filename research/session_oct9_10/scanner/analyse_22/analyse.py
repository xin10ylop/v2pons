"""analyse_22: four assigned families (POSM ac9650d8: 1444/500/10, 1444/590000/60, 2020/3000/60, 2020/790000/7900) + their wider groups
(same operator: the 2-ETH fresh-wallet "slow pump" operator also launches the 1444/100/1 family; the deployers of families 2 and 4) +
controls (vbot-v2.433 front, operator A follow), priced with common22.Pool (analyse_21/common21.py verbatim: the exact replay of
research/session_oct9_10/explore/chk/replay.py on the census: our buy at the END of block B after every other tx, every later swap replayed
by its own price shift, our sell at the HEAD of block S, a pull at or before S = the stake lost, the pool's own fee each way, gas
2 x 104,000 x the launch block's base fee). extra_txs.json (fetch_txs.py) adds the txs of the later swaps of the 2-ETH group and family 3.
Writes results.json."""
import sys, os, json, statistics as st, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common22 import *  # noqa

K = json.load(open(os.path.join(HERE, "keys.json")))
P = load_pools(); F = load_families(); T = load_txs(); M = load_blocks_meta()
T.update(json.load(open(os.path.join(HERE, "extra_txs.json"))))
F100 = "0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|100|1|true"
D2 = "0x909a0af40a3577f60bb3b0d6bd38fe2d8adfed54"; D4 = {"0x5dc9708f972a56d43620cc61f8236c5177270ce5", "0xa1e4bca023d741bd8d8609875ceef2abd8d755a3", "0x743508ffae72e5711c1f9d9765ca32794b6e43b9"}
groups = collections.OrderedDict()
groups["F1 " + K[0]] = F[K[0]]["pids"]
groups["F1-WIDE the 2-ETH fresh-wallet operator: F1 + " + F100] = F[K[0]]["pids"] + F[F100]["pids"]
groups["F2 " + K[1]] = F[K[1]]["pids"]
groups["F2-WIDE deployer 0x909a0af4 (all its launches)"] = [p["pid"] for p in P.values() if p["launch_from"] == D2]
groups["F3 " + K[2]] = F[K[2]]["pids"]
groups["F4 " + K[3]] = F[K[3]]["pids"]
groups["F4-WIDE deployers 0x5dc9708f/0xa1e4bca0/0x743508ff (all their launches)"] = [p["pid"] for p in P.values() if p["launch_from"] in D4]
V = [p["pid"] for p in P.values() if p["known"] == "vbot-v2.433"]
A = [p["pid"] for p in P.values() if p["known"] == "operator-A"]
E = load_events(set(x for v in groups.values() for x in v) | set(V) | set(A))
POOL = {}


def pool(pid):
    if pid not in POOL: POOL[pid] = Pool(P[pid], E.get(pid), T, M)
    return POOL[pid]


def is_bot(x): return x["to"] == VBOT_ROUTER and x["sel"] == "c1120e3d"
def is_crowd(x): return x["buy"] and x["to"] == UR and x["clen"] == 1284 and x["nonce"] == 0      # the 2-ETH operator's fresh-wallet buys


def real_buys(pl, after=None):
    """non-launch, non-relay buys of >= 0.0002 ETH, the chain-wide dust wallets excluded"""
    return [x for x in pl.buys() if x["eth"] >= MIN_REAL and x["from"] not in DUST_WALLETS and (after is None or x["bn"] > after)]


def sched_generic(pl, B): r = real_buys(pl, B); return r[0] if r else None
def sched_bot(pl, B): return next((x for x in pl.buys() if x["bn"] > B and is_bot(x)), None)
def sched_crowd(pl, B): return next((x for x in pl.buys() if x["bn"] > B and is_crowd(x)), None)


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


def front_kth(pl, k, fn=is_crowd, cap=3000, stake=STAKE):
    """buy at launch + 1, sell one block after the k-th scheduled buy (fn), or at launch + cap"""
    lb = pl.b0; B = lb + 1
    sb = [x for x in pl.buys() if x["bn"] > B and fn(x)]
    S = sb[k - 1]["bn"] + 1 if len(sb) >= k and sb[k - 1]["bn"] + 1 <= lb + cap else lb + cap
    return pl.trade(B, S, stake)


def capacity(pl, sb):
    s, L = pl.launch_state(); fee = pl.fee_at(sb["bn"]); Y = sb["eth"]
    quote = v4math.buy_out_int(int(s), L, Y, fee)
    if is_bot(sb) and sb["input"]:
        mo = word(sb["input"], 4); src = "calldata word 4 (bot router c1120e3d)"
    elif sb["sel"] == "3593564c":
        mo = int(quote * 0.99); src = "Universal-Router-style execute (nested, not decoded): ASSUMED minOut = 0.99 x launch-state quote"
    else:
        mo = int(quote * 0.99); src = "router %s sel %s not decoded: ASSUMED minOut = 0.99 x launch-state quote" % ((sb["to"] or "?")[:10], sb["sel"])
    return {"cap_eth": room(s, L, Y, fee, mo), "src": src, "minout_over_quote": (mo / quote) if quote else None, "Y": Y / 1e18}


out = {"window_days": WINDOW_DAYS}
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
diffs = []
for x in V + A:
    pl = pool(x); rel = [y for y in pl.seq if y["relay"]]
    rb = [y for y in rel if y["buy"]]; rsl = [y for y in rel if not y["buy"]]
    if len(rb) != 1 or len(rsl) != 1: continue
    b, s = rb[0], rsl[0]; real = (s["eth"] - b["eth"]) / b["eth"]
    before_in_S = any(y["bn"] == s["bn"] and y["li"] < s["li"] and not y["relay"] for y in pl.seq)
    sim = pl.trade(b["bn"], s["bn"] + (1 if before_in_S else 0), stake=b["eth"])
    if sim.get("gross") is not None: diffs.append((sim["gross"] - real, real, sim["gross"]))
d = [z[0] for z in diffs]
C["live_relay_calibration (our real relay round trips re-priced by the model)"] = {"n": len(diffs), "real_mean": round(st.mean(z[1] for z in diffs), 5),
    "model_mean": round(st.mean(z[2] for z in diffs), 5), "abs_diff_median": st.median(abs(z) for z in d), "within_0.5pt": sum(1 for z in d if abs(z) < 0.005)}
fa = [r for r in (follow(pool(x)) for x in A) if r]
C["opA_follow"] = summarize(fa); C["opA_follow_trig_p10_50_90"] = q([r["trig"] for r in fa])
C["gas_usd_per_trade_v2433_median"] = round(st.median(pool(x).gas for x in V) / 1e18 * USD_PER_ETH, 5)
out["controls"] = C
print("CONTROLS")
for k, v in C.items(): print("  ", k, fmt_rule(v) if isinstance(v, dict) and "exits" in v else v)

# ------------------------------------------------------------------ families
for g, pids in groups.items():
    pls = [pool(x) for x in pids]; ps = [P[x] for x in pids]
    lbs = [p["launch_block"] for p in ps]
    r = {"count": len(ps), "launches_per_day": round(len(ps) / WINDOW_DAYS, 2), "first_last_ts": [min(p["launch_ts"] for p in ps), max(p["launch_ts"] for p in ps)],
         "deployers": collections.Counter(p["launch_from"] for p in ps).most_common(4), "n_deployers": len(set(p["launch_from"] for p in ps)),
         "deployer_nonces": collections.Counter(p["launch_nonce"] for p in ps).most_common(4),
         "values": collections.Counter(p["launch_value_eth"] for p in ps).most_common(5), "fees": collections.Counter(p["fee"] for p in ps).most_common(6),
         "launch_ranges": collections.Counter(str([(a["lo"], a["hi"]) for a in pool(p["pid"]).adds if a["tx"] == p["launch_tx"]]) for p in ps).most_common(3),
         "start": collections.Counter(pl.start for pl in pls).most_common(), "later_adds_pools": sum(1 for pl in pls if len(pl.adds) > 1)}
    fb = [(pl, pl.buys()[0]) for pl in pls if pl.buys()]
    r["first_buy_any"] = {"pools_with": len(fb), "off_p10_50_90": q([x["bn"] - pl.b0 for pl, x in fb]), "eth_p10_50_90": q([x["eth"] / 1e18 for pl, x in fb], nd=8),
                          "to": collections.Counter(x["to"] for pl, x in fb).most_common(3), "from": collections.Counter(x["from"] for pl, x in fb).most_common(3)}
    fr = [(pl, real_buys(pl)[0]) for pl in pls if real_buys(pl)]
    r["first_buy_real"] = {"pools_with": len(fr), "frac": round(len(fr) / len(pls), 3), "off_p10_50_90": q([x["bn"] - pl.b0 for pl, x in fr]),
                           "eth_p10_50_90": q([x["eth"] / 1e18 for pl, x in fr]), "to_sel_len": collections.Counter("%s:%s:%s" % (x["to"], x["sel"], x["clen"]) for pl, x in fr).most_common(4),
                           "n_from": len(set(x["from"] for pl, x in fr)), "nonce0": sum(1 for pl, x in fr if x["nonce"] == 0),
                           "by_launch_wallet": sum(1 for pl, x in fr if x["from"] == pl.p["launch_from"]),
                           "from_top": collections.Counter(x["from"] for pl, x in fr).most_common(4)}
    allsw = [x for pl in pls for x in pl.seq if not x["in_launch"]]
    r["swaps_non_launch"] = {"total": len(allsw), "buys": sum(1 for x in allsw if x["buy"]), "sells": sum(1 for x in allsw if not x["buy"]),
                             "eth_in": round(sum(x["eth"] for x in allsw if x["buy"]) / 1e18, 6), "pools_with_any": sum(1 for pl in pls if any(not x["in_launch"] for x in pl.seq)),
                             "from_top": collections.Counter(x["from"] for x in allsw).most_common(6)}
    pl_ = [(pl, pl.pulls[0]) for pl in pls if pl.pulls]
    r["pull"] = {"pulled_3000": len(pl_), "frac": round(len(pl_) / len(pls), 3), "off_launch_p10_50_90": q([x["bn"] - pl.b0 for pl, x in pl_]),
                 "off_from_first_real_buy_p10_50_90": q([x["bn"] - real_buys(pl)[0]["bn"] for pl, x in pl_ if real_buys(pl)]),
                 "by_launch_wallet": sum(1 for pl, x in pl_ if pl.p["first_pull_from"] == pl.p["launch_from"]),
                 "via": collections.Counter("%s:%s" % (pl.p["first_pull_to"], pl.p["first_pull_selector"]) for pl, x in pl_).most_common(2)}
    # trap test: outsiders = non-launch buys before the first scheduled (real) buy by wallets other than the launch wallet, dust wallets apart
    wo, wi, out_sizes, out_from = [], [], [], collections.Counter()
    for pl in pls:
        sb = sched_generic(pl, pl.b0)
        outs = [x for x in pl.buys() if (sb is None or (x["bn"], x["li"]) < (sb["bn"], sb["li"])) and x["from"] != pl.p["launch_from"] and x["from"] not in DUST_WALLETS]
        pb = pl.pull_bn
        if outs: wi.append((pb - outs[0]["bn"]) if pb is not None else None); out_sizes += [x["eth"] / 1e18 for x in outs]; out_from.update(x["from"] for x in outs)
        else: wo.append((pb - pl.b0) if pb is not None else None)
    r["trap"] = {"pools_with_outsider_before_sched": len(wi), "outsider_eth_p10_50_90": q(out_sizes, nd=8), "outsider_wallets": out_from.most_common(5),
                 "pulled_after_outsider": sum(1 for z in wi if z is not None), "delay_after_outsider_p10_50_90": q([z for z in wi if z is not None]),
                 "pools_without": len(wo), "pulled_without": sum(1 for z in wo if z is not None), "pull_off_without_p10_50_90": q([z for z in wo if z is not None])}
    frs = [front(pl, sched_generic) for pl in pls]
    r["front"] = summarize(frs); r["front_rows"] = [{k: z.get(k) for k in ("pid", "sched", "S", "exit", "ret", "fee_b", "fee_s")} for z in frs][:8]
    fos = [z for z in (follow(pl) for pl in pls) if z]
    r["follow"] = summarize(fos); r["follow_rows"] = [{k: z.get(k) for k in ("pid", "trig", "trig_eth", "next", "B", "S", "exit", "ret")} for z in fos][:8]
    r["front_no20cap (sell 1 block after the first real buy, deadline +3000)"] = summarize([front(pl, sched_generic, hold=3000) for pl in pls])
    caps = [capacity(pl, sb) for pl in pls for sb in [sched_generic(pl, pl.b0 + 1)] if sb]
    r["capacity"] = {"n": len(caps), "cap_eth_p10_50_90": q([c["cap_eth"] for c in caps]), "src": collections.Counter(c["src"] for c in caps).most_common(2),
                     "Y_p10_50_90": q([c["Y"] for c in caps])}
    r["gas_usd_median"] = round(st.median(pl.gas for pl in pls) / 1e18 * USD_PER_ETH, 5)
    out[g] = r
    print("=" * 110); print(g)
    for k, v in r.items():
        if isinstance(v, dict) and "exits" in v: print("  %-22s %s" % (k, fmt_rule(v)))
        else: print("  %-22s %s" % (k, v))

# ------------------------------------------------------------------ the 2-ETH operator: its crowd, its pull, the hold rules
g = "F1-WIDE the 2-ETH fresh-wallet operator: F1 + " + F100
pls = [pool(x) for x in groups[g]]
X = {}
rows = []
for pl in pls:
    cr = [x for x in pl.buys() if is_crowd(x)]
    oth = [x for x in pl.buys() if not is_crowd(x) and x["from"] not in DUST_WALLETS and x["from"] != pl.p["launch_from"]]
    real_oth = [x for x in oth if x["eth"] >= MIN_REAL]
    rows.append({"pid": pl.pid[:12], "fee": pl.p["fee"], "val": pl.p["launch_value_eth"], "n_crowd": len(cr), "crowd_eth": round(sum(x["eth"] for x in cr) / 1e18, 4),
                 "first_crowd": (cr[0]["bn"] - pl.b0) if cr else None, "last_crowd": (cr[-1]["bn"] - pl.b0) if cr else None,
                 "gaps": [b["bn"] - a["bn"] for a, b in zip(cr, cr[1:])], "pull": (pl.pull_bn - pl.b0) if pl.pull_bn else None,
                 "pull_minus_last_crowd": (pl.pull_bn - cr[-1]["bn"]) if (pl.pull_bn and cr) else None,
                 "outsider_real_buys": [(x["bn"] - pl.b0, round(x["eth"] / 1e18, 6), (x["from"] or "?")[:10], (x["to"] or "?")[:10]) for x in real_oth],
                 "outsider_small_buys": len(oth) - len(real_oth), "crowd_minus_sells": sum(1 for x in pl.seq if not x["buy"] and is_crowd(dict(x, buy=True)))})
X["pools"] = rows
for z in rows: print(z)
X["crowd_n_p10_50_90"] = q([z["n_crowd"] for z in rows]); X["crowd_eth_p10_50_90"] = q([z["crowd_eth"] for z in rows])
X["first_crowd_p10_50_90"] = q([z["first_crowd"] for z in rows]); X["last_crowd_p10_50_90"] = q([z["last_crowd"] for z in rows])
X["gap_p10_50_90"] = q([g_ for z in rows for g_ in z["gaps"]]); X["pull_minus_last_crowd_p10_50_90"] = q([z["pull_minus_last_crowd"] for z in rows])
X["pools_without_crowd"] = [z["pid"] for z in rows if z["n_crowd"] == 0]
cs = [crowd for pl in pls for crowd in [sched_crowd(pl, pl.b0 + 1)] if crowd]
X["capacity_first_crowd_buy"] = {"cap_eth_p10_50_90": q([capacity(pl, c)["cap_eth"] for pl in pls for c in [sched_crowd(pl, pl.b0 + 1)] if c]),
                                 "note": "UR execute (V4_SWAP, actions 070b0e) not decoded: ASSUMED minOut = 0.99 x launch-state quote; the crowd buys come 190-460 blocks after the launch, so a launch-state quote is unlikely"}
rules = {}
for k in (1, 2, 3, 4, 5, 6, 8, 10):
    rules["front_k%d (buy +1, sell 1 block after the k-th crowd buy, else +3000)" % k] = summarize([front_kth(pl, k) for pl in pls])
for H in (100, 300, 500, 700, 900, 1100, 1300, 1500, 1700, 1900, 2100):
    rules["hold_%d (buy +1, sell at launch + %d)" % (H, H)] = summarize([pl.trade(pl.b0 + 1, pl.b0 + H) for pl in pls])
rules["crowd_follow (buy 1 block after the first crowd buy, sell 1 block after the next crowd buy)"] = summarize(
    [pl.trade(c[0]["bn"] + 1, c[1]["bn"] + 1) for pl in pls for c in [[x for x in pl.buys() if is_crowd(x)]] if len(c) >= 2])
X["rules"] = rules
for k, v in rules.items(): print("  %-80s %s" % (k, fmt_rule(v)))
# per-pool rows of the two best-looking rules
X["rows_front_k4"] = [{k: z.get(k) for k in ("S", "exit", "ret")} for z in [front_kth(pl, 4) for pl in pls]]
X["rows_hold_1300"] = [{k: z.get(k) for k in ("S", "exit", "ret")} for z in [pl.trade(pl.b0 + 1, pl.b0 + 1300) for pl in pls]]
out["F1-WIDE_detail"] = X
json.dump(out, open(os.path.join(HERE, "results.json"), "w"), indent=1, default=str)
