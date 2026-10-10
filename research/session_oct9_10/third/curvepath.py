"""price path of third-system launches: curve buy/sell events (ec36bf57 buy, 8113d738 sell) from launch to dump+50, crowd vs outsiders"""
from lib3 import *
BUY = '0xec36bf571f136799e8dc0b0b8bea4b04d8bd3d43de838aab0d5fc21d4cbfc455'; SELL = '0x8113d738abdcb6b38357e9d53a54a7157861a09031b453651f0fe7fe151f59df'
EX = '0xbbd947c36904eb5f28aeaa5593fbcb5a228551ad'
def path(curve, lb, db, crowd):
    ls = logs({'address': curve}, lb, db + 3000)
    rows = []
    for l in ls:
        t0 = l['topics'][0]; bn = int(l['blockNumber'], 16)
        dd = [int(l['data'][2+i:66+i], 16) for i in range(0, len(l['data']) - 2, 64)]
        if t0 == BUY:
            who = '0x' + l['topics'][2][26:]; rows.append([bn - lb, 'BUY', who, dd[0] / 1e18, dd[1] / 1e18, (dd[0] / dd[1]) * 1e9 if dd[1] else 0, who in crowd])
        elif t0 == SELL:
            who = '0x' + l['topics'][1][26:]; rows.append([bn - lb, 'SELL', who, dd[1] / 1e18, dd[0] / 1e18, (dd[1] / dd[0]) * 1e9 if dd[0] else 0, who in crowd or who == EX])
    return rows
if __name__ == '__main__':
    lk = json.load(open('links_84116000_84147499.json'))
    cl = {r['creator']: r for r in json.load(open('classify_84116000_84147499.json'))}
    import lib2, bc
    out = {}
    for r in lk:
        if r['kind'] != 'dump' or not r['launch_bn']: continue
        c = cl.get(r['creator'])
        crowd = set(r['wallets']) | {r['creator']}
        if c and c['fund_src']:
            crowd |= {t[2] for bn, ts, t in bc.txs(c['bn'] - 700, c['bn']) if t[1] == c['fund_src'] and int(t[3]) > 0}
        p = path(r['curve'], r['launch_bn'], r['bn'], crowd)
        out[r['token']] = dict(launch=r['launch_bn'], dump=r['bn'], rows=p)
        print('=== token', r['token'][:10], 'launch', r['launch_bn'], 'dump +%d blocks' % (r['bn'] - r['launch_bn']), 'quote', r['quote'])
        for x in p: print('   +%5d %-4s %s %-5s eth %.4f tok %.3gM px %.3f' % (x[0], x[1], x[2][:10], 'CROWD' if x[6] else 'OUT', x[3], x[4] / 1e6, x[5]))
    json.dump(out, open('curvepath.json', 'w'))
