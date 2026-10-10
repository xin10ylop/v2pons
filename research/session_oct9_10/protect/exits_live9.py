"""today's (Oct 9) live relay trades: buy block, sell block, pull block, from the chain"""
import sys, time
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import *
RELAY = "2abb5653352f6b2f3b4f4261877cd02d9e05a957"
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
head = int(rpc("eth_blockNumber", []), 16)
START = 82878144 + int(86400 / 0.103) - 2000           # ~ Oct 9 00:00 UTC
ours = logs({"address": PM, "topics": [T_SWAP, None, "0x" + "0" * 24 + RELAY]}, START, head)
pids = sorted({l["topics"][1] for l in ours}, key=lambda p: min(int(l["blockNumber"], 16) for l in ours if l["topics"][1] == p))
for pid in pids:
    mine = sorted([l for l in ours if l["topics"][1] == pid], key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
    B = int(mine[0]["blockNumber"], 16)
    ts = int(rpc("eth_getBlockByNumber", [hex(B), False])["timestamp"], 16)
    ml = logs({"address": PM, "topics": [T_ML, pid]}, B - 3000, min(B + 3000, head))
    pulls = sorted(int(l["blockNumber"], 16) for l in ml if sgn(W(l["data"], 2)) < 0)
    legs = [(int(l["blockNumber"], 16) - B, s128(W(l["data"], 0)) / 1e18) for l in mine]
    print(time.strftime("%m-%d %H:%M:%S", time.gmtime(ts)), pid[:12], "legs (blocks after buy, a0 ETH):", legs, "pull after buy:", [p - B for p in pulls[:2]])
