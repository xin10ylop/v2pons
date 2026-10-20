#!/usr/bin/env python3
"""Verifier's independent paper pricer for the FOLLOW entry (flip_engine 0.8, ENTRY=auto -> follow on the original launcher).
Reads only raw/<block>.json (vfetch.py) and relay_swaps.json (vgas.py); imports src/v4math.py and nothing of follow.py.

Engine semantics re-derived from src/flip_engine.py:
  feed: every signed tx of type 0/1/2 (parse_tx: anything else -> None, ignored), launch calls skipped (to == launcher or
        selector 2fcb9108), value == 0 or calldata < 20 bytes skipped, token's 20 bytes anywhere in calldata and to != token
        -> on_buy: apply_buy(value) (1/sqrtP += net_of_fee(value)/L_receipt), and if value >= 0.0002 ETH: first one = trigger.
  fire: in the trigger tx (expected/minOut from the feed copy through the trigger tx). TRIGGER_MAX_BLOCKS: offset > 150 -> skip.
  our buy lands in B = T + k, priced after every other swap of B; tokens < minOut -> revert.
  feed_tokens = buy_out_int(feed copy at our buy), then apply_buy(stake).
  take_profit: on each feed tx with value >= 0.0002 behind ours (B+1, B+2 here) after apply_buy: sell_out_int(feed sp, L, feed_tokens)
        - stake - base_fee*250000 >= 0.01 * stake -> send in that block; else deadline at B+2 (end of block).
  sell lands send+1 / send+2, priced at the head of S: chain after S-1 + our buy (exact replay: our buy added to 1/sqrtP after B,
        later buys add to 1/sqrtP, later sells add to sqrtP).  pull block <= S -> -100% - gas.
"""
import sys, os, json, glob, time, statistics as st
sys.path.insert(0, "/home/user/v2pons/src")
import v4math
HERE = os.path.dirname(os.path.abspath(__file__))
Q96 = 1 << 96
PM = "0x8366a39cc670b4001a1121b8f6a443a643e40951"
from eth_utils import keccak
T_INIT = "0x" + keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
T_SWAP = "0x" + keccak(text="Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)").hex()
T_ML = "0x" + keccak(text="ModifyLiquidity(bytes32,address,int24,int24,int256,bytes32)").hex()
OP = "0x3194e32622c5d860a0572c74edda99dcfd8fc827"; SEL_LAUNCH = "0x2fcb9108"
RELAY = "0x2abb5653352f6b2f3b4f4261877cd02d9e05a957"; WALLET = "0xab5a34c3f41e57fdee1a1d6f19d3e21f46df3ea8"
MIN_TRIG = 200_000_000_000_000; SLIP = 0.03; TP = 0.01; HOLD = 4; LEAD = 2; TMAX = 150
STAKES = (0.0012, 0.004, 0.012)


def word(d, i): return int(d[2 + 64 * i: 2 + 64 * (i + 1)], 16)
def sg(x, bits=256): return x - (1 << bits) if x >= (1 << (bits - 1)) else x
def nof(x, fee): return x - (x * fee + 999_999) // 1_000_000


GASREC = json.load(open(os.path.join(HERE, "relay_swaps.json")))
oct8 = [g for g in GASREC if g["block"] <= 83719338]
BUY_GAS = int(st.median([g["gasUsed"] for g in oct8 if g["a0"] < 0]))
SELL_GAS = int(st.median([g["gasUsed"] for g in oct8 if g["a0"] > 0]))
SELL_GAS_PULLED = int(st.median([g["gasUsed"] for g in oct8 if g["a0"] == 0]))


def price(path, arm_lag=6):
    R = json.load(open(path)); p = R["p"]; b0 = p["block"]; rec = R["rec"]; pid = p["pid"]
    blocks = {b["n"]: b for b in R["blocks"]}
    out = {"block": b0, "time_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(blocks[b0]["ts"])), "pid": pid, "kind": p["kind"], "fee_ppm": p["fee"],
           "entry": "follow", "eligible": None, "skip_reason": None, "fire_block": None, "trigger_offset": None, "trigger_value_eth": None,
           "pull_block": None, "results": None, "live": None, "close_block": None, "v": {}}
    # pool from the receipt (engine: pool_from_receipt)
    init = next(l for l in rec["logs"] if l["address"].lower() == PM and l["topics"][0] == T_INIT and l["topics"][1] == pid)
    d = init["data"]; c0 = init["topics"][2][-40:]; token = init["topics"][3][-40:]; fee = word(d, 0); hooks = d[2 + 64 * 2 + 24: 2 + 64 * 3]
    sp0 = word(d, 3); tick0 = sg(word(d, 4))
    adds = [(sg(word(l["data"], 0)), sg(word(l["data"], 1)), sg(word(l["data"], 2))) for l in rec["logs"]
            if l["address"].lower() == PM and l["topics"][0] == T_ML and l["topics"][1] == pid]
    liq = v4math.active_liquidity(tick0, adds)
    gates = {"eth": c0 == "0" * 40, "nohook": hooks == "0" * 40, "fee": 0 <= fee <= 9999, "liq": liq >= 1e21}
    out["eligible"] = all(gates.values()); out["v"]["gates"] = gates; out["v"]["liq"] = liq
    tb = bytes.fromhex(token)
    # chain events
    ev = sorted(R["near"], key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
    swaps = []; ours = []; mls = []
    for l in ev:
        bn = int(l["blockNumber"], 16); li = int(l["logIndex"], 16); dd = l["data"]
        if l["topics"][0] == T_SWAP:
            x = {"bn": bn, "li": li, "a0": sg(word(dd, 0) & ((1 << 128) - 1), 128), "a1": sg(word(dd, 1) & ((1 << 128) - 1), 128),
                 "sp": word(dd, 2), "L": word(dd, 3), "tick": sg(word(dd, 4)), "fee": word(dd, 5), "tx": l["transactionHash"], "sender": "0x" + l["topics"][2][-40:]}
            (ours if x["sender"] == RELAY else swaps).append(x)
        else:
            mls.append({"bn": bn, "li": li, "dl": sg(word(dd, 2)), "tx": l["transactionHash"]})
    rem = sorted((int(l["blockNumber"], 16), int(l["logIndex"], 16)) for l in R["ml"] if sg(word(l["data"], 2)) < 0)
    pull = rem[0][0] if rem else None
    out["pull_block"] = pull
    # wallet txs on the pool (trade 8: a router buy from our wallet)
    wallet_txs = {t["h"] for b in R["blocks"] for t in b["txs"] if t["from"] == WALLET}
    swaps_nw = [x for x in swaps if x["tx"] not in wallet_txs]
    out["v"]["our_swaps_excluded"] = len(ours) + (len(swaps) - len(swaps_nw)); swaps = swaps_nw
    # feed replay
    feed = []; skipped_types = []
    for k in sorted(blocks):
        for t in sorted(blocks[k]["txs"], key=lambda t: t["i"]):
            if t["from"] == WALLET:
                continue
            if t["to"] == OP or t["sel"] == SEL_LAUNCH:
                continue
            if t["value"] == 0 or t["len"] < 20 or t["input"] is None:
                continue
            if tb not in bytes.fromhex(t["input"][2:]) or t["to"][2:] == token:
                continue
            if t["type"] not in ("0x0", "0x1", "0x2"):
                skipped_types.append((k, t["type"], t["value"])); continue
            feed.append({"bn": k, "i": t["i"], "value": t["value"], "h": t["h"], "type": t["type"]})
    out["v"]["feed_skipped_types"] = skipped_types
    trig = next((f for f in feed if f["value"] >= MIN_TRIG), None)
    first_swap = next((x for x in swaps if x["a0"] <= -MIN_TRIG), None)
    out["v"]["first_real_swap_off"] = first_swap["bn"] - b0 if first_swap else None
    if trig is None:
        out["skip_reason"] = f"no feed tx >= 0.0002 ETH carrying the token in +0..+{max(blocks) - b0}"; return out
    T = trig["bn"]; off = T - b0
    out.update({"trigger_offset": off, "trigger_value_eth": trig["value"] / 1e18})
    out["v"]["trigger_tx"] = trig["h"]; out["v"]["trigger_type"] = trig["type"]
    if off > TMAX:
        out["skip_reason"] = f"late first buy +{off} > {TMAX}"; return out
    if off <= arm_lag:
        out["skip_reason"] = f"late: trigger +{off} <= arm lag"; return out
    if not out["eligible"]:
        out["skip_reason"] = "not eligible: " + ",".join(k for k, v in gates.items() if not v); return out
    out["fire_block"] = T

    def feed_sp(upto):                 # feed copy after every feed tx with (bn, i) <= upto
        s = float(sp0)
        for f in feed:
            if (f["bn"], f["i"]) > upto: break
            s = v4math.sqrt_after_buy(s, liq, nof(f["value"], fee))
        return s

    def chain_after(bn):
        s, L = sp0, liq
        for x in swaps:
            if x["bn"] > bn: break
            s, L = x["sp"], x["L"]
        return s, L
    sp_trig = feed_sp((T, trig["i"]))
    sp_blk_feed = feed_sp((T, 10 ** 9))
    swaps_in_T_after_trig = [x for x in swaps if x["bn"] == T and x["tx"] != trig["h"]]
    out["v"]["trigger_last_in_block_feed"] = abs(sp_trig - sp_blk_feed) < 1
    out["v"]["window_fees"] = sorted({x["fee"] for x in swaps if T <= x["bn"] <= T + 8})
    out["v"]["ml_in_window"] = [m for m in mls if b0 < m["bn"] <= T + 8 and m["tx"] != p["tx"]]
    results = {}; maxS = 0
    for stake in STAKES:
        X = int(round(stake * 1e18)); xn = nof(X, fee)
        expected = v4math.buy_out_int(int(sp_trig), liq, X, fee); minout = int(expected * (1 - SLIP))
        spT, LT = chain_after(T); exp_chainT = v4math.buy_out_int(spT, LT, X, fee)
        RR = {}
        for k in (1, 2):
            B = T + k
            spB, LB = chain_after(B)
            tokens = v4math.buy_out_int(spB, LB, X, fee)
            fs = feed_sp((B, 10 ** 9)); ftok = v4math.buy_out_int(int(fs), liq, X, fee); fs = v4math.sqrt_after_buy(fs, liq, xn)
            send = None; why = "deadline"; tpr = None
            for f in feed:
                if f["bn"] <= B: continue
                if f["bn"] > B + HOLD - LEAD: break
                fs = v4math.sqrt_after_buy(fs, liq, nof(f["value"], fee))
                if f["value"] < MIN_TRIG: continue
                bf = blocks[f["bn"] - 1]["bf"]                  # the engine's base_fee: the latest block it read (<=10 s old)
                r = (v4math.sell_out_int(int(fs), liq, ftok, fee) - X - bf * 250_000) / X
                if r >= TP:
                    send = f["bn"]; why = "take_profit"; tpr = r; break
            if send is None: send = B + HOLD - LEAD
            for sp_name, dl in (("fast", 1), ("slow", 2)):
                S = send + dl; maxS = max(maxS, S)
                gb = BUY_GAS * blocks[B]["bf"]; gs = SELL_GAS * blocks[S]["bf"]
                r = {"buy_block": B, "sell_send_block": send, "sell_land_block": S, "pull_after_buy": (pull - B) if pull is not None else None, "why": why,
                     "tp_ret": tpr, "tokens": tokens, "min_out": minout, "fill_over_minout": tokens / minout, "revert_if_chainT_minout": tokens < int(exp_chainT * (1 - SLIP))}
                if pull is not None and pull <= B:
                    r.update(exit="pull_at_or_before_buy", ret=-(gb + gs) / X, pnl_eth=-(gb + gs) / 1e18)
                elif tokens < minout:
                    r.update(exit="buy_reverted", ret=-(gb + gs) / X, pnl_eth=-(gb + gs) / 1e18)
                elif pull is not None and pull <= S:
                    g = gb + SELL_GAS_PULLED * blocks[S]["bf"]
                    r.update(exit="pull_first", ret=(-X - g) / X, pnl_eth=(-X - g) / 1e18)
                else:
                    # exact replay from the end of B
                    s = Q96 / (Q96 / spB + xn / LB); prev = spB; Lc = LB; crossed = False
                    for x in swaps:
                        if x["bn"] <= B: continue
                        if x["bn"] >= S: break
                        if x["L"] != LB: crossed = True
                        if x["a0"] < 0: s = Q96 / (Q96 / s + (Q96 / x["sp"] - Q96 / prev))
                        else: s = s + (x["sp"] - prev)
                        prev = x["sp"]
                    if any(B < m["bn"] < S for m in mls): crossed = True
                    eth = v4math.sell_out_int(int(s), LB, tokens, fee)
                    # additive variant (chain after S-1 + our buy)
                    spc, Lc = chain_after(S - 1); eth_add = v4math.sell_out_int(int(Q96 / (Q96 / spc + xn / Lc)), Lc, tokens, fee)
                    g = gb + gs
                    r.update(exit=why, ret=(eth - X - g) / X, ret_additive=(eth_add - X - g) / X, pnl_eth=(eth - X - g) / 1e18, crossed=crossed, eth_out=eth, gas_eth=g / 1e18)
                RR[f"land{k}_{sp_name}"] = r
        results[str(stake)] = RR
    out["results"] = results; out["close_block"] = maxS + 30
    return out


if __name__ == "__main__":
    files = sorted(glob.glob(os.path.join(HERE, "raw", "*.json")))
    want = set(sys.argv[1:])
    res = []
    for f in files:
        if want and os.path.basename(f)[:-5] not in want: continue
        res.append(price(f))
    json.dump(res, open(os.path.join(HERE, "vprice_out.json"), "w"), indent=1, default=str)
    print(f"gas: buy {BUY_GAS} sell {SELL_GAS} pulled {SELL_GAS_PULLED}")
    for o in res:
        line = f"{o['time_utc'][11:]} {o['block']} fee {o['fee_ppm']} trig +{o['trigger_offset']} pull {None if o['pull_block'] is None else o['pull_block'] - o['block']}"
        if o["results"]:
            line += " | " + " ".join(f"{k}:{v['ret']:+.4f}{v['exit'][0]}" for k, v in o["results"]["0.0012"].items())
            line += f" | trigtype {o['v']['trigger_type']} last {o['v']['trigger_last_in_block_feed']} fees {o['v']['window_fees']} skippedtypes {len(o['v']['feed_skipped_types'])}"
        else:
            line += " | " + o["skip_reason"]
        print(line)
