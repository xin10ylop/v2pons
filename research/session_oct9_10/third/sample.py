"""trace one executor dump: token, launch, creator funding (dispatcher burst), dispatcher's funder, buyers, collector onward"""
from lib3 import *
import blk3
from collections import defaultdict
F = '0x7ed598bcef8bd9edd8c97a195c6d13f40801ec7e'; TC = '0x8d4aad4953d0ca700d468f3753aa14432d1b35b43ec6409f051fb6aa43a89607'
SW = '0x0571d85fc9cce8d2ebf18e983becef6cc884e37503f377f9b6383d65850f96d2'; SELL = '0x8113d738abdcb6b38357e9d53a54a7157861a09031b453651f0fe7fe151f59df'
REL = '0x37bd8ddc5d977ce42a8180366ebe48bdd6d13a75'
def plain(lo, hi):
    return [(bn, ts, t) for bn, ts, t in blk3.txs(lo, hi) if int(t[3]) > 0 and t[6] == 0]
def trace(dbn, h):
    o = {'dump_bn': dbn, 'dump_tx': h}
    rc = rpc('eth_getTransactionReceipt', [h])
    col = defaultdict(float); hold = []
    for l in rc['logs']:
        t0 = l['topics'][0]
        if t0.startswith('0xa801e276'): o['token'] = '0x' + l['topics'][1][26:]
        if t0.startswith('0x3cc54530'): hold.append('0x' + l['topics'][1][26:])
        if t0 == SW: col['0x' + l['topics'][2][26:]] += int(l['data'][2:66], 16) / 1e18
        if t0 == SELL: o['sell_eth'] = int(l['data'][66:130], 16) / 1e18; o['curve'] = l['address'].lower()
    o['holders'] = hold; o['collector'] = max(col, key=col.get) if col else None
    la = logs({'address': F, 'topics': [TC, '0x' + '0' * 24 + o['token'][2:]]}, dbn - 3000000, dbn)
    if la:
        l = la[0]; o['launch_bn'] = int(l['blockNumber'], 16); o['creator'] = '0x' + l['topics'][3][26:]; o['curve'] = '0x' + l['topics'][2][26:]
        o['quote'] = '0x' + l['data'][26:66]
    lb = o['launch_bn']
    o['launch_utc'] = utc(blk3.chunk(lb // 100)[lb][0]); o['dump_utc'] = utc(blk3.chunk(dbn // 100)[dbn][0])
    # creator funding
    P = plain(lb - 700, lb)
    f = [(bn, t) for bn, ts, t in P if t[2] == o['creator']]
    if f:
        fb, ft = f[-1]; disp = ft[1]; o['dispatcher'] = disp; o['disp_to_creator'] = int(ft[3]) / 1e18; o['fund_bn'] = fb
        burst = [(bn, t) for bn, ts, t in plain(fb - 40, fb + 60) if t[1] == disp]
        o['burst_n'] = len(burst); o['burst_eth'] = round(sum(int(t[3]) for _, t in burst) / 1e18, 4); o['crowd'] = [t[2] for _, t in burst]
        P2 = plain(fb - 400, fb)
        g = [(bn, t) for bn, ts, t in P2 if t[2] == disp]
        if g: o['disp_funder'] = g[-1][1][1]; o['disp_funded_eth'] = int(g[-1][1][3]) / 1e18; o['disp_funded_bn'] = g[-1][0]
    # buyers in first 300 blocks
    # collector onward
    if o['collector']:
        C = [(bn, t) for bn, ts, t in plain(dbn, dbn + 120) if t[1] == o['collector']]
        o['collector_out'] = [[bn, t[2], int(t[3]) / 1e18] for bn, t in C]
    return o
if __name__ == '__main__':
    import sys
    d = json.load(open('ex_hist.json'))['dumps']
    picks = [int(x) for x in sys.argv[1:]]
    res = []
    for p in picks:
        x = min(d, key=lambda r: abs(r[0] - p))
        try: o = trace(x[0], x[1])
        except Exception as e: print('ERR', x, e); continue
        res.append(o)
        print(json.dumps({k: v for k, v in o.items() if k not in ('crowd', 'holders')})[:1500], flush=True)
        print('   holders', len(o['holders']), 'crowd', len(o.get('crowd', [])), 'overlap holders/crowd', len(set(o['holders']) & set(o.get('crowd', []) + [o.get('creator')])), flush=True)
    json.dump(res, open('samples_%s.json' % '_'.join(sys.argv[1:2]), 'w'))
