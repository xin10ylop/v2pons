import json, urllib.request, urllib.error, sys, collections, concurrent.futures as cf
RPC="https://rpc.mainnet.chain.robinhood.com"
import time
def rpc_batch(calls):
  for k in range(12):
   try:
    return _rb(calls)
   except urllib.error.HTTPError as e:
    if e.code!=429: raise
    time.sleep(1+k)
  raise SystemExit('429')
def _rb(calls):
    body=json.dumps([{"jsonrpc":"2.0","id":i,"method":m,"params":p} for i,(m,p) in enumerate(calls)]).encode()
    req=urllib.request.Request(RPC,body,{"Content-Type":"application/json","User-Agent":"Mozilla/5.0 Chrome/128"})
    r=json.loads(urllib.request.urlopen(req,timeout=30).read())
    r.sort(key=lambda x:x["id"]); return [x.get("result") for x in r]
head=int(rpc_batch([("eth_blockNumber",[])])[0],16)
N=int(sys.argv[1]) if len(sys.argv)>1 else 3000
types=collections.Counter(); t4=[]; single=0; users=0
def fetch(start):
    return rpc_batch([("eth_getBlockByNumber",[hex(b),True]) for b in range(start,min(start+20,head+1))])
starts=list(range(head-N+1,head+1,20))
with cf.ThreadPoolExecutor(2) as ex:
    for blocks in ex.map(fetch,starts):
        for b in blocks:
            if not b: continue
            u=[t for t in b["transactions"] if int(t["type"],16) not in (0x6a,0x64,0x65,0x66,0x68,0x69)]
            users+=len(u)
            if len(u)==1: single+=1
            for t in u:
                types[t["type"]]+=1
                if int(t["type"],16)==4:
                    t4.append((int(b["number"],16),t["hash"],t["from"],t.get("to"),int(t["value"],16),t["input"][:10],len(t["input"])//2-1,len(t.get("authorizationList") or [])))
print("head",head,"blocks",N,"user txs",users,"single-user-tx blocks",single)
print(types)
for x in t4: print(x)
