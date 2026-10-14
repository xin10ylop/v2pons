import sys; sys.path.insert(0,".")
from rpc import rpc, batch
from eth_hash.auto import keccak
def gs(tok,slot): return rpc("eth_getStorageAt",[tok,hex(slot),"latest"])
T18="0xef2622bddbc35a7025d1649c1608339258de54c9"   # 1365 template
T5f="0x314674a4eb7051637cddc0e85a302ff6bbdd67cb"   # 2995 template
OUR="0x950e681819a68f595bb3db313346393d64f66bb5"
for lbl,t in [("1365tmpl",T18),("2995tmpl",T5f),("ourtoken",OUR)]:
    s2,s3,s4,s5,s6=[gs(t,k) for k in (2,3,4,5,6)]
    def addr(x): return "0x"+x[-40:] if isinstance(x,str) else x
    print(lbl,t)
    print("   slot2(totalSupply)",int(s2,16) if isinstance(s2,str) else s2)
    print("   slot5             ",s5)
    print("   slot6(operator)   ",addr(s6))
