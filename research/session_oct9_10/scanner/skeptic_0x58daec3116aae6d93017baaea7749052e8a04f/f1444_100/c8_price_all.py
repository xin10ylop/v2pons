# claim rule priced on EVERY candidate launch (no-crowd pools included), and on the pools where an outsider of our size held before the crowd
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json, collections, statistics as st
from c3_price import Pool, rule_k, summ
HERE = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(HERE, 'data/rows.json')))
for r in R:
    r['cr_rel'] = [s['rel'] for s in r['swaps'] if s['crowd']]
    pulls = [m for m in r['mods'] if m['dl'] < 0]; r['pull'] = pulls[0]['rel'] if pulls else None
P = {r['pid'][:10]: Pool(r) for r in R}
def era(p):
    mo = [x['mo'] / x['tok'] for x in p.r['swaps'] if x['crowd'] and x['mo']]
    return None if not mo else ('mo0.8' if st.median(mo) <= 0.9 else 'mo0.98')
groups = {'all 339 launches': list(P.values()), 'Sep 28 on (blocks >= 75.9M)': [p for p in P.values() if p.lb >= 75_900_000],
          'Oct 5 on': [p for p in P.values() if p.lb >= 80_900_000]}
for lo, hi in (('0.0001', '0.0005'), ('0.0005', '0.002'), ('0.002', '0.01'), ('0.01', '10')):
    ev = json.load(open(os.path.join(HERE, f'data/c6_trap_{lo}_{hi}.json')))
    groups[f'early outsider holder {lo}-{hi} ETH'] = [P[e['pid']] for e in ev]
groups['early outsider holder >= 0.002 (our size class)'] = groups['early outsider holder 0.002-0.01 ETH'] + groups['early outsider holder 0.01-10 ETH']
out = {}
for name, G in groups.items():
    a = summ([rule_k(p, 10) for p in G]); b = summ([rule_k(p, 1) for p in G]); c = summ([rule_k(p, 10, gap=300) for p in G])
    out[name] = {'claim_rule': a, 'k1': b, 'k10_gap300': c}
    print(f'{name:50s} n {len(G):3d}\n   claim rule (sell after 10th, abort +640, dl +2400): {a}\n   sell after 1st crowd buy: {b}\n   claim rule + gap 300: {c}')
json.dump(out, open(os.path.join(HERE, 'data/c8.json'), 'w'), indent=1)
