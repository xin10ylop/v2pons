"""executor bbd947c3 dump events (a801e276) per 1M-block window, whole history; keep [bn, tx, token]"""
from lib3 import *
EX = '0xbbd947c36904eb5f28aeaa5593fbcb5a228551ad'; T = '0xa801e27679e1' 
head = int(rpc('eth_blockNumber', []), 16)
out = []; cnt = []; hi = head; empty = 0
while hi > 20000000 and empty < 4:
    lo = hi - 1000000 + 1
    r = logs({'address': EX}, lo, hi)
    c = {}
    for l in r: c[l['topics'][0][:10]] = c.get(l['topics'][0][:10], 0) + 1
    d = [[int(l['blockNumber'], 16), l['transactionHash'], '0x' + l['topics'][1][26:]] for l in r if l['topics'][0].startswith('0xa801e276')]
    out += d; cnt.append([lo, hi, len(r), c])
    print(lo, hi, len(r), c, flush=True)
    empty = empty + 1 if not r else 0
    hi = lo - 1; time.sleep(0.3)
out.sort()
json.dump({'head': head, 'dumps': out, 'cnt': cnt}, open('ex_hist.json', 'w'))
print('dumps', len(out), 'first', out[0] if out else None)
