"""all logs naming an address in topics 1-3 over [a, b]; usage: logsof.py addr a b"""
import sys; sys.path.insert(0,'/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad')
from chain import rpc, logs
a=sys.argv[1].lower(); A=int(sys.argv[2]); Bb=int(sys.argv[3]); T="0x"+"0"*24+a[2:]
out=[]
for pos in range(1,4):
    out += logs({"topics":[None]*pos+[T]}, A, Bb)
seen=set(); out2=[]
for l in sorted(out, key=lambda l:(int(l["blockNumber"],16), int(l["logIndex"],16))):
    k=(l["transactionHash"], l["logIndex"])
    if k in seen: continue
    seen.add(k); out2.append(l)
print(a[:10], len(out2), "logs")
for l in out2[:int(sys.argv[4]) if len(sys.argv)>4 else 60]:
    print("  ", int(l["blockNumber"],16), l["address"][:12], l["topics"][0][:12], l["transactionHash"][:14], [t[-40:][:10] for t in l["topics"][1:]], l["data"][:66])
