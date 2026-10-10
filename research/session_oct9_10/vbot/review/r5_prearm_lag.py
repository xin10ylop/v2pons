import sys, collections
sys.path.insert(0, '/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/vbot/react')
from common import load, classifier, COV
P, TX, M = load(); BOTW, cls = classifier(TX)
rows = collections.defaultdict(list)
for v in P.values():
    lim = min(COV[v['src']], v['pull'] if v['pull'] is not None else 10**9)
    seq = []; ok = True
    for s in v['sw']:
        if s['rel'] > min(lim, 80): break
        k, t = cls(v, s)
        if k is None: ok = False; break
        seq.append((s, k, t))
    if not ok: continue
    bb = [s['rel'] for s, k, t in seq if k == 'bot' and s['eth'] > 0]
    pre = [(s, t) for s, k, t in seq if k == 'out' and s['eth'] >= 3e-5 and (not bb or s['rel'] < bb[0])]
    if not pre: continue
    s, t = pre[0]
    rows[(v['fam'], t['from'][:10])].append((v['src'], s['rel'], round(s['eth'], 6), bb[0] if bb else None, v['pull'], (v['pull'] - s['rel']) if v['pull'] is not None else None, (v['pull'] - bb[0]) if (v['pull'] is not None and bb) else None))
for k, xs in sorted(rows.items()):
    if k[1] == '0xf6e55480':
        lag = [x[5] for x in xs if x[5] is not None]
        print(k, len(xs), 'pulled within 25 of its buy:', sum(1 for l in lag if l <= 25), 'within 60:', sum(1 for l in lag if l <= 60)); continue
    print(k, len(xs))
    for x in xs: print('   src %s outsider +%d %.6f ETH | bot1 %s | pull %s | pull-outsider %s | pull-bot1 %s' % x)
