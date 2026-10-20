import sys, json; sys.path.insert(0,'..')
from chain import rpc, batch, logs, PM, T_SWAP, T_ML, T_INIT
D=json.load(open("found.json"))
RELAY="2abb5653352f6b2f3b4f4261877cd02d9e05a957"; UR="8876789976decbfcbbbe364623c63652db8c0904"
# collect our swaps by tx
ours=[]
for h,r in D["rcs"].items():
    for l in r["logs"]:
        if l["topics"][0]==T_SWAP and l["address"].lower()==PM: ours.append((int(l["blockNumber"],16),int(l["transactionIndex"],16),int(l["logIndex"],16),h,l["topics"][1],D["txs"][h]["input"][:10]))
ours.sort()
pids=[]
for o in ours:
    if o[4] not in pids: pids.append(o[4])
out={}
for k,pid in enumerate(pids,1):
    mine=[o for o in ours if o[4]==pid]
    bb=mine[0][0]
    init=logs({"address":PM,"topics":[T_INIT,pid]},bb-40000,bb)
    assert len(init)==1, (pid,len(init))
    ib=int(init[0]["blockNumber"],16)
    hi = bb+300 if k<8 else bb+12000
    ev=logs({"address":PM,"topics":[[T_SWAP,T_ML],pid]},ib,hi)
    hs=sorted({l["transactionHash"] for l in ev})
    tx=dict(zip(hs,batch([("eth_getTransactionByHash",[h]) for h in hs]))) if len(hs)<3000 else {}
    out[pid]={"k":k,"init":init[0],"ev":ev,"mine":mine,"tx":{h:{"from":t["from"],"to":t["to"],"idx":t["transactionIndex"],"sel":t["input"][:10],"nonce":t["nonce"]} for h,t in tx.items()}}
    print(k,pid[:14],"init blk",ib,"buy",bb,"events",len(ev),"txs",len(hs))
json.dump(out,open("pools.json","w"))
