# pool 0xcee0878d: the launch wallet's whole life (funding before the launch, everything after the pull), and the crowd's funding before the launch
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from d1_scan import scan
R = {r['pid'][:10]: r for r in json.load(open(os.path.join(HERE, 'data/rows.json')))}
pid = sys.argv[1]; r = R[pid]; lb = r['lb']; L = r['launcher']
cr = [s for s in r['swaps'] if s['crowd']]
pulls = [m for m in r['mods'] if m['dl'] < 0]; pb = lb + pulls[0]['rel']
back = int(sys.argv[2]); fwd = int(sys.argv[3])
h = scan(lb - back, lb + 5, [L] + [s['frm'] for s in cr], 'pre_' + pid)
print('BEFORE LAUNCH (launch wallet + 10 crowd wallets)', L)
for x in h: print('   ', x['bn'] - lb, x['frm'][:12], '->', x['to'][:12], round(x['value'] / 1e18, 6), 'n', x['nonce'], x['sel'], x['clen'], 'touches', [w[:10] for w in x['which']])
h = scan(pb + 301, pb + fwd, [L], 'post2_' + pid)
print('AFTER PULL +301..', fwd)
for x in h: print('   ', x['bn'] - pb, x['frm'][:12], '->', x['to'][:12], round(x['value'] / 1e18, 6), 'n', x['nonce'], x['sel'], x['clen'])
