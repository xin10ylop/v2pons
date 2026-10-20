# recompute the claim's own numbers on its 17 (+5 fee-500) census pools, on the 7 launches after the census, and on the whole month
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json, collections, statistics as st
from c3_price import Pool, rule_k, summ
HERE = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(HERE, 'data/rows.json')))
for r in R:
    r['cr_rel'] = [s['rel'] for s in r['swaps'] if s['crowd']]
    pulls = [m for m in r['mods'] if m['dl'] < 0]; r['pull'] = pulls[0]['rel'] if pulls else None
fams = json.load(open('/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census/families.json'))
K1 = fams['0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|100|1|true']['pids']; K2 = fams['0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|500|10|true']['pids']
def q(v, qs=(0, .1, .5, .9, 1)):
    v = sorted(v); return [v[int(round(a * (len(v) - 1)))] for a in qs] if v else None
def stats(G, name):
    P = [Pool(r) for r in G]
    cr = [r for r in G if r['cr_rel']]
    first = [r['cr_rel'][0] for r in cr]; tenth = [r['cr_rel'][9] for r in cr if len(r['cr_rel']) >= 10]
    pre = [sum(1 for x in r['cr_rel'] if r['pull'] is None or x < r['pull']) for r in G]
    m10 = [r['pull'] - r['cr_rel'][9] for r in G if r['pull'] is not None and len(r['cr_rel']) >= 10 and r['cr_rel'][9] < r['pull']]
    tot = [round(sum(s['eth'] for s in r['swaps'] if s['crowd']) / 1e18, 4) for r in cr]
    d = dict(n=len(G), with_crowd=len(cr), crowd_count=sorted(collections.Counter(len(r['cr_rel']) for r in G).items()), crowd_before_pull=sorted(collections.Counter(pre).items()),
             first_crowd_min_p10_p50_p90_max=q(first), tenth_crowd=q(tenth), pulled=sum(r['pull'] is not None for r in G), pull_minus_10th=q(m10),
             crowd_total_eth=q(tot), claim_rule=summ([rule_k(p, 10) for p in P]), k1=summ([rule_k(p, 1) for p in P]))
    print(name, json.dumps(d)); return d
out = {}
out['claim17'] = stats([r for r in R if r['pid'] in K1], 'claim 17 (fee 100, census)')
out['claim22'] = stats([r for r in R if r['pid'] in K1 + K2], 'claim 22 (+fee 500)')
out['post_census'] = stats([r for r in R if r['lb'] > 85203897], 'after the census (Oct 10 18:20-22:06)')
out['month'] = stats(R, 'all 339 (Sep 11 - Oct 10)')
json.dump(out, open(os.path.join(HERE, 'data/c9.json'), 'w'), indent=1)
