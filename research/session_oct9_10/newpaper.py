import json, sys, time, statistics as st
sys.path.insert(0, "/home/user/v2pons/src")
import v4math
from chain import *
Q96 = 1 << 96
rows = json.load(open("newlaunch.json"))[1:]                      # the 40 new-style launches (the first row is the old launcher's 14:32)
head = int(rpc("eth_blockNumber", []), 16)
pids = [p for p, _ in rows]; b0s = dict(rows); ev = {p: [] for p in pids}
for i in range(0, len(pids), 40):
    bt = pids[i:i+40]; lo = min(b0s[p] for p in bt); hi = min(max(b0s[p] for p in bt) + 12000, head)
    for a in range(lo, hi + 1, 99999):
        for l in logs({"address": PM, "topics": [[T_SWAP, T_ML, T_INIT], bt]}, a, min(a + 99998, hi)): ev[l["topics"][1]].append(l)
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
STAKE = int(0.0012e18); GAS = 250_000 * 22_000_000
out = []
for p in pids:
    ls = sorted(ev[p], key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16))); b0 = b0s[p]
    init = [l for l in ls if l["topics"][0] == T_INIT][0]; fee = W(init["data"], 0); sp0 = W(init["data"], 3); tick0 = sgn(W(init["data"], 4))
    adds = [(sgn(W(l["data"], 0)), sgn(W(l["data"], 1)), sgn(W(l["data"], 2))) for l in ls if l["topics"][0] == T_ML and sgn(W(l["data"], 2)) > 0]
    liq = v4math.active_liquidity(tick0, adds)
    sw = [(int(l["blockNumber"], 16), s128(W(l["data"], 0)), W(l["data"], 2), W(l["data"], 3)) for l in ls if l["topics"][0] == T_SWAP]
    pulls = [int(l["blockNumber"], 16) for l in ls if l["topics"][0] == T_ML and sgn(W(l["data"], 2)) < 0]; pull = min(pulls) if pulls else None
    real = [x for x in sw if x[1] <= -2e14]
    if not real: out.append((p, fee, liq, None, None, pull and pull - b0, None)); continue
    f = real[0][0]; B = f + 2
    prev = [x for x in sw if x[0] < B]; sp, L = (prev[-1][2], prev[-1][3]) if prev else (sp0, liq)
    tok = v4math.buy_out_int(sp, L, STAKE, fee); xn = STAKE - (STAKE * fee + 999_999) // 1_000_000
    def ret_at(spc, Lc):
        s_ours = int(Q96 / (Q96 / spc + xn / Lc)); return (v4math.sell_out_int(s_ours, Lc, tok, fee) - STAKE - GAS) / STAKE
    send = B + 2
    for x in sw:
        if B <= x[0] <= B + 2 and x[1] < 0 and ret_at(x[2], x[3]) >= 0.01: send = x[0]; break
    land = send + 2
    if pull is not None and pull <= land: r = -1.0
    else:
        pv = [x for x in sw if x[0] <= land - 1]; r = ret_at(pv[-1][2], pv[-1][3])
    behind = [x[0] - f for x in real[1:] if x[0] - f <= 8]
    out.append((p, fee, liq, f - b0, behind, (pull - f) if pull else None, r))
print("pool          fee      liquidity  first buy  crowd buys after it (blocks)  pull after first buy   paper (land +2, 0.3 exit)")
for p, fee, liq, fo, behind, pg, r in out:
    print(f"{p[:12]}  {fee/1e4:.3f}%  {liq:9.3g}  {'+' + str(fo) if fo is not None else 'none':>7}    {str(behind):30s} {str(pg):>10}            {'' if r is None else f'{r:+.1%}'}")
v = [r for *_, r in out if r is not None]
print(f"\n{len(out)} launches, {len(v)} with a real-size first buy; paper mean {st.mean(v):+.2%}, median {st.median(v):+.2%}, positive {sum(1 for r in v if r > 0)}/{len(v)}, worst {min(v):+.1%}")
print("eligible for the engine (fee < 1%, liquidity >= 1e21):", sum(1 for _, fee, liq, *_ in out if fee < 10000 and liq >= 1e21), "of", len(out))

print("\nthe crowd's flow after its first block, per launch: buys and ETH in blocks first+1..+30, +31..+300, and until the pull")
agg = {"a": [], "b": [], "c": []}
for p in pids:
    ls = ev[p]; sw = [(int(l["blockNumber"], 16), s128(W(l["data"], 0))) for l in ls if l["topics"][0] == T_SWAP]
    pulls = [int(l["blockNumber"], 16) for l in ls if l["topics"][0] == T_ML and sgn(W(l["data"], 2)) < 0]; pull = min(pulls) if pulls else head
    real = sorted(x for x in sw if x[1] <= -2e14)
    if not real: continue
    f = real[0][0]
    for k, lo, hi in (("a", 1, 30), ("b", 31, 300), ("c", 301, 10**9)):
        bs = [-x[1] / 1e18 for x in real if lo <= x[0] - f <= hi and x[0] < pull]; agg[k].append((len(bs), sum(bs)))
for k, name in (("a", "+1..+30"), ("b", "+31..+300"), ("c", "+301..pull")):
    print(f"  {name:11s} median buys {st.median(n for n, _ in agg[k]):4.0f}, median ETH {st.median(e for _, e in agg[k]):.3f}, launches with any buy {sum(1 for n, _ in agg[k] if n)}/{len(agg[k])}")
