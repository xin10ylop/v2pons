"""Compact block cache + scanners. Cache: bc/<c>.json for 1000-block chunks (legacy) or bc/q<c>.json for 250-block chunks
{bn: [ts, [[hash, from, to, value_str, nonce, sel, inputlen, idx], ...]]}."""
import sys, json, os, time, threading, random, urllib.request, urllib.error
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import rpc, RPC, H
D = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops/lch/bc/"
os.makedirs(D, exist_ok=True)
CH = 250
_mem = {}
_lock = threading.Lock()
STATS = {"req": 0, "429": 0}
def post(body):
    for i in range(60):
        try:
            STATS["req"] += 1
            return json.load(urllib.request.urlopen(urllib.request.Request(RPC, json.dumps(body).encode(), H), timeout=90))
        except urllib.error.HTTPError as e:
            STATS["429"] += 1; time.sleep(0.4 + random.random() * (1.0 + 0.2 * i))
        except Exception: time.sleep(1 + i)
    raise RuntimeError("rpc")
def _getblocks(bns):
    """fetch blocks by number; items failing in a batch (e.g. 'response too large') are retried in smaller batches"""
    got = {}; todo = list(bns); size = 50; rounds = 0
    while todo:
        rounds += 1
        if rounds > 200: raise RuntimeError("blocks %d" % todo[0])
        nxt = []
        for i in range(0, len(todo), size):
            ch = todo[i:i + size]
            r = post([{"jsonrpc": "2.0", "id": j, "method": "eth_getBlockByNumber", "params": [hex(b), True]} for j, b in enumerate(ch)])
            if not isinstance(r, list): nxt += ch; continue
            ok = {x["id"]: x["result"] for x in r if "result" in x and x["result"]}
            for j, b in enumerate(ch):
                if j in ok: got[b] = ok[j]
                else: nxt.append(b)
        if nxt and len(nxt) == len(todo): time.sleep(1)
        todo = nxt; size = max(1, size // 2) if todo else size
    return got
def _fetch(lo, hi):
    out = {}
    for bn, blk in _getblocks(range(lo, hi)).items():
        out[bn] = [int(blk["timestamp"], 16), [[t["hash"], t["from"].lower(), (t.get("to") or "").lower(), str(int(t["value"], 16)), int(t["nonce"], 16),
                    t["input"][:10], (len(t["input"]) - 2) // 2, int(t["transactionIndex"], 16)] for t in blk["transactions"]]]
    return out
def chunk(c):
    if c in _mem: return _mem[c]
    big = D + "%d.json" % (c * CH // 1000)
    fn = D + "q%d.json" % c
    if os.path.exists(big):
        dd = {int(k): v for k, v in json.load(open(big)).items()}
        d = {k: v for k, v in dd.items() if c * CH <= k < (c + 1) * CH}
    elif os.path.exists(fn):
        d = {int(k): v for k, v in json.load(open(fn)).items()}
    else:
        d = _fetch(c * CH, (c + 1) * CH)
        json.dump(d, open(fn + ".tmp%d" % os.getpid(), "w")); os.rename(fn + ".tmp%d" % os.getpid(), fn)
    with _lock:
        if len(_mem) > 1600: _mem.clear()
        _mem[c] = d
    return d
def txs(lo, hi):
    for c in range(lo // CH, hi // CH + 1):
        d = chunk(c)
        for bn in range(max(lo, c * CH), min(hi, c * CH + CH - 1) + 1):
            if bn in d:
                ts, tl = d[bn]
                for t in tl: yield bn, ts, t
def txs_desc(lo, hi):
    for c in range(hi // CH, lo // CH - 1, -1):
        d = chunk(c)
        for bn in range(min(hi, c * CH + CH - 1), max(lo, c * CH) - 1, -1):
            if bn in d:
                ts, tl = d[bn]
                for t in tl: yield bn, ts, t
