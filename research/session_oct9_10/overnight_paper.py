import sys, time, statistics as st
sys.path.insert(0, "/home/user/v2pons/src")
import v4math
from chain import *
Q96 = 1 << 96; STAKE = int(0.0012e18); GAS = 250_000 * 22_000_000; RELAY = "2abb5653352f6b2f3b4f4261877cd02d9e05a957"
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
head = int(rpc("eth_blockNumber", []), 16)
inits = logs({"address": PM, "topics": [T_INIT, None, "0x" + "0"*64]}, 83500000, head)
txs = batch([("eth_getTransactionByHash", [l["transactionHash"]]) for l in inits])
op = [l for l, t in zip(inits, txs) if t and t["input"][:10] == "0x2fcb9108" and t["to"][2:].lower() == OP]
res = {1: [], 2: []}; rows = []
for l in op:
    pid = l["topics"][1]; b0 = int(l["blockNumber"], 16); d = l["data"]; fee = W(d, 0); sp0 = W(d, 3); tick0 = sgn(W(d, 4))
    ls = sorted(logs({"address": PM, "topics": [[T_SWAP, T_ML], pid]}, b0, min(b0 + 20000, head)), key=lambda x: (int(x["blockNumber"], 16), int(x["logIndex"], 16)))
    adds = [(sgn(W(x["data"], 0)), sgn(W(x["data"], 1)), sgn(W(x["data"], 2))) for x in ls if x["topics"][0] == T_ML and sgn(W(x["data"], 2)) > 0]
    liq = v4math.active_liquidity(tick0, adds)
    sw = [(int(x["blockNumber"], 16), s128(W(x["data"], 0)), W(x["data"], 2), W(x["data"], 3)) for x in ls if x["topics"][0] == T_SWAP and x["topics"][2][-40:] != RELAY]   # the pool without us
    pulls = [int(x["blockNumber"], 16) for x in ls if x["topics"][0] == T_ML and sgn(W(x["data"], 2)) < 0]; pull = min(pulls) if pulls else None
    real = [x for x in sw if x[1] <= -2e14]
    if not real or real[0][0] - b0 > 150: rows.append((b0, fee, None)); continue
    out = {}
    for land in (1, 2):
        B = real[0][0] + land; prev = [x for x in sw if x[0] < B]; sp, L = (prev[-1][2], prev[-1][3]) if prev else (sp0, liq)
        tok = v4math.buy_out_int(sp, L, STAKE, fee); xn = STAKE - (STAKE * fee + 999_999) // 1_000_000
        ret_at = lambda spc, Lc: (v4math.sell_out_int(int(Q96 / (Q96 / spc + xn / Lc)), Lc, tok, fee) - STAKE - GAS) / STAKE
        send = B + 2
        for x in sw:
            if B <= x[0] <= B + 2 and x[1] < 0 and ret_at(x[2], x[3]) >= 0.01: send = x[0]; break
        landb = send + 2
        if pull is not None and pull <= landb: r = -1.0
        else:
            pv = [x for x in sw if x[0] <= landb - 1]; r = ret_at(pv[-1][2], pv[-1][3])
        out[land] = r; res[land].append(r)
    rows.append((b0, fee, out))
print(f"the operator's launches through its original launcher since Oct 8 21:30: {len(op)}")
for b0, fee, out in rows:
    print(f"  block {b0} fee {fee/1e4:.3f}%: " + ("no real-size buy" if out is None else f"follow, landing first buy +1: {out[1]:+.1%}, +2: {out[2]:+.1%}"))
for land in (1, 2):
    v = res[land]; print(f"FOLLOW + 0.3 exit, landing first buy +{land}: n {len(v)}, mean {st.mean(v):+.2%}, median {st.median(v):+.2%}, positive {sum(1 for x in v if x > 0)}/{len(v)}, worst {min(v):+.1%}")
