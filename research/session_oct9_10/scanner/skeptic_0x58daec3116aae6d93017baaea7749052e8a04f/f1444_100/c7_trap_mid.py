# the follow variant's exposure: an outside wallet buys >= 0.002 ETH AFTER the first crowd buy and before the crowd's 10th, holds >= 30 blocks.
# Does the crowd still complete, or is the pool pulled first? (our "follow entry" is exactly such a buy)
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json, collections
HERE = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(HERE, 'data/rows.json')))
DUST = '0xe71a69f4'
rows = []
for r in sorted(R, key=lambda r: r['lb']):
    cr = [s for s in r['swaps'] if s['crowd']]; crowd_from = {s['frm'] for s in cr}
    if not cr: continue
    pulls = [m for m in r['mods'] if m['dl'] < 0]; pull = pulls[0]['rel'] if pulls else None
    first = cr[0]['rel']; tenth = cr[9]['rel'] if len(cr) >= 10 else None
    end = min(x for x in (tenth, pull, 10**9) if x is not None)
    ev = None
    for i, s in enumerate(r['swaps']):
        if s['rel'] <= first or s['rel'] >= end: continue
        if not s['buy'] or s['crowd'] or s['frm'] in crowd_from or (s['frm'] or '').startswith(DUST) or s['eth'] < 2e15: continue
        sold = [x for x in r['swaps'][i+1:] if x['frm'] == s['frm'] and not x['buy'] and x['rel'] <= s['rel'] + 30]
        if sold: continue
        ev = s; break
    if ev is None: continue
    k_before = sum(1 for s in cr if s['rel'] < ev['rel'])
    n_pre = sum(1 for s in cr if pull is None or s['rel'] < pull)
    crowd_after = sum(1 for s in cr if s['rel'] > ev['rel'] and (pull is None or s['rel'] < pull))
    rows.append(dict(pid=r['pid'][:10], lb=r['lb'], who=ev['frm'][:10], at=ev['rel'], eth=round(ev['eth'] / 1e18, 5), crowd_before=k_before, crowd_after=crowd_after,
                     reached10=n_pre >= 10, pull=pull, pull_after=(pull - ev['rel']) if pull is not None else None))
for x in rows: print(x)
print('\nn', len(rows), 'crowd reached 10 before pull:', sum(x['reached10'] for x in rows), ' pulled before the 10th:', sum(1 for x in rows if not x['reached10'] and x['pull'] is not None),
      ' pull within 100 blocks of the buy:', sum(1 for x in rows if x['pull_after'] is not None and x['pull_after'] <= 100))
json.dump(rows, open(os.path.join(HERE, 'data/c7_trap_mid.json'), 'w'), indent=1)
