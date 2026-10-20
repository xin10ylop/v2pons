"""Pricer and family statistics for analyse_14 (exact v4 replay in the manner of explore/chk/replay.py).

Model:
  - chain state after the launch tx = Initialize sqrt_p0 with L = liq_launch, then each swap of the pool in (bn, li) order;
  - our buy (X wei) lands in block B AFTER every other tx of B: our virtual state = the chain's state after its last swap with bn <= B,
    our tokens = buy_out_int(that state, L, X, fee); then 1/sqrtP += net(X)/L;
  - every later swap (bn > B, bn < S) is replayed by its own shift: a buy adds (Q96/sp_after - Q96/sp_before) to Q96/s, a sell adds
    (sp_after - sp_before) to s (exact for exact-in swaps in a single range);
  - swaps by our own relay (sender 0x2abb5653) are removed (their shift skipped); a volume-bot router buy (to 0x1cbaf24d, c1120e3d)
    whose output with our buy in front falls under its own minOut (calldata word 4) is dropped (it would revert);
  - our sell lands at the head of block S: priced on the replayed state with every swap of bn < S, eth = sell_out_int(...);
  - a pull (negative ModifyLiquidity) with bn <= S (and after our buy) = the whole stake lost + gas; a pull at or before B = no trade;
  - gas = 2 x 104,000 x base fee (the launch block's base fee from blocks_meta, else 0.02 gwei); two pool fees (fee ppm of the PoolKey,
    or the Swap event's fee for a dynamic-fee pool).
"""
import sys, json, statistics as st, collections, math
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
sys.path.insert(0, "/home/user/v2pons/src")
from load import *
import v4math
Q96 = 1 << 96
RELAY = "0x2abb5653352f6b2f3b4f4261877cd02d9e05a957"
VROUTER = "0x1cbaf24d53fe930fce8eff149fa797d2611da149"
UR = "0x8876789976decbfcbbbe364623c63652db8c0904"
STAKE = 0.0058; X = int(STAKE * 1e18); USD_PER_ETH = 15 / 0.0058
MIN_REAL = int(0.0002e18)
GAS_UNITS = 104_000
DAYS = 1_683_688 * 0.1026 / 86400      # census window


def net(x, fee): return x - (x * fee + 999_999) // 1_000_000


def wd(inp, i): return int(inp[10 + 64 * i: 10 + 64 * (i + 1)], 16)


def pct(v, qs=(0.1, 0.5, 0.9)):
    if not v: return None
    v = sorted(v); n = len(v)
    return [v[min(n - 1, int(q * n))] if q != 0.5 else st.median(v) for q in qs]


class Ctx:
    def __init__(self, pids):
        self.P = load_pools(); self.E = load_events(set(pids)); self.T = load_txs(); self.BM = load_blocks_meta()

    def basefee(self, bn):
        m = self.BM.get(bn)
        return m[1] if m else 20_000_000


def pool_fee(p, e):
    if p["fee"] & 0x800000:
        fs = [s["fee"] for s in e["swaps"]] if e else []
        return st.median(fs) if fs else 0
    return p["fee"]


def is_bot_buy(t):
    return t is not None and t.get("to") == VROUTER and t.get("selector") == "c1120e3d"


def bot_minout(t):
    inp = t.get("input") or t.get("input512")
    return wd(inp, 4)


def chain_swaps(ctx, pid):
    """the pool's swaps with our relay's removed (kept as 'skip' so the chain price pointer advances)"""
    e = ctx.E.get(pid)
    return e["swaps"] if e else []


def state_at(p, swaps, B, bn_strict=False):
    """the chain's (sqrtP, L) after every swap with bn <= B (relay swaps included: they are the chain's real state; callers that need the
    state without the relay use replay())"""
    sp, L = p["sqrt_p0"], p["liq_launch"]
    for s in swaps:
        if s["bn"] > B: break
        sp, L = s["sqrt_p"], s["liq"]
    return sp, L


def replay(ctx, p, B, S, X=X, minout_check=True, tax_ppm=0):
    """our buy of X wei after block B, sold at the head of S. Returns dict."""
    e = ctx.E.get(p["pid"]); swaps = e["swaps"] if e else []; pulls = e["pulls"] if e else []
    fee = pool_fee(p, e); lb = p["launch_block"]
    gas = 2 * GAS_UNITS * ctx.basefee(lb)
    pull = pulls[0]["bn"] if pulls else None
    if pull is not None and pull <= B:
        return {"exit": "pulled_before_buy", "ret": None, "pull": pull - lb}
    # virtual state without our relay through block B
    s = float(p["sqrt_p0"]); prev = p["sqrt_p0"]; L = p["liq_launch"]
    i = 0
    while i < len(swaps) and swaps[i]["bn"] <= B:
        x = swaps[i]
        if x["sender"] != RELAY:
            if x["a0"] < 0: s = Q96 / (Q96 / s + (Q96 / x["sqrt_p"] - Q96 / prev))
            else: s = s + (x["sqrt_p"] - prev)
        prev = x["sqrt_p"]; L = x["liq"]; i += 1
    if L <= 0:
        return {"exit": "no_liquidity", "ret": None}
    sB = int(s)
    Xp = net(X, tax_ppm)                     # a hook that takes tax_ppm of the ETH in before the pool (family 0x34c0d66f: 1.25%)
    tokens = v4math.buy_out_int(sB, L, Xp, fee)
    s = Q96 / (Q96 / s + net(Xp, fee) / L)
    dropped = []; seen = []
    while i < len(swaps) and swaps[i]["bn"] < S:
        x = swaps[i]; i += 1
        if x["sender"] == RELAY:
            prev = x["sqrt_p"]; continue
        if x["liq"] != L: L = x["liq"]
        if x["a0"] < 0:
            t = ctx.T.get(x["tx"])
            if minout_check and is_bot_buy(t):
                mo = bot_minout(t); out_us = v4math.buy_out_int(int(s), L, -x["a0"], fee)
                if out_us < mo:
                    dropped.append((x["bn"] - lb, round(out_us / mo, 5))); prev = x["sqrt_p"]; continue
            s = Q96 / (Q96 / s + (Q96 / x["sqrt_p"] - Q96 / prev))
            seen.append((x["bn"] - lb, -x["a0"] / 1e18))
        else:
            s = s + (x["sqrt_p"] - prev)
            seen.append((x["bn"] - lb, -x["a0"] / 1e18))
        prev = x["sqrt_p"]
    if pull is not None and pull <= S:
        return {"exit": "pulled_first", "ret": (-X - gas) / X, "pull": pull - lb, "B": B - lb, "S": S - lb}
    eth = net(v4math.sell_out_int(int(s), L, tokens, fee), tax_ppm)   # ASSUMED: the same hook tax on the ETH out of a sell
    return {"exit": "sold", "ret": (eth - X - gas) / X, "ret_gross": (eth - X) / X, "B": B - lb, "S": S - lb, "dropped": dropped,
            "between": seen[:6], "pull": (pull - lb) if pull else None}


def summ(rs, n_launch):
    v = [r["ret"] for r in rs if r.get("ret") is not None]
    if not v: return {"n": 0}
    pulled = sum(1 for r in rs if r.get("exit") == "pulled_first")
    m = st.mean(v); usd = m * STAKE * USD_PER_ETH
    return {"n": len(v), "mean": round(m, 5), "median": round(st.median(v), 5), "win": round(sum(1 for a in v if a > 0) / len(v), 4),
            "pulled_first": pulled, "usd_trade": round(usd, 4), "usd_day": round(usd * len(v) / DAYS, 2),
            "min": round(min(v), 4), "max": round(max(v), 4)}
