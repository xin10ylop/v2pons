# the closest analog of our trade: an outside wallet that bought >= X ETH BEFORE the first crowd buy and still held at the first crowd buy.
# outcome: did the crowd still reach 10 buys before the pull? when did the pull come relative to the 10th / the last crowd buy?
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json, collections, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__))
F = json.load(open(os.path.join(HERE, 'data/fam.json')))
DUST = '0xe71a69f4'
res = collections.defaultdict(list)
for r in F:
    cr = r['cr_rel']; pull = r['pull']; end = pull if pull is not None else 10**9
    mo = st.median([s['mo'] / s['tok'] for s in r['swaps'] if s['crowd'] and s['mo']] or [0])
    era = 'mo0.98' if mo > 0.9 else 'mo0.8'
    crowd_from = {s['frm'] for s in r['swaps'] if s['crowd']}
    first = cr[0]
    pos = collections.defaultdict(int); spent = collections.defaultdict(int); bought_at = {}
    for s in r['swaps']:
        if s['rel'] >= first: break
        if s['crowd'] or s['in_launch'] or (s['frm'] or '').startswith(DUST) or s['frm'] in crowd_from: continue
        w = s['frm']
        if s['buy']: pos[w] += s['tok']; spent[w] += s['eth']; bought_at.setdefault(w, s['rel'])
        else:
            pos[w] -= s['tok']
            if pos[w] <= 0: pos[w] = 0; spent[w] = 0
    holders = [(w, spent[w] / 1e18, bought_at[w]) for w in pos if pos[w] > 0]
    big = max([h[1] for h in holders] or [0])
    cls = 'none' if big < 0.0002 else ('tiny<0.002' if big < 0.002 else ('real>=0.002' if big < 0.02 else 'big>=0.02'))
    n_pre = sum(1 for x in cr if x < end)
    reached10 = n_pre >= 10
    margin = (pull - cr[9]) if (pull is not None and n_pre >= 10) else None
    res[(era, cls)].append(dict(pid=r['pid'][:10], reached10=reached10, n_pre=n_pre, pull=pull, first=first, margin=margin, holders=[(w[:8], round(e, 5), a) for w, e, a in holders if e >= 0.0002]))
for k in sorted(res):
    G = res[k]
    r10 = sum(g['reached10'] for g in G)
    pb = sum(1 for g in G if g['pull'] is not None and not g['reached10'])
    m = [g['margin'] for g in G if g['margin'] is not None]
    print(k, 'n', len(G), 'reached 10:', r10, f'({r10/len(G):.0%})', 'pulled before 10th:', pb, f'({pb/len(G):.0%})', 'pull-10th p0/10/50', sorted(m)[:3], st.median(m) if m else None)
    if k[1] not in ('none', 'tiny<0.002'):
        for g in G: print('    ', g)
json.dump({f'{a}|{b}': v for (a, b), v in res.items()}, open(os.path.join(HERE, 'data/c2.json'), 'w'))
