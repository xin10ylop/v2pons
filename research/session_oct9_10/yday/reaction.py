#!/usr/bin/env python3
"""How the operator reacts when someone else is in its pool (the paper prices assume it does not react to us).

Reads react_data.json (fetch.py: every Swap / ModifyLiquidity on the operator's 100 Oct 8 launches + the Oct 9 00:11 pool we
traded, the transaction of every swap up to the first pull + 50 blocks, our 20 receipts) and react_fp.json (fetch_fp.py: the
fingerprint of every buy transaction). Writes reaction.json and prints the summary.

The crowd is identified by its transaction fingerprint, not by a wallet list: every one of the operator's crowd buys (4,680 buys
from 860 wallets: the 33 recurring wallets of the original launcher, the per-launch fresh wallets of the copies, the 13:15 batch's
reused pairs) is a Universal Router execute() of 1,124 bytes with deadline = 2^256-1, an EIP-1559 transaction with priority fee
exactly 0.02 gwei and a gas limit of 220,000 (880,000 / 260,000 on two sub-groups). Nobody else on these pools sends that, except
our own release-0.2 router trade (it copied the crowd's calldata on purpose), which is excluded by our wallet.
"""
import sys, json, time, collections, statistics as st
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
sys.path.insert(0, "/home/user/v2pons/src")
from chain import T_SWAP, T_ML, W, sgn
import v4math

HERE = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/yday/"
D = json.load(open(HERE + "react_data.json")); FP = json.load(open(HERE + "react_fp.json"))
US = "0xab5a34c3f41e57fdee1a1d6f19d3e21f46df3ea8"; RELAY = "2abb5653352f6b2f3b4f4261877cd02d9e05a957"; UR = "8876789976decbfcbbbe364623c63652db8c0904"
DUST = "0xe71a69f434a719cd5afa411568b69716aab3b84a"
Q96 = 1 << 96; REAL = 2 * 10**14; ETH_USD = 2570.0
STAKE = int(0.0012e18); TP = 0.01; HOLD, LEAD = 4, 2; ENGINE_GAS_UNITS = 250_000; MAX_TRIG = 150
OCT8_LAST = 83719338


def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x


def utc(ts): return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(ts))


def is_crowd_fp(h, frm):
    f = FP.get(h)
    return bool(f) and frm != US and f["type"] == 2 and f["prio"] == 20_000_000 and f["len"] == 1124 and f["dl_max"] is True and f["gas"] in (220_000, 880_000, 260_000)


# ------------------------------------------------------------------ per pool: swaps with their sender class, the pull
pools = []
for pid, P in D["pools"].items():
    m = P["meta"]; b0 = m["block"]
    sw = []; adds = []; pull = None
    for e in P["ev"]:
        d = e["data"]
        if e["t0"] == T_ML:
            dl = sgn(W(d, 2))
            if dl > 0: adds.append((sgn(W(d, 0)), sgn(W(d, 1)), dl))
            elif pull is None:
                t = P["txs"].get(e["tx"], {}); pull = (e["bn"], t.get("idx", 0), e["li"])
            continue
        t = P["txs"].get(e["tx"])
        a0, a1 = s128(W(d, 0)), s128(W(d, 1))
        frm = t["from"] if t else None
        ours = (e["sender"] == RELAY) or frm == US
        cls = "us" if ours else ("dust" if frm == DUST else ("crowd" if (t and a0 < 0 and is_crowd_fp(e["tx"], frm)) else ("?" if t is None else "other")))
        sw.append({"bn": e["bn"], "li": e["li"], "idx": t["idx"] if t else None, "a0": a0, "a1": a1, "sp": W(d, 2), "L": W(d, 3), "from": frm, "via": e["sender"], "cls": cls, "tx": e["tx"],
                   "nonce": t["nonce"] if t else None})
    sw.sort(key=lambda x: (x["bn"], x["li"]))
    liq0 = v4math.active_liquidity(m["tick0"], adds)
    pools.append({"pid": pid, "m": m, "b0": b0, "sw": sw, "pull": pull, "liq0": liq0})
pools.sort(key=lambda p: p["b0"])
for n, p in enumerate(pools): p["n"] = n

# crowd wallets that also sell: classify sells by wallet (a crowd wallet's sell is a crowd sell)
crowd_wallets = {x["from"] for p in pools for x in p["sw"] if x["cls"] == "crowd"}
for p in pools:
    for x in p["sw"]:
        if x["cls"] == "other" and x["a0"] >= 0 and x["from"] in crowd_wallets: x["cls"] = "crowd"
recurring = collections.Counter()
for p in pools:
    for w in {x["from"] for x in p["sw"] if x["cls"] == "crowd" and x["a0"] < 0}: recurring[w] += 1


def before_pull(p, x):
    return p["pull"] is None or (x["bn"], x["li"]) < (p["pull"][0], p["pull"][2])


def real_buys(p, cls=None):
    return [x for x in p["sw"] if x["a0"] <= -REAL and before_pull(p, x) and (cls is None or x["cls"] in cls)]


# ------------------------------------------------------------------ the scheme of each launch (from the crowd's own pattern)
def scheme(p):
    m = p["m"]; rb = real_buys(p, ("crowd",))
    if not rb: return "no_crowd_buy"
    ws = {x["from"] for x in rb}; rec = sum(1 for w in ws if recurring[w] >= 20) / len(ws); rec3 = sum(1 for w in ws if 3 <= recurring[w] < 20) / len(ws)
    first = rb[0]["bn"] - p["b0"]; dur = (p["pull"][0] - rb[0]["bn"]) if p["pull"] else None
    if m["kind"] == "copy":
        return "copy_burst_only" if len(rb) <= 4 else "copy_burst_then_crowd"
    if rec >= 0.5: return "orig_classic"            # the 33 recurring wallets, first buy +41..55, a buy every few blocks
    if rec3 >= 0.5: return "orig_crowdB"             # the second recurring set (4 low-fee launches)
    if len(rb) <= 4 and dur is not None and dur <= 20: return "orig_quick_pull"   # 13:15-13:20: 2-4 buys from a reused pair, pulled 6-15 blocks after the first
    return "orig_fresh"                              # per-launch wallets, many buys


for p in pools: p["scheme"] = scheme(p)

# ------------------------------------------------------------------ exact replay of the pool, our sell removed / a buy inserted
def apply(sp, L, x, fee):
    """one swap on (sqrtP, L) by its input: a0 < 0 an ETH-in buy, else a token-in sell"""
    if x["a0"] < 0:
        net = -x["a0"] - (-x["a0"] * fee + 999_999) // 1_000_000
        den = L + (net * sp) // Q96
        return (L * sp + den - 1) // den
    tin = -x["a1"]
    if tin <= 0: return sp
    net = tin - (tin * fee + 999_999) // 1_000_000
    return sp + (net * Q96) // L


def state_at_head(p, S, skip=lambda x: False):
    """(sqrtP, L) at the head of block S: after every swap in blocks < S, without the swaps `skip` selects (replayed exactly
    from the first skipped one on, by each later swap's input amount)"""
    fee = p["m"]["fee"]; sp, L = p["m"]["sqrtP0"], p["liq0"]; replay = False
    for x in p["sw"]:
        if x["bn"] >= S: break
        if p["pull"] and (x["bn"], x["li"]) > (p["pull"][0], p["pull"][2]): break
        if skip(x): replay = True; continue
        if replay: sp = apply(sp, L, x, fee)
        else: sp, L = x["sp"], x["L"]
    return sp, L


def validate_replay():
    errs = []
    for p in pools:
        fee = p["m"]["fee"]; sp, L = p["m"]["sqrtP0"], p["liq0"]
        for x in p["sw"][:60]:
            if p["pull"] and (x["bn"], x["li"]) > (p["pull"][0], p["pull"][2]): break
            if x["L"] != L: break                                                     # a second range: stop
            sp2 = apply(sp, L, x, fee)
            if x["sp"]: errs.append(abs(sp2 - x["sp"]) / x["sp"])
            sp = x["sp"]
    return max(errs), st.median(errs), len(errs)


# ------------------------------------------------------------------ step 1: our ten live trades
rec = D["receipts"]
def gas_of(h): r = rec[h]; return r["gasUsed"] * r["egp"]


trades = []
for p in pools:
    ours = [x for x in p["sw"] if x["cls"] == "us"]
    if not ours: continue
    buy = ours[0]; sell = ours[1] if len(ours) > 1 else None
    B = buy["bn"]; fee = p["m"]["fee"]; b0 = p["b0"]
    entry = "seat" if B - b0 <= 12 else "follow"
    trig = next((x for x in real_buys(p) if x["cls"] != "us"), None)                # the engine's follow trigger: the first real-size buy
    pull_bn = p["pull"][0] if p["pull"] else None
    behind = [x for x in p["sw"] if x["a0"] <= -REAL and x["cls"] != "us" and (x["bn"], x["li"]) > (B, buy["li"]) and before_pull(p, x)]
    crowd_behind = [x for x in behind if x["cls"] == "crowd"]
    within4 = [x for x in crowd_behind if x["bn"] <= B + 4]
    # the CURRENT exit on the real chain: take profit on a real-size buy behind ours in B..B+2 (engine price copy: every buy by its
    # ETH, sells ignored, as the feed sees it; chain price shown too), else the deadline send at B+2; lands send+1 / send+2
    tokens = buy["a1"]; eth_in = -buy["a0"]; base_fee = D["base_fee"].get(str(B), 21_000_000); engine_gas = base_fee * ENGINE_GAS_UNITS
    feed_sp = p["m"]["sqrtP0"]; tp_at = None; tp_ret_feed = None; tp_ret_chain = None; tp_checks = []
    for x in p["sw"]:
        if x["bn"] > B + HOLD - LEAD: break
        if not before_pull(p, x): break
        if x["a0"] < 0: feed_sp = apply(feed_sp, p["liq0"], x, fee)                     # the feed applies buys (ours included), never sells
        if x["cls"] == "us" or x["a0"] > -REAL or (x["bn"], x["li"]) <= (B, buy["li"]): continue
        r_feed = (v4math.sell_out_int(feed_sp, p["liq0"], tokens, fee) - STAKE - engine_gas) / STAKE
        r_chain = (v4math.sell_out_int(x["sp"], x["L"], tokens, fee) - STAKE - engine_gas) / STAKE
        tp_checks.append({"block_after_buy": x["bn"] - B, "eth": round(-x["a0"] / 1e18, 5), "cls": x["cls"], "ret_engine_feed": round(r_feed, 4), "ret_chain": round(r_chain, 4)})
        if r_feed >= TP and tp_at is None: tp_at = x["bn"]; tp_ret_feed = r_feed; tp_ret_chain = r_chain
    send = tp_at if tp_at is not None else B + HOLD - LEAD
    real_gas = gas_of(buy["tx"]) + (gas_of(sell["tx"]) if sell else 0)
    is_our_sell = (lambda x: sell is not None and x["tx"] == sell["tx"])
    cur = {}
    for tag, S in (("fast", send + 1), ("slow", send + 2)):
        if pull_bn is not None and pull_bn <= S:
            cur[tag] = {"sell_land_block": S, "after_buy": S - B, "ret": round((-eth_in - real_gas) / eth_in, 4), "exit": "pull_first", "pull_after_buy": pull_bn - B}
        else:
            sp, L = state_at_head(p, S, skip=is_our_sell)
            out = v4math.sell_out_int(sp, L, tokens, fee)
            cur[tag] = {"sell_land_block": S, "after_buy": S - B, "eth_out": out, "ret": round((out - eth_in - real_gas) / eth_in, 4), "pnl_eth": (out - eth_in - real_gas) / 1e18,
                        "exit": "take_profit" if tp_at is not None else "deadline"}
    live_ret = ((sell["a0"] if sell else 0) - eth_in - real_gas) / eth_in
    trades.append({
        "n": None, "time_utc": utc(p["m"]["ts"]), "launch_block": b0, "pid": p["pid"], "kind": p["m"]["kind"], "scheme": p["scheme"], "fee_ppm": fee, "entry": entry,
        "route": "relay" if buy["via"] == RELAY else "router (crowd's calldata)",
        "trigger_offset": (trig["bn"] - b0) if trig else None, "trigger_eth": round(-trig["a0"] / 1e18, 5) if trig else None,
        "buy_block": B, "buy_offset_from_launch": B - b0, "buy_after_trigger": (B - trig["bn"]) if (trig and entry == "follow") else None, "buy_index": buy["idx"],
        "sell_block_live": sell["bn"] if sell else None, "sell_after_buy_live": (sell["bn"] - B) if sell else None,
        "crowd_buys_behind_within_4": len(within4), "crowd_buys_behind_within_4_detail": [(x["bn"] - B, round(-x["a0"] / 1e18, 4)) for x in within4],
        "crowd_buys_behind_same_block": sum(1 for x in within4 if x["bn"] == B),
        "first_crowd_buy_after_ours": (crowd_behind[0]["bn"] - B) if crowd_behind else None,
        "crowd_buys_before_pull_after_ours": len(crowd_behind),
        "other_real_buys_behind_before_pull": [(x["bn"] - B, round(-x["a0"] / 1e18, 5), x["from"][:10], x["cls"]) for x in behind if x["cls"] != "crowd"][:5],
        "pull_after_our_buy": (pull_bn - B) if pull_bn else None,
        "pull_after_last_crowd_buy": (pull_bn - real_buys(p, ("crowd",))[-1]["bn"]) if (pull_bn and real_buys(p, ("crowd",))) else None, "pull_after_trigger": (pull_bn - trig["bn"]) if (pull_bn and trig) else None,
        "pulled_before_live_sell": bool(pull_bn and sell and (p["pull"][0], p["pull"][2]) < (sell["bn"], sell["li"])),
        "live": {"eth_in": eth_in / 1e18, "eth_out": (sell["a0"] if sell else 0) / 1e18, "gas_eth": real_gas / 1e18, "gas_usd": round(real_gas / 1e18 * ETH_USD, 4),
                 "ret": round(live_ret, 4), "pnl_eth": (live_ret * eth_in) / 1e18, "pnl_usd": round(live_ret * eth_in / 1e18 * ETH_USD, 3),
                 "buy_gas_used": rec[buy["tx"]]["gasUsed"], "sell_gas_used": rec[sell["tx"]]["gasUsed"] if sell else None, "base_fee_gwei": base_fee / 1e9},
        "current_exit": {"tp_checks_B_to_B2": tp_checks, "would_take_profit": tp_at is not None, "sell_send_block": send, "send_after_buy": send - B,
                         "tp_ret_engine": round(tp_ret_feed, 4) if tp_ret_feed is not None else None, "tp_ret_chain_at_that_buy": round(tp_ret_chain, 4) if tp_ret_chain is not None else None,
                         "fast": cur["fast"], "slow": cur["slow"]},
    })
for i, t in enumerate(trades, 1): t["n"] = i

# ------------------------------------------------------------------ steps 2-4: every launch
def crowd_in(p, lo, hi):
    return [x for x in real_buys(p, ("crowd",)) if lo <= x["bn"] <= hi]


launch_rows = []
for p in pools:
    m = p["m"]; b0 = p["b0"]; rb_all = [x for x in real_buys(p) if x["cls"] != "us"]; rb_crowd = real_buys(p, ("crowd",))
    trig = rb_all[0] if rb_all else None; ctrig = rb_crowd[0] if rb_crowd else None
    ours = [x for x in p["sw"] if x["cls"] == "us"]
    pull_bn = p["pull"][0] if p["pull"] else None
    elig = m["fee"] <= 9999 and p["liq0"] >= 1e21 and m["hooks"] == "0" * 40 and m["c0"] == "0" * 40
    entry = "follow" if m["kind"] == "orig" else "seat"
    skip = None
    if not elig: skip = "fee >= 1%" if m["fee"] > 9999 else "pool not eligible"
    elif entry == "follow" and (trig is None or trig["bn"] - b0 > MAX_TRIG): skip = "no real-size buy within 150 blocks"
    row = {"block": b0, "time_utc": utc(m["ts"]), "pid": p["pid"], "kind": m["kind"], "scheme": p["scheme"], "fee_ppm": m["fee"], "entry": entry, "eligible": elig, "skip_reason": skip,
           "deployer": m["from"], "launcher": m["to"], "liquidity": p["liq0"], "traded_by_us": bool(ours),
           "trigger_offset": (trig["bn"] - b0) if trig else None, "trigger_value_eth": round(-trig["a0"] / 1e18, 6) if trig else None, "trigger_cls": trig["cls"] if trig else None,
           "first_crowd_buy_offset": (ctrig["bn"] - b0) if ctrig else None,
           "fire_block": (trig["bn"] if entry == "follow" else b0 + 6) if (trig or entry == "seat") else None,
           "pull_block": pull_bn, "pull_offset": (pull_bn - b0) if pull_bn else None, "pull_after_first_crowd_buy": (pull_bn - ctrig["bn"]) if (pull_bn and ctrig) else None,
           "crowd_real_buys_before_pull": len(rb_crowd), "crowd_wallets": len({x["from"] for x in rb_crowd}),
           "dust_buy_offsets": [x["bn"] - b0 for x in p["sw"] if x["cls"] == "dust" and x["a0"] < 0][:3]}
    if ctrig:
        T = ctrig["bn"]
        row["crowd_continues"] = {f"land_T+{k}": {"window": [T + k + 1 - b0, T + k + 4 - b0], "crowd_buys": len(crowd_in(p, T + k + 1, T + k + 4)), "pull_in_or_before_window": bool(pull_bn and pull_bn <= T + k + 4)}
                                  for k in (1, 2)}
        row["crowd_buys_T+1_to_T+4"] = len(crowd_in(p, T + 1, T + 4))
    # outsiders: real-size buys before the pull by a wallet that is not the crowd, not us, not the dust tester
    outs = []
    for x in real_buys(p, ("other", "?")):
        X = x["bn"]
        after = [y for y in real_buys(p, ("crowd",)) if (y["bn"], y["li"]) > (X, x["li"])]
        outs.append({"offset": X - b0, "block": X, "wallet": x["from"], "nonce": x["nonce"], "eth": round(-x["a0"] / 1e18, 6), "via": x["via"][:8],
                     "fingerprint": {k: FP.get(x["tx"], {}).get(k) for k in ("type", "gas", "prio", "len", "dl_max")},
                     "before_first_crowd_buy": bool(ctrig is None or (X, x["li"]) < (ctrig["bn"], ctrig["li"])),
                     "crowd_buys_next_1_4": sum(1 for y in after if y["bn"] <= X + 4), "crowd_buys_next_1_10": sum(1 for y in after if y["bn"] <= X + 10),
                     "crowd_buys_until_pull": len(after), "first_crowd_buy_after": (after[0]["bn"] - X) if after else None,
                     "crowd_buys_prev_10": sum(1 for y in real_buys(p, ("crowd",)) if X - 10 <= y["bn"] < X),
                     "pull_after": (pull_bn - X) if pull_bn else None})
    row["outsider_buys"] = outs
    if ours:
        row["live"] = next({k: t[k] for k in ("n", "entry", "buy_block", "live", "current_exit", "pull_after_our_buy", "crowd_buys_behind_within_4")} for t in trades if t["pid"] == p["pid"])
    else:
        row["live"] = None
    row["results"] = None                                  # this task measures the reaction; the pricing tasks fill results
    row["close_block"] = (pull_bn or b0) + 30
    launch_rows.append(row)

# ------------------------------------------------------------------ baselines: the hazard of a pull, by scheme, at a given offset
def clean(r):  # launches with no outsider and not traded by us
    return not r["traded_by_us"] and not r["outsider_buys"]


by_scheme = collections.defaultdict(list)
for r in launch_rows: by_scheme[r["scheme"]].append(r)


def pull_hazard(scheme_, offset, gap):
    """among clean launches of the scheme still alive at `offset`, the share pulled within (offset, offset + gap]"""
    alive = [r for r in by_scheme[scheme_] if clean(r) and (r["pull_offset"] is None or r["pull_offset"] > offset)]
    hit = [r for r in alive if r["pull_offset"] is not None and r["pull_offset"] <= offset + gap]
    return len(hit), len(alive)


for r in launch_rows:
    for o in r["outsider_buys"]:
        if o["pull_after"] is not None:
            h, a = pull_hazard(r["scheme"], o["offset"], o["pull_after"]); o["baseline_pulled_within_same_gap"] = f"{h}/{a}"
for t in trades:
    p = next(q for q in pools if q["pid"] == t["pid"])
    if t["pull_after_our_buy"] is not None:
        h, a = pull_hazard(t["scheme"], t["buy_offset_from_launch"], t["pull_after_our_buy"]); t["baseline_pulled_within_same_gap"] = f"{h}/{a} clean {t['scheme']} launches"

# ------------------------------------------------------------------ summaries
def rate(rows, key):
    v = [r for r in rows if r.get("crowd_continues")]
    n = sum(1 for r in v if r["crowd_continues"][key]["crowd_buys"] > 0 and not (r["crowd_continues"][key]["pull_in_or_before_window"] and r["crowd_continues"][key]["crowd_buys"] == 0))
    return n, len(v)


summary = {}
oct8 = [r for r in launch_rows if r["block"] <= OCT8_LAST]
wo = [r for r in oct8 if r["kind"] == "orig" and not r["traded_by_us"]]
wo_elig = [r for r in wo if r["skip_reason"] is None]
summary["follow_without_us"] = {}
for name, rows in (("all_orig_without_us", wo), ("engine_eligible_orig_without_us", wo_elig)):
    d = {}
    for key in ("land_T+2", "land_T+1"):
        n, m_ = rate(rows, key); d[key] = f"{n}/{m_}"
    d["by_scheme_land_T+2"] = {s: "%d/%d" % rate([r for r in rows if r["scheme"] == s], "land_T+2") for s in sorted({r["scheme"] for r in rows})}
    d["pull_after_first_crowd_buy_by_scheme"] = {s: sorted(r["pull_after_first_crowd_buy"] for r in rows if r["scheme"] == s and r["pull_after_first_crowd_buy"] is not None) for s in sorted({r["scheme"] for r in rows})}
    summary["follow_without_us"][name] = d
fol = [t for t in trades if t["entry"] == "follow"]
summary["follow_with_us"] = {"crowd_buy_behind_ours_in_B+1..B+4": f"{sum(1 for t in fol if any(b >= 1 for b, _ in t['crowd_buys_behind_within_4_detail']))}/{len(fol)}",
                             "crowd_buy_behind_ours_in_B..B+4": f"{sum(1 for t in fol if t['crowd_buys_behind_within_4'] > 0)}/{len(fol)}",
                             "pull_after_trigger": [t["pull_after_trigger"] for t in fol], "pull_after_our_buy": [t["pull_after_our_buy"] for t in fol],
                             "current_exit_take_profit": f"{sum(1 for t in fol if t['current_exit']['would_take_profit'])}/{len(fol)}"}

# the crowd's usual activity at the outsider's offset: mean crowd buys in the 10 blocks after the same offset on clean launches of
# the scheme still alive then (to tell "the crowd stopped" from "the crowd was idle anyway")
def crowd_rate_at(scheme_, offset, span=10):
    v = []
    for r in by_scheme[scheme_]:
        if not clean(r) or (r["pull_offset"] is not None and r["pull_offset"] <= offset + span): continue
        p = next(q for q in pools if q["pid"] == r["pid"]); v.append(len(crowd_in(p, p["b0"] + offset + 1, p["b0"] + offset + span)))
    return (round(st.mean(v), 2) if v else None), len(v)


for r in launch_rows:
    for o in r["outsider_buys"]:
        o["baseline_crowd_buys_next_1_10"], o["baseline_n"] = crowd_rate_at(r["scheme"], o["offset"])
        o["baseline_crowd_buys_prev_10"] = crowd_rate_at(r["scheme"], o["offset"] - 11)[0]


def tp_window_rate(rows, k):
    v = [r for r in rows if r.get("first_crowd_buy_offset") is not None]
    p_by = {q["pid"]: q for q in pools}
    n = 0
    for r in v:
        p = p_by[r["pid"]]; T = p["b0"] + r["first_crowd_buy_offset"]
        if crowd_in(p, T + k + 1, T + k + 2): n += 1
    return n, len(v)


for name, rows in (("all_orig_without_us", wo), ("engine_eligible_orig_without_us", wo_elig)):
    summary["follow_without_us"][name]["crowd_buy_in_TP_window_L+1..L+2"] = {f"land_T+{k}": "%d/%d" % tp_window_rate(rows, k) for k in (1, 2)}
    summary["follow_without_us"][name]["crowd_buy_in_TP_window_by_scheme_land_T+2"] = {s_: "%d/%d" % tp_window_rate([r for r in rows if r["scheme"] == s_], 2) for s_ in sorted({r["scheme"] for r in rows})}
summary["follow_with_us"]["crowd_buy_behind_ours_in_B+1..B+2"] = f"{sum(1 for t in fol if any(1 <= b <= 2 for b, _ in t['crowd_buys_behind_within_4_detail']))}/{len(fol)}"
summary["follow_with_us"]["current_exit_ret_fast"] = [t["current_exit"]["fast"]["ret"] for t in fol]
summary["follow_with_us"]["current_exit_ret_slow"] = [t["current_exit"]["slow"]["ret"] for t in fol]
summary["follow_with_us"]["live_ret"] = [t["live"]["ret"] for t in fol]
# the operator's reaction lag: blocks from a non-crowd buy (an outsider's or ours) to the pull, when the pull came within 60 blocks
lags = []
for r in launch_rows:
    for o in r["outsider_buys"]:
        if o["pull_after"] is not None and o["pull_after"] <= 60: lags.append(("outsider", r["time_utc"][11:16], r["scheme"], o["pull_after"], o["baseline_pulled_within_same_gap"]))
for t in trades:
    if t["pull_after_our_buy"] is not None and t["pull_after_our_buy"] <= 60: lags.append(("us_" + t["entry"], t["time_utc"][11:16], t["scheme"], t["pull_after_our_buy"], t.get("baseline_pulled_within_same_gap")))
summary["reaction_lags_pull_after_non_crowd_buy"] = sorted(lags, key=lambda x: x[3])
summary["non_crowd_buys_not_followed_by_pull_within_60"] = [(r["time_utc"][11:16], r["scheme"], o["offset"], o["via"], o["eth"], o["pull_after"]) for r in launch_rows for o in r["outsider_buys"] if o["pull_after"] is None or o["pull_after"] > 60] + \
    [("us " + t["time_utc"][11:16], t["scheme"], t["buy_offset_from_launch"], t["route"], 0.0012, t["pull_after_our_buy"]) for t in trades if t["pull_after_our_buy"] is None or t["pull_after_our_buy"] > 60]
# step 4: the dust tester on copy launches, and the burst
cp = [r for r in oct8 if r["kind"] == "copy"]
summary["dust_tester_copy"] = {"copy_launches": len(cp), "with_dust_buy": sum(1 for r in cp if r["dust_buy_offsets"]),
                               "dust_offsets": dict(collections.Counter(r["dust_buy_offsets"][0] for r in cp if r["dust_buy_offsets"])),
                               "burst_offsets": dict(collections.Counter(r["first_crowd_buy_offset"] for r in cp)),
                               "burst_after_dust": sum(1 for r in cp if r["dust_buy_offsets"] and r["first_crowd_buy_offset"] is not None and r["first_crowd_buy_offset"] > r["dust_buy_offsets"][0]),
                               "burst_size_buys_in_first_block": dict(collections.Counter(len(crowd_in(next(q for q in pools if q["pid"] == r["pid"]), r["block"] + r["first_crowd_buy_offset"], r["block"] + r["first_crowd_buy_offset"])) for r in cp)),
                               "pull_offsets_by_scheme": {s_: sorted(r["pull_offset"] for r in cp if r["scheme"] == s_) for s_ in ("copy_burst_only", "copy_burst_then_crowd")}}
og = [r for r in oct8 if r["kind"] == "orig"]
summary["dust_tester_orig"] = {"orig_launches": len(og), "with_dust_buy": sum(1 for r in og if r["dust_buy_offsets"]), "dust_offsets": dict(collections.Counter(r["dust_buy_offsets"][0] for r in og if r["dust_buy_offsets"]))}
# the seat evidence: our two seat buys on the original launcher, against the clean launches of the same scheme
cl = [r for r in launch_rows if r["scheme"] == "orig_classic" and clean(r)]
def crowd_first50(r):
    p = next(q for q in pools if q["pid"] == r["pid"]); T = r["block"] + r["first_crowd_buy_offset"]; return len(crowd_in(p, T, T + 50))
summary["seat_on_classic"] = {"clean_classic_first_crowd_buy_offsets": sorted(r["first_crowd_buy_offset"] for r in cl),
                              "clean_classic_crowd_buys_in_first_50_blocks": sorted(crowd_first50(r) for r in cl),
                              "ours": [{"n": t["n"], "buy_offset": t["buy_offset_from_launch"], "first_crowd_buy_offset": t["buy_offset_from_launch"] + t["first_crowd_buy_after_ours"],
                                        "crowd_buys_in_first_50_blocks": crowd_first50(next(r for r in launch_rows if r["pid"] == t["pid"])), "pull_offset": t["buy_offset_from_launch"] + t["pull_after_our_buy"],
                                        "pull_after_first_crowd_buy": t["pull_after_our_buy"] - t["first_crowd_buy_after_ours"]} for t in trades if t["entry"] == "seat"],
                              "clean_classic_pull_after_first_crowd_buy": sorted(r["pull_after_first_crowd_buy"] for r in cl)}
gas_b = [t["live"]["buy_gas_used"] for t in trades if t["route"] == "relay"]; gas_s = [t["live"]["sell_gas_used"] for t in trades if t["route"] == "relay"]
bf = [t["live"]["base_fee_gwei"] for t in trades]
summary["gas"] = {"relay_buy_gas_used": gas_b, "relay_sell_gas_used": gas_s, "base_fee_gwei_at_our_buys": bf,
                  "round_trip_eth_typical": st.median(gas_b) * 1e-9 * st.median(bf) + st.median(gas_s) * 1e-9 * st.median(bf),
                  "round_trip_usd_typical": round((st.median(gas_b) + st.median(gas_s)) * st.median(bf) * 1e-9 * ETH_USD, 4)}

json.dump({"about": __doc__, "conventions": {"real_size_eth": REAL / 1e18, "stake_eth": STAKE / 1e18, "take_profit": TP, "hold_lead": [HOLD, LEAD], "engine_tp_gas_units": ENGINE_GAS_UNITS,
                                             "crowd_fingerprint": "UR execute 1124 bytes, deadline 2^256-1, type 2, priority fee 0.02 gwei, gas limit 220000/880000/260000"},
           "replay_check": dict(zip(("max_rel_err", "median_rel_err", "n"), validate_replay())),
           "summary": summary, "trades": trades, "launches": launch_rows}, open(HERE + "reaction.json", "w"), indent=1, default=str)

# ------------------------------------------------------------------ print
print("replay check (max, median rel. error of sqrtP, n):", validate_replay())
print("\nSTEP 1: OUR TEN LIVE TRADES")
for t in trades:
    c = t["current_exit"]
    print(f" {t['n']:2d} {t['time_utc'][5:]} {t['entry']:6s} {t['scheme']:16s} fee {t['fee_ppm']:4d} {t['route'][:6]} trig +{t['trigger_offset']} buy +{t['buy_offset_from_launch']} (trig+{t['buy_after_trigger']}) "
          f"crowd<=4: {t['crowd_buys_behind_within_4']} {t['crowd_buys_behind_within_4_detail']} first crowd after {t['first_crowd_buy_after_ours']} pull +{t['pull_after_our_buy']} "
          f"(base {t.get('baseline_pulled_within_same_gap')}) | live sold +{t['sell_after_buy_live']} {t['live']['ret']:+.2%} | cur TP {c['would_take_profit']} send +{c['send_after_buy']} "
          f"fast {c['fast']['ret']:+.2%} ({c['fast']['exit']}) slow {c['slow']['ret']:+.2%} ({c['slow']['exit']})")
print("\nSTEP 2:", json.dumps(summary, indent=1))
print("\nSTEP 3: OUTSIDER BUYS")
for r in launch_rows:
    for o in r["outsider_buys"]:
        print(f"  {r['time_utc'][11:16]} {r['kind']} {r['scheme']:22s} +{o['offset']:5d} {o['wallet'][:10]} {o['eth']:.5f} via {o['via']} before-crowd {o['before_first_crowd_buy']!s:5s} crowd prev10 {o['crowd_buys_prev_10']} (usual {o['baseline_crowd_buys_prev_10']}) next4 {o['crowd_buys_next_1_4']} next10 {o['crowd_buys_next_1_10']} (usual {o['baseline_crowd_buys_next_1_10']} on {o['baseline_n']}) until pull {o['crowd_buys_until_pull']} pull after {o['pull_after']} (chance {o.get('baseline_pulled_within_same_gap')})")
print("\nSCHEMES:")
for s, rows in sorted(by_scheme.items()):
    print(f"  {s:22s} n {len(rows):3d} clean {sum(1 for r in rows if clean(r)):3d} pull offsets (clean) {sorted(r['pull_offset'] for r in rows if clean(r) and r['pull_offset'] is not None)[:40]}")
    print(f"  {'':22s} first crowd buy offsets {collections.Counter(r['first_crowd_buy_offset'] for r in rows).most_common(12)}")
