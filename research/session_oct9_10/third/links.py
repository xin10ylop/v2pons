"""for executor dumps/sweeps in [lo,hi]: receipt -> collector(s) (wallet 0571d85f events); token -> launch (factory event) -> creator; cache: collector outflows"""
from lib3 import *
import lib2; import bc
from collections import defaultdict
lo, hi = int(sys.argv[1]), int(sys.argv[2])
dumps = [x for x in json.load(open('ex_dumps.json')) if lo <= x[0] <= hi]
fe = {e[2]: e for e in json.load(open('fac_events.json'))['keep']}
SW = '0x0571d85fc9cce8d2ebf18e983becef6cc884e37503f377f9b6383d65850f96d2'
out = []
for bn, h, tok, nh, eth, nsw, sweth in dumps:
    rc = rpc('eth_getTransactionReceipt', [h])
    col = defaultdict(float); wal = set()
    for l in rc['logs']:
        if l['topics'][0] == SW:
            col['0x' + l['topics'][2][26:]] += int(l['data'][2:66], 16) / 1e18; wal.add(l['address'].lower())
    tk = tok[0] if tok else None
    la = fe.get(tk)
    r = dict(bn=bn, tx=h, kind='dump' if tok else 'sweep', token=tk, launch_bn=la[0] if la else None, creator=la[4] if la else None, curve=la[3] if la else None,
             quote=la[5] if la else None, wallets=sorted(wal), collectors={k: round(v, 6) for k, v in col.items()}, nh=nh, eth=eth, sweth=sweth)
    out.append(r)
    print(bn, r['kind'], tk and tk[:10], 'launch', r['launch_bn'], 'delay', (bn - r['launch_bn']) if r['launch_bn'] else None, 'creator', (r['creator'] or '')[:10],
          'wallets', len(wal), 'to', {k[:10]: v for k, v in r['collectors'].items()})
json.dump(out, open('links_%d_%d.json' % (lo, hi), 'w'), indent=0)
