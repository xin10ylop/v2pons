import json, urllib.request
H = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
URLS = ["https://bsc-rpc.publicnode.com", "https://bsc-dataseed1.defibit.io", "https://bsc-dataseed.bnbchain.org"]
def _one(U, body, t=40):
    req = urllib.request.Request(U, json.dumps(body).encode(), H)
    return json.load(urllib.request.urlopen(req, timeout=t))
def rpc(m, p):
    last=None
    for U in URLS:
        try:
            r=_one(U,{"jsonrpc":"2.0","id":1,"method":m,"params":p})
            if "result" in r: return r["result"]
            last={"__err__":r.get("error"),"url":U}
        except Exception as e: last={"__err__":str(e),"url":U}
    return last
def batch(calls, t=60):
    body=[{"jsonrpc":"2.0","id":i,"method":m,"params":p} for i,(m,p) in enumerate(calls)]
    for U in URLS:
        try:
            r=_one(U,body,t)
            if isinstance(r,list):
                out={x["id"]:x.get("result",x.get("error")) for x in r}
                return [out.get(i) for i in range(len(calls))]
        except Exception: pass
    return [None]*len(calls)
