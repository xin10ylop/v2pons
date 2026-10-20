"""Stage 5: a $5 front that follows the candidate, replayed on the slice's 3.0 pools with the operator's reaction modelled.
Fire: the first 1,444-byte PositionManager launch (any line) seen while the pool is open (after L+g, before the bot's buy at T is seen).
Our buy lands at the head of block B = signal + k (k = 1, 2: the engine reads the feed and lands 1-2 blocks after it decides).
Sell: sent on seeing the bot's buy at T, lands at the head of S = T + j (j = 1, 2). A buy that lands at or after T (too late) is sold at B + 1.
Reaction (our buy is 0.0019 ETH, non-dust): a pull at B + lag, lag = 3 (the minimum observed after a pre-T buy) or 5 (their median:
0x8c009ea5 x22, 0x7ae81404 x4, our probe; prior study R) or 12 (this slice's median after post-T outside buys). A pull at or before T
means no bot buy (as in all 27 prior pre-T cases, where the bot never bought) -> -100%; a pull after T but at or before S -> -100%.
The pool's real pull applies too. Swaps of others in [B, S) are re-applied by amount; the bot's buy reverts if its output falls below its
minOut (word 4 of c1120e3d). $: stake $5 at ETH $2,570, gas $0.15 a round trip (the live -100% trade cost $5.15)."""
import json, collections, statistics as st, sys
sys.path.insert(0, "/home/user/v2pons/src")
import v4math
from lib import *
Q96 = 1 << 96; USD = 2570.0; STAKE = 5.0; GAS = 0.15; QW = int(STAKE / USD * 1e18); FEE = 10000
P = json.load(open("s2_parsed.json"))["pools"]; S = json.load(open("s1_slice.json"))
sig = collections.defaultdict(list)
for r in S["launches"]:
    if r["is1444"]: sig[r["bn"]].append(r)
def net(x, fee): return x - (x * fee + 999_999) // 1_000_000
def buy_state(sp, L, eth_in, fee):
    x = net(eth_in, fee); num = L * sp; den = L + (x * sp) // Q96
    return (num + den - 1) // den
def sell_state(sp, L, tok_in, fee): return sp + (net(tok_in, fee) * Q96) // L
# validation: the bot's first buy re-applied from the state before it reproduces its logged sqrtP
errs = []
for p in P:
    sw = p["sw"]; i = next(k for k, s in enumerate(sw) if s["bot"])
    sp0, L0 = (sw[i - 1]["sp"], sw[i - 1]["Lq"]) if i > 0 else (SQRT30, p["L0"])
    if sw[i]["Lq"] != L0: errs.append(("L changed", p["pid"][:10])); continue
    errs.append(abs(buy_state(sp0, L0, sw[i]["q"], FEE) - sw[i]["sp"]) / sw[i]["sp"])
num = [e for e in errs if isinstance(e, float)]
print(f"validation: the bot's first buy re-applied in {len(num)} pools, max relative sqrtP error {max(num):.2e}; other: {[e for e in errs if not isinstance(e, float)]}")
slack = [s["t"] / s["minout"] for p in P for s in p["sw"] if s["bot"] and s["minout"] and s["off"] == p["T"]]
print(f"the bot's first buy: tokens out / minOut p10/50/90 {pct(slack,.1):.4f}/{pct(slack,.5):.4f}/{pct(slack,.9):.4f} min {min(slack):.4f}")

def replay(p, B, Sb, pull_bn):
    """our QW at the head of block B, sold at the head of block Sb; pull_bn: first pull block (reaction or real)"""
    sw = p["sw"]
    if pull_bn is not None and pull_bn <= Sb: return {"ret": -1.0, "why": "pulled", "usd": -STAKE - GAS}
    pre = [s for s in sw if s["bn"] < B]
    sp, L = (pre[-1]["sp"], pre[-1]["Lq"]) if pre else (SQRT30, p["L0"])
    tokens = v4math.buy_out_int(sp, L, QW, FEE); sp = buy_state(sp, L, QW, FEE); dropped = 0
    for s in sw:
        if s["bn"] < B: continue
        if s["bn"] >= Sb: break
        if s["Lq"] != L and s["Lq"] > 0: L = s["Lq"]
        if s["bot"] and s["minout"] and v4math.buy_out_int(sp, L, s["q"], FEE) < s["minout"]: dropped += 1; continue
        sp = buy_state(sp, L, s["q"], FEE) if s["buy"] else sell_state(sp, L, s["t"], FEE)
    eth = v4math.sell_out_int(sp, L, tokens, FEE); ret = (eth - QW) / QW
    return {"ret": ret, "why": "sold" + ("+botbuy-reverted" if dropped else ""), "usd": ret * STAKE - GAS}

def trade(p, b, k, j, lag):
    T = p["Tbn"]; B = b + k
    if B >= T: Sb = B + 1                       # too late: lands behind the bot's buy, sold on the next block
    else: Sb = T + j
    pulls = [x for x in (None if lag is None else B + lag, p["pullbn"]) if x is not None]
    pull = min(pulls) if pulls else None
    if lag is not None and B < T and B + lag <= T: return {"ret": -1.0, "why": "pulled before T (no bot buy)", "usd": -STAKE - GAS, "B": B - T, "S": Sb - T}
    r = replay(p, B, Sb, pull); r.update(B=B - T, S=Sb - T); return r

def summ(rs, npools):
    v = [r["ret"] for r in rs]
    if not v: return "no trades"
    usd = [r["usd"] for r in rs]
    return (f"trades {len(v):2d} ({100 * len(v) / npools:4.1f}% of pools): mean {100 * st.mean(v):+7.1f}%  median {100 * st.median(v):+7.1f}%  win {sum(1 for x in v if x > 0)}/{len(v)}  "
            f"pulled {sum(1 for r in rs if r['why'].startswith('pulled'))}  worst {100 * min(v):+.0f}%  $/trade {st.mean(usd):+.3f}  $ total {sum(usd):+.2f}  $/pool {sum(usd) / npools:+.3f}")
n = len(P)
out = {}
print(f"\nn pools {n}; a $5 front = {QW / 1e18:.6f} ETH; reaction lags tested: none / 12 / 5 / 3")
for g in (1, 16, 24):
    for k in (1, 2):
        for j in (1, 2):
            print(f"\n== gate L+{g}, buy lands signal+{k}, sell lands T+{j}")
            for lag in (None, 12, 5, 3):
                rs = []
                for p in P:
                    bs = [b for b in range(p["L"] + max(1, g), p["Tbn"]) if b in sig]
                    if not bs: continue
                    r = trade(p, bs[0], k, j, lag); r["pid"] = p["pid"][:10]; r["d"] = p["Tbn"] - bs[0]; rs.append(r)
                out[f"g{g}k{k}j{j}lag{lag}"] = rs
                print(f"  reaction {'none' if lag is None else 'pull at buy+' + str(lag):16s} {summ(rs, n)}")
# detail of the main case
print("\nper trade, gate L+1, k=1, j=1 (d = T - signal block; B, S relative to T):")
for lag in (None, 5, 3):
    print(f"  reaction {lag}:", [(r["pid"], r["d"], r["B"], r["S"], round(100 * r["ret"], 1), r["why"]) for r in out[f"g1k1j1lag{lag}"]])
# the oracle: only the pools whose signal sits at d 1..4 (as if the engine knew the signal was the one 'shortly before T')
print("\nthe oracle case: only the pools with a signal at d 1..4, buy at signal+k, sell T+j")
for k in (1, 2):
    for j in (1, 2):
        for lag in (None, 5, 3):
            rs = []
            for p in P:
                bs = [b for b in range(p["Tbn"] - 4, p["Tbn"]) if b in sig and b > p["L"]]
                if not bs: continue
                r = trade(p, bs[-1], k, j, lag); r["pid"] = p["pid"][:10]; r["d"] = p["Tbn"] - bs[-1]; rs.append(r)
            print(f"  k={k} j={j} reaction {'none' if lag is None else 'buy+' + str(lag):8s} {summ(rs, n)} | {[(r['pid'], r['d'], round(100 * r['ret'], 1), r['why']) for r in rs]}")
# the best case for a front at all: buy at exactly T-1 in every pool (a perfect predictor), sell T+1, for scale
print("\nfor scale, a perfect T predictor (buy lands at T-1 in every pool, sell T+1):")
for lag in (None, 5, 3):
    rs = [dict(trade(p, p["Tbn"] - 2, 1, 1, lag), pid=p["pid"][:10]) for p in P]
    print(f"  reaction {'none' if lag is None else 'buy+' + str(lag):8s} {summ(rs, n)}")
json.dump(out, open("s5_front.json", "w"))
