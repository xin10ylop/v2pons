#!/usr/bin/env python3
"""line_adapt: the exact replay of candidate rules on the v3.0 and v5.0 lines (data/rec.json, complete 1,200-block windows only).

Model (explore/chk/replay.py's, generalised):
  - our buy of X wei lands in block B = launch + entry, AFTER every other transaction of that block; tokens = buy_out_int at the pool's state at the
    end of block B (the last swap with block <= B, else the launch state)
  - entry refused (no trade, no cost) if a bot buy (router 0x1cbaf24d, c1120e3d) landed before block B (the feed showed it before the fire);
    a bot buy IN block B is ahead of ours: we buy behind it and the engine sells at once (B + 1)
  - a pull (first negative ModifyLiquidity) in a block < B: the pool is gone before we land (the engine has no pull detector: the buy reverts,
    the buy's gas is lost; counted as a trade at -gas); a pull in block B lands ahead of ours: the same
  - the sell lands at the HEAD of block S (ahead of every other transaction of S), priced on the chain state replayed with our buy in: every swap
    in blocks B+1..S-1 by its own shift (a buy adds its d(1/sqrtP), a sell its d(sqrtP)); a bot buy whose output with our buy ahead falls under
    its calldata minOut (word 4) is dropped (it reverts)
  - a pull in a block <= S: the stake is lost (-100% - gas)
  - gas 2 x 104,000 x the launch block's base fee; fees: the pool's 1% on the buy and on the sell (in buy_out_int / sell_out_int)
Rules:
  a  front +1: B = launch + 1; S = the block after the first bot buy behind ours, or launch + D (D 20/40/60/80) if none before it
  b  delayed front +X: B = launch + X (X 10..20); S as a, deadline launch + X + D
  c  ride: B = the block after the first bot buy; S = B + K (K 5/10/20/40) or the block after the next bot buy (deadline B + 40 / B + 80)
  d  see the D_RULES below
Each rule is also given 'with the observed reaction' (trap): an outsider buy at launch +1..+3 in the new regime was followed by a pull at
+7..+10 before any bot buy in 13 of 16 pools (trap_offsets.json); a rule entering at +1..+3 is then priced with a pull at launch + 8.
"""
import sys, os, json, time, collections, statistics as st
sys.path.insert(0, "/home/user/v2pons/src")
import v4math
HERE = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(HERE, "data")
Q96 = 1 << 96; GAS = 2 * 104_000; USD = 2570.0
NEW_FROM = int(time.mktime(time.strptime("2026-10-11 04:22:19", "%Y-%m-%d %H:%M:%S"))) - time.timezone   # the first late-bot launch (regime.py)


def net(x, fee): return x - (x * fee + 999_999) // 1_000_000


def prep(r):
    sw = sorted(r["swaps"], key=lambda s: (s["off"], s["li"]))
    bots = [s for s in sw if s["bot"] and s["side"] == "B"]
    return {"pid": r["pid"], "fam": r["fam"], "b0": r["b0"], "ts0": r["ts0"], "fee": r["fee"], "sp0": r["sp0"], "L0": r["L0"], "bf": r["basefee0"] or 20_000_000,
            "sw": sw, "bots": bots, "pull": r["pull"]["off"] if r["pull"] else None, "new": r["ts0"] >= NEW_FROM, "nonce": r["nonce"]}


def trade(p, X, B, mode, par, pull_override=None, lag=1):
    """mode 'bot': S = first bot buy behind ours + 1, deadline block par (absolute offset); 'fixed': S = B + par; """
    fee = p["fee"]; gas = GAS * p["bf"]
    pull = p["pull"] if pull_override is None else (min(p["pull"], pull_override) if p["pull"] is not None else pull_override)
    if any(b["off"] < B for b in p["bots"]) and mode == "bot":                   # a front: the bot's buy came before ours
        return {"exit": "late", "ret": None}
    if pull is not None and pull <= B:
        return {"exit": "pulled_before_buy", "ret": -(GAS // 2) * p["bf"] / X, "pulled": False}
    pre = [s for s in p["sw"] if s["off"] <= B]
    spB, LB = (pre[-1]["sp"], pre[-1]["L"]) if pre else (p["sp0"], p["L0"])
    if LB == 0: return {"exit": "pulled_before_buy", "ret": -(GAS // 2) * p["bf"] / X, "pulled": False}
    tokens = v4math.buy_out_int(spB, LB, X, fee)
    in_block = [b for b in p["bots"] if b["off"] == B]
    if mode == "nextbot":                                                          # a ride: out on the next bot buy behind ours, deadline par
        nb = next((b for b in p["bots"] if b["off"] > B), None)
        if nb is not None and nb["off"] < par: S = nb["off"] + lag; why = "bot"
        else: S = par; why = "deadline"
    elif mode == "bot":
        if in_block:
            S = B + lag; why = "behind_bot_in_block"
        else:
            nb = next((b for b in p["bots"] if b["off"] > B), None)
            if nb is not None and nb["off"] < par: S = nb["off"] + lag; why = "bot"
            else: S = par; why = "deadline"
    else:
        S = B + par; why = "fixed"
    if pull is not None and pull <= S:
        return {"exit": "pulled_first", "ret": (-X - gas) / X, "pulled": True, "S": S, "B": B}
    s = Q96 / (Q96 / spB + net(X, fee) / LB); prev = spB; L = LB; dropped = 0; filled = 0
    for x in p["sw"]:
        if x["off"] <= B: continue
        if x["off"] >= S: break
        L = x["L"]
        if x["a0"] < 0:
            d_inv = Q96 / x["sp"] - Q96 / prev
            if x["bot"]:
                out_us = v4math.buy_out_int(int(s), L, -x["a0"], fee)
                if out_us < x["minout"]:
                    dropped += 1; prev = x["sp"]; continue
                filled += 1
            s = Q96 / (Q96 / s + d_inv)
        else:
            s = s + (x["sp"] - prev)
        prev = x["sp"]
    eth = v4math.sell_out_int(int(s), L, tokens, fee)
    ret = (eth - X - gas) / X
    if why == "bot" and dropped and not filled: why = "bot_reverted"
    return {"exit": why, "ret": ret, "pulled": False, "S": S, "B": B, "filled": filled, "dropped": dropped}


def summ(rs, X, n_pools, rate_day):
    tr = [r for r in rs if r["ret"] is not None]
    v = [r["ret"] for r in tr]
    if not v: return {"n": 0, "pools": n_pools}
    m = st.mean(v); pulled = sum(1 for r in tr if r["pulled"])
    ex = collections.Counter(r["exit"] for r in rs)
    good = [r["ret"] for r in tr if r["exit"] in ("bot",) or (r["exit"] == "fixed" and r.get("filled"))]
    other = [r["ret"] for r in tr if not r["pulled"] and r not in [] and not (r["exit"] in ("bot",) or (r["exit"] == "fixed" and r.get("filled")))]
    q = pulled / len(v)
    be = None
    if good and other:
        rg, ro = st.mean(good), st.mean(other)
        if rg > ro: be = max(0.0, -((1 - q) * ro + q * (-1.0)) / (rg - ro))
    elif good and not other:
        rg = st.mean(good)
        if rg > 0: be = q / (rg + q) if q else 0.0
    usd_trade = m * X / 1e18 * USD
    npv = [r["ret"] for r in tr if not r["pulled"]]
    mnp = st.mean(npv) if npv else None
    q_be = (mnp / (1 + mnp)) if mnp is not None and mnp > 0 else None              # the share of trades the operator may pull under us before the rule loses money
    return {"n": len(v), "pools": n_pools, "entered_frac": round(len(v) / n_pools, 3), "mean%": round(100 * m, 3), "median%": round(100 * st.median(v), 3),
            "win": round(sum(1 for a in v if a > 0) / len(v), 3), "pulled_first": pulled, "exits": dict(ex),
            "usd_trade": round(usd_trade, 4), "usd_day": round(usd_trade * rate_day * len(v) / n_pools, 2),
            "good_frac": round(len(good) / len(v), 3), "breakeven_good_frac": None if be is None else round(be, 3),
            "mean_good%": round(100 * st.mean(good), 2) if good else None, "breakeven_pull_rate": None if q_be is None else round(q_be, 4), "mean_other%": round(100 * st.mean(other), 2) if other else None}


def rules():
    R = []
    for Dd in (20, 40, 60, 80):
        R.append((f"a front+1 D{Dd}", lambda p, Dd=Dd: (1, "bot", 1 + Dd), 1))
    for Xx in (10, 12, 14, 16, 18, 20):
        for Dd in (20, 40, 60, 80):
            R.append((f"b front+{Xx} D{Dd}", lambda p, Xx=Xx, Dd=Dd: (Xx, "bot", Xx + Dd), Xx))
    for K in (5, 10, 20, 40):
        R.append((f"c ride K{K}", lambda p, K=K: ((p["bots"][0]["off"] + 1, "fixed", K) if p["bots"] else None), None))
    for Dd in (40, 80):
        R.append((f"c ride next-bot D{Dd}", lambda p, Dd=Dd: ((p["bots"][0]["off"] + 1, "nextbot", p["bots"][0]["off"] + 1 + Dd) if p["bots"] else None), None))
    # d: ride from the k-th bot buy to the next one (the bot buys every ~20-25 blocks in the new regime)
    for k in (1, 2, 3):
        R.append((f"d ride bot{k + 1}->next D40", lambda p, k=k: ((p["bots"][k]["off"] + 1, "nextbot", p["bots"][k]["off"] + 1 + 40) if len(p["bots"]) > k else None), None))
    # d: the delayed front entered later, closer to the bot's first buy
    for Xx in (22, 25, 30):
        R.append((f"d front+{Xx} D60", lambda p, Xx=Xx: (Xx, "bot", Xx + 60), Xx))
    return R


def main():
    R = json.load(open(os.path.join(D, "rec.json")))
    P = [prep(r) for r in R if r["complete"]]
    out = {}; lines = []
    for fam in ("v3.0", "v5.0"):
        for reg in ("new", "all", "old"):
            G = [p for p in P if p["fam"] == fam and (reg == "all" or (reg == "new") == p["new"])]
            if not G: continue
            span_h = (max(p["ts0"] for p in G) - min(p["ts0"] for p in G)) / 3600 or 1
            rate = len(G) / span_h * 24
            for name, fn, ent in rules():
                for stake in (0.002, 0.0058):
                    X = int(stake * 1e18); rs = []
                    rs_trap = []
                    for p in G:
                        a = fn(p)
                        if a is None: rs.append({"exit": "no_bot", "ret": None}); rs_trap.append({"exit": "no_bot", "ret": None}); continue
                        B, mode, par = a
                        rs.append(trade(p, X, B, mode, par))
                        po = (8 if (ent is not None and ent <= 3) else None)
                        rs_trap.append(trade(p, X, B, mode, par, pull_override=po) if po else rs[-1])
                    k = f"{fam}|{reg}|{name}|{stake}"
                    out[k] = summ(rs, X, len(G), rate)
                    if ent is not None and ent <= 3: out[k + "|trap"] = summ(rs_trap, X, len(G), rate)
                    s = out[k]
                    lines.append(f"{fam} {reg:3s} {name:26s} {stake:<6} n {s['n']:4d}/{s['pools']:4d} mean {s.get('mean%', 0):+7.2f}% med {s.get('median%', 0):+7.2f}% win {s.get('win', 0):5.3f} pulled {s.get('pulled_first', 0):3d} "
                                 f"$/tr {s.get('usd_trade', 0):+7.3f} $/day {s.get('usd_day', 0):+8.1f} be {s.get('breakeven_good_frac')} good {s.get('good_frac')} qbe {s.get('breakeven_pull_rate')} exits {s.get('exits')}")
                    if k + "|trap" in out:
                        t = out[k + "|trap"]
                        lines.append(f"{'':12s} with the observed reaction (pull at +8): mean {t.get('mean%', 0):+7.2f}% med {t.get('median%', 0):+7.2f}% pulled {t.get('pulled_first', 0)} $/day {t.get('usd_day', 0):+8.1f}")
    json.dump(out, open(os.path.join(HERE, "replay_rules.json"), "w"), indent=1)
    open(os.path.join(HERE, "replay_rules.txt"), "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
