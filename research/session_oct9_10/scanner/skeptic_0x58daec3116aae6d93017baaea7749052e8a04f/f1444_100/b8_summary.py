import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json, collections, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(HERE, 'data/rows.json')))
def q(v, qs=(0, .1, .5, .9, 1)):
    v = sorted(v); 
    return [v[int(round(a*(len(v)-1)))] for a in qs] if v else None
fam = []
for r in R:
    cr = [s for s in r['swaps'] if s['crowd']]
    r['ncrowd'] = len(cr)
    pull = [m for m in r['mods'] if m['dl'] < 0]
    r['pull'] = pull[0]['rel'] if pull else None
    r['pull_from_launcher'] = (pull[0]['frm'] == r['launcher']) if pull else None
    r['pull_full'] = (pull[0]['dl'] == -r['L0']) if pull else None
    r['cr_rel'] = [s['rel'] for s in cr]
    r['cr_eth'] = [s['eth'] for s in cr]
    if cr: fam.append(r)
print('pools with >=1 crowd buy', len(fam), 'of', len(R))
print('ncrowd hist', sorted(collections.Counter(r['ncrowd'] for r in R).items()))
# the crowd's mo ratio
rat = [s['mo'] / s['tok'] for r in fam for s in r['swaps'] if s['crowd'] and s['mo']]
print('minOut/fill', len(rat), q(rat))
# values, launch nonce
print('values', collections.Counter(round(r['value']/1e18, 2) for r in fam).most_common())
print('nonce', collections.Counter(r['nonce'] for r in fam).most_common())
print('fee', collections.Counter((r['fee'], r['ts']) for r in fam).most_common())
print('first crowd', q([r['cr_rel'][0] for r in fam]))
print('10th crowd', q([r['cr_rel'][9] for r in fam if r['ncrowd'] >= 10]))
print('pull', collections.Counter(r['pull'] is not None for r in fam), q([r['pull'] for r in fam if r['pull'] is not None]))
print('pull from launcher', collections.Counter(r['pull_from_launcher'] for r in fam), 'full', collections.Counter(r['pull_full'] for r in fam))
# pull relative to last crowd buy before it, and number of crowd buys before the pull
bef = collections.Counter(); m10 = []
for r in fam:
    if r['pull'] is None: continue
    nb = sum(1 for x in r['cr_rel'] if x < r['pull']); bef[nb] += 1
    if nb >= 10: m10.append(r['pull'] - r['cr_rel'][9])
print('crowd buys before pull', sorted(bef.items()))
print('pull - 10th crowd', q(m10), len(m10))
# window cut: pools whose window ends before the crowd could finish
print('ev window short', sum(1 for r in fam if r['ev_to'] - r['lb'] < 3000))
json.dump(fam, open(os.path.join(HERE, 'data/fam.json'), 'w'))
