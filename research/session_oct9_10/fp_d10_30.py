import sys, json, os, time, datetime
sys.path.insert(0, '/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad')
sys.path.insert(0, '/home/user/v2pons/src')
from chain import *
import flip_engine
A, B = 59391955, 77007489
SD = '/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/fp'
CD = SD + '/d10_30_cache'
POSM = '0x58daec3116aae6d93017baaea7749052e8a04fa7'
VAL = 2433328500000000000
SQ = 1604517591721945638372359205383840
flt = {'address': PM, 'topics': [T_INIT, None, '0x' + '0'*64]}
gaps = []
allL = []
a = A
while a <= B:
    b = min(a + 99999, B)
    fn = f'{CD}/logs_{a}_{b}.json'
    if os.path.exists(fn):
        L = json.load(open(fn))
    else:
        L = None
        for k in range(5):
            try: L = logs(flt, a, b); break
            except Exception as e: print('err', a, b, e, flush=True); time.sleep(5)
        if L is None: gaps.append([a, b]); a = b + 1; continue
        json.dump(L, open(fn, 'w'))
    print(a, b, len(L), flush=True)
    allL += L
    a = b + 1
print('total logs', len(allL), 'gaps', gaps, flush=True)
kept = []
for l in allL:
    d = l['data']
    fee, ts, hooks, sq, tick = W(d,0), sgn(W(d,1)), W(d,2), W(d,3), sgn(W(d,4))
    if (fee == 2500 and ts == 50) or sq == SQ:
        kept.append(dict(block=int(l['blockNumber'],16), tx=l['transactionHash'], log_index=int(l['logIndex'],16), pid=l['topics'][1], token=l['topics'][3][-40:],
                         ev_fee=fee, ev_ts=ts, ev_hooks=hex(hooks), ev_sqrt=str(sq), ev_tick=tick))
print('kept', len(kept), flush=True)
def robust(calls):
    out = [None]*len(calls)
    todo = list(range(len(calls)))
    for it in range(8):
        if not todo: break
        try:
            r = batch([calls[i] for i in todo])
        except Exception as e:
            print('batch err', e, flush=True); time.sleep(5); continue
        nt = []
        for i, x in zip(todo, r):
            if x is None: nt.append(i)
            else: out[i] = x
        todo = nt
        if todo: time.sleep(3)
    return out, todo
txh = sorted(set(k['tx'] for k in kept))
txs, miss_tx = robust([('eth_getTransactionByHash', [h]) for h in txh])
txm = dict(zip(txh, txs))
blks = sorted(set(k['block'] for k in kept))
bh, miss_b = robust([('eth_getBlockByNumber', [hex(n), False]) for n in blks])
bts = {n: (int(h['timestamp'],16) if h else None) for n, h in zip(blks, bh)}
print('missing tx', len(miss_tx), 'missing blocks', len(miss_b), flush=True)
with open(f'{SD}/d10_30.jsonl', 'w') as f:
    for k in kept:
        t = txm.get(k['tx'])
        ts = bts.get(k['block'])
        k['ts'] = ts; k['day'] = datetime.datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d') if ts else None
        if t:
            inp = bytes.fromhex(t['input'][2:])
            k.update(frm=t['from'], to=t['to'], value=str(int(t['value'],16)), input_len=len(inp), selector=t['input'][:10], nonce=int(t['nonce'],16))
            dec = None
            if t['to'] and t['to'].lower() == POSM and len(inp) == 1444:
                dec = flip_engine.decode_launch(inp)
            if dec:
                dec = {kk: (str(v) if isinstance(v, int) and abs(v) > 2**53 else v) for kk, v in dec.items()}
            k['decoded'] = dec
        else:
            k['tx_missing'] = True
        f.write(json.dumps(k) + '\n')
json.dump({'gaps': gaps, 'miss_tx': [txh[i] for i in miss_tx], 'miss_b': [blks[i] for i in miss_b], 'n_logs': len(allL), 'n_kept': len(kept)}, open(f'{SD}/d10_30_meta.json', 'w'))
print('done', flush=True)
