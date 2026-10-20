"""P(the bot's quote saw a swap that landed L blocks before its buy), from every (bot buy, earlier swap within 25 blocks) pair: the quote
state is the latest state whose 0.95 x quote matches minOut (0.995..1.0005); a swap is 'seen' if it is at or before that state."""
import sys, pickle, collections
sys.path.insert(0, '..'); sys.path.insert(0, '/home/user/v2pons/src')
from chain import T_SWAP, T_INIT, W, sgn
import v4math
D = {}
for f in sys.argv[1:]: D.update(pickle.load(open(f, 'rb')))
seen = collections.Counter(); tot = collections.Counter(); nomatch = 0
for pid, P in D.items():
    b0 = P['meta']['b0']
    inits = [l for l in P['rec']['logs'] if l['topics'] and l['topics'][0] == T_INIT and l['topics'][1] == pid]
    if not inits: continue
    sp0 = W(inits[0]['data'], 3)
    sws = sorted([l for l in P['logs'] if l['topics'][0] == T_SWAP], key=lambda l: (int(l['blockNumber'], 16), int(l['logIndex'], 16)))
    if not sws: continue
    txin = {t['hash']: t for b in P['blocks'] for t in b['transactions']}
    states = [(b0, sp0, W(sws[0]['data'], 3))]
    for i, l in enumerate(sws):
        bn = int(l['blockNumber'], 16); t = txin.get(l['transactionHash'])
        if t and t['input'][:10] == '0xc1120e3d' and len(states) > 1:
            mo = int(t['input'][10 + 64*4: 10 + 64*5], 16); X = int(t['value'], 16)
            r = [mo / (0.95 * v4math.buy_out_int(sp, L, X, 10000)) for _, sp, L in states]
            ks = [k for k in range(len(r)) if 0.995 <= r[k] <= 1.0005]
            if not ks: nomatch += 1
            else:
                k = ks[-1]
                for j in range(1, len(states)):          # states[j] is the state after swap j-1, which landed at block states[j][0]
                    lag = bn - states[j][0]
                    if lag > 25: continue
                    tot[lag] += 1
                    if j <= k: seen[lag] += 1
        states.append((bn, W(l['data'], 2), W(l['data'], 3)))
print('no match', nomatch)
cum_s = cum_t = 0
for L in range(0, 26):
    if tot[L]: print(f"lag {L:2d}: swaps {tot[L]:3d} seen {seen[L]:3d}  P(seen) {seen[L] / tot[L]:.2f}")
