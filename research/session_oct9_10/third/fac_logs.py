"""factory 0x7ed598bc create events (8d4aad49). Keep compact [bn, tx, token, curve, creator, d0, d1, d2] for the last NKEEP blocks; for older windows
only counts. Windows of 250k blocks backwards until 3 empty windows."""
from lib3 import *
T = '0x8d4aad4953d0ca700d468f3753aa14432d1b35b43ec6409f051fb6aa43a89607'
F = '0x7ed598bcef8bd9edd8c97a195c6d13f40801ec7e'
head = int(rpc('eth_blockNumber', []), 16)
NKEEP = 2000000; WIN = 250000
keep = []; counts = []; empty = 0; hi = head
def comp(l):
    d = l['data'][2:]
    return [int(l['blockNumber'], 16), l['transactionHash'], '0x' + l['topics'][1][26:], '0x' + l['topics'][2][26:], '0x' + l['topics'][3][26:]] + \
           [int(d[i:i+64], 16) for i in range(0, len(d), 64)]
while empty < 3 and hi > 0:
    lo = max(0, hi - WIN + 1)
    r = logs({'address': F, 'topics': [T]}, lo, hi)
    c = [comp(l) for l in r]; del r
    counts.append([lo, hi, len(c), min([x[0] for x in c], default=None)])
    if head - lo <= NKEEP: keep += c
    print(lo, hi, len(c), flush=True)
    empty = empty + 1 if not c else 0
    hi = lo - 1
    time.sleep(0.3)
keep.sort()
json.dump({'head': head, 'keep': keep, 'counts': counts}, open('fac_events.json', 'w'))
print('kept', len(keep), 'total', sum(x[2] for x in counts))
