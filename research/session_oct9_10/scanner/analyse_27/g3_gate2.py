import sys
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/analyse_27")
import urllib.request, json
from load import *
P = load_pools()
g3 = [p for p in P.values() if (p["to_code_hash"] or "").replace("0x","").startswith("f07d1c53")]
OPWALLET = "0x9fdd8ceab2de4fa2d9b0f1f37475a47baff8cd9a"
OURWALLET = "0xab5a34c3f41e57fdee1a1d6f19d3e21f46df3ea8"
RAND = "0x1111111111111111111111111111111111111111"
PM = "0x8366a39cc670b4001a1121b8f6a443a643e40951"
RPC = "https://rpc.mainnet.chain.robinhood.com"
H = {"Content-Type":"application/json","User-Agent":"Mozilla/5.0"}
def w(x): return hex(x & ((1<<256)-1))[2:].rjust(64,"0")
def addr(a): return a[2:].rjust(64,"0")
def rawcall(frm, to, data):
    body={"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"from":frm,"to":to,"data":data},"latest"]}
    try:
        r=json.load(urllib.request.urlopen(urllib.request.Request(RPC,json.dumps(body).encode(),H),timeout=40))
        return r
    except urllib.error.HTTPError as e:
        return {"http":e.code, "body": e.read()[:200].decode('latch','ignore') if False else e.read()[:300].decode('utf-8','ignore')}
    except Exception as e:
        return {"err":str(e)[:120]}
BEFORE_SWAP = "575e24b4"
def beforeswap_data(key, sender):
    c0,c1,fee,ts,hooks = key
    # sender, poolkey(5), params(3: zeroForOne=1, amountSpecified=-1e15, sqrtLimit=min+1), hookData offset+len
    amt = -(10**15)
    sqrtlimit = 4295128740  # MIN_SQRT_PRICE+1
    words = [addr(sender), addr(c0), addr(c1), w(fee), w(ts), addr(hooks), w(1), w(amt), w(sqrtlimit), w(0x140), w(0)]
    return "0x"+BEFORE_SWAP+"".join(words)
for p in g3[2:6]:
    hook=p["hooks"]; key=("0x0000000000000000000000000000000000000000", "0x"+p["token"][-40:], p["fee"], p["tick_spacing"], hook)
    print("=== hook", hook, "pool", p["pid"][:10])
    for nm, frm in (("op",OPWALLET),("ours",OURWALLET),("rand",RAND)):
        d=beforeswap_data(key, frm)
        r=rawcall(frm, hook, d)
        res = r.get("result") if isinstance(r,dict) else r
        err = (r.get("error") or {}).get("data") if isinstance(r,dict) else None
        print("   from %-4s -> result %s error %s" % (nm, (res[:20]+'...' if res and len(res)>20 else res), str(r.get('error') if isinstance(r,dict) else r)[:140]))
