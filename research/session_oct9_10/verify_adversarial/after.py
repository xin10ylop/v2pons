import sys; sys.path.insert(0, "..")
from chain import *
relay = "0x2abb5653352f6b2f3b4f4261877cd02d9e05a957"
head = int(rpc("eth_blockNumber", []), 16)
L = logs({"address": "0x"+PM.replace("0x",""), "topics": [T_SWAP, None, "0x"+"0"*24+relay[2:]]}, 83300000, head)
print(len(L))
for l in L:
    print(int(l["blockNumber"],16), l["topics"][1][:12], l["transactionHash"][:12])
