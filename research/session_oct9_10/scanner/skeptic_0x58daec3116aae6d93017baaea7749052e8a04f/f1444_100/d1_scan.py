# money trace helpers: scan full blocks for transactions touching a set of addresses (to == addr, from == addr, or addr inside calldata)
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
import hashlib
def scan(a, b, addrs, cache_tag):
    addrs = {x.lower() for x in addrs}; needles = {x[2:] for x in addrs}
    p = os.path.join(HERE, 'data', 'scan', f'{cache_tag}_{a}_{b}.json')
    os.makedirs(os.path.dirname(p), exist_ok=True)
    if os.path.exists(p): return json.load(open(p))
    hits = []
    for s in range(a, b + 1, 50):
        bl = batch([("eth_getBlockByNumber", [hex(n), True]) for n in range(s, min(s + 50, b + 1))])
        for B in bl:
            if not B: continue
            for t in B['transactions']:
                fr = t['from'].lower(); to = (t['to'] or '').lower(); inp = t['input'].lower()
                if fr in addrs or to in addrs or any(n in inp for n in needles):
                    hits.append(dict(bn=int(B['number'], 16), ts=int(B['timestamp'], 16), hash=t['hash'], frm=fr, to=to, value=int(t['value'], 16), nonce=int(t['nonce'], 16),
                                     sel=t['input'][2:10], clen=(len(t['input']) - 2) // 2, which=[x for x in addrs if x == fr or x == to or x[2:] in inp]))
    json.dump(hits, open(p, 'w'))
    return hits
