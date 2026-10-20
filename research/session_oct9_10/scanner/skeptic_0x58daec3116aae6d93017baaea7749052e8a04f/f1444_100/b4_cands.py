import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
import glob, collections, datetime
K = []
for f in sorted(glob.glob(os.path.join(HERE, 'data/inits/*.json'))): K += json.load(open(f))['keep']
T = json.load(open(os.path.join(HERE, 'data/ltx.json')))
C = []
for k in K:
    t = T.get(k['tx'])
    if not t: continue
    if t['to'] == '0x58daec3116aae6d93017baaea7749052e8a04fa7' and t['sel'] == 'ac9650d8' and t['clen'] == 1444 and t['value'] >= 4 * 10**17:
        C.append(dict(k, **{x: t[x] for x in ('frm', 'value', 'nonce', 'ti')}))
C.sort(key=lambda c: c['bn'])
# block -> approx time: use 0.1028 s/block anchored at head
H = 85336458; HT = 1791669999
def ts(bn): return HT - (H - bn) * 0.10281
print(len(C))
day = collections.defaultdict(list)
for c in C:
    d = datetime.datetime.utcfromtimestamp(ts(c['bn'])).strftime('%m-%d')
    day[d].append(c)
for d in sorted(day):
    cs = day[d]
    print(d, len(cs), collections.Counter((c['fee'], round(c['value']/1e18, 2)) for c in cs).most_common(), 'nonce', collections.Counter(c['nonce'] for c in cs).most_common(4), 'ticks', collections.Counter(c['tick'] for c in cs).most_common(5))
json.dump(C, open(os.path.join(HERE, 'data/cands.json'), 'w'))
# exact wei tails
print(collections.Counter((c['value'] % 10**15) for c in C).most_common(10))
