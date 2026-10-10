#!/usr/bin/env python3
"""Exact replay of the release-0.9 'front' rule on every v2.433 launch in data.pkl (fetch.py), against the chain.

Engine (flip_engine 0.9, front):
  - armed from the launch tx at b0; feed buys (value > 0, >= 20 bytes carrying the token, to != token) after it in b0 move the engine's copy;
    at the end of b0 it fires unless a feed buy >= 0.04 ETH came (the bot's) or others' ETH + the stake > 0.008 ETH
  - our buy: minOut = buy_out_int(copy at fire) x 0.97; lands at B = b0+1 (fast) or b0+2 (slow), after every other tx of B
  - after our buy (live: the feed shows it at B, the copy moved by it): each later feed buy, in order:
      * the first one >= 0.04 ETH (the bot's): q1 = quote at the copy (ours in) vs q0 = quote at the launch state; q1 < 0.99 q0 -> the engine
        says it reverts, does not apply it, sends the sell at once
      * else applied; take_profit (any size, as coded): sell_out_int(copy, feed_tokens) - stake - basefee x 250k >= 1% of stake -> send
    deadline: send at B + 12 (after that block's txs)
  - dry-run model (what the running dry run prints): virtual buy at the HEAD of b0+2 (plan_buy_seq), feed_tokens from the copy through b0+1,
    our buy put into the copy for the bot check / take profit, deadline b0+14
Chain (as explore/chk/replay.py): our buy inserted after B's other txs; the sell lands at send+1 (fast) / send+2 (slow), priced at the head of
that block (also at its tail, as a check); every swap between replayed by its own shift (buys add to 1/sqrtP, sells to sqrtP); a volume-bot buy
(router c1120e3d) whose output with ours in front falls under its calldata minOut (word 4) is dropped as reverted; a pull (negative
ModifyLiquidity) at or before the sell's landing block = the stake lost. Gas: 103,861 (buy) + 103,894 (sell) x the landing blocks' base fee.
"""
import sys, os, pickle, json, statistics as st, datetime
HERE = os.path.dirname(os.path.abspath(__file__)); SCR = os.path.dirname(HERE)
sys.path.insert(0, SCR); sys.path.insert(0, "/home/user/v2pons/src")
from chain import T_INIT, T_SWAP, T_ML, W, sgn
import v4math
Q96 = 1 << 96
POSM = "58daec3116aae6d93017baaea7749052e8a04fa7"; ROUTER = "1cbaf24d53fe930fce8eff149fa797d2611da149"
STAKE = int(0.0012e18); TP = 0.01; HOLD = 12; AHEAD_MAX = int(0.008e18); BOT_MIN = int(0.04e18); BOT_MINOUT = 0.99; BUY_SLIP = 0.03
MIN_TRIG = int(0.0002e18)
BUY_GAS, SELL_GAS, SELL_GAS_PULLED = 103861, 103894, 135200
LAUNCH_LIQ = 49279426163460954002188; LAUNCH_SP = 1604517591721945638372359205383840
DUST = {"e71a69f434a719cd5afa411568b69716aab3b84a": "dustA", "f6e55480c5939da146092301e388654879c6e6fb": "dustB", "b002e8a04b2822d8f2890b022ddea3d25f9c3df8": "dustC"}


def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x


def net(x, fee): return x - (x * fee + 999_999) // 1_000_000


def wd(inp, i): return int(inp[10 + 64 * i: 10 + 64 * (i + 1)], 16)


def prep(R, txc):
    m = R["meta"]; pid = m["pid"]; b0 = m["b0"]; rec = R["rec"]
    init = [l for l in rec["logs"] if l["topics"] and l["topics"][0] == T_INIT and l["topics"][1] == pid][0]
    fee = W(init["data"], 0); sp0 = W(init["data"], 3); tick0 = sgn(W(init["data"], 4))
    adds = [(sgn(W(l["data"], 0)), sgn(W(l["data"], 1)), sgn(W(l["data"], 2))) for l in rec["logs"] if l["topics"] and l["topics"][0] == T_ML and l["topics"][1] == pid]
    liq = v4math.active_liquidity(tick0, adds)
    token = init["topics"][3][-40:]; tb = bytes.fromhex(token)
    bt = {int(b["number"], 16): b for b in R["blocks"] if b}
    sw, mls = [], []
    for l in R["logs"]:
        bn = int(l["blockNumber"], 16); d = l["data"]; t = txc.get(l["transactionHash"])
        if l["topics"][0] == T_SWAP:
            sw.append({"bn": bn, "li": int(l["logIndex"], 16), "ti": int(l["transactionIndex"], 16), "a0": s128(W(d, 0)), "a1": s128(W(d, 1)), "sp": W(d, 2), "L": W(d, 3),
                       "tx": l["transactionHash"], "to": (t["to"] or "")[2:].lower() if t else None, "input": t["input"] if t else None,
                       "from": t["from"][2:].lower() if t else None, "value": int(t["value"], 16) if t else None})
        else:
            mls.append({"bn": bn, "ti": int(l["transactionIndex"], 16), "dl": sgn(W(d, 2)), "tx": l["transactionHash"], "from": (txc.get(l["transactionHash"]) or {}).get("from")})
    pulls = [x for x in mls if x["dl"] < 0]
    feed = []
    launch_idx = m["txindex"]
    for k in sorted(bt):
        for t in bt[k]["transactions"]:
            ti = int(t["transactionIndex"], 16)
            if k == b0 and ti <= launch_idx: continue
            to = (t.get("to") or "")[2:].lower(); data = bytes.fromhex(t["input"][2:]); v = int(t["value"], 16)
            if to == POSM and data[:4].hex() == "ac9650d8" and len(data) == 1444: continue
            if v == 0 or len(data) < 20: continue
            if tb in data and to != token:
                feed.append({"bn": k, "idx": ti, "value": v, "hash": t["hash"], "to": to, "from": t["from"][2:].lower()})
    return {"pid": pid, "b0": b0, "fee": fee, "sp0": sp0, "liq": liq, "token": token, "bt": bt, "sw": sw, "mls": mls, "pull": pulls[0] if pulls else None, "feed": feed,
            "from": m["from"][2:].lower(), "ts": int(bt[b0]["timestamp"], 16), "txindex": launch_idx, "last_block": max(bt)}


def bf(p, n): return int(p["bt"][n]["baseFeePerGas"], 16) if n in p["bt"] else 20_000_000


def engine(p, B, dry):
    """the engine's decisions after our buy. dry: virtual buy at the head of B (feed buys of B behind ours); else our buy at the end of B.
    returns (send_block, why, tp_ret, feed_tokens, trig)"""
    liq = p["liq"]; fee = p["fee"]
    sp = float(p["sp0"])
    for f in p["feed"]:
        if (f["bn"] >= B) if dry else (f["bn"] > B): break
        sp = v4math.sqrt_after_buy(sp, liq, net(f["value"], fee))
    feed_tokens = v4math.buy_out_int(int(sp), liq, STAKE, fee)
    if not dry:
        sp = v4math.sqrt_after_buy(sp, liq, net(STAKE, fee))           # live: apply_buy(ours)
    bot_seen = any(f["value"] >= BOT_MIN for f in p["feed"] if ((f["bn"] < B) if dry else (f["bn"] <= B)))
    for f in p["feed"]:
        if (f["bn"] < B) if dry else (f["bn"] <= B): continue
        if f["bn"] > B + HOLD: break
        sp_us = v4math.sqrt_after_buy(sp, liq, net(STAKE, fee)) if dry else sp
        if f["value"] >= BOT_MIN and not bot_seen:
            bot_seen = True
            q0 = v4math.buy_out_int(p["sp0"], liq, f["value"], fee); q1 = v4math.buy_out_int(int(sp_us), liq, f["value"], fee)
            if q1 < q0 * BOT_MINOUT:
                return f["bn"], "engine: bot buy reverts", None, feed_tokens, f
        sp = v4math.sqrt_after_buy(sp, liq, net(f["value"], fee))
        sp_us = v4math.sqrt_after_buy(sp, liq, net(STAKE, fee)) if dry else sp
        eth = v4math.sell_out_int(int(sp_us), liq, feed_tokens, fee)
        r = (eth - STAKE - bf(p, f["bn"]) * 250_000) / STAKE
        if r >= TP:
            return f["bn"], "take profit", round(r, 4), feed_tokens, f
    return B + HOLD, "deadline", None, feed_tokens, None


def chain_state_after(p, B):
    prevB = [x for x in p["sw"] if x["bn"] <= B]
    return (prevB[-1]["sp"], prevB[-1]["L"]) if prevB else (p["sp0"], p["liq"])


def first_bot_buy(p):
    return next((x for x in p["sw"] if x["a0"] < 0 and x["to"] == ROUTER and x["input"] and x["input"][:10] == "0xc1120e3d"), None)


def trade(p, case):
    b0 = p["b0"]; fee = p["fee"]; liq = p["liq"]; X = STAKE; xn = net(X, fee)
    B = b0 + (1 if case == "fast" else 2); lag = 1 if case == "fast" else 2
    pull = p["pull"]["bn"] if p["pull"] else None
    # fire at the end of b0: the engine's copy and the skip rule
    sp_f = float(p["sp0"]); eth_in = 0; skip = None
    for f in p["feed"]:
        if f["bn"] > b0: break
        if f["value"] >= BOT_MIN: skip = "bot buy before fire"
        sp_f = v4math.sqrt_after_buy(sp_f, liq, net(f["value"], fee)); eth_in += f["value"]
        if eth_in + STAKE > AHEAD_MAX: skip = skip or "ahead > 0.008"
    out = {"eth_in_b0": eth_in, "B": B - b0}
    if skip: return dict(out, exit="skip", why=skip, ret=None)
    if pull is not None and pull <= b0: return dict(out, exit="pulled before fire", ret=None)
    expected = v4math.buy_out_int(int(sp_f), liq, X, fee); min_out = int(expected * (1 - BUY_SLIP))
    spB, LB = chain_state_after(p, B)
    if pull is not None and pull <= B:
        return dict(out, exit="pull before buy", ret=-(BUY_GAS + SELL_GAS) * bf(p, B) / X)
    tokens = v4math.buy_out_int(spB, LB, X, fee)
    if tokens < min_out:
        return dict(out, exit="buy reverted", ret=-(BUY_GAS * bf(p, B) + SELL_GAS * bf(p, B + 2)) / X)
    send, why, tp_live, feed_tokens, trig = engine(p, B, dry=False)
    S = send + lag
    out.update(send=send - b0, S=S - b0, why=why, tp_live=tp_live, trig_value=trig["value"] if trig else None, trig_to=trig["to"] if trig else None,
               tokens=tokens, feed_tokens=feed_tokens, tokens_vs_minout=tokens / min_out)
    if pull is not None and pull <= S:
        return dict(out, exit="pulled before sell", ret=(-X - BUY_GAS * bf(p, B) - SELL_GAS_PULLED * bf(p, S)) / X)
    if S > p["last_block"] and S > max(x["bn"] for x in p["sw"]):
        pass
    # chain at the head of S (and at its tail)
    s = Q96 / (Q96 / spB + xn / LB); prev = spB; L = LB; dropped = []; between = []
    s_head = None; L_head = None
    for x in p["sw"]:
        if x["bn"] <= B: continue
        if x["bn"] >= S and s_head is None: s_head, L_head = s, L
        if x["bn"] > S: break
        if x["L"] != L: L = x["L"]
        bot = x["to"] == ROUTER and x["input"] and x["input"][:10] == "0xc1120e3d"
        if x["a0"] < 0:
            d_inv = Q96 / x["sp"] - Q96 / prev
            if bot:
                mo = wd(x["input"], 4); X2 = -x["a0"]
                out_with_us = v4math.buy_out_int(int(s), L, X2, fee)
                if out_with_us < mo:
                    dropped.append((x["bn"] - b0, round(out_with_us / mo, 6))); prev = x["sp"]; continue
            s = Q96 / (Q96 / s + d_inv)
        else:
            s = s + (x["sp"] - prev)
        prev = x["sp"]
        if x["bn"] < S: between.append(("bot " if bot else "") + ("B" if x["a0"] < 0 else "S") + f"{abs(x['a0']) / 1e18:.5f}@+{x['bn'] - b0}")
    if s_head is None: s_head, L_head = s, L
    eth_head = v4math.sell_out_int(int(s_head), L_head, tokens, fee); eth_tail = v4math.sell_out_int(int(s), L, tokens, fee)
    gas = BUY_GAS * bf(p, B) + SELL_GAS * bf(p, S)
    return dict(out, exit=why, ret=(eth_head - X - gas) / X, ret_tail=(eth_tail - X - gas) / X, ret_gross=(eth_head - X) / X, bot_dropped=dropped, swaps_between=between)


def main():
    D = pickle.load(open(os.path.join(HERE, "data.pkl"), "rb"))
    pools = sorted((prep(R, D["txcache"]) for R in D["pools"].values()), key=lambda p: p["b0"])
    rows = []
    for p in pools:
        b0 = p["b0"]
        fb = first_bot_buy(p)
        row = {"pid": p["pid"], "b0": b0, "time_utc": datetime.datetime.fromtimestamp(p["ts"], datetime.UTC).strftime("%Y-%m-%d %H:%M:%S"),
               "pull": (p["pull"]["bn"] - b0) if p["pull"] else None, "pull_block": p["pull"]["bn"] if p["pull"] else None,
               "pull_by_launcher": (p["pull"]["from"] or "")[2:].lower() == p["from"] if p["pull"] else None, "logs_to": D["logs_to"]}
        if fb:
            row["bot_buy_block"] = fb["bn"]; row["bot_off"] = fb["bn"] - b0; row["bot_eth"] = -fb["a0"] / 1e18; row["bot_value"] = fb["value"]
            # with our buy in front (at the end of b0+1 or b0+2, both before the bot's block): output vs its minOut
            for case, B in (("fast", b0 + 1), ("slow", b0 + 2)):
                pre = [x for x in p["sw"] if (x["bn"], x["li"]) < (fb["bn"], fb["li"])]
                # chain before the bot buy with ours inserted at B
                spB, LB = chain_state_after(p, B); s = Q96 / (Q96 / spB + net(STAKE, p["fee"]) / LB); prev = spB
                for x in pre:
                    if x["bn"] <= B: continue
                    s = Q96 / (Q96 / s + (Q96 / x["sp"] - Q96 / prev)) if x["a0"] < 0 else s + (x["sp"] - prev); prev = x["sp"]
                row[f"bot_headroom_{case}"] = v4math.buy_out_int(int(s), LB, -fb["a0"], p["fee"]) / wd(fb["input"], 4)
        # others' buys before the bot (chain)
        row["ahead_of_bot_chain"] = [(x["bn"] - b0, -x["a0"] / 1e18, DUST.get(x["from"], x["from"][:8]), x["to"][:8]) for x in p["sw"] if fb and (x["bn"], x["li"]) < (fb["bn"], fb["li"]) and x["a0"] < 0]
        # outsiders: non-bot buys >= 0.0002 ETH after the launch (until the pull)
        outs = []
        pb = p["pull"]["bn"] if p["pull"] else None
        for x in p["sw"]:
            if x["a0"] >= 0 or -x["a0"] < MIN_TRIG: continue
            if x["to"] == ROUTER: continue
            if pb is not None and x["bn"] > pb: continue
            outs.append({"off": x["bn"] - b0, "eth": -x["a0"] / 1e18, "from": x["from"], "to": x["to"], "who": "launcher" if x["from"] == p["from"] else DUST.get(x["from"], "outsider"),
                         "to_pull": (pb - x["bn"]) if pb is not None else None})
        row["outsider_buys"] = outs
        # all non-router buys of any size (for context)
        row["small_nonbot_buys"] = [(x["bn"] - b0, round(-x["a0"] / 1e18, 7), DUST.get(x["from"], x["from"][:8]), x["to"][:8]) for x in p["sw"] if x["a0"] < 0 and x["to"] != ROUTER and (pb is None or x["bn"] <= pb)]
        # the dry-run engine model (virtual buy at the head of b0+2)
        send, why, tp, ft, trig = engine(p, b0 + 2, dry=True)
        row["dry"] = {"send": send - b0, "after_buy": send - (b0 + 2), "why": why, "tp_ret": tp, "trig_value": trig["value"] / 1e18 if trig else None}
        row["feed_b0"] = [(f["idx"], f["value"] / 1e18, f["to"][:8]) for f in p["feed"] if f["bn"] == b0]
        row["feed_first"] = [(f["bn"] - b0, f["value"] / 1e18, f["to"][:8]) for f in p["feed"][:6]]
        for case in ("fast", "slow"):
            row[case] = trade(p, case)
        rows.append(row)
    json.dump(rows, open(os.path.join(HERE, "replay.json"), "w"), indent=1, default=str)
    for r in rows:
        f, s, d = r["fast"], r["slow"], r["dry"]
        print(f"{r['time_utc'][11:]} {r['pid'][:10]} b0 {r['b0']} b0-feed {r['feed_b0']} bot +{r.get('bot_off')} {r.get('bot_eth')} hr {r.get('bot_headroom_fast', 0):.5f}/{r.get('bot_headroom_slow', 0):.5f} "
              f"pull +{r['pull']} | dry {d['why']} +{d['after_buy']} tp {d['tp_ret']} | fast {f['exit']} send +{f.get('send')} S +{f.get('S')} tp {f.get('tp_live')} ret {100 * (f['ret'] or 0):+.2f}% tail {100 * (f.get('ret_tail') or 0):+.2f}% "
              f"| slow {s['exit']} send +{s.get('send')} S +{s.get('S')} tp {s.get('tp_live')} ret {100 * (s['ret'] or 0):+.2f}% tail {100 * (s.get('ret_tail') or 0):+.2f}% drop {f.get('bot_dropped')}/{s.get('bot_dropped')} btw {f.get('swaps_between')}/{s.get('swaps_between')}")
    for case in ("fast", "slow"):
        v = [r[case]["ret"] for r in rows if r[case]["ret"] is not None]
        print(case, "n", len(v), "mean %+.3f%%" % (100 * st.mean(v)), "median %+.3f%%" % (100 * st.median(v)), "worst %+.3f%%" % (100 * min(v)), "best %+.3f%%" % (100 * max(v)),
              "-100%:", sum(1 for x in v if x < -0.9))
    tps = [r["dry"]["tp_ret"] for r in rows if r["dry"]["tp_ret"] is not None]
    print("dry model tp_ret first 16: mean %+.2f%% worst %+.2f%% (n %d)" % (100 * st.mean(tps[:16]), 100 * min(tps[:16]), len(tps[:16])))


if __name__ == "__main__":
    main()
