import sys, json, glob, os, re, collections
SP='/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad'
sys.path.insert(0, SP); from chain import W, sgn
VAL=2433328500000000000; SQ=1604517591721945638372359205383840; POSM='0x58daec3116aae6d93017baaea7749052e8a04fa7'
fams=json.load(open(SP+'/fpv/fams.json')); famtx=set(r['tx'] for r in fams)
for lab,cd,A,B in [('d10_30',SP+'/fp/d10_30_cache',59391955,77007489),('d2_9',SP+'/fp/d2_9_v2_cache',77007490,82879334)]:
    fs=sorted(glob.glob(cd+'/logs_*.json'),key=lambda f:int(re.findall(r'logs_(\d+)_',f)[0]))
    spans=[tuple(map(int,re.findall(r'logs_(\d+)_(\d+)',f)[0])) for f in fs]
    contig=spans[0][0]==A and spans[-1][1]==B and all(spans[i][1]+1==spans[i+1][0] for i in range(len(spans)-1))
    L=[l for f in fs for l in json.load(open(f))]
    sq=[l for l in L if W(l['data'],3)==SQ]; tier=[l for l in L if (W(l['data'],0),sgn(W(l['data'],1)))==(2500,50)]
    print(lab,'chunks',len(fs),'contiguous',contig,'logs',len(L),'sqrt-match',len(sq),'tier',len(tier),'sqrt-match not in family tx set',sum(1 for l in sq if l['transactionHash'] not in famtx),
          'sqrt-match with tier!=2500/50',sum(1 for l in sq if (W(l['data'],0),sgn(W(l['data'],1)))!=(2500,50)))
    txh=set(l['transactionHash'] for l in L); print('   unique tx',len(txh))
# tx caches
tx={}
for f in glob.glob(SP+'/fp/d10_30_cache/tx/*.json'): tx.update(json.load(open(f))['txs'])
L=[l for f in glob.glob(SP+'/fp/d10_30_cache/logs_*.json') for l in json.load(open(f))]
need=set(l['transactionHash'] for l in L); print('d10_30 tx cache',len(tx),'needed',len(need),'missing',len(need-set(tx)))
v=[h for h,t in tx.items() if int(t['value'])==VAL]
print('d10_30 value-2.4333285 txs',len(v),'non-family',[h for h in v if h not in famtx][:5])
fam_shape=[h for h in v if t_ok(h)] if False else None
d=json.load(open(SP+'/fp/d2_9_rest_tx.json')); print('d2_9_rest_tx keys',list(d.keys()), {k:(len(x) if hasattr(x,'__len__') else x) for k,x in d.items()})
tx2=d['txs']; L2=[l for f in glob.glob(SP+'/fp/d2_9_v2_cache/logs_*.json') for l in json.load(open(f))]
need2=set(l['transactionHash'] for l in L2)
print('d2_9 earlier-attempt tx cache',len(tx2),'cover of needed',len(need2 & set(tx2)),'of',len(need2))
v2=[h for h,t in tx2.items() if int(t['value'])==VAL]; print('d2_9 rest value-2.4333285 txs',len(v2),'non-family',[h for h in v2 if h not in famtx][:5])
