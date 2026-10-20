import sys, json; sys.path.insert(0,'..')
from chain import batch
WAL="0xab5a34c3f41e57fdee1a1d6f19d3e21f46df3ea8"
def scan(a,b):
    res=[]
    bl=batch([("eth_getBlockByNumber",[hex(n),True]) for n in range(a,b+1)])
    for B in bl:
        for t in B["transactions"]:
            if t["from"].lower()==WAL or (t.get("to") or "").lower()==WAL:
                res.append((int(B["number"],16),int(t["transactionIndex"],16),t["hash"],int(t["nonce"],16),t["from"][:10],(t["to"] or "")[:10],t["input"][:10],int(t["value"],16)/1e18))
    return res
for r in scan(int(sys.argv[1]),int(sys.argv[2])): print(r)
