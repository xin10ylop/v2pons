import json, statistics as st, collections
rows = json.load(open('reaction.json'))
WL = {'0x93b07902'}
def outside(b, thr):
    return b['cls'] == 'OUTSIDE' and (b['from'] or '')[:10] not in WL and b['eth'] >= thr
for thr in (1e-4, 3e-5):
    for src in ('census', 'new', None):
        d = []; never = []; wallets = set()
        for r in rows:
            if src and r['src'] != src: continue
            if any(b['cls'] == '?' for b in r['buys']): continue
            o = [b for b in r['buys'] if outside(b, thr)]
            if not o: continue
            wallets.add(o[0]['from'][:10])
            if r['pull_off'] is None or r['pull_off'] < o[0]['off']:
                never.append(r['b0']); continue
            d.append(r['pull_off'] - o[0]['off'])
        N = len(d) + len(never)
        cdf = {h: round(sum(1 for x in d if x <= h) / N, 3) for h in (2, 3, 5, 10, 12, 13, 15, 21, 25, 60)} if N else {}
        print(f'thr {thr} src {src}: n {N} pulled {len(d)} never {len(never)} median {st.median(d) if d else None} wallets {len(wallets)} cdf {cdf}')
# background: pools with no outside buy (non-WL, any size), P(pull in a window)
no = [r for r in rows if not [b for b in r['buys'] if b['cls']=='OUTSIDE' and (b['from'] or '')[:10] not in WL]]
print('no-outside pools', len(no), 'pulled<=45', sum(1 for r in no if r['pull_off'] is not None and r['pull_off']<=45), 'pulled<=60', sum(1 for r in no if r['pull_off'] is not None and r['pull_off']<=60))
# among pools pulled by +45: how many had an outside (non-WL any size) buy before the pull
p45 = [r for r in rows if r['pull_off'] is not None and r['pull_off'] <= 45]
had = [r for r in p45 if any(b['cls']=='OUTSIDE' and (b['from'] or '')[:10] not in WL and b['off'] <= r['pull_off'] for b in r['buys'])]
print('pulled <=45:', len(p45), 'with an outside buy before:', len(had))
