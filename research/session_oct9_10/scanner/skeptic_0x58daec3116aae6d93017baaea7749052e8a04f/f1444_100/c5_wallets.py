# who are the recurring non-crowd wallets in the family's pools, and where else (census, all families) do they trade?
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import load_txs, load_pools
HERE = os.path.dirname(os.path.abspath(__file__))
F = json.load(open(os.path.join(HERE, 'data/fam.json')))
famp = {r['pid'] for r in F}
w = collections.Counter(); info = {}
for r in F:
    crowd_from = {s['frm'] for s in r['swaps'] if s['crowd']}
    seen = set()
    for s in r['swaps']:
        if s['crowd'] or s['frm'] in crowd_from or s['in_launch'] or not s['frm']: continue
        if s['frm'] not in seen: w[s['frm']] += 1; seen.add(s['frm'])
        info.setdefault(s['frm'], collections.Counter())[(s['to'], s['sel'], s['clen'])] += 1
T = load_txs(); P = load_pools()
cen = collections.defaultdict(lambda: collections.Counter())
for h, t in T.items():
    if 'swap' not in t.get('kind', []): continue
    for pid, kind, rank in t['refs']:
        if kind == 'swap': cen[t['from']][P[pid]['family'] if pid not in famp else 'OPERATOR_C'] += 1
for a, n in w.most_common(25):
    c = cen.get(a, {})
    other = sum(v for k, v in c.items() if k != 'OPERATOR_C')
    print(a, 'opC pools', n, 'route', info[a].most_common(2), '| census swaps: opC', c.get('OPERATOR_C', 0), 'other families', other, 'top', [(k[:60], v) for k, v in collections.Counter({k: v for k, v in c.items() if k != 'OPERATOR_C'}).most_common(3)])
