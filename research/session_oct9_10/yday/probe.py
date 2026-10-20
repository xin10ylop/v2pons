import sys, json, calendar, time
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import *
RELAY = "2abb5653352f6b2f3b4f4261877cd02d9e05a957"
b_end = block_at(calendar.timegm(time.strptime("2026-10-09 01:00", "%Y-%m-%d %H:%M")))
head = int(rpc("eth_blockNumber", []), 16)
print("oct9 01:00 block", b_end, "head", head)
ls = logs({"address": PM, "topics": [T_SWAP, None, "0x" + "0"*24 + RELAY]}, 82878144, b_end)
print(len(ls))
for l in ls: print(int(l["blockNumber"],16), l["topics"][1], l["transactionHash"], sgn(W(l["data"],0)))
