# trace one pool's money: crowd wallets' funding, the launch wallet's funding, and where the pull's proceeds go
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from d1_scan import scan
R = {r['pid'][:10]: r for r in json.load(open(os.path.join(HERE, 'data/rows.json')))}
pid = sys.argv[1]; r = R[pid]; lb = r['lb']
cr = [s for s in r['swaps'] if s['crowd']]
pulls = [m for m in r['mods'] if m['dl'] < 0]
out = {'pid': pid, 'launcher': r['launcher'], 'lb': lb}
# 1. crowd wallets 0..2: funding within 400 blocks before their buy
for s in cr[:int(sys.argv[2]) if len(sys.argv) > 2 else 3]:
    h = scan(s['bn'] - 400, s['bn'], [s['frm']], 'crowd_' + s['frm'][:10])
    print('CROWD', s['frm'], 'buy', s['bn'], s['eth'] / 1e18)
    for x in h: print('   ', x['bn'] - s['bn'], x['frm'], '->', x['to'], x['value'] / 1e18, 'n', x['nonce'], x['sel'], x['clen'])
# 2. after the pull: the launch wallet's next transactions (300 blocks)
if pulls:
    pb = lb + pulls[0]['rel']
    h = scan(pb, pb + 300, [r['launcher']], 'post_' + r['launcher'][:10])
    print('POST-PULL', r['launcher'], 'pull block', pb)
    for x in h: print('   ', x['bn'] - pb, x['frm'], '->', x['to'], x['value'] / 1e18, 'n', x['nonce'], x['sel'], x['clen'])
