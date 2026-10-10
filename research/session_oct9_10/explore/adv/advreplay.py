#!/usr/bin/env python3
"""Exact feed replay of the PM1444 v2.433 front-run rule (fire at launch + K, TP on the first feed buy that prices the sell >= TP after gas,
else send at our buy + H; sell lands send + 1 (fast) / + 2 (slow), priced at the head of its landing block).
Adapted from yday/follow.py and vbot/replay.py:
  * feed = every tx of blocks b0..b0+45 in block/index order; a BUY = value > 0, calldata >= 20 bytes, token address in calldata, to != token,
    launch tx skipped (flip_engine 0.8 on_buy); a SELL = Universal Router V4_SWAP SWAP_EXACT_IN_SINGLE on this pool's key, zeroForOne false
    (view 'sells'; view 'buys' = 0.8 as it is, sells invisible to the engine's copy);
  * the engine fires when the feed shows block F = b0 + K: expected = buy_out_int(engine copy through F), minOut = expected x 0.97 (BUY_SLIP);
  * our buy lands at B = F + land, AFTER every other swap of block B (chain state after B); tokens < minOut -> buy reverts (gas only);
  * from B+1 every logged swap is re-executed as an exact-input swap of its logged input after our buy (integer v4 math, one full range);
    the volume bot's router buys (to 0x1cbaf24d.., sel c1120e3d) carry minOut (calldata word 4): if the replayed output < minOut the buy
    REVERTS (no swap; the feed still shows it). Its FIRST buy's minOut is 0.99 x a quote taken at the launch state (adv/quote.py), so this
    check is exact for it; for its later buys (quoted fresh) mode 'strict' applies the logged minOut too, 'fresh' does not;
    a wallet that bought behind us sells the same fraction of what it got (vbot convention);
  * the engine adds our buy to its copy and, from B+1, prices our sell on every feed buy >= 0.0002 ETH; TP after base_fee x 250k gas;
  * pull (ModifyLiquidity < 0, not the launch tx) at or before F: no trade; at or before B: buy reverts; at or before the sell's landing: -100% - gas;
  * gas: 103,900 + 103,900 x the base fee of the buy's / sell's block (effectiveGasPrice = base fee on this chain).
-> adv/replay.json"""
import sys, os, json, pickle, collections, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__)); SCR = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad"
sys.path.insert(0, SCR); sys.path.insert(0, "/home/user/v2pons/src"); 
from chain import T_SWAP, T_ML, T_INIT, W, sgn, PM
import v4math
import importlib.util as _iu
_sp = _iu.spec_from_file_location("vbot_replay", os.path.join(SCR, "vbot", "replay.py")); _vb = _iu.module_from_spec(_sp); _sp.loader.exec_module(_vb)
ur_sells, buy_int, sell_int, net_of_fee, s128 = _vb.ur_sells, _vb.buy_int, _vb.sell_int, _vb.net_of_fee, _vb.s128      # vbot/replay.py (exact integer v4 math, UR sell decoder)
Q96 = 1 << 96
BUY_SLIP = 0.03; MIN_TRIGGER_WEI = int(0.0002e18); BUY_GAS = 103_900; SELL_GAS = 103_900; GAS_EST = 250_000
ROUTER = "1cbaf24d53fe930fce8eff149fa797d2611da149"; UR = "8876789976decbfcbbbe364623c63652db8c0904"; SEL_RBUY = "c1120e3d"


def prep(P):
    m = P["meta"]; b0 = m["b0"]; pid = m["pid"]; rec = P["rec"]
    init = [l for l in rec["logs"] if l["address"].lower() == PM and l["topics"] and l["topics"][0] == T_INIT and l["topics"][1] == pid]
    d = init[0]["data"]; fee = W(d, 0); ts = sgn(W(d, 1)); sp0 = W(d, 3); tick0 = sgn(W(d, 4)); token = init[0]["topics"][3][-40:]
    adds = [(sgn(W(l["data"], 0)), sgn(W(l["data"], 1)), sgn(W(l["data"], 2))) for l in rec["logs"] if l["address"].lower() == PM and l["topics"]
            and l["topics"][0] == T_ML and l["topics"][1] == pid]
    L0 = v4math.active_liquidity(tick0, adds)
    key = {"token": token, "token_bytes": bytes.fromhex(token), "fee": fee, "ts": ts}
    bt = {int(b["number"], 16): b for b in P["blocks"] if b}
    base_fee = {n: int(b["baseFeePerGas"], 16) for n, b in bt.items()}
    ls = sorted(P["logs"], key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
    swaps = []; mls = []
    for l in ls:
        bn = int(l["blockNumber"], 16); dd = l["data"]
        if l["topics"][0] == T_SWAP:
            swaps.append({"bn": bn, "li": int(l["logIndex"], 16), "a0": s128(W(dd, 0)), "a1": s128(W(dd, 1)), "sp": W(dd, 2), "L": W(dd, 3), "tx": l["transactionHash"]})
        else:
            mls.append({"bn": bn, "dl": sgn(W(dd, 2)), "tx": l["transactionHash"]})
    pulls = [x["bn"] for x in mls if x["dl"] < 0 and x["tx"] != m["tx"]]
    pull = min(pulls) if pulls else None
    # validation: logged swaps replayed from the launch state
    sp = sp0; worst = 0.0
    for s in swaps:
        if pull is not None and s["bn"] >= pull: break
        if s["a0"] < 0: sp, _ = buy_int(sp, s["L"], -s["a0"], fee)
        elif s["a1"] < 0: sp, _ = sell_int(sp, s["L"], -s["a1"], fee)
        worst = max(worst, abs(sp - s["sp"]) / s["sp"]); sp = s["sp"]
    txs = {}; feed = []
    for n in sorted(bt):
        for t in bt[n]["transactions"]:
            h = t["hash"]; to = (t.get("to") or "")[2:].lower(); data = bytes.fromhex(t["input"][2:]); v = int(t["value"], 16); frm = t["from"][2:].lower()
            txs[h] = {"bn": n, "idx": int(t["transactionIndex"], 16), "to": to, "from": frm, "value": v, "sel": data[:4].hex()}
            if h == m["tx"] or key["token_bytes"] not in data: continue
            ev = None
            if v > 0 and len(data) >= 20 and to != token:
                ev = {"kind": "buy", "amt": v}
                if to == ROUTER and data[:4].hex() == SEL_RBUY: ev["min_out"] = int.from_bytes(data[4 + 32 * 4: 4 + 32 * 5], "big"); ev["bot"] = True
            elif v == 0 and to == UR:
                s = ur_sells(data, key)
                if s: ev = {"kind": "sell", "amt": sum(s)}
            if ev is None: continue
            ev.update({"bn": n, "idx": txs[h]["idx"], "tx": h, "from": frm}); feed.append(ev)
    feedtx = {e["tx"]: e for e in feed}
    unseen = [(s["bn"] - b0, s["a0"]) for s in swaps if s["bn"] <= max(bt) and s["tx"] not in feedtx]
    bot_buys = [s for s in swaps if s["tx"] in feedtx and feedtx[s["tx"]].get("bot") and s["a0"] < 0]
    return {"pid": pid, "b0": b0, "fee": fee, "sp0": sp0, "L0": L0, "token": token, "base_fee": base_fee, "swaps": swaps, "pull": pull, "feed": feed, "feedtx": feedtx,
            "txs": txs, "last_bn": max(bt), "replay_err": worst, "unseen": unseen, "src": m["src"], "nonce": m["nonce"],
            "first_bot": (bot_buys[0]["bn"] - b0, -bot_buys[0]["a0"] / 1e18) if bot_buys else None}


def engine_after(Q, upto, view, extra=None):
    sp = float(Q["sp0"]); L = Q["L0"]; fee = Q["fee"]
    for e in Q["feed"]:
        if e["bn"] > upto: break
        if e["kind"] == "buy": sp = v4math.sqrt_after_buy(sp, L, net_of_fee(e["amt"], fee))
        elif view == "sells": sp = sp + net_of_fee(e["amt"], fee) * Q96 / L
    return sp


def chain_after(Q, bn):
    sp, L = Q["sp0"], Q["L0"]
    for s in Q["swaps"]:
        if s["bn"] > bn: break
        sp, L = s["sp"], s["L"]
    return sp, L


def bf(Q, n):
    if n in Q["base_fee"]: return Q["base_fee"][n]
    return Q["base_fee"][max(Q["base_fee"])]


def replay_with_us(Q, B, sp_us, L, last, mode, first_bot_tx):
    """swaps of blocks B+1..last re-executed after our buy; bot buys revert when their replayed output < their logged minOut"""
    fee = Q["fee"]; sp = sp_us; wallet = {}; reverted = []
    for s in Q["swaps"]:
        if s["bn"] <= B: continue
        if s["bn"] > last: break
        frm = Q["txs"].get(s["tx"], {}).get("from"); e = Q["feedtx"].get(s["tx"])
        if s["a0"] < 0:
            sp2, out = buy_int(sp, L, -s["a0"], fee)
            mo = e.get("min_out") if e else None
            check = mo is not None and (mode == "strict" or s["tx"] == first_bot_tx)
            if check and out < mo:
                reverted.append(s["bn"] - Q["b0"])
                if frm: wallet[frm] = (s["a1"], 0)
                continue
            sp = sp2
            if frm: wallet[frm] = (s["a1"], out)
        elif s["a1"] < 0:
            y = -s["a1"]
            if frm in wallet:
                lg, rp = wallet[frm]; y = y * rp // lg if lg > 0 else 0
            if y > 0: sp, _ = sell_int(sp, L, y, fee)
    return sp, reverted


def trade(Q, K, X, land=1, tp=0.05, H=19, lag=1, view="buys", mode="fresh"):
    b0 = Q["b0"]; fee = Q["fee"]; L0 = Q["L0"]; pull = Q["pull"]
    F = b0 + K; B = F + land
    if pull is not None and pull <= F: return {"exit": "no_trade_pulled", "ret": None}
    bfB = bf(Q, B)
    sp_e = engine_after(Q, F, view)
    expected = v4math.buy_out_int(int(sp_e), L0, X, fee); min_out = int(expected * (1 - BUY_SLIP))
    if pull is not None and pull <= B: return {"exit": "pull_before_buy", "ret": -(BUY_GAS + SELL_GAS) * bfB / X, "B": B - b0}
    spB, LB = chain_after(Q, B)
    sp_us, tokens = buy_int(spB, LB, X, fee)
    if tokens < min_out: return {"exit": "buy_reverted", "ret": -(BUY_GAS + SELL_GAS) * bfB / X, "B": B - b0, "slip": tokens / expected - 1}
    first_bot_tx = next((s["tx"] for s in Q["swaps"] if Q["feedtx"].get(s["tx"], {}).get("bot") and s["a0"] < 0), None)
    bot_already = first_bot_tx is not None and Q["feedtx"][first_bot_tx]["bn"] <= B
    sp_e = engine_after(Q, B, view)
    feed_tokens = v4math.buy_out_int(int(sp_e), L0, X, fee)
    sp_e = v4math.sqrt_after_buy(sp_e, L0, net_of_fee(X, fee))
    deadline = B + H; send = deadline; why = "deadline"; tpf = None
    for e in Q["feed"]:
        if e["bn"] <= B: continue
        if e["bn"] > deadline: break
        if e["kind"] == "buy": sp_e = v4math.sqrt_after_buy(sp_e, L0, net_of_fee(e["amt"], fee))
        elif view == "sells": sp_e = sp_e + net_of_fee(e["amt"], fee) * Q96 / L0
        if e["kind"] == "buy" and e["amt"] >= MIN_TRIGGER_WEI:
            r = (v4math.sell_out_int(int(sp_e), L0, feed_tokens, fee) - X - bf(Q, e["bn"]) * GAS_EST) / X
            if r >= tp: send = e["bn"]; why = "tp"; tpf = r; break
    S = send + lag
    gas = BUY_GAS * bfB + SELL_GAS * bf(Q, S)
    if pull is not None and pull <= S: return {"exit": "pulled", "ret": (-X - gas) / X, "B": B - b0, "send": send - b0, "S": S - b0}
    sp, rev = replay_with_us(Q, B, sp_us, LB, S - 1, mode, first_bot_tx)
    eth = sell_int(sp, LB, tokens, fee)[1]
    return {"exit": why, "ret": (eth - X - gas) / X, "B": B - b0, "send": send - b0, "S": S - b0, "tp_feed": tpf, "bot_reverts": rev, "bot_before_us": bot_already,
            "tokens_vs_expected": tokens / expected - 1}


def cheap(Q, K, X, tp=0.05, H=19):
    """the explore/sim.py convention on the same pool (float, logs only), for the pricer-agreement check"""
    b0 = Q["b0"]; fee = Q["fee"] / 1e6; F = b0 + K; B = F + 1; pull = Q["pull"]
    if pull is not None and pull <= F: return None
    sp, L = chain_after(Q, B); s0 = sp / Q96; xn = X * (1 - fee)
    tok = L * (s0 - 1 / (1 / s0 + xn / L)); tn = tok * (1 - fee); G = 4.2e12
    def ret(spc, Lc):
        so = 1 / (1 / (spc / Q96) + xn / Lc); s2 = so + tn / Lc; return (Lc * (1 / so - 1 / s2) - X - G) / X
    send = B + H
    for s in Q["swaps"]:
        if B < s["bn"] <= B + H and s["a0"] < 0 and ret(s["sp"], s["L"]) >= tp: send = s["bn"]; break
    if pull is not None and pull <= send + 1: return -1 - G / X
    a, b = chain_after(Q, send); return ret(a, b)


if __name__ == "__main__":
    D = pickle.load(open(os.path.join(HERE, "cache.pkl"), "rb"))
    Qs = sorted([prep(P) for P in D.values()], key=lambda q: q["b0"])
    out = {"pools": [], "variants": {}}
    print("pools", len(Qs))
    for Q in Qs:
        print(f"  {Q['src']:5s} {Q['pid'][:12]} b0 {Q['b0']} nonce {Q['nonce']:2d} replay_err {Q['replay_err']:.1e} unseen {Q['unseen'][:3]} first_bot {Q['first_bot']} pull {(Q['pull'] - Q['b0']) if Q['pull'] else None}")
        out["pools"].append({k: Q[k] for k in ("pid", "b0", "src", "nonce", "replay_err", "first_bot")} | {"pull": (Q["pull"] - Q["b0"]) if Q["pull"] else None})
    V = []
    for X_ in (0.0012, 0.006, 0.012, 0.013):
        for K in (0, 1, 2, 3, 4, 5, 6, 7, 8):
            for land in (1, 2):
                for lag in (1, 2):
                    V.append((X_, K, land, lag, "buys", "fresh"))
    V += [(0.0012, 2, 1, 1, "sells", "fresh"), (0.0012, 2, 1, 1, "buys", "strict"), (0.012, 2, 1, 1, "buys", "strict"), (0.012, 2, 1, 1, "sells", "fresh")]
    for (X_, K, land, lag, view, mode) in V:
        X = int(X_ * 1e18); rows = []
        for Q in Qs:
            r = trade(Q, K, X, land=land, lag=lag, view=view, mode=mode); r["pid"] = Q["pid"]
            if land == 1 and lag == 1 and view == "buys" and mode == "fresh": r["cheap"] = cheap(Q, K, X)
            rows.append(r)
        rs = [r["ret"] for r in rows if r["ret"] is not None]
        k = f"X{X_}|K{K}|land{land}|lag{lag}|{view}|{mode}"
        out["variants"][k] = {"n": len(rs), "mean": st.mean(rs), "median": st.median(rs), "min": min(rs), "pos": sum(1 for x in rs if x > 0) / len(rs),
                              "exits": dict(collections.Counter(r["exit"] for r in rows)), "bot_reverts": sum(1 for r in rows if r.get("bot_reverts")), "rows": rows}
        c = [(r["ret"], r["cheap"]) for r in rows if r.get("cheap") is not None and r["ret"] is not None]
        cs = f" cheap {st.mean([b for a, b in c]):+.4f} max|diff| {max(abs(a - b) for a, b in c):.4f}" if c else ""
        print(f"{k:42s} n {len(rs):2d} mean {st.mean(rs):+.4f} med {st.median(rs):+.4f} min {min(rs):+.4f} pos {out['variants'][k]['pos']:.2f} "
              f"exits {dict(collections.Counter(r['exit'] for r in rows))} botrev {out['variants'][k]['bot_reverts']}{cs}")
    for k in ("X0.0012|K2|land1|lag1|buys|fresh", "X0.012|K2|land1|lag1|buys|fresh"):
        print("per pool", k)
        for Q, r in zip(Qs, out["variants"][k]["rows"]):
            print(f"   {Q['src']:5s} {Q['pid'][:12]} bot {Q['first_bot']} pull {(Q['pull'] - Q['b0']) if Q['pull'] else None} -> exit {r['exit']} B +{r.get('B')} send +{r.get('send')} "
                  f"land +{r.get('S')} ret {100*r['ret']:+.2f}% cheap {100*(r.get('cheap') or 0):+.2f}% botrev {r.get('bot_reverts')} tokens_vs_exp {r.get('tokens_vs_expected', 0):+.5f}")
    json.dump(out, open(os.path.join(HERE, "replay.json"), "w"), indent=1, default=str)
