#!/usr/bin/env python3
"""ethfull.py: the Ethereum 1852 B line (lineprobe.py eth ... 0x7a250d56 0xe8e33700 260 1852) followed to its LP burn: every swap of each
pool for 1,500 blocks with the reserves after it and the sender, the burn block, and each outsider's buys and sells (outsider: a wallet in
under 30% of the pools). Writes out/line_eth_full.json for ethride.py and ethblock.py. Read-only, public RPCs."""
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import hlib as H
d=json.load(open("out/line_eth_0x7a250d56_260_1852.json"))
url=H.CH["eth"]["rpc"]; head=int(H.rpc(url,"eth_blockNumber",[]),16)
T_SYNC="0x1c411e9a96e071241c2f21f7726b17ae89e3cab4c78be50e062b03a9fffbbad1"
tc=json.load(open("out/line_tx_eth.json"))
pools=[]
for p in d["pools"]:
    a=p["id"][3:]
    L=H.logs("eth", p["bn"], min(head, p["bn"]+1500), [[H.T_SWAP2, H.T_BURN2, T_SYNC]], a)
    L.sort(key=lambda x:(int(x["blockNumber"],16),int(x["logIndex"],16)))
    hs=sorted({x["transactionHash"] for x in L if x["transactionHash"] not in tc})
    for h,x in zip(hs,H.batch(url,[("eth_getTransactionByHash",[h]) for h in hs],size=50,workers=4,tries=8)):
        tc[h]=[x["from"].lower(), (x.get("to") or "").lower(), x["input"][:10], int(x.get("gasPrice") or "0x0",16), int(x["transactionIndex"],16)] if x else None
    ev=[]; sync=None; burn=None; nat=p["nat"]
    for x in L:
        dd=x["data"][2:]; bn=int(x["blockNumber"],16)
        if x["topics"][0]==T_SYNC:
            r0,r1=int(dd[:64],16),int(dd[64:128],16); sync=(r0,r1) if nat==0 else (r1,r0); continue
        if x["topics"][0]==H.T_BURN2:
            if burn is None: burn=bn-p["bn"]
            continue
        a0i,a1i,a0o,a1o=(int(dd[i:i+64],16) for i in (0,64,128,192))
        n=(a0i-a0o) if nat==0 else (a1i-a1o); t=(a1o-a1i) if nat==0 else (a0o-a0i)
        w=(tc.get(x["transactionHash"]) or ["?"])[0]
        ev.append([bn-p["bn"], int(x["logIndex"],16), n/1e18, t, sync[0]/1e18, sync[1], w, (tc.get(x["transactionHash"]) or [0,0,0,0,0])[4]])
    pools.append({"id":p["id"],"bn":p["bn"],"tok":p["tok"],"launcher":p["launcher"],"burn":burn,"ev":ev,"nin":p["nin"]})
json.dump(tc,open("out/line_tx_eth.json","w"))
json.dump({"pools":pools},open("out/line_eth_full.json","w"))
cnt=collections.Counter(w for p in pools for w in {e[6] for e in p["ev"]})
crew={w for w,c in cnt.items() if c>=0.3*len(pools)}
print("pools",len(pools),"crew (30%+ of pools over the life):",len(crew))
print("burn offsets:",sorted(p["burn"] for p in pools if p["burn"] is not None), "unburned", sum(p["burn"] is None for p in pools))
print("initial native:",[round(p["ev"][0][4]-p["ev"][0][2],2) for p in pools])
for p in pools:
    o=collections.defaultdict(lambda:[0,0,[],[]])
    for e in p["ev"]:
        if e[6] in crew or e[6]==p["launcher"]: continue
        r=o[e[6]]
        if e[2]>0: r[0]+=e[2]; r[2].append(e[0])
        else: r[1]+=-e[2]; r[3].append(e[0])
    s=[(w[:10], round(r[0],4), round(r[1],4), r[2][:2], r[3][:2]) for w,r in o.items()]
    print(p["id"][:12], "burn +",p["burn"], "outsiders (bought, sold, buy offs, sell offs):", s[:6])
