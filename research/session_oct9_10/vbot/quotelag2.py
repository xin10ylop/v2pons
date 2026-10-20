"""Which pool state does the bot's minOut come from? For each router buy, minOut/(0.95 x quote) at the state after each earlier swap (and the
initial state); report the latest state that matches within 3e-4, and how many blocks before the buy the NEXT swap after that state landed
(the quote is at least that stale: it did not see that swap)."""
import sys, pickle, collections, statistics as st
sys.path.insert(0, '..'); sys.path.insert(0, '/home/user/v2pons/src')
from chain import T_SWAP, T_ML, T_INIT, W, sgn
import v4math
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
D = pickle.load(open(sys.argv[1] if len(sys.argv) > 1 else 'cache84.pkl', 'rb'))
res = []; nomatch = 0
for pid, P in D.items():
    b0 = P['meta']['b0']
    init = [l for l in P['rec']['logs'] if l['topics'] and l['topics'][0] == T_INIT and l['topics'][1] == pid][0]
    sp0 = W(init['data'], 3)
    sws = sorted([l for l in P['logs'] if l['topics'][0] == T_SWAP], key=lambda l: (int(l['blockNumber'], 16), int(l['logIndex'], 16)))
    L0 = W(sws[0]['data'], 3) if sws else None
    txin = {}
    for b in P['blocks']:
        for t in b['transactions']: txin[t['hash']] = t
    for i, l in enumerate(sws):
        t = txin.get(l['transactionHash'])
        if not t or t['input'][:10] != '0xc1120e3d': continue
        bn = int(l['blockNumber'], 16); mo = int(t['input'][10 + 64*4: 10 + 64*5], 16); X = int(t['value'], 16)
        states = [(b0, sp0, L0, None)] + [(int(x['blockNumber'], 16), W(x['data'], 2), W(x['data'], 3), x) for x in sws[:i]]
        match = None
        for k in range(len(states) - 1, -1, -1):
            _, sp, L, _ = states[k]
            r = mo / (0.95 * v4math.buy_out_int(sp, L, X, 10000))
            if abs(r - 1) < 3e-4: match = k; break
        if match is None: nomatch += 1; continue
        nxt = states[match + 1][0] if match + 1 < len(states) else None   # the first swap the quote did not see
        n_unseen = len(states) - 1 - match
        res.append({'buy_off': bn - b0, 'n_unseen': n_unseen, 'unseen_first_blocks_before': (bn - nxt) if nxt is not None else None,
                    'seen_last_blocks_before': bn - states[match][0]})
print('matched', len(res), 'no match', nomatch)
print('n_unseen swaps:', collections.Counter(r['n_unseen'] for r in res).most_common())
u = [r['unseen_first_blocks_before'] for r in res if r['unseen_first_blocks_before'] is not None]
print('quote missed a swap that landed this many blocks before the buy (quote at least this stale):', sorted(u))
s = [r['seen_last_blocks_before'] for r in res if r['n_unseen'] == 0]
print('when nothing unseen: last seen swap blocks before the buy:', collections.Counter(s).most_common(15))
