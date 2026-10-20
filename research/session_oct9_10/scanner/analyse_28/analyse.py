"""analyse_28: two assigned families + the controls, priced with common28.Pool (analyse_27/common27.py verbatim: the exact replay of
research/session_oct9_10/explore/chk/replay.py on the census: our buy at the END of block B after every other tx of B, every later swap replayed
by its own price shift, a volume-bot router buy under its own minOut dropped, our sell at the HEAD of block S, a pull at or before S = the stake
lost, the pool's own fee each way, a hook's ETH-side tax each way, gas 2 x 104,000 x the launch block's base fee).
  F1 SELECTOR:ec64ddcf|196|0|60|false   69 pools, one launch contract per launch, fresh wallet per launch (nonce 2), one tax hook per launch
  F2 CODEHASH:8ce82419|bc9d39fd|*|0|200|false   28 pools, one deployer 0xdc7a139c, launch through its beacon-proxy executors, hook 0xdbebc6a7
Hook taxes (hookfee*.py, postwindow.py): F2 hook 0xdbebc6a7: 1% of the gross ETH in on buys (ERC6909 mint of ETH to the hook = 1.0101% of a0
in 141 of 142 buy receipts) and 1% of the ETH out on sells (9 of 9 sell receipts). F1: one hook per pool; its tax = (1 - a0 / (tx value x (1 - the
router's cut))) in the 9 pools with receipts (2%..20%), else the hook's current getters 9731aa2e/f4364515 (bps; 1%..19%; equal to the measured value
in 6 of 9 pools, lower in 3: a lower bound on the launch-window tax). Writes results.json, prints analyse.out."""
import sys, os, json, statistics as st, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import common28
from common28 import *  # noqa

P = load_pools(); F = load_families(); T = load_txs(); M = load_blocks_meta()
ids = json.load(open(os.path.join(HERE, "pids.json")))
PW = json.load(open(os.path.join(HERE, "postwindow_logs.json")))
HF = json.load(open(os.path.join(HERE, "hookfee.json")))
F2_HOOK = "0xdbebc6a7b2a38197932b6e01fb0e57e71d726aec"; F2_DEPLOYER = "0xdc7a139c58701faac4b1c0b209989f1230ae5489"
common28.HOOK_ETH_TAX[F2_HOOK] = (10_000, 10_000)
ROUTER_CUT = {"0x65050a9b": 0.01, "0x2fe63b82": 0.005, "0x6131b5fa": 0.0025, "0xe492912f": 0.01, "0xf2251d75": 0.01}
meas = collections.defaultdict(list)
for r in HF:
    if r["fam"] == "F1" and r["side"] == "buy" and r["val"] and r["to"] in ROUTER_CUT:
        meas[r["pid"]].append(1 - (-r["a0"]) / (r["val"] * (1 - ROUTER_CUT[r["to"]])))
F1_TAX_SRC = {}
for pid in ids["F1"]:
    m = meas.get(pid[:10])
    if m:
        t = int(round(st.median(m), 3) * 1_000_000); F1_TAX_SRC[pid] = "measured"
    else:
        t = PW["f1_tax"][pid][0] * 100; F1_TAX_SRC[pid] = "getter_now"
    common28.HOOK_ETH_TAX[P[pid]["hooks"]] = (t, t)

groups = collections.OrderedDict()
groups["F1 SELECTOR:ec64ddcf|196|0|60|false"] = ids["F1"]
groups["F2 CODEHASH:8ce82419|bc9d39fd|*|0|200|false"] = ids["F2"]
V = [p["pid"] for p in P.values() if p["known"] == "vbot-v2.433"]
A = [p["pid"] for p in P.values() if p["known"] == "operator-A"]
E = load_events(set(ids["F1"] + ids["F2"]) | set(V) | set(A))
POOL = {}


def pool(pid):
    if pid not in POOL: POOL[pid] = Pool(P[pid], E.get(pid), T, M)
    return POOL[pid]


# the F2 operator's executors: the launch contracts of F2 and every swap sender of a tx sent by the F2 deployer
EXEC = set(P[x]["launch_to"] for x in ids["F2"])
for x in ids["F2"]:
    for y in pool(x).seq:
        if y["from"] == F2_DEPLOYER: EXEC.add(y["sender"])
EXEC_BY_TX = len(EXEC)
# plus every other swap sender of the F2 pools (to the head) whose code is the same 291-byte beacon proxy (beacon 0xc798752b; others_f2.py)
for a, c in json.load(open(os.path.join(HERE, "others_f2.json"))).items():
    if c and "c798752b80049e7a67457af36822f85df37ddd74" in c: EXEC.add(a)


def is_bot(x): return x["to"] == VBOT_ROUTER and x["sel"] == "c1120e3d"
def is_op(x): return x["sender"] in EXEC or x["from"] == F2_DEPLOYER


def real_buys(pl, after=None):
    """non-launch, non-relay buys of >= 0.0002 ETH, the chain-wide dust wallets excluded"""
    return [x for x in pl.buys() if x["eth"] >= MIN_REAL and x["from"] not in DUST_WALLETS and (after is None or x["bn"] > after)]


def sched_generic(pl, B): r = real_buys(pl, B); return r[0] if r else None
def sched_bot(pl, B): return next((x for x in pl.buys() if x["bn"] > B and is_bot(x)), None)
def sched_op(pl, B): return next((x for x in pl.buys() if x["bn"] > B and is_op(x)), None)


def front(pl, sched_fn, hold=20, stake=STAKE):
    """buy landing at launch + 1 (after every tx of that block); sell landing one block after the first scheduled buy, or at launch + hold"""
    lb = pl.b0; B = lb + 1; sb = sched_fn(pl, B)
    S = sb["bn"] + 1 if (sb and sb["bn"] + 1 <= lb + hold) else lb + hold
    r = pl.trade(B, S, stake); r["sched"] = (sb["bn"] - lb) if sb else None; r["pid"] = pl.pid; return r


def front_fixed(pl, S_rel, stake=STAKE):
    r = pl.trade(pl.b0 + 1, pl.b0 + S_rel, stake); r["pid"] = pl.pid; return r


def follow(pl, hold=4, stake=STAKE):
    """buy landing one block after the first real buy (>= 0.0002 ETH); sell one block after the next real buy behind ours, or at our buy + hold"""
    lb = pl.b0; rb = real_buys(pl)
    if not rb: return None
    trig = rb[0]; B = trig["bn"] + 1
    nxt = next((x for x in rb if x["bn"] > B), None)
    S = nxt["bn"] + 1 if (nxt and nxt["bn"] + 1 <= B + hold) else B + hold
    r = pl.trade(B, S, stake); r.update({"pid": pl.pid, "trig": trig["bn"] - lb, "trig_eth": trig["eth"] / 1e18, "next": (nxt["bn"] - lb) if nxt else None}); return r


def capacity(pl, sb):
    s, L = pl.launch_state(); fee = pl.fee_at(sb["bn"]); Y = sb["eth"]
    quote = v4math.buy_out_int(int(s), L, Y, fee)
    if is_bot(sb) and sb["input"]:
        mo = word(sb["input"], 4); src = "calldata word 4 (bot router c1120e3d)"
    elif sb["sel"] == "ba20dec0" and sb["clen"] == 260:
        mo = 0; src = "F2 executor ba20dec0 (8 words: PM, PoolKey, zeroForOne, amountIn): no minOut in the calldata -> not bounded by a slippage check (the beacon implementation was not decoded)"
    elif sb["sel"] == "3593564c":
        mo = int(quote * 0.99); src = "Universal-Router execute (nested, not decoded): ASSUMED minOut = 0.99 x launch-state quote"
    else:
        mo = int(quote * 0.99); src = "router %s sel %s not decoded: ASSUMED minOut = 0.99 x launch-state quote" % ((sb["to"] or "?")[:10], sb["sel"])
    return {"cap_eth": room(s, L, Y, fee, mo), "src": src, "minout_over_quote": (mo / quote) if quote else None, "Y": Y / 1e18}


out = {"window_days": WINDOW_DAYS, "window_blocks": WINDOW_BLOCKS}
# ------------------------------------------------------------------ controls (calibrate the method)
C = {}
rs = [front(pool(x), sched_bot) for x in V]
C["v2433_front_bot_sched_all"] = summarize(rs)
C["v2433_sched_off_p10_50_90"] = q([r["sched"] for r in rs if r["sched"] is not None])
lw = [r for x, r in zip(V, rs) if 84880000 <= P[x]["launch_block"] <= 84970000]
C["v2433_front_livewindow_oct10_0907_1139"] = summarize(lw)
C["v2433_front_bot_bought_by_20 (sold one block after the bot's buy)"] = summarize([r for r in rs if r["sched"] is not None and r["sched"] + 1 <= 20])
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
C["live_relay_calibration (our real relay round trips re-priced by the model, gross)"] = {"n": len(diffs), "real_mean": round(st.mean(z[1] for z in diffs), 5),
    "model_mean": round(st.mean(z[2] for z in diffs), 5), "abs_diff_median": st.median(abs(z) for z in d), "within_0.5pt": sum(1 for z in d if abs(z) < 0.005)}
fa = [r for r in (follow(pool(x)) for x in A) if r]
C["opA_follow"] = summarize(fa); C["opA_follow_trig_p10_50_90"] = q([r["trig"] for r in fa])
C["gas_usd_per_trade_v2433_median"] = round(st.median(pool(x).gas for x in V) / 1e18 * USD_PER_ETH, 5)
out["controls"] = C
print("CONTROLS")
for k, v in C.items(): print("  ", k, fmt_rule(v) if isinstance(v, dict) and "exits" in v else v)


# ------------------------------------------------------------------ families
def analyse_group(g, pids, sched_fn, op_fn=None):
    pls = [pool(x) for x in pids]; ps = [P[x] for x in pids]
    r = {"count": len(ps), "launches_per_day": round(len(ps) / WINDOW_DAYS, 2), "first_last_ts": [min(p["launch_ts"] for p in ps), max(p["launch_ts"] for p in ps)],
         "launch_to_sel_len": collections.Counter("%s:%s:%s" % (p["launch_to"], p["selector"], p["calldata_len"]) for p in ps).most_common(4),
         "n_launch_to": len(set(p["launch_to"] for p in ps)), "to_code": collections.Counter("%s:%s" % (p["to_code_size"], (p["to_code_hash"] or "")[:8]) for p in ps).most_common(3),
         "deployers": collections.Counter(p["launch_from"] for p in ps).most_common(5), "n_deployers": len(set(p["launch_from"] for p in ps)),
         "deployer_nonce_p10_50_90": q([p["launch_nonce"] for p in ps]),
         "values_eth": collections.Counter(p["launch_value_eth"] for p in ps).most_common(3),
         "fees": collections.Counter(p["fee"] for p in ps).most_common(6), "hooks": collections.Counter(p["hooks"] for p in ps).most_common(3), "n_hooks": len(set(p["hooks"] for p in ps)),
         "launch_ranges": collections.Counter(str([(a["lo"] - p["tick0"], a["hi"] - p["tick0"]) for a in pool(p["pid"]).adds if a["tx"] == p["launch_tx"]]) for p in ps).most_common(3),
         "tick0": collections.Counter(p["tick0"] for p in ps).most_common(4),
         "liq_launch_p10_50_90": q([p["liq_launch"] for p in ps]), "buy_in_launch_tx": sum(1 for p in ps if p["buy_in_launch_tx"]),
         "start": collections.Counter(pl.start for pl in pls).most_common(), "later_adds_pools": sum(1 for pl in pls if len(pl.adds) > 1),
         "pools_with_events": sum(1 for p in ps if p["has_events"]), "eth_tax_buy_sell_ppm": collections.Counter(str(pl.etax) for pl in pls).most_common(8)}
    lt = [pl.seq for pl in pls]
    r["launch_tx_buy_eth_p10_50_90"] = q([sum(x["eth"] for x in pl.seq if x["in_launch"] and x["buy"]) / 1e18 for pl in pls], nd=9)
    fb = [(pl, pl.buys()[0]) for pl in pls if pl.buys()]
    r["first_buy_any"] = {"pools_with": len(fb), "frac": round(len(fb) / len(pls), 3), "off_p10_50_90": q([x["bn"] - pl.b0 for pl, x in fb]),
                          "eth_p10_50_90": q([x["eth"] / 1e18 for pl, x in fb], nd=9), "to_sel": collections.Counter("%s:%s" % (x["to"], x["sel"]) for pl, x in fb).most_common(5),
                          "from": collections.Counter(x["from"] for pl, x in fb).most_common(4), "n_from": len(set(x["from"] for pl, x in fb)),
                          "n_to": len(set(x["to"] for pl, x in fb)), "nonce_p10_50_90": q([x["nonce"] for pl, x in fb])}
    fr = [(pl, real_buys(pl)[0]) for pl in pls if real_buys(pl)]
    r["first_buy_real"] = {"pools_with": len(fr), "frac": round(len(fr) / len(pls), 3), "off_p10_50_90": q([x["bn"] - pl.b0 for pl, x in fr]),
                           "eth_p10_50_90": q([x["eth"] / 1e18 for pl, x in fr]), "to_sel_len": collections.Counter("%s:%s:%s" % (x["to"], x["sel"], x["clen"]) for pl, x in fr).most_common(4),
                           "n_from": len(set(x["from"] for pl, x in fr)), "nonce0": sum(1 for pl, x in fr if x["nonce"] == 0),
                           "by_launch_wallet": sum(1 for pl, x in fr if x["from"] == pl.p["launch_from"]),
                           "from_top": collections.Counter(x["from"] for pl, x in fr).most_common(4)}
    if op_fn:
        so = [(pl, sched_fn(pl, pl.b0)) for pl in pls]; so = [(pl, x) for pl, x in so if x]
        r["first_sched_buy"] = {"pools_with": len(so), "frac": round(len(so) / len(pls), 3), "off_p10_50_90": q([x["bn"] - pl.b0 for pl, x in so]),
                                "off_hist": collections.Counter(x["bn"] - pl.b0 for pl, x in so).most_common(8),
                                "eth_p10_50_90": q([x["eth"] / 1e18 for pl, x in so], nd=9), "to_sel_len": collections.Counter("%s:%s:%s" % (x["to"], x["sel"], x["clen"]) for pl, x in so).most_common(3),
                                "n_to_contracts": len(set(x["to"] for pl, x in so)), "from": collections.Counter(x["from"] for pl, x in so).most_common(2),
                                "same_contract_as_launch": sum(1 for pl, x in so if x["to"] == pl.p["launch_to"])}
        ob = [(pl, [x for x in pl.buys() if op_fn(x)]) for pl in pls]
        r["op_buys_first3000"] = {"n_per_pool_p10_50_90": q([len(v) for pl, v in ob]), "eth_per_pool_p10_50_90": q([sum(x["eth"] for x in v) / 1e18 for pl, v in ob], nd=6),
                                  "eth_by_+50_p10_50_90": q([sum(x["eth"] for x in v if x["bn"] - pl.b0 <= 50) / 1e18 for pl, v in ob], nd=6),
                                  "gap_between_op_buys_hist": collections.Counter(b["bn"] - a["bn"] for pl, v in ob for a, b in zip(v, v[1:]) if b["bn"] - pl.b0 <= 120).most_common(8)}
    allsw = [x for pl in pls for x in pl.seq if not x["in_launch"]]
    r["swaps_non_launch"] = {"total": len(allsw), "buys": sum(1 for x in allsw if x["buy"]), "sells": sum(1 for x in allsw if not x["buy"]),
                             "buys_ge_0.0002": sum(1 for x in allsw if x["buy"] and x["eth"] >= MIN_REAL),
                             "eth_in": round(sum(x["eth"] for x in allsw if x["buy"]) / 1e18, 6), "eth_out_sells": round(sum(x["eth"] for x in allsw if not x["buy"]) / 1e18, 6),
                             "pools_with_any": sum(1 for pl in pls if any(not x["in_launch"] for x in pl.seq)),
                             "senders_top": collections.Counter(x["sender"] for x in allsw).most_common(6),
                             "from_top (first-8 txs only)": collections.Counter(x["from"] for x in allsw if x["from"]).most_common(6),
                             "to_sel_top": collections.Counter("%s:%s" % (x["to"], x["sel"]) for x in allsw if x["to"]).most_common(5),
                             "sell_off_p10_50_90": q([x["bn"] - pl.b0 for pl in pls for x in pl.seq if not x["in_launch"] and not x["buy"]])}
    if op_fn:
        r["swaps_non_launch"]["by_operator"] = sum(1 for x in allsw if op_fn(x)); r["swaps_non_launch"]["by_others"] = sum(1 for x in allsw if not op_fn(x))
        r["swaps_non_launch"]["others_eth_in"] = round(sum(x["eth"] for x in allsw if x["buy"] and not op_fn(x)) / 1e18, 6)
    pl_ = [(pl, pl.pulls[0]) for pl in pls if pl.pulls]
    r["pull"] = {"pulled_3000": len(pl_), "frac": round(len(pl_) / len(pls), 3), "off_launch_p10_50_90": q([x["bn"] - pl.b0 for pl, x in pl_]),
                 "off_from_first_real_buy_p10_50_90": q([x["bn"] - real_buys(pl)[0]["bn"] for pl, x in pl_ if real_buys(pl)]),
                 "by_launch_wallet": sum(1 for pl, x in pl_ if pl.p["first_pull_from"] == pl.p["launch_from"]),
                 "via": collections.Counter("%s:%s" % (pl.p["first_pull_to"], pl.p["first_pull_selector"]) for pl, x in pl_).most_common(3)}
    ml = [l for l in PW["ml_all"] if l["topics"][1] in set(pids)]
    from chain_w import sgn_w
    neg = [l for l in ml if sgn_w(l["data"], 2) < 0]
    if set(pids) <= set(ids["F1"] + ids["F2"]):
        r["pull"]["to_head (eth_getLogs ModifyLiquidity, launch .. head %d)" % PW["head"]] = {"modify_liquidity_logs": len(ml), "negative": len(neg),
            "blocks_watched_p10_50_90": q([PW["head"] - p["launch_block"] for p in ps])}
    # trap test: outsiders = non-launch buys before the first scheduled buy by others than the operator (dust wallets apart)
    wo, wi, out_sizes, out_from = [], [], [], collections.Counter()
    for pl in pls:
        sb = sched_fn(pl, pl.b0)
        outs = [x for x in pl.buys() if (sb is None or (x["bn"], x["li"]) < (sb["bn"], sb["li"])) and x["from"] != pl.p["launch_from"] and x["from"] not in DUST_WALLETS
                and not (op_fn and op_fn(x))]
        pb = pl.pull_bn
        if outs: wi.append((pb - outs[0]["bn"]) if pb is not None else None); out_sizes += [x["eth"] / 1e18 for x in outs]; out_from.update(x["from"] or x["sender"] for x in outs)
        else: wo.append((pb - pl.b0) if pb is not None else None)
    r["trap"] = {"pools_with_outsider_before_sched": len(wi), "outsider_eth_p10_50_90": q(out_sizes, nd=9), "outsider_wallets": out_from.most_common(5),
                 "pulled_after_outsider": sum(1 for z in wi if z is not None), "delay_after_outsider_p10_50_90": q([z for z in wi if z is not None]),
                 "pools_without": len(wo), "pulled_without": sum(1 for z in wo if z is not None), "pull_off_without_p10_50_90": q([z for z in wo if z is not None])}
    frs = [front(pl, sched_fn) for pl in pls]
    r["front"] = summarize(frs)
    r["front_sched_off_p10_50_90"] = q([z["sched"] for z in frs if z.get("sched") is not None])
    r["front_sold_by"] = collections.Counter("sched+1" if (z.get("sched") is not None and z["sched"] + 1 <= 20) else "deadline+20" for z in frs).most_common()
    r["front_rows"] = [{k: (round(z[k], 5) if isinstance(z.get(k), float) else z.get(k)) for k in ("pid", "sched", "S", "exit", "ret", "gross", "fee_b", "fee_s")} for z in frs][:8]
    fos = [z for z in (follow(pl) for pl in pls) if z]
    r["follow"] = summarize(fos); r["follow_rows"] = [{k: (round(z[k], 5) if isinstance(z.get(k), float) else z.get(k)) for k in ("pid", "trig", "trig_eth", "next", "B", "S", "exit", "ret")} for z in fos][:8]
    r["front_no20cap (sell 1 block after the first scheduled buy, deadline +3000)"] = summarize([front(pl, sched_fn, hold=3000) for pl in pls])
    r["front_gross_mean (before gas, after taxes)"] = round(st.mean(z["gross"] for z in frs if z.get("gross") is not None), 5) if any(z.get("gross") is not None for z in frs) else None
    caps = [capacity(pl, sb) for pl in pls for sb in [sched_fn(pl, pl.b0 + 1)] if sb]
    r["capacity"] = {"n": len(caps), "cap_eth_p10_50_90": q([c["cap_eth"] for c in caps]), "src": collections.Counter(c["src"] for c in caps).most_common(2),
                     "Y_p10_50_90": q([c["Y"] for c in caps], nd=6)}
    r["gas_usd_median"] = round(st.median(pl.gas for pl in pls) / 1e18 * USD_PER_ETH, 5)
    return r


with open(os.path.join(HERE, "chain_w.py"), "w") as fh:
    fh.write("def sgn_w(d, i):\n    x = int(d[2 + 64 * i: 2 + 64 * (i + 1)], 16)\n    return x - (1 << 256) if x >= (1 << 255) else x\n")
sys.path.insert(0, HERE)
specs = {"F1 SELECTOR:ec64ddcf|196|0|60|false": (sched_generic, None), "F2 CODEHASH:8ce82419|bc9d39fd|*|0|200|false": (sched_op, is_op)}
for g, pids in groups.items():
    fn, opf = specs[g]
    r = analyse_group(g, pids, fn, opf); out[g] = r
    print("=" * 110); print(g)
    for k, v in r.items():
        if isinstance(v, dict) and "exits" in v: print("  %-22s %s" % (k, fmt_rule(v)))
        else: print("  %-22s %s" % (k, v))
# ------------------------------------------------------------------ F2 extras: the operator's schedule, fixed holds (no pull ever), and the trade with no tax (what the tax costs)
g2 = "F2 CODEHASH:8ce82419|bc9d39fd|*|0|200|false"; X2 = {}
for H in (5, 11, 13, 20, 30, 50, 100, 200, 500, 1000, 2000):
    X2["front_fixed_sell_at_launch+%d" % H] = summarize([front_fixed(pool(x), H) for x in ids["F2"]])
save = common28.HOOK_ETH_TAX[F2_HOOK]; common28.HOOK_ETH_TAX[F2_HOOK] = (0, 0)
for x in ids["F2"]: POOL.pop(x, None)
X2["front_rule_IF_NO_HOOK_TAX"] = summarize([front(pool(x), sched_op) for x in ids["F2"]])
X2["front_fixed_+50_IF_NO_HOOK_TAX"] = summarize([front_fixed(pool(x), 50) for x in ids["F2"]])
common28.HOOK_ETH_TAX[F2_HOOK] = save
for x in ids["F2"]: POOL.pop(x, None)
# the whole life of the F2 pools to the head (Swap logs): who trades, when the operator sells
sw = collections.defaultdict(list)
for l in PW["swap_f2"]:
    d = l["data"]; a0 = int(d[2:66], 16); a0 = a0 - (1 << 256) if a0 >= (1 << 255) else a0
    sw[l["topics"][1]].append((int(l["blockNumber"], 16), "0x" + l["topics"][2][-40:], a0))
life = {"swaps_to_head": len(PW["swap_f2"]), "by_executor": sum(1 for v in sw.values() for b, s, a in v if s in EXEC),
        "by_other_senders": collections.Counter(s for v in sw.values() for b, s, a in v if s not in EXEC).most_common(6),
        "other_eth_in": round(sum(-a for v in sw.values() for b, s, a in v if s not in EXEC and a < 0) / 1e18, 6),
        "op_sell_off_p10_50_90": q([b - P[pid]["launch_block"] for pid, v in sw.items() for b, s, a in v if s in EXEC and a > 0]),
        "op_net_eth_per_pool_p10_50_90 (sells - buys, launch-tx buy included)": q([sum(a for b, s, a in v if s in EXEC) / 1e18 for v in sw.values()], nd=6),
        "n_executors": len(EXEC), "n_executors_seen_in_deployer_txs": EXEC_BY_TX}
X2["life_to_head"] = life
out[g2]["extras"] = X2
print("=" * 110); print("F2 extras")
for k, v in X2.items(): print("  %-40s %s" % (k, fmt_rule(v) if isinstance(v, dict) and "exits" in v else v))
# ------------------------------------------------------------------ F1 extras: tax source and the taxes
g1 = "F1 SELECTOR:ec64ddcf|196|0|60|false"
out[g1]["extras"] = {"tax_source": collections.Counter(F1_TAX_SRC.values()).most_common(), "tax_ppm_used": collections.Counter(pool(x).etax[0] for x in ids["F1"]).most_common(),
                     "measured_tax_by_pool": {k: [round(z, 4) for z in v][:3] for k, v in meas.items()}, "tax_now_bps": collections.Counter(tuple(v) for v in PW["f1_tax"].values()).most_common(),
                     "front_IF_NO_HOOK_TAX": None}
for x in ids["F1"]: common28.HOOK_ETH_TAX[P[x]["hooks"]] = (0, 0); POOL.pop(x, None)
out[g1]["extras"]["front_IF_NO_HOOK_TAX"] = summarize([front(pool(x), sched_generic) for x in ids["F1"]])
out[g1]["extras"]["follow_IF_NO_HOOK_TAX"] = summarize([z for z in (follow(pool(x)) for x in ids["F1"]) if z])
print("=" * 110); print("F1 extras")
for k, v in out[g1]["extras"].items(): print("  %-40s %s" % (k, fmt_rule(v) if isinstance(v, dict) and "exits" in v else v))
# ------------------------------------------------------------------ the controls through the same per-family pipeline
for g, pids in (("CONTROL vbot-v2.433", V), ("CONTROL operator-A", A)):
    r = analyse_group(g, pids, sched_bot if g.endswith("v2.433") else sched_generic)
    if g.endswith("v2.433"):
        bb = [(pool(x), sched_bot(pool(x), P[x]["launch_block"])) for x in V]
        bb = [(pl, x) for pl, x in bb if x]
        r["bot_buy"] = {"pools_with": len(bb), "frac": round(len(bb) / len(V), 3), "off_p10_50_90": q([x["bn"] - pl.b0 for pl, x in bb]),
                        "eth_p10_50_90": q([x["eth"] / 1e18 for pl, x in bb]), "n_from": len(set(x["from"] for pl, x in bb)),
                        "pull_minus_bot_buy_p10_50_90": q([pl.pull_bn - x["bn"] for pl, x in bb if pl.pull_bn]),
                        "minout_over_launch_quote_p10_50_90": q([capacity(pl, x)["minout_over_quote"] for pl, x in bb], nd=5)}
    out[g] = r
    print("=" * 110); print(g)
    for k, v in r.items():
        if k.endswith("_rows"): continue
        if isinstance(v, dict) and "exits" in v: print("  %-22s %s" % (k, fmt_rule(v)))
        else: print("  %-22s %s" % (k, v))
# ------------------------------------------------------------------ pricer check inside the assigned families: every observed buy re-priced from the model state
chk = []
for g, pids in groups.items():
    for x in pids:
        pl = pool(x)
        for y in pl.seq:
            if y["buy"] and not y["relay"]:
                st_, Lst = pl.state_through(None, upto_li=(y["bn"], y["li"]))
                pred = v4math.buy_out_int(int(st_), Lst, y["eth"], y["fee"])
                chk.append((g.split()[0], (pred - y["a1"]) / y["a1"] if y["a1"] else None))
out["pricer_check_assigned"] = {g: {"n": sum(1 for a, b in chk if a == g), "max_abs_rel_err": max((abs(b) for a, b in chk if a == g and b is not None), default=None),
                                    "median_abs_rel_err": st.median([abs(b) for a, b in chk if a == g and b is not None])} for g in sorted(set(a for a, b in chk))}
print("PRICER CHECK (model tokens out vs the Swap event, every buy in the assigned groups):", out["pricer_check_assigned"])
json.dump(out, open(os.path.join(HERE, "results.json"), "w"), indent=1, default=str)
