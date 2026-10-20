"""Every swap our relay made since 09:00 UTC Oct 10 (the live front start was 09:07), from the PoolManager's Swap events with sender = relay.
Pairs them per pool into trades, prints a table, saves our_swaps.json. Then for every trade whose sell got 0 ETH (or has no sell swap),
pulls the pool's full record (Initialize, every Swap and ModifyLiquidity, every tx in the blocks launch..sell+3) into losers.json."""
import sys, json, datetime, time
sys.path.insert(0, '/home/user/v2pons/research/session_oct9_10'); sys.path.insert(0, '/home/user/v2pons/src')
from chain import rpc, batch, logs, PM, T_INIT, T_SWAP, T_ML, W, sgn, block_at
RELAY = '0x2abb5653352f6b2f3b4f4261877cd02d9e05a957'; WALLET = '0xab5a34c3f41e57fdee1a1d6f19d3e21f46df3ea8'
BOT_ROUTER = '1cbaf24d53fe930fce8eff149fa797d2611da149'; POSM = '58daec3116aae6d93017baaea7749052e8a04fa7'
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
pad = lambda a: '0x' + a.lower().replace('0x', '').zfill(64)
UTC = datetime.timezone.utc
t_lo = int(datetime.datetime(2026, 10, 10, 9, 0, tzinfo=UTC).timestamp())
a = block_at(t_lo); head = int(rpc('eth_blockNumber', []), 16)
print('window blocks', a, head, 'head time', datetime.datetime.fromtimestamp(int(rpc('eth_getBlockByNumber', [hex(head), False])['timestamp'], 16), UTC))
sw = logs({'address': PM, 'topics': [T_SWAP, None, pad(RELAY)]}, a, head)
print('relay swaps', len(sw))
txh = sorted({l['transactionHash'] for l in sw})
txs = dict(zip(txh, batch([('eth_getTransactionByHash', [h]) for h in txh])))
rows = []
for l in sw:
    t = txs[l['transactionHash']]; d = l['data']
    rows.append({'bn': int(l['blockNumber'], 16), 'ti': int(l['transactionIndex'], 16), 'pid': l['topics'][1], 'a0': s128(W(d, 0)), 'a1': s128(W(d, 1)), 'sp': W(d, 2), 'L': W(d, 3),
                 'tx': l['transactionHash'], 'nonce': int(t['nonce'], 16), 'sel': t['input'][2:10], 'gasPrice': int(t['gasPrice'], 16)})
rows.sort(key=lambda r: (r['bn'], r['ti']))
# block timestamps for the trades' buy blocks
bns = sorted({r['bn'] for r in rows})
ts = {}
for i in range(0, len(bns), 50):
    ch = bns[i:i + 50]
    for b, blk in zip(ch, batch([('eth_getBlockByNumber', [hex(b), False]) for b in ch])):
        ts[b] = int(blk['timestamp'], 16)
trades = {}
for r in rows:
    tr = trades.setdefault(r['pid'], {'pid': r['pid'], 'buys': [], 'sells': []})
    (tr['buys'] if r['sel'] == '5ed06f60' else tr['sells']).append(r)
out = []
for pid, tr in trades.items():
    b = tr['buys'][0] if tr['buys'] else None; s = tr['sells'][0] if tr['sells'] else None
    eth_in = -b['a0'] if b else 0; eth_out = s['a0'] if s else None
    out.append({'pid': pid, 'time': datetime.datetime.fromtimestamp(ts[b['bn']], UTC).strftime('%H:%M:%S') if b else None, 'buy_bn': b['bn'] if b else None, 'buy_nonce': b['nonce'] if b else None,
                'sell_bn': s['bn'] if s else None, 'sell_nonce': s['nonce'] if s else None, 'eth_in': eth_in / 1e18, 'eth_out': (eth_out / 1e18) if eth_out is not None else None,
                'tokens': b['a1'] if b else None, 'tokens_sold': -s['a1'] if s else None, 'ret': ((eth_out - eth_in) / eth_in) if (b and s and eth_in) else None,
                'sell_after_buy': (s['bn'] - b['bn']) if (b and s) else None, 'n_buys': len(tr['buys']), 'n_sells': len(tr['sells']), 'buy_tx': b['tx'] if b else None, 'sell_tx': s['tx'] if s else None})
out.sort(key=lambda x: x['buy_bn'] or 0)
json.dump(out, open('our_swaps.json', 'w'), indent=1)
print(f"{'time':8s} {'buy_bn':>9s} {'nonce':>5s} {'stake':>7s} {'eth_out':>8s} {'ret':>8s} {'sold@':>5s} pid")
losers = []
for x in out:
    flag = ''
    if x['ret'] is None or x['ret'] < -0.5:
        flag = '   <== LOSS'; losers.append(x)
    if flag or x['ret'] is not None and x['ret'] < 0 or x['n_buys'] != 1 or x['n_sells'] != 1:
        print(f"{x['time']:8s} {x['buy_bn']:>9} {x['buy_nonce']:>5} {x['eth_in']:7.4f} {str(round(x['eth_out'], 5)) if x['eth_out'] is not None else 'none':>8s} {('%+.1f%%' % (100 * x['ret'])) if x['ret'] is not None else 'n/a':>8s} {str(x['sell_after_buy']):>5s} {x['pid'][:12]} buys {x['n_buys']} sells {x['n_sells']}{flag}")
rets = [x['ret'] for x in out if x['ret'] is not None]
import statistics as st
print('trades', len(out), 'with ret', len(rets), 'mean %+.2f%% median %+.2f%% up %d, <0: %d, <-50%%: %d' % (100 * st.mean(rets), 100 * st.median(rets), sum(1 for r in rets if r > 0), sum(1 for r in rets if r <= 0), sum(1 for r in rets if r < -0.5)))
print('stakes:', sorted({round(x['eth_in'], 5) for x in out}))
print('sold-after-buy distribution:', sorted(((k, v) for k, v in __import__('collections').Counter(x['sell_after_buy'] for x in out).items()), key=lambda kv: (kv[0] is None, kv[0])))
print('LOSERS', len(losers))
# ---- the losers' full record
rec = []
for x in losers:
    pid = x['pid']; b0 = x['buy_bn']; s1 = x['sell_bn'] or (b0 + 25)
    init = logs({'address': PM, 'topics': [T_INIT, pid]}, b0 - 40, b0)
    L = int(init[0]['blockNumber'], 16) if init else None
    lo = (L if L else b0 - 5) - 1; hi = s1 + 40
    lg = logs({'address': PM, 'topics': [[T_SWAP, T_ML], pid]}, lo, hi)
    ev = []
    for l in lg:
        d = l['data']
        if l['topics'][0] == T_SWAP:
            ev.append({'kind': 'swap', 'bn': int(l['blockNumber'], 16), 'ti': int(l['transactionIndex'], 16), 'sender': '0x' + l['topics'][2][-40:], 'a0': s128(W(d, 0)) / 1e18, 'a1': s128(W(d, 1)), 'sp': W(d, 2), 'L': W(d, 3), 'tx': l['transactionHash']})
        else:
            ev.append({'kind': 'modliq', 'bn': int(l['blockNumber'], 16), 'ti': int(l['transactionIndex'], 16), 'sender': '0x' + l['topics'][2][-40:], 'dl': sgn(W(d, 2)), 'tx': l['transactionHash']})
    ev.sort(key=lambda e: (e['bn'], e['ti']))
    # every transaction in the blocks launch .. sell + 3 (reverted ones included): who touched the token
    token = '0x' + init[0]['topics'][3][-40:] if init else None
    blocks = {}
    need = list(range(L if L else b0 - 2, s1 + 4))
    for i in range(0, len(need), 25):
        ch = need[i:i + 25]
        for b, blk in zip(ch, batch([('eth_getBlockByNumber', [hex(b), True]) for b in ch])):
            blocks[b] = blk
    touched = []
    tb = bytes.fromhex(token[2:]) if token else b''
    for b in sorted(blocks):
        blk = blocks[b]
        for t in blk['transactions']:
            inp = t['input']; to = (t.get('to') or '').lower(); frm = t['from'].lower(); val = int(t['value'], 16)
            if (tb and tb in bytes.fromhex(inp[2:])) or frm == WALLET or to == RELAY.lower() or to == '0x' + BOT_ROUTER:
                touched.append({'bn': b, 'ti': int(t['transactionIndex'], 16), 'from': frm, 'to': to, 'value': val / 1e18, 'sel': inp[2:10], 'len': (len(inp) - 2) // 2, 'hash': t['hash'], 'nonce': int(t['nonce'], 16),
                                'carries_token': bool(tb and tb in bytes.fromhex(inp[2:]))})
    hashes = sorted({t['hash'] for t in touched})
    recs = dict(zip(hashes, batch([('eth_getTransactionReceipt', [h]) for h in hashes])))
    for t in touched:
        r = recs.get(t['hash']); t['status'] = (r or {}).get('status'); t['gasUsed'] = int(r['gasUsed'], 16) if r else None
    tsb = {b: int(blocks[b]['timestamp'], 16) for b in blocks}
    rec.append({'trade': x, 'launch_block': L, 'token': token, 'events': ev, 'txs_touching': touched, 'block_ts': tsb,
                'launch_tx': init[0]['transactionHash'] if init else None})
    print('\n=== LOSER', x['time'], 'pid', pid, 'launch block', L, 'our buy', b0, '(+%s)' % (b0 - L if L else '?'), 'our sell', x['sell_bn'], 'token', token)
    for e in ev:
        off = e['bn'] - L if L else None
        if e['kind'] == 'swap':
            who = 'RELAY(us)' if e['sender'].lower() == RELAY else ('BOT_ROUTER' if e['sender'].lower()[2:] == BOT_ROUTER else e['sender'][:10])
            print(f"  +{off:>3} blk {e['bn']} ti {e['ti']:>2} SWAP   {who:12s} eth {e['a0']:+.6f} tokens {e['a1']:+d} L {e['L']}")
        else:
            print(f"  +{off:>3} blk {e['bn']} ti {e['ti']:>2} MODLIQ {e['sender'][:10]:12s} dl {e['dl']:+d}")
    print('  txs touching the token / us / the bot router (reverted included):')
    for t in touched:
        off = t['bn'] - L if L else None
        who = 'WALLET(us)' if t['from'] == WALLET else t['from'][:10]
        tag = 'BOT_ROUTER' if t['to'] == '0x' + BOT_ROUTER else ('RELAY' if t['to'] == RELAY.lower() else ('POSM' if t['to'] == '0x' + POSM else t['to'][:10]))
        print(f"  +{off:>3} blk {t['bn']} ti {t['ti']:>2} {who:12s} -> {tag:12s} val {t['value']:.6f} sel {t['sel']} len {t['len']:>5} status {t['status']} nonce {t['nonce']} {'token' if t['carries_token'] else ''}")
    print('  block times:', {b - L: datetime.datetime.fromtimestamp(tsb[b], UTC).strftime('%H:%M:%S') for b in sorted(tsb) if (b - L) % 5 == 0 or b in (b0, x['sell_bn'])})
json.dump(rec, open('losers.json', 'w'), indent=1, default=str)
print('saved our_swaps.json, losers.json')
