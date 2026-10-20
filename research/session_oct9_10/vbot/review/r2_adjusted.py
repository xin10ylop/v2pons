import pickle, json, statistics as st, collections
P = pickle.load(open('res_all.pkl', 'rb'))
rows = json.load(open('reaction.json'))
WL = {'0x93b07902'}
d = []
for r in rows:
    o = [b for b in r['buys'] if b['cls'] == 'OUTSIDE' and (b['from'] or '')[:10] not in WL and b['eth'] >= 1e-4]
    if o and r['pull_off'] is not None and r['pull_off'] >= o[0]['off']:
        d.append(r['pull_off'] - o[0]['off'])
N = len(d); F = lambda h: sum(1 for x in d if x <= h) / N
for stake in ('0.0012', '0.012', '0.1'):
    k = f'T+12|{stake}|b1|tp0.01|D42|s1'
    raw = []; adj = []; holds = []; exits = collections.Counter()
    for p in P:
        r = p['R'].get(k)
        if not r or r.get('ret') is None: continue
        exits[r['exit']] += 1; raw.append(r['ret'])
        if r['exit'] in ('buy_reverted', 'pulled', 'pull_before_buy'): adj.append(r['ret']); continue
        h = r['send'] + 1 - r['B']; holds.append(h); q = F(h)
        adj.append((1 - q) * r['ret'] + q * -1)
    hs = sorted(holds)
    print(stake, 'n', len(raw), 'raw mean %.4f median %.4f' % (st.mean(raw), st.median(raw)), 'adj mean %.4f' % st.mean(adj), dict(exits),
          'hold p5/p50/p95', hs[len(hs)//20], st.median(hs), hs[-len(hs)//20-1], 'min/max', hs[0], hs[-1])
# a sanity variant: what if the operator ignores 0.0012 ETH more than 0.0001 (reaction only with prob x)? break-even reaction prob
k = 'T+12|0.0012|b1|tp0.01|D42|s1'
for scale in (1.0, 0.5, 0.2, 0.1, 0.05, 0.03):
    adj = []
    for p in P:
        r = p['R'].get(k)
        if not r or r.get('ret') is None: continue
        if r['exit'] in ('buy_reverted', 'pulled', 'pull_before_buy'): adj.append(r['ret']); continue
        q = scale * F(r['send'] + 1 - r['B']); adj.append((1 - q) * r['ret'] - q)
    print('reaction prob x%.2f -> mean %.4f' % (scale, st.mean(adj)))
