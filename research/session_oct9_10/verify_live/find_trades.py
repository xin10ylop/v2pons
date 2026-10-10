import sys, json, time; sys.path.insert(0, '..')
from chain import rpc, batch, logs, PM, T_SWAP, T_ML, T_INIT
from eth_utils import keccak
WAL="ab5a34c3f41e57fdee1a1d6f19d3e21f46df3ea8"; RELAY="2abb5653352f6b2f3b4f4261877cd02d9e05a957"
T_TR="0x"+keccak(text="Transfer(address,address,uint256)").hex()
pad=lambda a:"0x"+"0"*24+a
A,B=83279856,83402530
out={}
# 1) swaps on PM with sender == relay
sw_relay=logs({"address":PM,"topics":[T_SWAP,None,pad(RELAY)]},A,B)
print("relay swaps",len(sw_relay))
# 2) ERC20 transfers to/from wallet and to/from relay
tr_to=logs({"topics":[T_TR,None,pad(WAL)]},A,B); tr_from=logs({"topics":[T_TR,pad(WAL)]},A,B)
tr_rto=logs({"topics":[T_TR,None,pad(RELAY)]},A,B); tr_rfrom=logs({"topics":[T_TR,pad(RELAY)]},A,B)
print("transfers to wallet",len(tr_to),"from wallet",len(tr_from),"to relay",len(tr_rto),"from relay",len(tr_rfrom))
hs=sorted({l["transactionHash"] for l in sw_relay+tr_to+tr_from+tr_rto+tr_rfrom})
txs=dict(zip(hs,batch([("eth_getTransactionByHash",[h]) for h in hs])))
rcs=dict(zip(hs,batch([("eth_getTransactionReceipt",[h]) for h in hs])))
json.dump({"sw_relay":sw_relay,"tr_to":tr_to,"tr_from":tr_from,"tr_rto":tr_rto,"tr_rfrom":tr_rfrom,"txs":txs,"rcs":rcs},open("found.json","w"))
for h in hs:
    t=txs[h]; r=rcs[h]
    print(int(t["blockNumber"],16), int(t["transactionIndex"],16), h[:12], "from",t["from"][2:10],"to",(t["to"] or "")[2:10], "status",r["status"], "sel",t["input"][:10], "val",int(t["value"],16)/1e18)
