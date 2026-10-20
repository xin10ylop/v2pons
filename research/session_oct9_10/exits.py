import json, sys
sys.path.insert(0, "/home/user/v2pons/src")
import v4math
from chain import *
D = json.load(open("oct8.json")); pools = D["pools"]; ev = D["ev"]
RELAY = "2abb5653352f6b2f3b4f4261877cd02d9e05a957"
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
mine = sorted([pid for pid, ls in ev.items() if any(l["topics"][0] == T_SWAP and l["topics"][2][-40:] == RELAY for l in ls)], key=lambda p: pools[p]["bn"])
GAS_ETH = 2 * 110000 * 0.0201e9 / 1e18   # two swaps at the base fee
print("trade fee | actual | sell lands at buy+k: priced after every other swap up to and including block buy+k-1 (k=1..7); X = pull landed at or before")
for n, pid in enumerate(mine, 1):
    p = pools[pid]; fee = p["fee"]
    ls = sorted(ev[pid], key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
    sw = [(int(l["blockNumber"], 16), int(l["logIndex"], 16), l["topics"][2][-40:], s128(W(l["data"], 0)), s128(W(l["data"], 1)), W(l["data"], 2), W(l["data"], 3)) for l in ls if l["topics"][0] == T_SWAP]
    pull = min(int(l["blockNumber"], 16) for l in ls if l["topics"][0] == T_ML and sgn(W(l["data"], 2)) < 0)
    ours = [x for x in sw if x[2] == RELAY]; buy, sell = ours[0], ours[1]; B = buy[0]
    eth_in = -buy[3]; tok = buy[4]; actual = (sell[3] - eth_in) / eth_in
    row = []
    for k in range(1, 8):
        if B + k > pull or (B + k == pull):
            row.append("   X   " if B + k > pull else "  =pull"); continue
        prev = [x for x in sw if x[2] != RELAY and (x[0], x[1]) > (buy[0], buy[1]) and x[0] <= B + k - 1]
        sp, L = (prev[-1][5], prev[-1][6]) if prev else (buy[5], buy[6])
        out = v4math.sell_out_int(sp, L, tok, fee)
        row.append(f"{(out - eth_in - GAS_ETH) / eth_in:+6.1%} ")
    behind = [(x[0] - B, round(-x[3] / 1e18, 4)) for x in sw if x[2] != RELAY and (x[0], x[1]) > (buy[0], buy[1]) and x[0] < pull and x[3] < 0]
    print(f"T{n} {fee/1e4:.4f}% | actual {actual:+6.1%} (sell +{sell[0]-B}, pull +{pull-B}) | " + " ".join(row) + f" | crowd behind us: {behind}")
