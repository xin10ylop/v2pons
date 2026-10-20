import json, sys, collections, statistics as st
sys.path.insert(0, "/home/user/v2pons/src")
import v4math
from chain import *
Q96 = 1 << 96; STAKE = int(0.0012e18); GAS = 250_000 * 22_000_000
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
head = int(rpc("eth_blockNumber", []), 16)
inits = logs({"address": PM, "topics": [T_INIT, None, "0x" + "0"*64]}, 83394000, head)
txs = batch([("eth_getTransactionByHash", [l["transactionHash"]]) for l in inits])
P = {}
for l, t in zip(inits, txs):
    d = l["data"]
    if d[2+64*2+24:2+64*3] != "0"*40: continue                                   # hooked pools: the relay trades no-hook only
    fam = "operator (0x2fcb9108)" if t["input"][:10] == "0x2fcb9108" else f"{t['to'][:10]} {t['input'][:10]}"
    P[l["topics"][1]] = {"b0": int(l["blockNumber"], 16), "fee": W(d, 0), "sp0": W(d, 3), "tick0": sgn(W(d, 4)), "fam": fam}
pids = sorted(P, key=lambda p: P[p]["b0"]); ev = collections.defaultdict(list)
for i in range(0, len(pids), 60):
    bt = pids[i:i+60]; lo = min(P[p]["b0"] for p in bt); hi = min(max(P[p]["b0"] for p in bt) + 1500, head)
    for a in range(lo, hi + 1, 99999):
        for l in logs({"address": PM, "topics": [[T_SWAP, T_ML], bt]}, a, min(a + 99998, hi)): ev[l["topics"][1]].append(l)
def trade(p, B, exit_rule):
    """$3 at the head of block B; exit_rule(sw_after) -> landing block; -100% if the pull lands first"""
    q = P[p]; ls = sorted(ev[p], key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
    adds = [(sgn(W(l["data"], 0)), sgn(W(l["data"], 1)), sgn(W(l["data"], 2))) for l in ls if l["topics"][0] == T_ML and sgn(W(l["data"], 2)) > 0 and int(l["blockNumber"], 16) < B]
    liq0 = v4math.active_liquidity(q["tick0"], adds)
    sw = [(int(l["blockNumber"], 16), s128(W(l["data"], 0)), W(l["data"], 2), W(l["data"], 3)) for l in ls if l["topics"][0] == T_SWAP]
    pulls = [int(l["blockNumber"], 16) for l in ls if l["topics"][0] == T_ML and sgn(W(l["data"], 2)) < 0]; pull = min(pulls) if pulls else None
    if pull is not None and pull <= B or liq0 <= 0: return None
    prev = [x for x in sw if x[0] < B]; sp, L = (prev[-1][2], prev[-1][3]) if prev else (q["sp0"], liq0)
    if L < 1e21: return None
    fee = q["fee"]; tok = v4math.buy_out_int(sp, L, STAKE, fee); xn = STAKE - (STAKE * fee + 999_999) // 1_000_000
    ret_at = lambda spc, Lc: (v4math.sell_out_int(int(Q96 / (Q96 / spc + xn / Lc)), Lc, tok, fee) - STAKE - GAS) / STAKE
    land = exit_rule(B, [x for x in sw if x[0] >= B], ret_at)
    if pull is not None and pull <= land: return -1.0
    pv = [x for x in sw if x[0] <= land - 1]; spl, Ll = (pv[-1][2], pv[-1][3]) if pv else (sp, L)
    return ret_at(spl, Ll)
def tp_rule(maxwait):
    def r(B, after, ret_at):
        for x in after:
            if x[0] - B <= maxwait and x[1] < 0 and ret_at(x[2], x[3]) >= 0.01: return x[0] + 2
        return B + maxwait + 2
    return r
# 1. the first seat on the operator's new launches: buy at launch + k, sell 2 blocks after the burst (take profit), at the latest +12 after our buy
print("1. THE FIRST SEAT on the operator's new launches (no reaction to us assumed): $3 at launch + k, sold on the burst")
for k in (2, 3, 4, 5):
    v = [r for p in pids if P[p]["fam"].startswith("operator") for r in [trade(p, P[p]["b0"] + k, tp_rule(12))] if r is not None]
    print(f"   buy at launch +{k}: n {len(v)}, mean {st.mean(v):+.1%}, median {st.median(v):+.1%}, positive {sum(1 for x in v if x > 0)}/{len(v)}, worst {min(v):+.1%}")
# 2. the old trade on every family: buy 2 blocks after the first real buy, the 0.3 exit
print("\n2. THE OLD TRADE on every launch family since 14:45 (land first real buy + 2, take profit, out by +4)")
fam = collections.defaultdict(list)
for p in pids:
    sw = sorted((int(l["blockNumber"], 16), s128(W(l["data"], 0))) for l in ev[p] if l["topics"][0] == T_SWAP)
    real = [x for x in sw if x[1] <= -2e14 and x[0] - P[p]["b0"] <= 150]
    if not real: continue
    r = trade(p, real[0][0] + 2, tp_rule(2))
    if r is not None: fam[P[p]["fam"]].append((r, P[p]["fee"]))
for f, v in sorted(fam.items(), key=lambda kv: -len(kv[1])):
    rs = [r for r, _ in v]
    print(f"   {f:28s} n {len(rs):3d} fee {collections.Counter(fe/1e4 for _, fe in v).most_common(2)}: mean {st.mean(rs):+.2%}, positive {sum(1 for x in rs if x > 0)}/{len(rs)}, worst {min(rs):+.1%}")
