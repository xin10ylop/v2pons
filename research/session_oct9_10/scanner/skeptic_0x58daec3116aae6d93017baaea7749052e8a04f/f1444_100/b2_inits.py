# scan PoolManager Initialize logs with currency0 = ETH over [A, B], keep fee/ts combos of this family (100/1, 500/10) with hooks 0
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
A = int(sys.argv[1]); B = int(sys.argv[2])
os.makedirs(os.path.join(HERE, 'data', 'inits'), exist_ok=True)
Z = "0x" + "0" * 64
step = 100000
for a in range(A - A % step, B + 1, step):
    p = os.path.join(HERE, 'data', 'inits', f'{a}.json')
    b = min(a + step - 1, B)
    if os.path.exists(p):
        d = json.load(open(p))
        if d['to'] >= b: continue
    L = logs({"address": PM, "topics": [T_INIT, None, Z]}, a, b)
    keep = []
    for l in L:
        d = l['data']; fee = W(d, 0); ts = sgn(W(d, 1)); hooks = W(d, 2); sp = W(d, 3); tick = sgn(W(d, 4))
        if hooks == 0 and (fee, ts) in ((100, 1), (500, 10)):
            keep.append(dict(bn=int(l['blockNumber'], 16), tx=l['transactionHash'], pid=l['topics'][1], token='0x' + l['topics'][3][-40:], fee=fee, ts=ts, sp=sp, tick=tick, li=int(l['logIndex'], 16)))
    json.dump({'from': a, 'to': b, 'n_all': len(L), 'keep': keep}, open(p, 'w'))
    print(a, b, len(L), len(keep), flush=True)
