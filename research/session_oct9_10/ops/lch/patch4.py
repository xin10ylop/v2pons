s=open('bc.py').read()
a=s.index('def _fetch('); b=s.index('def chunk(')
s=s[:a]+'''def _getblocks(bns):
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
'''+s[b:]
open('bc.py','w').write(s)
