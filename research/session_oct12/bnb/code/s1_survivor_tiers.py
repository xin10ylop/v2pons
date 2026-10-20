# Per-tier stats of the surviving 0xc9b7cc61 line (L+60, hold 200, $15 head, crowd re-quotes = 'fresh' model)
# from the reaction lens's per-pool replay (a10_replay.json), joined to the census for msg.value and launch block.
import json, statistics as st, sys
B='/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/bnb'
rep=json.load(open(B+'/verify/reaction_PancakeSwap_V2_on_BNB_Chain__F_lc_83af7929e5a814a2ef2296c29da510961dab2/out/a10_replay.json'))
fresh={k.lower():v[0] for k,v in rep['fresh'].items()}
allm={k.lower():v[0] for k,v in rep['all'].items()}
W0,W1=125757132,127101132
DAYS=(W1-W0)*0.4503/86400
VAL0=W1-int(48.1*3600/0.4503)
VDAYS=48.1/24
info={}
with open(B+'/census_PancakeSwap_V2/pools.jsonl') as f:
    for line in f:
        if '50b6f139' not in line: continue
        p=json.loads(line); a=p['pool'].lower()
        if a in fresh:
            info[a]=(round(p['launch']['value_bnb'],2), p['launch_block'])
print('pools in replay',len(fresh),'joined',len(info),'days',round(DAYS,3),'val start block',VAL0)
def stats(keys, d):
    r=[d[k] for k in keys]
    if not r: return None
    return dict(n=len(r), mean=round(100*st.mean(r),2), median=round(100*st.median(r),2), win=round(sum(x>0 for x in r)/len(r),3))
tiers=sorted(set(v[0] for v in info.values()))
out={}
for sel_name, sel in [('all',tiers),('no15',[t for t in tiers if t!=15.0]),('1_10_25',[1.0,10.0,25.0])]+[('t%s'%t,[t]) for t in tiers]:
    ks=[k for k,v in info.items() if v[0] in sel]
    vk=[k for k in ks if info[k][1]>=VAL0]
    s=stats(ks,fresh); sv=stats(vk,fresh); sa=stats(ks,allm)
    usd=round(sum(fresh[k] for k in ks)*15/DAYS,1)
    usdv=round(sum(fresh[k] for k in vk)*15/VDAYS,1)
    usd5=round(sum(fresh[k] for k in ks)*5/DAYS,1)
    out[sel_name]=dict(whole=s,val=sv,adversarial_all_revert=sa,launches_per_day=round(len(ks)/DAYS,1),usd_day_q15_whole=usd,usd_day_q15_val=usdv,usd_day_at_q5_scaled=usd5)
    print(sel_name, json.dumps(out[sel_name]))
json.dump(out,open(B+'/report/out/s1_survivor_tiers.json','w'),indent=1)
# 6-hour slices (by launch block) for each selection
SL=int(6*3600/0.4503)
for sel_name, sel in [('all',tiers),('no15',[t for t in tiers if t!=15.0]),('1_10_25',[1.0,10.0,25.0])]:
    sl={}
    for k,v in info.items():
        if v[0] in sel: sl.setdefault((v[1]-W0)//SL,[]).append(fresh[k])
    pos=sum(1 for r in sl.values() if st.mean(r)>0); posm=sum(1 for r in sl.values() if st.median(r)>0)
    print('slices',sel_name,'n_slices',len(sl),'mean>0',pos,'median>0',posm,'min slice n',min(len(r) for r in sl.values()))
