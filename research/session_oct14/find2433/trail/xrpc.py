"""Paced read-only JSON-RPC to the public publicnode endpoints of other chains (>= 0.5 s between posts, back-off on errors)."""
import json, ssl, urllib.request, urllib.error, time
CTX = ssl.create_default_context(cafile="/root/.ccr/ca-bundle.crt"); H = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
URL = {"ethereum": "https://ethereum-rpc.publicnode.com", "base": "https://base-rpc.publicnode.com", "arbitrum": "https://arbitrum-one-rpc.publicnode.com",
       "unichain": "https://unichain-rpc.publicnode.com", "bsc": "https://bsc-rpc.publicnode.com", "optimism": "https://optimism-rpc.publicnode.com",
       "bsc_archive": "https://bsc-mainnet.public.blastapi.io", "bsc_drpc": "https://bsc.drpc.org",
       "eth_archive": "https://eth-mainnet.public.blastapi.io", "base_archive": "https://base-mainnet.public.blastapi.io",
       "eth_drpc": "https://eth.drpc.org"}
_last = [0.0]
def post(chain, body):
    err = None
    for i in range(12):
        dt = time.time() - _last[0]
        if dt < 0.5: time.sleep(0.5 - dt)
        _last[0] = time.time()
        try: return json.load(urllib.request.urlopen(urllib.request.Request(URL[chain], json.dumps(body).encode(), H), timeout=60, context=CTX))
        except urllib.error.HTTPError as e:
            err = e
            if e.code not in (429, 502, 503, 504): raise RuntimeError("http %s %s" % (e.code, e.read()[:200]))
            time.sleep(min(20, 2 * (i + 1)))
        except Exception as e: err = e; time.sleep(min(20, 2 * (i + 1)))
    raise RuntimeError("rpc failed %s" % err)
def call(chain, m, p):
    d = post(chain, {"jsonrpc": "2.0", "id": 1, "method": m, "params": p})
    if "error" in d: raise RuntimeError(str(d["error"])[:300])
    return d["result"]
def batch(chain, m, plist, n=10):
    out = []
    for i in range(0, len(plist), n):
        d = post(chain, [{"jsonrpc": "2.0", "id": j, "method": m, "params": p} for j, p in enumerate(plist[i:i + n])])
        if isinstance(d, dict): d = [d]
        d = sorted(d, key=lambda x: x["id"]); out += [x.get("result") for x in d]
    return out
