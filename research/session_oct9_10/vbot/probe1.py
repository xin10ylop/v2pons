import sys, json, pickle
sys.path.insert(0, '..'); sys.path.insert(0, '/home/user/v2pons/src')
from chain import *
R=[json.loads(l) for l in open('../others/census.jsonl')]
v3=[r for r in R if r['sel']=='0xac9650d8' and r['inlen']==1444 and r['fee']==10000 and r['ts']==200 and round(r['value'] or 0,3)==3.0]
v3.sort(key=lambda r:r['b0'])
r=v3[400]
print(json.dumps({k:v for k,v in r.items() if k!='paper'}))
b0=r['b0']; tok=r['token'][2:].lower()
blocks=batch([("eth_getBlockByNumber",[hex(b0+k),True]) for k in range(0,61)])
pickle.dump(blocks, open('probe1_blocks.pkl','wb'))
for k,b in enumerate(blocks):
    for t in b['transactions']:
        inp=t['input']
        if tok in inp.lower() or t['hash']==r['tx']:
            print(k, int(t['transactionIndex'],16), t['from'][:12], int(t['nonce'],16), (t['to'] or '')[:12], int(t['value'],16)/1e18, len(inp)//2-1, inp[:10], t.get('maxPriorityFeePerGas'), t['type'])
print('ntx per block', [len(b['transactions']) for b in blocks])
