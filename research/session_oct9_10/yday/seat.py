#!/usr/bin/env python3
"""Paper-price the SEAT entry of flip_engine 0.8 (ENTRY=auto -> seat on a launch through a per-launch launcher copy whose code hash
is in SEAT_CODE_HASHES) on every Oct 8 2026 launch of kind "copy" in oct8_pools.json, from the chain (data: seat_fetch.py,
seat_fetch_deploy.py -> cache_seat.pkl).

Engine semantics replayed (flip_engine.py 0.8):
  arm_launch   pool from the launch receipt (pool_from_receipt: ETH currency0, hooks, fee, active liquidity of the receipt's adds);
               eligible = ETH pair, no hook, 0 <= fee <= 9999 ppm, liq >= 1e21, launcher code hash in LAUNCHER_CODE_HASHES;
               entry = seat when the code hash is in SEAT_CODE_HASHES.
  ingest/on_buy  every tx in block order with value > 0, calldata >= 20 bytes, the token's 20 address bytes in the calldata,
               to != token (launch calls skipped) moves the engine's copy of the price by tx.value (apply_buy); one with value >=
               MIN_TRIGGER_ETH is a real buy; on a seat pool still "armed" the first real buy makes it "late" (no trade).
  seat fire    when the feed shows L + SEAT_FIRE_AT (6) with no real buy seen in L..L+6: fire. expected = buy_out_int(feed sqrtP at
               the fire block, receipt liq, stake, fee), minOut = expected * (1 - BUY_SLIP).
  our buy      lands at L+7 or L+8 ("land7"/"land8"), priced AFTER every other swap of its block (conservative). Real fill (chain
               state after block B) < minOut -> the buy reverts: result = minus the gas of both txs, exit "buy_reverted".
  take_profit  in the feed blocks B+1..B+2 (the conservative ordering puts every tx of block B ahead of ours), each real buy (value
               >= MIN_TRIGGER) moves the feed price and prices our sell: sell_out_int(feed sqrtP incl. our buy, liq, feed_tokens, fee)
               - stake - base_fee * 250000 >= TAKE_PROFIT * stake -> the sell is sent in that block; otherwise at B + HOLD - LEAD
               (B+2), the deadline. It lands at send+1 ("fast") or send+2 ("slow").
  the sell     priced at the head of S: the chain after block S-1 with our buy inserted at the end of block B (each later swap
               replayed by its own chain delta: a buy's d(1/sqrtP), a sell's d(sqrtP), exact for exact-input swaps on one range;
               equal to the 1/sqrtP-additive convention when only buys intervene), fee on the input (v4math.sell_out_int).
  the pull     the first ModifyLiquidity with negative liquidityDelta; pull block <= S -> -100% of the stake minus gas ("pull_first").
  gas          gasUsed of our real Oct 8 relay receipts (median buy / sell; a sell into a pulled pool 135,200) x baseFeePerGas of
               the landing block (effectiveGasPrice == baseFee on this chain, checked on all 18 relay receipts of the day).

    python3 seat.py      -> seat.json (one record per copy launch) + a summary on stdout
"""
import sys, os, json, time, pickle, statistics as st, collections
HERE = os.path.dirname(os.path.abspath(__file__)); SCRATCH = os.path.dirname(HERE)
sys.path.insert(0, SCRATCH); sys.path.insert(0, "/home/user/v2pons/src")
from chain import PM, T_INIT, T_SWAP, T_ML, W, sgn
from eth_utils import keccak
import v4math

Q96 = 1 << 96
OP = "3194e32622c5d860a0572c74edda99dcfd8fc827"; LAUNCHERS = {OP}; LAUNCH_SELECTORS = {"2fcb9108"}
RELAY = "2abb5653352f6b2f3b4f4261877cd02d9e05a957"; WALLET = "ab5a34c3f41e57fdee1a1d6f19d3e21f46df3ea8"
DUST = "e71a69f434a719cd5afa411568b69716aab3b84a"
SEAT_CODE_HASHES = {"2793923de1845d8707004ebbf2ab49fe7286113b7b69991aea7d6656f26f6d1c"}
LAUNCHER_CODE_HASHES = {"2793923de1845d8707004ebbf2ab49fe7286113b7b69991aea7d6656f26f6d1c", "42544ef5d4754816b3cfe77f3a6fb1c8eb842d6eee101f7d15c638593a3351d2"}
BUY_SLIP = 0.03; TAKE_PROFIT = 0.01; HOLD_BLOCKS = 4; SELL_LEAD_BLOCKS = 2; MIN_TRIGGER_WEI = int(0.0002 * 1e18)
TRIGGER_MAX_BLOCKS = 150; SEAT_FIRE_AT = 6; FEE_MIN_PPM, FEE_MAX_PPM = 0, 9999; MIN_LIQUIDITY = 1e21; ETH_USD = 2570.0
STAKES = (0.0012, 0.004, 0.012)
LANDS = (7, 8)                  # the task's variants (fire at L+6); an arming between the feed's L+6 and L+7 fires at L+7: extra_fire7 (land 8/9)
CACHE = os.path.join(HERE, "cache_seat.pkl"); OUT = os.path.join(HERE, "seat.json")


def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x


def net_of_fee(x, fee):                                      # flip_engine.net_of_fee
    return x - (x * fee + 999_999) // 1_000_000


def pool_from_receipt(rec):                                  # flip_engine.pool_from_receipt (topics compared with the 0x)
    init = None; adds = []
    for l in rec.get("logs", []):
        if l["address"].lower() != PM or not l["topics"]:
            continue
        if l["topics"][0] == T_INIT:
            init = l
        elif l["topics"][0] == T_ML:
            d = l["data"]; adds.append((sgn(W(d, 0)), sgn(W(d, 1)), sgn(W(d, 2)), l["topics"][1]))
    if init is None:
        return None
    d = init["data"]; pid = init["topics"][1]
    p = {"pid": pid, "c0": init["topics"][2][-40:], "token": init["topics"][3][-40:].lower(), "fee": W(d, 0), "tick_spacing": sgn(W(d, 1)),
         "hooks": d[2 + 64*2 + 24: 2 + 64*3], "sqrt_p": W(d, 3), "tick0": sgn(W(d, 4))}
    p["ranges"] = [(lo, hi, dl) for lo, hi, dl, ppid in adds if ppid == pid]
    p["liq"] = v4math.active_liquidity(p["tick0"], p["ranges"])
    return p


def sqrt_at_tick(t):
    return (1.0001 ** (t / 2)) * Q96


# ------------------------------------------------------------------ gas
def measure_gas(d):
    buys, sells, sells_pulled, egp_eq_base = [], [], [], 0
    for l, r in zip(d["relay_logs"], d["relay_receipts"]):
        if r is None or r["status"] != "0x1" or int(l["blockNumber"], 16) > d["last"]:
            continue
        a0 = s128(W(l["data"], 0)); g = int(r["gasUsed"], 16)
        (buys if a0 < 0 else sells if a0 > 0 else sells_pulled).append(g)
    return {"buy_gas": int(st.median(buys)), "sell_gas": int(st.median(sells)), "sell_gas_pulled": int(st.median(sells_pulled)),
            "n_buys": len(buys), "n_sells": len(sells), "n_sells_pulled": len(sells_pulled), "buys": buys, "sells": sells, "sells_pulled": sells_pulled}


# ------------------------------------------------------------------ the feed
def feed_matches(blocks, token, L):
    """the engine's view, block by block: [(block, tx_index, value, hash, from, to)] of txs on_buy would see for this token"""
    tb = bytes.fromhex(token); out = []
    for b in blocks:
        bn = int(b["number"], 16)
        for t in sorted(b["transactions"], key=lambda t: int(t["transactionIndex"], 16)):
            to = (t["to"] or "")[2:].lower(); data = bytes.fromhex(t["input"][2:]); value = int(t["value"], 16)
            if to in LAUNCHERS or (LAUNCH_SELECTORS and data[:4].hex() in LAUNCH_SELECTORS):
                continue
            if value == 0 or len(data) < 20:
                continue
            if tb in data and to != token:
                out.append((bn, int(t["transactionIndex"], 16), value, t["hash"], t["from"][2:].lower(), to))
    return out


# ------------------------------------------------------------------ one launch
def price_launch(i, p, d, G):
    L = p["block"]; pid = p["pid"]; blocks = d["blocks"][pid]; bt = {int(b["number"], 16): b for b in blocks}
    base_fee = {n: int(b["baseFeePerGas"], 16) for n, b in bt.items()}
    ts0 = int(bt[L]["timestamp"], 16)
    out = {"block": L, "time_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(ts0)), "pid": pid, "kind": p["kind"], "fee_ppm": p["fee"], "entry": None,
           "eligible": None, "skip_reason": None, "fire_block": None, "trigger_offset": None, "trigger_value_eth": None, "pull_block": None, "results": None,
           "live": None, "close_block": None, "launcher": p["to"], "notes": []}
    # launcher code (the public RPC keeps no historical state: the code read at 'latest'; its creation tx is in L-8..L-7)
    code = d["code_latest"][i]; ch = keccak(bytes.fromhex(code[2:])).hex() if code and len(code) > 2 else None
    dep = d["deploy"].get(pid)
    out["launcher_code"] = {"hash": ch, "bytes": len(code) // 2 - 1 if code else 0, "read_at": "latest (eth_getCode at the launch block: 'historical state not available' on the public RPC)",
                            "created_block": dep["block"] if dep else None, "created_offset": (dep["block"] - L) if dep else None, "created_by_launch_sender": bool(dep and dep["from"].lower() == p["from"].lower())}
    rec = d["rec"][i]
    pool = pool_from_receipt(rec) if rec and rec.get("status") == "0x1" else None
    if pool is None or pool["pid"] != pid:
        out.update({"eligible": False, "skip_reason": "launch receipt has no pool"}); return out
    fee = pool["fee"]; liq = pool["liq"]; token = pool["token"]
    out.update({"token": "0x" + token, "liq_receipt": liq, "sqrt_p0": pool["sqrt_p"], "tick0": pool["tick0"], "ranges": pool["ranges"]})
    code_ok = ch in LAUNCHER_CODE_HASHES
    out["entry"] = "seat" if ch in SEAT_CODE_HASHES else "follow"
    gates = {"currency0_eth": pool["c0"] == "0" * 40, "hooks_zero": pool["hooks"] == "0" * 40, "fee_in_range": FEE_MIN_PPM <= fee <= FEE_MAX_PPM,
             "liquidity_ok": liq >= MIN_LIQUIDITY, "launcher_code_operator": code_ok}
    out["gates"] = gates; out["eligible"] = all(gates.values())
    if fee != p["fee"]:
        out["notes"].append(f"fee in receipt {fee} != json {p['fee']}")

    # chain: the pool's swaps and the pull
    ls = sorted(d["logs"][pid], key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
    txs = {t["hash"]: t for b in blocks for t in b["transactions"]}
    sw_all = []; pull = None
    for l in ls:
        bn = int(l["blockNumber"], 16)
        if l["topics"][0] == T_ML:
            if sgn(W(l["data"], 2)) < 0 and pull is None:
                pull = bn
            continue
        dd = l["data"]
        sw_all.append({"bn": bn, "li": int(l["logIndex"], 16), "a0": s128(W(dd, 0)), "a1": s128(W(dd, 1)), "sp": W(dd, 2), "L": W(dd, 3), "tick": sgn(W(dd, 4)),
                       "sender": l["topics"][2][-40:].lower(), "tx": l["transactionHash"]})
    ours = [x for x in sw_all if x["sender"] == RELAY]
    sw = [x for x in sw_all if x["sender"] != RELAY]                                      # the paper is the pool without us
    out["pull_block"] = pull; out["pull_offset"] = (pull - L) if pull else None
    if ours:
        out["notes"].append(f"{len(ours)} relay swaps on this pool (excluded from the paper)")

    # the burst and who bought before it (chain swaps, with the tx's sender and value)
    buys = []
    for x in sw:
        if x["a0"] >= 0: continue
        t = txs.get(x["tx"]); fr = t["from"][2:].lower() if t else None
        buys.append({"offset": x["bn"] - L, "eth": -x["a0"] / 1e18, "tx_value_eth": int(t["value"], 16) / 1e18 if t else None, "from": "0x" + fr if fr else None,
                     "to": t["to"] if t else None, "dust_tester": fr == DUST})
    real = [b for b in buys if b["eth"] * 1e18 >= MIN_TRIGGER_WEI and not b["dust_tester"]]
    burst = None
    if real:
        bo = real[0]["offset"]; inb = [b for b in real if b["offset"] == bo]; first3 = real[:3]
        pre = [b for b in buys if b["offset"] < bo]
        same_block_small = [b for b in buys if b["offset"] == bo and b not in inb]
        burst = {"block_offset": bo, "buys_in_burst_block": len(inb), "eth_in_burst_block": round(sum(b["eth"] for b in inb), 6),
                 "first_three_real_buys": [{"offset": b["offset"], "eth": round(b["eth"], 6), "from": b["from"]} for b in first3],
                 "first_three_eth": round(sum(b["eth"] for b in first3), 6), "first_three_one_block": len({b["offset"] for b in first3}) == 1,
                 "buys_before_burst": [{"offset": b["offset"], "eth": b["eth"], "from": b["from"], "dust_tester": b["dust_tester"]} for b in pre],
                 "dust_tester_before_burst": any(b["dust_tester"] for b in pre), "dust_tester_eth_before": sum(b["eth"] for b in pre if b["dust_tester"]),
                 "others_before_burst_n": sum(1 for b in pre if not b["dust_tester"]), "others_before_burst_eth": sum(b["eth"] for b in pre if not b["dust_tester"]),
                 "real_size_before_burst": [b for b in pre if b["eth"] * 1e18 >= MIN_TRIGGER_WEI],
                 "dust_tester_in_burst_block": [b["eth"] for b in same_block_small if b["dust_tester"]],
                 "next_real_buy_after_burst_offset": next((b["offset"] for b in real if b["offset"] > bo), None)}
    out["burst"] = burst

    # the feed replay
    fm = feed_matches(blocks, token, L)
    out["feed_txs_to_L12"] = [{"offset": bn - L, "idx": ix, "value_eth": v / 1e18, "from": "0x" + fr} for bn, ix, v, h, fr, to in fm if bn - L <= 12]
    if out["entry"] != "seat":
        out["skip_reason"] = "other code"; return out
    if not out["eligible"]:
        out["skip_reason"] = "not eligible: " + ",".join(k for k, ok in gates.items() if not ok); return out

    def feed_through(fire):
        """the engine's sqrtP at the end of the fire block and the first real buy at or before it (the seat's 'late')"""
        spf = float(pool["sqrt_p"]); first = None
        for bn, ix, v, h, fr, to in fm:
            if bn > fire: break
            spf = v4math.sqrt_after_buy(spf, liq, net_of_fee(v, fee))
            if v >= MIN_TRIGGER_WEI and first is None: first = (bn, v)
        return spf, first

    def chain_after(blk):                                          # the chain state after a block (no swap of ours on these pools)
        prev = [x for x in sw if x["bn"] <= blk]
        return (prev[-1]["sp"], prev[-1]["L"]) if prev else (pool["sqrt_p"], liq)
    tick_lo = min(lo for lo, hi, dl in pool["ranges"] if dl > 0 and lo < pool["tick0"] <= hi); tick_hi = max(hi for lo, hi, dl in pool["ranges"] if dl > 0 and lo < pool["tick0"] <= hi)
    s_lo, s_hi = sqrt_at_tick(tick_lo), sqrt_at_tick(tick_hi)

    def price(fire, B, stake_eth, sp_fire):
        X = int(round(stake_eth * 1e18)); xn = net_of_fee(X, fee)
        expected = v4math.buy_out_int(int(sp_fire), liq, X, fee); min_out = int(expected * (1 - BUY_SLIP))
        spf = sp_fire                                              # the feed through our buy's block (every tx of block B ahead of ours), then our buy
        for bn, ix, v, h, fr, to in fm:
            if fire < bn <= B: spf = v4math.sqrt_after_buy(spf, liq, net_of_fee(v, fee))
        feed_tokens = v4math.buy_out_int(int(spf), liq, X, fee)
        spf = v4math.sqrt_after_buy(spf, liq, xn)
        spc, Lc = chain_after(B)                                   # the chain fill, after every other swap of block B
        fill = v4math.buy_out_int(spc, Lc, X, fee) if (pull is None or pull > B) else 0
        gas_est = base_fee[B] * 250_000; send = B + HOLD_BLOCKS - SELL_LEAD_BLOCKS; why = "deadline"; tp_ret = None
        for bn, ix, v, h, fr, to in fm:                            # take_profit on the feed's real buys behind ours, B+1..B+HOLD-LEAD
            if bn <= B: continue
            if bn > B + HOLD_BLOCKS - SELL_LEAD_BLOCKS: break
            spf = v4math.sqrt_after_buy(spf, liq, net_of_fee(v, fee))
            if v < MIN_TRIGGER_WEI: continue
            r = (v4math.sell_out_int(int(spf), liq, feed_tokens, fee) - X - gas_est) / X
            if r >= TAKE_PROFIT:
                send = bn; why = "take_profit"; tp_ret = r; break
        res = {}
        for spd, lag in (("fast", 1), ("slow", 2)):
            S = send + lag
            rr = {"buy_block": B, "sell_send_block": send, "sell_land_block": S, "pull_after_buy": (pull - B) if pull else None,
                  "expected_tokens": expected, "min_out": min_out, "feed_tokens": feed_tokens, "fill_tokens": fill, "fill_vs_expected": fill / expected - 1 if expected else None,
                  "send_why": why, "tp_ret_feed": tp_ret, "base_fee_buy_gwei": base_fee[B] / 1e9, "base_fee_sell_gwei": base_fee.get(S, base_fee[B]) / 1e9}
            if pull is not None and pull <= B:
                gas = G["buy_gas"] * base_fee[B] + G["sell_gas"] * base_fee.get(S, base_fee[B])
                rr.update({"exit": "buy_reverted", "eth_out": 0, "gas_eth": gas / 1e18, "pnl_eth": -gas / 1e18, "ret": -gas / X, "why": "pulled at or before our buy's block"})
            elif fill < min_out:
                gas = G["buy_gas"] * base_fee[B] + G["sell_gas"] * base_fee.get(S, base_fee[B])      # both revert; the success gas, an upper bound
                rr.update({"exit": "buy_reverted", "eth_out": 0, "gas_eth": gas / 1e18, "pnl_eth": -gas / 1e18, "ret": -gas / X})
            elif pull is not None and pull <= S:
                gas = G["buy_gas"] * base_fee[B] + G["sell_gas_pulled"] * base_fee.get(S, base_fee[B])
                rr.update({"exit": "pull_first", "eth_out": 0, "gas_eth": gas / 1e18, "pnl_eth": (-X - gas) / 1e18, "ret": (-X - gas) / X})
            else:
                so = v4math.sqrt_after_buy(spc, Lc, xn); prev_sp = spc; crossed = False; sells_between = 0
                for x in sw:                                       # our buy at the end of B, the chain's later swaps replayed onto it
                    if B < x["bn"] <= S - 1:
                        if x["L"] != Lc: crossed = True
                        if x["a0"] < 0: so = 1.0 / (1.0 / so + (Q96 / x["sp"] - Q96 / prev_sp) / Q96)
                        else: so = so + (x["sp"] - prev_sp); sells_between += 1
                        prev_sp = x["sp"]
                spS, LS = chain_after(S - 1)
                so_conv = Q96 / (Q96 / spS + xn / LS)              # the task's 1/sqrtP-additive convention
                eth_out = v4math.sell_out_int(int(so), Lc, fill, fee)
                eth_out_conv = v4math.sell_out_int(int(so_conv), LS, fill, fee)
                s_after_sell = so + net_of_fee(fill, fee) * Q96 / Lc
                if not (s_lo <= so <= s_hi) or s_after_sell > s_hi * (1 + 1e-12): crossed = True
                gas = G["buy_gas"] * base_fee[B] + G["sell_gas"] * base_fee[S]
                rr.update({"exit": why, "eth_out": eth_out, "gas_eth": gas / 1e18, "pnl_eth": (eth_out - X - gas) / 1e18, "ret": (eth_out - X - gas) / X,
                           "ret_gross": (eth_out - X) / X, "ret_convention": (eth_out_conv - X - gas) / X, "sells_between": sells_between, "range_crossed_or_L_changed": crossed,
                           "eth_out_flat": v4math.sell_out_int(int(v4math.sqrt_after_buy(spc, Lc, xn)), Lc, fill, fee)})
            res[spd] = rr
        return res

    # the seat as asked: fire at the feed's L+6, land at L+7 / L+8
    fire = L + SEAT_FIRE_AT
    sp_fire, first_real = feed_through(fire)
    if first_real is not None:
        out["skip_reason"] = f"late: a real buy ({first_real[1] / 1e18:.5f} ETH) at +{first_real[0] - L}, before the seat fired at +{SEAT_FIRE_AT}"; return out
    out.update({"fire_block": fire, "trigger_offset": SEAT_FIRE_AT, "trigger_value_eth": 0.0})
    out["feed_vs_chain_sqrtp_at_fire"] = sp_fire / chain_after(fire)[0] - 1
    results = {}
    for stake_eth in STAKES:
        results[str(stake_eth)] = {}
        for k in LANDS:
            r2 = price(fire, L + k, stake_eth, sp_fire)
            for spd in ("fast", "slow"): results[str(stake_eth)][f"land{k}_{spd}"] = r2[spd]
    out["results"] = results
    out["close_block"] = max(results[str(s)][f"land{k}_{spd}"]["sell_land_block"] for s in STAKES for k in LANDS for spd in ("fast", "slow")) + 30
    # extra: armed between the feed's L+6 and L+7 -> the engine fires at L+7 (its own late check and minOut through L+7), landing L+8 / L+9
    sp7, first7 = feed_through(L + SEAT_FIRE_AT + 1)
    if first7 is not None:
        out["extra_fire7"] = {"skip_reason": f"late: a real buy at +{first7[0] - L}"}
    else:
        ex = {}
        for stake_eth in STAKES:
            ex[str(stake_eth)] = {}
            for k in (SEAT_FIRE_AT + 2, SEAT_FIRE_AT + 3):
                r2 = price(L + SEAT_FIRE_AT + 1, L + k, stake_eth, sp7)
                for spd in ("fast", "slow"): ex[str(stake_eth)][f"land{k}_{spd}"] = r2[spd]
        out["extra_fire7"] = {"skip_reason": None, "fire_block": L + SEAT_FIRE_AT + 1, "results": ex}
    return out


def main():
    d = pickle.load(open(CACHE, "rb"))
    G = measure_gas(d)
    recs = [price_launch(i, p, d, G) for i, p in enumerate(d["copies"])]
    bfs = [int(b["baseFeePerGas"], 16) for blks in d["blocks"].values() for b in blks]
    bf_med = st.median(bfs)
    meta = {"engine": "flip_engine 0.8, ENTRY=auto -> seat (per-launch launcher copy, code hash in SEAT_CODE_HASHES)", "stakes_eth": STAKES,
            "params": {"BUY_SLIP": BUY_SLIP, "TAKE_PROFIT": TAKE_PROFIT, "HOLD_BLOCKS": HOLD_BLOCKS, "SELL_LEAD_BLOCKS": SELL_LEAD_BLOCKS, "MIN_TRIGGER_ETH": 0.0002,
                       "SEAT_FIRE_AT": SEAT_FIRE_AT, "FEE_PPM": [FEE_MIN_PPM, FEE_MAX_PPM], "MIN_LIQUIDITY": MIN_LIQUIDITY, "ETH_USD": ETH_USD},
            "gas": {"buy_gas": G["buy_gas"], "sell_gas": G["sell_gas"], "sell_gas_pulled": G["sell_gas_pulled"], "n_buys": G["n_buys"], "n_sells": G["n_sells"],
                    "n_sells_pulled": G["n_sells_pulled"], "base_fee_median_gwei_in_scanned_blocks": bf_med / 1e9,
                    "round_trip_eth_at_median": (G["buy_gas"] + G["sell_gas"]) * bf_med / 1e18, "round_trip_usd_at_median": (G["buy_gas"] + G["sell_gas"]) * bf_med / 1e18 * ETH_USD,
                    "how": "median gasUsed of our real Oct 8 relay receipts x baseFeePerGas of the landing block (effectiveGasPrice == baseFee on all 18 relay receipts)"},
            "conventions": "see seat.py docstring"}
    pools_traded_live = {l["topics"][1] for l in d["relay_logs"]}
    for r in recs:
        if r["pid"] not in pools_traded_live:
            r["notes"].append("live: null - none of our 18 relay swaps (Oct 8 13:15 - Oct 9 00:11) is on this pool")
    ev = {}
    pj = os.path.join(HERE, "seat_rpc_lag_probe.json")
    if os.path.exists(pj):
        pr = [x for x in json.load(open(pj)) if x["blocks"] is not None]; c = collections.Counter(x["blocks"] for x in pr); n = len(pr)
        ev["arming_rpc_receipt_lag_probe"] = {"what": "LIVE probe on Oct 9 from this container (through its HTTPS proxy, not the box): feed message -> public RPC serves the receipt (arm_launch's wait_receipt, 40 ms polls)",
            "n": n, "ms_p10_p50_p90": [sorted(x["ms"] for x in pr)[int(q * (n - 1))] for q in (.1, .5, .9)], "feed_blocks_elapsed_hist": dict(sorted(c.items())),
            "share_fire_at_L6": sum(v for k, v in c.items() if k <= 5) / n, "share_fire_at_L7": c.get(6, 0) / n, "share_armed_too_late": sum(v for k, v in c.items() if k >= 7) / n,
            "box_release_0_5": "14 of 29 seat launches 'armed too late' (48%)",
            "not_measurable_from_chain": "when the RPC served the launch receipt on Oct 8 is in no log; the chain only shows block timestamps (1 s resolution)"}
    cj = os.path.join(HERE, "seat_crowd_slip.json")
    if os.path.exists(cj):
        cr = json.load(open(cj)); sl = [x["slack"] for x in cr if x["slack"] is not None]
        ev["crowd_slippage"] = {"n_crowd_buys": len(cr), "amountOutMinimum": "90% of the quote; the three burst buys quoted on the same pre-burst state",
                                "slack_got_over_min_min_median_max": [min(sl), st.median(sl), max(sl)],
                                "would_fail_with_our_buy_ahead": {s_: sum(1 for x in cr if x["fails_with_ours"][str(s_)]) for s_ in STAKES}}
    ev["burst"] = {"offsets": dict(sorted(collections.Counter(r["burst"]["block_offset"] for r in recs).items())),
                   "first_three_in_one_block": sum(1 for r in recs if r["burst"]["first_three_one_block"]),
                   "dust_tester_before_burst": sum(1 for r in recs if r["burst"]["dust_tester_before_burst"]),
                   "others_before_burst": [(r["block"], r["burst"]["others_before_burst_n"], r["burst"]["others_before_burst_eth"]) for r in recs if r["burst"]["others_before_burst_n"]],
                   "real_size_outside_buy_before_burst": sum(len(r["burst"]["real_size_before_burst"]) for r in recs),
                   "burst_eth_min_median_max": [min(r["burst"]["eth_in_burst_block"] for r in recs), st.median(r["burst"]["eth_in_burst_block"] for r in recs), max(r["burst"]["eth_in_burst_block"] for r in recs)]}
    ev["overnight_seat_trades_on_original_launcher"] = "our 0.0012 ETH seat buys at +7 (22:48, pool 0xfd84a22b) and +8 (Oct 9 00:11, pool 0xbe2a35f9), sold at +10/+11: that crowd still came at +51 / +46 (as usual for that launcher), the liquidity was removed at +105 / +278"
    meta["evidence"] = ev
    json.dump({"meta": meta, "launches": recs}, open(OUT, "w"), indent=1, default=str)
    # ---- summary
    print(f"gas: buy {G['buy_gas']}, sell {G['sell_gas']}, sell into pulled pool {G['sell_gas_pulled']} (n {G['n_buys']}/{G['n_sells']}/{G['n_sells_pulled']}); base fee median {bf_med/1e9:.4f} gwei; "
          f"round trip {(G['buy_gas'] + G['sell_gas']) * bf_med / 1e18:.3e} ETH = ${(G['buy_gas'] + G['sell_gas']) * bf_med / 1e18 * ETH_USD:.4f}")
    traded = [r for r in recs if r["results"]]
    print(f"{len(recs)} copy launches; traded {len(traded)}; skips: {dict(collections.Counter(r['skip_reason'] for r in recs if not r['results']))}")
    for s in STAKES:
        for k in LANDS:
            for spd in ("fast", "slow"):
                v = [r["results"][str(s)][f"land{k}_{spd}"] for r in traded]
                rets = [x["ret"] for x in v]
                print(f"  stake {s} land{k}_{spd}: n {len(v)} mean {st.mean(rets):+.4f} median {st.median(rets):+.4f} worst {min(rets):+.4f} wins {sum(1 for x in rets if x > 0)} "
                      f"total {sum(x['pnl_eth'] for x in v):+.6f} ETH exits {dict(collections.Counter(x['exit'] for x in v))}")
    for s in STAKES:
        ex = [r["extra_fire7"] for r in traded]
        ok = [e for e in ex if e.get("results")]
        for k in (8, 9):
            for spd in ("fast", "slow"):
                v = [e["results"][str(s)][f"land{k}_{spd}"] for e in ok]; rets = [x["ret"] for x in v]
                print(f"  (extra: fired at L+7) stake {s} land{k}_{spd}: n {len(v)} (late at +7: {len(ex) - len(ok)}) mean {st.mean(rets):+.4f} total {sum(x['pnl_eth'] for x in v):+.6f} ETH "
                      f"exits {dict(collections.Counter(x['exit'] for x in v))}")
    # the day for the seat alone, in time order, with the engine's daily cap (3) and stop ($15); the follow trades on the original
    # launcher's launches share the same cap and come earlier in the day (the orchestrator's job; printed here only as context)
    for s in STAKES:
        for key in ("land7_slow", "land8_slow"):
            pnl = 0.0; n = 0
            for r in sorted(traded, key=lambda r: r["block"]):
                if n >= 3 or pnl * ETH_USD <= -15: break
                x = r["results"][str(s)][key]; n += 1; pnl += x["pnl_eth"]
            print(f"  seat alone, cap 3/day, stake {s} {key}: first {n} trades {pnl:+.6f} ETH (${pnl * ETH_USD:+.2f})")

if __name__ == "__main__":
    main()
