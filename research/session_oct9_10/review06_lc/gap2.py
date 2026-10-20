import json, sys, time, urllib.request, urllib.error
from eth_utils import keccak
import rlp
RPC="https://rpc.mainnet.chain.robinhood.com"; H={"Content-Type":"application/json","User-Agent":"Mozilla/5.0 Chrome/128"}
PM="0x8366a39cc670b4001a1121b8f6a443a643e40951"
T_INIT="0x"+keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
def post(b):
    for i in range(10):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(RPC,json.dumps(b).encode(),H),timeout=60))
        except urllib.error.HTTPError as e: time.sleep(3*(i+1) if e.code==429 else 2)
        except Exception: time.sleep(2+i)
    raise RuntimeError("rpc")
def rpc(m,p):
    r=post({"jsonrpc":"2.0","id":1,"method":m,"params":p})
    if "error" in r: raise RuntimeError(str(r["error"])[:200])
    return r["result"]
def logs(f,a,b):
    try: return rpc("eth_getLogs",[dict(f,fromBlock=hex(a),toBlock=hex(b))])
    except RuntimeError:
        if b<=a: raise
        m=(a+b)//2; return logs(f,a,m)+logs(f,m+1,b)
head=int(rpc("eth_blockNumber",[]),16); span=int(sys.argv[1]) if len(sys.argv)>1 else 60000
inits=logs({"address":PM,"topics":[T_INIT,None,"0x"+"0"*64]},head-span,head)
print("head",head,"inits",len(inits))
seen=set()
for l in inits:
    t=rpc("eth_getTransactionByHash",[l["transactionHash"]])
    if t["input"][:10]!="0x2fcb9108" or t["hash"] in seen: continue
    seen.add(t["hash"]); L=int(t["blockNumber"],16)
    frm=t["from"]; to=t["to"]
    ca="0x"+keccak(rlp.encode([bytes.fromhex(frm[2:]),0]))[12:].hex()
    D=None
    for i in range(0,60,20):
        r=post([{"jsonrpc":"2.0","id":j,"method":"eth_getBlockByNumber","params":[hex(L-1-i-j),True]} for j in range(20)])
        for x in sorted(r,key=lambda x:x["id"]):
            b=x.get("result")
            if not b: continue
            for tx in b["transactions"]:
                if tx["from"].lower()==frm.lower() and tx["to"] is None: D=int(b["number"],16)
        if D: break
    if D is None: print("launch",L,"no deploy found in 60 blocks"); continue
    tsL=int(rpc("eth_getBlockByNumber",[hex(L),False])["timestamp"],16); tsD=int(rpc("eth_getBlockByNumber",[hex(D),False])["timestamp"],16)
    print(f"launch {L} nonce {int(t['nonce'],16)} nonce0-addr-match {ca==to} deployed {D} gap {L-D} blocks {tsL-tsD}s")
