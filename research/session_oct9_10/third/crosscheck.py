"""offline pass over the whole shared bc cache: any tx between third-system set S and loops A/B set P (+ injectors); txs touching relayer/executor by P"""
from lib3 import *
import lib2, bc, os, re
S = set(json.load(open('third_set.json')))
P = set(json.load(open('pots_addrs.json'))) | {'0xf31d79a3bcbc5402dafb6e5684b685ebec960d5b', '0xcfcf219e97dc6111f8de776fc4761a06098cdc74', '0x51a1407797395a4115b745642751a85af5938cfe'}
cs = sorted(int(f[1:-5]) for f in os.listdir(bc.D) if f.startswith('q') and f.endswith('.json'))
big = sorted(int(f[:-5]) for f in os.listdir(bc.D) if re.match(r'^\d+\.json$', f))
chunks = sorted(set(cs) | {b * 4 + k for b in big for k in range(4)})
hits = []; n = 0
for c in chunks:
    try: d = bc.chunk(c)
    except Exception: continue
    for bn, (ts, tl) in d.items():
        for t in tl:
            n += 1
            f, to = t[1], t[2]
            if (f in S and to in P) or (f in P and to in S): hits.append([bn, ts] + t)
    bc._mem.clear()
json.dump(hits, open('crosscheck.json', 'w'))
print('txs scanned', n, 'chunks', len(chunks), 'hits', len(hits))
for h in hits[:20]: print(h)
