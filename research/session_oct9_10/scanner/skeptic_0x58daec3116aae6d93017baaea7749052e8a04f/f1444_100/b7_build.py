# per-pool rows for every candidate (POSM ac9650d8 1444-byte, fee 100/ts 1 or fee 500/ts 10, value >= 0.4 ETH), Sep 11 - Oct 10
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json, collections
HERE = os.path.dirname(os.path.abspath(__file__))
C = json.load(open(os.path.join(HERE, 'data/cands.json'))); EV = json.load(open(os.path.join(HERE, 'data/events.json'))); S = json.load(open(os.path.join(HERE, 'data/stx.json')))
UR = '0x8876789976decbfcbbbe364623c63652db8c0904'; DUST = '0xe71a69f4'
RELAY = '0x2abb5653352f6b2f3b4f4261877cd02d9e05a957'
def ur_minout(inp, value):
    d = inp[10:]; n = len(d) // 64
    if n < 23: return None
    w = [int(d[64*i:64*i+64], 16) for i in range(n)]
    if w[21] == value: return w[22]
    return None
rows = []
for c in C:
    e = EV[c['pid']]; lb = c['bn']
    sw = []
    for s in e['swaps']:
        t = S.get(s['tx']) or {}
        buy = s['a0'] < 0
        crowd = bool(t) and t['to'] == UR and t['sel'] == '3593564c' and t['clen'] == 1284 and t['nonce'] == 0 and buy
        mo = ur_minout(t['input'], t['value']) if crowd and len(t.get('input', '')) > 1000 else None
        sw.append(dict(rel=s['bn'] - lb, bn=s['bn'], ti=s['ti'], li=s['li'], buy=buy, eth=abs(s['a0']), tok=abs(s['a1']), sp=s['sp'], liq=s['liq'], fee=s['fee'],
                       frm=t.get('frm'), to=t.get('to'), sel=t.get('sel'), clen=t.get('clen'), nonce=t.get('nonce'), crowd=crowd, mo=mo, tx=s['tx'], in_launch=s['tx'] == c['tx']))
    pulls = []
    for m in e['mods']:
        if m['tx'] == c['tx']: continue
        t = S.get(m['tx']) or {}
        pulls.append(dict(rel=m['bn'] - lb, bn=m['bn'], dl=m['dl'], frm=t.get('frm'), to=t.get('to'), sel=t.get('sel'), lo=m['lo'], hi=m['hi']))
    adds = [m for m in e['mods'] if m['tx'] == c['tx']]
    rows.append(dict(pid=c['pid'], token=c['token'], lb=lb, tx=c['tx'], launcher=c['frm'], nonce=c['nonce'], value=c['value'], fee=c['fee'], ts=c['ts'], sp0=c['sp'], tick0=c['tick'],
                     L0=sum(a['dl'] for a in adds), adds=[(a['lo'], a['hi'], a['dl']) for a in adds], ev_to=e['to'], swaps=sw, mods=pulls))
json.dump(rows, open(os.path.join(HERE, 'data/rows.json'), 'w'))
print(len(rows))
