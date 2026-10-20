"""small block cache for sampling: third/blk/<bn//100>.json; tx = [hash, from, to, value_str, nonce, sel, inputlen]"""
from lib3 import *
import os
BD = os.path.dirname(os.path.abspath(__file__)) + '/blk/'
def _get(bns):
    got = {}; todo = list(bns); size = 25
    for _ in range(60):
        if not todo: break
        nxt = []
        for i in range(0, len(todo), size):
            ch = todo[i:i+size]
            try: r = post([{"jsonrpc": "2.0", "id": j, "method": "eth_getBlockByNumber", "params": [hex(b), True]} for j, b in enumerate(ch)])
            except Exception: r = None
            if not isinstance(r, list): nxt += ch; time.sleep(3); continue
            ok = {x['id']: x['result'] for x in r if x.get('result')}
            for j, b in enumerate(ch):
                if j in ok: got[b] = ok[j]
                else: nxt.append(b)
            time.sleep(0.2)
        if nxt: time.sleep(2); size = max(1, size // 2)
        todo = nxt
    if todo: raise RuntimeError('blocks missing %s' % todo[:3])
    return got
def chunk(c):
    p = BD + '%d.json' % c
    if os.path.exists(p): return {int(k): v for k, v in json.load(open(p)).items()}
    # reuse the shared bc cache when it has the range
    try:
        import lib2, bc
        if lib2.have(c * 100 // bc.CH):
            d = bc.chunk(c * 100 // bc.CH)
            return {bn: d[bn] for bn in range(c * 100, c * 100 + 100) if bn in d}
    except Exception: pass
    g = _get(range(c * 100, c * 100 + 100))
    d = {bn: [int(b['timestamp'], 16), [[t['hash'], t['from'].lower(), (t.get('to') or '').lower(), str(int(t['value'], 16)), int(t['nonce'], 16), t['input'][:10], (len(t['input']) - 2) // 2] for t in b['transactions']]] for bn, b in g.items()}
    json.dump(d, open(p, 'w'))
    return d
def txs(lo, hi):
    for c in range(lo // 100, hi // 100 + 1):
        d = chunk(c)
        for bn in range(max(lo, c * 100), min(hi, c * 100 + 99) + 1):
            if bn in d:
                ts, tl = d[bn]
                for t in tl: yield bn, ts, t
