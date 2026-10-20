import sys, pickle, collections, json
sys.path.insert(0, '..')
from chain import T_SWAP, T_ML, W, sgn
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
D = pickle.load(open('cache84.pkl', 'rb'))
kinds = collections.Counter(); valmatch = collections.Counter(); minout = []; sellmatch = collections.Counter(); unmatched_swaps = collections.Counter()
offs = collections.defaultdict(list)
for pid, P in D.items():
    b0 = P['meta']['b0']; tok = P['meta']['token'][2:].lower()
    sw = {}
    for l in P['logs']:
        if l['topics'][0] == T_SWAP:
            sw.setdefault(l['transactionHash'], []).append(l)
    seen = set()
    for b in P['blocks']:
        bn = int(b['number'], 16)
        for t in b['transactions']:
            inp = t['input'].lower()
            if tok not in inp: continue
            to = (t['to'] or '').lower(); sel = inp[:10]; v = int(t['value'], 16)
            k = (to[:10], sel, len(inp)//2-1, 'v>0' if v else 'v=0')
            kinds[k] += 1
            ls = sw.get(t['hash'])
            if ls:
                seen.add(t['hash'])
                a0 = s128(W(ls[0]['data'], 0)); a1 = s128(W(ls[0]['data'], 1))
                if a0 < 0:
                    valmatch[(to[:10], 'eq' if -a0 == v else ('lt' if -a0 < v else 'gt'))] += 1
                    if sel == '0xc1120e3d':
                        mo = int(inp[10+64*4:10+64*5], 16); minout.append(a1 / mo if mo else None)
                    offs['buy'].append(bn - b0)
                else:
                    if sel == '0x24856bc3':
                        # find amountIn: scan words for -a1
                        words = [int(inp[10+64*i:10+64*(i+1)], 16) for i in range((len(inp)-10)//64)]
                        sellmatch['amountIn in calldata' if -a1 in words else 'not found'] += 1
                    else:
                        sellmatch[(to[:10], sel)] += 1
                    offs['sell'].append(bn - b0)
    for h, ls in sw.items():
        bn = int(ls[0]['blockNumber'], 16)
        if bn <= b0 + 64 and h not in seen:
            unmatched_swaps[(bn - b0) // 10] += 1
print('tx kinds carrying the token:'); [print('  ', k, v) for k, v in kinds.most_common(30)]
print('buy value vs |a0|:', valmatch)
import statistics as st
mo = [x for x in minout if x]
print('router buys: tokens out / word4 :', len(mo), min(mo), st.median(mo), max(mo))
print('sells:', sellmatch)
print('swaps in [b0,b0+64] not found in decoded token-carrying txs, by decade:', unmatched_swaps)
print('first-buy offset hist', collections.Counter(offs['buy']).most_common(20))
