"""Oct 9 launches: creator code -> 7702 delegate; delegate code -> does it embed executor bbd947c3?"""
from lib3 import *
from collections import Counter
d = json.load(open('fac_events.json'))
o9 = [e for e in d['keep'] if e[0] >= 83719339]
cr = sorted(set(e[4] for e in o9))
codes = {}
for i in range(0, len(cr), 50):
    ch = cr[i:i+50]
    for a, c in zip(ch, batch([('eth_getCode', [a, 'latest']) for a in ch])): codes[a] = c or '0x'
    time.sleep(0.3)
dele = {}
for a, c in codes.items():
    dele[a] = '0x' + c[8:48] if c.startswith('0xef0100') else ('eoa' if c == '0x' else 'contract')
impls = sorted(set(v for v in dele.values() if v.startswith('0x')))
icode = {}
for i in range(0, len(impls), 50):
    ch = impls[i:i+50]
    for a, c in zip(ch, batch([('eth_getCode', [a, 'latest']) for a in ch])): icode[a] = c or '0x'
EXI = 'bbd947c36904eb5f28aeaa5593fbcb5a228551ad'
imp_ex = {a: (EXI in c) for a, c in icode.items()}
imp_len = {a: len(c) // 2 - 1 for a, c in icode.items()}
res = []
for e in o9:
    dl = dele[e[4]]
    res.append([e[0], e[2], e[4], dl, imp_ex.get(dl, False)])
json.dump({'res': res, 'imp_len': imp_len, 'imp_ex': imp_ex}, open('creators9.json', 'w'))
print('launches', len(o9), 'creators', len(cr))
print('creator kinds', Counter('eoa' if r[3] == 'eoa' else 'contract' if r[3] == 'contract' else '7702' for r in res))
print('7702 impls', Counter(r[3] for r in res if r[3].startswith('0x')).most_common(15))
print('impl sizes', {a[:10]: imp_len[a] for a in impls})
print('launches by creators whose delegate embeds bbd947c3:', sum(1 for r in res if r[4]))
