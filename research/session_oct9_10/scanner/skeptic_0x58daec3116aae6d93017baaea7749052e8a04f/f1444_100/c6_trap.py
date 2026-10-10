# TRAP TEST over every candidate launch (crowd or not): an outside wallet buys >= 0.002 ETH BEFORE the crowd starts (or before +600 when no crowd)
# and still holds 60 blocks later. What happens next: abort (pull before any crowd buy), crowd cut (< 10), or crowd completes?
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json, collections, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(HERE, 'data/rows.json')))
DUST = '0xe71a69f4'
rows = []
for r in sorted(R, key=lambda r: r['lb']):
    cr = [s for s in r['swaps'] if s['crowd']]; crowd_from = {s['frm'] for s in cr}
    pulls = [m for m in r['mods'] if m['dl'] < 0]; pull = pulls[0]['rel'] if pulls else None
    first = cr[0]['rel'] if cr else None
    horizon = first if first is not None else (pull if pull is not None else 600)
    horizon = min(horizon, 600) if first is None else horizon
    ev = None
    for i, s in enumerate(r['swaps']):
        if s['rel'] >= horizon: break
        if not s['buy'] or s['crowd'] or s['in_launch'] or s['frm'] in crowd_from or (s['frm'] or '').startswith(DUST): continue
        if s['eth'] < 2e15: continue
        sold = [x for x in r['swaps'][i+1:] if x['frm'] == s['frm'] and not x['buy'] and x['rel'] <= s['rel'] + 60]
        if sold: continue
        ev = s; break
    if ev is None: continue
    n_pre = sum(1 for s in cr if pull is None or s['rel'] < pull)
    outcome = 'abort (pulled, no crowd buy before pull)' if (pull is not None and (first is None or pull < first)) else ('crowd cut <10, then pulled' if (pull is not None and n_pre < 10) else ('crowd completed 10' if n_pre >= 10 else 'no pull in window, crowd <10'))
    rows.append(dict(lb=r['lb'], pid=r['pid'][:10], who=ev['frm'][:10], at=ev['rel'], eth=round(ev['eth'] / 1e18, 5), first_crowd=first, n_pre=n_pre, pull=pull,
                     pull_after_buy=(pull - ev['rel']) if pull is not None else None, outcome=outcome))
for x in rows: print(x)
c = collections.Counter(x['outcome'] for x in rows)
print('\nTOTAL', len(rows), dict(c))
d = [x['pull_after_buy'] for x in rows if x['outcome'].startswith('abort')]
print('abort: pull after the early buy, blocks:', sorted(d))
json.dump(rows, open(os.path.join(HERE, 'data/c6_trap.json'), 'w'), indent=1)
