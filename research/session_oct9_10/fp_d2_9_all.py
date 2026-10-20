import sys, json, os, time, glob
sys.path.insert(0, '/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad')
sys.path.insert(0, '/home/user/v2pons/src')
from chain import *
import flip_engine
SD = '/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/fp'
allL = []
for fn in glob.glob(SD + '/d2_9_cache/logs_*.json'): allL += json.load(open(fn))
kept = set(json.loads(l)['tx'] for l in open(SD + '/d2_9.jsonl'))
rest = sorted(set(l['transactionHash'] for l in allL) - kept)
print('rest txs', len(rest), flush=True)
out = {}
miss = []
for i in range(0, len(rest), 500):
    ch = rest[i:i+500]
    todo = ch
    for it in range(8):
        try: r = batch([('eth_getTransactionByHash', [h]) for h in todo])
        except Exception as e: print('err', e, flush=True); time.sleep(5); continue
        nt = []
        for h, x in zip(todo, r):
            if x is None: nt.append(h)
            else: out[h] = dict(to=x['to'], value=str(int(x['value'], 16)), input_len=(len(x['input'])-2)//2, selector=x['input'][:10], frm=x['from'], input=x['input'] if (x['to'] or '').lower()=='0x58daec3116aae6d93017baaea7749052e8a04fa7' and (len(x['input'])-2)//2==1444 else None)
        todo = nt
        if not todo: break
        time.sleep(3)
    miss += todo
    if i % 5000 == 0: print(i, len(out), len(miss), flush=True)
json.dump({'txs': out, 'miss': miss}, open(SD + '/d2_9_rest_tx.json', 'w'))
print('done', len(out), len(miss))
