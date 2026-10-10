import json, sys
sys.path.insert(0, "/home/user/v2pons/src")
import v4math
from chain import *
D = json.load(open("oct8.json")); pools = D["pools"]; ev = D["ev"]
RELAY = "2abb5653352f6b2f3b4f4261877cd02d9e05a957"
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
mine = sorted([pid for pid, ls in ev.items() if any(l["topics"][0] == T_SWAP and l["topics"][2][-40:] == RELAY for l in ls)], key=lambda p: pools[p]["bn"])
STAKE = int(0.0012e18)
for n, pid in enumerate(mine, 1):
    p = pools[pid]; fee = p["fee"]
    ls = sorted(ev[pid], key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
    add = [l for l in ls if l["topics"][0] == T_ML and sgn(W(l["data"], 2)) > 0][0]
    liq = v4math.active_liquidity(p["tick0"], [(sgn(W(add["data"], 0)), sgn(W(add["data"], 1)), sgn(W(add["data"], 2)))])
    sp = p["sqrtP0"]; sw = [l for l in ls if l["topics"][0] == T_SWAP]
    trig_only = None; sp_all = sp; first_real = None
    for l in sw:
        a0 = s128(W(l["data"], 0)); a1 = s128(W(l["data"], 1))
        if l["topics"][2][-40:] == RELAY:
            pe = v4math.buy_out_int(sp_all, liq, STAKE, fee); pt = v4math.buy_out_int(trig_only, liq, STAKE, fee)
            print(f"T{n}: actual {a1}  feed-all-buys {pe} (rel {(pe-a1)/a1:+.2e})  engine trigger-only {pt} (rel {(pt-a1)/a1:+.2e})")
            break
        x = -a0; xn = x - (x * fee + 999_999) // 1_000_000
        sp_all = int(v4math.sqrt_after_buy(sp_all, liq, xn))
        if first_real is None and x >= 2e14:
            first_real = l; trig_only = int(v4math.sqrt_after_buy(p["sqrtP0"], liq, xn))
