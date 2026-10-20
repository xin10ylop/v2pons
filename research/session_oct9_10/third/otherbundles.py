"""launches in cached window with >=6 distinct buyers within 100 blocks but no dispatcher burst: who are the buyers, how were they funded (any tx touching them in prior 3000 blocks)"""
from lib3 import *
import lib2, bc
from collections import defaultdict, Counter
cl = json.load(open('classify_84116000_84147499.json'))
cand = [r for r in cl if r['burst'] < 8 and r['n_buys_10s'] >= 6]
for r in cand:
    L = r['bn']
    buys = [(bn, t) for bn, ts, t in bc.txs(L, L + 100) if t[2] == r['curve'] or t[5] in ('0xdb61c76e', '0x926ae287')]
    B = sorted(set(t[1] for _, t in buys))
    nonces = [t[4] for _, t in buys]
    inc = defaultdict(list)
    for bn, ts, t in bc.txs(max(84116000, L - 3000), L):
        if t[2] in B and int(t[3]) > 0: inc[t[2]].append((bn - L, t[1], int(t[3]) / 1e18, t[5]))
        if t[1] in B: inc[t[1]].append((bn - L, 'OUT->' + t[2][:10], int(t[3]) / 1e18, t[5]))
    srcs = Counter(x[1] for v in inc.values() for x in v if not x[1].startswith('OUT'))
    print('==', L, r['utc'], 'creator', r['creator'][:10], r['deleg'][:10], 'buyers', len(B), 'buy nonces', sorted(Counter(nonces).items())[:6], 'funded-in-window', len([b for b in B if inc[b]]), 'srcs', srcs.most_common(3))
