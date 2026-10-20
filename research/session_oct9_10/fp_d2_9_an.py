import sys, json, collections
fn = sys.argv[1]
POSM = '0x58daec3116aae6d93017baaea7749052e8a04fa7'
VAL = '2433328500000000000'
SQ = '1604517591721945638372359205383840'
CANON = (SQ, '49279426163460954002188', 2500, 50, -887250, 887250)
rows = [json.loads(l) for l in open(fn)]
print('rows', len(rows), 'tx_missing', sum(1 for r in rows if r.get('tx_missing')), 'no day', sum(1 for r in rows if not r.get('day')))
def fam(r):
    return (r.get('to') or '').lower() == POSM and r.get('value') == VAL and r.get('input_len') == 1444 and r.get('selector') == '0xac9650d8'
def fp(r):
    d = r.get('decoded')
    if not d: return None
    return (str(d['sqrt_p']), str(d['mint_liq']), d['fee'], d['tick_spacing'], d['lo'], d['hi'], d['hooks'], d['c0'])
days = collections.defaultdict(lambda: collections.Counter())
nf = collections.Counter(); tier = collections.Counter(); alld = set()
first = None
for r in rows:
    alld.add(r['day'])
    if r['ev_fee'] == 2500 and r['ev_ts'] == 50: tier[r['day']] += 1
    if fam(r):
        nf[r['day']] += 1
        days[r['day']][fp(r)] += 1
        if first is None: first = r
for d in sorted(alld):
    print(d, 'tier', tier[d], 'family', nf[d])
    for k, c in days[d].most_common(): print('   ', c, k, 'CANON' if k and k[:6] == CANON and k[6] == '0'*40 else 'DIFF')
print('first family', first and (first['block'], first['day'], first['tx']))
print('--- value VAL not canonical fingerprint')
for r in rows:
    if r.get('value') == VAL:
        k = fp(r)
        if not (fam(r) and k and k[:6] == CANON and k[6] == '0'*40):
            print(r['block'], r['day'], r['tx'], r.get('to'), r.get('input_len'), r.get('selector'), k, r['ev_fee'], r['ev_ts'], r['ev_sqrt'])
print('--- sqrt SQ but not family')
for r in rows:
    if r['ev_sqrt'] == SQ and not fam(r):
        print(r['block'], r['day'], r['tx'], r.get('to'), r.get('value'), r.get('input_len'), r.get('selector'), r['ev_fee'], r['ev_ts'], r['ev_hooks'], fp(r))
# senders of family
print('--- family senders', collections.Counter(r['frm'] for r in rows if fam(r)).most_common(10))
# other common tier-2500/50 shapes
print('--- tier shapes (to,value,len) top')
print(collections.Counter(((r.get('to') or '')[:10], r.get('value'), r.get('input_len')) for r in rows if r['ev_fee'] == 2500 and r['ev_ts'] == 50).most_common(15))
