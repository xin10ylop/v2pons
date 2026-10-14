import sys; sys.path.insert(0,".")
from rpc import rpc
import json
TOK="0x950e681819a68f595bb3db313346393d64f66bb5"; PAIR="0x2de2620b04a0382390b18441cd033da7b798e57e"
W="0x8881bba6787848f4e86780ef69a34bb45c8d4fcb"
TT="0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
LAUNCH=127550490
logs=[]
for a in range(LAUNCH-2, LAUNCH+900, 50):
    r=rpc("eth_getLogs",[{"address":TOK,"topics":[TT],"fromBlock":hex(a),"toBlock":hex(a+49)}])
    if isinstance(r,list): logs+=r
    else: print("err",a,r)
rows=[]
for l in logs:
    fr="0x"+l["topics"][1][-40:]; to="0x"+l["topics"][2][-40:]; v=int(l["data"],16); b=int(l["blockNumber"],16); li=int(l["logIndex"],16)
    rows.append((b,li,fr,to,v,l["transactionHash"]))
rows.sort()
buyers={}
print("n transfers:",len(rows))
for b,li,fr,to,v,h in rows:
    tag="BUY" if fr==PAIR else ("SELL" if to==PAIR else "xfer")
    if fr==PAIR and to not in buyers: buyers[to]=b
    us="  <<WALLET" if (fr==W or to==W) else ""
    print(b,"L+%-3d"%(b-LAUNCH),tag,fr[:10],"->",to[:10],v,h[:12],us)
json.dump({"buyers":buyers,"launch":LAUNCH}, open("buyers.json","w"))
print("\nfirst buyers by block:")
for a,b in sorted(buyers.items(),key=lambda kv:kv[1]): print(" ",a,"L+"+str(b-LAUNCH), "US" if a==W else "")
