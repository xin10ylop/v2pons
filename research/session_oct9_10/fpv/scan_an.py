import json, collections
SP='/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad'
VAL=2433328500000000000; SQ='1604517591721945638372359205383840'
rows=[json.loads(l) for l in open(SP+'/fpv/scan_all.jsonl')]
print('rows',len(rows),'tx missing',sum(1 for r in rows if r.get('tx_missing')))
def fp(r):
    d=r['decoded']; return (d['sqrt_p'],d['mint_liq'],d['fee'],d['tick_spacing'],d['lo'],d['hi'],d['hooks']) if d else None
fam=[r for r in rows if r.get('family')]
print('family',len(fam),'distinct fps',collections.Counter(fp(r) for r in fam))
def seg(b): return 'census 82879335-84238619' if b<=84238619 else 'recent 84238620-84540923' if b<=84540923 else 'oct10 84540924-84849139' if b<=84849139 else 'tail 84849140-84852915'
per=collections.defaultdict(collections.Counter)
for r in fam: per[(r['day'])][seg(r['block'])]+=1
for d in sorted(per): print(d,sum(per[d].values()),dict(per[d]))
print('Oct8-9 census range family:',sum(1 for r in fam if r['block']<=84238619))
# compare to agent files
ag={}
for lab in ['recent','oct10']:
    for l in open(SP+f'/fp/{lab}.jsonl'):
        r=json.loads(l); ag[r['tx']]=lab
mine=set(r['tx'] for r in fam if 84238620<=r['block']<=84849139)
print('recent+oct10: mine',len(mine),'agents',len(ag),'only mine',len(mine-set(ag)),'only agents',len(set(ag)-mine))
sv=[r for r in rows if r.get('value') and int(r['value'])==VAL and not (r.get('family') and fp(r)[:6]==(SQ,'49279426163460954002188',2500,50,-887250,887250))]
print('value 2.4333285 not family-fp:',len(sv),[(r['block'],r['to'],r['input_len'],r['ev_fee'],r['ev_ts'],r['ev_sqrt']) for r in sv[:10]])
la=[r for r in rows if r['ev_sqrt']==SQ and not r.get('family')]; print('lookalikes by event sqrt',len(la))
la2=[r for r in rows if r.get('decoded') and r['decoded']['sqrt_p']==SQ and not r.get('family')]; print('lookalikes by decoded sqrt',len(la2))
tier=[r for r in rows if (r['ev_fee'],r['ev_ts'])==(2500,50) and not r.get('family')]
print('tier 2500/50 non-family',len(tier),[(r['block'],r['day'],r['to'],r['value'],r['input_len'],r['selector'],r['ev_sqrt'],fp(r)) for r in tier])
evbad=[r for r in fam if not (r['ev_sqrt']==r['decoded']['sqrt_p'] and r['ev_fee']==2500 and r['ev_ts']==50 and r['ev_hooks']==0 and r['pid']==r['decoded']['pid'])]; print('event/decode mismatch',len(evbad))
# near-miss: POSM 1444 multicalls with family mint_liq or value close to 2.4333
nm=[r for r in rows if r.get('decoded') and r['decoded']['mint_liq']=='49279426163460954002188' and not r.get('family')]; print('family mint_liq but not family',len(nm))
vals=collections.Counter(r['value'] for r in rows if r.get('to') and r['to'].lower()=='0x58daec3116aae6d93017baaea7749052e8a04fa7' and r['input_len']==1444 and r['value'] and abs(int(r['value'])-VAL)<VAL*0.05 and int(r['value'])!=VAL); print('POSM-1444 values within 5% of 2.4333285 but not equal:',vals.most_common(5))
print('senders',len(set(r['frm'] for r in fam)),'pids',len(set(r['pid'] for r in fam)))
f=[r for r in fam]; print('first in scan',f[0]['block'],f[0]['day'],'last',f[-1]['block'],f[-1]['ts'])
# hourly gaps > 3h within scan
import datetime
ts=[r['ts'] for r in fam]; g=[(datetime.datetime.fromtimestamp(a,datetime.UTC),round((b-a)/3600,2)) for a,b in zip(ts,ts[1:]) if b-a>3*3600]; print('gaps>3h',g)
