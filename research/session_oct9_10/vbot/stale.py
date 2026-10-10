"""How stale is the volume bot's quote (its buy's minOut)? For each router buy after the pool's first: r_k = minOut / (0.95 x exact quote at
the state after earlier swap k). The quote 'saw' swap k if r_k is in the band of the matched values. Report, per buy, the lag (blocks before
the buy) of the latest swap it saw and of the earliest swap it did not see."""
import sys, pickle, collections, statistics as st
sys.path.insert(0, '..'); sys.path.insert(0, '/home/user/v2pons/src')
from chain import T_SWAP, T_ML, T_INIT, W, sgn
import v4math
D = pickle.load(open(sys.argv[1] if len(sys.argv) > 1 else 'cache84.pkl', 'rb'))
best = []; seen_lag = collections.Counter(); unseen_lag = collections.Counter(); amb = 0
for pid, P in D.items():
    b0 = P['meta']['b0']
    inits = [l for l in P['rec']['logs'] if l['topics'] and l['topics'][0] == T_INIT and l['topics'][1] == pid]
    if not inits: continue
    sp0 = W(inits[0]['data'], 3)
    sws = sorted([l for l in P['logs'] if l['topics'][0] == T_SWAP], key=lambda l: (int(l['blockNumber'], 16), int(l['logIndex'], 16)))
    if not sws: continue
    txin = {}
    for b in P['blocks']:
        for t in b['transactions']: txin[t['hash']] = t
    states = [(b0, sp0, W(sws[0]['data'], 3))]
    for i, l in enumerate(sws):
        bn = int(l['blockNumber'], 16); t = txin.get(l['transactionHash'])
        if t and t['input'][:10] == '0xc1120e3d' and len(states) > 1:
            mo = int(t['input'][10 + 64*4: 10 + 64*5], 16); X = int(t['value'], 16)
            r = [mo / (0.95 * v4math.buy_out_int(sp, L, X, 10000)) for _, sp, L in states]
            # the state the quote came from: the latest k whose r is within [0.995, 1.0005]
            ks = [k for k in range(len(r)) if 0.995 <= r[k] <= 1.0005]
            if not ks: amb += 1
            else:
                k = ks[-1]; best.append(r[k])
                if k >= 1: seen_lag[bn - states[k][0]] += 1          # the latest swap it saw (states[k] is after swap k-1)
                if k + 1 < len(states): unseen_lag[bn - states[k + 1][0]] += 1
        states.append((bn, W(l['data'], 2), W(l['data'], 3)))
print('buys', len(best), 'no state matched', amb)
print('matched r: min %.5f median %.5f max %.5f' % (min(best), st.median(best), max(best)))
print('latest swap the quote SAW, blocks before the buy:', sorted(seen_lag.items())[:25])
print('earliest swap the quote did NOT see, blocks before the buy:', sorted(unseen_lag.items()))
