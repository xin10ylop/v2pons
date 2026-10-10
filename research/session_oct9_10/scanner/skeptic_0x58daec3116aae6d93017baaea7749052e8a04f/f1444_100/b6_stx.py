# every swap / liquidity tx of the candidate pools (from, to, nonce, value, selector, calldata)
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
EV = json.load(open(os.path.join(HERE, 'data/events.json')))
p = os.path.join(HERE, 'data', 'stx.json')
have = json.load(open(p)) if os.path.exists(p) else {}
need = sorted({s['tx'] for e in EV.values() for s in e['swaps'] + e['mods']} - set(have))
print('need', len(need), flush=True)
for i in range(0, len(need), 250):
    ch = need[i:i+250]
    r = batch([("eth_getTransactionByHash", [h]) for h in ch])
    for h, t in zip(ch, r):
        if t is None: continue
        have[h] = dict(frm=t['from'], to=t['to'], value=int(t['value'], 16), nonce=int(t['nonce'], 16), bn=int(t['blockNumber'], 16), ti=int(t['transactionIndex'], 16),
                       sel=t['input'][2:10], clen=(len(t['input']) - 2) // 2, gp=int(t.get('gasPrice', '0x0'), 16), prio=int(t.get('maxPriorityFeePerGas', '0x0'), 16),
                       input=t['input'] if len(t['input']) < 6000 else t['input'][:2000])
    json.dump(have, open(p, 'w'))
    print(i, flush=True)
