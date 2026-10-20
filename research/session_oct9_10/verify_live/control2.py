import sys, json; sys.path.insert(0,'..')
from chain import W, sgn, T_SWAP, T_ML, batch
D=json.load(open("../oct8.json")); P=json.load(open("pools.json"))
def s(x,bits):
    x&=(1<<bits)-1; return x-(1<<bits) if x>=(1<<(bits-1)) else x
for pid,p in sorted(D["pools"].items(), key=lambda kv: kv[1]["bn"]):
    if pid in P: continue
    ev=sorted(D["ev"][pid], key=lambda l:(int(l["blockNumber"],16),int(l["logIndex"],16)))
    hs=[l["transactionHash"] for l in ev[:14]]
    T=batch([("eth_getTransactionByHash",[h]) for h in hs])
    b0=p["bn"]; print(f"\n control pool {pid[:10]} fee {p['fee']} launch {b0}")
    fb=None
    for l,t in zip(ev[:14],T):
        bn=int(l["blockNumber"],16)
        if l["topics"][0]==T_SWAP:
            a0=s(W(l["data"],0),128)
            if a0<0 and -a0>=10**15 and fb is None: fb=bn
            print(f"   +{bn-b0:5d} (firstbuy{(bn-fb) if fb else 0:+4d}) {'BUY ' if a0<0 else 'SELL'} {abs(a0)/1e18:.5f} from {t['from'][2:10]} via {l['topics'][2][-40:][:8]}")
        else: print(f"   +{bn-b0:5d} ML dL {sgn(W(l['data'],2)):+.3e} from {t['from'][2:10]}")
