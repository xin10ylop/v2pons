"""today's relay trades: the swaps on each pool from the first real buy to our sell (blocks relative to the first >= 0.0002 ETH buy)"""
import sys, time
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import *
RELAY = "2abb5653352f6b2f3b4f4261877cd02d9e05a957"
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
head = int(rpc("eth_blockNumber", []), 16)
START = 82878144 + int(86400 / 0.103) - 2000
ours = logs({"address": PM, "topics": [T_SWAP, None, "0x" + "0" * 24 + RELAY]}, START, head)
for pid in sorted({l["topics"][1] for l in ours}, key=lambda p: min(int(l["blockNumber"], 16) for l in ours if l["topics"][1] == p)):
    B = min(int(l["blockNumber"], 16) for l in ours if l["topics"][1] == pid)
    il = logs({"address": PM, "topics": [T_INIT, pid]}, B - 400, B)
    b0 = int(il[0]["blockNumber"], 16) if il else None
    ls = sorted(logs({"address": PM, "topics": [[T_SWAP, T_ML], pid]}, B - 400, B + 20), key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
    sw = [(int(l["blockNumber"], 16), s128(W(l["data"], 0)), l["topics"][2][-40:] == RELAY, l["transactionHash"]) for l in ls if l["topics"][0] == T_SWAP]
    real = [x for x in sw if x[1] <= -int(0.0002e18) and not x[2]]
    T = real[0][0] if real else None
    txs = dict(zip([x[3] for x in sw], batch([("eth_getTransactionByHash", [x[3]]) for x in sw])))
    print(f"pool {pid[:10]} launch +0={b0} T=+{T - b0 if T and b0 else None} our buy T+{B - T if T else None}")
    for bn, a0, us, h in sw:
        if T and T <= bn <= B + 12:
            print(f"   T+{bn - T:3d} {'US ' if us else '   '}{'buy ' if a0 < 0 else 'sell'} {abs(a0) / 1e18:.4f}  from {txs[h]['from'][:10]}")
    for l in ls:
        if l["topics"][0] == T_ML and sgn(W(l["data"], 2)) < 0:
            print(f"   T+{int(l['blockNumber'], 16) - T:3d} PULL")
