"""The brief's replay on a v4 pool (single active range; integer v4 math as src/v4math.py, both currency orders):
buy q ETH at the head of block L+a, re-apply every later swap by its input amount (buys: quote in; sells: tokens in) with the event's
liquidity and fee, sell all tokens at the head of block L+b. A pull (ModifyLiquidity < 0) in a block <= L+b = -100%. Gas $0.02."""
from common import *
from v4math import buy_out_int, sell_out_int, Q96          # src/v4math.py (read-only import)
ETH_USD = 2570.0; GAS_USD = 0.02


def net(x, fee): return x - (x * fee + 999_999) // 1_000_000


def step0(s, L, x_gross, fee):
    """currency0 in (exact input, fee on input): -> (new sqrtP, currency1 out); same arithmetic as v4math.buy_out_int"""
    x = net(x_gross, fee)
    if x <= 0 or L <= 0: return s, 0
    den = L + (x * s) // Q96; s2 = (L * s + den - 1) // den
    return s2, (L * (s - s2)) // Q96


def step1(s, L, y_gross, fee):
    """currency1 in: -> (new sqrtP, currency0 out); same arithmetic as v4math.sell_out_int"""
    y = net(y_gross, fee)
    if y <= 0 or L <= 0: return s, 0
    s2 = s + (y * Q96) // L
    return s2, (L * (s2 - s) * Q96) // (s * s2)


def prep(r, o):
    """-> dict with launch block, quote side, initial (sqrtP, L), swaps [(bn, li, buy, q_in_or_t_in, L_ev, fee_ev, sqrt_ev, q_abs, t_abs, tx)], pulls [bn], adds [(bn, li, L)]"""
    qs = r["quote_side"]; lb = r["launch_block"]; t0 = r["tick0"]
    adds0 = [e for e in o["ev"] if e[0] == "m" and e[8] > 0 and e[10] == r["launch_tx"]]
    act = (lambda lo, hi: lo < t0 <= hi) if qs == 0 else (lambda lo, hi: lo <= t0 < hi)
    L0 = sum(e[8] for e in adds0 if act(e[6], e[7]))
    sw, pulls, adds = [], [], []
    for e in o["ev"]:
        if e[0] == "s":
            dq, dt = (e[6], e[7]) if qs == 0 else (e[7], e[6])
            buy = dq < 0
            sw.append({"bn": e[1], "li": e[3], "buy": buy, "inp": (-dq if buy else -dt), "q": abs(dq), "t": abs(dt), "L": e[9], "fee": e[11], "sqrt": e[8], "tx": e[12]})
        elif e[0] == "m":
            if e[8] < 0: pulls.append(e[1])
            elif e[10] != r["launch_tx"]: adds.append((e[1], e[3], e[8]))
    return {"lb": lb, "qs": qs, "s0": r["sqrt_p0"], "L0": L0, "sw": sw, "pulls": pulls, "adds": adds, "fee": r["fee"]}


def q_units(r, q_eth):
    return int(q_eth * 2570 * 10**6) if r["quote"] == "USDG" else int(q_eth * 10**18)


def to_eth(r, x):
    return x / (2570 * 10**6) if r["quote"] == "USDG" else x / 1e18


def buy_step(qs, s, L, x, fee):
    """quote in -> (s, tokens out)"""
    return step0(s, L, x, fee) if qs == 0 else step1(s, L, x, fee)


def sell_step(qs, s, L, t, fee):
    """tokens in -> (s, quote out)"""
    return step1(s, L, t, fee) if qs == 0 else step0(s, L, t, fee)


def state_before(P, blk):
    """(sqrtP, L, fee) after every event in blocks < blk"""
    s, L, fee = P["s0"], P["L0"], P["fee"] if P["fee"] < 1_000_000 else 0
    evs = [("s", w["bn"], w["li"], w) for w in P["sw"] if w["bn"] < blk] + [("a", a[0], a[1], a[2]) for a in P["adds"] if a[0] < blk]
    for k, bn, li, w in sorted(evs, key=lambda x: (x[1], x[2])):
        if k == "s": s, L, fee = w["sqrt"], w["L"], w["fee"]
        else: L += w
    return s, L, fee


def replay(r, P, a, b, q_eth=0.0058):
    """-> dict(ret, usd, pulled, buy_ok) ; ret is the fractional return net of gas"""
    lb = P["lb"]; A, B = lb + a, lb + b
    if B <= A: return None
    pulled = any(p <= B for p in P["pulls"])
    if pulled:
        usd = -q_eth * ETH_USD - GAS_USD
        return {"ret": usd / (q_eth * ETH_USD), "usd": usd, "pulled": True, "pull_before_buy": any(p < A for p in P["pulls"])}
    s, L, fee = state_before(P, A)
    qs = P["qs"]
    s, tok = buy_step(qs, s, L, q_units(r, q_eth), fee)
    if tok <= 0: return None
    for w in P["sw"]:
        if w["bn"] < A or w["bn"] >= B: continue
        L = w["L"]; f = w["fee"]
        if w["buy"]: s, _ = buy_step(qs, s, L, w["inp"], f)
        else: s, _ = sell_step(qs, s, L, w["inp"], f)
    for ad in P["adds"]:
        if A <= ad[0] < B: pass   # adds change L; the next swap event carries the new L (our sell uses the last L seen)
    s2, out = sell_step(qs, s, L, tok, fee)
    out_eth = to_eth(r, out)
    usd = (out_eth - q_eth) * ETH_USD - GAS_USD
    return {"ret": usd / (q_eth * ETH_USD), "usd": usd, "pulled": False, "pull_before_buy": False}


def validate(r, P):
    """re-apply every swap from the launch state without our trade; -> max relative error of the simulated sqrtP vs the events"""
    s, L, fee = P["s0"], P["L0"], P["fee"]; errs = []
    for w in P["sw"]:
        L = w["L"]
        s = buy_step(P["qs"], s, L, w["inp"], w["fee"])[0] if w["buy"] else sell_step(P["qs"], s, L, w["inp"], w["fee"])[0]
        errs.append(abs(s - w["sqrt"]) / w["sqrt"]); s = w["sqrt"]
    return max(errs) if errs else 0.0


def stats(res, per_day_launches=None, tradable_share=1.0):
    res = [x for x in res if x is not None]
    if not res: return {"n": 0}
    rets = [x["ret"] for x in res]; usd = [x["usd"] for x in res]
    m = S.mean(usd)
    out = {"n": len(res), "mean": round(S.mean(rets), 4), "median": round(S.median(rets), 4), "win": round(sum(1 for x in rets if x > 0) / len(rets), 3),
           "worst": round(min(rets), 4), "best": round(max(rets), 4), "pulled": round(sum(1 for x in res if x["pulled"]) / len(res), 3), "mean_usd": round(m, 4)}
    if per_day_launches is not None: out["usd_day"] = round(m * per_day_launches * tradable_share, 2)
    return out
