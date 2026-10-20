"""full-block cache (eth_getBlockByNumber, true) on disk: blocks/<bn>.json; batch 50, chain.py's backoff"""
import sys, os, json
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10"); import chain
HERE=os.path.dirname(os.path.abspath(__file__)); BD=os.path.join(HERE,"blocks"); os.makedirs(BD,exist_ok=True)
def get_blocks(bns):
    need=[b for b in bns if not os.path.exists(os.path.join(BD,"%d.json"%b))]
    for i in range(0,len(need),50):
        ch=need[i:i+50]
        res=chain.batch([("eth_getBlockByNumber",[hex(b),True]) for b in ch])
        for b,r in zip(ch,res):
            if r is None: continue
            json.dump(r,open(os.path.join(BD,"%d.json"%b),"w"))
    out={}
    for b in bns:
        f=os.path.join(BD,"%d.json"%b)
        if os.path.exists(f): out[b]=json.load(open(f))
    return out
RC=os.path.join(HERE,"receipts"); os.makedirs(RC,exist_ok=True)
def get_receipts(hs):
    need=[h for h in hs if not os.path.exists(os.path.join(RC,h+".json"))]
    for i in range(0,len(need),50):
        ch=need[i:i+50]
        res=chain.batch([("eth_getTransactionReceipt",[h]) for h in ch])
        for h,r in zip(ch,res):
            if r is not None: json.dump(r,open(os.path.join(RC,h+".json"),"w"))
    return {h:json.load(open(os.path.join(RC,h+".json"))) for h in hs if os.path.exists(os.path.join(RC,h+".json"))}
