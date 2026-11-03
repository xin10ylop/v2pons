#!/usr/bin/env python3
"""ethblock.py: are the Ethereum 1852 B line's real outside buyers blocked? For outside buyers of the line (out/line_eth_full.json),
eth_simulateV1 (archive RPCs) of the holder's own sell of its whole balance at the end of each block after its buy, and of a fresh
wallet's buy-and-sell at the same state. A holder whose sell reverts while a fresh wallet's passes has been blocked by the token's
controller (0x610b10d3, called on every transfer). Read-only."""
import json, urllib.request, time
URLS=["https://eth.drpc.org","https://ethereum.publicnode.com"]; R2="0x7a250d5630b4cf539739df2c5dacb4c659f2488d"; WETH="c02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
def rpc(m,p):
    last=None
    for i in range(6):
        u=URLS[i%2]
        try:
            r=json.loads(urllib.request.urlopen(urllib.request.Request(u,json.dumps({"jsonrpc":"2.0","id":1,"method":m,"params":p}).encode(),{"Content-Type":"application/json","User-Agent":"curl/8"}),timeout=60).read())
            if "error" in r: last=str(r["error"])[:200]; time.sleep(2); continue
            return r["result"]
        except Exception as e: last=str(e); time.sleep(2)
    raise RuntimeError(last)
w=lambda x: format(x,"064x"); ad=lambda a:"0"*24+a.lower().replace("0x","")
d=json.load(open(__import__("os").path.join(__import__("os").path.dirname(__import__("os").path.abspath(__file__)), "out/line_eth_full.json")))
cases=[("v2:0xf303e77","0x803cee8d"),("v2:0x83a0555","0x499b58ba"),("v2:0x32768dd","0x702f63fc"),("v2:0x3720b23","0x6741f6eb"),("v2:0x140608a","0x407b514c"),("v2:0x9cbb060","0x465f0b08"),("v2:0x48091b9","0x56c26202")]
for pid,who in cases:
    p=[q for q in d["pools"] if q["id"].startswith(pid)][0]
    e=[e for e in p["ev"] if e[6].startswith(who) and e[2]>0][0]
    full=e[6]; b=p["bn"]+min(p["burn"]-3, e[0]+40)
    bal=int(rpc("eth_call",[{"to":p["tok"],"data":"0x70a08231"+ad(full)},hex(b)]),16)
    res=[]
    for frm in (full, "0x5e11e5e11e5e11e5e11e5e11e5e11e5e11e5e11e"):
        so={frm:{"balance":hex(10**19)}}
        calls=[]
        if frm!=full:
            calls.append({"from":frm,"to":R2,"value":hex(10**16),"data":"0x7ff36ab5"+w(0)+w(0x80)+ad(frm)+w(2**40)+w(2)+ad(WETH)+ad(p["tok"])})
        calls.append({"from":frm,"to":p["tok"],"data":"0x095ea7b3"+ad(R2)+w(2**256-1)})
        amt = bal if frm==full else 10**18
        if amt==0: res.append(("holder","holds 0")); continue
        calls.append({"from":frm,"to":R2,"data":"0x791ac947"+w(amt)+w(0)+w(0xa0)+ad(frm)+w(2**40)+w(2)+ad(p["tok"])+ad(WETH)})
        r=rpc("eth_simulateV1",[{"blockStateCalls":[{"stateOverrides":so,"calls":calls}]},hex(b)])
        sc=r[0]["calls"][-1]; res.append(("holder" if frm==full else "fresh", "OK" if sc["status"]=="0x1" else "REVERT", (sc.get("error") or {}).get("message","")[:90]))
    print(pid, who, "bought", round(e[2],4), "at +", e[0], "| sim at +", b-p["bn"], "holds", bal, "|", res, flush=True)

print("\n-- when does each buyer get blocked? (its own sell simulated at the end of each block after its buy)")
def can_sell(p, full, b):
    bal=int(rpc("eth_call",[{"to":p["tok"],"data":"0x70a08231"+ad(full)},hex(b)]),16)
    if bal==0: return None
    so={full:{"balance":hex(10**19)}}
    calls=[{"from":full,"to":p["tok"],"data":"0x095ea7b3"+ad(R2)+w(2**256-1)},
           {"from":full,"to":R2,"data":"0x791ac947"+w(bal)+w(0)+w(0xa0)+ad(full)+w(2**40)+w(2)+ad(p["tok"])+ad(WETH)}]
    r=rpc("eth_simulateV1",[{"blockStateCalls":[{"stateOverrides":so,"calls":calls}]},hex(b)])
    return r[0]["calls"][-1]["status"]=="0x1"
for pid,who in cases[:6]:
    p=[q for q in d["pools"] if q["id"].startswith(pid)][0]
    e=[e for e in p["ev"] if e[6].startswith(who) and e[2]>0][0]; full=e[6]; b0=p["bn"]+e[0]
    seq=[]
    for k in range(0,8):
        s=can_sell(p, full, b0+k)   # the state at the END of block b0+k
        seq.append((k, s))
        if s is False: break
    print(pid, who, "bought at +", e[0], "tx index", e[7], "| sellable at the end of block buy+k:", seq, flush=True)
