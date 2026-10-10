import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
import glob
K = []
for f in sorted(glob.glob(os.path.join(HERE, 'data/inits/*.json'))): K += json.load(open(f))['keep']
p = os.path.join(HERE, 'data', 'ltx.json')
have = json.load(open(p)) if os.path.exists(p) else {}
need = sorted({k['tx'] for k in K} - set(have))
print('need', len(need))
for i in range(0, len(need), 200):
    ch = need[i:i+200]
    r = batch([("eth_getTransactionByHash", [h]) for h in ch])
    for h, t in zip(ch, r):
        if t is None: continue
        have[h] = dict(frm=t['from'], to=t['to'], value=int(t['value'], 16), nonce=int(t['nonce'], 16), bn=int(t['blockNumber'], 16), ti=int(t['transactionIndex'], 16),
                       sel=t['input'][2:10], clen=(len(t['input']) - 2) // 2, input=t['input'] if len(t['input']) < 4200 else t['input'][:1000])
    json.dump(have, open(p, 'w'))
    print(i, flush=True)
