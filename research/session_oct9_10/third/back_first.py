"""backward scan from the first third-system launch (Sep 21 12:18:27, block 68790933) for funding of: relayer 37bd8ddc, creator 2bea0fb6, the 65 first holders.
Stops when >= 60% of targets have an incoming value tx, or after MAXB blocks. Gentle: blk3 chunks of 100."""
from lib3 import *
import blk3
from collections import defaultdict
T = set(json.load(open('first_holders.json'))) | {'0x2bea0fb6b71351fb9de24b7b831c0db6c42ae8a2', '0x37bd8ddc5d977ce42a8180366ebe48bdd6d13a75'}
START = 68791583; MAXB = int(sys.argv[1]) if len(sys.argv) > 1 else 6000
found = defaultdict(list); hits = []
c = START // 100
while c * 100 > START - MAXB:
    d = blk3.chunk(c)
    for bn in sorted(d, reverse=True):
        ts, tl = d[bn]
        for t in tl:
            if (t[2] in T and int(t[3]) > 0) or t[1] in T:
                hits.append([bn, utc(ts)] + t)
                if t[2] in T and int(t[3]) > 0: found[t[2]].append([bn, t[1], int(t[3]) / 1e18, t[5]])
    print(time.strftime('%H:%M:%S'), 'chunk', c * 100, 'targets funded', len(found), '/', len(T), flush=True)
    json.dump({'hits': hits, 'found': found}, open('back_first.json', 'w'))
    if len(found) >= 0.6 * len(T) and '0x37bd8ddc5d977ce42a8180366ebe48bdd6d13a75' in found: break
    c -= 1
print('done')
