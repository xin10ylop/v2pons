"""analyse_26: four assigned families (orchestrator keys LAUNCHER:<to>|<selector>|<calldata_len>, any fee / tick spacing)
  F1 POSM multicall 54,500 bytes (70 pools per tx, value 0.000735)    F2 POSM multicall 46,788 bytes (60 pools per tx, value 0.00063)
  F3 operator A's launcher 0x3194e326 2fcb9108 (control, follow)       F4 PoolManager.initialize called directly (6276cbbe, 196 bytes), all 336 pools
     + its sub-families F4a (fee 500, ts 1, no hook: 192 pools, 192 fresh deployers), F4b (fee 500, ts 1, a hook per pool: 23), F4c (the other 121)
+ the controls (vbot-v2.433 front with the bot's router buy as the schedule; operator A follow) and the live-relay calibration.
Pricer: common26.Pool (the exact replay of explore/chk/replay.py on the census: our buy at the END of block B after every other tx of B, every later
swap replayed by its own price shift, a volume-bot router buy under its own minOut dropped, our sell at the HEAD of block S, a pull at or before S
= the stake lost, the pool's own fee each way, gas 2 x 104,000 x the launch block's base fee).
The anchor ("launch") of every rule is the LIVE block = the block of the pool's first liquidity add (the launch block itself for POSM / operator A
launches, whose mint is in the launch tx; ~40 blocks after the Initialize for F4, whose liquidity comes in a separate POSM modifyLiquidities tx).
Writes results.json, prints analyse.out."""
import sys, os, json, statistics as st, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common26 import *  # noqa

P = load_pools(); T = load_txs(); M = load_blocks_meta()
ADD = json.load(open(os.path.join(HERE, "cache", "add_txs.json")))
POSM = "0x58daec3116aae6d93017baaea7749052e8a04fa7"; PMA = "0x8366a39cc670b4001a1121b8f6a443a643e40951"; OPA = "0x3194e32622c5d860a0572c74edda99dcfd8fc827"
CROWD7169 = "7169b574"
fam = lambda to, sel, ln: [p["pid"] for p in P.values() if p["launch_to"] == to and p["selector"] == sel and p["calldata_len"] == ln]
F4 = fam(PMA, "6276cbbe", 196)
groups = collections.OrderedDict()
groups["F1 LAUNCHER:POSM|ac9650d8|54500"] = fam(POSM, "ac9650d8", 54500)
groups["F2 LAUNCHER:POSM|ac9650d8|46788"] = fam(POSM, "ac9650d8", 46788)
groups["F3 LAUNCHER:0x3194e326|2fcb9108|644 (operator A, control)"] = fam(OPA, "2fcb9108", 644)
groups["F4 LAUNCHER:PoolManager|6276cbbe|196 (all)"] = F4
groups["F4a fee 500 ts 1 no hook"] = [x for x in F4 if P[x]["fee"] == 500 and P[x]["tick_spacing"] == 1 and P[x]["hooks_zero"]]
groups["F4b fee 500 ts 1 hooked"] = [x for x in F4 if P[x]["fee"] == 500 and P[x]["tick_spacing"] == 1 and not P[x]["hooks_zero"]]
groups["F4c the rest of F4"] = [x for x in F4 if not (P[x]["fee"] == 500 and P[x]["tick_spacing"] == 1)]
V = [p["pid"] for p in P.values() if p["known"] == "vbot-v2.433"]
A = [p["pid"] for p in P.values() if p["known"] == "operator-A"]
E = load_events(set(x for v in groups.values() for x in v) | set(V) | set(A))
POOL = {}


def pool(pid):
    if pid not in POOL: POOL[pid] = Pool(P[pid], E.get(pid), T, M)
    return POOL[pid]


def anchor(pl): return live_block(pl)
def is_bot(x): return x["to"] == VBOT_ROUTER and x["sel"] == "c1120e3d"
def is_crowd7169(x): return x["sel"] == CROWD7169


def real_buys(pl, after=None):
    """non-launch, non-relay buys of >= 0.0002 ETH, the chain-wide dust wallets excluded"""
    return [x for x in pl.buys() if x["eth"] >= MIN_REAL and x["from"] not in DUST_WALLETS and (after is None or x["bn"] > after)]


def sched_generic(pl, B): r = real_buys(pl, B); return r[0] if r else None
def sched_bot(pl, B): return next((x for x in pl.buys() if x["bn"] > B and is_bot(x)), None)


def front(pl, sched_fn, hold=20, stake=STAKE):
    """buy landing at anchor + 1 (after every tx of that block); sell landing one block after the first scheduled buy, or at anchor + hold"""
    lb = anchor(pl); B = lb + 1; sb = sched_fn(pl, B)
    S = sb["bn"] + 1 if (sb and sb["bn"] + 1 <= lb + hold) else lb + hold
    r = pl.trade(B, S, stake); r["sched"] = (sb["bn"] - lb) if sb else None; r["pid"] = pl.pid
    r["late"] = any(x["bn"] <= B for x in real_buys(pl)); return r


def follow(pl, hold=4, stake=STAKE):
    """buy landing one block after the first real buy (>= 0.0002 ETH); sell one block after the next real buy behind ours, or at our buy + hold"""
    lb = anchor(pl); rb = real_buys(pl)
    if not rb: return None
    trig = rb[0]; B = trig["bn"] + 1
    nxt = next((x for x in rb if x["bn"] > B), None)
    S = nxt["bn"] + 1 if (nxt and nxt["bn"] + 1 <= B + hold) else B + hold
    r = pl.trade(B, S, stake); r.update({"pid": pl.pid, "trig": trig["bn"] - lb, "trig_eth": trig["eth"] / 1e18, "next": (nxt["bn"] - lb) if nxt else None}); return r


def ride(pl, K, stake=STAKE):
    """variant: buy landing at anchor + 1, sell at anchor + K whatever happens (the pull at or before = lost)"""
    lb = anchor(pl); r = pl.trade(lb + 1, lb + K, stake); r["pid"] = pl.pid; return r


def dec7169(x):
    """crowd router 7169b574 (a struct: word 1 = the Universal Router, 4 = token, 5 = recipient, 6 = amountIn, 7 = minOut?, 10 = fee, 11 = tick
    spacing, 12 = hooks); returns (amountIn, word7) or None"""
    inp = x["input"]
    if not inp or len(inp) < 10 + 64 * 13: return None
    return word(inp, 6), word(inp, 7), word(inp, 10), word(inp, 11), word(inp, 12)


def capacity(pl, sb):
    s, L = pl.launch_state(); fee = pl.fee_at(sb["bn"]); Y = sb["eth"]
    quote = v4math.buy_out_int(int(s), L, Y, fee)
    if is_bot(sb) and sb["input"]:
        mo = word(sb["input"], 4); src = "calldata word 4 (bot router c1120e3d)"
    elif is_crowd7169(sb) and dec7169(sb) and dec7169(sb)[0] == Y:
        mo = dec7169(sb)[1]; src = "calldata word 7 of the 7169b574 router (word 6 = amountIn matches the swap): the decoded minOut"
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
C["v2433_front_bot_bought_by_20"] = summarize([r for r in rs if r["sched"] is not None and r["sched"] + 1 <= 20])
C["v2433_front_generic_sched"] = summarize([front(pool(x), sched_generic) for x in V])
caps = [capacity(pool(x), sb) for x in V for sb in [sched_bot(pool(x), P[x]["launch_block"])] if sb]
C["v2433_capacity_p10_50_90"] = q([c["cap_eth"] for c in caps]); C["v2433_minout_over_quote_p10_50_90"] = q([c["minout_over_quote"] for c in caps], nd=5)
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
C["live_relay_calibration"] = {"what": "our real relay round trips (one buy, one sell) re-priced by the model, gross", "n": len(diffs),
                               "real_mean": round(st.mean(z[1] for z in diffs), 5), "model_mean": round(st.mean(z[2] for z in diffs), 5),
                               "abs_diff_median": st.median(abs(z) for z in d), "abs_diff_max": max(abs(z) for z in d), "within_0.5pt": sum(1 for z in d if abs(z) < 0.005)}
fa = [r for r in (follow(pool(x)) for x in A) if r]
C["opA_follow"] = summarize(fa); C["opA_follow_trig_p10_50_90"] = q([r["trig"] for r in fa])
C["gas_usd_per_trade_v2433_median"] = round(st.median(pool(x).gas for x in V) / 1e18 * USD_PER_ETH, 5)
out["controls"] = C
print("CONTROLS")
for k, v in C.items(): print("  ", k, fmt_rule(v) if isinstance(v, dict) and "exits" in v else v)


# ------------------------------------------------------------------ families
def analyse_group(g, pids):
    pls = [pool(x) for x in pids]; ps = [P[x] for x in pids]
    r = {"count": len(ps), "launches_per_day": round(len(ps) / WINDOW_DAYS, 2), "launch_txs": len(set(p["launch_tx"] for p in ps)),
         "launch_txs_per_day": round(len(set(p["launch_tx"] for p in ps)) / WINDOW_DAYS, 2),
         "first_last_ts": [min(p["launch_ts"] for p in ps), max(p["launch_ts"] for p in ps)],
         "launch_to_sel_len": collections.Counter("%s:%s:%s" % (p["launch_to"], p["selector"], p["calldata_len"]) for p in ps).most_common(3),
         "deployers": collections.Counter(p["launch_from"] for p in ps).most_common(4), "n_deployers": len(set(p["launch_from"] for p in ps)),
         "deployer_nonce_p10_50_90": q([p["launch_nonce"] for p in ps]),
         "values_eth": collections.Counter(p["launch_value_eth"] for p in ps).most_common(6),
         "fees": collections.Counter(p["fee"] for p in ps).most_common(6), "n_fees": len(set(p["fee"] for p in ps)),
         "tick_spacings": collections.Counter(p["tick_spacing"] for p in ps).most_common(4), "hooks": collections.Counter(p["hooks"] for p in ps).most_common(3),
         "n_hooks": len(set(p["hooks"] for p in ps)), "tokens": len(set(p["token"] for p in ps)),
         "init_to_live_blocks_p10_50_90": q([anchor(pl) - pl.b0 for pl in pls if pl.adds]), "no_liquidity_add": sum(1 for pl in pls if not pl.adds),
         "live_ranges": collections.Counter(str([(a["lo"], a["hi"]) for a in pl.adds if a["tx"] == pl.live_tx]) for pl in pls).most_common(3),
         "L0_p10_50_90": q([pl.L0 for pl in pls]), "start": collections.Counter(pl.start for pl in pls).most_common(),
         "virtual_eth_reserve_p10_50_90": q([pl.L0 / (pl.s_eff / Q96) / 1e18 for pl in pls if pl.L0 and pl.s_eff], nd=8),
         "later_adds_pools": sum(1 for pl in pls if len(pl.adds) > 1), "pools_with_events": sum(1 for p in ps if p["has_events"])}
    addtx = [ADD.get(pl.live_tx) or T.get(pl.live_tx) for pl in pls if pl.adds and pl.live_tx != pl.p["launch_tx"]]
    addtx = [t for t in addtx if t]
    if addtx:
        r["add_tx"] = {"n": len(addtx), "to_sel_len": collections.Counter("%s:%s:%s" % (t["to"], t["selector"], t["calldata_len"]) for t in addtx).most_common(3),
                       "by_launch_wallet": sum(1 for pl in pls for t in [ADD.get(pl.live_tx) or T.get(pl.live_tx)] if t and pl.live_tx != pl.p["launch_tx"] and t["from"] == pl.p["launch_from"]),
                       "value_eth": collections.Counter(round(t["value_wei"] / 1e18, 6) for t in addtx).most_common(5), "nonce": collections.Counter(t["nonce"] for t in addtx).most_common(4)}
    fb = [(pl, pl.buys()[0]) for pl in pls if pl.buys()]
    r["first_buy_any"] = {"pools_with": len(fb), "frac": round(len(fb) / len(pls), 3), "off_live_p10_50_90": q([x["bn"] - anchor(pl) for pl, x in fb]),
                          "eth_p10_50_90": q([x["eth"] / 1e18 for pl, x in fb], nd=10), "to_sel": collections.Counter("%s:%s" % (x["to"], x["sel"]) for pl, x in fb).most_common(4),
                          "from": collections.Counter(x["from"] for pl, x in fb).most_common(4), "n_from": len(set(x["from"] for pl, x in fb))}
    fr = [(pl, real_buys(pl)[0]) for pl in pls if real_buys(pl)]
    r["first_buy_real"] = {"pools_with": len(fr), "frac": round(len(fr) / len(pls), 3), "off_live_p10_50_90": q([x["bn"] - anchor(pl) for pl, x in fr]),
                           "off_init_p10_50_90": q([x["bn"] - pl.b0 for pl, x in fr]),
                           "eth_p10_50_90": q([x["eth"] / 1e18 for pl, x in fr]), "to_sel_len": collections.Counter("%s:%s:%s" % (x["to"], x["sel"], x["clen"]) for pl, x in fr).most_common(4),
                           "n_from": len(set(x["from"] for pl, x in fr)), "nonce_p10_50_90": q([x["nonce"] for pl, x in fr]),
                           "by_launch_wallet": sum(1 for pl, x in fr if x["from"] == pl.p["launch_from"]),
                           "from_top": collections.Counter(x["from"] for pl, x in fr).most_common(4),
                           "same_block_as_live": sum(1 for pl, x in fr if x["bn"] == anchor(pl)), "at_live_plus_1": sum(1 for pl, x in fr if x["bn"] == anchor(pl) + 1)}
    allsw = [x for pl in pls for x in pl.seq if not x["in_launch"]]
    r["swaps_non_launch"] = {"total": len(allsw), "buys": sum(1 for x in allsw if x["buy"]), "sells": sum(1 for x in allsw if not x["buy"]),
                             "buys_ge_0.0002": sum(1 for x in allsw if x["buy"] and x["eth"] >= MIN_REAL),
                             "eth_in": round(sum(x["eth"] for x in allsw if x["buy"]) / 1e18, 6), "eth_out_sells": round(sum(x["eth"] for x in allsw if not x["buy"]) / 1e18, 6),
                             "pools_with_any": sum(1 for pl in pls if any(not x["in_launch"] for x in pl.seq)),
                             "from_top(first 8 swaps)": collections.Counter(x["from"] for x in allsw if x["from"]).most_common(6),
                             "to_sel_top(first 8 swaps)": collections.Counter("%s:%s" % (x["to"], x["sel"]) for x in allsw if x["to"]).most_common(5),
                             "sell_off_live_p10_50_90": q([x["bn"] - anchor(pl) for pl in pls for x in pl.seq if not x["in_launch"] and not x["buy"]])}
    pl_ = [(pl, pl.pulls[0]) for pl in pls if pl.pulls]
    r["pull"] = {"pulled_3000": len(pl_), "frac": round(len(pl_) / len(pls), 3), "off_live_p10_50_90": q([x["bn"] - anchor(pl) for pl, x in pl_]),
                 "off_from_first_real_buy_p10_50_90": q([x["bn"] - real_buys(pl)[0]["bn"] for pl, x in pl_ if real_buys(pl)]),
                 "by_launch_wallet": sum(1 for pl, x in pl_ if pl.p["first_pull_from"] == pl.p["launch_from"]),
                 "via": collections.Counter("%s:%s" % (pl.p["first_pull_to"], pl.p["first_pull_selector"]) for pl, x in pl_).most_common(3),
                 "full_pull": sum(1 for pl, x in pl_ if -x["dl"] >= sum(a["dl"] for a in pl.adds if a["bn"] <= x["bn"]))}
    # trap test: outsiders = non-launch buys (first 8 swaps carry the tx) before the first scheduled (real) buy, by wallets other than the launch wallet,
    # the chain-wide dust wallets apart; also real-size (>= 0.0002) outsiders at ANY time among the first 8 swaps that are not the family's scheduled router
    wo, wi, out_sizes, out_from = [], [], [], collections.Counter()
    for pl in pls:
        sb = sched_generic(pl, anchor(pl) - 1)
        outs = [x for x in pl.buys() if x["known_tx"] and (sb is None or (x["bn"], x["li"]) < (sb["bn"], sb["li"])) and x["from"] != pl.p["launch_from"] and x["from"] not in DUST_WALLETS]
        pb = pl.pull_bn
        if outs: wi.append((pb - outs[0]["bn"]) if pb is not None else None); out_sizes += [x["eth"] / 1e18 for x in outs]; out_from.update(x["from"] for x in outs)
        else: wo.append((pb - anchor(pl)) if pb is not None else None)
    r["trap"] = {"pools_with_outsider_before_sched": len(wi), "outsider_eth_p10_50_90": q(out_sizes, nd=10), "outsider_wallets": out_from.most_common(5),
                 "pulled_after_outsider": sum(1 for z in wi if z is not None), "delay_after_outsider_p10_50_90": q([z for z in wi if z is not None]),
                 "pools_without": len(wo), "pulled_without": sum(1 for z in wo if z is not None), "pull_off_live_without_p10_50_90": q([z for z in wo if z is not None])}
    frs = [front(pl, sched_generic) for pl in pls]
    r["front"] = summarize(frs)
    r["front_sched_off_p10_50_90"] = q([z["sched"] for z in frs if z.get("sched") is not None]); r["front_late"] = sum(1 for z in frs if z.get("late"))
    r["front_S_hist"] = collections.Counter(z.get("S") for z in frs).most_common(5)
    fos = [z for z in (follow(pl) for pl in pls) if z]
    r["follow"] = summarize(fos); r["follow_trig_off_p10_50_90"] = q([z["trig"] for z in fos])
    r["follow_next_minus_trig_p10_50_90"] = q([z["next"] - z["trig"] for z in fos if z["next"] is not None])
    r["follow_rows"] = [{k: z.get(k) for k in ("pid", "trig", "trig_eth", "next", "B", "S", "exit", "ret")} for z in fos][:4]
    r["front_nocap (sell 1 block after the first real buy whenever it comes, deadline +3000)"] = summarize([front(pl, sched_generic, hold=3000) for pl in pls])
    caps = [capacity(pl, sb) for pl in pls for sb in [sched_generic(pl, anchor(pl) + 1)] if sb]
    r["capacity"] = {"n": len(caps), "cap_eth_p10_50_90": q([c["cap_eth"] for c in caps]), "src": collections.Counter(c["src"] for c in caps).most_common(2),
                     "minout_over_quote_p10_50_90": q([c["minout_over_quote"] for c in caps], nd=5), "Y_p10_50_90": q([c["Y"] for c in caps])}
    r["gas_usd_median"] = round(st.median(pl.gas for pl in pls) / 1e18 * USD_PER_ETH, 5)
    return r


for g, pids in groups.items():
    r = analyse_group(g, pids); out[g] = r
    print("=" * 110); print(g)
    for k, v in r.items():
        if k.endswith("_rows"): continue
        if isinstance(v, dict) and "exits" in v: print("  %-22s %s" % (k, fmt_rule(v)))
        else: print("  %-22s %s" % (k, v))
# ------------------------------------------------------------------ the controls through the same per-family pipeline
for g, pids in (("CONTROL vbot-v2.433", V),):
    r = analyse_group(g, pids)
    bb = [(pool(x), sched_bot(pool(x), P[x]["launch_block"])) for x in V]
    bb = [(pl, x) for pl, x in bb if x]
    r["bot_buy"] = {"pools_with": len(bb), "frac": round(len(bb) / len(V), 3), "off_p10_50_90": q([x["bn"] - pl.b0 for pl, x in bb]),
                    "eth_p10_50_90": q([x["eth"] / 1e18 for pl, x in bb]), "n_from": len(set(x["from"] for pl, x in bb)),
                    "pull_minus_bot_buy_p10_50_90": q([pl.pull_bn - x["bn"] for pl, x in bb if pl.pull_bn]),
                    "pull_minus_bot_buy_hist": collections.Counter(pl.pull_bn - x["bn"] for pl, x in bb if pl.pull_bn and pl.pull_bn - x["bn"] < 10).most_common(6)}
    r["front_bot_sched"] = C["v2433_front_bot_sched_all"]
    out[g] = r
    print("=" * 110); print(g)
    for k, v in r.items():
        if k.endswith("_rows"): continue
        if isinstance(v, dict) and "exits" in v: print("  %-22s %s" % (k, fmt_rule(v)))
        else: print("  %-22s %s" % (k, v))
# ------------------------------------------------------------------ pricer check: every observed buy in the assigned groups re-priced from the model state
chk = collections.defaultdict(list)
for g, pids in groups.items():
    for x in pids:
        pl = pool(x)
        for y in pl.seq:
            if y["buy"] and not y["relay"] and not y["in_launch"] and y["a1"]:
                st_, Lst = pl.state_through(None, upto_li=(y["bn"], y["li"]))
                pred = v4math.buy_out_int(int(st_), Lst, y["eth"], y["fee"])
                chk[g.split()[0]].append((pred - y["a1"]) / y["a1"])
out["pricer_check_assigned"] = {g: {"n": len(v), "median_abs_rel_err": st.median(abs(z) for z in v) if v else None, "p99_abs": q([abs(z) for z in v], qs=(.99,), nd=8),
                                    "n_over_1e-3": sum(1 for z in v if abs(z) > 1e-3)} for g, v in chk.items()}
print("PRICER CHECK (model tokens out vs the Swap event, every buy in the assigned groups):", out["pricer_check_assigned"])
json.dump(out, open(os.path.join(HERE, "results_main.json"), "w"), indent=1, default=str)
