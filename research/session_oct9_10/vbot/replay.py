#!/usr/bin/env python3
"""Exact feed-replay pricing of a 'hold and sell into the volume bot's next buy' trade on PM1444 v3.0 pools (fee 1%, tick spacing 200,
3 ETH full-range position, a new deployer per pool, the bot's buys through router 0x1cbaf24d..., its sells through the Universal Router).

Data: vbot/cache.pkl (fetch.py): per pool the launch receipt, every block b0..b0+64 with all its transactions, the pool's Swap and
ModifyLiquidity logs over [b0, b0+1500].

THE ENGINE AS SIMULATED (flip_engine 0.8's matching, extended for this family):
  * feed = every transaction of every block in block order and index order (what the sequencer feed delivers);
  * a BUY is what 0.8's on_buy matches: value > 0, calldata >= 20 bytes, the token's address in the calldata, to != token; it moves
    the engine's copy of the price by tx.value net of the fee (apply_buy, float, as 0.8);
  * a SELL (new: 0.8 ignores value-0 transactions) is a Universal Router execute() whose V4_SWAP holds SWAP_EXACT_IN_SINGLE on this
    pool's key with zeroForOne = false; the engine moves its copy by amountIn net of the fee (sqrtP += x Q96 / L). view='buys' turns
    this off (0.8 as it is);
  * FIRE when the feed shows block F (F = b0 + K, or the first real buy's block + K'); expected = buy_out_int(engine copy through F),
    minOut = expected x (1 - BUY_SLIP 3%);
  * OUR BUY lands at B = F + 1 (fast) or F + 2 (slow), priced AFTER every other swap of block B (chain state after B); tokens < minOut ->
    the buy reverts (cost: buy gas + the presigned sell's gas, nothing else);
  * the engine adds our buy to its copy (our_buy_landed) and, from block B + 1 on, prices our sell on every real buy (value >= 0.0002
    ETH) the feed shows (take_profit: sell_out_int(engine copy) - stake - base_fee x 250k >= TP x stake); the first one that passes
    sends the sell in that block; otherwise the sell is sent when the feed shows b0 + D (or B, if B is later);
  * THE SELL lands at send + 1 (fast) or send + 2 (slow), priced at the HEAD of the landing block S (option: after every swap of S);
    a pull (ModifyLiquidity with liquidity < 0) at or before S = -100% - gas.
CHAIN REPLAY WITH US IN THE POOL: from the state after block B, our buy, then every logged swap of blocks B+1..S-1 re-applied as an
exact-input swap of its logged input (integer v4 math): a buy of |amount0| ETH, a sell of |amount1| tokens. Two reactions of the bot
to our buy are modelled:
  * the bot's router buys carry minOut (calldata word 4 = 0.95 x its quote); its quote is 3..14+ blocks stale (stale.py). A bot buy
    landing fewer than STALE blocks after our buy is assumed quoted WITHOUT our buy: if its replayed output < its minOut it reverts
    (no swap; the feed still shows it, so the engine's copy still counts it);
  * a wallet that bought after our buy (fewer tokens) sells the same fraction of its balance (its amountIn scaled; 0 if its buy
    reverted).
Gas: buy 103,900 + sell 103,900 gas x the base fee of the buy's and the sell's block (effectiveGasPrice = base fee on this chain).
IDEAL (upper bound): our sell right behind the first real buy behind ours (no latency, no deadline, to b0 + 60).
"""
import sys, os, json, pickle, collections, statistics as st, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, "/home/user/v2pons/src")
from chain import T_SWAP, T_ML, T_INIT, W, sgn, PM
import v4math
from eth_abi import decode as abi_decode

Q96 = 1 << 96
BUY_SLIP = 0.03; MIN_TRIGGER_WEI = int(0.0002e18); BUY_GAS = 103_900; SELL_GAS = 103_900; GAS_EST = 250_000
STAKES = (0.0012, 0.012, 0.03, 0.1)
KS = (12, 16, 20, 25); KAFTER = (4, 8, 12, 16)
TPS = (0.01, 0.02, 0.03); DS = (34, 38, 42)
ROUTER = "1cbaf24d53fe930fce8eff149fa797d2611da149"; UR = "8876789976decbfcbbbe364623c63652db8c0904"
SEL_RBUY = "c1120e3d"


def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x


def net_of_fee(x, fee):
    return x - (x * fee + 999_999) // 1_000_000


# ---------------------------------------------------------------- exact v4 integer math (one range; the PoolManager's rounding)
def buy_int(sp, L, x, fee):
    """x wei gross in; (new sqrtP, tokens out)"""
    xn = net_of_fee(x, fee)
    if xn <= 0: return sp, 0
    num = L * sp; den = L + (xn * sp) // Q96
    sp2 = (num + den - 1) // den
    return sp2, (L * (sp - sp2)) // Q96


def sell_int(sp, L, y, fee):
    """y tokens gross in; (new sqrtP, ETH out)"""
    yn = net_of_fee(y, fee)
    if yn <= 0: return sp, 0
    sp2 = sp + (yn * Q96) // L
    return sp2, (L * (sp2 - sp) * Q96) // (sp * sp2)


# ---------------------------------------------------------------- the feed decoder
def ur_sells(inp, key):
    """the exact-in single sells (zeroForOne=false) on pool `key` in a Universal Router execute() calldata: [amountIn]; None = not a UR
    swap we can read"""
    sel = inp[:4].hex()
    try:
        if sel == "3593564c":
            cmds, inputs, _ = abi_decode(["bytes", "bytes[]", "uint256"], inp[4:])
        elif sel == "24856bc3":
            cmds, inputs = abi_decode(["bytes", "bytes[]"], inp[4:])
        else:
            return None
    except Exception:
        return None
    out = []
    for c, data in zip(cmds, inputs):
        if (c & 0x3f) != 0x10:                       # V4_SWAP
            continue
        try:
            actions, params = abi_decode(["bytes", "bytes[]"], data)
        except Exception:
            return None
        for a, p in zip(actions, params):
            if a == 0x06:                            # SWAP_EXACT_IN_SINGLE
                try:
                    (pk, z, amt, mino, hd), = abi_decode(["((address,address,uint24,int24,address),bool,uint128,uint128,bytes)"], p)
                except Exception:
                    return None
                if pk[1].lower()[2:] == key["token"] and pk[0] == "0x" + "0" * 40 and pk[2] == key["fee"] and pk[3] == key["ts"] and not z:
                    out.append(amt)
            elif a in (0x07, 0x08, 0x09):            # multi-hop / exact-out: not modelled (flag)
                if key["token_bytes"] in p:
                    return None
    return out


def prep(P):
    """everything about one pool that does not depend on the variant"""
    m = P["meta"]; b0 = m["b0"]; pid = m["pid"]; rec = P["rec"]
    init = [l for l in rec["logs"] if l["address"].lower() == PM and l["topics"] and l["topics"][0] == T_INIT and l["topics"][1] == pid]
    if rec.get("status") != "0x1" or not init:
        return {"pid": pid, "b0": b0, "skip": "launch receipt has no pool"}
    d = init[0]["data"]
    fee = W(d, 0); ts = sgn(W(d, 1)); sp0 = W(d, 3); tick0 = sgn(W(d, 4)); token = init[0]["topics"][3][-40:]
    adds = [(sgn(W(l["data"], 0)), sgn(W(l["data"], 1)), sgn(W(l["data"], 2))) for l in rec["logs"] if l["address"].lower() == PM and l["topics"]
            and l["topics"][0] == T_ML and l["topics"][1] == pid]
    L0 = v4math.active_liquidity(tick0, adds)
    key = {"token": token, "token_bytes": bytes.fromhex(token), "fee": fee, "ts": ts}
    bt = {int(b["number"], 16): b for b in P["blocks"] if b}
    base_fee = {n: int(b["baseFeePerGas"], 16) for n, b in bt.items()}
    ts_of = {n: int(b["timestamp"], 16) for n, b in bt.items()}
    # chain: swaps and liquidity events
    ls = sorted(P["logs"], key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
    swaps = []; mls = []
    for l in ls:
        bn = int(l["blockNumber"], 16); dd = l["data"]
        if l["topics"][0] == T_SWAP:
            swaps.append({"bn": bn, "li": int(l["logIndex"], 16), "a0": s128(W(dd, 0)), "a1": s128(W(dd, 1)), "sp": W(dd, 2), "L": W(dd, 3), "tx": l["transactionHash"]})
        elif l["topics"][0] == T_ML:
            mls.append({"bn": bn, "dl": sgn(W(dd, 2)), "tx": l["transactionHash"]})
    pulls = [x["bn"] for x in mls if x["dl"] < 0 and x["tx"] != m["tx"]]
    pull = min(pulls) if pulls else None
    # validation: the logged swaps replayed exactly from the launch state
    sp = sp0; worst = 0.0; Ls = set()
    for s in swaps:
        if pull is not None and s["bn"] >= pull: break              # after the pull the range is gone: not our concern
        Ls.add(s["L"])
        if s["a0"] < 0: sp, _ = buy_int(sp, s["L"], -s["a0"], fee)
        elif s["a1"] < 0: sp, _ = sell_int(sp, s["L"], -s["a1"], fee)
        worst = max(worst, abs(sp - s["sp"]) / s["sp"]); sp = s["sp"]
    # the feed
    txs = {}
    feed = []; unknown_kinds = collections.Counter()
    for n in sorted(bt):
        for t in bt[n]["transactions"]:
            h = t["hash"]; to = (t.get("to") or "")[2:].lower(); data = bytes.fromhex(t["input"][2:]); v = int(t["value"], 16); frm = t["from"][2:].lower()
            idx = int(t["transactionIndex"], 16)
            txs[h] = {"bn": n, "idx": idx, "to": to, "from": frm, "value": v, "sel": data[:4].hex(), "len": len(data)}
            if h == m["tx"]:
                continue
            if key["token_bytes"] not in data:
                continue
            ev = None
            if v > 0 and len(data) >= 20 and to != token:
                ev = {"kind": "buy", "amt": v}
                if to == ROUTER and data[:4].hex() == SEL_RBUY:
                    ev["min_out"] = int.from_bytes(data[4 + 32*4: 4 + 32*5], "big")
            elif v == 0 and to == UR:
                s = ur_sells(data, key)
                if s:
                    ev = {"kind": "sell", "amt": sum(s)}
            if ev is None:
                unknown_kinds[(to[:8], data[:4].hex())] += 1
                continue
            ev.update({"bn": n, "idx": idx, "tx": h, "from": frm})
            feed.append(ev)
    # which logged swaps the feed saw (by tx), amounts compared
    by_tx = collections.defaultdict(list)
    for s in swaps: by_tx[s["tx"]].append(s)
    feed_tx = {e["tx"]: e for e in feed}
    last_bn = max(bt) if bt else b0
    unseen = [s for s in swaps if s["bn"] <= last_bn and s["tx"] not in feed_tx]
    mism = 0; feed_reverted = 0
    for e in feed:
        ss = by_tx.get(e["tx"])
        if not ss:
            feed_reverted += 1; e["reverted"] = True; continue
        s = ss[0]
        if e["kind"] == "buy" and -s["a0"] != e["amt"]: mism += 1
        if e["kind"] == "sell" and -s["a1"] != e["amt"]: mism += 1
    # buy sequence offsets (real buys)
    real_buys = [s for s in swaps if s["a0"] < 0 and -s["a0"] >= MIN_TRIGGER_WEI]
    sells = [s for s in swaps if s["a1"] < 0]
    first_feed_buy = next((e for e in feed if e["kind"] == "buy" and e["amt"] >= MIN_TRIGGER_WEI and not e.get("reverted")), None)
    return {"pid": pid, "b0": b0, "fee": fee, "ts": ts, "sp0": sp0, "L0": L0, "tick0": tick0, "ranges": adds, "token": token, "key": key,
            "base_fee": base_fee, "ts0": ts_of.get(b0), "swaps": swaps, "pull": pull, "feed": feed, "txs": txs, "last_bn": last_bn,
            "replay_err": worst, "single_L": len(Ls) <= 1 and (not Ls or Ls == {L0}), "unknown_kinds": dict(unknown_kinds),
            "unseen_swaps": [(s["bn"] - b0, s["a0"], s["a1"]) for s in unseen], "feed_amount_mismatch": mism, "feed_reverted": feed_reverted,
            "real_buy_offsets": [s["bn"] - b0 for s in real_buys[:8]], "sell_offsets": [s["bn"] - b0 for s in sells[:6]],
            "first_feed_buy": first_feed_buy["bn"] if first_feed_buy else None, "deployer": P["meta"].get("from"), "src": P["meta"].get("src")}


# ---------------------------------------------------------------- the engine's copy of the pool
def engine_after(Q, upto, view):
    """the engine's float sqrtP after every feed event with (bn, idx) <= upto (a block number: the whole block)"""
    sp = float(Q["sp0"]); L = Q["L0"]; fee = Q["fee"]
    for e in Q["feed"]:
        if e["bn"] > upto: break
        sp = apply_ev(sp, L, fee, e, view, e["amt"])
    return sp


def apply_ev(sp, L, fee, e, view, amt):
    if e["kind"] == "buy":
        return v4math.sqrt_after_buy(sp, L, net_of_fee(amt, fee))
    if view == "sells":
        return sp + net_of_fee(amt, fee) * Q96 / L
    return sp


# ---------------------------------------------------------------- one trade
def chain_state_after(Q, bn):
    """(sqrtP, L) after every logged swap through block bn"""
    sp, L = Q["sp0"], Q["L0"]
    for s in Q["swaps"]:
        if s["bn"] > bn: break
        sp, L = s["sp"], s["L"]
    return sp, L


def replay_with_us(Q, B, sp_us, L, upto_bn, stale, X, stop_on_first_real_buy=False, include_last_block=False):
    """the logged swaps of blocks B+1 .. upto_bn-1 (or .. upto_bn if include_last_block) re-applied after our buy; returns the state and
    the events (which bot buys reverted). stop_on_first_real_buy: stop right after the first real buy that went in (the ideal)."""
    fee = Q["fee"]; sp = sp_us; txs = Q["txs"]
    feedtx = {e["tx"]: e for e in Q["feed"]}
    wallet = {}                                   # from -> (logged tokens, replay tokens) for buys after ours
    reverted = []; first_real = None
    last = upto_bn if include_last_block else upto_bn - 1
    for s in Q["swaps"]:
        if s["bn"] <= B: continue
        if s["bn"] > last: break
        frm = txs.get(s["tx"], {}).get("from")
        if s["a0"] < 0:
            x = -s["a0"]
            sp2, out = buy_int(sp, L, x, fee)
            e = feedtx.get(s["tx"])
            mo = e.get("min_out") if e else None
            if mo is not None and (s["bn"] - B) < stale and out < mo:
                reverted.append(s["bn"] - Q["b0"])
                if frm: wallet[frm] = (s["a1"], 0)
                continue
            sp = sp2
            if frm: wallet[frm] = (s["a1"], out)
            if stop_on_first_real_buy and x >= MIN_TRIGGER_WEI:
                first_real = s["bn"]; break
        elif s["a1"] < 0:
            y = -s["a1"]
            if frm in wallet:
                lg, rp = wallet[frm]
                y = y * rp // lg if lg > 0 else 0
            if y > 0:
                sp, _ = sell_int(sp, L, y, fee)
    return sp, reverted, first_real


def trade(Q, entry, X, land, tp, D, sell_lag, view="sells", stale=15, sell_pos="head", Drel=None):
    """one variant on one pool; returns a dict (ret net of gas, exit kind, ...) or None when the entry has no fire block"""
    b0 = Q["b0"]; fee = Q["fee"]; L0 = Q["L0"]
    kind, K = entry
    if kind == "fixed":
        F = b0 + K
    else:
        if Q["first_feed_buy"] is None or Q["first_feed_buy"] - b0 > 60: return {"exit": "no_first_buy", "ret": None}
        F = Q["first_feed_buy"] + K
    B = F + land
    if B + 3 > Q["last_bn"]: return {"exit": "beyond_scan", "ret": None}
    bfB = Q["base_fee"].get(B, 20_000_000)
    # the engine fires: its copy through block F
    sp_e = engine_after(Q, F, view)
    expected = v4math.buy_out_int(int(sp_e), L0, X, fee); min_out = int(expected * (1 - BUY_SLIP))
    pull = Q["pull"]
    if pull is not None and pull <= B:
        return {"exit": "pull_before_buy", "ret": -(BUY_GAS + SELL_GAS) * bfB / X, "B": B - b0}
    spB, LB = chain_state_after(Q, B)
    sp_us, tokens = buy_int(spB, LB, X, fee)
    if tokens < min_out:
        return {"exit": "buy_reverted", "ret": -(BUY_GAS + SELL_GAS) * bfB / X, "B": B - b0, "slip": tokens / expected - 1}
    # the engine adds our buy and watches for a real buy behind ours
    sp_e = engine_after(Q, B, view)
    feed_tokens = v4math.buy_out_int(int(sp_e), L0, X, fee)
    sp_e = v4math.sqrt_after_buy(sp_e, L0, net_of_fee(X, fee))
    deadline = max(b0 + D, B) if Drel is None else B + Drel
    send = deadline; why = "deadline"; tp_feed = None
    for e in Q["feed"]:
        if e["bn"] <= B: continue
        if e["bn"] > deadline: break
        sp_e = apply_ev(sp_e, L0, fee, e, view, e["amt"])
        if e["kind"] == "buy" and e["amt"] >= MIN_TRIGGER_WEI:
            r = (v4math.sell_out_int(int(sp_e), L0, feed_tokens, fee) - X - Q["base_fee"].get(e["bn"], 20_000_000) * GAS_EST) / X
            if r >= tp:
                send = e["bn"]; why = "tp"; tp_feed = r; break
    S = send + sell_lag
    bfS = Q["base_fee"].get(S, 20_000_000); gas = BUY_GAS * bfB + SELL_GAS * bfS
    if pull is not None and pull <= S:
        return {"exit": "pulled", "ret": (-X - gas) / X, "B": B - b0, "send": send - b0}
    sp, reverted, _ = replay_with_us(Q, B, sp_us, LB, S, stale, X, include_last_block=(sell_pos == "tail"))
    eth = sell_int(sp, LB, tokens, fee)[1]
    nxt = next((s["bn"] for s in Q["swaps"] if s["bn"] > B and s["a0"] < 0 and -s["a0"] >= MIN_TRIGGER_WEI), None)
    return {"exit": why, "ret": (eth - X - gas) / X, "B": B - b0, "send": send - b0, "tp_feed": tp_feed, "bot_reverts": reverted,
            "tokens_vs_expected": tokens / expected - 1, "gap_next_real_buy": (nxt - B) if nxt else None}


def ideal(Q, entry, X, land, stale=15, horizon=60):
    """our sell right behind the first real buy behind ours (no latency, no deadline)"""
    b0 = Q["b0"]; fee = Q["fee"]; L0 = Q["L0"]
    kind, K = entry
    if kind == "fixed": F = b0 + K
    else:
        if Q["first_feed_buy"] is None or Q["first_feed_buy"] - b0 > 60: return {"exit": "no_first_buy", "ret": None}
        F = Q["first_feed_buy"] + K
    B = F + land
    if B + 3 > Q["last_bn"]: return {"exit": "beyond_scan", "ret": None}
    bfB = Q["base_fee"].get(B, 20_000_000)
    sp_e = engine_after(Q, F, "sells")
    expected = v4math.buy_out_int(int(sp_e), L0, X, fee); min_out = int(expected * (1 - BUY_SLIP))
    pull = Q["pull"]
    if pull is not None and pull <= B: return {"exit": "pull_before_buy", "ret": -(BUY_GAS + SELL_GAS) * bfB / X}
    spB, LB = chain_state_after(Q, B)
    sp_us, tokens = buy_int(spB, LB, X, fee)
    if tokens < min_out: return {"exit": "buy_reverted", "ret": -(BUY_GAS + SELL_GAS) * bfB / X}
    end = min(b0 + horizon, Q["last_bn"])
    sp, reverted, first_real = replay_with_us(Q, B, sp_us, LB, end, stale, X, stop_on_first_real_buy=True)
    S = first_real if first_real is not None else end
    if pull is not None and pull <= S: return {"exit": "pulled", "ret": -1.0}
    gas = BUY_GAS * bfB + SELL_GAS * Q["base_fee"].get(S, 20_000_000)
    eth = sell_int(sp, LB, tokens, fee)[1]
    return {"exit": "ideal" if first_real else "ideal_none", "ret": (eth - X - gas) / X, "sell_at": S - b0}


# ---------------------------------------------------------------- the census's cheap pricer, on the same pools (variants.py paper())
def cheap(Q, hold=30, tp=0.01, X=int(0.0012e18), gasw=int(4.2e12), arm=6):
    b0 = Q["b0"]; fee = Q["fee"]
    sw = [(s["bn"], s["li"], s["a0"], s["a1"], s["sp"], s["L"]) for s in Q["swaps"]]
    real = [x for x in sw if -x[2] >= MIN_TRIGGER_WEI and x[0] - b0 <= 150]
    a = [x for x in real if x[0] - b0 > arm]
    if not a: return None
    B = a[0][0] + 1
    prev = [x for x in sw if x[0] < B]
    sp, L = (prev[-1][4], prev[-1][5]) if prev else (Q["sp0"], Q["L0"])
    tok = v4math.buy_out_int(sp, L, X, fee)
    xn = X - (X * fee + 999_999) // 1_000_000
    def ret_at(spc, Lc):
        return (v4math.sell_out_int(int(Q96 / (Q96 / spc + xn / Lc)), Lc, tok, fee) - X - gasw) / X
    send = B + hold; why = "deadline"
    for x in sw:
        if B <= x[0] <= B + hold and x[2] < 0 and ret_at(x[4], x[5]) >= tp: send = x[0]; why = "tp"; break
    lb = send + 1
    if Q["pull"] is not None and Q["pull"] <= lb: return {"ret": -1.0 - gasw / X, "why": "pulled", "B": B - b0, "send": send - b0}
    pv = [x for x in sw if x[0] <= lb - 1]
    return {"ret": ret_at(pv[-1][4], pv[-1][5]) if pv else ret_at(sp, L), "why": why, "B": B - b0, "send": send - b0}


ENTRIES = [("fixed", k) for k in KS] + [("after", k) for k in KAFTER]


def ename(e): return f"K{e[1]}" if e[0] == "fixed" else f"T+{e[1]}"


def run(cache_path, out_path, pids=None):
    D = pickle.load(open(cache_path, "rb"))
    if pids is not None: D = {k: v for k, v in D.items() if k in pids}
    pools = []; res = {}
    t0 = time.time()
    for pid, P in sorted(D.items(), key=lambda kv: kv[1]["meta"]["b0"]):
        Q = prep(P)
        if Q.get("skip"):
            pools.append({"pid": pid, "b0": P["meta"]["b0"], "skip": Q["skip"]}); continue
        info = {k: Q[k] for k in ("pid", "b0", "ts0", "fee", "ts", "L0", "sp0", "pull", "replay_err", "single_L", "unknown_kinds", "unseen_swaps",
                                  "feed_amount_mismatch", "feed_reverted", "real_buy_offsets", "sell_offsets", "first_feed_buy", "deployer", "src")}
        info["first_feed_buy_off"] = Q["first_feed_buy"] - Q["b0"] if Q["first_feed_buy"] else None
        info["cheap_hold30"] = cheap(Q)
        info["cheap_hold30_stake"] = {str(x): cheap(Q, X=int(x * 1e18)) for x in STAKES}
        R = {}
        for e in ENTRIES:
            for X_ in STAKES:
                X = int(X_ * 1e18)
                for land in (1, 2):
                    R[f"{ename(e)}|{X_}|b{land}|ideal"] = ideal(Q, e, X, land)
                    for tp in TPS:
                        for Dd in DS:
                            for sl in (1, 2):
                                R[f"{ename(e)}|{X_}|b{land}|tp{tp}|D{Dd}|s{sl}"] = trade(Q, e, X, land, tp, Dd, sl)
        # side variants on a few: the 0.8 engine view (buys only), the bot never blind to us / blind only 4 blocks, sell after its landing block
        for e in ENTRIES:
            for X_ in STAKES:
                X = int(X_ * 1e18)
                for tp in TPS:
                    for Dd in DS:
                        R[f"{ename(e)}|{X_}|b1|tp{tp}|D{Dd}|s1|buysonly"] = trade(Q, e, X, 1, tp, Dd, 1, view="buys")
                        R[f"{ename(e)}|{X_}|b1|tp{tp}|D{Dd}|s1|stale4"] = trade(Q, e, X, 1, tp, Dd, 1, stale=4)
                        R[f"{ename(e)}|{X_}|b1|tp{tp}|D{Dd}|s1|stale0"] = trade(Q, e, X, 1, tp, Dd, 1, stale=0)
                        R[f"{ename(e)}|{X_}|b1|tp{tp}|D{Dd}|s1|tail"] = trade(Q, e, X, 1, tp, Dd, 1, sell_pos="tail")
        # the seat ahead of the bot's 2nd buy: fire g blocks after the first real buy, sell sent at our buy + Drel (or on TP), lands +1
        for g in (16, 18, 20, 22, 24):
            for X_ in (0.0012, 0.012):
                for land in (1, 2):
                    for Drel in (0, 1, 2):
                        R[f"T+{g}|{X_}|b{land}|tp0.01|R{Drel}|s1"] = trade(Q, ("after", g), int(X_ * 1e18), land, 0.01, 99, 1, Drel=Drel)
        info["R"] = R
        pools.append(info)
    print(f"priced {len(pools)} pools in {time.time() - t0:.0f}s", file=sys.stderr)
    pickle.dump(pools, open(out_path, "wb"))
    return pools


if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2])
