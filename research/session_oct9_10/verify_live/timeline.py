import sys, json; sys.path.insert(0,'..')
from chain import W, sgn, T_SWAP, T_ML, T_INIT
P=json.load(open("pools.json"))
def s(x,bits):
    x=sgn(x) if bits==256 else x
    if bits<256:
        x &= (1<<bits)-1
        if x>=(1<<(bits-1)): x-=(1<<bits)
    return x
WAL="0xab5a34c3f41e57fdee1a1d6f19d3e21f46df3ea8"
lim=int(sys.argv[1]) if len(sys.argv)>1 else 60
for pid,p in P.items():
    k=p["k"]; I=p["init"]; d=I["data"]
    fee=W(d,0); ts=s(W(d,1),24); sp0=W(d,3); tick0=s(W(d,4),24)
    bb=p["mine"][0][0]
    print(f"\n=== trade {k} pool {pid[:14]} currency0 {I['topics'][2][-40:][:8]} currency1(token) {I['topics'][3][-40:][:10]} fee {fee} ts {ts} tick0 {tick0} init blk {int(I['blockNumber'],16)} (buy-{bb-int(I['blockNumber'],16)}) init tx from {p['tx'].get(I['transactionHash'],{}).get('from','?')[:10]}")
    ev=sorted(p["ev"],key=lambda l:(int(l["blockNumber"],16),int(l["logIndex"],16)))
    n=0
    for l in ev:
        bn=int(l["blockNumber"],16); t=p["tx"][l["transactionHash"]]; d=l["data"]
        rel=bn-bb
        if rel>lim and k==8:
            if l["topics"][0]!=T_ML: continue
        me = "  <== OURS" if (t["from"].lower()==WAL) else ""
        if l["topics"][0]==T_SWAP:
            a0=s(W(d,0),128); a1=s(W(d,1),128)
            print(f"  blk {bn} (buy{rel:+5d}) txi {int(t['idx'],16):3d} li {int(l['logIndex'],16):3d} {'BUY ' if a0<0 else 'SELL'} eth {a0/1e18:+.7f} tok {a1:+.4e} sqrtP {W(d,2)} L {W(d,3)} tick {s(W(d,4),24)} fee {W(d,5)} from {t['from'][2:10]} via {l['topics'][2][-40:][:8]}{me}")
        else:
            print(f"  blk {bn} (buy{rel:+5d}) txi {int(t['idx'],16):3d} li {int(l['logIndex'],16):3d} ML  ticks [{s(W(d,0),24)},{s(W(d,1),24)}] dL {s(W(d,2),256):+.4e} from {t['from'][2:10]} via {l['topics'][2][-40:][:8]} sel {t['sel']}{me}")
