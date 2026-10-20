# verify UTC day labels of all 3491 family rows in the four agent files from fresh block headers
import sys, json, datetime, time, collections
SP='/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad'
sys.path.insert(0, SP); from chain import *
fams=json.load(open(SP+'/fpv/fams.json'))
blks=sorted(set(r['block'] for r in fams))
out={}
for i in range(0,len(blks),50):
    ch=blks[i:i+50]
    for k in range(8):
        try: r=batch([('eth_getBlockByNumber',[hex(n),False]) for n in ch]); break
        except Exception as e: print('err',e,flush=True); time.sleep(4+2*k)
    for n,h in zip(ch,r): out[n]=int(h['timestamp'],16) if h else None
print('fetched',len(out),'missing',sum(1 for v in out.values() if v is None))
bad=[];tsbad=[]
per=collections.Counter()
for r in fams:
    ts=out[r['block']]; d=datetime.datetime.fromtimestamp(ts,datetime.UTC).strftime('%Y-%m-%d')
    per[d]+=1
    if d!=r['day']: bad.append((r['lab'],r['block'],r['day'],d))
    if r.get('ts') is not None and r['ts']!=ts: tsbad.append((r['lab'],r['block'],r['ts'],ts))
print('day mismatches',len(bad),bad[:10]); print('ts mismatches',len(tsbad),tsbad[:5])
for d in sorted(per): print(d,per[d])
f=min(fams,key=lambda r:r['block']); print('first family', f['block'], datetime.datetime.fromtimestamp(out[f['block']],datetime.UTC))
