import sys, json, glob
sys.path.insert(0, '/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad')
sys.path.insert(0, '/home/user/v2pons/src')
from chain import *
import flip_engine
from collections import Counter
SD = '/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/fp'
POSM = '0x58daec3116aae6d93017baaea7749052e8a04fa7'; VAL = 2433328500000000000; SQ = 1604517591721945638372359205383840
tx = {}
for fn in sorted(glob.glob(SD + '/d10_30_cache/tx/c*.json'))[:3]: tx.update(json.load(open(fn))['txs'])
L = []
for fn in glob.glob(SD + '/d10_30_cache/logs_*.json'): L += json.load(open(fn))
c = Counter(); fps = Counter()
blocks = []
for l in L:
    d = l['data']; fee, ts, sq = W(d, 0), sgn(W(d, 1)), W(d, 3)
    if not ((fee == 2500 and ts == 50) or sq == SQ): continue
    t = tx.get(l['transactionHash'])
    if not t: c['missing'] += 1; continue
    key = ((t['to'] or '').lower() == POSM, int(t['value']) == VAL, t['input_len'], t['selector'], sq == SQ, fee, ts)
    c[key] += 1
    if key[0] and key[2] == 1444:
        dd = flip_engine.decode_launch(bytes.fromhex(t['input'][2:]))
        if dd: fps[(dd['sqrt_p'] == SQ, dd['mint_liq'], dd['fee'], dd['tick_spacing'], dd['lo'], dd['hi'], dd['hooks'] == '0'*40, int(t['value']))] += 1
    if key[0] and key[1] and key[2] == 1444: blocks.append(l['blockNumber'])
for k, v in c.most_common(): print(v, k)
for k, v in fps.most_common(): print(v, k)
b = sorted(int(x, 16) for x in blocks); print('family blocks', len(b), b[:3], b[-3:])
