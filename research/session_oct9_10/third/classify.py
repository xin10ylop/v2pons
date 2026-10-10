"""classify launches inside a cached block window: creator funding pattern (dispatcher burst), crowd buys, creator 7702 delegate"""
from lib3 import *
import lib2; import bc
from collections import defaultdict, Counter
lo, hi = int(sys.argv[1]), int(sys.argv[2])
d = json.load(open('fac_events.json'))
L = [e for e in d['keep'] if lo + 300 <= e[0] <= hi - 300]
pots = set(json.load(open('pots_addrs.json')))
# plain transfers in window
pin = defaultdict(list); pout = defaultdict(list); calls_to = defaultdict(list)
for bn, ts, t in bc.txs(lo - 0, hi):
    h, f, to, v, n, sel, ln, idx = t
    if int(v) > 0 and ln == 0:
        pin[to].append((bn, f, int(v) / 1e18, n)); pout[f].append((bn, to, int(v) / 1e18, n))
    if to: calls_to[to].append((bn, f, sel, int(v) / 1e18, n))
codes = batch([('eth_getCode', [e[4], 'latest']) for e in L])
res = []
for e, code in zip(L, codes):
    bn, tx, token, curve, creator = e[:5]
    fund = [x for x in pin[creator] if x[0] <= bn]
    src = fund[-1][1] if fund else None
    burst = [x for x in pout.get(src, []) if abs(x[0] - fund[-1][0]) <= 30] if src else []
    buys = [x for x in calls_to[curve] if bn <= x[0] <= bn + 600 and x[2] == '0x59a87bc1']
    deleg = (code or '0x')[8:48] if (code or '').startswith('0xef0100') else ('eoa' if code in ('0x', None) else 'contract')
    r = dict(bn=bn, utc=utc(bc.chunk(bn // bc.CH)[bn][0]), token=token, curve=curve, creator=creator, q=e[5], deleg=deleg,
             fund_src=src, fund_eth=fund[-1][2] if fund else None, burst=len(burst), burst_eth=round(sum(x[2] for x in burst), 4),
             src_in_pots=src in pots, creator_in_pots=creator in pots, n_buys_10s=len(set(x[1] for x in buys if x[0] <= bn + 100)), n_buys_60s=len(set(x[1] for x in buys)))
    res.append(r)
json.dump(res, open('classify_%d_%d.json' % (lo, hi), 'w'), indent=0)
for r in res:
    print(r['bn'], r['utc'], r['creator'][:10], r['deleg'][:10], 'q', 'ETH' if r['q'] == 0 else hex(r['q'])[:10], 'src', (r['fund_src'] or '-')[:10], r['fund_eth'] and round(r['fund_eth'], 4),
          'burst', r['burst'], r['burst_eth'], 'pots' if (r['src_in_pots'] or r['creator_in_pots']) else '', 'buy10s', r['n_buys_10s'], 'buy60s', r['n_buys_60s'])
print(Counter(r['deleg'][:10] for r in res))
print('dispatcher-funded (burst>=8):', sum(1 for r in res if r['burst'] >= 8), 'of', len(res))
