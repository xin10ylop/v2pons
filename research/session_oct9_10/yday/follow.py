#!/usr/bin/env python3
"""Paper-price the FOLLOW entry of flip_engine 0.8 (ENTRY=auto -> follow on launches through the original launcher) on every Oct 8
2026 launch of kind "orig" in oct8_pools.json, from the chain.

Feed replay: every block from the launch to launch + 156 is fetched with its transactions, and the engine's own matching is applied
in block order (ingest/on_buy: value > 0, calldata >= 20 bytes, the token's address in the calldata, to != token, launch calls
skipped); each match moves the engine's copy of the price by tx.value (apply_buy, the receipt's liquidity). The first match with
value >= MIN_TRIGGER_ETH is the trigger; if it is at or before the arming block (launch + ARM_LAG) the pool is "late".
Pricing conventions: see the task / README in follow.json["meta"].

    python3 follow.py            (caches raw chain data in cache_follow.pkl next to this file)
"""
import sys, os, json, time, pickle, math, re, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__))
SCRATCH = os.path.dirname(HERE)
sys.path.insert(0, SCRATCH); sys.path.insert(0, "/home/user/v2pons/src")
from chain import rpc, batch, logs, PM, T_INIT, T_SWAP, T_ML, W, sgn
import v4math

Q96 = 1 << 96
OP = "3194e32622c5d860a0572c74edda99dcfd8fc827"; LAUNCHERS = {OP}; LAUNCH_SELECTORS = {"2fcb9108"}
RELAY = "2abb5653352f6b2f3b4f4261877cd02d9e05a957"; WALLET = "ab5a34c3f41e57fdee1a1d6f19d3e21f46df3ea8"
# the engine as it runs on the box (flip_engine 0.8 + /etc/flip/engine.env as given)
BUY_SLIP = 0.03; TAKE_PROFIT = 0.01; HOLD_BLOCKS = 4; SELL_LEAD_BLOCKS = 2; MIN_TRIGGER_WEI = int(0.0002 * 1e18)
TRIGGER_MAX_BLOCKS = 150; BUY_DELAY_BLOCKS = 0; FEE_MIN_PPM, FEE_MAX_PPM = 0, 9999; MIN_LIQUIDITY = 1e21; ETH_USD = 2570.0
ARM_LAG = 6            # arm_seq - launch_seq, median of 9 real armings of original-launcher launches by the 0.6 engine (Oct 9 dry run, 4-11 blocks)
ARM_LAG_RANGE = (3, 11)
STAKES = (0.0012, 0.004, 0.012)
SCAN = 157             # blocks scanned in full after the launch: trigger <= +150, buy <= trigger + 2, sell lands <= buy + 4
LOG_SPAN = 60000       # pool logs scanned after the launch for the pull (~1.7 h)
CACHE = os.path.join(HERE, "cache_follow.pkl")


def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x


def net_of_fee(x, fee):                                      # flip_engine.net_of_fee
    return x - (x * fee + 999_999) // 1_000_000


def pool_from_receipt(rec):                                  # flip_engine.pool_from_receipt, verbatim logic
    init = None; adds = []
    for l in rec.get("logs", []):
        if l["address"].lower() != PM or not l["topics"]:
            continue
        tp = l["topics"][0]
        if tp == T_INIT:
            init = l
        elif tp == T_ML:
            d = l["data"]; adds.append((sgn(W(d, 0)), sgn(W(d, 1)), sgn(W(d, 2)), l["topics"][1]))
    if init is None:
        return None
    d = init["data"]; pid = init["topics"][1]
    p = {"pid": pid, "c0": init["topics"][2][-40:], "token": init["topics"][3][-40:], "fee": W(d, 0), "tick_spacing": sgn(W(d, 1)), "hooks": d[2 + 64*2 + 24: 2 + 64*3],
         "sqrt_p": W(d, 3), "tick0": sgn(W(d, 4))}
    p["ranges"] = [(lo, hi, dl) for lo, hi, dl, ppid in adds if ppid == pid]
    p["liq"] = v4math.active_liquidity(p["tick0"], p["ranges"])
    return p


# ------------------------------------------------------------------ data
def gather():
    if os.path.exists(CACHE):
        return pickle.load(open(CACHE, "rb"))
    D = json.load(open(os.path.join(SCRATCH, "oct8_pools.json")))
    orig = [p for p in D["pools"] if p["kind"] == "orig"]
    head = int(rpc("eth_blockNumber", []), 16)
    recs = batch([("eth_getTransactionReceipt", [p["tx"]]) for p in orig])
    data = {"orig": orig, "head": head, "launch": {}}
    for i, (p, rec) in enumerate(zip(orig, recs)):
        b0 = p["block"]
        ls = logs({"address": PM, "topics": [[T_SWAP, T_ML], p["pid"]]}, b0, min(b0 + LOG_SPAN, head))
        blocks = batch([("eth_getBlockByNumber", [hex(b0 + k), True]) for k in range(SCAN)])
        data["launch"][p["pid"]] = {"rec": rec, "logs": ls, "blocks": blocks}
        print(f"  {i + 1}/{len(orig)} {b0} {len(ls)} logs", file=sys.stderr)
    # our relay's swaps on the day (and their receipts: gas), for the 'live' field and the gas measurement
    our = logs({"address": PM, "topics": [T_SWAP, None, "0x" + "0" * 24 + RELAY]}, D["first"], min(D["last"] + 20000, head))
    data["relay_logs"] = our
    data["relay_receipts"] = batch([("eth_getTransactionReceipt", [l["transactionHash"]]) for l in our])
    pickle.dump(data, open(CACHE, "wb"))
    return data


def wallet_receipts(data, hashes):
    key = "wallet_receipts"
    have = data.setdefault(key, {})
    need = [h for h in hashes if h not in have]
    if need:
        for h, r in zip(need, batch([("eth_getTransactionReceipt", [h]) for h in need])):
            have[h] = r
        pickle.dump(data, open(CACHE, "wb"))
    return have


# ------------------------------------------------------------------ gas
def measure_gas(data):
    """gasUsed of our real relay buys and sells on Oct 8 (status ok); a sell into a pulled pool costs more (135,200)"""
    buys, sells, sells_empty, egp_vs_base = [], [], [], []
    for l, r in zip(data["relay_logs"], data["relay_receipts"]):
        bn = int(l["blockNumber"], 16)
        if bn > 83719338 or r is None or r["status"] != "0x1":
            continue
        a0 = s128(W(l["data"], 0)); g = int(r["gasUsed"], 16)
        if a0 < 0: buys.append(g)
        elif a0 > 0: sells.append(g)
        else: sells_empty.append(g)
    return {"buy_gas": int(st.median(buys)), "sell_gas": int(st.median(sells)), "sell_gas_pulled": int(st.median(sells_empty)) if sells_empty else 135200,
            "n_buys": len(buys), "n_sells": len(sells), "n_sells_pulled": len(sells_empty), "buys": buys, "sells": sells, "sells_pulled": sells_empty}


# ------------------------------------------------------------------ one launch
def price_launch(p, L, G, ours_hashes):
    b0 = p["block"]; rec = L["rec"]; blocks = L["blocks"]
    bt = {int(b["number"], 16): b for b in blocks}
    base_fee = {n: int(b["baseFeePerGas"], 16) for n, b in bt.items()}
    ts0 = int(bt[b0]["timestamp"], 16)
    out = {"block": b0, "time_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(ts0)), "pid": p["pid"], "kind": p["kind"], "fee_ppm": p["fee"], "entry": "follow",
           "eligible": None, "skip_reason": None, "fire_block": None, "trigger_offset": None, "trigger_value_eth": None, "pull_block": None, "results": None, "live": None,
           "close_block": None, "notes": []}
    pool = pool_from_receipt(rec) if rec and rec.get("status") == "0x1" else None
    if pool is None or pool["pid"] != p["pid"]:
        out["eligible"] = False; out["skip_reason"] = "launch receipt has no pool (engine: launch_no_pool)"; return out
    fee = pool["fee"]; liq = pool["liq"]; token = pool["token"].lower(); tb = bytes.fromhex(token)
    gates = {"currency0_eth": pool["c0"] == "0" * 40, "hooks_zero": pool["hooks"] == "0" * 40, "fee_in_range": FEE_MIN_PPM <= fee <= FEE_MAX_PPM, "liquidity_ok": liq >= MIN_LIQUIDITY}
    eligible = all(gates.values())
    out.update({"eligible": eligible, "gates": gates, "liq_receipt": liq, "sqrt_p0": pool["sqrt_p"], "tick0": pool["tick0"], "ranges": pool["ranges"], "token": "0x" + token})
    if fee != p["fee"]:
        out["notes"].append(f"fee in receipt {fee} != json {p['fee']}")

    # chain: the pool's swaps (ours excluded) and liquidity changes
    ls = sorted(L["logs"], key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
    swaps = []; our_swaps = []; mls = []
    for l in ls:
        bn = int(l["blockNumber"], 16); li = int(l["logIndex"], 16); d = l["data"]
        if l["topics"][0] == T_SWAP:
            x = {"bn": bn, "li": li, "a0": s128(W(d, 0)), "a1": s128(W(d, 1)), "sp": W(d, 2), "L": W(d, 3), "tick": sgn(W(d, 4)), "fee": W(d, 5), "tx": l["transactionHash"],
                 "sender": l["topics"][2][-40:]}
            if x["sender"] == RELAY or l["transactionHash"] in ours_hashes:
                our_swaps.append(x)
            else:
                swaps.append(x)
        elif l["topics"][0] == T_ML:
            mls.append({"bn": bn, "li": li, "lo": sgn(W(d, 0)), "hi": sgn(W(d, 1)), "dl": sgn(W(d, 2)), "tx": l["transactionHash"]})
    pulls = [m for m in mls if m["dl"] < 0]
    pull = pulls[0]["bn"] if pulls else None
    out["pull_block"] = pull; out["pull_offset"] = (pull - b0) if pull is not None else None
    out["n_our_swaps_excluded"] = len(our_swaps)
    adds_after = [m for m in mls if m["dl"] > 0 and m["tx"] != p["tx"]]
    if adds_after:
        out["notes"].append(f"liquidity added after the launch at blocks {[m['bn'] for m in adds_after][:5]}")
    fees_seen = sorted({x["fee"] for x in swaps})
    if fees_seen and fees_seen != [fee]:
        out["notes"].append(f"swap fee field {fees_seen} != pool fee {fee}")

    def chain_after(bn):
        """(sqrtP, L) after every (non-our) swap up to and including block bn"""
        prev = [x for x in swaps if x["bn"] <= bn]
        return (prev[-1]["sp"], prev[-1]["L"]) if prev else (pool["sqrt_p"], liq)

    # feed replay (ingest + on_buy): the engine's copy of the price and the trigger
    feed = []   # (block, index, value, hash, from)
    for k in range(SCAN):
        b = bt.get(b0 + k)
        if b is None:
            continue
        for t in b["transactions"]:
            to = (t.get("to") or "")[2:].lower(); data = bytes.fromhex(t["input"][2:]); value = int(t["value"], 16)
            if to in LAUNCHERS or (LAUNCH_SELECTORS and data[:4].hex() in LAUNCH_SELECTORS):
                continue
            if value == 0 or len(data) < 20:
                continue
            if tb in data and to != token:
                feed.append({"bn": b0 + k, "idx": int(t["transactionIndex"], 16), "value": value, "tx": t["hash"], "from": t["from"][2:].lower(), "to": to})
    ours_feed = [f for f in feed if f["from"] == WALLET]
    feed = [f for f in feed if f["from"] != WALLET]                                 # the paper is the pool without us (trade 8's router buy carried ETH)
    if ours_feed:
        out["notes"].append(f"{len(ours_feed)} of our wallet's own ETH buys excluded from the feed replay")
    swap_txs = {x["tx"] for x in swaps}
    trig = next((f for f in feed if f["value"] >= MIN_TRIGGER_WEI), None)
    first_chain = next((x for x in swaps if -x["a0"] >= MIN_TRIGGER_WEI and x["a0"] < 0), None)
    out["first_real_swap_offset"] = (first_chain["bn"] - b0) if first_chain else None
    out["small_buys_before_trigger"] = sum(1 for f in feed if trig is None or (f["bn"], f["idx"]) < (trig["bn"], trig["idx"]))
    if trig is None:
        out["skip_reason"] = f"no real-size buy (tx value >= 0.0002 ETH carrying the token) within TRIGGER_MAX_BLOCKS ({TRIGGER_MAX_BLOCKS}; scanned {SCAN - 1})"
        if first_chain:
            out["skip_reason"] += f"; the chain's first >= 0.0002 ETH swap is at +{first_chain['bn'] - b0} (the engine logs 'late first buy (not the crowd)')"
        return out
    T = trig["bn"]; off = T - b0
    out.update({"trigger_offset": off, "trigger_value_eth": trig["value"] / 1e18, "trigger_tx": trig["tx"], "trigger_to": "0x" + trig["to"],
                "trigger_is_swap_in_pool": trig["tx"] in swap_txs})
    if not out["trigger_is_swap_in_pool"]:
        out["notes"].append("the trigger transaction made no Swap on this pool (reverted or other): the engine still fires on it")
    if first_chain and (first_chain["bn"] != T):
        out["notes"].append(f"feed trigger +{off} differs from the chain's first >=0.0002 ETH swap +{first_chain['bn'] - b0}")
    out["arm_sensitive"] = ARM_LAG_RANGE[0] <= off <= ARM_LAG_RANGE[1]
    if off > TRIGGER_MAX_BLOCKS:
        out["skip_reason"] = f"late first buy (not the crowd): trigger at +{off} > TRIGGER_MAX_BLOCKS {TRIGGER_MAX_BLOCKS}"; return out
    if off <= ARM_LAG:
        out["skip_reason"] = f"late: first real buy at +{off}, at or before the arming block (+{ARM_LAG})"; return out
    if not eligible:
        out["skip_reason"] = "pool not eligible: " + ", ".join(k for k, v in gates.items() if not v); return out

    # the engine fires in the trigger block (BUY_DELAY_BLOCKS 0), from its copy of the pool through the trigger transaction
    out["fire_block"] = T
    sp_feed_trig = float(pool["sqrt_p"])
    for f in feed:
        if (f["bn"], f["idx"]) > (trig["bn"], trig["idx"]):
            break
        sp_feed_trig = v4math.sqrt_after_buy(sp_feed_trig, liq, net_of_fee(f["value"], fee))
    sp_chain_T = chain_after(T)
    pos = [m["lo"] for m in mls if m["dl"] > 0 and m["lo"] < pool["tick0"] <= m["hi"]]
    tick_lo = max(pos) if pos else None
    sqrt_lo = (1.0001 ** (tick_lo / 2)) * Q96 if tick_lo is not None else 0.0

    results = {}; max_land = 0; live_gas = G
    for stake in STAKES:
        X = int(round(stake * 1e18)); xn = net_of_fee(X, fee)
        expected = v4math.buy_out_int(int(sp_feed_trig), liq, X, fee); min_out = int(expected * (1 - BUY_SLIP))
        expected_blk = v4math.buy_out_int(sp_chain_T[0], sp_chain_T[1], X, fee)    # the task's variant: every swap through the fire block
        R = {}
        for land in (1, 2):
            B = T + land
            spB, LB = chain_after(B)
            tokens = v4math.buy_out_int(spB, LB, X, fee) if LB > 0 else 0
            # the engine's copy at our buy (last in B) and the take-profit over B+1..B+HOLD-LEAD
            sp_f = float(pool["sqrt_p"])
            for f in feed:
                if f["bn"] > B:
                    break
                sp_f = v4math.sqrt_after_buy(sp_f, liq, net_of_fee(f["value"], fee))
            feed_tokens = v4math.buy_out_int(int(sp_f), liq, X, fee)
            sp_f = v4math.sqrt_after_buy(sp_f, liq, net_of_fee(X, fee))                 # our_buy_landed: apply_buy(p, STAKE)
            send = None; tp_ret = None; why = "deadline"; tp_seen = []
            for f in feed:
                if f["bn"] <= B:
                    continue
                if f["bn"] > B + HOLD_BLOCKS - SELL_LEAD_BLOCKS:
                    break
                sp_f = v4math.sqrt_after_buy(sp_f, liq, net_of_fee(f["value"], fee))
                if f["value"] < MIN_TRIGGER_WEI:
                    continue
                eth = v4math.sell_out_int(int(sp_f), liq, feed_tokens, fee)
                r = (eth - X - base_fee.get(f["bn"], 21_000_000) * 250_000) / X
                tp_seen.append(round(r, 5))
                if r >= TAKE_PROFIT:
                    send = f["bn"]; tp_ret = r; why = "take_profit"; break
            if send is None:
                send = B + HOLD_BLOCKS - SELL_LEAD_BLOCKS
            for speed, dl in (("fast", 1), ("slow", 2)):
                S = send + dl; max_land = max(max_land, S)
                bf_b = base_fee.get(B, 21_000_000); bf_s = base_fee.get(S, 21_000_000)
                rec_ = {"buy_block": B, "sell_send_block": send, "sell_land_block": S, "pull_after_buy": (pull - B) if pull is not None else None,
                        "send_reason": why, "tp_ret_feed": round(tp_ret, 5) if tp_ret is not None else None, "tp_checks": tp_seen,
                        "expected_tokens": expected, "min_out": min_out, "tokens": tokens, "feed_tokens": feed_tokens}
                if pull is not None and pull < B:
                    gas = (G["buy_gas"] + G["sell_gas"]) * bf_b
                    rec_.update({"exit": "pull_before_buy", "eth_out": 0, "gas_eth": gas / 1e18, "pnl_eth": -gas / 1e18, "ret": -gas / X})
                elif tokens < min_out:
                    gas = G["buy_gas"] * bf_b + G["sell_gas"] * bf_s                          # both revert; the success gas, an upper bound
                    rec_.update({"exit": "buy_reverted", "eth_out": 0, "gas_eth": gas / 1e18, "pnl_eth": -gas / 1e18, "ret": -gas / X,
                                 "revert_also_with_block_expected": tokens < int(expected_blk * (1 - BUY_SLIP))})
                elif pull is not None and pull <= S:
                    gas = G["buy_gas"] * bf_b + G["sell_gas_pulled"] * bf_s
                    rec_.update({"exit": "pull_first", "eth_out": 0, "gas_eth": gas / 1e18, "pnl_eth": (-X - gas) / 1e18, "ret": (-X - gas) / X})
                else:
                    spc, Lc = chain_after(S - 1)
                    sp_ours = int(Q96 / (Q96 / spc + xn / Lc))
                    eth_out = v4math.sell_out_int(sp_ours, Lc, tokens, fee)
                    gas = G["buy_gas"] * bf_b + G["sell_gas"] * bf_s
                    # exact replay: our buy put in after block B, then every later swap's own shift (buys add to 1/s, sells to s)
                    s = Q96 / (Q96 / spB + xn / LB); prev = spB
                    for x in swaps:
                        if x["bn"] <= B:
                            continue
                        if x["bn"] > S - 1:
                            break
                        if x["a0"] < 0:
                            s = Q96 / (Q96 / s + (Q96 / x["sp"] - Q96 / prev))
                        else:
                            s = s + (x["sp"] - prev)
                        prev = x["sp"]
                    eth_replay = v4math.sell_out_int(int(s), Lc, tokens, fee)
                    crossed = (Lc != LB) or (LB != liq) or (sp_ours <= sqrt_lo) or (Q96 / (Q96 / spB + xn / LB) <= sqrt_lo)
                    rec_.update({"exit": why, "eth_out": eth_out, "gas_eth": gas / 1e18, "pnl_eth": (eth_out - X - gas) / 1e18, "ret": (eth_out - X - gas) / X,
                                 "ret_gross": (eth_out - X) / X, "ret_exact_replay": (eth_replay - X - gas) / X, "range_crossed_or_L_changed": crossed})
                    if crossed:
                        out["notes"].append(f"stake {stake} land{land}_{speed}: liquidity range crossed or L changed (L at buy {LB}, at sell {Lc}, receipt {liq})")
                rec_["ret"] = round(rec_["ret"], 6); rec_["pnl_eth"] = round(rec_["pnl_eth"], 9)
                R[f"land{land}_{speed}"] = rec_
        results[str(stake)] = R
    out["results"] = results
    out["close_block"] = max_land + 30
    out["expected_from_feed_vs_chain_through_fire_block"] = {"feed_sqrtP_after_trigger_tx": int(sp_feed_trig), "chain_sqrtP_after_fire_block": sp_chain_T[0]}
    return out


# ------------------------------------------------------------------ live trades
def parse_live_txt():
    """research/data/live_trades_oct8.txt: section 1 (launch time -> trade #) and section 3 (the release-0.3 exit = the current exit,
    repriced on the real chain with our real buy in it)"""
    txt = open("/home/user/v2pons/research/data/live_trades_oct8.txt").read()
    s1 = {}; s3 = {}
    for m in re.finditer(r"^\s+(\d)\s+(\d\d:\d\d:\d\d)\s+(relay|router)\s+([\d.]+)%\s+\+(\d+)\s+trig\+(\d)\s+([+-][\d.]+)%\s+(\d+)\s+(\d+)\s+(YES|no)", txt, re.M):
        s1[m.group(2)] = {"n": int(m.group(1)), "route": m.group(3), "trigger_offset": int(m.group(5)), "buy_after_trigger": int(m.group(6)),
                          "ret_reported": float(m.group(7)) / 100, "pull_after_buy": int(m.group(8)), "sell_after_buy": int(m.group(9)), "pulled_first": m.group(10) == "YES"}
    for m in re.finditer(r"^\s+(\d): sent at \+(\d) \(([a-z ]+)\), landing \+(\d): ([^,]+), landing \+(\d): (.+)$", txt, re.M):
        f = lambda s: -1.0 if "pull" in s else float(s.strip().rstrip("%")) / 100
        s3[int(m.group(1))] = {"sent_after_buy": int(m.group(2)), "why": m.group(3), f"land_fast_after_buy": int(m.group(4)), "ret_fast": f(m.group(5)),
                               "land_slow_after_buy": int(m.group(6)), "ret_slow": f(m.group(7)),
                               "note": "live_trades_oct8.txt section 3: our real buy (real block, real tokens), the chain with it, gas 2 x 110,000 x 0.0201 gwei"}
    return s1, s3


def live_record(p, L, data, out, s1, s3):
    """our real trade on this pool, from the receipts"""
    ls = sorted(L["logs"], key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
    hs = []
    for b in L["blocks"]:
        for t in b["transactions"]:
            if t["from"][2:].lower() == WALLET:
                hs.append(t["hash"])
    relay_tx = [l["transactionHash"] for l in ls if l["topics"][0] == T_SWAP and l["topics"][2][-40:] == RELAY]
    hs = sorted(set(hs) | set(relay_tx))
    if not hs:
        return None
    R = wallet_receipts(data, hs)
    legs = []
    for h in hs:
        r = R[h]
        if r is None:
            continue
        sw = [l for l in r["logs"] if l["address"].lower() == PM and l["topics"] and l["topics"][0] == T_SWAP and l["topics"][1] == p["pid"]]
        g = int(r["gasUsed"], 16) * int(r["effectiveGasPrice"], 16)
        leg = {"tx": h, "block": int(r["blockNumber"], 16), "index": int(r["transactionIndex"], 16), "status": r["status"], "gas_used": int(r["gasUsed"], 16), "gas_eth": g / 1e18,
               "to": r["to"]}
        if sw:
            leg["a0"] = s128(W(sw[0]["data"], 0)); leg["a1"] = s128(W(sw[0]["data"], 1))
        legs.append(leg)
    legs = [x for x in legs if "a0" in x or x["status"] != "0x1"]
    if not legs:
        return None
    buy = next((x for x in legs if x.get("a0", 0) < 0), None); sell = next((x for x in legs if x.get("a0", -1) >= 0 and x is not buy), None)
    pulls = sorted((int(l["blockNumber"], 16), int(l["logIndex"], 16)) for l in ls if l["topics"][0] == T_ML and sgn(W(l["data"], 2)) < 0)
    eth_in = -buy["a0"] if buy else 0; eth_out = sell["a0"] if sell else 0; gas = sum(x["gas_eth"] for x in legs)
    rec = {"route": "relay" if buy and buy["to"][2:].lower() == RELAY else "router (wallet)", "buy_block": buy["block"] if buy else None, "sell_block": sell["block"] if sell else None,
           "buy_offset_from_launch": (buy["block"] - p["block"]) if buy else None,
           "buy_after_feed_trigger": (buy["block"] - out["fire_block"]) if buy and out.get("fire_block") else None,
           "eth_in": eth_in / 1e18, "eth_out": eth_out / 1e18, "tokens_bought": buy["a1"] if buy else None, "tokens_sold": -sell["a1"] if sell else None, "gas_eth": gas,
           "pnl_eth": eth_out / 1e18 - eth_in / 1e18 - gas, "ret_gross": (eth_out - eth_in) / eth_in if eth_in else None,
           "ret_net": (eth_out / 1e18 - eth_in / 1e18 - gas) / (eth_in / 1e18) if eth_in else None,
           "pull_block": pulls[0][0] if pulls else None, "pull_after_buy": (pulls[0][0] - buy["block"]) if pulls and buy else None,
           "pulled_before_sell": bool(pulls and sell and pulls[0] < (sell["block"], 10**9) and pulls[0][0] <= sell["block"]) if pulls and sell else False,
           "legs": legs}
    # precise pulled-first: the pull's log before the sell's swap log
    if pulls and sell:
        sell_li = next((int(l["logIndex"], 16) for l in ls if l["transactionHash"] == sell["tx"] and l["topics"][0] == T_SWAP), None)
        rec["pulled_before_sell"] = pulls[0] < (sell["block"], sell_li if sell_li is not None else 10**9)
    hhmmss = out["time_utc"][11:]
    if hhmmss in s1:
        n = s1[hhmmss]["n"]; rec["live_trades_oct8"] = {"trade": n, **s1[hhmmss]}
        rec["entry_live"] = "follow (release 0.2-0.3, the OLD exit)"
        rec["current_exit_on_real_chain"] = s3.get(n)
    else:
        rec["entry_live"] = "seat (overnight live trade, release 0.5/0.6 ENTRY=seat, the current exit)"
        rec["current_exit_on_real_chain"] = None
    return rec


def day_summary(recs, cap=3, stop_usd=15.0):
    """the day for the follow entry alone: (a) every traded launch; (b) the engine's limits in time order: MAX_TRADES_PER_DAY 3 (a fired
    trade counts, a reverted buy too: it has a receipt), one position at a time (fire_block before the previous close_block = skip),
    DAILY_STOP_USD 15, the halt after a pull at or before our sell. Seat trades on the per-launch copies (from block 83402323, 14:59)
    share the cap; under the cap of 3 they never come, since three follow trades fire before 09:46."""
    out = {}
    traded = sorted([r for r in recs if r["results"]], key=lambda r: r["fire_block"])
    for stake in STAKES:
        for v in ("land1_fast", "land1_slow", "land2_fast", "land2_slow"):
            xs = [r["results"][str(stake)][v] for r in traded]
            allr = {"n": len(xs), "pnl_eth": sum(x["pnl_eth"] for x in xs), "mean_ret": st.mean([x["ret"] for x in xs]), "wins": sum(1 for x in xs if x["ret"] > 0)}
            n = 0; pnl = 0.0; busy_until = -1; halted = False; taken = []
            for r in traded:
                x = r["results"][str(stake)][v]
                if halted or n >= cap or pnl * ETH_USD <= -stop_usd or r["fire_block"] < busy_until:
                    continue
                n += 1; pnl += x["pnl_eth"]; busy_until = r["close_block"]; taken.append(r["block"])
                if x["exit"] == "pull_first":
                    halted = True
            out[f"{stake}/{v}"] = {"all": allr, "engine_limits": {"n": n, "pnl_eth": pnl, "pnl_usd": pnl * ETH_USD, "launches": taken, "halted": halted}}
    return out


def main():
    data = gather()
    G = measure_gas(data)
    print(f"gas measured on our {G['n_buys']} relay buys / {G['n_sells']} sells (Oct 8): buy {G['buy_gas']}, sell {G['sell_gas']}, sell into a pulled pool {G['sell_gas_pulled']}")
    s1, s3 = parse_live_txt()
    recs = []; allbf = []
    for p in data["orig"]:
        L = data["launch"][p["pid"]]
        allbf += [int(b["baseFeePerGas"], 16) for b in L["blocks"]]
        ours_hashes = set()
        for b in L["blocks"]:
            for t in b["transactions"]:
                if t["from"][2:].lower() == WALLET:
                    ours_hashes.add(t["hash"])
        out = price_launch(p, L, G, ours_hashes)
        out["live"] = live_record(p, L, data, out, s1, s3)
        recs.append(out)
    bf_med = st.median(allbf)
    meta = {"engine": "flip_engine 0.8, ENTRY=auto -> follow on the original launcher", "params": {"BUY_SLIP": BUY_SLIP, "TAKE_PROFIT": TAKE_PROFIT, "HOLD_BLOCKS": HOLD_BLOCKS,
            "SELL_LEAD_BLOCKS": SELL_LEAD_BLOCKS, "MIN_TRIGGER_ETH": 0.0002, "TRIGGER_MAX_BLOCKS": TRIGGER_MAX_BLOCKS, "BUY_DELAY_BLOCKS": 0, "FEE_PPM": [0, 9999],
            "MIN_LIQUIDITY": MIN_LIQUIDITY, "ARM_LAG_blocks": ARM_LAG, "ETH_USD": ETH_USD},
            "gas": {**{k: v for k, v in G.items() if k not in ("buys", "sells", "sells_pulled")}, "base_fee_median_wei": bf_med,
                    "round_trip_eth_at_median": (G["buy_gas"] + G["sell_gas"]) * bf_med / 1e18, "round_trip_usd_at_median": (G["buy_gas"] + G["sell_gas"]) * bf_med / 1e18 * ETH_USD,
                    "how": "gasUsed (median of our real Oct 8 relay receipts) x baseFeePerGas of the buy's and the sell's landing block (effectiveGasPrice == baseFee on this chain)"}}
    meta["day_summary"] = day_summary(recs)
    meta["conventions"] = ("buy priced after every other swap of its block; minOut = the engine's expected (its feed copy through the trigger tx) x 0.97, a fill "
                           "under it = buy_reverted (minus both txs' gas); sell sent on the first feed buy behind ours (blocks B+1..B+2) pricing the sell at "
                           ">= +1% after base_fee x 250k gas (take_profit()), else at B+2; lands send+1 (fast) or send+2 (slow) and is priced at the head of "
                           "that block (chain after S-1 + our buy, 1/sqrtP additive; ret_exact_replay replays later sells exactly); pull block <= S = "
                           "pull_first (-100% - gas), pull < B = pull_before_buy (buy reverts); our own swaps (relay sender, wallet txs) excluded")
    json.dump({"meta": meta, "launches": recs}, open(os.path.join(HERE, "follow.json"), "w"), indent=1, default=str)
    # summary
    print(f"base fee median {bf_med / 1e9:.4f} gwei; round trip {(G['buy_gas'] + G['sell_gas']) * bf_med / 1e18:.3e} ETH = ${(G['buy_gas'] + G['sell_gas']) * bf_med / 1e18 * ETH_USD:.4f}")
    traded = [r for r in recs if r["results"]]
    print(f"{len(recs)} orig launches; traded {len(traded)}; skips:")
    import collections
    print(collections.Counter((r["skip_reason"] or "").split(":")[0] for r in recs if not r["results"]))
    for r in recs:
        res = r["results"]
        line = f"{r['time_utc'][11:]} {r['block']} fee {r['fee_ppm']:5d} trig +{r['trigger_offset']} pull {r['pull_offset']}"
        if res:
            line += " | " + " ".join(f"{k}:{v['ret']:+.3f}{v['exit'][0]}" for k, v in res["0.0012"].items())
        else:
            line += " | " + str(r["skip_reason"])
        if r["live"]:
            lv = r["live"]; line += f" || LIVE {lv['entry_live'][:6]} net {lv['ret_net']:+.3f}"
        print(line)
    for stake in STAKES:
        for v in ("land1_fast", "land1_slow", "land2_fast", "land2_slow"):
            xs = [r["results"][str(stake)][v] for r in traded]
            rets = [x["ret"] for x in xs]
            print(f"stake {stake} {v}: n {len(rets)} mean {st.mean(rets):+.4f} median {st.median(rets):+.4f} worst {min(rets):+.4f} wins {sum(1 for x in rets if x > 0)} "
                  f"total {sum(x['pnl_eth'] for x in xs):+.6f} ETH exits {dict(collections.Counter(x['exit'] for x in xs))}")
    print("\nthe day under the engine's limits (cap 3/day, one position, $15 stop, halt on pull_first), follow entry alone:")
    for k, v in meta["day_summary"].items():
        e = v["engine_limits"]
        print(f"  {k:22s} n {e['n']} pnl {e['pnl_eth']:+.6f} ETH (${e['pnl_usd']:+.3f}) launches {e['launches']}{' HALTED' if e['halted'] else ''} | uncapped: n {v['all']['n']} {v['all']['pnl_eth']:+.6f} ETH")


if __name__ == "__main__":
    main()
