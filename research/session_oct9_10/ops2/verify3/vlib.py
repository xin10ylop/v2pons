"""verify3 helpers: read the shared bc cache (no RPC) and a gentle block fetch for small uncached ranges."""
import sys, os, json, time, random, urllib.request, urllib.error, pickle
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import RPC, H
D = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops/lch/bc/"
MY = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops2/verify3/blk.pkl"
try: MB = pickle.load(open(MY, "rb"))
except Exception: MB = {}
_c = {}
def chunk(c):
    if c in _c: return _c[c]
    p = D + "q%d.json" % c; d = None
    if os.path.exists(p):
        try: d = {int(k): v for k, v in json.load(open(p)).items()}
        except Exception: d = None
    if d is None:
        p2 = D + "%d.json" % (c * 250 // 1000)
        if os.path.exists(p2):
            try: d = {int(k): v for k, v in json.load(open(p2)).items() if c * 250 <= int(k) < c * 250 + 250}
            except Exception: d = None
    _c[c] = d; return d
def post(body):
    for i in range(30):
        try:
            r = json.load(urllib.request.urlopen(urllib.request.Request(RPC, json.dumps(body).encode(), H), timeout=90)); time.sleep(0.3); return r
        except urllib.error.HTTPError: time.sleep(min(30, 3 + 2 * i) + random.random())
        except Exception: time.sleep(min(30, 2 + i))
    raise RuntimeError("rpc")
def block(bn, fetch=True):
    """[(hash, from, to, value_wei, nonce, sel)] for block bn from cache, else fetched (and kept in my own pickle)"""
    c = chunk(bn // 250)
    if c and bn in c: return [(x[0], x[1], x[2], int(x[3]), x[4], x[5]) for x in c[bn][1]]
    if bn in MB: return MB[bn]
    if not fetch: return None
    return fetch_range(bn, bn)[bn]
def fetch_range(lo, hi):
    need = [b for b in range(lo, hi + 1) if b not in MB and not ((chunk(b // 250) or {}).get(b))]
    for i in range(0, len(need), 25):
        ch = need[i:i + 25]
        r = post([{"jsonrpc": "2.0", "id": j, "method": "eth_getBlockByNumber", "params": [hex(b), True]} for j, b in enumerate(ch)])
        ok = {x["id"]: x.get("result") for x in r} if isinstance(r, list) else {}
        for j, b in enumerate(ch):
            blk = ok.get(j)
            if blk: MB[b] = [(x["hash"], x["from"].lower(), (x.get("to") or "").lower(), int(x["value"], 16), int(x["nonce"], 16), x["input"][:10]) for x in blk["transactions"]]
        time.sleep(1.0)
    pickle.dump(MB, open(MY, "wb"))
    return {b: block(b, fetch=False) for b in range(lo, hi + 1)}
def touching(addrs, lo, hi, fetch=True):
    A = {a.lower() for a in addrs}
    if fetch: fetch_range(lo, hi)
    out = []
    for b in range(lo, hi + 1):
        tl = block(b, fetch=False)
        if tl is None: continue
        for t in tl:
            if t[1] in A or t[2] in A: out.append((b,) + tuple(t))
    return out
def cached(lo, hi):
    return sum(1 for b in range(lo, hi + 1) if block(b, fetch=False) is not None)
