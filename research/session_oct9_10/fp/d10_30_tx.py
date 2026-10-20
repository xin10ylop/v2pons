import sys, json, os, time, glob
sys.path.insert(0, '/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad')
from chain import *
from concurrent.futures import ThreadPoolExecutor
SD = '/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/fp'
CD = SD + '/d10_30_cache'
POSM = '0x58daec3116aae6d93017baaea7749052e8a04fa7'
VAL = 2433328500000000000
SQ = 1604517591721945638372359205383840
L = []
for fn in glob.glob(CD + '/logs_*.json'): L += json.load(open(fn))
keptx = set()
for l in L:
    d = l['data']; fee, ts, sq = W(d, 0), sgn(W(d, 1)), W(d, 3)
    if (fee == 2500 and ts == 50) or sq == SQ: keptx.add(l['transactionHash'])
allx = sorted(set(l['transactionHash'] for l in L))
order = sorted(keptx) + [h for h in allx if h not in keptx]   # kept first
os.makedirs(CD + '/tx', exist_ok=True)
chunks = [order[i:i+500] for i in range(0, len(order), 500)]
def one_batch(hs):
    r = post([{"jsonrpc": "2.0", "id": j, "method": 'eth_getTransactionByHash', "params": [h]} for j, h in enumerate(hs)])
    if not isinstance(r, list): raise RuntimeError('nonlist ' + str(r)[:200])
    m = {x['id']: x.get('result') for x in r}
    return [m.get(j) for j in range(len(hs))]
def job(ci):
    fn = f'{CD}/tx/c{ci:04d}.json'
    if os.path.exists(fn): return ci, 0
    hs = chunks[ci]; out = {}; todo = list(hs)
    for it in range(10):
        nt = []
        for i in range(0, len(todo), 50):
            sub = todo[i:i+50]
            try: r = one_batch(sub)
            except Exception as e:
                print('err', ci, repr(e)[:150], flush=True); time.sleep(3); nt += sub; continue
            for h, x in zip(sub, r):
                if x is None: nt.append(h); continue
                inp = x['input']; n = (len(inp) - 2) // 2
                keep_inp = h in keptx or int(x['value'], 16) == VAL or ((x['to'] or '').lower() == POSM and n == 1444)
                out[h] = dict(frm=x['from'], to=x['to'], value=str(int(x['value'], 16)), input_len=n, selector=inp[:10], nonce=int(x['nonce'], 16),
                              block=int(x['blockNumber'], 16), input=inp if keep_inp else None)
        todo = nt
        if not todo: break
        time.sleep(3 * (it + 1))
    json.dump({'txs': out, 'miss': todo}, open(fn + '.tmp', 'w')); os.replace(fn + '.tmp', fn)
    return ci, len(todo)
print('kept tx', len(keptx), 'all tx', len(allx), 'chunks', len(chunks), flush=True)
t0 = time.time()
with ThreadPoolExecutor(4) as ex:
    for ci, nm in ex.map(job, range(len(chunks))):
        print(ci, nm, round(time.time() - t0), flush=True)
print('done', flush=True)
