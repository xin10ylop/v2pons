import sys; sys.path.insert(0,".")
from rpc import URLS, _one
from eth_hash.auto import keccak
import json
TOK="0x950e681819a68f595bb3db313346393d64f66bb5"; DEAD="0x000000000000000000000000000000000000dead"
W="0x8881bba6787848f4e86780ef69a34bb45c8d4fcb"; C="0x5339668e4dece6f25645b117265a465859672487"
SLOT6="0xbd418ce6a83995971de9f1cf9f61f345e91aeadd"
def h32(x): return "0x"+(x if isinstance(x,int) else int(x,16)).to_bytes(32,"big").hex()
def mapslot(addr,slot): return "0x"+keccak(bytes.fromhex(addr[2:].rjust(64,"0"))+slot.to_bytes(32,"big")).hex()
def allowslot(owner,spender):  # allowance[owner][spender] slot=1
    inner=keccak(bytes.fromhex(owner[2:].rjust(64,"0"))+(1).to_bytes(32,"big"))
    return "0x"+keccak(bytes.fromhex(spender[2:].rjust(64,"0"))+inner).hex()
def xfer(to,amt): return "0xa9059cbb"+to[2:].rjust(64,"0")+hex(amt)[2:].rjust(64,"0")
def sim(frm, overrides=None, block=None, data=None, to=TOK):
    call={"from":frm,"to":to,"data":data or xfer(DEAD,1000)}
    bsc={"calls":[call]}
    if overrides: bsc["stateOverrides"]=overrides
    if block: bsc["blockOverrides"]=block
    body={"jsonrpc":"2.0","id":1,"method":"eth_simulateV1","params":[{"blockStateCalls":[bsc],"validation":False,"traceTransfers":False},"latest"]}
    for U in URLS:
        try:
            r=_one(U,body)
            if "result" in r:
                c=r["result"][0]["calls"][0]
                st=c.get("status"); ret=c.get("returnData","")
                err=c.get("error")
                return f"status={st} ret={ret[:18]} err={err}"
            e=r.get("error")
            # some nodes put revert at top level
        except Exception as ex: last=str(ex)
    return "NODE-ERR "+str(locals().get("last","?"))[:60]
AMT=1000
print("base US   :", sim(W))
print("base CROWD:", sim(C))
print()
# Exp1: US with huge balance slot0
print("E1 US +huge bal slot0:", sim(W, {TOK:{"stateDiff":{mapslot(W,0):h32(10**18)}}}))
# Exp8: US balance set to crowd's exact value
print("E8 US bal:=crowd value:", sim(W, {TOK:{"stateDiff":{mapslot(W,0):h32(433536700279152)}}}))
# Exp7: CROWD balance set to US's exact value
print("E7 CROWD bal:=US value :", sim(C, {TOK:{"stateDiff":{mapslot(C,0):h32(26815492626516)}}}))
# Exp2: slot6 -> 0
print("E2 US slot6:=0         :", sim(W, {TOK:{"stateDiff":{h32(6):h32(0)}}}))
# Exp3: slot6 -> W
print("E3 US slot6:=W         :", sim(W, {TOK:{"stateDiff":{h32(6):"0x"+W[2:].rjust(64,'0')}}}))
# Exp4: slot5 -> 0
print("E4 US slot5:=0         :", sim(W, {TOK:{"stateDiff":{h32(5):h32(0)}}}))
# Exp5: block number & ts far future
print("E5 US block+1e6 ts+1e7 :", sim(W, block={"number":h32(127550490+1000000),"time":h32(2000000000)}))
# Exp6: allowance[W][slot6]=MAX
print("E6 US allow[W][slot6]=MX:", sim(W, {TOK:{"stateDiff":{allowslot(W,SLOT6):h32((1<<256)-1)}}}))
# Exp6b: allowance[W][W]=MAX
print("E6b US allow[W][W]=MAX  :", sim(W, {TOK:{"stateDiff":{allowslot(W,W):h32((1<<256)-1)}}}))
