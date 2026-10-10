import sys, pickle
sys.path.insert(0, '..'); sys.path.insert(0, '/home/user/v2pons/src')
from chain import T_SWAP, T_ML, T_INIT, W, sgn
import v4math
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
D = pickle.load(open('cache84.pkl', 'rb'))
for pid in list(D)[int(sys.argv[1]):int(sys.argv[1]) + 2]:
    P = D[pid]; b0 = P['meta']['b0']
    init = [l for l in P['rec']['logs'] if l['topics'] and l['topics'][0] == T_INIT and l['topics'][1] == pid][0]
    sp0 = W(init['data'], 3)
    sws = sorted([l for l in P['logs'] if l['topics'][0] == T_SWAP], key=lambda l: (int(l['blockNumber'], 16), int(l['logIndex'], 16)))
    txin = {}
    for b in P['blocks']:
        for t in b['transactions']: txin[t['hash']] = t
    print('pool', pid[:10], b0)
    states = [(0, sp0, W(sws[0]['data'], 3))]
    for i, l in enumerate(sws[:12]):
        bn = int(l['blockNumber'], 16); a0 = s128(W(l['data'], 0)); a1 = s128(W(l['data'], 1)); t = txin.get(l['transactionHash'])
        line = f"  +{bn-b0:3d} {'BUY ' if a0 < 0 else 'SELL'} eth {abs(a0)/1e18:.5f} tok {abs(a1):.4e} via {t['to'][:8] if t else '?'} {t['input'][:10] if t else ''} from {t['from'][:10] if t else ''}"
        if t and t['input'][:10] == '0xc1120e3d':
            mo = int(t['input'][10 + 64*4: 10 + 64*5], 16); X = int(t['value'], 16)
            line += ' | minOut/(.95 q) at states: ' + ' '.join(f"{mo / (0.95 * v4math.buy_out_int(sp, L, X, 10000)):.5f}" for _, sp, L in states)
            line += f' | tokens/minOut {abs(a1)/mo:.5f}'
        print(line)
        states.append((bn - b0, W(l['data'], 2), W(l['data'], 3)))
