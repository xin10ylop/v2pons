"""Block fetcher sharing the ops/lch/bc cache format (q<c>.json = 250 blocks {bn: [ts, [[hash, from, to, value, nonce, sel, inputlen, idx]...]]}).
Small batches (20) with backoff on 429, to share the public RPC politely."""
import sys, json, os, time, random, urllib.request, urllib.error
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import RPC, H, rpc
D = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops/lch/bc/"
CH = 250; BS = 20
STATS = {"req": 0, "429": 0}
def post(body):
    back = 1.0
    for i in range(80):
        try:
            STATS["req"] += 1
            return json.load(urllib.request.urlopen(urllib.request.Request(RPC, json.dumps(body).encode(), H), timeout=90))
        except urllib.error.HTTPError as e:
            STATS["429"] += 1; time.sleep(back + random.random()); back = min(back * 1.5, 20)
        except Exception: time.sleep(2 + i)
    raise RuntimeError("rpc")
def _blocks(bns):
    got = {}; todo = list(bns)
    while todo:
        ch = todo[:BS]; todo = todo[BS:]
        r = post([{"jsonrpc": "2.0", "id": j, "method": "eth_getBlockByNumber", "params": [hex(b), True]} for j, b in enumerate(ch)])
        bad = []
        if isinstance(r, list):
            ok = {x["id"]: x["result"] for x in r if x.get("result")}
            for j, b in enumerate(ch):
                if j in ok: got[b] = ok[j]
                else: bad.append(b)
        else: bad = ch
        if bad:
            time.sleep(1.5)
            if len(bad) == len(ch) and len(ch) > 1:   # maybe "too large": retry one by one
                for b in bad:
                    rr = post({"jsonrpc": "2.0", "id": 1, "method": "eth_getBlockByNumber", "params": [hex(b), True]})
                    if rr.get("result"): got[b] = rr["result"]
                    else: todo.append(b)
            else: todo = bad + todo
        time.sleep(0.15)
    return got
def chunk(c):
    big = D + "%d.json" % (c * CH // 1000); fn = D + "q%d.json" % c
    if os.path.exists(big):
        dd = {int(k): v for k, v in json.load(open(big)).items()}
        return {k: v for k, v in dd.items() if c * CH <= k < (c + 1) * CH}
    if os.path.exists(fn):
        try: return {int(k): v for k, v in json.load(open(fn)).items()}
        except Exception: pass
    out = {}
    for bn, blk in _blocks(range(c * CH, (c + 1) * CH)).items():
        out[bn] = [int(blk["timestamp"], 16), [[t["hash"], t["from"].lower(), (t.get("to") or "").lower(), str(int(t["value"], 16)), int(t["nonce"], 16),
                   t["input"][:10], (len(t["input"]) - 2) // 2, int(t["transactionIndex"], 16)] for t in blk["transactions"]]]
    tmp = fn + ".tmp%d" % os.getpid(); json.dump(out, open(tmp, "w")); os.rename(tmp, fn)
    return out
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
                for t in tl[::-1]: yield bn, ts, t
def cached(c): return os.path.exists(D + "q%d.json" % c) or os.path.exists(D + "%d.json" % (c * CH // 1000))
