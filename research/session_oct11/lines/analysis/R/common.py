"""Shared constants and helpers for the ride study (R)."""
import sys, json, math, statistics as st, collections
sys.path.insert(0, "/home/user/v2pons/src")
import v4math
Q96 = 1 << 96
USD = 2570.0
GAS_USD = 0.02
BOT = "0x1cbaf24d53fe930fce8eff149fa797d2611da149"
UR = "0x8876789976decbfcbbbe364623c63652db8c0904"
OURS = "0xab5a34c3f41e57fdee1a1d6f19d3e21f46df3ea8"
RELAY = "0x2abb5653352f6b2f3b4f4261877cd02d9e05a957"
SENTINEL = "0xe71a69f434a719cd5afa411568b69716aab3b84a"
T0_CENSUS = 1791121980          # 2026-10-04 13:53 UTC-ish; day index = (ts - census start) // 86400
CENSUS_START = 1791121920       # Oct 4 13:52 UTC
NEW30 = 1791692539              # 2026-10-11 04:22:19 UTC (the 3.0 line's late-bot regime)
FEE_CHANGE = 1791732720         # 2026-10-11 15:32:00 UTC (2.4333 fee 2500 -> 5000)
DECOY_FILL = 1791736080         # 2026-10-11 16:28:00 UTC


def utc(ts): import time; return time.strftime("%m-%d %H:%M", time.gmtime(ts))


def net(x, fee): return x - (x * fee + 999_999) // 1_000_000


def buy_state(sp, L, eth_in, fee):
    """integer: new sqrtP after a buy of eth_in gross (PoolManager rounding: up)"""
    x = net(eth_in, fee)
    num = L * sp; den = L + (x * sp) // Q96
    return (num + den - 1) // den


def sell_state(sp, L, tok_in, fee):
    return sp + (net(tok_in, fee) * Q96) // L


def pct(v, p):
    v = sorted(v)
    if not v: return None
    return v[min(len(v) - 1, int(p * len(v)))]


def p1059(v):
    return (pct(v, .1), pct(v, .5), pct(v, .9)) if v else (None, None, None)


def replay(sw, start_sp, start_L, B, S, q_wei, fee_ours, fee_pool, pull_bn, skip=None):
    """our buy q at the HEAD of block B, sell at the HEAD of block S. sw: list of swaps sorted (bn, li), each with bn, buy, q (ETH abs),
    t (token abs), sp, L (after). Others' swaps in blocks [B, S) are re-applied by amount (buys ETH in, sells tokens in) at fee_pool.
    skip(s, sp, L) -> True drops that swap (e.g. a bot buy reverting on its minOut). Returns dict(ret, why)."""
    if pull_bn is not None and pull_bn < B:
        return {"ret": None, "why": "pulled_before_buy"}
    pre = [s for s in sw if s["bn"] < B]
    sp, L = (pre[-1]["sp"], pre[-1]["L"]) if pre else (start_sp, start_L)
    if L == 0: return {"ret": None, "why": "no_liquidity"}
    tokens = v4math.buy_out_int(sp, L, q_wei, fee_ours)
    sp = buy_state(sp, L, q_wei, fee_ours)
    if pull_bn is not None and pull_bn <= S:
        return {"ret": -1.0 - GAS_USD / (q_wei / 1e18 * USD), "why": "pulled", "tokens": tokens}
    dropped = 0
    for s in sw:
        if s["bn"] < B: continue
        if s["bn"] >= S: break
        if s["L"] != L and s["L"] > 0: L = s["L"]
        if skip is not None and skip(s, sp, L):
            dropped += 1; continue
        if s["buy"]: sp = buy_state(sp, L, s["q"], fee_pool)
        else: sp = sell_state(sp, L, s["t"], fee_pool)
    eth = v4math.sell_out_int(sp, L, tokens, fee_ours)
    return {"ret": (eth - q_wei) / q_wei - GAS_USD / (q_wei / 1e18 * USD), "why": "sold", "dropped": dropped}


def summ(rets, q_eth, rate_day=None, share=1.0):
    v = [r["ret"] for r in rets if r["ret"] is not None]
    if not v: return {"n": 0}
    m = st.mean(v); pulled = sum(1 for r in rets if r.get("why") == "pulled")
    usd = m * q_eth * USD
    o = {"n": len(v), "mean%": round(100 * m, 2), "med%": round(100 * st.median(v), 2), "win": round(sum(1 for a in v if a > 0) / len(v), 3),
         "worst%": round(100 * min(v), 1), "pulled": pulled, "pulled%": round(100 * pulled / len(v), 1), "usd_tr": round(usd, 4)}
    if rate_day is not None: o["usd_day"] = round(usd * rate_day * share, 2)
    return o
