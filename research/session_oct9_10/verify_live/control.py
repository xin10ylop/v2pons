import sys, json; sys.path.insert(0,'..')
from chain import W, sgn, T_SWAP, T_ML
D=json.load(open("../oct8.json")); P=json.load(open("pools.json"))
def s(x,bits):
    x&=(1<<bits)-1; return x-(1<<bits) if x>=(1<<(bits-1)) else x
ours={pid:p["k"] for pid,p in P.items()}
for pid,p in sorted(D["pools"].items(), key=lambda kv: kv[1]["bn"]):
    ev=sorted(D["ev"][pid], key=lambda l:(int(l["blockNumber"],16),int(l["logIndex"],16)))
    b0=p["bn"]; buys=[]; pull=None; sells=0
    for l in ev:
        bn=int(l["blockNumber"],16)
        if l["topics"][0]==T_SWAP:
            a0=s(W(l["data"],0),128)
            if a0<0: buys.append((bn,-a0))
            elif a0>0: sells+=1
        elif sgn(W(l["data"],2))<0 and pull is None: pull=bn
    big=[b for b in buys if b[1]>=10**15]
    fb=big[0][0] if big else None
    print(f"pool {pid[:10]} fee {p['fee']:6d} launch {b0} ours={ours.get(pid,'-')!s:2s} first>=0.001ETH buy +{(fb-b0) if fb else None}  pull +{(pull-b0) if pull else None}  pull-firstbuy {((pull-fb) if pull and fb else None)} blocks (~{((pull-fb)*0.103 if pull and fb else 0):.0f}s)  buys {len(buys)} (>=0.001: {len(big)}) sells {sells}")
