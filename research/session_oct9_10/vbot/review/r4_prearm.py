"""Reviewer check: outsider buys BEFORE the bot's first buy (the 0.9 FRONT entry slot), per family: was the pool pulled, when, relative
to the outsider buy and to the bot's first buy. Uses the reaction study's loader/classifier (react/common.py)."""
import sys, os, collections, statistics as st
sys.path.insert(0, '/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/vbot/react')
from common import load, classifier, COV
P, TX, M = load(); BOTW, cls = classifier(TX)
out = collections.defaultdict(list)
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
    out[v['fam']].append({'b0': v['b0'], 'src': v['src'], 'rel': s['rel'], 'eth': s['eth'], 'w': t['from'][:10], 'bot1': bb[0] if bb else None, 'pull': v['pull']})
for fam, xs in out.items():
    n = len(xs)
    p_after_bot1 = [x['pull'] - x['bot1'] for x in xs if x['bot1'] is not None and x['pull'] is not None]
    pulled_before_bot1 = sum(1 for x in xs if x['pull'] is not None and (x['bot1'] is None or x['pull'] <= x['bot1']))
    w60 = sum(1 for x in xs if x['pull'] is not None and x['pull'] <= 60)
    print(f'{fam}: pools with a pre-arm outsider buy >=3e-5: {n} (census {sum(1 for x in xs if x["src"]=="census")}); pulled by +60: {w60}; pulled at/before bot buy 1: {pulled_before_bot1}')
    print('   pull - bot1 (blocks):', sorted(collections.Counter(min(d, 999) for d in p_after_bot1).items())[:25])
    print('   wallets:', collections.Counter(x['w'] for x in xs).most_common(6), 'sizes median', st.median(x['eth'] for x in xs), 'max', max(x['eth'] for x in xs))
    big = [x for x in xs if x['eth'] >= 1e-4]
    print('   >=1e-4:', len(big), 'pulled by +60', sum(1 for x in big if x['pull'] is not None and x['pull'] <= 60), [(x['rel'], round(x['eth'], 5), x['w'], x['bot1'], x['pull']) for x in big[:12]])
