import sys, json; sys.path.insert(0,'..')
from chain import rpc, batch, logs, PM, T_SWAP
from eth_utils import keccak
WAL="ab5a34c3f41e57fdee1a1d6f19d3e21f46df3ea8"; RELAY="2abb5653352f6b2f3b4f4261877cd02d9e05a957"
T_TR="0x"+keccak(text="Transfer(address,address,uint256)").hex(); pad=lambda a:"0x"+"0"*24+a
A=83402531; B=int(rpc("eth_blockNumber",[]),16)
print("range",A,B)
r=logs({"address":PM,"topics":[T_SWAP,None,pad(RELAY)]},A,B); print("relay swaps after 15:00:",len(r))
for f in ([T_TR,None,pad(WAL)],[T_TR,pad(WAL)],[T_TR,None,pad(RELAY)],[T_TR,pad(RELAY)]):
    x=logs({"topics":f},A,B); print("transfers",len(x), [ (int(l["blockNumber"],16), l["transactionHash"][:12]) for l in x[:5]])
# earlier: before 11:30 (nonce 0,1, and earlier wallet activity)
r0=logs({"address":PM,"topics":[T_SWAP,None,pad(RELAY)]},83200000,83279855); print("relay swaps before 11:30 (from blk 83200000):",len(r0))
print("relay code size", len(rpc("eth_getCode",["0x"+RELAY,"latest"])))
