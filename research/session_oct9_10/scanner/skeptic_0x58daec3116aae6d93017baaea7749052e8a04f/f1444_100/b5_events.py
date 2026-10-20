# Swap + ModifyLiquidity logs for every candidate pool over [launch, launch + 3000]
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
C = json.load(open(os.path.join(HERE, 'data/cands.json')))
p = os.path.join(HERE, 'data', 'events.json')
EV = json.load(open(p)) if os.path.exists(p) else {}
HEAD = int(rpc('eth_blockNumber', []), 16)
todo = [c for c in C if c['pid'] not in EV or (EV[c['pid']]['to'] < c['bn'] + 3000 and EV[c['pid']]['to'] < HEAD - 5)]
groups = []; g = []
for c in todo:
    if g and (len(g) >= 20 or c['bn'] - g[0]['bn'] > 20000): groups.append(g); g = []
    g.append(c)
if g: groups.append(g)
print('groups', len(groups))
for g in groups:
    a = g[0]['bn']; b = min(g[-1]['bn'] + 3000, HEAD - 5)
    L = logs({"address": PM, "topics": [[T_SWAP, T_ML], [c['pid'] for c in g]]}, a, b)
    by = {c['pid']: {'swaps': [], 'mods': [], 'to': min(c['bn'] + 3000, b)} for c in g}
    for l in L:
        pid = l['topics'][1]; c = by[pid]; d = l['data']; bn = int(l['blockNumber'], 16)
        base = dict(bn=bn, ti=int(l['transactionIndex'], 16), li=int(l['logIndex'], 16), tx=l['transactionHash'], sender='0x' + l['topics'][2][-40:])
        if l['topics'][0] == T_SWAP:
            c['swaps'].append(dict(base, a0=sgn(W(d, 0)), a1=sgn(W(d, 1)), sp=W(d, 2), liq=W(d, 3), tick=sgn(W(d, 4)), fee=W(d, 5)))
        else:
            c['mods'].append(dict(base, lo=sgn(W(d, 0)), hi=sgn(W(d, 1)), dl=sgn(W(d, 2))))
    for pid, c in by.items():
        c['swaps'].sort(key=lambda s: (s['bn'], s['li'])); c['mods'].sort(key=lambda s: (s['bn'], s['li']))
        EV[pid] = c
    json.dump(EV, open(p, 'w'))
    print(a, b, len(L), flush=True)
