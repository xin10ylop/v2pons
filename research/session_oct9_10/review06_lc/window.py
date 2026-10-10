import asyncio, json, time, sys, urllib.request, concurrent.futures, collections
import websockets
RPC="https://rpc.mainnet.chain.robinhood.com"; FEED="wss://feed.mainnet.chain.robinhood.com"
DUR=float(sys.argv[1]); EVERY=int(sys.argv[2])
mono=time.monotonic; feed={"seq":0}
def rpc(m,p,timeout=3):
    req=urllib.request.Request(RPC,json.dumps({"jsonrpc":"2.0","id":1,"method":m,"params":p}).encode(),{"Content-Type":"application/json","User-Agent":"Mozilla/5.0 Chrome/128"})
    try: d=json.load(urllib.request.urlopen(req,timeout=timeout))
    except Exception as e: return ("exc",str(e)[:60])
    return ("ok",d["result"]) if "result" in d else ("err",d.get("error"))
out=[]
def code_like(L,k,r):
    a=rpc("eth_getBlockByNumber",[hex(L-k),False]); r[f"m{k}"]= "have" if (a[0]=="ok" and a[1]) else ("null" if a[0]=="ok" else "E:"+str(a[1])[:30])
def probe(L,t0):
    r={"L":L}
    ths=[pool2.submit(code_like,L,k,r) for k in (7,8)]
    while mono()<t0+2.0:
        b=rpc("eth_getBlockByNumber",[hex(L),False],timeout=2)
        if b[0]=="ok" and b[1]: r["rcpt_ms"]=round(1000*(mono()-t0)); r["rcpt_at_feed"]=feed["seq"]-L; break
        if b[0]!="ok": r["poll_err"]=r.get("poll_err",0)+1
        time.sleep(0.04)
    for t in ths: t.result()
    out.append(r)
pool=concurrent.futures.ThreadPoolExecutor(64); pool2=concurrent.futures.ThreadPoolExecutor(64)
async def main():
    n=0; tend=mono()+DUR
    async with websockets.connect(FEED,max_size=None,compression="deflate",open_timeout=10) as ws:
        while mono()<tend:
            fr=json.loads(await asyncio.wait_for(ws.recv(),timeout=5)); t0=mono()
            for m in fr.get("messages",[]):
                s=m.get("sequenceNumber")
                if s is None or s<=feed["seq"]: continue
                feed["seq"]=s; n+=1
                if n%EVERY==0: pool.submit(probe,s,t0)
    pool.shutdown(wait=True)
asyncio.run(main())
N=len(out); print("samples",N)
for k in (7,8): print(f"block L-{k} missing at feed time:",collections.Counter(r[f'm{k}'] for r in out))
print("receipt-equivalent arrives when the feed shows L+",sorted(collections.Counter(r.get('rcpt_at_feed','none') for r in out).items(),key=str))
# the finding's window: L-k missing at T0 but block L in time for the seat (armed before the feed shows L+7)
for k in (7,8):
    w=[r for r in out if r[f"m{k}"]!="have" and isinstance(r.get("rcpt_at_feed"),int) and r["rcpt_at_feed"]<=6]
    late=[r for r in out if isinstance(r.get("rcpt_at_feed"),int) and r["rcpt_at_feed"]>6 or "rcpt_at_feed" not in r]
    print(f"deploy at L-{k}: code missing AND receipt in time: {len(w)}/{N}; receipt too late for the seat anyway: {len(late)}/{N}")
json.dump(out,open("window_out.json","w"))
