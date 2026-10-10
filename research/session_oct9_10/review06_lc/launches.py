import json,sys,time,urllib.request,urllib.error,collections
from eth_utils import keccak
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
a,b=int(sys.argv[1]),int(sys.argv[2])
inits=logs({"address":PM,"topics":[T_INIT,None,"0x"+"0"*64]},a,b)
hs=sorted({l["transactionHash"] for l in inits})
res=[]
for i in range(0,len(hs),50):
    r=post([{"jsonrpc":"2.0","id":j,"method":"eth_getTransactionByHash","params":[h]} for j,h in enumerate(hs[i:i+50])])
    res+= [x["result"] for x in r if x.get("result")]
op=[t for t in res if t["input"][:10]=="0x2fcb9108"]
op.sort(key=lambda t:int(t["blockNumber"],16))
for t in op: print(int(t["blockNumber"],16), t["to"], int(t["nonce"],16), t["from"])
