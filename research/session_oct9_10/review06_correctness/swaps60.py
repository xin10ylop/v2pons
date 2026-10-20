import json, urllib.request, urllib.error, time, sys, collections
from eth_utils import keccak
RPC="https://rpc.mainnet.chain.robinhood.com"
PM="0x8366a39cc670b4001a1121b8f6a443a643e40951"
T_SWAP="0x"+keccak(text="Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)").hex()
T_INIT="0x"+keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
def _rb(calls):
    body=json.dumps([{"jsonrpc":"2.0","id":i,"method":m,"params":p} for i,(m,p) in enumerate(calls)]).encode()
    req=urllib.request.Request(RPC,body,{"Content-Type":"application/json","User-Agent":"Mozilla/5.0 Chrome/128"})
    r=json.loads(urllib.request.urlopen(req,timeout=60).read()); r.sort(key=lambda x:x["id"]); return r
def rb(calls):
    for k in range(15):
        try:
            r=_rb(calls)
            if any("error" in x for x in r) and any("rate" in str(x.get("error","")).lower() or "429" in str(x.get("error","")) for x in r): raise urllib.error.HTTPError(RPC,429,"",None,None)
            return [x.get("result") if "result" in x else x for x in r]
        except urllib.error.HTTPError as e:
            if e.code!=429: raise
            time.sleep(1+k)
    raise SystemExit("429")
head=int(rb([("eth_blockNumber",[])])[0],16)
span=int(sys.argv[1]); lo=head-span
inits=[]; a=lo
while a<head:
    b=min(a+99998,head); r=rb([("eth_getLogs",[{"address":PM,"topics":[T_INIT,None,"0x"+"0"*64],"fromBlock":hex(a),"toBlock":hex(b)}])])[0]
    if isinstance(r,dict): print("err",r); break
    inits+=r; a=b+1
print("ETH pools initialized in window:",len(inits))
pools={l["topics"][1]:int(l["blockNumber"],16) for l in inits}
# early swaps: within 400 blocks of init
hashes={}
pl=list(pools.items())
for i in range(0,len(pl),20):
    chunk=pl[i:i+20]
    calls=[("eth_getLogs",[{"address":PM,"topics":[T_SWAP,pid],"fromBlock":hex(bn),"toBlock":hex(min(bn+60,head))}]) for pid,bn in chunk]
    for (pid,bn),r in zip(chunk,rb(calls)):
        if isinstance(r,dict): print("err",r); continue
        for l in r: hashes[l["transactionHash"]]=(pid,int(l["blockNumber"],16)-bn)
print("early swap txs:",len(hashes))
types=collections.Counter(); t4=[]
hl=list(hashes)
for i in range(0,len(hl),100):
    for h,t in zip(hl[i:i+100],rb([("eth_getTransactionByHash",[h]) for h in hl[i:i+100]])):
        types[t["type"]]+=1
        if int(t["type"],16)==4: t4.append((h,hashes[h],t["from"],t["to"],int(t["value"],16)))
print(types)
for x in t4: print(x)
