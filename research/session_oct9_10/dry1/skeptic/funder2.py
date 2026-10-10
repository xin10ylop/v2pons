import sys, pickle, collections
sys.path.insert(0, '/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad')
from chain import batch, rpc
D = pickle.load(open('data_s.pkl', 'rb'))
fam = D['fam']
lo, hi = 84862394 - 300, 84863214 + 10
bl = batch([("eth_getBlockByNumber", [hex(k), True]) for k in range(lo, hi)])
pickle.dump(bl, open('blk_862.pkl', 'wb'))
launchers = {x['from'].lower(): x for x in fam}
F = '0x488faf521a2d5f16ee55d1335841bb3ba9a0946e'
for b in bl:
    n = int(b['number'], 16)
    for t in b['transactions']:
        fr = t['from'].lower(); to = (t['to'] or '').lower()
        if fr == F or to in launchers or fr in launchers:
            print(n, fr[:10], '->', to[:10], round(int(t['value'], 16) / 1e18, 6), t['input'][:10], 'nonce', int(t['nonce'], 16), ('LAUNCHER of ' + launchers[to]['pid'][:10] + ' b0 ' + str(launchers[to]['bn'])) if to in launchers else '', ('from launcher of ' + launchers[fr]['pid'][:10]) if fr in launchers else '')
print('488f nonce now', int(rpc('eth_getTransactionCount', [F, 'latest']), 16), 'bal', int(rpc('eth_getBalance', [F, 'latest']), 16) / 1e18)
