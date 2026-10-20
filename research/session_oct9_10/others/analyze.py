#!/usr/bin/env python3
"""Census analysis: per pool (census.jsonl) the launch, the gates, the crowd's buys, the pull, and the cheap paper FOLLOW trade from the
pool's own Swap logs (score.py price() conventions); per family (families.json) the aggregate.

Paper FOLLOW (flip_engine 0.8): trigger = the first swap paying >= 0.0002 ETH into the pool (not our relay) within 150 blocks of the launch;
if it is at or before launch + ARM (the bot arms ~+6) the pool is "late" (no trade). Our buy (0.0012 ETH) at the head of trigger + 1 / + 2;
the sell is sent in the block of the first buy behind ours (our buy block .. buy + 2) that prices it >= +1% after gas, else at buy + 2;
it lands 1 block later ("fast") or 2 ("slow"); a negative ModifyLiquidity at or before the landing block = -100%. Gas 4.2e-6 ETH a round trip.
"""
import sys, os, json, pickle, statistics as st, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, "/home/user/v2pons/src")
from chain import T_SWAP, T_ML, W, sgn
import v4math
Q96 = 1 << 96; STAKE = int(0.0012e18); GAS = int(4.2e12); TP = 0.01; MINW = int(2e14); ARM = 6; TMAX = 150
RELAY = "2abb5653352f6b2f3b4f4261877cd02d9e05a957"; OP = "0x3194e32622c5d860a0572c74edda99dcfd8fc827"
OPCODES = {"2793923de1845d8707004ebbf2ab49fe7286113b7b69991aea7d6656f26f6d1c", "42544ef5d4754816b3cfe77f3a6fb1c8eb842d6eee101f7d15c638593a3351d2"}
C = lambda n: pickle.load(open(os.path.join(HERE, f"cache_{n}.pkl"), "rb"))
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x

inits = C("inits")["logs"]; txs = C("txs"); codes = C("codes"); plogs = C("plogs")
try: rcs = C("rcs")
except Exception: rcs = {}
oct8 = {p["pid"]: p["kind"] for p in json.load(open(os.path.join(os.path.dirname(HERE), "oct8_pools.json")))["pools"]}


def paper(sw, mls, b0, sp0, tick0, fee, trig_bn, land, lag, pull_bn, hold=2):
    B = trig_bn + land
    prev = [x for x in sw if x[0] < B]
    if prev: sp, L = prev[-1][4], prev[-1][5]
    else: sp, L = sp0, v4math.active_liquidity(tick0, [(lo, hi, d) for bn, lo, hi, d in mls if bn < B and d > 0])
    if L <= 0 or sp <= 0: return None
    tok = v4math.buy_out_int(sp, L, STAKE, fee)
    if tok <= 0: return None
    xn = STAKE - (STAKE * fee + 999_999) // 1_000_000
    def ret_at(spc, Lc):
        if Lc <= 0: return -1.0
        s_ours = int(Q96 / (Q96 / spc + xn / Lc))
        return (v4math.sell_out_int(s_ours, Lc, tok, fee) - STAKE - GAS) / STAKE
    send = B + hold; why = "deadline"
    for x in sw:
        if B <= x[0] <= B + hold and x[2] < 0 and ret_at(x[4], x[5]) >= TP: send = x[0]; why = "tp"; break
    lb = send + lag
    if pull_bn is not None and pull_bn <= lb: return {"ret": -1.0 - GAS / STAKE, "why": "pulled", "send": send - B, "landb": lb - B}
    pv = [x for x in sw if x[0] <= lb - 1]
    r = ret_at(pv[-1][4], pv[-1][5]) if pv else ret_at(sp, L)
    return {"ret": r, "why": why, "send": send - B, "landb": lb - B}


rows = []
for l in inits:
    pid = l["topics"][1]; b0 = int(l["blockNumber"], 16); d = l["data"]; h = l["transactionHash"]
    fee = W(d, 0); ts = sgn(W(d, 1)); hooks = "0x" + d[2 + 64 * 2 + 24: 2 + 64 * 3]; sp0 = W(d, 3); tick0 = sgn(W(d, 4))
    t = txs.get(h, {}); to = t.get("to"); code = codes.get(to, {}) if to else {}
    if to is None and h in rcs: to_eff = "create:" + str(rcs[h].get("contractAddress"))
    else: to_eff = to
    ev = sorted(plogs.get(pid, []), key=lambda x: (x[0], x[1])) if pid in plogs else None
    r = {"pid": pid, "b0": b0, "tx": h, "token": "0x" + l["topics"][3][-40:], "fee": fee, "ts": ts, "hooks": hooks, "from": t.get("from"), "to": to_eff,
         "nonce": int(t["nonce"], 16) if t.get("nonce") else None, "sel": t.get("input4"), "inlen": t.get("inlen"), "value": int(t["value"], 16) / 1e18 if t.get("value") else None,
         "prio": int(t["maxPriorityFeePerGas"], 16) if t.get("maxPriorityFeePerGas") else None, "code": code.get("hash"), "codesize": code.get("size"),
         "oct8kind": oct8.get(pid), "logs": ev is not None}
    r["ours"] = "orig" if to == OP else ("copy" if code.get("hash") in OPCODES else None)
    if ev is None: rows.append(r); continue
    sw = []; mls = []; rem = []
    for bn, li, t0, sender, dd, th in ev:
        if t0 == T_SWAP:
            if sender[-40:] == RELAY: continue
            sw.append((bn, li, s128(W(dd, 0)), s128(W(dd, 1)), W(dd, 2), W(dd, 3), sgn(W(dd, 4)), th))
        else:
            lo, hi, dl = sgn(W(dd, 0)), sgn(W(dd, 1)), sgn(W(dd, 2)); mls.append((bn, lo, hi, dl))
            if dl < 0: rem.append((bn, dl, th))
    adds_launch = [(lo, hi, dl) for (bn, li, t0, sender, dd, th) in ev if t0 == T_ML and th == h
                   for lo, hi, dl in [(sgn(W(dd, 0)), sgn(W(dd, 1)), sgn(W(dd, 2)))] if dl > 0]
    r["liq"] = v4math.active_liquidity(tick0, adds_launch); r["n_add_launch"] = len(adds_launch)
    r["liq_total_launch"] = sum(x[2] for x in adds_launch)
    tot_added = sum(x[3] for x in mls if x[3] > 0)
    r["pull"] = (rem[0][0] - b0) if rem else None
    r["pull_frac"] = (-rem[0][1] / max(1, sum(x[3] for x in mls if x[0] <= rem[0][0] and x[3] > 0))) if rem else None
    r["pull_tx"] = rem[0][2] if rem else None
    r["n_pulls"] = len(rem)
    buys = [x for x in sw if x[2] < 0]; real = [x for x in buys if -x[2] >= MINW]
    r["n_swaps"] = len(sw); r["n_buys"] = len(buys)
    r["first_any_buy"] = (buys[0][0] - b0) if buys else None
    if real:
        f = real[0]; r["trig"] = f[0] - b0; r["trig_eth"] = -f[2] / 1e18; r["trig_tx"] = f[7]
    else: r["trig"] = None
    r300 = [x for x in real if x[0] - b0 <= 300]; r["n_real300"] = len(r300)
    gaps = [b[0] - a[0] for a, b in zip(r300, r300[1:])]; r["gap_med300"] = st.median(gaps) if gaps else None
    pb = rem[0][0] if rem else None
    r["eth_in_before_pull"] = sum(-x[2] for x in buys if pb is None or x[0] < pb) / 1e18
    r["eth_out_before_pull"] = sum(x[2] for x in sw if x[2] > 0 and (pb is None or x[0] < pb)) / 1e18
    r["n_real_before_pull"] = sum(1 for x in real if pb is None or x[0] < pb)
    # gates
    g = []
    if hooks != "0x" + "0" * 40: g.append("hooks")
    if fee >= 10000: g.append("fee")
    if r["liq"] < 1e21: g.append("liq")
    if r["trig"] is None or r["trig"] > TMAX: g.append("no_trig")
    elif r["trig"] <= ARM: g.append("late")
    r["gates"] = g; r["tradable"] = not g
    if r["trig"] is not None and r["trig"] <= TMAX and hooks == "0x" + "0" * 40:
        tb = f[0]
        r["behind10"] = sum(1 for x in real if tb < x[0] <= tb + 10); r["behind10_eth"] = sum(-x[2] for x in buys if tb < x[0] <= tb + 10) / 1e18
        r["pull_after_trig"] = (pb - tb) if pb is not None else None
        r["paper"] = {}
        for land in (1, 2):
            for lag, nm in ((1, "fast"), (2, "slow")):
                r["paper"][f"land{land}_{nm}"] = paper(sw, mls, b0, sp0, tick0, fee, tb, land, lag, pb)
        r["paper"]["hold30"] = paper(sw, mls, b0, sp0, tick0, fee, tb, 1, 1, pb, hold=30)     # variant: sell on the first buy that pays +1% within 30 blocks
    alt = [x for x in real if ARM < x[0] - b0 <= TMAX]                                          # variant: the first real buy after the arming, even if one came before
    if alt and hooks == "0x" + "0" * 40 and r["trig"] is not None and r["trig"] <= ARM:
        r["alt_trig"] = alt[0][0] - b0
        r["paper_alt"] = {"land1_fast": paper(sw, mls, b0, sp0, tick0, fee, alt[0][0], 1, 1, pb), "hold30": paper(sw, mls, b0, sp0, tick0, fee, alt[0][0], 1, 1, pb, hold=30)}
    rows.append(r)

with open(os.path.join(HERE, "census.jsonl"), "w") as fo:
    for r in rows: fo.write(json.dumps(r) + "\n")
print("pools", len(rows), "with logs", sum(1 for r in rows if r["logs"]), "tradable", sum(1 for r in rows if r.get("tradable")))
