import asyncio, json, time, sys, threading, urllib.request, concurrent.futures, collections
import websockets
RPC="https://rpc.mainnet.chain.robinhood.com"; FEED="wss://feed.mainnet.chain.robinhood.com"
DUR=float(sys.argv[1]) if len(sys.argv)>1 else 120; EVERY=int(sys.argv[2]) if len(sys.argv)>2 else 10
mono=time.monotonic
def rpc(m,p,timeout=3):
    req=urllib.request.Request(RPC,json.dumps({"jsonrpc":"2.0","id":1,"method":m,"params":p}).encode(),{"Content-Type":"application/json","User-Agent":"Mozilla/5.0 Chrome/128"})
    try:
        d=json.load(urllib.request.urlopen(req,timeout=timeout))
    except Exception as e:
        return ("exc",str(e)[:80])
    if "result" in d: return ("ok",d["result"])
    return ("err",d.get("error"))
out=[]
def probe(seq,t0):
    # like arm_launch: one 'getCode-like' check (is block seq-7 present?) and a receipt-like poll for block seq every 40 ms
    r={"seq":seq}
    a=rpc("eth_getBlockByNumber",["latest",False])
    r["latest_ms"]=round(1000*(mono()-t0),1)
    if a[0]=="ok" and a[1]: r["lag"]=seq-int(a[1]["number"],16)
    else: r["lag_err"]=str(a[1])[:60]
    deadline=t0+1.5
    while mono()<deadline:
        b=rpc("eth_getBlockByNumber",[hex(seq),False],timeout=2)
        if b[0]=="ok" and b[1]:
            r["have_ms"]=round(1000*(mono()-t0),1); break
        if b[0]!="ok": r.setdefault("poll_err",[]).append(str(b[1])[:40])
        time.sleep(0.04)
    out.append(r)
pool=concurrent.futures.ThreadPoolExecutor(32)
async def main():
    n=0; last=0; tend=mono()+DUR
    async with websockets.connect(FEED,max_size=None,compression="deflate",open_timeout=10) as ws:
        while mono()<tend:
            raw=await asyncio.wait_for(ws.recv(),timeout=5)
            t0=mono()
            fr=json.loads(raw)
            for m in fr.get("messages",[]):
                s=m.get("sequenceNumber")
                if s is None or s<=last: continue
                last=s; n+=1
                if n%EVERY==0: pool.submit(probe,s,t0)
    pool.shutdown(wait=True)
asyncio.run(main())
lags=collections.Counter(r.get("lag","E") for r in out)
print("samples",len(out)); print("lag (feed seq - rpc latest) at feed arrival:",sorted(lags.items(),key=lambda x:str(x[0])))
hv=sorted(r["have_ms"] for r in out if "have_ms" in r)
import statistics
if hv: print("block available after ms: p50",hv[len(hv)//2],"p90",hv[int(len(hv)*.9)],"p99",hv[min(len(hv)-1,int(len(hv)*.99))],"max",hv[-1],"missing",len(out)-len(hv))
print("errors:",sum(1 for r in out if "lag_err" in r or "poll_err" in r))
for r in out:
    if r.get("lag",0)>=4 or "lag_err" in r or "poll_err" in r or "have_ms" not in r: print(r)
json.dump(out,open(sys.argv[3] if len(sys.argv)>3 else "/dev/null","w"))
