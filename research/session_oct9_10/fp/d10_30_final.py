import sys, json, glob, bisect
sys.path.insert(0, '/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad')
sys.path.insert(0, '/home/user/v2pons/src')
from chain import *
import flip_engine
from collections import Counter, defaultdict
SD = '/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/fp'
POSM = '0x58daec3116aae6d93017baaea7749052e8a04fa7'; VAL = 2433328500000000000; SQ = 1604517591721945638372359205383840
A, B = 59391955, 77007489
days = json.load(open(SD + '/d10_30_days.json'))
dk = sorted(days['first_block_of_day'].items(), key=lambda x: x[1]); dnames = ['2026-09-10'] + [d for d, _ in dk]; dstarts = [A] + [b for _, b in dk]
def day(n): return dnames[bisect.bisect_right(dstarts, n) - 1]
L = []
for fn in glob.glob(SD + '/d10_30_cache/logs_*.json'): L += json.load(open(fn))
L.sort(key=lambda l: (int(l['blockNumber'], 16), int(l['logIndex'], 16)))
tx = {}; miss = []
for fn in sorted(glob.glob(SD + '/d10_30_cache/tx/c*.json')):
    j = json.load(open(fn)); tx.update(j['txs']); miss += j['miss']
allx = set(l['transactionHash'] for l in L)
print('logs', len(L), 'txs', len(allx), 'fetched', len(set(tx) & allx), 'missing', len(allx - set(tx)), 'miss-list', len(miss))
S = lambda v: str(v) if isinstance(v, int) and abs(v) > 2**53 else v
rows = []
for l in L:
    d = l['data']; fee, ts, hooks, sq, tick = W(d, 0), sgn(W(d, 1)), W(d, 2), W(d, 3), sgn(W(d, 4))
    h = l['transactionHash']; t = tx.get(h)
    why = []
    if fee == 2500 and ts == 50: why.append('tier')
    if sq == SQ: why.append('sqrt')
    dec = None
    if t:
        if int(t['value']) == VAL: why.append('value')
        if (t['to'] or '').lower() == POSM and t['input_len'] == 1444:
            why.append('posm1444')
            dec = flip_engine.decode_launch(bytes.fromhex(t['input'][2:]))
    elif why == []:
        continue
    if not why: continue
    blk = int(l['blockNumber'], 16)
    r = dict(block=blk, day=day(blk), tx=h, log_index=int(l['logIndex'], 16), pid=l['topics'][1], token=l['topics'][3][-40:],
             ev_fee=fee, ev_ts=ts, ev_hooks=hex(hooks), ev_sqrt=str(sq), ev_tick=tick, why=why)
    if t:
        r.update(frm=t['frm'], to=t['to'], value=t['value'], input_len=t['input_len'], selector=t['selector'], nonce=t['nonce'])
        r['decoded'] = {k: S(v) for k, v in dec.items()} if dec else None
    else:
        r['tx_missing'] = True
    rows.append(r)
with open(SD + '/d10_30.jsonl', 'w') as f:
    for r in rows: f.write(json.dumps(r) + '\n')
print('rows', len(rows), Counter(tuple(r['why']) for r in rows).most_common())
isfam = lambda r: (r.get('to') or '').lower() == POSM and r.get('value') == str(VAL) and r.get('input_len') == 1444
fpk = lambda r: (r['decoded']['sqrt_p'], r['decoded']['mint_liq'], r['decoded']['fee'], r['decoded']['tick_spacing'], r['decoded']['lo'], r['decoded']['hi'], r['decoded']['hooks']) if r.get('decoded') else ('undecodable',)
perday = defaultdict(Counter); nfam = Counter()
for r in rows:
    if isfam(r): nfam[r['day']] += 1; perday[r['day']][fpk(r)] += 1
print('\nPER DAY family')
for d in dnames: print(d, nfam[d], dict(perday[d]))
fam = [r for r in rows if isfam(r)]
if fam: print('first family', fam[0]['block'], fam[0]['day'], fam[0]['tx'], 'last', fam[-1]['block'])
print('\nVALUE == VAL but not family or other fp')
canon = (str(SQ), '49279426163460954002188', 2500, 50, -887250, 887250, '0'*40)
for r in rows:
    if r.get('value') == str(VAL) and (not isfam(r) or fpk(r) != canon): print(r['block'], r['day'], r['tx'], r.get('to'), r.get('input_len'), fpk(r))
print('\nSQRT == SQ but not family (lookalikes)')
for r in rows:
    if r['ev_sqrt'] == str(SQ) and not isfam(r): print(r['block'], r['day'], r['tx'], r.get('to'), r.get('value'), r.get('input_len'), r.get('selector'))
print('\nPOSM 1444 launches by value/fp (all ETH Initialize)')
c = Counter(); cd = defaultdict(Counter)
for r in rows:
    if 'posm1444' in r['why']:
        k = (r['value'], fpk(r)); c[k] += 1; cd[k][r['day']] += 1
for k, v in c.most_common(30): print(v, k, sorted(cd[k].items())[:3], '...', sorted(cd[k].items())[-1])
print('\ntier rows not family')
for r in rows:
    if 'tier' in r['why'] and not isfam(r): print(r['block'], r['day'], r['tx'], r.get('to'), r.get('value'), r.get('input_len'), r.get('selector'), fpk(r) if r.get('decoded') else None)
print('\nfamily senders', len(set(r['frm'] for r in fam)), Counter(r['nonce'] for r in fam).most_common(8))
# gaps between family launches
bs = [r['block'] for r in fam]; gs = sorted(b - a for a, b in zip(bs, bs[1:]))
if gs: print('gap blocks min/med/max', gs[0], gs[len(gs)//2], gs[-1])
