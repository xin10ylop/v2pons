import json,sys,urllib.request
RPC="https://rpc.mainnet.chain.robinhood.com"; H={"Content-Type":"application/json","User-Agent":"Mozilla/5.0 Chrome/128"}
def post(b): return json.load(urllib.request.urlopen(urllib.request.Request(RPC,json.dumps(b).encode(),H),timeout=60))
rows=[l.split() for l in open("ops.txt") if "3194e326" not in l]
import random; random.seed(1); pick=rows[:4]+rows[-8:]
for L,to,n in pick:
    L=int(L)
    blk=post({"jsonrpc":"2.0","id":1,"method":"eth_getBlockByNumber","params":[hex(L),True]})["result"]
    t=[x for x in blk["transactions"] if x["input"][:10]=="0x2fcb9108"][0]; frm=t["from"]
    D=None
    r=post([{"jsonrpc":"2.0","id":j,"method":"eth_getBlockByNumber","params":[hex(L-1-j),True]} for j in range(40)])
    for x in r:
        b=x.get("result")
        if not b: continue
        for tx in b["transactions"]:
            if tx["from"].lower()==frm.lower() and tx.get("to") is None: D=(int(b["number"],16),int(b["timestamp"],16))
    if D: print(L,"gap",L-D[0],"blocks",int(blk["timestamp"],16)-D[1],"s")
    else: print(L,"deploy not in 40 blocks")
