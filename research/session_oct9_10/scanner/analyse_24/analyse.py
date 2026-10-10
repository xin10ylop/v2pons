"""analyse_24: four assigned families
  F1 launcher 0x815542e8 (openlaunch.lol) 7c33638d 833 bytes, fee 1%, ts 200, value 0, single-sided token range [-887200, tick0]
  F2 launcher 0xb4038254 7fde822e 772 bytes, fee 1%, ts 200 (deployer 0x06cb3a68, imortal.buzz metadata)
  F3 launcher 0xc97b9d2d 7fde822e 740 bytes   F4 launcher 0xc97b9d2d 7fde822e 772 bytes (same deployer)
+ their wider groups (the same launcher / deployer seen through a looser key) + the controls (vbot-v2.433 front, operator A follow),
priced with common24.Pool (analyse_23/common23.py verbatim): the exact replay of research/session_oct9_10/explore/chk/replay.py on the census
(our buy at the END of block B after every other tx of B, every later swap replayed by its own price shift, a volume-bot router buy under
its own minOut dropped, our sell at the HEAD of block S, a pull at or before S = the stake lost, the pool's own fee each way, gas
2 x 104,000 x the launch block's base fee). Writes results.json and prints analyse.out."""
import sys, os, json, statistics as st, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common24 import *  # noqa

K = json.load(open(os.path.join(HERE, "keys.json")))
P = load_pools(); F = load_families(); T = load_txs(); M = load_blocks_meta()
L1 = "0x815542e8b392389a1389e22e588e4b62a67ade72"
D1 = {"0xbabb7be0b5d6871331cbef588ae95695df8088ba", "0xaca4c6614c08ffa6b6a7e71db9b4c09ec31f33ba", "0xd5755214f14a1dc4cdf00fd5a571ea1c1be9904c", "0x14a202fb4f4ff73d542a189030d3e112234a830b"}
L2 = "0xb40382548413c559ad7f0bb6e24410401238eded"; L34 = "0xc97b9d2da8ec41ce090e8f3f8d7b664eda013da8"
D234 = "0x06cb3a6841c92525e7a1998328e7c9d37e98d937"
groups = collections.OrderedDict()
for i, k in enumerate(K): groups["F%d %s" % (i + 1, k)] = F[k]["pids"]
groups["F1-LAUNCHER all launches through 0x815542e8 (openlaunch.lol, any fee / calldata length)"] = [p["pid"] for p in P.values() if p["launch_to"] == L1]
groups["F1-DEPLOYERS all launches of F1's 4 deployers"] = [p["pid"] for p in P.values() if p["launch_from"] in D1]
groups["F2-LAUNCHER all launches through 0xb4038254"] = [p["pid"] for p in P.values() if p["launch_to"] == L2]
groups["F34-LAUNCHER all launches through 0xc97b9d2d"] = [p["pid"] for p in P.values() if p["launch_to"] == L34]
groups["F234-DEPLOYER all 7fde822e launches of 0x06cb3a68 (imortal.buzz)"] = [p["pid"] for p in P.values() if p["selector"] == "7fde822e" and p["launch_from"] == D234]
V = [p["pid"] for p in P.values() if p["known"] == "vbot-v2.433"]
A = [p["pid"] for p in P.values() if p["known"] == "operator-A"]
E = load_events(set(x for v in groups.values() for x in v) | set(V) | set(A))
POOL = {}


def pool(pid):
    if pid not in POOL: POOL[pid] = Pool(P[pid], E.get(pid), T, M)
    return POOL[pid]


def is_bot(x): return x["to"] == VBOT_ROUTER and x["sel"] == "c1120e3d"


def real_buys(pl, after=None):
    """non-launch, non-relay buys of >= 0.0002 ETH, the chain-wide dust wallets excluded"""
    return [x for x in pl.buys() if x["eth"] >= MIN_REAL and x["from"] not in DUST_WALLETS and (after is None or x["bn"] > after)]


def sched_generic(pl, B): r = real_buys(pl, B); return r[0] if r else None
def sched_bot(pl, B): return next((x for x in pl.buys() if x["bn"] > B and is_bot(x)), None)
def sched_dev(pl, B): return next((x for x in pl.buys() if x["bn"] > B and x["from"] == pl.p["launch_from"]), None)


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


def capacity(pl, sb):
    s, L = pl.launch_state(); fee = pl.fee_at(sb["bn"]); Y = sb["eth"]
    quote = v4math.buy_out_int(int(s), L, Y, fee)
    if is_bot(sb) and sb["input"]:
        mo = word(sb["input"], 4); src = "calldata word 4 (bot router c1120e3d)"
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
C["v2433_front_bot_bought_by_20 (the live trade: sold one block after the bot's buy)"] = summarize([r for r in rs if r["sched"] is not None and r["sched"] + 1 <= 20])
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
def analyse_group(g, pids):
    pls = [pool(x) for x in pids]; ps = [P[x] for x in pids]
    r = {"count": len(ps), "launches_per_day": round(len(ps) / WINDOW_DAYS, 2), "first_last_ts": [min(p["launch_ts"] for p in ps), max(p["launch_ts"] for p in ps)],
         "launch_to_sel_len": collections.Counter("%s:%s:%s" % (p["launch_to"], p["selector"], p["calldata_len"]) for p in ps).most_common(4),
         "deployers": collections.Counter(p["launch_from"] for p in ps).most_common(5), "n_deployers": len(set(p["launch_from"] for p in ps)),
         "deployer_nonce_p10_50_90": q([p["launch_nonce"] for p in ps]), "deployer_nonce0": sum(1 for p in ps if p["launch_nonce"] == 0),
         "values_eth_p10_50_90": q([p["launch_value_eth"] for p in ps], nd=9), "n_distinct_values": len(set(p["launch_value_wei"] for p in ps)),
         "fees": collections.Counter(p["fee"] for p in ps).most_common(6), "hooks": collections.Counter(p["hooks"] for p in ps).most_common(3),
         "tick0": collections.Counter(p["tick0"] for p in ps).most_common(5),
         "launch_ranges": collections.Counter(str([(a["lo"], a["hi"]) for a in pool(p["pid"]).adds if a["tx"] == p["launch_tx"]]) for p in ps).most_common(3),
         "mint_sender": collections.Counter(pool(p["pid"]).adds[0]["sender"] for p in ps if pool(p["pid"]).adds).most_common(3),
         "liq_launch_p10_50_90": q([p["liq_launch"] for p in ps]), "buy_in_launch_tx": sum(1 for p in ps if p["buy_in_launch_tx"]),
         "start": collections.Counter(pl.start for pl in pls).most_common(), "later_adds_pools": sum(1 for pl in pls if len(pl.adds) > 1),
         "pools_with_events": sum(1 for p in ps if p["has_events"])}
    fb = [(pl, pl.buys()[0]) for pl in pls if pl.buys()]
    r["first_buy_any"] = {"pools_with": len(fb), "frac": round(len(fb) / len(pls), 3), "off_p10_50_90": q([x["bn"] - pl.b0 for pl, x in fb]),
                          "eth_p10_50_90": q([x["eth"] / 1e18 for pl, x in fb], nd=9), "to_sel": collections.Counter("%s:%s" % (x["to"], x["sel"]) for pl, x in fb).most_common(4),
                          "from": collections.Counter(x["from"] for pl, x in fb).most_common(4), "n_from": len(set(x["from"] for pl, x in fb))}
    fr = [(pl, real_buys(pl)[0]) for pl in pls if real_buys(pl)]
    r["first_buy_real"] = {"pools_with": len(fr), "frac": round(len(fr) / len(pls), 3), "off_p10_50_90": q([x["bn"] - pl.b0 for pl, x in fr]),
                           "offs": sorted(x["bn"] - pl.b0 for pl, x in fr)[:20],
                           "eth_p10_50_90": q([x["eth"] / 1e18 for pl, x in fr]), "to_sel_len": collections.Counter("%s:%s:%s" % (x["to"], x["sel"], x["clen"]) for pl, x in fr).most_common(4),
                           "n_from": len(set(x["from"] for pl, x in fr)), "nonce_p10_50_90": q([x["nonce"] for pl, x in fr]),
                           "by_launch_wallet": sum(1 for pl, x in fr if x["from"] == pl.p["launch_from"]),
                           "from_top": collections.Counter(x["from"] for pl, x in fr).most_common(4)}
    dv = [(pl, sched_dev(pl, pl.b0)) for pl in pls]; dv = [(pl, x) for pl, x in dv if x]
    r["dev_buy (the launch wallet's own buy)"] = {"pools_with": len(dv), "frac": round(len(dv) / len(pls), 3), "offs": sorted(x["bn"] - pl.b0 for pl, x in dv)[:20],
                                                  "eth": sorted(round(x["eth"] / 1e18, 6) for pl, x in dv)[:20],
                                                  "to_sel_len": collections.Counter("%s:%s:%s" % (x["to"], x["sel"], x["clen"]) for pl, x in dv).most_common(3),
                                                  "nonce": collections.Counter(x["nonce"] for pl, x in dv).most_common(4)}
    allsw = [x for pl in pls for x in pl.seq if not x["in_launch"]]
    r["swaps_non_launch"] = {"total": len(allsw), "buys": sum(1 for x in allsw if x["buy"]), "sells": sum(1 for x in allsw if not x["buy"]),
                             "buys_ge_0.0002": sum(1 for x in allsw if x["buy"] and x["eth"] >= MIN_REAL),
                             "eth_in": round(sum(x["eth"] for x in allsw if x["buy"]) / 1e18, 6), "eth_out_sells": round(sum(x["eth"] for x in allsw if not x["buy"]) / 1e18, 6),
                             "pools_with_any": sum(1 for pl in pls if any(not x["in_launch"] for x in pl.seq)),
                             "from_top": collections.Counter(x["from"] for x in allsw).most_common(6),
                             "to_sel_top": collections.Counter("%s:%s" % (x["to"], x["sel"]) for x in allsw).most_common(5),
                             "sell_off_p10_50_90": q([x["bn"] - pl.b0 for pl in pls for x in pl.seq if not x["in_launch"] and not x["buy"]])}
    pl_ = [(pl, pl.pulls[0]) for pl in pls if pl.pulls]
    r["pull"] = {"pulled_3000": len(pl_), "frac": round(len(pl_) / len(pls), 3), "off_launch_p10_50_90": q([x["bn"] - pl.b0 for pl, x in pl_]),
                 "off_from_first_real_buy_p10_50_90": q([x["bn"] - real_buys(pl)[0]["bn"] for pl, x in pl_ if real_buys(pl)]),
                 "by_launch_wallet": sum(1 for pl, x in pl_ if pl.p["first_pull_from"] == pl.p["launch_from"]),
                 "via": collections.Counter("%s:%s" % (pl.p["first_pull_to"], pl.p["first_pull_selector"]) for pl, x in pl_).most_common(3)}
    # trap test: outsiders = non-launch buys before the first scheduled (real) buy by wallets other than the launch wallet, dust wallets apart
    wo, wi, out_sizes, out_from = [], [], [], collections.Counter()
    for pl in pls:
        sb = sched_generic(pl, pl.b0)
        outs = [x for x in pl.buys() if (sb is None or (x["bn"], x["li"]) < (sb["bn"], sb["li"])) and x["from"] != pl.p["launch_from"] and x["from"] not in DUST_WALLETS]
        pb = pl.pull_bn
        if outs: wi.append((pb - outs[0]["bn"]) if pb is not None else None); out_sizes += [x["eth"] / 1e18 for x in outs]; out_from.update(x["from"] for x in outs)
        else: wo.append((pb - pl.b0) if pb is not None else None)
    r["trap"] = {"pools_with_outsider_before_sched": len(wi), "outsider_eth_p10_50_90": q(out_sizes, nd=9), "outsider_wallets": out_from.most_common(5),
                 "pulled_after_outsider": sum(1 for z in wi if z is not None), "delay_after_outsider_p10_50_90": q([z for z in wi if z is not None]),
                 "pools_without": len(wo), "pulled_without": sum(1 for z in wo if z is not None), "pull_off_without_p10_50_90": q([z for z in wo if z is not None])}
    frs = [front(pl, sched_generic) for pl in pls]
    r["front"] = summarize(frs)
    r["front_sched_off_p10_50_90"] = q([z["sched"] for z in frs if z.get("sched") is not None])
    r["front_rows"] = [{k: z.get(k) for k in ("pid", "sched", "S", "exit", "ret", "fee_b", "fee_s")} for z in frs][:6]
    fos = [z for z in (follow(pl) for pl in pls) if z]
    r["follow"] = summarize(fos); r["follow_rows"] = [{k: z.get(k) for k in ("pid", "trig", "trig_eth", "next", "B", "S", "exit", "ret")} for z in fos][:8]
    r["front_no20cap (sell 1 block after the first real buy, deadline +3000)"] = summarize([front(pl, sched_generic, hold=3000) for pl in pls])
    dvp = [pl for pl, x in dv]
    fd = [front(pl, sched_dev, hold=3000) for pl in dvp]
    r["front_into_dev_buy (pools with a launch-wallet buy only; sell 1 block after it)"] = summarize(fd)
    r["front_into_dev_buy_rows"] = [{k: z.get(k) for k in ("pid", "sched", "S", "exit", "ret", "gross")} for z in fd][:8]
    caps = [capacity(pl, sb) for pl in pls for sb in [sched_generic(pl, pl.b0 + 1)] if sb]
    r["capacity"] = {"n": len(caps), "cap_eth_p10_50_90": q([c["cap_eth"] for c in caps]), "src": collections.Counter(c["src"] for c in caps).most_common(2),
                     "Y_p10_50_90": q([c["Y"] for c in caps])}
    r["gas_usd_median"] = round(st.median(pl.gas for pl in pls) / 1e18 * USD_PER_ETH, 5)
    r["eth_tax_buy_sell_ppm"] = collections.Counter(str(pl.etax) for pl in pls).most_common(2)
    return r


for g, pids in groups.items():
    r = analyse_group(g, pids); out[g] = r
    print("=" * 110); print(g)
    for k, v in r.items():
        if isinstance(v, dict) and "exits" in v: print("  %-22s %s" % (k, fmt_rule(v)))
        else: print("  %-22s %s" % (k, v))
# ------------------------------------------------------------------ the controls through the same per-family pipeline
for g, pids in (("CONTROL vbot-v2.433", V), ("CONTROL operator-A", A)):
    r = analyse_group(g, pids)
    if g.endswith("v2.433"):
        bb = [(pool(x), sched_bot(pool(x), P[x]["launch_block"])) for x in V]
        bb = [(pl, x) for pl, x in bb if x]
        r["bot_buy"] = {"pools_with": len(bb), "frac": round(len(bb) / len(V), 3), "off_p10_50_90": q([x["bn"] - pl.b0 for pl, x in bb]),
                        "eth_p10_50_90": q([x["eth"] / 1e18 for pl, x in bb]), "n_from": len(set(x["from"] for pl, x in bb)),
                        "pull_minus_bot_buy_p10_50_90": q([pl.pull_bn - x["bn"] for pl, x in bb if pl.pull_bn]),
                        "pull_minus_bot_buy_hist": collections.Counter(pl.pull_bn - x["bn"] for pl, x in bb if pl.pull_bn and pl.pull_bn - x["bn"] < 10).most_common(6),
                        "minout_over_launch_quote_p10_50_90": q([capacity(pl, x)["minout_over_quote"] for pl, x in bb], nd=5)}
        r["front_bot_sched"] = C["v2433_front_bot_sched_all"]
    out[g] = r
    print("=" * 110); print(g)
    for k, v in r.items():
        if k.endswith("_rows"): continue
        if isinstance(v, dict) and "exits" in v: print("  %-22s %s" % (k, fmt_rule(v)))
        else: print("  %-22s %s" % (k, v))
json.dump(out, open(os.path.join(HERE, "results.json"), "w"), indent=1, default=str)
