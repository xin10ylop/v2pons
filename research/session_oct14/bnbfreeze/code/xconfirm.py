import sys,os; sys.path.insert(0,".")
from rpc import URLS, _one
from eth_hash.auto import keccak
def h32(v): return "0x"+v.to_bytes(32,"big").hex()
def mapslot(a,s): return "0x"+keccak(bytes.fromhex(a[2:].rjust(64,"0"))+s.to_bytes(32,"big")).hex()
def allowslot(o,s):
    inner=keccak(bytes.fromhex(o[2:].rjust(64,"0"))+(1).to_bytes(32,"big"))
    return "0x"+keccak(bytes.fromhex(s[2:].rjust(64,"0"))+inner).hex()
DEAD="0x000000000000000000000000000000000000dead"
def sim(tok,frm,ov):
    call={"from":frm,"to":tok,"data":"0xa9059cbb"+DEAD[2:].rjust(64,"0")+hex(1000)[2:].rjust(64,"0")}
    body={"jsonrpc":"2.0","id":1,"method":"eth_simulateV1","params":[{"blockStateCalls":[{"stateOverrides":ov,"calls":[call]}],"validation":False},"latest"]}
    for U in URLS:
        try:
            r=_one(U,body)
            if "result" in r:
                c=r["result"][0]["calls"][0]; return "PASS" if c.get("status")=="0x1" else "REVERT"
        except Exception: pass
    return "?"
T18="0xef2622bddbc35a7025d1649c1608339258de54c9"; OP18="0xd604540564b6f659de163ad928e29782185da2fd"
z="0x"+os.urandom(20).hex()
base={T18:{"stateDiff":{mapslot(z,0):h32(10**15)}}}
print("1365 template token 0xef2622bd, operator 0xd604..., fresh holder z:")
for v in [0,1,2,3,(1<<256)-1,(1<<256)-2]:
    ov={T18:{"stateDiff":{mapslot(z,0):h32(10**15), allowslot(OP18,z):h32(v)}}}
    print(f"  allow[op][z]={v:>78} {'ODD ' if v&1 else 'EVEN'} -> {sim(T18,z,ov)}")
