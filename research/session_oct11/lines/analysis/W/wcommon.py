"""shared: V3 log -> analyst C compact rows"""
import os
from eth_utils import keccak
tp = lambda s: "0x" + keccak(text=s).hex()
T_SW = tp("Swap(address,address,int256,int256,uint160,uint128,int24)"); T_MI = tp("Mint(address,address,int24,int24,uint128,uint256,uint256)")
T_BU = tp("Burn(address,int24,int24,uint128,uint256,uint256)")
CROWD_SHAPES = {("3593564c", 484), ("a0193551", 452), ("49f74a5d", 452)}
UR = "0x8876789976decbfcbbbe364623c63652db8c0904"
def S(x): x = int(x, 16); return x - (1 << 256) if x >> 255 else x
def W(d, i): return d[2 + 64 * i: 2 + 64 * (i + 1)]
def compact(l):
    t = l["topics"]; d = l["data"]; bn = int(l["blockNumber"], 16); ti = int(l["transactionIndex"], 16); li = int(l["logIndex"], 16); tx = l["transactionHash"]; a = l["address"].lower()
    if t[0] == T_SW: return ["s", bn, ti, li, a, "0x" + t[1][-40:], "0x" + t[2][-40:], S(W(d, 0)), S(W(d, 1)), int(W(d, 2), 16), int(W(d, 3), 16), S(W(d, 4)), tx]
    if t[0] == T_MI: return ["mi", bn, ti, li, a, "0x" + t[1][-40:], S(t[2]), S(t[3]), int(W(d, 1), 16), int(W(d, 2), 16), int(W(d, 3), 16), tx]
    if t[0] == T_BU: return ["b", bn, ti, li, a, "0x" + t[1][-40:], S(t[2]), S(t[3]), int(W(d, 0), 16), int(W(d, 1), 16), int(W(d, 2), 16), tx]
