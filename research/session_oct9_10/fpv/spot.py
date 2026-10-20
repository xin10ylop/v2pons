import sys, json, random, datetime
SP='/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad'
sys.path.insert(0, SP); sys.path.insert(0,'/home/user/v2pons/src')
from chain import *
import flip_engine
fams=json.load(open(SP+'/fpv/fams.json'))
random.seed(20261010)
picks=[]
for day in ['2026-09-26','2026-09-29','2026-10-03','2026-10-07','2026-10-10']:
    c=[r for r in fams if r['day']==day]; picks.append(random.choice(c))
for p in picks:
    t=rpc('eth_getTransactionByHash',[p['tx']]); rc=rpc('eth_getTransactionReceipt',[p['tx']]); bh=rpc('eth_getBlockByNumber',[t['blockNumber'],False])
    inp=bytes.fromhex(t['input'][2:]); d=flip_engine.decode_launch(inp)
    init=[l for l in rc['logs'] if l['topics'][0]==T_INIT and l['address'].lower()==PM]
    ev=init[0]['data']; 
    print(p['lab'],p['day'],'block',int(t['blockNumber'],16),p['tx'])
    print('  utc',datetime.datetime.fromtimestamp(int(bh['timestamp'],16),datetime.UTC),'status',rc['status'],'to',t['to'],'value',int(t['value'],16),'len',len(inp),'sel',t['input'][:10],'from',t['from'])
    print('  decoded: sqrt',d['sqrt_p'],'liq',d['mint_liq'],'fee',d['fee'],'ts',d['tick_spacing'],'lo',d['lo'],'hi',d['hi'],'hooks',d['hooks'],'c0',d['c0'])
    print('  receipt Initialize: id',init[0]['topics'][1]==d['pid'],'c0',init[0]['topics'][2][-40:],'fee',W(ev,0),'ts',sgn(W(ev,1)),'sqrt',W(ev,3),'tick',sgn(W(ev,4)),'| n Init logs',len(init))
    print('  matches saved row:', str(d['sqrt_p'])==p['ev_sqrt'] and d['pid']==p['pid'] and int(t['value'],16)==int(p['value']))
