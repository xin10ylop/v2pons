import json, collections, sys
D='/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/fp/'
POSM='0x58daec3116aae6d93017baaea7749052e8a04fa7'; VAL=2433328500000000000; SQ='1604517591721945638372359205383840'
RANGES={'d10_30':(59391955,77007489),'d2_9':(77007490,82879334),'recent':(84238620,84540923),'oct10':(84540924,84849139)}
allrows=[]
for lab,(a,b) in RANGES.items():
    rows=[json.loads(l) for l in open(D+lab+'.jsonl')]
    keys=collections.Counter(k for r in rows for k in r)
    print('==',lab,len(rows),'keys:',sorted(keys))
    oor=[r['block'] for r in rows if not a<=r['block']<=b]
    print(' out of range rows:',len(oor))
    for r in rows:
        r['_lab']=lab
        r['_dec']=r.get('dec') or r.get('decoded')
        r['_sel']=(r.get('selector') or '').lower().removeprefix('0x')
        r['_li']=r.get('logIndex',r.get('log_index'))
    allrows+=rows
# dedupe check
c=collections.Counter((r['tx'],r['_li']) for r in allrows)
print('dup (tx,logIndex):',sum(1 for v in c.values() if v>1))
def fam(r): return (r.get('to') or '').lower()==POSM and int(r.get('value') or 0)==VAL and r.get('input_len')==1444 and r['_sel']=='ac9650d8'
fams=[r for r in allrows if fam(r)]
print('family rows by my def:',len(fams))
# compare to agents' flag
for lab in RANGES:
    mine=sum(1 for r in fams if r['_lab']==lab); theirs=sum(1 for r in allrows if r['_lab']==lab and r.get('family'))
    print(' ',lab,'mine',mine,'agent family flag',theirs)
nodec=[r for r in fams if not r['_dec']]; print('family w/o decode:',len(nodec))
def fp(r):
    d=r['_dec']; return (d['sqrt_p'],d['mint_liq'],d['fee'],d['tick_spacing'],d['lo'],d['hi'],d['hooks'],d['c0'])
# event vs decode consistency
bad=[r for r in fams if not (str(r['ev_sqrt'])==r['_dec']['sqrt_p'] and r['ev_fee']==r['_dec']['fee'] and r['ev_ts']==r['_dec']['tick_spacing'] and r['pid'].lower()==r['_dec']['pid'].lower() and int(r['ev_hooks'],16)==0)]
print('event/decode mismatches:',len(bad))
# token check
tk=[r for r in fams if (r.get('currency1') or r.get('token') or '').lower().removeprefix('0x')!=r['_dec']['token'].lower()]
print('token mismatches:',len(tk))
json.dump([{k:v for k,v in r.items() if not k.startswith('_')}|{'lab':r['_lab']} for r in fams],open('/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/fpv/fams.json','w'))
per=collections.defaultdict(collections.Counter)
for r in fams: per[r['day']][fp(r)]+=1
fps=collections.Counter(fp(r) for r in fams); print('distinct fingerprints overall:',fps)
for d in sorted(per): print(d, sum(per[d].values()), len(per[d]), sorted(set(r['_lab'] for r in fams if r['day']==d)))
# same value other fp, lookalikes across all rows
sv=[r for r in allrows if int(r.get('value') or 0)==VAL and not (fam(r) and fp(r)[:6]==(SQ,'49279426163460954002188',2500,50,-887250,887250))]
print('value 2.4333285 but not family-fp:',len(sv))
la=[r for r in allrows if str(r.get('ev_sqrt'))==SQ and not fam(r)]
print('lookalikes (family sqrt, not family tx):',len(la))
la2=[r for r in allrows if r['_dec'] and r['_dec']['sqrt_p']==SQ and not fam(r)]; print('lookalikes by decoded sqrt:',len(la2))
# family sqrt in rows that are not 2500/50
print('rows with family sqrt and tier != 2500/50:',sum(1 for r in allrows if str(r.get('ev_sqrt'))==SQ and (r['ev_fee'],r['ev_ts'])!=(2500,50)))
# tier rows not family
tier=[r for r in allrows if (r['ev_fee'],r['ev_ts'])==(2500,50) and not fam(r)]
print('tier 2500/50 non-family:',len(tier))
for r in tier: print('  ',r['_lab'],r['block'],r.get('to'),r.get('value'),r.get('input_len'),r['_sel'],r['ev_sqrt'],(r['_dec'] or {}).get('mint_liq'),(r['_dec'] or {}).get('lo'),(r['_dec'] or {}).get('hi'))
# senders
s=collections.Counter(r['frm'] for r in fams); print('senders',len(s),'max',s.most_common(3))
print('distinct tx',len(set(r['tx'] for r in fams)),'pids',len(set(r['pid'] for r in fams)),'tokens',len(set(r['_dec']['token'] for r in fams)))
fb=min(fams,key=lambda r:r['block']); lb=max(fams,key=lambda r:r['block'])
print('first',fb['block'],fb['tx'],fb['day'],fb.get('ts'),'last',lb['block'],lb['day'],lb.get('ts'))
