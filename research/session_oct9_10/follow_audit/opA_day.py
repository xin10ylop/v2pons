"""Operator A on Oct 10 (00:00 UTC -> head): every launch through its launcher or a copy, plus a classification of every other ETH-pool launch family."""
import sys, json, datetime, collections
sys.path.insert(0, '/home/user/v2pons/research/session_oct9_10')
from chain import rpc, batch, logs, PM, T_INIT, T_SWAP, T_ML, W, sgn, block_at, OP
UTC = datetime.timezone.utc
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
t_lo = int(datetime.datetime(2026, 10, 10, 0, 0, tzinfo=UTC).timestamp())
a = block_at(t_lo); head = int(rpc('eth_blockNumber', []), 16)
inits = logs({'address': PM, 'topics': [T_INIT, None, '0x' + '0' * 64]}, a, head)
print('ETH-paired pools initialized since 00:00 UTC:', len(inits), 'blocks', a, head)
txh = sorted({l['transactionHash'] for l in inits}); txs = {}
for i in range(0, len(txh), 200):
    ch = txh[i:i + 200]; txs.update(dict(zip(ch, batch([('eth_getTransactionByHash', [h]) for h in ch]))))
bns = sorted({int(l['blockNumber'], 16) for l in inits}); ts = {}
for i in range(0, len(bns), 100):
    ch = bns[i:i + 100]
    for bn, blk in zip(ch, batch([('eth_getBlockByNumber', [hex(x), False]) for x in ch])):
        ts[bn] = int(blk['timestamp'], 16)
fams = collections.defaultdict(list); ops = []
for l in inits:
    t = txs[l['transactionHash']]; to = (t.get('to') or '').lower(); inp = t['input']; sel = inp[2:10]; val = int(t['value'], 16); d = l['data']; bn = int(l['blockNumber'], 16)
    kind = 'A-orig' if to == '0x' + OP else ('A-copy' if sel == '2fcb9108' else None)
    if to == '0x58daec3116aae6d93017baaea7749052e8a04fa7' and val == 2433328500000000000: kind = kind or 'front'
    key = kind or f"to {to[:10]} sel {sel} len {(len(inp) - 2) // 2} val {val / 1e18:.4g} fee {W(d, 0)} ts {sgn(W(d, 1))}"
    fams[key].append((bn, ts[bn]))
    if kind and kind.startswith('A'):
        ops.append({'pid': l['topics'][1], 'bn': bn, 't': ts[bn], 'kind': kind, 'fee': W(d, 0), 'ts': sgn(W(d, 1)), 'hooks': W(d, 2), 'from': t['from'].lower(), 'to': to})
print('\nfamilies today (count, first, last):')
for k, v in sorted(fams.items(), key=lambda kv: -len(kv[1])):
    v.sort(); print(f"  {len(v):4d}  {datetime.datetime.fromtimestamp(v[0][1], UTC).strftime('%H:%M:%S')} - {datetime.datetime.fromtimestamp(v[-1][1], UTC).strftime('%H:%M:%S')}  {k}")
ops.sort(key=lambda o: o['bn'])
print('\noperator A launches today:', len(ops))
print('per hour:', sorted(collections.Counter(datetime.datetime.fromtimestamp(o['t'], UTC).strftime('%H') for o in ops).items()))
print('by kind:', collections.Counter(o['kind'] for o in ops))
print('fees:', sorted(collections.Counter(o['fee'] for o in ops).items()))
if ops:
    last = ops[-12:]; print('last launches:', len(last))
    pids = [o['pid'] for o in last]
    lg = logs({'address': PM, 'topics': [[T_SWAP, T_ML], pids]}, last[0]['bn'], head)
    ev = collections.defaultdict(list)
    for l in lg:
        d = l['data']; bn = int(l['blockNumber'], 16)
        ev[l['topics'][1]].append(('swap', bn, s128(W(d, 0))) if l['topics'][0] == T_SWAP else ('ml', bn, sgn(W(d, 2))))
    for o in last:
        e = sorted(ev[o['pid']], key=lambda x: x[1]); b0 = o['bn']
        buys = [(x[1] - b0, -x[2]) for x in e if x[0] == 'swap' and x[2] < 0]
        first = next((bo for bo, v in buys if v >= 0.0002e18), None); pull = next((x[1] - b0 for x in e if x[0] == 'ml' and x[2] < 0), None)
        print(f"  {datetime.datetime.fromtimestamp(o['t'], UTC).strftime('%H:%M:%S')} {o['kind']} fee {o['fee'] / 1e4:.3f}% ts {o['ts']} hooks {o['hooks']} first real buy +{first} buys {len(buys)} eth {sum(v for _, v in buys) / 1e18:.4f} pull +{pull} | buys {[(bo, round(v / 1e18, 5)) for bo, v in buys[:12]]}")
json.dump({'ops': ops, 'fams': {k: len(v) for k, v in fams.items()}}, open('opA_day.json', 'w'), indent=1, default=str)
