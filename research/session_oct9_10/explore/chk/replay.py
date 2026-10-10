#!/usr/bin/env python3
"""Exact feed replay of the v2.433 rule (launch+2, TP 5%, H 19) on replay_data.pkl, adapted from yday/follow.py.

Engine model (flip_engine 0.8 logic, with a launch recogniser for this family):
  - the launch is the PositionManager multicall (to 0x58daec31, sel ac9650d8, 1444 bytes, value 2.4333285 ETH) seen in the feed at b0;
    the pool (sqrtP, L) from its receipt; arming "calldata" = the pool known at b0 (decoded from the call), "receipt" = armed ARM blocks later
  - the engine's copy of the price: launch state, then every feed tx with value > 0, >= 20 bytes of calldata carrying the token (to != token),
    in block/tx order (apply_buy by tx.value); minOut = buy_out_int(copy at the fire block) x (1 - BUY_SLIP 3%)
  - fire at F; our buy lands at F+1 (fast) or F+2 (slow), AFTER every other tx of its block (conservative); tokens from the chain state
    after that block; a fill under minOut = buy reverted (gas of both txs lost)
  - take-profit: on each feed buy >= 0.0002 ETH in a later block, the engine's copy prices the sell; >= TP after gas (base fee x 250k) =
    send in that block; else send at B + H; the sell lands at send+1 (fast) or send+2 (slow), priced at the head of that block
  - chain at the sell: our buy inserted after block B, every later swap replayed by its own shift (exact-in: buys add to 1/sqrtP, sells to
    sqrtP); a volume-bot buy (c1120e3d) whose output with our buy in front falls under its own minOut (calldata word 4) is dropped (reverts)
  - a pull (negative ModifyLiquidity) at or before F: no trade; after F and at or before the sell's landing block: -100% - gas
  - gas: 103,861 (buy) + 103,894 (sell; 135,200 into a pulled pool) x baseFeePerGas of the landing blocks (yday/follow.json meta.gas)
"""
import sys, os, pickle, json, collections, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__)); EX = os.path.dirname(HERE); SCR = os.path.dirname(EX)
sys.path.insert(0, SCR); sys.path.insert(0, "/home/user/v2pons/src"); sys.path.insert(0, EX)
from chain import T_INIT, T_SWAP, T_ML, W, sgn, PM
import v4math
Q96 = 1 << 96
POSM = "58daec3116aae6d93017baaea7749052e8a04fa7"; ROUTER = "1cbaf24d53fe930fce8eff149fa797d2611da149"
BUY_SLIP = 0.03; MIN_TRIG = int(0.0002e18); TP = 0.05; H = 19
BUY_GAS, SELL_GAS, SELL_GAS_PULLED = 103861, 103894, 135200
STAKES = (0.0012, 0.012)


def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x


def net(x, fee): return x - (x * fee + 999_999) // 1_000_000


def wd(inp, i): return int(inp[10 + 64 * i: 10 + 64 * (i + 1)], 16)


def prep(R):
    m = R["meta"]; pid = m["pid"]; b0 = m["b0"]; rec = R["rec"]
    init = [l for l in rec["logs"] if l["topics"] and l["topics"][0] == T_INIT and l["topics"][1] == pid][0]
    fee = W(init["data"], 0); sp0 = W(init["data"], 3); tick0 = sgn(W(init["data"], 4))
    adds = [(sgn(W(l["data"], 0)), sgn(W(l["data"], 1)), sgn(W(l["data"], 2))) for l in rec["logs"] if l["topics"] and l["topics"][0] == T_ML and l["topics"][1] == pid]
    liq = v4math.active_liquidity(tick0, adds)
    token = init["topics"][3][-40:]; tb = bytes.fromhex(token)
    bt = {int(b["number"], 16): b for b in R["blocks"] if b}
    txs = {}
    for b in R["blocks"]:
        if not b: continue
        for t in b["transactions"]: txs[t["hash"]] = t
    sw, mls = [], []
    for l in sorted(R["logs"], key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16))):
        bn = int(l["blockNumber"], 16); d = l["data"]
        if l["topics"][0] == T_SWAP:
            t = txs.get(l["transactionHash"])
            sw.append({"bn": bn, "li": int(l["logIndex"], 16), "a0": s128(W(d, 0)), "a1": s128(W(d, 1)), "sp": W(d, 2), "L": W(d, 3), "tx": l["transactionHash"],
                       "to": (t["to"] or "")[2:].lower() if t else None, "input": t["input"] if t else None, "from": t["from"][2:].lower() if t else None})
        else:
            mls.append({"bn": bn, "dl": sgn(W(d, 2)), "tx": l["transactionHash"]})
    pulls = [x for x in mls if x["dl"] < 0]
    feed = []
    for k in sorted(bt):
        if k == b0: pass
        for t in bt[k]["transactions"]:
            to = (t.get("to") or "")[2:].lower(); data = bytes.fromhex(t["input"][2:]); v = int(t["value"], 16)
            if to == POSM and data[:4].hex() == "ac9650d8" and len(data) == 1444: continue      # a launch call (the recogniser), skipped as in ingest()
            if v == 0 or len(data) < 20: continue
            if tb in data and to != token:
                feed.append({"bn": k, "idx": int(t["transactionIndex"], 16), "value": v, "hash": t["hash"], "to": to, "from": t["from"][2:].lower()})
    return {"pid": pid, "b0": b0, "fee": fee, "sp0": sp0, "liq": liq, "token": token, "bt": bt, "sw": sw, "pull": pulls[0]["bn"] if pulls else None, "feed": feed,
            "logspan_end": R["logspan_end"], "src": R["src"], "txindex": int(rec["transactionIndex"], 16)}


def trade(p, F, land, sell_lag, stake):
    b0 = p["b0"]; fee = p["fee"]; liq = p["liq"]; X = int(round(stake * 1e18)); xn = net(X, fee)
    bf = lambda n: int(p["bt"][n]["baseFeePerGas"], 16) if n in p["bt"] else 20_152_000
    pull = p["pull"]
    if pull is not None and pull <= F: return {"exit": "pulled_before_fire", "ret": None}
    # engine's copy through the fire block
    sp_f = float(p["sp0"])
    for f in p["feed"]:
        if f["bn"] > F: break
        sp_f = v4math.sqrt_after_buy(sp_f, liq, net(f["value"], fee))
    expected = v4math.buy_out_int(int(sp_f), liq, X, fee); min_out = int(expected * (1 - BUY_SLIP))
    B = F + land
    prevB = [x for x in p["sw"] if x["bn"] <= B]
    spB, LB = (prevB[-1]["sp"], prevB[-1]["L"]) if prevB else (p["sp0"], liq)
    if pull is not None and pull <= B:
        return {"exit": "pull_before_buy_landed", "ret": -(BUY_GAS + SELL_GAS) * bf(B) / X, "B": B - b0}
    tokens = v4math.buy_out_int(spB, LB, X, fee)
    if tokens < min_out:
        return {"exit": "buy_reverted", "ret": -(BUY_GAS * bf(B) + SELL_GAS * bf(B + 2)) / X, "B": B - b0}
    # engine: our buy seen at B; feed tokens; TP on later feed buys
    sp_e = float(p["sp0"])
    for f in p["feed"]:
        if f["bn"] > B: break
        sp_e = v4math.sqrt_after_buy(sp_e, liq, net(f["value"], fee))
    feed_tokens = v4math.buy_out_int(int(sp_e), liq, X, fee)
    sp_e = v4math.sqrt_after_buy(sp_e, liq, xn)
    send = None; why = "deadline"; tp_seen = None
    for f in p["feed"]:
        if f["bn"] <= B: continue
        if f["bn"] > B + H: break
        sp_e = v4math.sqrt_after_buy(sp_e, liq, net(f["value"], fee))
        if f["value"] < MIN_TRIG: continue
        eth = v4math.sell_out_int(int(sp_e), liq, feed_tokens, fee)
        r = (eth - X - bf(f["bn"]) * 250_000) / X
        if r >= TP: send = f["bn"]; why = "tp"; tp_seen = round(r, 4); break
    if send is None: send = B + H
    S = send + sell_lag
    if pull is not None and pull <= S:
        return {"exit": "pull_first", "ret": (-X - BUY_GAS * bf(B) - SELL_GAS_PULLED * bf(S)) / X, "B": B - b0, "send": send - b0, "S": S - b0, "pull": pull - b0}
    if S > p["logspan_end"]: return {"exit": "no_data", "ret": None}
    # chain at the head of S: our buy after block B, the later swaps replayed by their own shift; bot buys under their minOut dropped
    s = Q96 / (Q96 / spB + xn / LB); prev = spB; L = LB; dropped = []
    for x in p["sw"]:
        if x["bn"] <= B: continue
        if x["bn"] >= S: break
        if x["L"] != L: L = x["L"]
        if x["a0"] < 0:
            d_inv = Q96 / x["sp"] - Q96 / prev
            if x["to"] == ROUTER and x["input"] and x["input"][:10] == "0xc1120e3d":
                mo = wd(x["input"], 4); X2 = -x["a0"]
                out_with_us = v4math.buy_out_int(int(s), L, X2, fee)
                if out_with_us < mo:
                    dropped.append((x["bn"] - b0, out_with_us / mo)); prev = x["sp"]; continue
            s = Q96 / (Q96 / s + d_inv)
        else:
            s = s + (x["sp"] - prev)
        prev = x["sp"]
    eth_out = v4math.sell_out_int(int(s), L, tokens, fee)
    gas = BUY_GAS * bf(B) + SELL_GAS * bf(S)
    # the bot's first buy: its output with us in front over its minOut (headroom)
    fb = next((x for x in p["sw"] if x["a0"] < 0 and x["to"] == ROUTER and x["input"] and x["input"][:10] == "0xc1120e3d"), None)
    hr = None
    if fb and fb["bn"] > B:
        pre = [x for x in p["sw"] if (x["bn"], x["li"]) < (fb["bn"], fb["li"])]
        sp_pre = pre[-1]["sp"] if pre else p["sp0"]
        sp_pre_us = int(Q96 / (Q96 / sp_pre + xn / LB))
        hr = v4math.buy_out_int(sp_pre_us, LB, -fb["a0"], fee) / wd(fb["input"], 4)
    return {"exit": why, "ret": (eth_out - X - gas) / X, "ret_gross": (eth_out - X) / X, "B": B - b0, "send": send - b0, "S": S - b0, "tp_feed": tp_seen,
            "tokens_vs_minout": tokens / min_out, "bot_dropped": dropped, "bot_first_buy_headroom": hr, "first_bot_buy": (fb["bn"] - b0) if fb else None}


def main():
    D = pickle.load(open(os.path.join(HERE, "replay_data.pkl"), "rb"))
    pools = [prep(R) for R in D["pools"].values()]
    pools.sort(key=lambda p: p["b0"])
    scen = {"calldata F=b0+2": [(2, l, s) for l in (1, 2) for s in (1, 2)], "calldata F=b0+1": [(1, l, s) for l in (1, 2) for s in (1, 2)],
            "receipt F=b0+6": [(6, l, s) for l in (1, 2) for s in (1, 2)], "receipt F=b0+11": [(11, l, s) for l in (1, 2) for s in (1, 2)]}
    out = {"pools": [], "summary": {}}

    for p in pools:
        row = {"pid": p["pid"], "src": p["src"], "b0": p["b0"], "pull": (p["pull"] - p["b0"]) if p["pull"] else None, "feed_first": [(f["bn"] - p["b0"], round(f["value"] / 1e18, 6), f["to"][:8]) for f in p["feed"][:6]],
               "res": {}}
        for sc, combos in scen.items():
            for (K, land, sl) in combos:
                for stake in STAKES:
                    row["res"][f"{sc}|land+{land}|sell+{sl}|{stake}"] = trade(p, p["b0"] + K, land, sl, stake)
        out["pools"].append(row)
    # summary
    keys = list(out["pools"][0]["res"].keys())
    print(f"{len(pools)} pools: " + str(collections.Counter(p['src'] for p in pools)))
    for k in keys:
        rs = [r["res"][k] for r in out["pools"]]
        tr = [x for x in rs if x["ret"] is not None]
        ex = collections.Counter(x["exit"] for x in rs)
        v = [x["ret"] for x in tr]
        out["summary"][k] = {"n": len(v), "mean": st.mean(v) if v else None, "median": st.median(v) if v else None, "min": min(v) if v else None, "pos": sum(1 for a in v if a > 0), "exits": dict(ex)}
        print(f"{k:42s} n {len(v):2d} mean {100*st.mean(v):+7.2f}% median {100*st.median(v):+7.2f}% min {100*min(v):+8.2f}% pos {sum(1 for a in v if a > 0):2d} exits {dict(ex)}")
    print("\nper pool, calldata F=b0+2, land+1, sell+1:")
    for r in out["pools"]:
        a = r["res"]["calldata F=b0+2|land+1|sell+1|0.0012"]; b = r["res"]["calldata F=b0+2|land+1|sell+1|0.012"]
        print(f"  {r['src']:7s} {r['pid'][:10]} b0 {r['b0']} pull {r['pull']} | 0.0012 {a['exit']:10s} {100*(a['ret'] or 0):+7.2f}% send {a.get('send')} S {a.get('S')} 1stbot {a.get('first_bot_buy')} "
              f"| 0.012 {b['exit']:10s} {100*(b['ret'] or 0):+7.2f}% headroom {b.get('bot_first_buy_headroom') and round(b['bot_first_buy_headroom'], 5)} dropped {b.get('bot_dropped')} feed {r['feed_first'][:4]}")
    json.dump(out, open(os.path.join(HERE, "replay.json"), "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
