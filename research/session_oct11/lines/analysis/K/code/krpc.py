"""K: minimal sequential JSON-RPC helper (read-only; one request at a time; backs off on 429). Caches under ../data."""
import json, time, gzip, os, urllib.request, urllib.error
from eth_utils import keccak
RPC = "https://rpc.mainnet.chain.robinhood.com"
H = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 Chrome/128", "Accept-Encoding": "gzip"}
K = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(K, "data"); OUT = os.path.join(K, "out")
CEN = os.path.join(os.path.dirname(os.path.dirname(K)), "census")
GAP = float(os.environ.get("GAP", "0.3")); _last = [0.0]; STATS = {"posts": 0, "429": 0, "errs": 0}
W = lambda d, i: int(d[2 + 64 * i: 2 + 64 * (i + 1)], 16)
A = lambda t: "0x" + t[-40:]
def sgn(x): return x - (1 << 256) if x >= (1 << 255) else x
def sig(s): return "0x" + keccak(text=s).hex()
def sel(s): return keccak(text=s).hex()[:8]

def post(body, tries=14):
    last = None
    for i in range(tries):
        g = time.time() - _last[0]
        if g < GAP: time.sleep(GAP - g)
        _last[0] = time.time()
        try:
            STATS["posts"] += 1
            r = urllib.request.urlopen(urllib.request.Request(RPC, json.dumps(body).encode(), H), timeout=120)
            raw = r.read(); data = gzip.decompress(raw) if r.headers.get("Content-Encoding") == "gzip" else raw
            out = json.loads(data)
            if isinstance(body, list) and not isinstance(out, list): last = out; time.sleep(3 + 2 * i); continue
            return out
        except urllib.error.HTTPError as e:
            last = e
            if e.code == 429: STATS["429"] += 1; time.sleep(min(60, 5 * (i + 1)))
            else: STATS["errs"] += 1; time.sleep(2 + i)
        except Exception as e:
            last = e; STATS["errs"] += 1; time.sleep(2 + 2 * i)
    raise RuntimeError(f"rpc failed: {str(last)[:300]}")

def rpc(m, p):
    r = post({"jsonrpc": "2.0", "id": 1, "method": m, "params": p})
    if "error" in r: raise RuntimeError(str(r["error"])[:300])
    return r["result"]

def batch(calls, size=40, tries=5):
    out = [None] * len(calls); todo = list(range(len(calls)))
    for a in range(tries):
        nxt = []
        for i in range(0, len(todo), size):
            ch = todo[i:i + size]
            r = post([{"jsonrpc": "2.0", "id": j, "method": calls[j][0], "params": calls[j][1]} for j in ch])
            got = {x.get("id"): x for x in r if isinstance(x, dict)}
            for j in ch:
                x = got.get(j)
                if x is None or "error" in x: nxt.append(j)
                else: out[j] = x.get("result")
        if not nxt: break
        todo = nxt; time.sleep(3 + 3 * a)
    return out

def logs(flt, a, b, maxspan=None):
    if maxspan and b - a + 1 > maxspan:
        res = []; x = a
        while x <= b:
            y = min(b, x + maxspan - 1); res += logs(flt, x, y); x = y + 1
        return res
    try: return rpc("eth_getLogs", [dict(flt, fromBlock=hex(a), toBlock=hex(b))])
    except RuntimeError as e:
        if b <= a: raise
        m = (a + b) // 2; return logs(flt, a, m) + logs(flt, m + 1, b)

def call(to, data, block="latest"):
    return rpc("eth_call", [{"to": to, "data": data}, block])

def jl_append(path, rows):
    with open(path, "a") as f:
        for r in rows: f.write(json.dumps(r) + "\n")

def jl_read(path):
    if not os.path.exists(path): return []
    return [json.loads(l) for l in open(path) if l.strip()]
