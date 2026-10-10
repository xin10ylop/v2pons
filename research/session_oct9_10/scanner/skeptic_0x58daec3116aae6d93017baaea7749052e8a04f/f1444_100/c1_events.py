# event study: does an outsider HOLDING real size during the pre-crowd / crowd phase cut the crowd short and bring the pull?
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json, collections, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__))
F = json.load(open(os.path.join(HERE, 'data/fam.json')))
Q96 = 2**96
DUST = '0xe71a69f4'
def price(sp): return (sp / Q96) ** 2   # tokens per ETH
out = []
for r in F:
    crowd_from = {s['frm'] for s in r['swaps'] if s['crowd']}
    cr = r['cr_rel']; pull = r['pull']
    end = pull if pull is not None else 10**9
    # outsider holdings through time (token units), only swaps before the pull
    pos = collections.defaultdict(int); first_hold = {}
    maxhold = 0.0; maxhold_at = None; holders = []
    big_events = []
    for s in r['swaps']:
        if s['rel'] >= end: break
        if s['crowd'] or s['in_launch'] or (s['frm'] or '').startswith(DUST) or s['frm'] in crowd_from: continue
        w = s['frm'] or s['tx']
        pos[w] += s['tok'] if s['buy'] else -s['tok']
        if pos[w] < 0: pos[w] = 0
        val = sum(v for v in pos.values()) / price(s['sp'])
        if val > maxhold: maxhold, maxhold_at = val, s['rel']
        if s['buy'] and s['eth'] >= 2e15: big_events.append((s['rel'], s['eth'] / 1e18, w[:8]))
    # holdings value at each crowd buy (approx: tokens / price after that crowd buy)
    n_before_pull = sum(1 for x in cr if x < end)
    out.append(dict(pid=r['pid'][:10], lb=r['lb'], era='late' if r['lb'] >= 82_000_000 else 'early', mo=st.median([s['mo'] / s['tok'] for s in r['swaps'] if s['crowd'] and s['mo']] or [0]),
                    ncrowd=r['ncrowd'], n_pre=n_before_pull, pull=pull, first=cr[0], last_pre=max([x for x in cr if x < end] or [None]) if cr else None,
                    maxhold=maxhold / 1e18, maxhold_at=maxhold_at, big=big_events))
json.dump(out, open(os.path.join(HERE, 'data/c1.json'), 'w'))
# era split by minOut ratio (0.98 = old, 0.8 = new)
for era_name, sel in (('mo0.98 era', lambda o: o['mo'] > 0.9), ('mo0.8 era', lambda o: o['mo'] <= 0.9)):
    E = [o for o in out if sel(o)]
    print(era_name, len(E), 'ncrowd', sorted(collections.Counter(o['ncrowd'] for o in E).items()))
    for lo, hi in ((0, 0.0005), (0.0005, 0.002), (0.002, 0.01), (0.01, 99)):
        G = [o for o in E if lo <= o['maxhold'] < hi]
        if not G: continue
        full = sum(1 for o in G if o['n_pre'] >= 10)
        pulled_short = sum(1 for o in G if o['pull'] is not None and o['n_pre'] < 10)
        print(f"   outsider max holding [{lo},{hi}) ETH: n {len(G)}  crowd reached 10 before pull {full} ({full/len(G):.0%})  pulled before 10th {pulled_short} ({pulled_short/len(G):.0%})")
