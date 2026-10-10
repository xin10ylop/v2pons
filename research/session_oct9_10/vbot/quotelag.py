"""When does the volume bot quote its buy? For each router buy (0x1cbaf24d c1120e3d), word 4 = minOut; tokens/minOut ~ 1/0.95. Find the
pool state (after block bn-j, j=0..6; j=0 = just before the buy in its own block) whose 0.95 x quote reproduces minOut."""
import sys, pickle, collections, statistics as st
sys.path.insert(0, '..'); sys.path.insert(0, '/home/user/v2pons/src')
from chain import T_SWAP, T_ML, W, sgn
import v4math
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
D = pickle.load(open('cache84.pkl', 'rb'))
lagc = collections.Counter(); ratios = collections.defaultdict(list)
for pid, P in D.items():
    b0 = P['meta']['b0']; tok = P['meta']['token'][2:].lower()
    sws = sorted([l for l in P['logs'] if l['topics'][0] == T_SWAP], key=lambda l: (int(l['blockNumber'], 16), int(l['logIndex'], 16)))
    txin = {}
    for b in P['blocks']:
        for t in b['transactions']: txin[t['hash']] = t
    rec = P['rec']; init = [l for l in rec['logs'] if l['topics'][0] == '0x' + __import__('chain').T_INIT[2:]] if False else None
    for i, l in enumerate(sws):
        t = txin.get(l['transactionHash'])
        if not t or t['input'][:10] != '0xc1120e3d': continue
        bn = int(l['blockNumber'], 16); mo = int(t['input'][10 + 64*4: 10 + 64*5], 16); X = int(t['value'], 16)
        prev = sws[:i]
        cands = {}
        for j in range(0, 7):
            pv = [x for x in prev if int(x['blockNumber'], 16) < bn - j] if j > 0 else prev
            if not pv: continue
            sp = W(pv[-1]['data'], 2); L = W(pv[-1]['data'], 3)
            q = v4math.buy_out_int(sp, L, X, 10000)
            cands[j] = mo / q
        best = min(cands, key=lambda j: abs(cands[j] - 0.95)) if cands else None
        exact = [j for j in cands if abs(cands[j] - 0.95) < 1e-6]
        lagc[(tuple(exact[:3]) if exact else ('none', best))] += 1
        for j, r in cands.items(): ratios[j].append(r)
print(lagc.most_common(20))
for j in sorted(ratios): print(j, len(ratios[j]), 'median minOut/quote', round(st.median(ratios[j]), 6), 'frac within 1e-6 of .95', sum(1 for r in ratios[j] if abs(r - .95) < 1e-6) / len(ratios[j]))
print('---- buys whose pool changed in the 8 blocks before them')
n = 0
for pid, P in D.items():
    b0 = P['meta']['b0']
    sws = sorted([l for l in P['logs'] if l['topics'][0] == T_SWAP], key=lambda l: (int(l['blockNumber'], 16), int(l['logIndex'], 16)))
    txin = {}
    for b in P['blocks']:
        for t in b['transactions']: txin[t['hash']] = (t, int(b['number'], 16))
    for i, l in enumerate(sws):
        tt = txin.get(l['transactionHash'])
        if not tt or tt[0]['input'][:10] != '0xc1120e3d': continue
        t = tt[0]; bn = int(l['blockNumber'], 16); mo = int(t['input'][10 + 64*4: 10 + 64*5], 16); X = int(t['value'], 16)
        prev = sws[:i]
        if not prev or int(prev[-1]['blockNumber'], 16) < bn - 8: continue
        row = []
        for j in range(0, 9):
            pv = [x for x in prev if int(x['blockNumber'], 16) < bn - j] if j > 0 else prev
            if not pv: row.append(None); continue
            sp = W(pv[-1]['data'], 2); L = W(pv[-1]['data'], 3)
            row.append(round(mo / v4math.buy_out_int(sp, L, X, 10000), 5))
        last = int(prev[-1]['blockNumber'], 16)
        a0 = s128(W(prev[-1]['data'], 0))
        print(pid[:10], 'buy +%d' % (bn - b0), 'prev swap at -%d (%s %.4f)' % (bn - last, 'buy' if a0 < 0 else 'sell', abs(a0) / 1e18), 'X %.3f' % (X / 1e18), row, 'deadline-ts', int(t['input'][10+64*6:10+64*7],16))
        n += 1
        if n > 40: break
    if n > 40: break
