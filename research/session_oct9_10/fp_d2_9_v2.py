import sys, json, os, time, datetime
SP = '/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad'
sys.path.insert(0, SP)
sys.path.insert(0, '/home/user/v2pons/src')
from chain import *
import flip_engine
A, B = 77007490, 82879334
SD = SP + '/fp'
CD = SD + '/d2_9_v2_cache'
os.makedirs(CD, exist_ok=True)
POSM = '0x58daec3116aae6d93017baaea7749052e8a04fa7'
VAL = 2433328500000000000
SQ = 1604517591721945638372359205383840
flt = {'address': PM, 'topics': [T_INIT, None, '0x' + '0'*64]}

def getlogs(a, b):
    for k in range(8):
        try: return logs(flt, a, b)
        except Exception as e: print('err', a, b, e, flush=True); time.sleep(5 + 3*k)
    return None

# (1) logs, fresh, with a half-split completeness check per chunk
gaps, mismatch, allL = [], [], []
a = A
while a <= B:
    b = min(a + 99999, B)
    fn = f'{CD}/logs_{a}_{b}.json'
    if os.path.exists(fn):
        L = json.load(open(fn))
    else:
        L = getlogs(a, b)
        if L is None: gaps.append([a, b]); a = b + 1; continue
        m = (a + b) // 2
        L1, L2 = getlogs(a, m), getlogs(m + 1, b)
        if L1 is None or L2 is None:
            mismatch.append([a, b, 'half query failed'])
        else:
            k0 = sorted((l['transactionHash'], l['logIndex']) for l in L)
            k1 = sorted((l['transactionHash'], l['logIndex']) for l in L1 + L2)
            if k0 != k1:
                mismatch.append([a, b, len(L), len(L1) + len(L2)])
                print('MISMATCH', a, b, len(L), len(L1) + len(L2), flush=True)
                # take the union
                seen = {}
                for l in L + L1 + L2: seen[(l['transactionHash'], l['logIndex'])] = l
                L = list(seen.values())
        bad = [l for l in L if not a <= int(l['blockNumber'], 16) <= b]
        if bad: print('OUT OF RANGE', a, b, len(bad), flush=True)
        json.dump(L, open(fn, 'w'))
    print(a, b, len(L), flush=True)
    allL += L
    a = b + 1
print('total logs', len(allL), 'gaps', gaps, 'mismatch', mismatch, flush=True)

def robust(calls, step=100):
    out = [None]*len(calls)
    todo = list(range(len(calls)))
    for it in range(10):
        if not todo: break
        nt = []
        for s in range(0, len(todo), step):
            idx = todo[s:s+step]
            try:
                r = batch([calls[i] for i in idx])
            except Exception as e:
                print('batch err', e, flush=True); time.sleep(5); nt += idx; continue
            for i, x in zip(idx, r):
                if x is None: nt.append(i)
                else: out[i] = x
        todo = nt
        if todo: print('retry', it, len(todo), flush=True); time.sleep(3 + 2*it)
    return out, todo

# (3) every transaction behind an ETH-pair Initialize (so value-2.4333285 launches on other tiers are seen too)
txh = sorted(set(l['transactionHash'] for l in allL))
print('unique txs', len(txh), flush=True)
txs, miss_tx = robust([('eth_getTransactionByHash', [h]) for h in txh])
txm = dict(zip(txh, txs))
print('missing tx', len(miss_tx), flush=True)

rows = []
for l in allL:
    d = l['data']
    fee, tsp, hooks, sq, tick = W(d,0), sgn(W(d,1)), W(d,2), W(d,3), sgn(W(d,4))
    t = txm.get(l['transactionHash'])
    val = int(t['value'], 16) if t else None
    tier = fee == 2500 and tsp == 50
    if not (tier or sq == SQ or val == VAL):
        continue
    k = dict(block=int(l['blockNumber'],16), tx=l['transactionHash'], log_index=int(l['logIndex'],16), pid=l['topics'][1], token=l['topics'][3][-40:],
             ev_fee=fee, ev_ts=tsp, ev_hooks='0x%040x' % hooks, ev_sqrt=str(sq), ev_tick=tick,
             kept_by=('tier' if tier else '') + ('+sqrt' if sq == SQ else '') + ('+value' if val == VAL else ''))
    if t:
        inp = bytes.fromhex(t['input'][2:])
        k.update(frm=t['from'], to=t['to'], value=str(val), input_len=len(inp), selector=t['input'][:10], nonce=int(t['nonce'],16))
        dec = None
        if t['to'] and t['to'].lower() == POSM and len(inp) == 1444:
            dec = flip_engine.decode_launch(inp)
        if dec:
            dec = {kk: (str(v) if isinstance(v, int) and abs(v) > 2**53 else v) for kk, v in dec.items()}
        k['decoded'] = dec
        k['family'] = bool(t['to'] and t['to'].lower() == POSM and val == VAL and len(inp) == 1444 and t['input'][:10] == '0xac9650d8')
    else:
        k['tx_missing'] = True; k['family'] = None
    rows.append(k)
print('kept rows', len(rows), flush=True)

# (4) block timestamps for every kept row
blks = sorted(set(k['block'] for k in rows))
bh, miss_b = robust([('eth_getBlockByNumber', [hex(n), False]) for n in blks])
bts = {n: (int(h['timestamp'],16) if h else None) for n, h in zip(blks, bh)}
print('missing blocks', len(miss_b), flush=True)
rows.sort(key=lambda k: (k['block'], k['log_index']))
with open(f'{SD}/d2_9.jsonl', 'w') as f:
    for k in rows:
        ts = bts.get(k['block'])
        k['ts'] = ts; k['day'] = datetime.datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d') if ts else None
        f.write(json.dumps(k) + '\n')
# chunk boundary times, for the record
edges = sorted(set([A, B] + [x for x in range(A, B, 100000)]))
eh, _ = robust([('eth_getBlockByNumber', [hex(n), False]) for n in edges])
json.dump({'range': [A, B], 'gaps': gaps, 'half_split_mismatch': mismatch, 'miss_tx': [txh[i] for i in miss_tx], 'miss_b': [blks[i] for i in miss_b],
           'n_logs': len(allL), 'n_unique_tx': len(txh), 'n_kept': len(rows),
           'edge_ts': {n: (int(h['timestamp'],16) if h else None) for n, h in zip(edges, eh)}}, open(f'{SD}/d2_9_meta.json', 'w'))
print('done', flush=True)
