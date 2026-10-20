import sys, json, collections, time
sys.path.insert(0, '/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad')
sys.path.insert(0, '/home/user/v2pons/src')
from chain import *
import flip_engine
P="/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/fp/"
meta=json.load(open(P+"oct10_meta.json"))
A,END=meta["from"],meta["to"]
flt = {"address": PM, "topics": [T_INIT, None, "0x" + "0"*64]}
# re-scan in 25k chunks to cross-check counts
allinit=[]; b=A; sub=[]
while b<=END:
    e=min(b+24999,END); L=logs(flt,b,e); allinit+=L; sub.append((b,e,len(L))); b=e+1
print("rescan total", len(allinit), "orig", meta["n_all"], flush=True)
SP=1604517591721945638372359205383840; VAL=2433328500000000000; POSM="0x58daec3116aae6d93017baaea7749052e8a04fa7"
hs=sorted(set(l["transactionHash"] for l in allinit))
res={}
for attempt in range(8):
    todo=[h for h in hs if h not in res]
    if not todo: break
    r=batch([("eth_getTransactionByHash",[h]) for h in todo])
    for h,x in zip(todo,r):
        if x: res[h]=x
    time.sleep(2)
print("txs fetched", len(res), "of", len(hs), flush=True)
c=collections.Counter(); valrows=[]; famlike=[]
for l in allinit:
    t=res.get(l["transactionHash"])
    d=l["data"]; fee=W(d,0); ts=sgn(W(d,1)); sp=W(d,3)
    if not t: c["missing"]+=1; continue
    inp=bytes.fromhex(t["input"][2:]); v=int(t["value"],16)
    if v==VAL:
        dec=flip_engine.decode_launch(inp) if len(inp)==1444 else None
        valrows.append((int(l["blockNumber"],16), l["transactionHash"], t["to"], len(inp), inp[:4].hex(), fee, ts, str(sp), dec and (str(dec["sqrt_p"]), str(dec["mint_liq"]), dec["lo"], dec["hi"])))
    if (t["to"] or "").lower()==POSM and len(inp)==1444 and inp[:4].hex()=="ac9650d8" and v!=VAL:
        famlike.append((int(l["blockNumber"],16), l["transactionHash"], v, fee, ts, str(sp)))
    c[(fee,ts)]+=1
print("value==VAL among all ETH inits:", len(valrows))
fpc=collections.Counter((r[2],r[3],r[4],r[5],r[6],r[7],r[8]) for r in valrows)
for k,v in fpc.items(): print(v,k)
print("POSM 1444 multicall, other value:", len(famlike))
vc=collections.Counter((r[2],r[3],r[4]) for r in famlike)
for k,v in vc.most_common(20): print(v,k)
print("fee/ts tiers:", c.most_common(15))
json.dump({"rescan_chunks":sub,"rescan_total":len(allinit),"tx_fetched":len(res),"n_tx":len(hs),"val_rows":len(valrows)}, open(P+"oct10_check.json","w"))
