import sys; sys.path.insert(0,".")
from rpc import rpc, batch
from eth_hash.auto import keccak
TOK="0x950e681819a68f595bb3db313346393d64f66bb5"; PAIR="0x2de2620b04a0382390b18441cd033da7b798e57e"
W ="0x8881bba6787848f4e86780ef69a34bb45c8d4fcb"      # us (L+52)
C ="0x5339668e4dece6f25645b117265a465859672487"      # crowd L+65 (can transfer per task; holds? bought, not seen selling)
C2="0xb27ad6a5c4b1b71e04fda767b5ba2577e0950ffb"      # crowd L+120
def mapslot(addr,slot): return "0x"+keccak(bytes.fromhex(addr[2:].rjust(64,"0"))+slot.to_bytes(32,"big")).hex()
def bo(a):  # balanceOf
    r=rpc("eth_call",[{"to":TOK,"data":"0x70a08231"+a[2:].rjust(64,"0")},"latest"]); 
    return int(r,16) if isinstance(r,str) else r
print("balanceOf us   :",bo(W))
print("balanceOf crowd:",bo(C))
print("balanceOf crowd2:",bo(C2))
print("balanceOf pair :",bo(PAIR))
# raw storage for mapping slot bases 0..15 for each address
print("\n== raw storage mapping[addr @ slot k] for k in 0..15 ==")
for name,a in [("US",W),("CROWD",C),("CROWD2",C2),("PAIR",PAIR)]:
    calls=[("eth_getStorageAt",[TOK,mapslot(a,k),"latest"]) for k in range(16)]
    res=batch(calls)
    nz={k:v for k,v in enumerate(res) if isinstance(v,str) and int(v,16)!=0}
    print(name,a[:10],"nonzero slots:",{k:(int(v,16)) for k,v in nz.items()})
# singleton slots 0..20
print("\n== singleton slots 0..24 ==")
res=batch([("eth_getStorageAt",[TOK,hex(k),"latest"]) for k in range(25)])
for k,v in enumerate(res):
    if isinstance(v,str) and int(v,16)!=0: print(" slot",k,v, int(v,16))
