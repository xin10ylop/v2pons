import sys; sys.path.insert(0,".")
from rpc import rpc, batch
from eth_hash.auto import keccak
TOK="0x950e681819a68f595bb3db313346393d64f66bb5"; PAIR="0x2de2620b04a0382390b18441cd033da7b798e57e"
W="0x8881bba6787848f4e86780ef69a34bb45c8d4fcb"; C="0x5339668e4dece6f25645b117265a465859672487"
X="0xbd418ce6a83995971de9f1cf9f61f345e91aeadd"; ROUTER="0x10ed43c718714eb63d5aa57b78b54704e256024e"
def allowance(o,s):
    d="0xdd62ed3e"+o[2:].rjust(64,"0")+s[2:].rjust(64,"0")
    r=rpc("eth_call",[{"to":TOK,"data":d},"latest"]); return int(r,16) if isinstance(r,str) else r
print("code @0xbd418ce6:", (rpc("eth_getCode",[X,"latest"]) or "")[:20], "len", len(rpc("eth_getCode",[X,"latest"]) or "0x")//2-1)
print("code @crowd     :", "len", len(rpc("eth_getCode",[C,"latest"]) or "0x")//2-1)
print("nonce US        :", rpc("eth_getTransactionCount",[W,"latest"]))
print("nonce 0xbd418ce6:", rpc("eth_getTransactionCount",[X,"latest"]))
print()
for o,s,lbl in [(X,W,"allow[0xbd418ce6][US]"),(X,C,"allow[0xbd418ce6][crowd]"),(X,ROUTER,"allow[0xbd418ce6][router]"),
                (W,X,"allow[US][0xbd418ce6]"),(W,ROUTER,"allow[US][router]"),(C,ROUTER,"allow[crowd][router]"),
                (X,PAIR,"allow[0xbd418ce6][pair]"),(X,X,"allow[0xbd418ce6][0xbd418ce6]")]:
    print(f"{lbl:28}",allowance(o,s))
# Approval logs around L+70
TA="0x8c5be1e5ebec7d5bd14f714f4f5ec7c46ab3db174da78c3f62f10b71e9aeeaa0"
LAUNCH=127550490
logs=[]
for a in range(LAUNCH, LAUNCH+120, 40):
    r=rpc("eth_getLogs",[{"address":TOK,"topics":[TA],"fromBlock":hex(a),"toBlock":hex(a+39)}])
    if isinstance(r,list): logs+=r
print("\nApproval events L+0..120:")
for l in logs:
    owner="0x"+l["topics"][1][-40:]; spender="0x"+l["topics"][2][-40:]; v=int(l["data"],16); b=int(l["blockNumber"],16)
    print(" L+%-3d"%(b-LAUNCH),"owner",owner[:12],"spender",spender[:12],"amt",v, l["transactionHash"][:12])
