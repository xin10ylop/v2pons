import json, sys
sys.path.insert(0, "/home/user/v2pons/src")
import v4math
from chain import *
D = json.load(open("oct8.json")); pools = D["pools"]; ev = D["ev"]
RELAY = "2abb5653352f6b2f3b4f4261877cd02d9e05a957"
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
mine = sorted([pid for pid, ls in ev.items() if any(l["topics"][0] == T_SWAP and l["topics"][2][-40:] == RELAY for l in ls)], key=lambda p: pools[p]["bn"])
cases = {0: (83341743 + 6, 25, 0.01708e18, 1.6511e25), 2: (83342495 + 4, 35, 0.06835e18, 6.2826e25)}
for i, (bn, idx, x, mn) in cases.items():
    pid = mine[i]; p = pools[pid]; fee = p["fee"]
    ls = sorted(ev[pid], key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
    sw = [l for l in ls if l["topics"][0] == T_SWAP and int(l["blockNumber"], 16) <= bn]
    last = sw[-1]; sp, L = W(last["data"], 2), W(last["data"], 3)
    if int(last["blockNumber"], 16) == bn: print("note: a swap in the same block before?", last["logIndex"])
    got_now = v4math.buy_out_int(sp, L, int(x), fee)
    # what it would have got with our buy not in the pool: replay every swap except ours
    add = [l for l in ls if l["topics"][0] == T_ML and sgn(W(l["data"], 2)) > 0][0]
    liq = v4math.active_liquidity(p["tick0"], [(sgn(W(add["data"], 0)), sgn(W(add["data"], 1)), sgn(W(add["data"], 2)))])
    s = p["sqrtP0"]
    for l in sw:
        if l["topics"][2][-40:] == RELAY: continue
        a = -s128(W(l["data"], 0)); s = int(v4math.sqrt_after_buy(s, liq, a - (a * fee + 999_999) // 1_000_000))
    got_without_us = v4math.buy_out_int(s, liq, int(x), fee)
    print(f"T{i+1}: reverted buy {x/1e18:.5f} ETH, minOut {mn:.4e}; at the real state it gets {got_now:.4e} ({'>= minOut' if got_now >= mn else 'BELOW minOut'}); without our buy {got_without_us:.4e}; minOut/got {mn/got_now:.4f}")
    # the crowd's minOut vs got for its successful buys: the slippage they allow
for pid in mine:
    pass
