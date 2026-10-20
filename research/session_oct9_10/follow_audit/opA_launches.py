"""Operator A's launches 10:00 UTC Oct 10 -> head: through its original launcher (to == 0x3194e326) or a per-launch copy (selector 2fcb9108);
per launch: fee, the crowd's first real buy (>= 0.0002 ETH) offset, buys within 150 blocks, the pull offset. For HANDOFF 12.4 ('follow is not moving')."""
import sys, json, datetime, collections
sys.path.insert(0, '/home/user/v2pons/research/session_oct9_10'); sys.path.insert(0, '/home/user/v2pons/src')
from chain import rpc, batch, logs, PM, T_INIT, T_SWAP, T_ML, W, sgn, block_at, OP
import v4math
UTC = datetime.timezone.utc
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
t_lo = int(datetime.datetime(2026, 10, 10, 10, 0, tzinfo=UTC).timestamp())
a = block_at(t_lo); head = int(rpc('eth_blockNumber', []), 16)
inits = logs({'address': PM, 'topics': [T_INIT, None, '0x' + '0' * 64]}, a, head)
print('ETH-paired pools initialized since 10:00 UTC:', len(inits), 'blocks', a, head)
txh = sorted({l['transactionHash'] for l in inits}); txs = {}
for i in range(0, len(txh), 200):
    ch = txh[i:i + 200]; txs.update(dict(zip(ch, batch([('eth_getTransactionByHash', [h]) for h in ch]))))
ops = []
fam = collections.Counter()
for l in inits:
    t = txs[l['transactionHash']]; to = (t.get('to') or '').lower(); sel = t['input'][2:10]; val = int(t['value'], 16)
    kind = 'orig' if to == '0x' + OP else ('copy' if sel == '2fcb9108' else None)
    fam[(kind or ('front' if to == '0x58daec3116aae6d93017baaea7749052e8a04fa7' and val == 2433328500000000000 else 'other'))] += 1
    if kind:
        d = l['data']
        ops.append({'pid': l['topics'][1], 'bn': int(l['blockNumber'], 16), 'kind': kind, 'fee': W(d, 0), 'ts': sgn(W(d, 1)), 'hooks': W(d, 2), 'sp0': W(d, 3), 'tick0': sgn(W(d, 4)), 'tx': l['transactionHash'], 'to': to, 'from': t['from'].lower()})
print('launch families:', dict(fam))
ops.sort(key=lambda o: o['bn'])
bns = sorted({o['bn'] for o in ops}); ts = {}
for i in range(0, len(bns), 50):
    ch = bns[i:i + 50]
    for bn, blk in zip(ch, batch([('eth_getBlockByNumber', [hex(x), False]) for x in ch])):
        ts[bn] = int(blk['timestamp'], 16)
pids = [o['pid'] for o in ops]
lg = []
for i in range(0, len(pids), 20):
    lg += logs({'address': PM, 'topics': [[T_SWAP, T_ML], pids[i:i + 20]]}, a - 10, head)
ev = collections.defaultdict(list)
for l in lg:
    d = l['data']; bn = int(l['blockNumber'], 16)
    if l['topics'][0] == T_SWAP:
        ev[l['topics'][1]].append(('swap', bn, s128(W(d, 0)), s128(W(d, 1))))
    else:
        ev[l['topics'][1]].append(('ml', bn, sgn(W(d, 2)), None))
print(f"\n{'time':8s} {'kind':4s} {'fee%':>6s} {'liq>=1e21':>9s} {'1st buy':>7s} {'buys<=150':>9s} {'eth<=150':>8s} {'pull':>6s}  pid")
rows = []
for o in ops:
    e = sorted(ev[o['pid']], key=lambda x: x[1]); b0 = o['bn']
    adds = [(x[2]) for x in e if x[0] == 'ml' and x[2] > 0 and x[1] <= b0 + 1]
    liq = sum(adds)
    buys = [(x[1] - b0, -x[2]) for x in e if x[0] == 'swap' and x[2] < 0]
    first = next((bo for bo, v in buys if v >= 0.0002e18), None)
    pull = next((x[1] - b0 for x in e if x[0] == 'ml' and x[2] < 0), None)
    in150 = [v for bo, v in buys if bo <= 150]
    eligible = o['fee'] <= 9999 and o['hooks'] == 0 and liq >= 1e21
    row = {'time': datetime.datetime.fromtimestamp(ts[b0], UTC).strftime('%H:%M:%S'), 'kind': o['kind'], 'fee': o['fee'], 'eligible': eligible, 'liq': liq, 'first_buy_off': first, 'buys150': len(in150), 'eth150': sum(in150) / 1e18, 'pull_off': pull, 'pid': o['pid'], 'bn': b0, 'from': o['from'], 'n_buys': len(buys)}
    rows.append(row)
    print(f"{row['time']:8s} {o['kind']:4s} {o['fee'] / 1e4:6.3f} {'yes' if liq >= 1e21 else 'NO':>9s} {str(first):>7s} {len(in150):>9d} {sum(in150) / 1e18:8.4f} {str(pull):>6s}  {o['pid'][:10]}{'' if eligible else '   NOT ELIGIBLE'}")
json.dump(rows, open('opA_launches.json', 'w'), indent=1)
print('\nlaunches', len(rows), 'eligible', sum(1 for r in rows if r['eligible']), 'with a first real buy within 150 blocks', sum(1 for r in rows if r['first_buy_off'] is not None and r['first_buy_off'] <= 150))
import statistics as st
fo = [r['first_buy_off'] for r in rows if r['first_buy_off'] is not None]
if fo: print('first buy offsets: min', min(fo), 'median', st.median(fo), 'max', max(fo))
print('per hour:', sorted(collections.Counter(r['time'][:2] for r in rows).items()))
print('fees:', sorted(collections.Counter(r['fee'] for r in rows).items()))
