import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json, collections, statistics as st, datetime
HERE = os.path.dirname(os.path.abspath(__file__))
F = json.load(open(os.path.join(HERE, 'data/fam.json')))
H = 85336458; HT = 1791669999
def when(bn): return datetime.datetime.fromtimestamp(HT - (H - bn) * 0.10281, datetime.UTC).strftime('%m-%d %H:%M')
DUST = '0xe71a69f4'
for r in F:
    crowd_from = {s['frm'] for s in r['swaps'] if s['crowd']}
    outs = []
    for s in r['swaps']:
        if s['crowd'] or s['in_launch']: continue
        if s['frm'] and s['frm'].startswith(DUST): continue
        if s['eth'] < 1.5e-5 and s['buy']: continue
        outs.append(f"{'B' if s['buy'] else 'S'}{s['rel']}:{s['eth']/1e18:.5f}:{(s['frm'] or '?')[:6]}{'*' if s['frm'] in crowd_from else ''}")
    mo = [round(s['mo']/s['tok'], 3) for s in r['swaps'] if s['crowd'] and s['mo']]
    pull = r['pull']
    nb = sum(1 for x in r['cr_rel'] if pull is None or x < pull)
    print(f"{when(r['lb'])} {r['pid'][:8]} v{r['value']/1e18:.2f} f{r['fee']} n{r['nonce']} t{r['tick0']} crowd {r['ncrowd']:2d} ({nb:2d} pre-pull) first {r['cr_rel'][0]:5d} last {r['cr_rel'][-1]:5d} pull {pull} tot {sum(r['cr_eth'])/1e18:.4f} mo {min(mo) if mo else None}-{max(mo) if mo else None} | {' '.join(o for o in outs if pull is None or int(o[1:].split(':')[0]) <= pull + 5)[:300]}")
