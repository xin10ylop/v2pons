import sys, json, os, time, datetime
SP='/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad'
sys.path.insert(0, SP); sys.path.insert(0, '/home/user/v2pons/src')
from chain import *
import flip_engine
OUT=SP+'/fpv'; CD=OUT+'/cache'; os.makedirs(CD, exist_ok=True)
POSM='0x58daec3116aae6d93017baaea7749052e8a04fa7'; VAL=2433328500000000000; SQ=1604517591721945638372359205383840
A=82879335; B=int(rpc('eth_blockNumber',[]),16)
flt={'address': PM, 'topics': [T_INIT, None, '0x'+'0'*64]}
allL=[]; chunks=[]
a=A
while a<=B:
    b=min(a+99999,B); fn=f'{CD}/logs_{a}_{b}.json'
    if os.path.exists(fn): L=json.load(open(fn))
    else:
        for k in range(8):
            try: L=logs(flt,a,b); break
            except Exception as e: print('err',a,b,e,flush=True); time.sleep(5+3*k)
        else: raise SystemExit('log gap %d %d'%(a,b))
        json.dump(L,open(fn,'w'))
    chunks.append([a,b,len(L)]); print(a,b,len(L),flush=True); allL+=L; a=b+1
def robust(calls, step=50):
    out=[None]*len(calls); todo=list(range(len(calls)))
    for it in range(12):
        if not todo: break
        nt=[]
        for s in range(0,len(todo),step):
            idx=todo[s:s+step]
            try: r=batch([calls[i] for i in idx])
            except Exception as e: print('batch err',e,flush=True); time.sleep(5); nt+=idx; continue
            for i,x in zip(idx,r):
                if x is None: nt.append(i)
                else: out[i]=x
            if s % 2000 == 0: print(' tx progress', s, len(todo), flush=True)
        todo=nt
        if todo: print('retry',it,len(todo),flush=True); time.sleep(3+2*it)
    return out,todo
txh=sorted(set(l['transactionHash'] for l in allL)); print('logs',len(allL),'txs',len(txh),flush=True)
tfn=CD+'/txs.json'
txm=json.load(open(tfn)) if os.path.exists(tfn) else {}
need=[h for h in txh if h not in txm]
r,miss=robust([('eth_getTransactionByHash',[h]) for h in need])
for h,t in zip(need,r):
    if t: txm[h]={'from':t['from'],'to':t['to'],'value':t['value'],'input':t['input'],'nonce':t['nonce']}
json.dump(txm,open(tfn,'w'))
print('missing tx',len(miss),flush=True)
blks=sorted(set(int(l['blockNumber'],16) for l in allL))
bfn=CD+'/bts.json'
bts={int(k):v for k,v in json.load(open(bfn)).items()} if os.path.exists(bfn) else {}
needb=[n for n in blks if n not in bts]
r,missb=robust([('eth_getBlockByNumber',[hex(n),False]) for n in needb])
for n,h in zip(needb,r):
    if h: bts[n]=int(h['timestamp'],16)
json.dump(bts,open(bfn,'w'))
print('missing blocks',len(missb),flush=True)
rows=[]
for l in allL:
    d=l['data']; fee,tsp,hooks,sq,tick=W(d,0),sgn(W(d,1)),W(d,2),W(d,3),sgn(W(d,4))
    t=txm.get(l['transactionHash']); bn=int(l['blockNumber'],16); ts=bts.get(bn)
    row=dict(block=bn,tx=l['transactionHash'],log_index=int(l['logIndex'],16),pid=l['topics'][1],token=l['topics'][3][-40:],ev_fee=fee,ev_ts=tsp,ev_hooks=hooks,ev_sqrt=str(sq),ev_tick=tick,ts=ts,
             day=datetime.datetime.fromtimestamp(ts,datetime.UTC).strftime('%Y-%m-%d') if ts else None)
    if t:
        inp=bytes.fromhex(t['input'][2:]); val=int(t['value'],16)
        dec=flip_engine.decode_launch(inp) if (t['to'] or '').lower()==POSM else None
        if dec: dec={k:(str(v) if isinstance(v,int) and abs(v)>2**53 else v) for k,v in dec.items()}
        row.update(frm=t['from'],to=t['to'],value=str(val),input_len=len(inp),selector=t['input'][2:10],decoded=dec,
                   family=(t['to'] or '').lower()==POSM and val==VAL and len(inp)==1444 and t['input'][2:10]=='ac9650d8')
    else: row['tx_missing']=True
    rows.append(row)
rows.sort(key=lambda k:(k['block'],k['log_index']))
with open(OUT+'/scan_all.jsonl','w') as f:
    for k in rows: f.write(json.dumps(k)+'\n')
json.dump({'A':A,'B':B,'chunks':chunks,'n_logs':len(allL),'n_tx':len(txh),'miss_tx':len(miss),'miss_b':len(missb)},open(OUT+'/scan_meta.json','w'))
print('done',A,B,len(rows),flush=True)
