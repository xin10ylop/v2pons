import sys, json, os, time
sys.path.insert(0, '/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad')
from chain import *
from concurrent.futures import ThreadPoolExecutor
A, B = 59391955, 77007489
CD = '/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/fp/d10_30_cache'
flt = {'address': PM, 'topics': [T_INIT, None, '0x' + '0'*64]}
chunks = []
a = A
while a <= B:
    b = min(a + 99999, B); chunks.append((a, b)); a = b + 1
def job(ab):
    a, b = ab
    fn = f'{CD}/logs_{a}_{b}.json'
    if os.path.exists(fn): return a, b, len(json.load(open(fn))), None
    for k in range(6):
        try:
            L = logs(flt, a, b)
            # sanity: all logs in range
            assert all(a <= int(l['blockNumber'], 16) <= b for l in L)
            json.dump(L, open(fn + '.tmp', 'w')); os.replace(fn + '.tmp', fn)
            return a, b, len(L), None
        except Exception as e:
            print('err', a, b, repr(e)[:200], flush=True); time.sleep(5 * (k + 1))
    return a, b, None, 'fail'
gaps = []
with ThreadPoolExecutor(4) as ex:
    for a, b, n, err in ex.map(job, chunks):
        print(a, b, n, err, flush=True)
        if err: gaps.append([a, b])
print('chunks', len(chunks), 'gaps', gaps, flush=True)
json.dump({'chunks': chunks, 'gaps': gaps}, open(CD + '/../d10_30_logs_meta.json', 'w'))
